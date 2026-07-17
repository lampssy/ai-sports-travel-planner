from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal, Protocol, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.ai.llm_client import LLMClient
from app.ai.search_refinement import (
    RefinementGenerationResult,
    generate_refinement_proposals,
)
from app.data.audit_search_factor_readiness import DEFAULT_TRUST_MANIFEST_PATH
from app.data.catalog_repository import CatalogRepository
from app.data.repositories import get_snow_climatology_repository
from app.data.weather_forecast_repository import WeatherForecastRepository
from app.domain.catalog import (
    CatalogSnapshot,
    LiftPassProduct,
    SkiArea,
    SkiAreaAccess,
    SkiRegion,
    StayBase,
    StayDestination,
    TerrainDomain,
)
from app.domain.catalog_graph import CatalogGraph
from app.domain.catalog_trust import CatalogTrustManifest, Status
from app.domain.models import (
    PlanningEvidenceProfile,
    SnowClimatologyDaily,
    TravelEffort,
)
from app.domain.ranking import quality_score
from app.domain.search_constraints import (
    CandidateFeatureFact,
    CandidateLocation,
    CandidateLodgingEstimate,
    CandidatePassPrice,
    CandidateSeasonEvidence,
    CandidateTravelEvidence,
    ConstraintCandidateFacts,
    ConstraintDecision,
    ConstraintIssue,
    evaluate_search_constraints,
)
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_factors.static import (
    ManifestCatalogEvidenceResolver,
    StaticEvaluationContext,
    StaticFactorCandidate,
    build_static_factor_registry,
    derive_numeric_bounds,
    select_accessible_terrain_source,
    select_matching_pass_price,
)
from app.domain.search_factors.weather import (
    WeatherEvaluationContext,
    WeatherFactorCandidate,
    build_weather_factor_registry,
)
from app.domain.search_intent_policy import (
    validate_search_intent,
)
from app.domain.search_policy import SearchPolicy, load_search_policy
from app.domain.search_ranking import (
    FactorScoreBreakdown,
    GroupScoreBreakdown,
    RankedScore,
    UnscoredAllocation,
    score_factor_evaluations,
)
from app.domain.search_refinement import (
    RefinementCandidateState,
    RefinementOption,
    RefinementVariantOutcome,
    ValidatedRefinementProposal,
    build_deterministic_refinement_fallback,
)
from app.domain.search_refinement_snapshot import (
    RefinementBaselineCandidate,
    RefinementBaselineSnapshot,
    RefinementFactorEvaluation,
    SearchRefinementSnapshotStore,
    canonical_search_intent_digest,
)
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    GroupPriorityPatch,
    SearchIdentifier,
    SearchIntent,
    SearchObjective,
)
from app.domain.search_weather_evidence import (
    SearchWeatherEvidenceAvailableResponse,
    SearchWeatherEvidenceResponse,
    SearchWeatherEvidenceUnavailableResponse,
    build_search_weather_evidence,
    select_weather_evidence_forecast_rows,
)
from app.domain.travel import assess_deterministic_travel_effort
from app.domain.weather_forecast import (
    ServedWeatherForecastDaily,
    WeatherForecastRun,
)
from app.observability.search import (
    record_search_refinement_completed,
    record_search_refinement_snapshot_outcome,
    record_search_v4_completed,
    search_phase,
)

_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")
_FORECAST_CONSISTENCY_DELAY = timedelta(minutes=10)
_CURRENCY_PREFIX = re.compile(r"^\s*([A-Za-z]{3})\b")
SEARCH_REFINEMENT_REQUEST_BUDGET_SECONDS = 5.0
_EMPTY_BASELINE_FINGERPRINT = "0" * 64
BaselineFingerprint = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    ),
]
default_refinement_snapshot_store = SearchRefinementSnapshotStore()


class _ClimatologyRepository(Protocol):
    def list_daily_rows_for_ski_areas_window(
        self,
        ski_area_ids: tuple[str, ...],
        **kwargs: object,
    ) -> Mapping[tuple[str, str, str], Sequence[SnowClimatologyDaily]]: ...


class _ForecastRepository(Protocol):
    def list_latest_daily_rows(
        self,
        *,
        ski_area_ids: Sequence[str],
        start_date: date,
        end_date: date,
        source_keys: Sequence[str],
        elevation_band: str = "mid",
    ) -> tuple[ServedWeatherForecastDaily, ...]: ...


class _SearchV4Model(BaseModel):
    model_config = _MODEL_CONFIG


class SearchV4AccessSummary(_SearchV4Model):
    ski_area_access_id: str
    access_mode: str
    lift_distance: str
    nearest_lift_name: str | None
    distance_m: int | None
    duration_minutes: int | None
    is_direct: bool
    relationship_trust_status: Status
    access_mode_distance_trust_status: Status


class SearchV4PassPriceSummary(_SearchV4Model):
    duration_days: int
    audience: str
    amount: float | None
    amount_min: float | None
    amount_max: float | None
    currency: str
    price_kind: str
    season_label: str | None


class SearchV4TerrainEvidence(_SearchV4Model):
    trust_status: Status
    scope: Literal["pass", "terrain_domain", "ski_area"]
    source_entity_id: str
    field_group: Literal[
        "pass_accessible_terrain",
        "aggregate_terrain",
        "terrain_metrics",
    ]


class SearchV4PassSummary(_SearchV4Model):
    lift_pass_product_id: str
    name: str
    validity_scope: str
    covered_ski_area_ids: tuple[str, ...]
    accessible_piste_km: float | None
    accessible_piste_km_evidence: SearchV4TerrainEvidence | None
    price: SearchV4PassPriceSummary | None


class SearchV4Configuration(_SearchV4Model):
    candidate_id: str
    ski_region_id: str
    ski_region_name: str
    stay_destination_id: str
    stay_destination_name: str
    stay_base_id: str
    stay_base_name: str
    ski_area_id: str
    ski_area_name: str
    evidence_profile: PlanningEvidenceProfile
    access: SearchV4AccessSummary
    selected_pass: SearchV4PassSummary
    lodging_estimate: CandidateLodgingEstimate | None
    ranking_status: Literal["ranked", "unscored"]
    fit_score: float | None = Field(default=None, ge=0, le=100)
    groups: tuple[GroupScoreBreakdown, ...] = ()
    factors: tuple[FactorScoreBreakdown, ...] = ()
    constraint_warnings: tuple[ConstraintIssue, ...] = ()


class SearchV4RecommendationGroup(_SearchV4Model):
    ski_region_id: str
    ski_region_name: str
    rank: int = Field(gt=0)
    fit_score: float | None = Field(default=None, ge=0, le=100)
    top_configuration: SearchV4Configuration
    alternative_configurations: tuple[SearchV4Configuration, ...] = ()


class SearchV4RefinementRankChange(_SearchV4Model):
    ski_region_id: str
    previous_rank: int | None = Field(default=None, gt=0)
    preview_rank: int | None = Field(default=None, gt=0)


class SearchV4RefinementPreview(_SearchV4Model):
    top_rank_changes: tuple[SearchV4RefinementRankChange, ...] = Field(max_length=3)
    eligible_candidate_count_delta: int


class SearchV4RefinementOption(_SearchV4Model):
    label: str
    description: str
    intent_changed: bool
    group_priority_patches: tuple[GroupPriorityPatch, ...] = ()
    factor_preference_patches: tuple[FactorPreferencePatch, ...] = ()
    objective_patches: tuple[SearchObjective, ...] = ()
    preview: SearchV4RefinementPreview | None = None


class SearchV4RefinementProposal(_SearchV4Model):
    question_id: str
    question: str
    reason: str
    options: tuple[SearchV4RefinementOption, ...]


