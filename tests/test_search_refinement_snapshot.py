from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from datetime import date
from types import SimpleNamespace
from typing import cast

import pytest

from app.domain.search_constraints import CandidateLocation, ConstraintCandidateFacts
from app.domain.search_policy import SearchPolicy, load_search_policy
from app.domain.search_refinement_snapshot import (
    RefinementBaselineCandidate,
    RefinementBaselineSnapshot,
    RefinementCandidateReplayState,
    RefinementFactorEvaluation,
    SearchRefinementSnapshotStore,
    WeatherEvaluationReplayContextTemplate,
    canonical_search_intent_digest,
)
from app.domain.search_v4_models import SearchIntent

pytestmark = pytest.mark.db_free


class _Clock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class _ManualCleanupHandle:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class _ManualCleanupScheduler:
    def __init__(self) -> None:
        self.callback = None
        self.handle = _ManualCleanupHandle()

    def start(self, *, interval_seconds: float, callback):
        assert interval_seconds > 0
        self.callback = callback
        return self.handle

    def run_once(self) -> int:
        assert self.callback is not None
        return self.callback()


def _candidate(
    candidate_id: str = "candidate",
    *,
    weather_rows: tuple[object, ...] = (),
) -> RefinementBaselineCandidate:
    constraint_facts = ConstraintCandidateFacts(
        candidate_id=candidate_id,
        location=CandidateLocation(
            country="Austria",
            region="Tyrol",
            ski_region_ids=("ski-region",),
            destination_id="destination",
        ),
    )
    evaluation = RefinementFactorEvaluation(
        factor_id="accessible_terrain_scale",
        raw_utility=0.75,
        neutral_utility=0.5,
        effective_evidence_cap=1,
    )
    replay_state = (
        cast(
            RefinementCandidateReplayState,
            SimpleNamespace(
                weather_candidate=SimpleNamespace(
                    climatology_rows=weather_rows,
                    forecast_rows=(),
                )
            ),
        )
        if weather_rows
        else None
    )
    return RefinementBaselineCandidate(
        candidate_id=candidate_id,
        ski_region_id="ski-region",
        constraint_facts=constraint_facts,
        evaluations=(evaluation,),
        unscored=False,
        replay_state=replay_state,
    )


def _snapshot(
    fingerprint: str = "fingerprint",
    *,
    intent: SearchIntent | None = None,
    policy: SearchPolicy | None = None,
) -> RefinementBaselineSnapshot:
    resolved_intent = intent or SearchIntent()
    return RefinementBaselineSnapshot(
        fingerprint=fingerprint,
        intent_digest=canonical_search_intent_digest(resolved_intent),
        policy=policy or load_search_policy(),
        candidates=(_candidate(f"candidate-{fingerprint}"),),
    )


def _capacity_snapshot(
    fingerprint: str,
    *,
    candidate_count: int = 1,
    weather_rows: tuple[object, ...] = (),
) -> RefinementBaselineSnapshot:
    return RefinementBaselineSnapshot(
        fingerprint=fingerprint,
        intent_digest=canonical_search_intent_digest(SearchIntent()),
        policy=load_search_policy(),
        candidates=tuple(
            _candidate(
                f"candidate-{fingerprint}-{index}",
                weather_rows=weather_rows,
            )
            for index in range(candidate_count)
        ),
    )


def test_canonical_intent_digest_is_stable_and_changes_with_intent() -> None:
    intent = SearchIntent()
    payload = intent.model_dump(mode="json", exclude_computed_fields=True)
    reordered = SearchIntent.model_validate(dict(reversed(tuple(payload.items()))))
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    assert canonical_search_intent_digest(intent) == expected
    assert canonical_search_intent_digest(reordered) == expected
    assert (
        canonical_search_intent_digest(SearchIntent(assumptions=("Flexible dates",)))
        != expected
    )


def test_weather_replay_preserves_original_reference_date_at_forecast_boundary() -> (
    None
):
    reference_date = date(2027, 1, 1)
    template = WeatherEvaluationReplayContextTemplate(
        policy=load_search_policy(),
        reference_date=reference_date,
        stale_run_ids=frozenset({"stale-run"}),
    )

    replay = template.materialize(SearchIntent())

    assert replay.reference_date == reference_date
    assert replay.stale_run_ids == frozenset({"stale-run"})


def test_put_and_get_return_frozen_results_for_a_hit() -> None:
    store = SearchRefinementSnapshotStore()
    snapshot = _snapshot()

    mutation = store.put(snapshot)
    lookup = store.get(snapshot.fingerprint, snapshot.intent_digest)

    assert mutation.expired_count == 0
    assert mutation.evicted_count == 0
    assert lookup.outcome == "hit"
    assert lookup.snapshot is snapshot
    assert len(store) == 1
    with pytest.raises(FrozenInstanceError):
        mutation.expired_count = 1  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        lookup.outcome = "miss"  # type: ignore[misc]


