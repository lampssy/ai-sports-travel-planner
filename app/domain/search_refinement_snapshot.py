from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from threading import RLock
from typing import Literal

from app.domain.search_constraints import ConstraintCandidateFacts
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_factors.static import (
    CatalogEvidenceResolver,
    NumericBounds,
    StaticEvaluationContext,
    StaticFactorCandidate,
    build_static_factor_registry,
)
from app.domain.search_factors.weather import (
    WeatherEvaluationContext,
    WeatherFactorCandidate,
    build_weather_factor_registry,
)
from app.domain.search_policy import SearchPolicy
from app.domain.search_v4_models import SearchIntent


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

    def materialize(self, intent: SearchIntent) -> StaticEvaluationContext:
        return StaticEvaluationContext(
            intent=intent,
            policy=self.policy,
            trust_resolver=self.trust_resolver,
            numeric_bounds=self.numeric_bounds,
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

    def evaluate(self, intent: SearchIntent) -> tuple[FactorEvaluation, ...]:
        static_context = self.static_context_template.materialize(intent)
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


@dataclass(frozen=True, slots=True)
class SnapshotGetResult:
    outcome: Literal["hit", "miss", "expired", "intent_mismatch"]
    snapshot: RefinementBaselineSnapshot | None


@dataclass(frozen=True, slots=True)
class _StoredSnapshot:
    snapshot: RefinementBaselineSnapshot
    expires_at: float


def canonical_search_intent_digest(intent: SearchIntent) -> str:
    payload = intent.model_dump(mode="json", exclude_computed_fields=True)
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class SearchRefinementSnapshotStore:
    def __init__(
        self,
        ttl_seconds: float = 60.0,
        max_entries: int = 64,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")

        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, _StoredSnapshot] = OrderedDict()
        self._lock = RLock()

    def put(self, snapshot: RefinementBaselineSnapshot) -> SnapshotPutResult:
        with self._lock:
            now = self._clock()
            expired_count = self._purge_expired(now)
            self._entries.pop(snapshot.fingerprint, None)
            self._entries[snapshot.fingerprint] = _StoredSnapshot(
                snapshot=snapshot,
                expires_at=now + self._ttl_seconds,
            )

            evicted_count = 0
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
                evicted_count += 1

            return SnapshotPutResult(
                expired_count=expired_count,
                evicted_count=evicted_count,
            )

    def get(self, fingerprint: str, intent_digest: str) -> SnapshotGetResult:
        with self._lock:
            stored = self._entries.get(fingerprint)
            if stored is None:
                return SnapshotGetResult(outcome="miss", snapshot=None)

            if self._clock() >= stored.expires_at:
                del self._entries[fingerprint]
                return SnapshotGetResult(outcome="expired", snapshot=None)

            if stored.snapshot.intent_digest != intent_digest:
                return SnapshotGetResult(outcome="intent_mismatch", snapshot=None)

            self._entries.move_to_end(fingerprint)
            return SnapshotGetResult(outcome="hit", snapshot=stored.snapshot)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def _purge_expired(self, now: float) -> int:
        expired = [
            fingerprint
            for fingerprint, stored in self._entries.items()
            if now >= stored.expires_at
        ]
        for fingerprint in expired:
            del self._entries[fingerprint]
        return len(expired)
