from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from threading import Event, RLock, Thread
from typing import Literal, Protocol

from app.domain.search_constraints import ConstraintCandidateFacts
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_factors.static import (
    CatalogEvidenceResolver,
    NumericBounds,
    StaticEvaluationContext,
    StaticFactorCandidate,
    build_static_factor_registry,
    derive_numeric_bounds,
)
from app.domain.search_factors.weather import (
    WeatherEvaluationContext,
    WeatherFactorCandidate,
    build_weather_factor_registry,
)
from app.domain.search_policy import SearchPolicy
from app.domain.search_v4_models import SearchIntent

DEFAULT_MAX_SNAPSHOT_ENTRIES = 64
DEFAULT_MAX_CANDIDATE_REPLAY_STATES = 2_048
DEFAULT_MAX_WEATHER_ROWS = 8_192
DEFAULT_CLEANUP_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class RefinementFactorEvaluation:
    factor_id: str
    raw_utility: float
    neutral_utility: float
    effective_evidence_cap: float

    def materialize(self) -> FactorEvaluation:
        return FactorEvaluation(
            factor_id=self.factor_id,
            scope="refinement_snapshot",
            entity_ids=(),
            raw_value=None,
            raw_utility=self.raw_utility,
            neutral_utility=self.neutral_utility,
            effective_evidence_cap=self.effective_evidence_cap,
            evidence_cap_components={},
            warnings=(),
            provenance_summary="Refinement baseline.",
            explanation_inputs={},
        )


@dataclass(frozen=True, slots=True)
class StaticEvaluationReplayContextTemplate:
    """Intent-free static evaluator context retained for bounded replay."""

    policy: SearchPolicy
    trust_resolver: CatalogEvidenceResolver
    numeric_bounds: Mapping[str, NumericBounds]
    pass_duration_days: int
    pass_audience: str
    pass_season_label: str | None

    def materialize(
        self,
        intent: SearchIntent,
        *,
        numeric_bounds: Mapping[str, NumericBounds] | None = None,
    ) -> StaticEvaluationContext:
        return StaticEvaluationContext(
            intent=intent,
            policy=self.policy,
            trust_resolver=self.trust_resolver,
            numeric_bounds=(
                numeric_bounds if numeric_bounds is not None else self.numeric_bounds
            ),
            pass_duration_days=self.pass_duration_days,
            pass_audience=self.pass_audience,
            pass_season_label=self.pass_season_label,
        )


@dataclass(frozen=True, slots=True)
class WeatherEvaluationReplayContextTemplate:
    """Intent-free weather evaluator context retained for bounded replay."""

    policy: SearchPolicy
    stale_run_ids: frozenset[str]

    def materialize(self, intent: SearchIntent) -> WeatherEvaluationContext:
        return WeatherEvaluationContext(
            intent=intent,
            policy=self.policy,
            stale_run_ids=self.stale_run_ids,
        )


@dataclass(frozen=True, slots=True)
class RefinementCandidateReplayState:
    """Exact evaluator inputs retained for one candidate in a bounded baseline."""

    static_context_template: StaticEvaluationReplayContextTemplate
    static_candidate: StaticFactorCandidate
    weather_context_template: WeatherEvaluationReplayContextTemplate
    weather_candidate: WeatherFactorCandidate

    def evaluate(
        self,
        intent: SearchIntent,
        *,
        numeric_bounds: Mapping[str, NumericBounds] | None = None,
    ) -> tuple[FactorEvaluation, ...]:
        static_context = self.static_context_template.materialize(
            intent,
            numeric_bounds=numeric_bounds,
        )
        static_registry = build_static_factor_registry()
        static_evaluations = tuple(
            static_registry.get(factor_id).evaluate(
                static_context,
                self.static_candidate,
            )
            for factor_id in static_registry.factor_ids
        )
        snowmaking = next(
            (
                evaluation
                for evaluation in static_evaluations
                if evaluation.factor_id == "snowmaking_availability"
            ),
            None,
        )
        weather_context = self.weather_context_template.materialize(intent)
        weather_candidate = replace(
            self.weather_candidate,
            snowmaking_evaluation=snowmaking,
        )
        weather_registry = build_weather_factor_registry()
        weather_evaluations = tuple(
            weather_registry.get(factor_id).evaluate(
                weather_context,
                weather_candidate,
            )
            for factor_id in weather_registry.factor_ids
        )
        return (*static_evaluations, *weather_evaluations)