def test_get_returns_miss_for_unknown_fingerprint() -> None:
    result = SearchRefinementSnapshotStore().get("missing", "intent")

    assert result.outcome == "miss"
    assert result.snapshot is None


def test_intent_mismatch_does_not_return_or_remove_snapshot() -> None:
    store = SearchRefinementSnapshotStore()
    snapshot = _snapshot()
    store.put(snapshot)

    mismatch = store.get(snapshot.fingerprint, "different-intent")

    assert mismatch.outcome == "intent_mismatch"
    assert mismatch.snapshot is None
    assert len(store) == 1
    assert store.get(snapshot.fingerprint, snapshot.intent_digest).snapshot is snapshot


def test_entry_expires_at_exact_ttl_boundary_and_is_removed() -> None:
    clock = _Clock(50)
    store = SearchRefinementSnapshotStore(ttl_seconds=10, clock=clock)
    snapshot = _snapshot()
    store.put(snapshot)

    clock.now = 59.999
    assert store.get(snapshot.fingerprint, snapshot.intent_digest).outcome == "hit"

    clock.now = 60
    expired = store.get(snapshot.fingerprint, snapshot.intent_digest)

    assert expired.outcome == "expired"
    assert expired.snapshot is None
    assert len(store) == 0
    assert store.get(snapshot.fingerprint, snapshot.intent_digest).outcome == "miss"


def test_successful_hit_touches_lru_recency_before_eviction() -> None:
    store = SearchRefinementSnapshotStore(max_entries=2)
    first = _snapshot("first")
    second = _snapshot("second")
    third = _snapshot("third")
    store.put(first)
    store.put(second)

    assert store.get(first.fingerprint, first.intent_digest).outcome == "hit"
    mutation = store.put(third)

    assert mutation.evicted_count == 1
    assert store.get(second.fingerprint, second.intent_digest).outcome == "miss"
    assert store.get(first.fingerprint, first.intent_digest).outcome == "hit"
    assert store.get(third.fingerprint, third.intent_digest).outcome == "hit"


def test_put_purges_all_expired_entries_and_reports_count() -> None:
    clock = _Clock()
    store = SearchRefinementSnapshotStore(
        ttl_seconds=10,
        max_entries=2,
        clock=clock,
    )
    first = _snapshot("first")
    second = _snapshot("second")
    third = _snapshot("third")
    store.put(first)
    clock.now = 5
    store.put(second)

    clock.now = 10
    mutation = store.put(third)

    assert mutation.expired_count == 1
    assert mutation.evicted_count == 0
    assert len(store) == 2
    assert store.get(first.fingerprint, first.intent_digest).outcome == "expired"


def test_store_never_exceeds_max_entries() -> None:
    store = SearchRefinementSnapshotStore(max_entries=3)
    snapshots = tuple(_snapshot(str(index)) for index in range(10))

    mutations = tuple(store.put(snapshot) for snapshot in snapshots)

    assert len(store) == 3
    assert sum(result.evicted_count for result in mutations) == 7
    assert all(
        store.get(snapshot.fingerprint, snapshot.intent_digest).outcome == "miss"
        for snapshot in snapshots[:-3]
    )
    assert all(
        store.get(snapshot.fingerprint, snapshot.intent_digest).outcome == "hit"
        for snapshot in snapshots[-3:]
    )


def test_candidate_budget_evicts_least_recently_used_snapshot() -> None:
    store = SearchRefinementSnapshotStore(max_candidate_replay_states=2)
    first = _capacity_snapshot("first")
    second = _capacity_snapshot("second")
    third = _capacity_snapshot("third")
    store.put(first)
    store.put(second)
    assert store.get(first.fingerprint, first.intent_digest).outcome == "hit"

    mutation = store.put(third)

    assert mutation.evicted_count == 1
    assert mutation.capacity_rejected is False
    assert store.get(second.fingerprint, second.intent_digest).outcome == "miss"
    assert store.get(first.fingerprint, first.intent_digest).outcome == "hit"
    assert store.get(third.fingerprint, third.intent_digest).outcome == "hit"
    assert store.usage().candidate_replay_state_count == 2


def test_weather_row_budget_counts_shared_rows_once_and_evicts_lru() -> None:
    store = SearchRefinementSnapshotStore(max_weather_rows=2)
    first_row = object()
    third_row = object()
    first = _capacity_snapshot(
        "first",
        candidate_count=2,
        weather_rows=(first_row,),
    )
    second = _capacity_snapshot("second", weather_rows=(first_row,))
    third = _capacity_snapshot("third", weather_rows=(third_row,))
    store.put(first)
    assert store.usage().weather_row_count == 1
    store.put(second)
    assert store.usage().weather_row_count == 2
    assert store.get(first.fingerprint, first.intent_digest).outcome == "hit"

    mutation = store.put(third)

    assert mutation.evicted_count == 1
    assert store.get(second.fingerprint, second.intent_digest).outcome == "miss"
    assert store.get(first.fingerprint, first.intent_digest).outcome == "hit"
    assert store.get(third.fingerprint, third.intent_digest).outcome == "hit"
    assert store.usage().weather_row_count == 2