class SearchV4Response(_SearchV4Model):
    search_model_version: Literal["search-v4"]
    ranking_policy_version: str
    baseline_fingerprint: BaselineFingerprint = _EMPTY_BASELINE_FINGERPRINT
    ranking_status: Literal["ranked", "unscored"]
    unscored_reason: str | None = None
    applied_intent: SearchIntent
    eligible_candidate_count: int = Field(ge=0)
    excluded_candidate_count: int = Field(ge=0)
    results: tuple[SearchV4RecommendationGroup, ...]
    refinements: tuple[SearchV4RefinementProposal, ...] = ()


class SearchV4Request(_SearchV4Model):
    intent: SearchIntent
    brief: str | None = Field(default=None, max_length=2_000)
    generate_refinements: bool = True
    already_answered_question_ids: tuple[SearchIdentifier, ...] = Field(
        default=(), max_length=50
    )

    @model_validator(mode="after")
    def require_unique_answered_question_ids(self) -> Self:
        if len(self.already_answered_question_ids) != len(
            set(self.already_answered_question_ids)
        ):
            raise ValueError("answered refinement question IDs must be unique")
        return self


class SearchV4RefinementRequest(_SearchV4Model):
    intent: SearchIntent
    brief: str | None = Field(default=None, max_length=2_000)
    baseline_fingerprint: BaselineFingerprint
    already_answered_question_ids: tuple[SearchIdentifier, ...] = Field(
        default=(), max_length=50
    )

    @model_validator(mode="after")
    def require_unique_answered_question_ids(self) -> Self:
        if len(self.already_answered_question_ids) != len(
            set(self.already_answered_question_ids)
        ):
            raise ValueError("answered refinement question IDs must be unique")
        return self


class SearchV4RefinementResponse(_SearchV4Model):
    search_model_version: Literal["search-v4"]
    ranking_policy_version: str
    baseline_fingerprint: BaselineFingerprint = _EMPTY_BASELINE_FINGERPRINT
    baseline_status: Literal["current", "stale", "unverified"] = "current"
    refinement_status: Literal[
        "questions_available",
        "not_needed",
        "temporarily_unavailable",
    ]
    fallback_used: bool = False
    refinements: tuple[SearchV4RefinementProposal, ...] = ()

    @model_validator(mode="after")
    def require_status_consistent_queue(self) -> Self:
        if self.refinement_status == "questions_available" and not self.refinements:
            raise ValueError("questions_available requires refinements")
        if self.refinement_status != "questions_available" and self.refinements:
            raise ValueError("non-question statuses must not include refinements")
        if self.fallback_used and self.refinement_status != "questions_available":
            raise ValueError("fallback_used requires questions_available")
        if self.baseline_status != "current" and self.refinements:
            raise ValueError("non-current baselines must not include refinements")
        if (
            self.baseline_status != "current"
            and self.refinement_status != "temporarily_unavailable"
        ):
            raise ValueError("non-current baselines must be temporarily_unavailable")
        return self


@dataclass(frozen=True)
class V4CandidateRecord:
    candidate_id: str
    region: SkiRegion
    destination: StayDestination
    stay_base: StayBase
    ski_area: SkiArea
    access: SkiAreaAccess
    selected_pass: LiftPassProduct
    terrain_domains: tuple[TerrainDomain, ...]
    pass_covered_ski_area_ids: tuple[str, ...]
    constraint_facts: ConstraintCandidateFacts
    travel_effort: TravelEffort | None


@dataclass(frozen=True)
class _EvaluatedCandidate:
    record: V4CandidateRecord
    constraint_decision: ConstraintDecision
    evaluations: tuple[FactorEvaluation, ...]
    ranking: RankedScore | UnscoredAllocation


@dataclass(frozen=True)
class _FactorEvaluatedCandidate:
    record: V4CandidateRecord
    constraint_decision: ConstraintDecision
    evaluations: tuple[FactorEvaluation, ...]


@dataclass(frozen=True)
class _EvaluatedSearch:
    intent: SearchIntent
    policy: SearchPolicy
    snapshot: CatalogSnapshot
    manifest: CatalogTrustManifest
    all_records: tuple[V4CandidateRecord, ...]
    ordered: tuple[_EvaluatedCandidate, ...]
    excluded_count: int
    ranking_status: Literal["ranked", "unscored"]
    unscored_reason: str | None
    duration_days: int
    audience: str
    season_label: str | None


class UnknownSearchWeatherAreaError(ValueError):
    def __init__(self, ski_area_id: str) -> None:
        super().__init__(f"unknown ski area ID: {ski_area_id}")
        self.ski_area_id = ski_area_id


def forecast_run_is_fresh(
    run: WeatherForecastRun,
    reference_time: datetime,
) -> bool:
    """Return whether a latest head remains inside its provider issue interval."""

    update_interval = run.provider_metadata.get("update_interval_seconds")
    if (
        not isinstance(update_interval, (int, float))
        or isinstance(update_interval, bool)
        or update_interval <= 0
    ):
        return False
    if reference_time.tzinfo is None or reference_time.utcoffset() is None:
        raise ValueError("reference_time must be timezone-aware")
    return reference_time <= forecast_run_valid_until(run)


def forecast_run_valid_until(run: WeatherForecastRun) -> datetime:
    update_interval = run.provider_metadata.get("update_interval_seconds")
    if (
        not isinstance(update_interval, (int, float))
        or isinstance(update_interval, bool)
        or update_interval <= 0
    ):
        raise ValueError("forecast run has no positive update interval")
    return (
        run.provider_availability_time
        + timedelta(seconds=float(update_interval))
        + _FORECAST_CONSISTENCY_DELAY
    )


def get_search_weather_evidence(
    *,
    intent: SearchIntent,
    ski_area_id: SearchIdentifier,
    catalog_snapshot: CatalogSnapshot | None = None,
    trust_manifest: CatalogTrustManifest | None = None,
    climatology_repository: _ClimatologyRepository | None = None,
    forecast_repository: _ForecastRepository | None = None,
    policy: SearchPolicy | None = None,
    reference_time: datetime | None = None,
) -> SearchWeatherEvidenceResponse:
    selected_policy = policy or load_search_policy()
    validate_search_intent(intent, selected_policy)
    snapshot = catalog_snapshot or CatalogRepository().get_snapshot()
    manifest = trust_manifest or _load_trust_manifest(DEFAULT_TRUST_MANIFEST_PATH)
    manifest.validate_against_catalog(snapshot)
    if ski_area_id not in {area.ski_area_id for area in snapshot.ski_areas}:
        raise UnknownSearchWeatherAreaError(ski_area_id)

    evaluated_at = reference_time or datetime.now(UTC)
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("reference_time must be timezone-aware")
    cache_valid_until = evaluated_at + timedelta(minutes=5)
    window = intent.constraints.travel_window
    if window is None:
        return SearchWeatherEvidenceUnavailableResponse(
            weather_evidence_version="search-weather-evidence-v1",
            ski_area_id=ski_area_id,
            evaluated_at=evaluated_at.isoformat(),
            cache_valid_until=cache_valid_until.isoformat(),
            unavailable_reason="travel_window_missing",
            limitations=("A travel month or exact travel dates are required.",),
        )

    climate_by_area, forecast_by_area, stale_run_ids = _load_weather_evidence(
        intent=intent,
        area_ids=(ski_area_id,),
        policy=selected_policy,
        climatology_repository=(
            climatology_repository or get_snow_climatology_repository()
        ),
        forecast_repository=forecast_repository or WeatherForecastRepository(),
        reference_time=evaluated_at,
    )
    context = WeatherEvaluationContext(
        intent=intent,
        policy=selected_policy,
        stale_run_ids=stale_run_ids,
    )
    candidate = WeatherFactorCandidate(
        ski_area_id=ski_area_id,
        climatology_rows=climate_by_area.get(ski_area_id, ()),
        forecast_rows=forecast_by_area.get(ski_area_id, ()),
    )
    accepted_forecast_rows = select_weather_evidence_forecast_rows(
        context,
        candidate,
        window,
    )
    evidence = build_search_weather_evidence(
        context=context,
        candidate=candidate,
        accepted_forecast_rows=accepted_forecast_rows,
    )
    if evidence is None:
        return SearchWeatherEvidenceUnavailableResponse(
            weather_evidence_version="search-weather-evidence-v1",
            ski_area_id=ski_area_id,
            evaluated_at=evaluated_at.isoformat(),
            cache_valid_until=cache_valid_until.isoformat(),
            unavailable_reason="historical_evidence_unavailable",
            limitations=(
                "No trustworthy mid-mountain historical evidence is available.",
            ),
        )

    if evidence.forecast is not None:
        if accepted_forecast_rows:
            cache_valid_until = min(
                forecast_run_valid_until(row.run)
                for _valid_date, row, _share in accepted_forecast_rows
            )
    return SearchWeatherEvidenceAvailableResponse(
        weather_evidence_version="search-weather-evidence-v1",
        ski_area_id=ski_area_id,
        evaluated_at=evaluated_at.isoformat(),
        cache_valid_until=cache_valid_until.isoformat(),
        evidence=evidence,
    )


