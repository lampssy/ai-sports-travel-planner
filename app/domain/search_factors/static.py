from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from app.domain.catalog import (
    ApresProfileFact,
    CatalogLiftPassPrice,
    LiftPassProduct,
    SkiArea,
    SkiAreaAccess,
    SkiRegion,
    StayBase,
    StayDestination,
    TerrainDomain,
)
from app.domain.catalog_trust import CatalogTrustManifest
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_factors.registry import FactorRegistry
from app.domain.search_policy import SearchPolicy
from app.domain.search_v4_models import SearchIntent

CatalogTrustStatus = Literal[
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
]
_TRUST_CAPS: Mapping[CatalogTrustStatus, float] = {
    "verified": 1,
    "verified_with_adjustment": 1,
    "estimated": 0.25,
    "needs_source": 0,
}
_NUMERIC_FACTOR_IDS = (
    "accessible_terrain_scale",
    "terrain_potential_scale",
    "lift_network_scale",
    "pass_price_per_day",
    "pass_terrain_value",
    "travel_effort",
)


@dataclass(frozen=True)
class NumericBounds:
    minimum: float
    maximum: float

    def normalize(self, value: float, *, lower_is_better: bool = False) -> float:
        if self.maximum <= self.minimum:
            return 0.5
        utility = (value - self.minimum) / (self.maximum - self.minimum)
        utility = min(1.0, max(0.0, utility))
        return 1 - utility if lower_is_better else utility


@dataclass(frozen=True)
class ResolvedCatalogEvidence:
    status: CatalogTrustStatus
    source_refs: tuple[str, ...]

    @property
    def cap(self) -> float:
        return _TRUST_CAPS[self.status]


class CatalogEvidenceResolver(Protocol):
    def resolve(
        self,
        entity_type: str,
        entity_id: str,
        field_group: str,
    ) -> ResolvedCatalogEvidence: ...


@dataclass(frozen=True)
class ManifestCatalogEvidenceResolver:
    manifest: CatalogTrustManifest

    def resolve(
        self,
        entity_type: str,
        entity_id: str,
        field_group: str,
    ) -> ResolvedCatalogEvidence:
        entry = self.manifest.entities[entity_type][entity_id]  # type: ignore[index]
        return ResolvedCatalogEvidence(
            status=entry.field_statuses[field_group],
            source_refs=entry.field_source_refs[field_group],
        )


@dataclass(frozen=True)
class StaticFactorCandidate:
    region: SkiRegion
    destination: StayDestination
    stay_base: StayBase
    ski_area: SkiArea
    access: SkiAreaAccess
    selected_pass: LiftPassProduct
    terrain_domains: tuple[TerrainDomain, ...]
    travel_duration_minutes: int | None = None
    travel_evidence_cap: float = 0
    travel_provenance: str = "No comparable route evidence."

    def __post_init__(self) -> None:
        if not 0 <= self.travel_evidence_cap <= 1:
            raise ValueError("travel_evidence_cap must be between zero and one")


@dataclass(frozen=True)
class StaticEvaluationContext:
    intent: SearchIntent
    policy: SearchPolicy
    trust_resolver: CatalogEvidenceResolver
    numeric_bounds: Mapping[str, NumericBounds]
    pass_duration_days: int
    pass_audience: str
    pass_season_label: str | None


@dataclass
class _StaticFactorEvaluator:
    factor_id: str
    function: Callable[
        [StaticEvaluationContext, StaticFactorCandidate], FactorEvaluation
    ]

    def evaluate(self, context: object, candidate: object) -> FactorEvaluation:
        if not isinstance(context, StaticEvaluationContext):
            raise TypeError("static evaluator requires StaticEvaluationContext")
        if not isinstance(candidate, StaticFactorCandidate):
            raise TypeError("static evaluator requires StaticFactorCandidate")
        return self.function(context, candidate)


@dataclass(frozen=True)
class _NumericSource:
    value: float | None
    scope: str
    entity_ids: tuple[str, ...]
    entity_type: str | None
    entity_id: str | None
    field_group: str | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class AccessibleTerrainSelection:
    value: float | None
    scoring_scope: str
    scoring_entity_ids: tuple[str, ...]
    source_entity_type: str | None
    source_entity_id: str | None
    field_group: str | None
    summary_scope: Literal["pass", "terrain_domain", "ski_area"] | None
    evidence: ResolvedCatalogEvidence
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _PriceSlice:
    amount: float
    currency: str
    evidence_shape_cap: float
    price_kind: str


def build_static_factor_registry() -> FactorRegistry:
    return FactorRegistry(
        _StaticFactorEvaluator(factor_id=factor_id, function=function)
        for factor_id, function in _STATIC_EVALUATORS.items()
    )


