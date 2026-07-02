from __future__ import annotations

import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Protocol

from app.data.catalog_repository import CatalogRepository
from app.data.repositories import (
    get_condition_history_repository,
    get_raw_weather_history_repository,
    get_snow_climatology_repository,
)
from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_graph import CatalogGraph
from app.domain.models import (
    ConfidenceContributor,
    ExplanationItem,
    SearchExplanation,
    SearchFilters,
    TravelEffort,
)
from app.domain.pass_selection import select_pass
from app.domain.ranking import availability_penalty, quality_score
from app.domain.resort_fit import (
    ResortFitFactor,
    ski_area_access_factor,
    skill_fit_factor_for_ski_area,
    terrain_scale_factor_for_catalog_area,
)
from app.domain.search_evidence import (
    ConditionHistoryProtocol,
    ConditionsProviderProtocol,
    RawWeatherHistoryProtocol,
    SkiAreaPlanningContext,
    SnowClimatologyProtocol,
    load_planning_contexts,
)
from app.domain.search_v3_candidates import (
    TripConfigurationSeed,
    generate_candidate_seeds,
)
from app.domain.search_v3_models import (
    AccessSummary,
    AreaResilienceItem,
    PassOption,
    RecommendationGroup,
    ResilienceSummary,
    TripConfiguration,
)
from app.domain.search_v3_scoring import (
    SearchV3ScoreInputs,
    active_factor_cap,
    score_search_v3_configuration,
)
from app.domain.travel import (
    TravelCacheProtocol,
    assess_deterministic_travel_effort,
    assess_travel_effort,
)
from app.integrations.conditions import get_conditions_provider
from app.observability.search import (
    record_search_v3_completed,
    search_phase,
    search_span,
)

MAX_ALTERNATIVE_CONFIGURATIONS = 3


class CatalogSnapshotRepository(Protocol):
    def get_snapshot(self) -> CatalogSnapshot: ...


def search_trip_markets(
    filters: SearchFilters,
    *,
    catalog_repository: CatalogSnapshotRepository | None = None,
    conditions_provider: ConditionsProviderProtocol | None = None,
    condition_history_repository: ConditionHistoryProtocol | None = None,
    raw_weather_history_repository: RawWeatherHistoryProtocol | None = None,
    snow_climatology_repository: SnowClimatologyProtocol | None = None,
    travel_cache_repository: TravelCacheProtocol | None = None,
) -> list[RecommendationGroup]:
    started_at = time.perf_counter()
    repository = catalog_repository or CatalogRepository()
    graph = CatalogGraph.from_snapshot(repository.get_snapshot())
    with search_span(filters) as span:
        with search_phase("generate_v3_candidates", filters):
            seeds = generate_candidate_seeds(graph, filters)
        contexts = load_planning_contexts(
            ski_areas=tuple(seed.ski_area for seed in seeds),
            filters=filters,
            conditions_provider=conditions_provider or get_conditions_provider(),
            condition_history_repository=(
                condition_history_repository or get_condition_history_repository()
            ),
            raw_weather_history_repository=(
                raw_weather_history_repository or get_raw_weather_history_repository()
            ),
            snow_climatology_repository=(
                snow_climatology_repository or get_snow_climatology_repository()
            ),
        )
        travel_efforts = _travel_efforts_by_destination(
            seeds=seeds,
            filters=filters,
            travel_cache_repository=travel_cache_repository,
        )
        with search_phase("build_v3_configurations", filters):
            configurations = tuple(
                configuration
                for seed in seeds
                if (
                    configuration := _build_trip_configuration(
                        seed=seed,
                        graph=graph,
                        filters=filters,
                        planning_contexts=contexts,
                        travel_effort=travel_efforts[
                            seed.stay_destination.stay_destination_id
                        ],
                    )
                )
                is not None
            )
        with search_phase("group_v3_trip_markets", filters):
            groups = _rank_and_group_configurations(configurations, graph)
        record_search_v3_completed(
            filters=filters,
            candidate_seed_count=len(seeds),
            configuration_count=len(configurations),
            result_count=len(groups),
            evidence_profile_counts=_evidence_profile_counts(contexts),
            duration_seconds=time.perf_counter() - started_at,
            span=span,
        )
        return groups