def generate_v4_candidate_records(
    *,
    graph: CatalogGraph,
    intent: SearchIntent,
    trust_manifest: CatalogTrustManifest,
) -> tuple[V4CandidateRecord, ...]:
    """Expand every modeled access edge across every applicable pass product."""

    records: list[V4CandidateRecord] = []
    domains_by_area: dict[str, list[TerrainDomain]] = defaultdict(list)
    for domain in graph.snapshot.terrain_domains:
        for ski_area_id in domain.ski_area_ids:
            domains_by_area[ski_area_id].append(domain)

    for base in sorted(graph.snapshot.stay_bases, key=lambda item: item.stay_base_id):
        destination = graph.destinations_by_id[base.stay_destination_id]
        region = graph.regions_by_id[destination.trip_market_region_id]
        for access in graph.accesses_by_base_id.get(base.stay_base_id, ()):
            area = graph.areas_by_id[access.ski_area_id]
            passes = graph.passes_by_destination_area.get(
                (destination.stay_destination_id, area.ski_area_id),
                (),
            )
            for product in passes:
                candidate_id = (
                    f"{access.ski_area_access_id}--{product.lift_pass_product_id}"
                )
                travel_effort = _travel_effort(intent, destination)
                records.append(
                    V4CandidateRecord(
                        candidate_id=candidate_id,
                        region=region,
                        destination=destination,
                        stay_base=base,
                        ski_area=area,
                        access=access,
                        selected_pass=product,
                        terrain_domains=_candidate_terrain_domains(
                            area=area,
                            product=product,
                            domains_by_area=domains_by_area,
                            domains_by_id=graph.domains_by_id,
                        ),
                        pass_covered_ski_area_ids=_pass_covered_ski_area_ids(
                            product,
                            graph.domains_by_id,
                        ),
                        constraint_facts=_constraint_facts(
                            candidate_id=candidate_id,
                            graph=graph,
                            destination=destination,
                            base=base,
                            area=area,
                            product=product,
                            travel_effort=travel_effort,
                            manifest=trust_manifest,
                        ),
                        travel_effort=travel_effort,
                    )
                )
    return tuple(records)


def _pass_covered_ski_area_ids(
    product: LiftPassProduct,
    domains_by_id: Mapping[str, TerrainDomain],
) -> tuple[str, ...]:
    covered = set(product.valid_ski_area_ids)
    for domain_id in product.terrain_domain_ids:
        covered.update(domains_by_id[domain_id].ski_area_ids)
    return tuple(sorted(covered))


def _candidate_terrain_domains(
    *,
    area: SkiArea,
    product: LiftPassProduct,
    domains_by_area: Mapping[str, Sequence[TerrainDomain]],
    domains_by_id: Mapping[str, TerrainDomain],
) -> tuple[TerrainDomain, ...]:
    domains = {
        domain.terrain_domain_id: domain
        for domain in domains_by_area.get(area.ski_area_id, ())
    }
    for domain_id in product.terrain_domain_ids:
        domains[domain_id] = domains_by_id[domain_id]
    return tuple(domains[domain_id] for domain_id in sorted(domains))


def search_trip_configurations(
    *,
    intent: SearchIntent,
    catalog_snapshot: CatalogSnapshot | None = None,
    trust_manifest: CatalogTrustManifest | None = None,
    climatology_repository: _ClimatologyRepository | None = None,
    forecast_repository: _ForecastRepository | None = None,
    policy: SearchPolicy | None = None,
    reference_time: datetime | None = None,
    include_refinements: bool | None = None,
    refinement_snapshot_store: SearchRefinementSnapshotStore | None = None,
) -> SearchV4Response:
    """Rank Search V4 candidates without refinement generation."""

    started = time.perf_counter()
    evaluated = _evaluate_search(
        intent=intent,
        catalog_snapshot=catalog_snapshot,
        trust_manifest=trust_manifest,
        climatology_repository=climatology_repository,
        forecast_repository=forecast_repository,
        policy=policy,
        reference_time=reference_time,
    )
    results = _group_results(
        evaluated.ordered,
        evaluated.duration_days,
        evaluated.audience,
        evaluated.season_label,
        evaluated.manifest,
    )
    baseline_fingerprint = _baseline_fingerprint(evaluated)
    store = (
        refinement_snapshot_store
        if refinement_snapshot_store is not None
        else default_refinement_snapshot_store
    )
    mutation = store.put(
        RefinementBaselineSnapshot(
            fingerprint=baseline_fingerprint,
            intent_digest=canonical_search_intent_digest(evaluated.intent),
            policy=evaluated.policy,
            candidates=_refinement_baseline_candidates(evaluated.ordered),
        )
    )
    if mutation.expired_count:
        record_search_refinement_snapshot_outcome(
            "expired",
            count=mutation.expired_count,
        )
    if mutation.evicted_count:
        record_search_refinement_snapshot_outcome(
            "evicted",
            count=mutation.evicted_count,
        )
    response = SearchV4Response(
        search_model_version=evaluated.policy.search_model_version,
        ranking_policy_version=evaluated.policy.ranking_policy_version,
        baseline_fingerprint=baseline_fingerprint,
        ranking_status=evaluated.ranking_status,
        unscored_reason=evaluated.unscored_reason,
        applied_intent=intent,
        eligible_candidate_count=len(evaluated.ordered),
        excluded_candidate_count=evaluated.excluded_count,
        results=results,
        refinements=(),
    )
    record_search_v4_completed(
        intent=intent,
        ranking_policy_version=evaluated.policy.ranking_policy_version,
        ranking_status=evaluated.ranking_status,
        candidate_count=len(evaluated.all_records),
        eligible_candidate_count=len(evaluated.ordered),
        result_group_count=len(results),
        duration_seconds=time.perf_counter() - started,
    )
    return response