def derive_numeric_bounds(
    *,
    candidates: tuple[StaticFactorCandidate, ...],
    pass_duration_days: int,
    pass_audience: str,
    pass_season_label: str | None,
    trust_resolver: CatalogEvidenceResolver,
) -> dict[str, NumericBounds]:
    values: dict[str, list[float]] = {
        factor_id: [] for factor_id in _NUMERIC_FACTOR_IDS
    }
    comparable_price_currencies = {
        price.currency
        for candidate in candidates
        if (
            price := _matching_price_slice_values(
                product=candidate.selected_pass,
                duration_days=pass_duration_days,
                audience=pass_audience,
                season_label=pass_season_label,
            )
        )
        is not None
        and trust_resolver.resolve(
            "lift_pass_products",
            candidate.selected_pass.lift_pass_product_id,
            "prices",
        ).cap
        > 0
    }
    comparable_price_currency = (
        next(iter(comparable_price_currencies))
        if len(comparable_price_currencies) == 1
        else None
    )
    for candidate in candidates:
        for factor_id in _NUMERIC_FACTOR_IDS:
            if factor_id in {"pass_price_per_day", "pass_terrain_value"}:
                price = _matching_price_slice_values(
                    product=candidate.selected_pass,
                    duration_days=pass_duration_days,
                    audience=pass_audience,
                    season_label=pass_season_label,
                )
                if (
                    comparable_price_currency is None
                    or price is None
                    or price.currency != comparable_price_currency
                ):
                    continue
            value = _raw_numeric_value(
                factor_id=factor_id,
                candidate=candidate,
                pass_duration_days=pass_duration_days,
                pass_audience=pass_audience,
                pass_season_label=pass_season_label,
                trust_resolver=trust_resolver,
            )
            if (
                value is not None
                and _numeric_bounds_evidence_cap(
                    factor_id=factor_id,
                    candidate=candidate,
                    pass_duration_days=pass_duration_days,
                    pass_audience=pass_audience,
                    pass_season_label=pass_season_label,
                    trust_resolver=trust_resolver,
                )
                > 0
            ):
                values[factor_id].append(value)
    return {
        factor_id: NumericBounds(minimum=min(items), maximum=max(items))
        for factor_id, items in values.items()
        if items
    }