def _travel_efforts_by_destination(
    *,
    seeds: tuple[TripConfigurationSeed, ...],
    filters: SearchFilters,
    travel_cache_repository: TravelCacheProtocol | None,
) -> dict[str, TravelEffort | None]:
    destinations = {
        seed.stay_destination.stay_destination_id: seed.stay_destination
        for seed in seeds
    }
    if not filters.origin_text:
        return {destination_id: None for destination_id in destinations}
    efforts: dict[str, TravelEffort | None] = {}
    for destination_id, destination in destinations.items():
        if travel_cache_repository is None:
            effort = assess_deterministic_travel_effort(
                filters.origin_text,
                destination,
                filters.max_drive_minutes,
                filters.travel_tolerance,
            )
        else:
            effort = assess_travel_effort(
                filters.origin_text,
                destination,
                travel_cache_repository,
                filters.max_drive_minutes,
                filters.travel_tolerance,
            )
        efforts[destination_id] = effort
    return efforts


def _build_trip_configuration(
    *,
    seed: TripConfigurationSeed,
    graph: CatalogGraph,
    filters: SearchFilters,
    planning_contexts: Mapping[str, SkiAreaPlanningContext],
    travel_effort: TravelEffort | None,
) -> TripConfiguration | None:
    context = planning_contexts[seed.ski_area.ski_area_id]
    if availability_penalty(context.conditions.availability_status) is None:
        return None
    if travel_effort is not None and travel_effort.exceeds_max_drive:
        return None
    pass_selection = select_pass(
        products=seed.candidate_passes,
        graph=graph,
        stay_destination_id=seed.stay_destination.stay_destination_id,
        focus_ski_area_id=seed.ski_area.ski_area_id,
        trip_start_date=filters.trip_start_date,
        trip_end_date=filters.trip_end_date,
    )
    terrain_factor = terrain_scale_factor_for_catalog_area(
        seed.ski_area,
        graph.snapshot.terrain_domains,
    )
    skill_factor = skill_fit_factor_for_ski_area(seed.ski_area)
    access_factor = ski_area_access_factor(seed.access)
    score = score_search_v3_configuration(
        SearchV3ScoreInputs(
            lodging_quality=quality_score(seed.stay_base.quality),
            terrain_scale=_factor_string(terrain_factor),
            terrain_trust_cap=_factor_cap(terrain_factor),
            skill_fit=_factor_tuple(skill_factor),
            skill_trust_cap=_factor_cap(skill_factor),
            access_fit=_factor_string(access_factor),
            access_trust_cap=_factor_cap(access_factor),
            snow_confidence_score=context.conditions.snow_confidence_score,
            conditions_score=context.conditions.conditions_score,
            budget_penalty=seed.budget_penalty,
            travel_effort_score=(travel_effort.score if travel_effort else None),
        )
    )
    return TripConfiguration(
        configuration_id=seed.access.ski_area_access_id,
        ski_region_id=seed.region.ski_region_id,
        stay_destination_id=seed.stay_destination.stay_destination_id,
        stay_destination_name=seed.stay_destination.name,
        stay_base_id=seed.stay_base.stay_base_id,
        stay_base_name=seed.stay_base.name,
        focus_ski_area_id=seed.ski_area.ski_area_id,
        focus_ski_area_name=seed.ski_area.name,
        access=AccessSummary(
            ski_area_access_id=seed.access.ski_area_access_id,
            mode=seed.access.access_mode,
            lift_distance=seed.access.lift_distance,
            nearest_lift_name=seed.access.nearest_lift_name,
            distance_m=seed.access.distance_m,
            duration_minutes=seed.access.duration_minutes,
            is_direct=seed.access.is_direct,
        ),
        selected_pass=pass_selection.selected,
        alternative_passes=list(pass_selection.alternatives),
        resilience=build_resilience_summary(
            selected_pass=pass_selection.selected,
            focus_ski_area_id=seed.ski_area.ski_area_id,
            graph=graph,
            planning_contexts=planning_contexts,
        ),
        score=score.total,
        score_components=dict(score.components),
        budget_penalty=seed.budget_penalty,
        travel_effort=travel_effort,
        conditions_summary=context.conditions.weather_summary,
        snow_confidence_score=context.conditions.snow_confidence_score,
        conditions_score=context.conditions.conditions_score,
        planning_summary=context.planning_summary,
        planning_provenance=context.planning_provenance,
        planning_evidence_count=context.planning_evidence_count,
        planning_weather_metrics=context.planning_weather_metrics,
        evidence_quality=context.conditions_provenance,
        explanation=_build_explanation(seed, context, travel_effort),
    )