def _evaluate_search(
    *,
    intent: SearchIntent,
    catalog_snapshot: CatalogSnapshot | None = None,
    trust_manifest: CatalogTrustManifest | None = None,
    climatology_repository: _ClimatologyRepository | None = None,
    forecast_repository: _ForecastRepository | None = None,
    policy: SearchPolicy | None = None,
    reference_time: datetime | None = None,
) -> _EvaluatedSearch:
    """Build the bounded deterministic state shared by ranking and refinement."""

    selected_policy = policy or load_search_policy()
    validate_search_intent(intent, selected_policy)
    snapshot = catalog_snapshot or CatalogRepository().get_snapshot()
    manifest = trust_manifest or _load_trust_manifest(DEFAULT_TRUST_MANIFEST_PATH)
    manifest.validate_against_catalog(snapshot)
    graph = CatalogGraph.from_snapshot(snapshot)
    all_records = generate_v4_candidate_records(
        graph=graph,
        intent=intent,
        trust_manifest=manifest,
    )
    decisions = {
        record.candidate_id: evaluate_search_constraints(
            candidate=record.constraint_facts,
            intent=intent,
        )
        for record in all_records
    }
    eligible_records = tuple(
        record for record in all_records if decisions[record.candidate_id].eligible
    )
    excluded_count = len(all_records) - len(eligible_records)
    if not eligible_records:
        return _EvaluatedSearch(
            intent=intent,
            policy=selected_policy,
            snapshot=snapshot,
            manifest=manifest,
            all_records=all_records,
            ordered=(),
            excluded_count=excluded_count,
            ranking_status="ranked",
            unscored_reason=None,
            duration_days=1,
            audience="adult",
            season_label=None,
        )

    duration_days, audience, season_label = _pass_slice(intent)
    static_candidates = tuple(_static_candidate(record) for record in eligible_records)
    trust_resolver = ManifestCatalogEvidenceResolver(manifest)
    static_context = StaticEvaluationContext(
        intent=intent,
        policy=selected_policy,
        trust_resolver=trust_resolver,
        numeric_bounds=derive_numeric_bounds(
            candidates=static_candidates,
            pass_duration_days=duration_days,
            pass_audience=audience,
            pass_season_label=season_label,
            trust_resolver=trust_resolver,
        ),
        pass_duration_days=duration_days,
        pass_audience=audience,
        pass_season_label=season_label,
    )
    static_registry = build_static_factor_registry()
    with search_phase(phase="static_factor_evaluation", intent=intent):
        static_by_candidate = {
            record.candidate_id: tuple(
                static_registry.get(factor_id).evaluate(
                    static_context,
                    static_candidate,
                )
                for factor_id in static_registry.factor_ids
            )
            for record, static_candidate in zip(
                eligible_records,
                static_candidates,
                strict=True,
            )
        }

    area_ids = tuple(
        sorted({record.ski_area.ski_area_id for record in eligible_records})
    )
    search_reference_time = reference_time or datetime.now(UTC)
    if (
        search_reference_time.tzinfo is None
        or search_reference_time.utcoffset() is None
    ):
        raise ValueError("reference_time must be timezone-aware")
    with search_phase(phase="weather_preload", intent=intent):
        climate_by_area, forecast_by_area, stale_run_ids = _load_weather_evidence(
            intent=intent,
            area_ids=area_ids,
            policy=selected_policy,
            climatology_repository=(
                climatology_repository or get_snow_climatology_repository()
            ),
            forecast_repository=forecast_repository or WeatherForecastRepository(),
            reference_time=search_reference_time,
        )
    weather_context = WeatherEvaluationContext(
        intent=intent,
        policy=selected_policy,
        stale_run_ids=stale_run_ids,
    )
    weather_registry = build_weather_factor_registry()
    with search_phase(phase="weather_factor_evaluation", intent=intent):
        factor_evaluated: list[_FactorEvaluatedCandidate] = []
        for record in eligible_records:
            static_evaluations = static_by_candidate[record.candidate_id]
            snowmaking = next(
                (
                    item
                    for item in static_evaluations
                    if item.factor_id == "snowmaking_availability"
                ),
                None,
            )
            weather_candidate = WeatherFactorCandidate(
                ski_area_id=record.ski_area.ski_area_id,
                climatology_rows=climate_by_area.get(
                    record.ski_area.ski_area_id,
                    (),
                ),
                forecast_rows=forecast_by_area.get(
                    record.ski_area.ski_area_id,
                    (),
                ),
                snowmaking_evaluation=snowmaking,
            )
            weather_evaluations = tuple(
                weather_registry.get(factor_id).evaluate(
                    weather_context,
                    weather_candidate,
                )
                for factor_id in weather_registry.factor_ids
            )
            evaluations = (*static_evaluations, *weather_evaluations)
            factor_evaluated.append(
                _FactorEvaluatedCandidate(
                    record=record,
                    constraint_decision=decisions[record.candidate_id],
                    evaluations=evaluations,
                )
            )
    with search_phase(phase="ranking", intent=intent):
        evaluated = tuple(
            _EvaluatedCandidate(
                record=item.record,
                constraint_decision=item.constraint_decision,
                evaluations=item.evaluations,
                ranking=score_factor_evaluations(
                    evaluations=item.evaluations,
                    intent=intent,
                    policy=selected_policy,
                ),
            )
            for item in factor_evaluated
        )

    ordered = tuple(sorted(evaluated, key=_evaluated_sort_key))
    ranking_status: Literal["ranked", "unscored"] = (
        "ranked"
        if any(isinstance(item.ranking, RankedScore) for item in ordered)
        else "unscored"
    )
    unscored_reason = (
        next(
            (
                item.ranking.reason
                for item in ordered
                if isinstance(item.ranking, UnscoredAllocation)
            ),
            None,
        )
        if ranking_status == "unscored"
        else None
    )
    return _EvaluatedSearch(
        intent=intent,
        policy=selected_policy,
        snapshot=snapshot,
        manifest=manifest,
        all_records=all_records,
        ordered=ordered,
        excluded_count=excluded_count,
        ranking_status=ranking_status,
        unscored_reason=unscored_reason,
        duration_days=duration_days,
        audience=audience,
        season_label=season_label,
    )