def test_individually_oversized_snapshot_is_not_retained() -> None:
    store = SearchRefinementSnapshotStore(max_candidate_replay_states=1)
    snapshot = _capacity_snapshot("oversized", candidate_count=2)

    mutation = store.put(snapshot)

    assert mutation.capacity_rejected is True
    assert mutation.evicted_count == 0
    assert store.get(snapshot.fingerprint, snapshot.intent_digest).outcome == "miss"
    assert store.usage().entry_count == 0


def test_individually_oversized_weather_snapshot_is_not_retained() -> None:
    store = SearchRefinementSnapshotStore(max_weather_rows=1)
    snapshot = _capacity_snapshot(
        "oversized-weather",
        weather_rows=(object(), object()),
    )

    mutation = store.put(snapshot)

    assert mutation.capacity_rejected is True
    assert mutation.evicted_count == 0
    assert store.get(snapshot.fingerprint, snapshot.intent_digest).outcome == "miss"
    assert store.usage().weather_row_count == 0


def test_cleanup_scheduler_reclaims_expired_snapshot_without_another_request() -> None:
    clock = _Clock()
    scheduler = _ManualCleanupScheduler()
    store = SearchRefinementSnapshotStore(
        ttl_seconds=60,
        clock=clock,
        cleanup_scheduler=scheduler,
        cleanup_interval_seconds=5,
    )
    store.put(_snapshot("active-expiry"))

    clock.now = 60
    assert scheduler.run_once() == 1
    assert store.usage().entry_count == 0
    intent_digest = _snapshot("active-expiry").intent_digest
    assert store.get("active-expiry", intent_digest).outcome == "expired"

    store.close()
    assert scheduler.handle.cancelled is True


def test_scheduled_cleanup_reports_expiry_once_and_bounds_expired_tombstones() -> None:
    clock = _Clock()
    scheduler = _ManualCleanupScheduler()
    expired_counts: list[int] = []
    store = SearchRefinementSnapshotStore(
        ttl_seconds=10,
        max_entries=2,
        clock=clock,
        cleanup_scheduler=scheduler,
        cleanup_interval_seconds=1,
        expiration_observer=expired_counts.append,
    )
    snapshots = tuple(_snapshot(f"expired-{index}") for index in range(3))
    for snapshot in snapshots:
        store.put(snapshot)

    clock.now = 10
    assert scheduler.run_once() == 2
    assert expired_counts == [2]
    assert store.get(snapshots[0].fingerprint, snapshots[0].intent_digest).outcome == (
        "miss"
    )
    retained_expiry = store.get(
        snapshots[-1].fingerprint,
        snapshots[-1].intent_digest,
    )
    assert retained_expiry.outcome == "expired"
    assert retained_expiry.expiration_already_recorded is True


def test_store_supports_basic_concurrent_puts_and_gets() -> None:
    store = SearchRefinementSnapshotStore(max_entries=64)
    policy = load_search_policy()
    snapshots = tuple(_snapshot(str(index), policy=policy) for index in range(32))

    with ThreadPoolExecutor(max_workers=8) as executor:
        mutations = tuple(executor.map(store.put, snapshots))
    with ThreadPoolExecutor(max_workers=8) as executor:
        lookups = tuple(
            executor.map(
                lambda snapshot: store.get(
                    snapshot.fingerprint,
                    snapshot.intent_digest,
                ),
                snapshots,
            )
        )

    assert all(result.evicted_count == 0 for result in mutations)
    assert all(result.outcome == "hit" for result in lookups)
    assert len(store) == len(snapshots)


def test_store_supports_interleaved_concurrent_puts_and_gets() -> None:
    store = SearchRefinementSnapshotStore(max_entries=16)
    policy = load_search_policy()
    snapshots = tuple(_snapshot(str(index), policy=policy) for index in range(64))

    def put_then_get(snapshot: RefinementBaselineSnapshot) -> str:
        store.put(snapshot)
        return store.get(snapshot.fingerprint, snapshot.intent_digest).outcome

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = tuple(executor.map(put_then_get, snapshots))

    assert set(outcomes) <= {"hit", "miss"}
    assert "hit" in outcomes
    assert len(store) <= 16


@pytest.mark.parametrize(
    "kwargs",
    (
        {"ttl_seconds": 0},
        {"ttl_seconds": -1},
        {"max_entries": 0},
        {"max_entries": -1},
        {"max_candidate_replay_states": 0},
        {"max_candidate_replay_states": -1},
        {"max_weather_rows": 0},
        {"max_weather_rows": -1},
        {"cleanup_interval_seconds": 0},
        {"cleanup_interval_seconds": -1},
    ),
)
def test_store_rejects_non_positive_configuration(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        SearchRefinementSnapshotStore(**kwargs)


def test_clear_removes_all_entries() -> None:
    store = SearchRefinementSnapshotStore()
    store.put(_snapshot("first"))
    store.put(_snapshot("second"))

    store.clear()

    assert len(store) == 0