@dataclass(frozen=True, slots=True)
class RefinementCohortReplay:
    """Replay one dynamically eligible candidate cohort with shared bounds."""

    replay_states: tuple[tuple[str, RefinementCandidateReplayState], ...]

    def __post_init__(self) -> None:
        candidate_ids = [candidate_id for candidate_id, _state in self.replay_states]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("refinement cohort replay candidate IDs must be unique")

    def evaluate(
        self,
        intent: SearchIntent,
        eligible_candidate_ids: tuple[str, ...],
    ) -> Mapping[str, tuple[FactorEvaluation, ...]]:
        if not eligible_candidate_ids:
            return {}
        state_by_id = dict(self.replay_states)
        try:
            selected = tuple(
                (candidate_id, state_by_id[candidate_id])
                for candidate_id in eligible_candidate_ids
            )
        except KeyError as error:
            raise KeyError(
                f"unknown refinement cohort candidate ID: {error.args[0]}"
            ) from error
        template = selected[0][1].static_context_template
        if any(
            state.static_context_template != template
            for _candidate_id, state in selected
        ):
            raise ValueError("refinement cohort candidates must share static context")
        numeric_bounds = derive_numeric_bounds(
            candidates=tuple(
                state.static_candidate for _candidate_id, state in selected
            ),
            pass_duration_days=template.pass_duration_days,
            pass_audience=template.pass_audience,
            pass_season_label=template.pass_season_label,
            trust_resolver=template.trust_resolver,
        )
        return {
            candidate_id: state.evaluate(intent, numeric_bounds=numeric_bounds)
            for candidate_id, state in selected
        }


@dataclass(frozen=True, slots=True)
class RefinementBaselineCandidate:
    candidate_id: str
    ski_region_id: str
    constraint_facts: ConstraintCandidateFacts
    evaluations: tuple[RefinementFactorEvaluation, ...]
    unscored: bool
    replay_state: RefinementCandidateReplayState | None = None


@dataclass(frozen=True, slots=True)
class RefinementBaselineSnapshot:
    fingerprint: str
    intent_digest: str
    policy: SearchPolicy
    candidates: tuple[RefinementBaselineCandidate, ...]


@dataclass(frozen=True, slots=True)
class SnapshotPutResult:
    expired_count: int
    evicted_count: int
    capacity_rejected: bool


@dataclass(frozen=True, slots=True)
class SnapshotGetResult:
    outcome: Literal["hit", "miss", "expired", "intent_mismatch"]
    snapshot: RefinementBaselineSnapshot | None
    expiration_already_recorded: bool = False


@dataclass(frozen=True, slots=True)
class _StoredSnapshot:
    snapshot: RefinementBaselineSnapshot
    expires_at: float
    candidate_replay_state_count: int
    weather_row_count: int


@dataclass(frozen=True, slots=True)
class SnapshotStoreUsage:
    entry_count: int
    candidate_replay_state_count: int
    weather_row_count: int


class SnapshotCleanupHandle(Protocol):
    def cancel(self) -> None: ...


class SnapshotCleanupScheduler(Protocol):
    def start(
        self,
        *,
        interval_seconds: float,
        callback: Callable[[], int],
    ) -> SnapshotCleanupHandle: ...


class _ThreadedCleanupHandle:
    def __init__(
        self,
        *,
        interval_seconds: float,
        callback: Callable[[], int],
    ) -> None:
        self._cancelled = Event()
        self._thread = Thread(
            target=self._run,
            args=(interval_seconds, callback),
            name="search-refinement-snapshot-cleanup",
            daemon=True,
        )
        self._thread.start()

    def _run(
        self,
        interval_seconds: float,
        callback: Callable[[], int],
    ) -> None:
        while not self._cancelled.wait(interval_seconds):
            callback()

    def cancel(self) -> None:
        self._cancelled.set()


class ThreadedSnapshotCleanupScheduler:
    """Create one cancellable recurring cleanup worker for a production store."""

    def start(
        self,
        *,
        interval_seconds: float,
        callback: Callable[[], int],
    ) -> SnapshotCleanupHandle:
        return _ThreadedCleanupHandle(
            interval_seconds=interval_seconds,
            callback=callback,
        )