def get_search_refinements(
    *,
    intent: SearchIntent,
    brief: str | None,
    baseline_fingerprint: str,
    already_answered_question_ids: frozenset[str],
    llm_client_factory: Callable[[float], LLMClient],
    policy: SearchPolicy | None = None,
    refinement_snapshot_store: SearchRefinementSnapshotStore | None = None,
    clock: Callable[[], float] = time.monotonic,
    request_started_at: float | None = None,
) -> SearchV4RefinementResponse:
    """Generate refinement state from the exact evaluated ranking baseline."""

    started = request_started_at if request_started_at is not None else clock()
    store = (
        refinement_snapshot_store
        if refinement_snapshot_store is not None
        else default_refinement_snapshot_store
    )
    lookup = store.get(
        baseline_fingerprint,
        canonical_search_intent_digest(intent),
    )
    record_search_refinement_snapshot_outcome(lookup.outcome)
    baseline = lookup.snapshot
    if baseline is None:
        selected_policy = policy or load_search_policy()
        validate_search_intent(intent, selected_policy)
        baseline_status: Literal["stale", "unverified"] = (
            "stale" if lookup.outcome == "intent_mismatch" else "unverified"
        )
        return _refinement_response(
            policy=selected_policy,
            status="temporarily_unavailable",
            baseline_fingerprint=baseline_fingerprint,
            baseline_status=baseline_status,
            fallback_used=False,
            refinements=(),
            reason=f"snapshot_{lookup.outcome}",
            intent=intent,
            duration_seconds=clock() - started,
        )
    selected_policy = baseline.policy
    validate_search_intent(intent, selected_policy)
    if not baseline.candidates:
        return _refinement_response(
            policy=selected_policy,
            status="not_needed",
            baseline_fingerprint=baseline.fingerprint,
            baseline_status="current",
            fallback_used=False,
            refinements=(),
            reason="zero_results",
            intent=intent,
            duration_seconds=clock() - started,
        )
    states = _refinement_states(baseline.candidates)
    remaining_seconds = SEARCH_REFINEMENT_REQUEST_BUDGET_SECONDS - (clock() - started)
    if remaining_seconds > 0:
        with search_phase(phase="refinement", intent=intent):
            generated = generate_refinement_proposals(
                brief=brief,
                intent=intent,
                candidates=states,
                policy=selected_policy,
                client=llm_client_factory(remaining_seconds),
                already_answered_question_ids=already_answered_question_ids,
            )
    else:
        generated = RefinementGenerationResult(
            outcome="provider_unavailable",
            proposals=(),
        )

    fallback = (
        build_deterministic_refinement_fallback(
            intent=intent,
            candidates=states,
            policy=selected_policy,
            already_answered_question_ids=already_answered_question_ids,
        )
        if not generated.proposals
        and clock() - started < SEARCH_REFINEMENT_REQUEST_BUDGET_SECONDS
        else None
    )
    validated = (
        generated.proposals
        if generated.proposals
        else ((fallback,) if fallback else ())
    )
    fallback_used = fallback is not None
    status: Literal["questions_available", "not_needed", "temporarily_unavailable"] = (
        "questions_available"
        if validated
        else (
            "temporarily_unavailable"
            if generated.outcome == "provider_unavailable"
            else "not_needed"
        )
    )
    refinements = _serialized_refinements(
        validated=validated,
        intent=intent,
        candidates=baseline.candidates,
    )
    elapsed_seconds = clock() - started
    if elapsed_seconds >= SEARCH_REFINEMENT_REQUEST_BUDGET_SECONDS:
        return _refinement_response(
            policy=selected_policy,
            status="temporarily_unavailable",
            baseline_fingerprint=baseline.fingerprint,
            baseline_status="current",
            fallback_used=False,
            refinements=(),
            reason="deadline_exhausted",
            intent=intent,
            duration_seconds=elapsed_seconds,
        )
    reason = (
        "deterministic_fallback"
        if fallback_used
        else "provider_proposal"
        if generated.proposals
        else "provider_unavailable"
        if generated.outcome == "provider_unavailable"
        else "no_material_question"
    )
    return _refinement_response(
        policy=selected_policy,
        status=status,
        baseline_fingerprint=baseline.fingerprint,
        baseline_status="current",
        fallback_used=fallback_used,
        refinements=refinements,
        reason=reason,
        intent=intent,
        duration_seconds=elapsed_seconds,
    )


def _refinement_response(
    *,
    policy: SearchPolicy,
    status: Literal["questions_available", "not_needed", "temporarily_unavailable"],
    baseline_fingerprint: str,
    baseline_status: Literal["current", "stale", "unverified"],
    fallback_used: bool,
    refinements: tuple[SearchV4RefinementProposal, ...],
    reason: str,
    intent: SearchIntent,
    duration_seconds: float,
) -> SearchV4RefinementResponse:
    record_search_refinement_completed(
        intent=intent,
        ranking_policy_version=policy.ranking_policy_version,
        status=status,
        reason=reason,
        fallback_used=fallback_used,
        question_count=len(refinements),
        duration_seconds=duration_seconds,
    )
    return SearchV4RefinementResponse(
        search_model_version=policy.search_model_version,
        ranking_policy_version=policy.ranking_policy_version,
        baseline_fingerprint=baseline_fingerprint,
        baseline_status=baseline_status,
        refinement_status=status,
        fallback_used=fallback_used,
        refinements=refinements,
    )


def _baseline_fingerprint(evaluated: _EvaluatedSearch) -> str:
    payload = {
        "candidate_states": [
            {
                "candidate_id": item.record.candidate_id,
                "rank": rank,
                "evaluations": [
                    evaluation.model_dump(mode="json")
                    for evaluation in item.evaluations
                ],
                "ranking": item.ranking.model_dump(mode="json"),
            }
            for rank, item in enumerate(evaluated.ordered, start=1)
        ],
        "catalog_content_digest": _canonical_digest(
            evaluated.snapshot.model_dump(mode="json")
        ),
        "intent_digest": canonical_search_intent_digest(evaluated.intent),
        "ranking_policy_version": evaluated.policy.ranking_policy_version,
        "search_model_version": evaluated.policy.search_model_version,
        "trust_manifest_digest": _canonical_digest(
            evaluated.manifest.model_dump(mode="json")
        ),
        "weather_selection_revision": evaluated.policy.weather.policy_version,
    }
    return _canonical_digest(payload)


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _refinement_baseline_candidates(
    ordered: Sequence[_EvaluatedCandidate],
) -> tuple[RefinementBaselineCandidate, ...]:
    return tuple(
        RefinementBaselineCandidate(
            candidate_id=item.record.candidate_id,
            ski_region_id=item.record.region.ski_region_id,
            constraint_facts=item.record.constraint_facts,
            evaluations=tuple(
                _compact_refinement_evaluation(evaluation)
                for evaluation in item.evaluations
            ),
            unscored=isinstance(item.ranking, UnscoredAllocation),
        )
        for item in ordered
    )


def _compact_refinement_evaluation(
    evaluation: FactorEvaluation,
) -> RefinementFactorEvaluation:
    """Retain only fields consumed by refinement actionability and scoring."""

    return RefinementFactorEvaluation(
        factor_id=evaluation.factor_id,
        raw_utility=evaluation.raw_utility,
        neutral_utility=evaluation.neutral_utility,
        effective_evidence_cap=evaluation.effective_evidence_cap,
    )


def _refinement_states(
    candidates: Sequence[RefinementBaselineCandidate],
) -> tuple[RefinementCandidateState, ...]:
    return tuple(
        RefinementCandidateState(
            candidate_id=item.candidate_id,
            evaluations=tuple(
                evaluation.materialize() for evaluation in item.evaluations
            ),
            eligibility_evaluator=(
                lambda candidate_intent, facts=item.constraint_facts: (
                    evaluate_search_constraints(
                        candidate=facts,
                        intent=candidate_intent,
                    ).eligible
                )
            ),
        )
        for item in candidates
    )


def _serialized_refinements(
    *,
    validated: Sequence[ValidatedRefinementProposal],
    intent: SearchIntent,
    candidates: Sequence[RefinementBaselineCandidate],
) -> tuple[SearchV4RefinementProposal, ...]:
    baseline_ordered_candidate_ids = tuple(item.candidate_id for item in candidates)
    baseline_unscored_candidate_ids = frozenset(
        item.candidate_id for item in candidates if item.unscored
    )
    candidate_region_ids = {
        item.candidate_id: item.ski_region_id for item in candidates
    }
    return tuple(
        _response_refinement_proposal(
            item,
            intent=intent,
            baseline_ordered_candidate_ids=baseline_ordered_candidate_ids,
            baseline_unscored_candidate_ids=baseline_unscored_candidate_ids,
            candidate_region_ids=candidate_region_ids,
        )
        for item in validated
    )


def _load_trust_manifest(path: Path) -> CatalogTrustManifest:
    return CatalogTrustManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _travel_effort(
    intent: SearchIntent,
    destination: StayDestination,
) -> TravelEffort | None:
    origin = intent.travel_context.origin_text
    requested_mode = intent.travel_context.mode or (
        intent.constraints.travel_limit.mode
        if intent.constraints.travel_limit is not None
        else "car"
    )
    if origin is None or requested_mode != "car":
        return None
    maximum_minutes = (
        round(intent.constraints.travel_limit.maximum_duration_hours * 60)
        if intent.constraints.travel_limit is not None
        and intent.constraints.travel_limit.mode == "car"
        else None
    )
    return assess_deterministic_travel_effort(
        origin,
        destination,
        max_drive_minutes=maximum_minutes,
    )