def build_resilience_summary(
    *,
    selected_pass: PassOption,
    focus_ski_area_id: str,
    graph: CatalogGraph,
    planning_contexts: Mapping[str, SkiAreaPlanningContext],
) -> ResilienceSummary:
    items = [
        AreaResilienceItem(
            ski_area_id=area_id,
            ski_area_name=graph.areas_by_id[area_id].name,
            evidence_profile=(
                planning_contexts[area_id].planning_provenance.evidence_profile
                if planning_contexts[area_id].planning_provenance is not None
                else None
            ),
            evidence_seasons=planning_contexts[area_id].planning_evidence_count,
            conditions_summary=planning_contexts[area_id].conditions.weather_summary,
        )
        for area_id in selected_pass.accessible_ski_area_ids
        if area_id != focus_ski_area_id and area_id in planning_contexts
    ]
    alternative_count = max(len(selected_pass.accessible_ski_area_ids) - 1, 0)
    evidenced_count = sum(
        item.evidence_seasons is not None and item.evidence_seasons > 0
        for item in items
    )
    if alternative_count == 0:
        summary = "No alternative modeled ski areas on this pass."
    elif items:
        summary = f"{alternative_count} alternative modeled ski area(s) on this pass."
    else:
        summary = (
            f"{alternative_count} alternative modeled ski area(s); "
            "member evidence is unavailable."
        )
    return ResilienceSummary(
        alternative_area_count=alternative_count,
        evidenced_alternative_count=evidenced_count,
        areas=items[:4],
        summary=summary,
        ranking_component=0,
    )


def _build_explanation(
    seed: TripConfigurationSeed,
    context: SkiAreaPlanningContext,
    travel_effort: TravelEffort | None,
) -> SearchExplanation:
    highlights = [
        ExplanationItem(
            label=f"{seed.ski_area.name} supports the requested skill level."
        ),
        ExplanationItem(
            label=f"Access from {seed.stay_base.name} is modeled directly."
        ),
    ]
    risks: list[ExplanationItem] = []
    contributors = [
        ConfidenceContributor(
            label="The selected stay and ski area have an explicit access link.",
            direction="positive",
        )
    ]
    if context.conditions.snow_confidence_label == "poor":
        risks.append(ExplanationItem(label="Snow confidence is poor for this window."))
        contributors.append(
            ConfidenceContributor(
                label="Weak snow outlook lowers recommendation confidence.",
                direction="negative",
            )
        )
    else:
        highlights.append(
            ExplanationItem(
                label=(
                    f"Snow confidence is {context.conditions.snow_confidence_label}."
                )
            )
        )
    if seed.budget_penalty > 0:
        risks.append(ExplanationItem(label="The stay requires the budget tolerance."))
    if travel_effort is not None:
        target = (
            highlights if travel_effort.effort_label in {"easy", "moderate"} else risks
        )
        target.append(ExplanationItem(label=travel_effort.summary))
    return SearchExplanation(
        highlights=highlights,
        risks=risks,
        confidence_contributors=contributors,
    )


def _rank_and_group_configurations(
    configurations: tuple[TripConfiguration, ...],
    graph: CatalogGraph,
) -> list[RecommendationGroup]:
    grouped: dict[str, list[TripConfiguration]] = defaultdict(list)
    for configuration in configurations:
        grouped[configuration.ski_region_id].append(configuration)
    ordered_groups = sorted(
        (
            (region_id, sorted(items, key=_configuration_sort_key))
            for region_id, items in grouped.items()
        ),
        key=lambda item: (_configuration_sort_key(item[1][0]), item[0]),
    )
    return [
        RecommendationGroup(
            ski_region_id=region_id,
            ski_region_name=graph.regions_by_id[region_id].name,
            rank=rank,
            score=items[0].score,
            top_configuration=items[0],
            alternative_configurations=items[1 : 1 + MAX_ALTERNATIVE_CONFIGURATIONS],
        )
        for rank, (region_id, items) in enumerate(ordered_groups, start=1)
    ]


def _configuration_sort_key(
    configuration: TripConfiguration,
) -> tuple[float, float, str, str, str]:
    return (
        -configuration.score,
        -configuration.snow_confidence_score,
        configuration.stay_destination_id,
        configuration.stay_base_id,
        configuration.focus_ski_area_id,
    )


def _factor_cap(factor: ResortFitFactor) -> float:
    return active_factor_cap(factor.lifecycle_state, factor.ranking_cap)


def _factor_string(factor: ResortFitFactor) -> str | None:
    return factor.value if isinstance(factor.value, str) else None


def _factor_tuple(factor: ResortFitFactor) -> tuple[str, ...]:
    if isinstance(factor.value, tuple):
        return tuple(str(value) for value in factor.value)
    if isinstance(factor.value, str):
        return (factor.value,)
    return ()


def _evidence_profile_counts(
    contexts: Mapping[str, SkiAreaPlanningContext],
) -> dict[str, int]:
    return dict(
        Counter(
            (
                context.planning_provenance.evidence_profile
                if context.planning_provenance is not None
                else "current_only"
            )
            or "current_only"
            for context in contexts.values()
        )
    )