def canonical_search_intent_digest(intent: SearchIntent) -> str:
    payload = intent.model_dump(mode="json", exclude_computed_fields=True)
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class SearchRefinementSnapshotStore:
    def __init__(
        self,
        ttl_seconds: float = 60.0,
        max_entries: int = DEFAULT_MAX_SNAPSHOT_ENTRIES,
        max_candidate_replay_states: int = DEFAULT_MAX_CANDIDATE_REPLAY_STATES,
        max_weather_rows: int = DEFAULT_MAX_WEATHER_ROWS,
        clock: Callable[[], float] = time.monotonic,
        cleanup_scheduler: SnapshotCleanupScheduler | None = None,
        cleanup_interval_seconds: float = DEFAULT_CLEANUP_INTERVAL_SECONDS,
        expiration_observer: Callable[[int], None] | None = None,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        if max_candidate_replay_states <= 0:
            raise ValueError("max_candidate_replay_states must be positive")
        if max_weather_rows <= 0:
            raise ValueError("max_weather_rows must be positive")
        if cleanup_interval_seconds <= 0:
            raise ValueError("cleanup_interval_seconds must be positive")

        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._max_candidate_replay_states = max_candidate_replay_states
        self._max_weather_rows = max_weather_rows
        self._clock = clock
        self._entries: OrderedDict[str, _StoredSnapshot] = OrderedDict()
        self._expired_tombstones: OrderedDict[str, bool] = OrderedDict()
        self._expiration_observer = expiration_observer
        self._lock = RLock()
        self._cleanup_handle = (
            cleanup_scheduler.start(
                interval_seconds=cleanup_interval_seconds,
                callback=self.cleanup_expired,
            )
            if cleanup_scheduler is not None
            else None
        )

    def put(self, snapshot: RefinementBaselineSnapshot) -> SnapshotPutResult:
        with self._lock:
            now = self._clock()
            expired_count = self._purge_expired(now)
            candidate_count = len(snapshot.candidates)
            weather_row_count = _snapshot_weather_row_count(snapshot)
            self._entries.pop(snapshot.fingerprint, None)
            self._expired_tombstones.pop(snapshot.fingerprint, None)
            if (
                candidate_count > self._max_candidate_replay_states
                or weather_row_count > self._max_weather_rows
            ):
                return SnapshotPutResult(
                    expired_count=expired_count,
                    evicted_count=0,
                    capacity_rejected=True,
                )
            self._entries[snapshot.fingerprint] = _StoredSnapshot(
                snapshot=snapshot,
                expires_at=now + self._ttl_seconds,
                candidate_replay_state_count=candidate_count,
                weather_row_count=weather_row_count,
            )

            evicted_count = 0
            while self._over_capacity():
                self._entries.popitem(last=False)
                evicted_count += 1

            return SnapshotPutResult(
                expired_count=expired_count,
                evicted_count=evicted_count,
                capacity_rejected=False,
            )

    def get(self, fingerprint: str, intent_digest: str) -> SnapshotGetResult:
        with self._lock:
            now = self._clock()
            stored = self._entries.get(fingerprint)
            if stored is not None and now >= stored.expires_at:
                self._purge_expired(now)
                recorded = self._expired_tombstones.pop(fingerprint, False)
                return SnapshotGetResult(
                    outcome="expired",
                    snapshot=None,
                    expiration_already_recorded=recorded,
                )
            self._purge_expired(now)
            stored = self._entries.get(fingerprint)
            if stored is None:
                if fingerprint in self._expired_tombstones:
                    recorded = self._expired_tombstones.pop(fingerprint)
                    return SnapshotGetResult(
                        outcome="expired",
                        snapshot=None,
                        expiration_already_recorded=recorded,
                    )
                return SnapshotGetResult(outcome="miss", snapshot=None)

            if stored.snapshot.intent_digest != intent_digest:
                return SnapshotGetResult(outcome="intent_mismatch", snapshot=None)

            self._entries.move_to_end(fingerprint)
            return SnapshotGetResult(outcome="hit", snapshot=stored.snapshot)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._expired_tombstones.clear()

    def cleanup_expired(self) -> int:
        with self._lock:
            return self._purge_expired(self._clock())

    def usage(self) -> SnapshotStoreUsage:
        with self._lock:
            self._purge_expired(self._clock())
            return SnapshotStoreUsage(
                entry_count=len(self._entries),
                candidate_replay_state_count=sum(
                    stored.candidate_replay_state_count
                    for stored in self._entries.values()
                ),
                weather_row_count=sum(
                    stored.weather_row_count for stored in self._entries.values()
                ),
            )

    def close(self) -> None:
        handle = self._cleanup_handle
        if handle is not None:
            handle.cancel()
            self._cleanup_handle = None

    def __len__(self) -> int:
        return self.usage().entry_count

    def _over_capacity(self) -> bool:
        return (
            len(self._entries) > self._max_entries
            or sum(
                stored.candidate_replay_state_count for stored in self._entries.values()
            )
            > self._max_candidate_replay_states
            or sum(stored.weather_row_count for stored in self._entries.values())
            > self._max_weather_rows
        )

    def _purge_expired(self, now: float) -> int:
        expired = [
            fingerprint
            for fingerprint, stored in self._entries.items()
            if now >= stored.expires_at
        ]
        for fingerprint in expired:
            del self._entries[fingerprint]
        expiration_recorded = False
        if expired and self._expiration_observer is not None:
            try:
                self._expiration_observer(len(expired))
                expiration_recorded = True
            except Exception:
                expiration_recorded = False
        for fingerprint in expired:
            self._expired_tombstones[fingerprint] = expiration_recorded
            self._expired_tombstones.move_to_end(fingerprint)
        while len(self._expired_tombstones) > self._max_entries:
            self._expired_tombstones.popitem(last=False)
        return len(expired)


def _snapshot_weather_row_count(snapshot: RefinementBaselineSnapshot) -> int:
    retained_row_ids: set[int] = set()
    for candidate in snapshot.candidates:
        replay_state = candidate.replay_state
        if replay_state is None:
            continue
        weather_candidate = replay_state.weather_candidate
        retained_row_ids.update(id(row) for row in weather_candidate.climatology_rows)
        retained_row_ids.update(id(row) for row in weather_candidate.forecast_rows)
    return len(retained_row_ids)