def _constraint_facts(
    *,
    candidate_id: str,
    graph: CatalogGraph,
    destination: StayDestination,
    base: StayBase,
    area: SkiArea,
    product: LiftPassProduct,
    travel_effort: TravelEffort | None,
    manifest: CatalogTrustManifest,
) -> ConstraintCandidateFacts:
    season_status = _status(manifest, "ski_areas", area.ski_area_id, "elevation_season")
    lodging_status = _status(
        manifest,
        "stay_bases",
        base.stay_base_id,
        "lodging_price_quality",
    )
    currency = _lodging_currency(base.price_range)
    lodging = (
        CandidateLodgingEstimate(
            mode="lodging_nightly",
            minimum=base.price_min,
            maximum=base.price_max,
            currency=currency,
            trust_status=lodging_status,
            provenance="Catalog lodging range; estimate-aware constraint only.",
        )
        if currency is not None
        else None
    )
    return ConstraintCandidateFacts(
        candidate_id=candidate_id,
        location=CandidateLocation(
            country=destination.country,
            region=destination.region,
            ski_region_ids=_region_lineage(
                destination.trip_market_region_id,
                graph.regions_by_id,
            ),
            destination_id=destination.stay_destination_id,
        ),
        season=CandidateSeasonEvidence(
            exact_windows=tuple(
                (window.start_date, window.end_date) for window in area.season_windows
            ),
            recurring_start_month=area.season_start_month,
            recurring_end_month=area.season_end_month,
            trust_status=season_status,
        ),
        lodging=lodging,
        travel=(
            CandidateTravelEvidence(
                mode="car",
                duration_minutes=travel_effort.duration_minutes,
                provenance=travel_effort.provenance,
            )
            if travel_effort is not None
            else None
        ),
        stay_quality_score=quality_score(base.quality) / 3 * 10,
        features=_feature_facts(area=area, base=base, manifest=manifest),
        pass_prices=_pass_prices(product, manifest),
    )


def _feature_facts(
    *,
    area: SkiArea,
    base: StayBase,
    manifest: CatalogTrustManifest,
) -> tuple[CandidateFeatureFact, ...]:
    features: list[CandidateFeatureFact] = []
    area_features = (
        ("marked_freeride_routes", "marked_freeride_routes"),
        ("snow_park", "snow_park"),
        ("night_skiing", "night_skiing"),
        ("glacier_terrain", "glacier_terrain"),
    )
    for factor_id, field_group in area_features:
        fact = getattr(area, factor_id)
        features.append(
            CandidateFeatureFact(
                factor_id=factor_id,
                availability=fact.availability,
                trust_status=_status(
                    manifest,
                    "ski_areas",
                    area.ski_area_id,
                    field_group,
                ),
            )
        )
    features.append(
        CandidateFeatureFact(
            factor_id="snowmaking_availability",
            availability=area.snowmaking.availability,
            trust_status=_status(
                manifest,
                "ski_areas",
                area.ski_area_id,
                "snowmaking",
            ),
        )
    )
    features.extend(
        (
            _apres_feature(
                factor_id="ski_day_apres",
                fact=area.ski_day_apres_profile,
                trust_status=_status(
                    manifest,
                    "ski_areas",
                    area.ski_area_id,
                    "ski_day_apres",
                ),
            ),
            _apres_feature(
                factor_id="local_apres",
                fact=base.local_apres_profile,
                trust_status=_status(
                    manifest,
                    "stay_bases",
                    base.stay_base_id,
                    "local_apres",
                ),
            ),
            _categorical_feature(
                factor_id="local_pace",
                value=base.base_character.local_pace,
                trust_status=_status(
                    manifest,
                    "stay_bases",
                    base.stay_base_id,
                    "base_character",
                ),
            ),
            _categorical_feature(
                factor_id="development_style",
                value=base.base_character.development_style,
                trust_status=_status(
                    manifest,
                    "stay_bases",
                    base.stay_base_id,
                    "base_character",
                ),
            ),
            _categorical_feature(
                factor_id="base_type",
                value=base.base_type,
                trust_status=_status(
                    manifest,
                    "stay_bases",
                    base.stay_base_id,
                    "base_type",
                ),
            ),
        )
    )
    return tuple(features)


def _apres_feature(
    *,
    factor_id: str,
    fact: object,
    trust_status: Status,
) -> CandidateFeatureFact:
    availability = getattr(fact, "availability")
    intensity = getattr(fact, "intensity")
    return CandidateFeatureFact(
        factor_id=factor_id,
        availability=availability,
        trust_status=trust_status,
        values=(intensity,) if intensity is not None else (),
    )


def _categorical_feature(
    *,
    factor_id: str,
    value: str | None,
    trust_status: Status,
) -> CandidateFeatureFact:
    return CandidateFeatureFact(
        factor_id=factor_id,
        availability="unknown" if value in {None, "unknown"} else "available",
        trust_status=trust_status,
        values=(value,) if value not in {None, "unknown"} else (),
    )


def _pass_prices(
    product: LiftPassProduct,
    manifest: CatalogTrustManifest,
) -> tuple[CandidatePassPrice, ...]:
    trust_status = _status(
        manifest,
        "lift_pass_products",
        product.lift_pass_product_id,
        "prices",
    )
    result: list[CandidatePassPrice] = []
    for price in product.prices:
        if price.season_label is None:
            continue
        amount_maximum: float | None
        if price.price_kind == "fixed":
            amount_maximum = price.amount
        elif price.price_kind == "range":
            amount_maximum = price.amount_max
        else:
            amount_maximum = None
        if amount_maximum is None:
            continue
        result.append(
            CandidatePassPrice(
                duration_days=price.duration_days,
                audience=price.audience,
                amount_maximum=amount_maximum,
                currency=price.currency,
                season=price.season_label,
                trust_status=trust_status,
            )
        )
    return tuple(result)


def _status(
    manifest: CatalogTrustManifest,
    entity_type: str,
    entity_id: str,
    field_group: str,
) -> Status:
    return manifest.entities[entity_type][entity_id].field_statuses[field_group]  # type: ignore[index,return-value]


def _lodging_currency(price_range: str) -> str | None:
    match = _CURRENCY_PREFIX.match(price_range)
    return match.group(1).upper() if match is not None else None


def _region_lineage(
    region_id: str,
    regions_by_id: Mapping[str, SkiRegion],
) -> tuple[str, ...]:
    result: list[str] = []
    current: str | None = region_id
    while current is not None and current not in result:
        result.append(current)
        current = regions_by_id[current].parent_ski_region_id
    return tuple(result)


def _pass_slice(intent: SearchIntent) -> tuple[int, str, str | None]:
    ceiling = intent.constraints.pass_price_ceiling
    if ceiling is not None:
        return ceiling.duration_days, ceiling.audience, ceiling.season
    window = intent.constraints.travel_window
    return (
        window.ski_day_count if window is not None and window.ski_day_count else 6,
        "adult",
        None,
    )


def _static_candidate(record: V4CandidateRecord) -> StaticFactorCandidate:
    travel = record.travel_effort
    return StaticFactorCandidate(
        region=record.region,
        destination=record.destination,
        stay_base=record.stay_base,
        ski_area=record.ski_area,
        access=record.access,
        selected_pass=record.selected_pass,
        terrain_domains=record.terrain_domains,
        travel_duration_minutes=(
            travel.duration_minutes if travel is not None else None
        ),
        travel_evidence_cap=(0.5 if travel is not None else 0),
        travel_provenance=(
            travel.provenance if travel is not None else "No comparable route evidence."
        ),
    )