def _party_skill_coverage(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    area = candidate.ski_area
    levels = context.intent.party.skill_levels
    evidence = _catalog_evidence(context, "ski_areas", area.ski_area_id, "skill_fit")
    if not levels:
        return _make_evaluation(
            context=context,
            factor_id="party_skill_coverage",
            scope="ski_area",
            entity_ids=(area.ski_area_id,),
            raw_value=None,
            raw_utility=0.5,
            evidence_cap=0,
            evidence=evidence,
            warnings=("party skill levels not supplied",),
            explanation_inputs={},
        )

    difficulty = area.piste_km_by_difficulty
    if difficulty is not None:
        total = difficulty.beginner + difficulty.intermediate + difficulty.advanced
        if total > 0:
            fits = {
                level: _skill_fit_from_kilometres(
                    level=level,
                    beginner=difficulty.beginner,
                    intermediate=difficulty.intermediate,
                    advanced=difficulty.advanced,
                    total=total,
                )
                for level in levels
            }
            return _make_evaluation(
                context=context,
                factor_id="party_skill_coverage",
                scope="ski_area",
                entity_ids=(area.ski_area_id,),
                raw_value={
                    "basis": "piste_km_by_difficulty",
                    "minimum_party_fit": min(fits.values()),
                },
                raw_utility=min(fits.values()),
                evidence_cap=evidence.cap,
                evidence=evidence,
                warnings=(),
                explanation_inputs={
                    "fits_by_level": fits,
                    "piste_km_by_difficulty": difficulty.model_dump(),
                },
            )

    supported = set(area.supported_skill_levels)
    positive_fits = {level: 1 if level in supported else 0.5 for level in levels}
    qualitative_cap = min(evidence.cap, 0.25) if supported else 0
    return _make_evaluation(
        context=context,
        factor_id="party_skill_coverage",
        scope="ski_area",
        entity_ids=(area.ski_area_id,),
        raw_value={
            "basis": "supported_skill_levels" if supported else "unknown",
            "supported_skill_levels": tuple(sorted(supported)),
        },
        raw_utility=min(positive_fits.values()),
        evidence_cap=qualitative_cap,
        evidence=evidence,
        warnings=("difficulty profile unavailable",),
        explanation_inputs={"fits_by_level": positive_fits},
    )


def _skill_fit_from_kilometres(
    *,
    level: str,
    beginner: float,
    intermediate: float,
    advanced: float,
    total: float,
) -> float:
    if level == "beginner":
        compatible = beginner
        full_share = 0.30
        full_amount = 10
    elif level == "intermediate":
        compatible = beginner + intermediate
        full_share = 0.70
        full_amount = 30
    else:
        compatible = beginner + intermediate + advanced
        full_share = 1
        full_amount = 50
    share_utility = min(1.0, compatible / total / full_share)
    amount_utility = min(1.0, compatible / full_amount)
    return 0.65 * share_utility + 0.35 * amount_utility


def _accessible_terrain_scale(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    return _numeric_evaluation(
        context=context,
        candidate=candidate,
        factor_id="accessible_terrain_scale",
        source=_accessible_terrain_source(candidate, context.trust_resolver),
    )


def _terrain_potential_scale(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    return _numeric_evaluation(
        context=context,
        candidate=candidate,
        factor_id="terrain_potential_scale",
        source=_terrain_potential_source(
            candidate,
            metric="total_piste_km",
            trust_resolver=context.trust_resolver,
        ),
    )


def _lift_network_scale(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    return _numeric_evaluation(
        context=context,
        candidate=candidate,
        factor_id="lift_network_scale",
        source=_terrain_potential_source(
            candidate,
            metric="total_lift_count",
            trust_resolver=context.trust_resolver,
        ),
    )


def _numeric_evaluation(
    *,
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
    factor_id: str,
    source: _NumericSource,
    lower_is_better: bool = False,
    evidence_shape_cap: float = 1,
    extra_inputs: Mapping[str, object] | None = None,
) -> FactorEvaluation:
    del candidate
    bounds = context.numeric_bounds.get(factor_id)
    evidence = _source_evidence(context, source)
    if source.value is None or bounds is None:
        raw_utility = 0.5
        cap = 0
        warnings = (*source.warnings, "comparison value or bounds unavailable")
    else:
        raw_utility = bounds.normalize(source.value, lower_is_better=lower_is_better)
        cap = evidence.cap * evidence_shape_cap
        warnings = source.warnings
    explanation_inputs: dict[str, object] = {
        "comparison_bounds": (
            {"minimum": bounds.minimum, "maximum": bounds.maximum}
            if bounds is not None
            else None
        )
    }
    if extra_inputs:
        explanation_inputs.update(extra_inputs)
    return _make_evaluation(
        context=context,
        factor_id=factor_id,
        scope=source.scope,
        entity_ids=source.entity_ids,
        raw_value=source.value,
        raw_utility=raw_utility,
        evidence_cap=cap,
        evidence=evidence,
        warnings=warnings,
        explanation_inputs=explanation_inputs,
    )


def _positive_presence(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
    *,
    factor_id: str,
) -> FactorEvaluation:
    area = candidate.ski_area
    fact = getattr(area, factor_id)
    evidence = _catalog_evidence(context, "ski_areas", area.ski_area_id, factor_id)
    availability = fact.availability
    utility = {"available": 1.0, "unavailable": 0.0, "unknown": 0.5}[availability]
    warnings = ("unknown",) if availability == "unknown" else ()
    return _make_evaluation(
        context=context,
        factor_id=factor_id,
        scope="ski_area",
        entity_ids=(area.ski_area_id,),
        raw_value=fact.model_dump(mode="python"),
        raw_utility=utility,
        evidence_cap=evidence.cap,
        evidence=evidence,
        warnings=warnings,
        explanation_inputs={"availability": availability},
    )


def _marked_freeride_routes(
    context: StaticEvaluationContext, candidate: StaticFactorCandidate
) -> FactorEvaluation:
    return _positive_presence(context, candidate, factor_id="marked_freeride_routes")


def _snow_park(
    context: StaticEvaluationContext, candidate: StaticFactorCandidate
) -> FactorEvaluation:
    return _positive_presence(context, candidate, factor_id="snow_park")


def _night_skiing(
    context: StaticEvaluationContext, candidate: StaticFactorCandidate
) -> FactorEvaluation:
    return _positive_presence(context, candidate, factor_id="night_skiing")


def _glacier_terrain(
    context: StaticEvaluationContext, candidate: StaticFactorCandidate
) -> FactorEvaluation:
    return _positive_presence(context, candidate, factor_id="glacier_terrain")


def _snowmaking_availability(
    context: StaticEvaluationContext, candidate: StaticFactorCandidate
) -> FactorEvaluation:
    area = candidate.ski_area
    evidence = _catalog_evidence(context, "ski_areas", area.ski_area_id, "snowmaking")
    availability = area.snowmaking.availability
    utility = {"available": 1.0, "unavailable": 0.0, "unknown": 0.5}[availability]
    return _make_evaluation(
        context=context,
        factor_id="snowmaking_availability",
        scope="ski_area_window",
        entity_ids=(area.ski_area_id,),
        raw_value=area.snowmaking.model_dump(mode="python"),
        raw_utility=utility,
        evidence_cap=evidence.cap,
        evidence=evidence,
        warnings=("unknown",) if availability == "unknown" else (),
        explanation_inputs={"availability": availability},
    )


def _stay_base_access(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    access = candidate.access
    evidence = _catalog_evidence(
        context,
        "ski_area_access",
        access.ski_area_access_id,
        "access_mode_distance",
    )
    utility = {
        "ski_in_ski_out": 1.0,
        "walk": 0.9,
        "ski_bus": 0.7,
        "mixed": 0.6,
        "drive": 0.35,
        "unknown": 0.5,
    }[access.access_mode]
    return _make_evaluation(
        context=context,
        factor_id="stay_base_access",
        scope="stay_base_access_edge",
        entity_ids=(access.ski_area_access_id,),
        raw_value={
            "access_mode": access.access_mode,
            "lift_distance": access.lift_distance,
            "duration_minutes": access.duration_minutes,
            "distance_m": access.distance_m,
            "is_direct": access.is_direct,
        },
        raw_utility=utility,
        evidence_cap=evidence.cap,
        evidence=evidence,
        warnings=(("unknown access mode",) if access.access_mode == "unknown" else ()),
        explanation_inputs={"access_mode": access.access_mode},
    )


def _lodging_budget_fit(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    base = candidate.stay_base
    evidence = _catalog_evidence(
        context, "stay_bases", base.stay_base_id, "lodging_price_quality"
    )
    return _make_evaluation(
        context=context,
        factor_id="lodging_budget_fit",
        scope="stay_base",
        entity_ids=(base.stay_base_id,),
        raw_value={
            "minimum": base.price_min,
            "maximum": base.price_max,
            "display": base.price_range,
        },
        raw_utility=0.5,
        evidence_cap=evidence.cap,
        evidence=evidence,
        warnings=("measured estimate; excluded from ranking",),
        explanation_inputs={"quality": base.quality},
    )


def _pass_price_per_day(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    price = _matching_price_slice(context, candidate.selected_pass)
    source = _pass_numeric_source(
        candidate,
        None if price is None else price.amount / context.pass_duration_days,
    )
    return _numeric_evaluation(
        context=context,
        candidate=candidate,
        factor_id="pass_price_per_day",
        source=source,
        lower_is_better=True,
        evidence_shape_cap=price.evidence_shape_cap if price is not None else 0,
        extra_inputs={"price_kind": price.price_kind if price is not None else None},
    )


def _pass_terrain_value(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    price = _matching_price_slice(context, candidate.selected_pass)
    terrain = _accessible_terrain_source(candidate, context.trust_resolver)
    value = (
        terrain.value / price.amount
        if terrain.value is not None and price is not None and price.amount > 0
        else None
    )
    source = _pass_numeric_source(candidate, value)
    pass_evidence = _source_evidence(context, source)
    terrain_evidence = _source_evidence(context, terrain)
    bounds = context.numeric_bounds.get("pass_terrain_value")
    cap = (
        min(pass_evidence.cap, terrain_evidence.cap) * price.evidence_shape_cap
        if value is not None and price is not None and bounds is not None
        else 0
    )
    utility = (
        bounds.normalize(value) if value is not None and bounds is not None else 0.5
    )
    combined_evidence = ResolvedCatalogEvidence(
        status=_weaker_status(pass_evidence.status, terrain_evidence.status),
        source_refs=tuple(
            sorted(set(pass_evidence.source_refs + terrain_evidence.source_refs))
        ),
    )
    return _make_evaluation(
        context=context,
        factor_id="pass_terrain_value",
        scope="pass_trip_duration",
        entity_ids=(
            candidate.selected_pass.lift_pass_product_id,
            candidate.ski_area.ski_area_id,
        ),
        raw_value=value,
        raw_utility=utility,
        evidence_cap=cap,
        evidence=combined_evidence,
        warnings=(
            ("comparable price or terrain unavailable",) if value is None else ()
        ),
        explanation_inputs={
            "pass_duration_days": context.pass_duration_days,
            "price": price.amount if price is not None else None,
            "accessible_piste_km": terrain.value,
            "comparison_bounds": (
                {"minimum": bounds.minimum, "maximum": bounds.maximum}
                if bounds is not None
                else None
            ),
        },
    )


def _ski_day_apres(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    return _apres_evaluation(
        context=context,
        factor_id="ski_day_apres",
        scope="ski_area",
        entity_type="ski_areas",
        entity_id=candidate.ski_area.ski_area_id,
        field_group="ski_day_apres",
        fact=candidate.ski_area.ski_day_apres_profile,
    )


def _local_apres(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    return _apres_evaluation(
        context=context,
        factor_id="local_apres",
        scope="stay_base",
        entity_type="stay_bases",
        entity_id=candidate.stay_base.stay_base_id,
        field_group="local_apres",
        fact=candidate.stay_base.local_apres_profile,
    )


def _apres_evaluation(
    *,
    context: StaticEvaluationContext,
    factor_id: str,
    scope: str,
    entity_type: str,
    entity_id: str,
    field_group: str,
    fact: ApresProfileFact,
) -> FactorEvaluation:
    evidence = _catalog_evidence(context, entity_type, entity_id, field_group)
    requested_values = _requested_values(context.intent, factor_id)
    if fact.availability == "unknown":
        utility = 0.5
    elif fact.availability == "unavailable":
        utility = 0
    elif requested_values:
        utility = 1 if fact.intensity in requested_values else 0
    else:
        utility = 1
    return _make_evaluation(
        context=context,
        factor_id=factor_id,
        scope=scope,
        entity_ids=(entity_id,),
        raw_value=fact.model_dump(mode="python"),
        raw_utility=utility,
        evidence_cap=evidence.cap,
        evidence=evidence,
        warnings=("unknown",) if fact.availability == "unknown" else (),
        explanation_inputs={"requested_values": requested_values},
    )


def _local_pace(
    context: StaticEvaluationContext, candidate: StaticFactorCandidate
) -> FactorEvaluation:
    return _categorical_evaluation(
        context=context,
        factor_id="local_pace",
        entity_id=candidate.stay_base.stay_base_id,
        field_group="base_character",
        value=candidate.stay_base.base_character.local_pace,
    )


def _development_style(
    context: StaticEvaluationContext, candidate: StaticFactorCandidate
) -> FactorEvaluation:
    return _categorical_evaluation(
        context=context,
        factor_id="development_style",
        entity_id=candidate.stay_base.stay_base_id,
        field_group="base_character",
        value=candidate.stay_base.base_character.development_style,
    )


def _base_type(
    context: StaticEvaluationContext, candidate: StaticFactorCandidate
) -> FactorEvaluation:
    return _categorical_evaluation(
        context=context,
        factor_id="base_type",
        entity_id=candidate.stay_base.stay_base_id,
        field_group="base_type",
        value=candidate.stay_base.base_type,
    )


def _categorical_evaluation(
    *,
    context: StaticEvaluationContext,
    factor_id: str,
    entity_id: str,
    field_group: str,
    value: str | None,
) -> FactorEvaluation:
    evidence = _catalog_evidence(context, "stay_bases", entity_id, field_group)
    requested_values = _requested_values(context.intent, factor_id)
    if value in {None, "unknown"} or not requested_values:
        utility = 0.5
    else:
        utility = 1 if value in requested_values else 0
    return _make_evaluation(
        context=context,
        factor_id=factor_id,
        scope="stay_base",
        entity_ids=(entity_id,),
        raw_value=value,
        raw_utility=utility,
        evidence_cap=evidence.cap,
        evidence=evidence,
        warnings=("unknown",) if value in {None, "unknown"} else (),
        explanation_inputs={"requested_values": requested_values},
    )


def _travel_effort(
    context: StaticEvaluationContext,
    candidate: StaticFactorCandidate,
) -> FactorEvaluation:
    bounds = context.numeric_bounds.get("travel_effort")
    value = candidate.travel_duration_minutes
    utility = (
        bounds.normalize(value, lower_is_better=True)
        if bounds is not None and value is not None
        else 0.5
    )
    cap = (
        candidate.travel_evidence_cap if value is not None and bounds is not None else 0
    )
    return FactorEvaluation(
        factor_id="travel_effort",
        scope="origin_to_stay_base_route",
        entity_ids=(candidate.stay_base.stay_base_id,),
        raw_value=value,
        raw_utility=utility,
        neutral_utility=context.policy.factor("travel_effort").neutral_utility,
        effective_evidence_cap=cap,
        evidence_cap_components={
            "route_evidence_cap": candidate.travel_evidence_cap,
        },
        warnings=("route evidence unavailable",) if value is None else (),
        provenance_summary=candidate.travel_provenance,
        explanation_inputs={
            "comparison_bounds": (
                {"minimum": bounds.minimum, "maximum": bounds.maximum}
                if bounds is not None
                else None
            )
        },
    )


def _raw_numeric_value(
    *,
    factor_id: str,
    candidate: StaticFactorCandidate,
    pass_duration_days: int,
    pass_audience: str,
    pass_season_label: str | None,
    trust_resolver: CatalogEvidenceResolver,
) -> float | None:
    if factor_id == "accessible_terrain_scale":
        return _accessible_terrain_source(candidate, trust_resolver).value
    if factor_id == "terrain_potential_scale":
        return _terrain_potential_source(
            candidate,
            metric="total_piste_km",
            trust_resolver=trust_resolver,
        ).value
    if factor_id == "lift_network_scale":
        return _terrain_potential_source(
            candidate,
            metric="total_lift_count",
            trust_resolver=trust_resolver,
        ).value
    if factor_id == "travel_effort":
        return (
            float(candidate.travel_duration_minutes)
            if candidate.travel_duration_minutes is not None
            else None
        )
    price = _matching_price_slice_values(
        product=candidate.selected_pass,
        duration_days=pass_duration_days,
        audience=pass_audience,
        season_label=pass_season_label,
    )
    if price is None:
        return None
    if factor_id == "pass_price_per_day":
        return price.amount / pass_duration_days
    if factor_id == "pass_terrain_value":
        terrain = _accessible_terrain_source(candidate, trust_resolver).value
        return (
            terrain / price.amount if terrain is not None and price.amount > 0 else None
        )
    raise KeyError(factor_id)


def _accessible_terrain_source(
    candidate: StaticFactorCandidate,
    trust_resolver: CatalogEvidenceResolver,
) -> _NumericSource:
    selection = select_accessible_terrain_source(
        product=candidate.selected_pass,
        ski_area=candidate.ski_area,
        terrain_domains=candidate.terrain_domains,
        trust_resolver=trust_resolver,
    )
    return _NumericSource(
        value=selection.value,
        scope=selection.scoring_scope,
        entity_ids=selection.scoring_entity_ids,
        entity_type=selection.source_entity_type,
        entity_id=selection.source_entity_id,
        field_group=selection.field_group,
        warnings=selection.warnings,
    )


def select_accessible_terrain_source(
    *,
    product: LiftPassProduct,
    ski_area: SkiArea,
    terrain_domains: tuple[TerrainDomain, ...],
    trust_resolver: CatalogEvidenceResolver,
) -> AccessibleTerrainSelection:
    candidates: list[
        tuple[_NumericSource, Literal["pass", "terrain_domain", "ski_area"]]
    ] = []
    aggregate = product.pass_accessible_terrain
    if aggregate is not None and aggregate.total_piste_km is not None:
        candidates.append(
            (
                _NumericSource(
                    value=aggregate.total_piste_km,
                    scope="ski_area_pass_terrain_domain",
                    entity_ids=(product.lift_pass_product_id, ski_area.ski_area_id),
                    entity_type="lift_pass_products",
                    entity_id=product.lift_pass_product_id,
                    field_group="pass_accessible_terrain",
                ),
                "pass",
            )
        )
    domains = [
        domain
        for domain in terrain_domains
        if domain.terrain_domain_id in product.terrain_domain_ids
        and domain.total_piste_km is not None
    ]
    if len(domains) == 1:
        domain = domains[0]
        candidates.append(
            (
                _NumericSource(
                    value=domain.total_piste_km,
                    scope="ski_area_pass_terrain_domain",
                    entity_ids=(
                        product.lift_pass_product_id,
                        domain.terrain_domain_id,
                    ),
                    entity_type="terrain_domains",
                    entity_id=domain.terrain_domain_id,
                    field_group="aggregate_terrain",
                ),
                "terrain_domain",
            )
        )
    if (
        not product.terrain_domain_ids
        and ski_area.ski_area_id in product.valid_ski_area_ids
        and ski_area.total_piste_km is not None
    ):
        candidates.append(
            (
                _NumericSource(
                    value=ski_area.total_piste_km,
                    scope="ski_area_pass_terrain_domain",
                    entity_ids=(product.lift_pass_product_id, ski_area.ski_area_id),
                    entity_type="ski_areas",
                    entity_id=ski_area.ski_area_id,
                    field_group="terrain_metrics",
                    warnings=(
                        "pass aggregate unavailable; selected ski-area terrain used",
                    ),
                ),
                "ski_area",
            )
        )
    for source, summary_scope in candidates:
        evidence = _source_evidence_for_resolver(trust_resolver, source)
        if evidence.cap > 0:
            return AccessibleTerrainSelection(
                value=source.value,
                scoring_scope=source.scope,
                scoring_entity_ids=source.entity_ids,
                source_entity_type=source.entity_type,
                source_entity_id=source.entity_id,
                field_group=source.field_group,
                summary_scope=summary_scope,
                evidence=evidence,
                warnings=source.warnings,
            )
    return AccessibleTerrainSelection(
        value=None,
        scoring_scope="ski_area_pass_terrain_domain",
        scoring_entity_ids=(product.lift_pass_product_id, ski_area.ski_area_id),
        source_entity_type=None,
        source_entity_id=None,
        field_group=None,
        summary_scope=None,
        evidence=ResolvedCatalogEvidence(status="needs_source", source_refs=()),
        warnings=("pass-accessible terrain unresolved",),
    )


def _terrain_potential_source(
    candidate: StaticFactorCandidate,
    *,
    metric: str,
    trust_resolver: CatalogEvidenceResolver | None = None,
) -> _NumericSource:
    area_value = getattr(candidate.ski_area, metric)
    sources: list[tuple[float, str, str, str]] = []
    if area_value is not None:
        sources.append(
            (
                float(area_value),
                "ski_areas",
                candidate.ski_area.ski_area_id,
                "terrain_metrics",
            )
        )
    for domain in candidate.terrain_domains:
        value = getattr(domain, metric)
        if candidate.ski_area.ski_area_id in domain.ski_area_ids and value is not None:
            sources.append(
                (
                    float(value),
                    "terrain_domains",
                    domain.terrain_domain_id,
                    "aggregate_terrain",
                )
            )
    if not sources:
        return _NumericSource(
            value=None,
            scope="ski_area_or_terrain_domain",
            entity_ids=(candidate.ski_area.ski_area_id,),
            entity_type=None,
            entity_id=None,
            field_group=None,
            warnings=(f"{metric} unresolved",),
        )
    if trust_resolver is not None:
        sources = [
            item
            for item in sources
            if trust_resolver.resolve(item[1], item[2], item[3]).cap > 0
        ]
    if not sources:
        return _NumericSource(
            value=None,
            scope="ski_area_or_terrain_domain",
            entity_ids=(candidate.ski_area.ski_area_id,),
            entity_type=None,
            entity_id=None,
            field_group=None,
            warnings=(f"{metric} lacks source-backed evidence",),
        )
    value, entity_type, entity_id, field_group = max(sources)
    return _NumericSource(
        value=value,
        scope="ski_area_or_terrain_domain",
        entity_ids=(candidate.ski_area.ski_area_id, entity_id),
        entity_type=entity_type,
        entity_id=entity_id,
        field_group=field_group,
    )


def _pass_numeric_source(
    candidate: StaticFactorCandidate, value: float | None
) -> _NumericSource:
    return _NumericSource(
        value=value,
        scope="pass_trip_duration",
        entity_ids=(candidate.selected_pass.lift_pass_product_id,),
        entity_type="lift_pass_products",
        entity_id=candidate.selected_pass.lift_pass_product_id,
        field_group="prices",
        warnings=("comparable price unavailable",) if value is None else (),
    )


def _matching_price_slice(
    context: StaticEvaluationContext, product: LiftPassProduct
) -> _PriceSlice | None:
    return _matching_price_slice_values(
        product=product,
        duration_days=context.pass_duration_days,
        audience=context.pass_audience,
        season_label=context.pass_season_label,
    )


def _matching_price_slice_values(
    *,
    product: LiftPassProduct,
    duration_days: int,
    audience: str,
    season_label: str | None,
) -> _PriceSlice | None:
    price = select_matching_pass_price(
        product=product,
        duration_days=duration_days,
        audience=audience,
        season_label=season_label,
    )
    if price is None:
        return None
    if price.price_kind == "range":
        assert price.amount_max is not None
        return _PriceSlice(
            amount=price.amount_max,
            currency=price.currency.upper(),
            evidence_shape_cap=0.8,
            price_kind=price.price_kind,
        )
    if price.price_kind in {"fixed", "from"}:
        assert price.amount is not None
        return _PriceSlice(
            amount=price.amount,
            currency=price.currency.upper(),
            evidence_shape_cap=1 if price.price_kind == "fixed" else 0.5,
            price_kind=price.price_kind,
        )
    return None


def select_matching_pass_price(
    *,
    product: LiftPassProduct,
    duration_days: int,
    audience: str,
    season_label: str | None,
) -> CatalogLiftPassPrice | None:
    """Select one comparable price without guessing between season slices."""

    matches = [
        price
        for price in product.prices
        if price.duration_days == duration_days
        and _same_text(price.audience, audience)
        and (
            season_label is None
            or (
                price.season_label is not None
                and _same_text(price.season_label, season_label)
            )
        )
    ]
    if not matches:
        return None
    if season_label is None and len({_price_signature(item) for item in matches}) > 1:
        return None
    return matches[0]


def _price_signature(price: CatalogLiftPassPrice) -> tuple[object, ...]:
    return (
        price.currency.upper(),
        price.price_kind,
        price.amount,
        price.amount_min,
        price.amount_max,
    )


def _numeric_bounds_evidence_cap(
    *,
    factor_id: str,
    candidate: StaticFactorCandidate,
    pass_duration_days: int,
    pass_audience: str,
    pass_season_label: str | None,
    trust_resolver: CatalogEvidenceResolver,
) -> float:
    if factor_id == "travel_effort":
        return candidate.travel_evidence_cap
    if factor_id == "accessible_terrain_scale":
        return _source_evidence_for_resolver(
            trust_resolver,
            _accessible_terrain_source(candidate, trust_resolver),
        ).cap
    if factor_id in {"terrain_potential_scale", "lift_network_scale"}:
        metric = (
            "total_piste_km"
            if factor_id == "terrain_potential_scale"
            else "total_lift_count"
        )
        return _source_evidence_for_resolver(
            trust_resolver,
            _terrain_potential_source(
                candidate,
                metric=metric,
                trust_resolver=trust_resolver,
            ),
        ).cap
    price = _matching_price_slice_values(
        product=candidate.selected_pass,
        duration_days=pass_duration_days,
        audience=pass_audience,
        season_label=pass_season_label,
    )
    if price is None:
        return 0
    price_cap = (
        trust_resolver.resolve(
            "lift_pass_products",
            candidate.selected_pass.lift_pass_product_id,
            "prices",
        ).cap
        * price.evidence_shape_cap
    )
    if factor_id == "pass_price_per_day":
        return price_cap
    if factor_id == "pass_terrain_value":
        terrain_cap = _source_evidence_for_resolver(
            trust_resolver,
            _accessible_terrain_source(candidate, trust_resolver),
        ).cap
        return min(price_cap, terrain_cap)
    raise KeyError(factor_id)


def _requested_values(intent: SearchIntent, factor_id: str) -> tuple[str, ...]:
    for preference in intent.factor_preferences:
        if preference.factor_id == factor_id:
            return preference.values
    return ()


def _catalog_evidence(
    context: StaticEvaluationContext,
    entity_type: str,
    entity_id: str,
    field_group: str,
) -> ResolvedCatalogEvidence:
    return context.trust_resolver.resolve(entity_type, entity_id, field_group)


def _source_evidence(
    context: StaticEvaluationContext, source: _NumericSource
) -> ResolvedCatalogEvidence:
    return _source_evidence_for_resolver(context.trust_resolver, source)


def _source_evidence_for_resolver(
    resolver: CatalogEvidenceResolver,
    source: _NumericSource,
) -> ResolvedCatalogEvidence:
    if (
        source.entity_type is None
        or source.entity_id is None
        or source.field_group is None
    ):
        return ResolvedCatalogEvidence(status="needs_source", source_refs=())
    return resolver.resolve(
        source.entity_type,
        source.entity_id,
        source.field_group,
    )


def _make_evaluation(
    *,
    context: StaticEvaluationContext,
    factor_id: str,
    scope: str,
    entity_ids: tuple[str, ...],
    raw_value: object,
    raw_utility: float,
    evidence_cap: float,
    evidence: ResolvedCatalogEvidence,
    warnings: tuple[str, ...],
    explanation_inputs: Mapping[str, object],
) -> FactorEvaluation:
    return FactorEvaluation(
        factor_id=factor_id,
        scope=scope,
        entity_ids=entity_ids,
        raw_value=raw_value,
        raw_utility=raw_utility,
        neutral_utility=context.policy.factor(factor_id).neutral_utility,
        effective_evidence_cap=evidence_cap,
        evidence_cap_components={
            "catalog_status": evidence.status,
            "catalog_status_cap": evidence.cap,
            "source_count": len(evidence.source_refs),
        },
        warnings=warnings,
        provenance_summary=(
            f"Catalog field-group evidence: {evidence.status}; "
            f"{len(evidence.source_refs)} source reference(s)."
        ),
        explanation_inputs=explanation_inputs,
    )


def _weaker_status(
    left: CatalogTrustStatus, right: CatalogTrustStatus
) -> CatalogTrustStatus:
    order = {
        "needs_source": 0,
        "estimated": 1,
        "verified_with_adjustment": 2,
        "verified": 3,
    }
    return left if order[left] <= order[right] else right


def _same_text(left: str, right: str) -> bool:
    return left.strip().casefold() == right.strip().casefold()


_STATIC_EVALUATORS: Mapping[
    str,
    Callable[[StaticEvaluationContext, StaticFactorCandidate], FactorEvaluation],
] = {
    "party_skill_coverage": _party_skill_coverage,
    "accessible_terrain_scale": _accessible_terrain_scale,
    "terrain_potential_scale": _terrain_potential_scale,
    "lift_network_scale": _lift_network_scale,
    "marked_freeride_routes": _marked_freeride_routes,
    "snow_park": _snow_park,
    "night_skiing": _night_skiing,
    "glacier_terrain": _glacier_terrain,
    "snowmaking_availability": _snowmaking_availability,
    "stay_base_access": _stay_base_access,
    "lodging_budget_fit": _lodging_budget_fit,
    "pass_price_per_day": _pass_price_per_day,
    "pass_terrain_value": _pass_terrain_value,
    "ski_day_apres": _ski_day_apres,
    "local_apres": _local_apres,
    "local_pace": _local_pace,
    "development_style": _development_style,
    "base_type": _base_type,
    "travel_effort": _travel_effort,
}
