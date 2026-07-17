from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from app.domain.search_constraints import CandidateLocation, ConstraintCandidateFacts
from app.domain.search_policy import SearchPolicy, load_search_policy
from app.domain.search_refinement_snapshot import (
    RefinementBaselineCandidate,
    RefinementBaselineSnapshot,
    RefinementFactorEvaluation,
    SearchRefinementSnapshotStore,
    canonical_search_intent_digest,
)
from app.domain.search_v4_models import SearchIntent

pytestmark = pytest.mark.db_free


class _Clock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def _candidate(candidate_id: str = "candidate") -> RefinementBaselineCandidate:
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
    return RefinementBaselineCandidate(
        candidate_id=candidate_id,
        ski_region_id="ski-region",
        constraint_facts=constraint_facts,
        evaluations=(evaluation,),
        unscored=False,
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
    assert store.get(first.fingerprint, first.intent_digest).outcome == "miss"


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