def _load_weather_evidence(
    *,
    intent: SearchIntent,
    area_ids: tuple[str, ...],
    policy: SearchPolicy,
    climatology_repository: _ClimatologyRepository,
    forecast_repository: _ForecastRepository,
    reference_time: datetime,
) -> tuple[
    dict[str, tuple[SnowClimatologyDaily, ...]],
    dict[str, tuple[ServedWeatherForecastDaily, ...]],
    frozenset[str],
]:
    window = intent.constraints.travel_window
    if window is None or not area_ids:
        return {}, {}, frozenset()
    climate_groups = climatology_repository.list_daily_rows_for_ski_areas_window(
        area_ids,
        elevation_bands=("mid",),
        baseline_periods=("normal_30y", "recent_15y"),
        travel_month=window.month if window.mode == "month" else None,
        trip_start_date=window.start_date,
        trip_end_date=window.end_date,
    )
    climate_by_area: dict[str, list[SnowClimatologyDaily]] = defaultdict(list)
    for (area_id, _elevation_band, _baseline), rows in climate_groups.items():
        climate_by_area[area_id].extend(rows)

    forecast_rows: tuple[ServedWeatherForecastDaily, ...] = ()
    if window.mode == "exact_dates":
        assert window.start_date is not None and window.end_date is not None
        forecast_rows = forecast_repository.list_latest_daily_rows(
            ski_area_ids=area_ids,
            start_date=window.start_date,
            end_date=window.end_date,
            source_keys=(
                policy.weather.preferred_short_range_source,
                policy.weather.fallback_and_long_range_source,
            ),
            elevation_band="mid",
        )
    forecast_by_area: dict[str, list[ServedWeatherForecastDaily]] = defaultdict(list)
    stale_run_ids: set[str] = set()
    for row in forecast_rows:
        forecast_by_area[row.daily.ski_area_id].append(row)
        if not forecast_run_is_fresh(row.run, reference_time):
            stale_run_ids.add(row.run.forecast_run_id)
    return (
        {key: tuple(value) for key, value in climate_by_area.items()},
        {key: tuple(value) for key, value in forecast_by_area.items()},
        frozenset(stale_run_ids),
    )


def _evaluated_sort_key(item: _EvaluatedCandidate) -> tuple[object, ...]:
    if isinstance(item.ranking, RankedScore):
        return (0, -item.ranking.fit_score, item.record.candidate_id)
    return (1, 0, item.record.candidate_id)


def _group_results(
    ordered: Sequence[_EvaluatedCandidate],
    duration_days: int,
    audience: str,
    season_label: str | None,
    manifest: CatalogTrustManifest,
) -> tuple[SearchV4RecommendationGroup, ...]:
    grouped: dict[str, list[_EvaluatedCandidate]] = defaultdict(list)
    for item in ordered:
        grouped[item.record.region.ski_region_id].append(item)
    ordered_groups = sorted(
        grouped.values(),
        key=lambda items: _evaluated_sort_key(items[0]),
    )
    result: list[SearchV4RecommendationGroup] = []
    for rank, items in enumerate(ordered_groups, start=1):
        selected = _material_alternatives(items)
        configurations = tuple(
            _configuration(
                item,
                duration_days,
                audience,
                season_label,
                manifest,
            )
            for item in selected
        )
        top = configurations[0]
        result.append(
            SearchV4RecommendationGroup(
                ski_region_id=top.ski_region_id,
                ski_region_name=top.ski_region_name,
                rank=rank,
                fit_score=top.fit_score,
                top_configuration=top,
                alternative_configurations=configurations[1:],
            )
        )
    return tuple(result)


def _material_alternatives(
    items: Sequence[_EvaluatedCandidate],
) -> tuple[_EvaluatedCandidate, ...]:
    top = items[0]
    selected = [top]
    represented = {
        (top.record.destination.stay_destination_id, top.record.ski_area.ski_area_id)
    }
    for item in items[1:]:
        identity = (
            item.record.destination.stay_destination_id,
            item.record.ski_area.ski_area_id,
        )
        if identity not in represented:
            selected.append(item)
            represented.add(identity)
        if len(selected) == 4:
            return tuple(selected)
    for item in items[1:]:
        if item not in selected:
            selected.append(item)
        if len(selected) == 4:
            break
    return tuple(selected)


def _configuration(
    item: _EvaluatedCandidate,
    duration_days: int,
    audience: str,
    season_label: str | None,
    manifest: CatalogTrustManifest,
) -> SearchV4Configuration:
    record = item.record
    ranking = item.ranking
    return SearchV4Configuration(
        candidate_id=record.candidate_id,
        ski_region_id=record.region.ski_region_id,
        ski_region_name=record.region.name,
        stay_destination_id=record.destination.stay_destination_id,
        stay_destination_name=record.destination.name,
        stay_base_id=record.stay_base.stay_base_id,
        stay_base_name=record.stay_base.name,
        ski_area_id=record.ski_area.ski_area_id,
        ski_area_name=record.ski_area.name,
        evidence_profile=_evidence_profile(item.evaluations),
        access=SearchV4AccessSummary(
            ski_area_access_id=record.access.ski_area_access_id,
            access_mode=record.access.access_mode,
            lift_distance=record.access.lift_distance,
            nearest_lift_name=record.access.nearest_lift_name,
            distance_m=record.access.distance_m,
            duration_minutes=record.access.duration_minutes,
            is_direct=record.access.is_direct,
            relationship_trust_status=_status(
                manifest,
                "ski_area_access",
                record.access.ski_area_access_id,
                "relationship",
            ),
            access_mode_distance_trust_status=_status(
                manifest,
                "ski_area_access",
                record.access.ski_area_access_id,
                "access_mode_distance",
            ),
        ),
        selected_pass=_pass_summary(
            record,
            duration_days=duration_days,
            audience=audience,
            season_label=season_label,
            manifest=manifest,
        ),
        lodging_estimate=record.constraint_facts.lodging,
        ranking_status="ranked" if isinstance(ranking, RankedScore) else "unscored",
        fit_score=ranking.fit_score if isinstance(ranking, RankedScore) else None,
        groups=ranking.groups if isinstance(ranking, RankedScore) else (),
        factors=ranking.factors if isinstance(ranking, RankedScore) else (),
        constraint_warnings=item.constraint_decision.warnings,
    )


def _evidence_profile(
    evaluations: Sequence[FactorEvaluation],
) -> PlanningEvidenceProfile:
    snow = next(
        (
            evaluation
            for evaluation in evaluations
            if evaluation.factor_id == "trip_window_snow_fit"
        ),
        None,
    )
    if snow is None or snow.effective_evidence_cap <= 0:
        return "fallback_heavy"
    forecast_coverage = snow.evidence_cap_components.get(
        "forecast_date_coverage",
        0,
    )
    if (
        isinstance(forecast_coverage, (int, float))
        and not isinstance(forecast_coverage, bool)
        and forecast_coverage > 0
    ):
        return "forecast_assisted"
    climatology_coverage = snow.evidence_cap_components.get(
        "climatology_date_coverage",
        0,
    )
    if (
        isinstance(climatology_coverage, (int, float))
        and not isinstance(climatology_coverage, bool)
        and climatology_coverage >= 1
    ):
        return "archive_backed"
    return "fallback_heavy"


def _pass_summary(
    record: V4CandidateRecord,
    *,
    duration_days: int,
    audience: str,
    season_label: str | None,
    manifest: CatalogTrustManifest,
) -> SearchV4PassSummary:
    product = record.selected_pass
    terrain = select_accessible_terrain_source(
        product=product,
        ski_area=record.ski_area,
        terrain_domains=record.terrain_domains,
        trust_resolver=ManifestCatalogEvidenceResolver(manifest),
    )
    terrain_evidence = (
        SearchV4TerrainEvidence(
            trust_status=terrain.evidence.status,
            scope=terrain.summary_scope,
            source_entity_id=terrain.source_entity_id,
            field_group=terrain.field_group,
        )
        if (
            terrain.value is not None
            and terrain.summary_scope is not None
            and terrain.source_entity_id is not None
            and terrain.field_group is not None
        )
        else None
    )
    price = select_matching_pass_price(
        product=product,
        duration_days=duration_days,
        audience=audience,
        season_label=season_label,
    )
    return SearchV4PassSummary(
        lift_pass_product_id=product.lift_pass_product_id,
        name=product.name,
        validity_scope=product.validity_scope,
        covered_ski_area_ids=record.pass_covered_ski_area_ids,
        accessible_piste_km=terrain.value,
        accessible_piste_km_evidence=terrain_evidence,
        price=(
            SearchV4PassPriceSummary(
                duration_days=price.duration_days,
                audience=price.audience,
                amount=price.amount,
                amount_min=price.amount_min,
                amount_max=price.amount_max,
                currency=price.currency,
                price_kind=price.price_kind,
                season_label=price.season_label,
            )
            if price is not None
            else None
        ),
    )


def _refinements(
    *,
    include: bool,
    brief: str | None,
    intent: SearchIntent,
    ordered: Sequence[_EvaluatedCandidate],
    policy: SearchPolicy,
    client: LLMClient | None,
    already_answered_question_ids: frozenset[str],
) -> tuple[SearchV4RefinementProposal, ...]:
    if not include or client is None:
        return ()
    candidates = _refinement_baseline_candidates(ordered)
    states = _refinement_states(candidates)
    generated = generate_refinement_proposals(
        brief=brief,
        intent=intent,
        candidates=states,
        policy=policy,
        client=client,
        already_answered_question_ids=already_answered_question_ids,
    )
    validated = (
        generated.proposals
        if isinstance(generated, RefinementGenerationResult)
        else generated
    )
    return _serialized_refinements(
        validated=validated,
        intent=intent,
        candidates=candidates,
    )


def _response_refinement_proposal(
    validated: ValidatedRefinementProposal,
    *,
    intent: SearchIntent,
    baseline_ordered_candidate_ids: tuple[str, ...],
    baseline_unscored_candidate_ids: frozenset[str],
    candidate_region_ids: Mapping[str, str],
) -> SearchV4RefinementProposal:
    proposal = validated.proposal
    return SearchV4RefinementProposal(
        question_id=proposal.question_id,
        question=proposal.question,
        reason=proposal.reason,
        options=tuple(
            SearchV4RefinementOption(
                **option.model_dump(mode="python"),
                intent_changed=variant_outcome.intent_changed,
                preview=_refinement_preview(
                    intent=intent,
                    option=option,
                    baseline_ordered_candidate_ids=baseline_ordered_candidate_ids,
                    baseline_unscored_candidate_ids=baseline_unscored_candidate_ids,
                    candidate_region_ids=candidate_region_ids,
                    variant_outcome=variant_outcome,
                ),
            )
            for option, variant_outcome in zip(
                proposal.options,
                validated.variant_outcomes,
                strict=True,
            )
        ),
    )


def _refinement_preview(
    *,
    baseline_ordered_candidate_ids: Sequence[str],
    candidate_region_ids: Mapping[str, str],
    variant_outcome: RefinementVariantOutcome,
    baseline_unscored_candidate_ids: frozenset[str] = frozenset(),
    intent: SearchIntent | None = None,
    option: RefinementOption | None = None,
) -> SearchV4RefinementPreview | None:
    if (
        intent is not None
        and option is not None
        and _option_can_expand_existing_require(intent, option)
    ):
        return None
    if _visible_top_three_has_unscored_candidate(
        baseline_ordered_candidate_ids,
        candidate_region_ids,
        baseline_unscored_candidate_ids,
    ):
        return None

    variant_scored_ids = set(variant_outcome.ordered_candidate_ids)
    variant_unscored_candidate_ids = (
        variant_outcome.eligible_candidate_ids - variant_scored_ids
    )
    variant_ordered_candidate_ids = (
        *variant_outcome.ordered_candidate_ids,
        *sorted(variant_unscored_candidate_ids),
    )
    if _visible_top_three_has_unscored_candidate(
        variant_ordered_candidate_ids,
        candidate_region_ids,
        variant_unscored_candidate_ids,
    ):
        return None

    baseline_region_ids = _ordered_region_ids(
        baseline_ordered_candidate_ids,
        candidate_region_ids,
    )
    preview_region_ids = _ordered_region_ids(
        variant_ordered_candidate_ids,
        candidate_region_ids,
    )
    baseline_ranks = {
        ski_region_id: rank
        for rank, ski_region_id in enumerate(baseline_region_ids[:3], start=1)
    }
    preview_ranks = {
        ski_region_id: rank
        for rank, ski_region_id in enumerate(preview_region_ids[:3], start=1)
    }
    changed_region_ids = _deduplicated(
        (*preview_region_ids[:3], *baseline_region_ids[:3])
    )
    changes = tuple(
        SearchV4RefinementRankChange(
            ski_region_id=ski_region_id,
            previous_rank=baseline_ranks.get(ski_region_id),
            preview_rank=preview_ranks.get(ski_region_id),
        )
        for ski_region_id in changed_region_ids
        if baseline_ranks.get(ski_region_id) != preview_ranks.get(ski_region_id)
    )[:3]
    return SearchV4RefinementPreview(
        top_rank_changes=changes,
        eligible_candidate_count_delta=(
            len(variant_outcome.eligible_candidate_ids)
            - len(set(baseline_ordered_candidate_ids))
        ),
    )


def _option_can_expand_existing_require(
    intent: SearchIntent,
    option: RefinementOption,
) -> bool:
    explicit_requirement_ids = {
        requirement.factor_id for requirement in intent.constraints.factor_requirements
    }
    existing_requires = {
        preference.factor_id: preference
        for preference in intent.factor_preferences
        if preference.mode == "require"
        and preference.factor_id not in explicit_requirement_ids
    }
    if any(
        objective.factor_id in existing_requires
        for objective in option.objective_patches
    ):
        return True
    for patch in option.factor_preference_patches:
        existing = existing_requires.get(patch.factor_id)
        if existing is None:
            continue
        if patch.mode != "require":
            return True
        if _require_values_can_expand(existing.values, patch.values):
            return True
    return False


def _require_values_can_expand(
    existing_values: Sequence[str],
    proposed_values: Sequence[str],
) -> bool:
    if not existing_values:
        return False
    if not proposed_values:
        return True
    return not set(proposed_values).issubset(existing_values)


def _visible_top_three_has_unscored_candidate(
    ordered_candidate_ids: Sequence[str],
    candidate_region_ids: Mapping[str, str],
    unscored_candidate_ids: frozenset[str],
) -> bool:
    visible_region_ids: set[str] = set()
    for candidate_id in ordered_candidate_ids:
        ski_region_id = candidate_region_ids[candidate_id]
        if ski_region_id in visible_region_ids:
            continue
        visible_region_ids.add(ski_region_id)
        if candidate_id in unscored_candidate_ids:
            return True
        if len(visible_region_ids) == 3:
            return False
    return False


def _ordered_region_ids(
    ordered_candidate_ids: Sequence[str],
    candidate_region_ids: Mapping[str, str],
) -> tuple[str, ...]:
    region_ids: list[str] = []
    for candidate_id in ordered_candidate_ids:
        region_ids.append(candidate_region_ids[candidate_id])
    return _deduplicated(region_ids)


def _deduplicated(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
