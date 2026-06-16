import re
import time
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

from app.data.repositories import (
    get_condition_history_repository,
    get_raw_weather_history_repository,
    get_resort_repository,
    get_snow_climatology_repository,
    is_condition_fresh,
)
from app.domain.models import (
    ConfidenceContributor,
    Destination,
    ExplanationItem,
    ProvenanceInfo,
    Rental,
    ResortConditions,
    SearchExplanation,
    SearchFilters,
    SearchResult,
    SkiArea,
    SnowClimatologyBaselinePeriod,
    SnowClimatologyDaily,
    StayBase,
    TravelEffort,
    TripOption,
    WeatherElevationBand,
    WeatherEvidenceMetrics,
)
from app.domain.planning import (
    derive_climatology_weather_evidence_metrics,
    derive_planning_assessment,
    derive_weather_evidence_metrics,
)
from app.domain.planning_policy import DEFAULT_PLANNING_HEURISTIC_POLICY
from app.domain.ranking import (
    availability_penalty,
    budget_range_penalty,
    lift_distance_matches,
    lift_distance_score,
    quality_score,
    skill_fit_score,
    skill_level_matches,
    stay_base_budget_price,
)
from app.domain.travel import (
    TravelCacheProtocol,
    assess_deterministic_travel_effort,
    assess_travel_effort,
)
from app.integrations.conditions import get_conditions_provider
from app.observability.search import (
    record_search_completed,
    search_phase,
    search_span,
)

POLICY = DEFAULT_PLANNING_HEURISTIC_POLICY
MAX_ALTERNATIVE_OPTIONS = 3
MIN_ALTERNATIVE_SCORE_DELTA = 0.03
DEFAULT_PLANNING_WEATHER_BANDS: tuple[WeatherElevationBand, ...] = ("mid",)
DEFAULT_CLIMATOLOGY_BASELINE_PERIODS: tuple[
    SnowClimatologyBaselinePeriod,
    ...,
] = ("normal_30y", "recent_15y")
RawWeatherCache = dict[tuple[str, str], tuple]
SnowClimatologyCache = dict[
    tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod],
    tuple[SnowClimatologyDaily, ...],
]
PlanningSnapshotCache = dict[str, tuple]


@dataclass(frozen=True)
class _SkiAreaPlanningContext:
    conditions: ResortConditions | None
    conditions_provenance: ProvenanceInfo
    planning_summary: str | None
    planning_provenance: ProvenanceInfo | None
    planning_evidence_count: int | None
    planning_weather_metrics: WeatherEvidenceMetrics | None
    best_travel_months: tuple[int, ...]


def build_accommodation_link(*, resort_name: str, country: str) -> str:
    query = urlencode(
        {
            "ss": f"{resort_name}, {country}",
            "group_adults": 2,
            "no_rooms": 1,
            "group_children": 0,
        }
    )
    return f"https://www.booking.com/searchresults.html?{query}"


def _fallback_conditions(resort_name: str) -> ResortConditions:
    return ResortConditions(
        resort_name=resort_name,
        snow_confidence_score=0.4,
        availability_status="limited",
        weather_summary="No live conditions signal available for this ski area.",
        conditions_score=0.4,
    )


def _build_conditions_provenance(
    conditions: ResortConditions | None,
) -> ProvenanceInfo:
    if conditions is None or (
        conditions.updated_at is None and conditions.source is None
    ):
        return ProvenanceInfo(
            source_name=None,
            source_type="estimated",
            updated_at=None,
            freshness_status="unknown",
            basis_summary=(
                "Using an estimated fallback because no live forecast signal is "
                "available for this resort."
            ),
        )

    freshness_status = "unknown"
    if conditions.updated_at is not None:
        freshness_status = "fresh" if is_condition_fresh(conditions) else "stale"

    return ProvenanceInfo(
        source_name=conditions.source or "open-meteo",
        source_type="forecast",
        updated_at=conditions.updated_at,
        freshness_status=freshness_status,
        basis_summary=(
            "Using a current forecast-based conditions signal from the latest "
            "weather refresh."
        ),
    )


def _build_planning_provenance(
    *,
    evidence_count: int,
    latest_snapshot_at: str | None,
    evidence_source: str,
    evidence_profile: str,
) -> ProvenanceInfo:
    text_policy = POLICY.text
    if evidence_profile == "forecast_assisted":
        profile_text = text_policy.forecast_assisted
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary
    elif evidence_profile == "archive_backed":
        profile_text = text_policy.archive_backed
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary
    elif evidence_source == "snapshot_history":
        source_name = text_policy.snapshot_fallback_source_name
        basis_summary = text_policy.snapshot_fallback_provenance_summary
    else:
        profile_text = text_policy.fallback_heavy
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary
    if evidence_count > 0:
        return ProvenanceInfo(
            source_name=source_name,
            source_type="estimated",
            updated_at=latest_snapshot_at,
            freshness_status="historical",
            basis_summary=basis_summary,
            evidence_profile=evidence_profile,
        )

    return ProvenanceInfo(
        source_name=source_name,
        source_type="estimated",
        updated_at=None,
        freshness_status="unknown",
        basis_summary=basis_summary,
        evidence_profile=evidence_profile,
    )


def _build_explanation(
    *,
    stay_base: StayBase,
    ski_area: SkiArea,
    filters: SearchFilters,
    penalty: float,
    conditions: ResortConditions,
    travel_effort: TravelEffort | None = None,
) -> SearchExplanation:
    quality_label = {
        1: "budget",
        2: "standard",
        3: "premium",
    }[filters.stars]
    highlights = [
        ExplanationItem(
            label=f"{stay_base.name} supports {filters.skill_level} skiers."
        ),
        ExplanationItem(
            label=(f"Stay-base quality clears the requested {quality_label} tier.")
        ),
    ]
    risks: list[ExplanationItem] = []
    confidence_contributors = [
        ConfidenceContributor(
            label=(
                f"Skill match is strong for the requested {filters.skill_level} level."
            ),
            direction="positive",
        ),
    ]

    if conditions.snow_confidence_label == "good":
        highlights.append(
            ExplanationItem(
                label=f"{ski_area.name} has good snow confidence for this trip window."
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Snow outlook is strong for the selected ski area.",
                direction="positive",
            )
        )
    elif conditions.snow_confidence_label == "fair":
        highlights.append(
            ExplanationItem(
                label=f"{ski_area.name} has fair snow confidence for this trip window."
            )
        )
    else:
        risks.append(
            ExplanationItem(
                label=f"{ski_area.name} has poor snow confidence for this trip window."
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Weak snow outlook reduces recommendation certainty.",
                direction="negative",
            )
        )

    if penalty > 0:
        risks.append(
            ExplanationItem(
                label=(
                    "Stay-base nightly estimate is slightly outside the requested "
                    "budget."
                )
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label=(
                    "Budget stretch lowers certainty that this is the best-fit option."
                ),
                direction="negative",
            )
        )

    if conditions.availability_status == "limited":
        risks.append(
            ExplanationItem(
                label="Weather signal suggests some disruption risk right now."
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Weather disruption risk reduces recommendation certainty.",
                direction="negative",
            )
        )
    elif conditions.availability_status == "temporarily_closed":
        risks.append(
            ExplanationItem(
                label=("Weather signal suggests high disruption risk right now.")
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label=(
                    "High disruption risk materially lowers recommendation certainty."
                ),
                direction="negative",
            )
        )
    elif conditions.availability_status == "out_of_season":
        risks.append(
            ExplanationItem(label="Resort is outside its typical ski season window.")
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label=(
                    "Out-of-season timing materially lowers recommendation certainty."
                ),
                direction="negative",
            )
        )

    if stay_base.lift_distance == "near":
        highlights.append(
            ExplanationItem(label="Selected stay base keeps you close to the lift.")
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Near-lift access improves practical fit for the trip.",
                direction="positive",
            )
        )

    if travel_effort is not None:
        travel_item = ExplanationItem(label=travel_effort.summary)
        if travel_effort.effort_label in {"easy", "moderate"}:
            highlights.append(travel_item)
            confidence_contributors.append(
                ConfidenceContributor(
                    label="Drive effort is compatible with the requested trip.",
                    direction="positive",
                )
            )
        else:
            risks.append(travel_item)
            confidence_contributors.append(
                ConfidenceContributor(
                    label="Longer drive effort lowers practical trip fit.",
                    direction="negative",
                )
            )

    return SearchExplanation(
        highlights=highlights,
        risks=risks,
        confidence_contributors=confidence_contributors,
    )


def _list_planning_snapshots(
    *,
    history_repository,
    planning_snapshot_cache: PlanningSnapshotCache,
    destination: Destination,
    ski_area: SkiArea,
) -> tuple:
    snapshots = _cached_planning_snapshots(
        history_repository=history_repository,
        planning_snapshot_cache=planning_snapshot_cache,
        resort_id=ski_area.ski_area_id,
    )
    if snapshots or ski_area.ski_area_id == destination.resort_id:
        return snapshots
    return _cached_planning_snapshots(
        history_repository=history_repository,
        planning_snapshot_cache=planning_snapshot_cache,
        resort_id=destination.resort_id,
    )


def _cached_planning_snapshots(
    *,
    history_repository,
    planning_snapshot_cache: PlanningSnapshotCache,
    resort_id: str,
) -> tuple:
    if resort_id not in planning_snapshot_cache:
        planning_snapshot_cache[resort_id] = (
            history_repository.list_snapshots_for_resort(resort_id)
        )
    return planning_snapshot_cache[resort_id]


def _preload_raw_weather_observations(
    *,
    raw_history_repository,
    resorts: tuple[Destination, ...],
    ski_area_ids: tuple[str, ...] | None = None,
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> RawWeatherCache:
    resort_ids = (
        ski_area_ids
        if ski_area_ids is not None
        else tuple(
            dict.fromkeys(
                ski_area.ski_area_id
                for resort in resorts
                for ski_area in resort.ski_areas
            )
        )
    )
    cache: RawWeatherCache = {}
    if not resort_ids:
        return cache

    window_batch_loader = getattr(
        raw_history_repository,
        "list_archive_observations_for_resorts_window",
        None,
    )
    if window_batch_loader is not None:
        grouped = window_batch_loader(
            resort_ids,
            elevation_bands=DEFAULT_PLANNING_WEATHER_BANDS,
            travel_month=travel_month,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
        )
        for resort_id in resort_ids:
            for elevation_band in DEFAULT_PLANNING_WEATHER_BANDS:
                cache[(resort_id, elevation_band)] = grouped.get(
                    (resort_id, elevation_band),
                    (),
                )
        return cache

    batch_loader = getattr(
        raw_history_repository,
        "list_observations_for_resorts",
        None,
    )
    if batch_loader is None:
        return cache

    grouped = batch_loader(
        resort_ids,
        elevation_bands=DEFAULT_PLANNING_WEATHER_BANDS,
    )
    for resort_id in resort_ids:
        for elevation_band in DEFAULT_PLANNING_WEATHER_BANDS:
            cache[(resort_id, elevation_band)] = grouped.get(
                (resort_id, elevation_band),
                (),
            )
    return cache


def _preload_snow_climatology(
    *,
    snow_climatology_repository,
    resorts: tuple[Destination, ...],
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> SnowClimatologyCache:
    ski_area_ids = tuple(
        dict.fromkeys(
            ski_area.ski_area_id
            for resort in resorts
            for ski_area in resort.ski_areas
        )
    )
    cache: SnowClimatologyCache = {}
    if not ski_area_ids:
        return cache

    loader = getattr(
        snow_climatology_repository,
        "list_daily_rows_for_resorts_window",
        None,
    )
    if loader is None:
        return cache

    grouped = loader(
        ski_area_ids,
        elevation_bands=DEFAULT_PLANNING_WEATHER_BANDS,
        baseline_periods=DEFAULT_CLIMATOLOGY_BASELINE_PERIODS,
        travel_month=travel_month,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
    )
    for ski_area_id in ski_area_ids:
        for elevation_band in DEFAULT_PLANNING_WEATHER_BANDS:
            for baseline_period in DEFAULT_CLIMATOLOGY_BASELINE_PERIODS:
                cache[(ski_area_id, elevation_band, baseline_period)] = grouped.get(
                    (ski_area_id, elevation_band, baseline_period),
                    (),
                )
    return cache


def _preload_planning_snapshots(
    *,
    history_repository,
    resort_ids: tuple[str, ...],
) -> PlanningSnapshotCache:
    resort_ids = tuple(dict.fromkeys(resort_ids))
    cache: PlanningSnapshotCache = {}
    if not resort_ids:
        return cache

    batch_loader = getattr(history_repository, "list_snapshots_for_resorts", None)
    if batch_loader is None:
        return cache

    grouped = batch_loader(resort_ids)
    for resort_id in resort_ids:
        cache[resort_id] = grouped.get(resort_id, ())
    return cache


def _has_preloaded_raw_weather(
    *,
    raw_weather_cache: RawWeatherCache,
    ski_area: SkiArea,
) -> bool:
    return any(
        raw_weather_cache.get((ski_area.ski_area_id, elevation_band))
        for elevation_band in DEFAULT_PLANNING_WEATHER_BANDS
    )


def _has_preloaded_snow_climatology(
    *,
    snow_climatology_cache: SnowClimatologyCache,
    ski_area: SkiArea,
) -> bool:
    return any(
        snow_climatology_cache.get((ski_area.ski_area_id, elevation_band, "normal_30y"))
        or snow_climatology_cache.get(
            (ski_area.ski_area_id, elevation_band, "recent_15y")
        )
        for elevation_band in DEFAULT_PLANNING_WEATHER_BANDS
    )


def _list_snow_climatology_rows(
    *,
    snow_climatology_cache: SnowClimatologyCache,
    ski_area: SkiArea,
) -> tuple[SnowClimatologyDaily, ...]:
    for elevation_band in DEFAULT_PLANNING_WEATHER_BANDS:
        normal_rows = snow_climatology_cache.get(
            (ski_area.ski_area_id, elevation_band, "normal_30y"),
            (),
        )
        recent_rows = snow_climatology_cache.get(
            (ski_area.ski_area_id, elevation_band, "recent_15y"),
            (),
        )
        rows = (*normal_rows, *recent_rows)
        if rows:
            return rows
    return ()


def _cached_raw_weather_observations_for_resort(
    *,
    raw_history_repository,
    raw_weather_cache: RawWeatherCache,
    resort_id: str,
    elevation_band: str,
) -> tuple:
    key = (resort_id, elevation_band)
    if key not in raw_weather_cache:
        raw_weather_cache[key] = raw_history_repository.list_observations_for_resort(
            resort_id,
            elevation_band=elevation_band,
        )
    return raw_weather_cache[key]


def _list_raw_weather_observations(
    *,
    raw_history_repository,
    raw_weather_cache: RawWeatherCache,
    destination: Destination,
    ski_area: SkiArea,
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> tuple:
    for elevation_band in DEFAULT_PLANNING_WEATHER_BANDS:
        observations = _list_raw_weather_observations_for_band(
            raw_history_repository=raw_history_repository,
            raw_weather_cache=raw_weather_cache,
            destination=destination,
            ski_area=ski_area,
            elevation_band=elevation_band,
        )
        if _has_archive_observations_for_window(
            observations,
            travel_month=travel_month,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
        ):
            return observations

    return ()


def _list_raw_weather_observations_for_band(
    *,
    raw_history_repository,
    raw_weather_cache: RawWeatherCache,
    destination: Destination,
    ski_area: SkiArea,
    elevation_band: str,
) -> tuple:
    observations = _cached_raw_weather_observations_for_resort(
        raw_history_repository=raw_history_repository,
        raw_weather_cache=raw_weather_cache,
        resort_id=ski_area.ski_area_id,
        elevation_band=elevation_band,
    )
    if observations or ski_area.ski_area_id == destination.resort_id:
        return observations
    return _cached_raw_weather_observations_for_resort(
        raw_history_repository=raw_history_repository,
        raw_weather_cache=raw_weather_cache,
        resort_id=destination.resort_id,
        elevation_band=elevation_band,
    )


def _has_archive_observations_for_window(
    observations: tuple,
    *,
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> bool:
    for observation in observations:
        if observation.record_type != "archive":
            continue
        observed_on = date.fromisoformat(observation.observed_on)
        if trip_start_date is not None and trip_end_date is not None:
            if _matches_month_day_window(
                observed_on=observed_on,
                trip_start_date=trip_start_date,
                trip_end_date=trip_end_date,
            ):
                return True
        elif travel_month is not None and observed_on.month == travel_month:
            return True
    return False


def _matches_month_day_window(
    *,
    observed_on: date,
    trip_start_date: date,
    trip_end_date: date,
) -> bool:
    normalized_observed = date(2000, observed_on.month, observed_on.day)
    normalized_start = date(2000, trip_start_date.month, trip_start_date.day)
    normalized_end = date(2000, trip_end_date.month, trip_end_date.day)
    if normalized_start <= normalized_end:
        return normalized_start <= normalized_observed <= normalized_end
    return (
        normalized_observed >= normalized_start or normalized_observed <= normalized_end
    )


def _build_ski_area_planning_context(
    *,
    filters: SearchFilters,
    conditions_provider,
    history_repository,
    raw_history_repository,
    raw_weather_cache: RawWeatherCache,
    snow_climatology_cache: SnowClimatologyCache,
    planning_snapshot_cache: PlanningSnapshotCache,
    destination: Destination,
    ski_area: SkiArea,
) -> _SkiAreaPlanningContext:
    current_conditions = conditions_provider.get_conditions_for_resort(ski_area.name)
    conditions_provenance = _build_conditions_provenance(current_conditions)
    planning_summary: str | None = None
    planning_provenance: ProvenanceInfo | None = None
    planning_evidence_count: int | None = None
    planning_weather_metrics: WeatherEvidenceMetrics | None = None
    best_travel_months: tuple[int, ...] = ()

    if filters.travel_month is not None or (
        filters.trip_start_date is not None and filters.trip_end_date is not None
    ):
        snow_climatology_rows = _list_snow_climatology_rows(
            snow_climatology_cache=snow_climatology_cache,
            ski_area=ski_area,
        )
        raw_weather_observations = (
            ()
            if snow_climatology_rows
            else _list_raw_weather_observations(
                raw_history_repository=raw_history_repository,
                raw_weather_cache=raw_weather_cache,
                destination=destination,
                ski_area=ski_area,
                travel_month=filters.travel_month,
                trip_start_date=filters.trip_start_date,
                trip_end_date=filters.trip_end_date,
            )
        )
        snapshots = (
            ()
            if raw_weather_observations or snow_climatology_rows
            else _list_planning_snapshots(
                history_repository=history_repository,
                planning_snapshot_cache=planning_snapshot_cache,
                destination=destination,
                ski_area=ski_area,
            )
        )
        planning = derive_planning_assessment(
            resort=ski_area,
            travel_month=filters.travel_month,
            snapshots=snapshots,
            raw_weather_observations=raw_weather_observations,
            snow_climatology_rows=snow_climatology_rows,
            current_conditions=current_conditions,
            trip_start_date=filters.trip_start_date,
            trip_end_date=filters.trip_end_date,
        )
        conditions = planning.conditions
        planning_summary = planning.planning_summary
        planning_evidence_count = planning.evidence_count
        best_travel_months = planning.best_travel_months
        planning_provenance = _build_planning_provenance(
            evidence_count=planning.evidence_count,
            latest_snapshot_at=planning.latest_snapshot_at,
            evidence_source=planning.evidence_source,
            evidence_profile=planning.evidence_profile,
        )
        planning_weather_metrics = (
            derive_climatology_weather_evidence_metrics(
                snow_climatology_rows=snow_climatology_rows,
                travel_month=filters.travel_month,
                trip_start_date=filters.trip_start_date,
                trip_end_date=filters.trip_end_date,
            )
            if snow_climatology_rows
            else derive_weather_evidence_metrics(
                raw_weather_observations=raw_weather_observations,
                travel_month=filters.travel_month,
                trip_start_date=filters.trip_start_date,
                trip_end_date=filters.trip_end_date,
            )
        )
    else:
        conditions = current_conditions

    return _SkiAreaPlanningContext(
        conditions=conditions,
        conditions_provenance=conditions_provenance,
        planning_summary=planning_summary,
        planning_provenance=planning_provenance,
        planning_evidence_count=planning_evidence_count,
        planning_weather_metrics=planning_weather_metrics,
        best_travel_months=best_travel_months,
    )


def _slug_part(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "option"


def _trip_option_id(result: SearchResult) -> str:
    return "--".join(
        (
            _slug_part(result.resort_id),
            _slug_part(result.selected_ski_area_id),
            _slug_part(result.selected_stay_base_name),
        )
    )


def _trip_option_tradeoff_summary(result: SearchResult) -> str:
    lift_text = {
        "near": "near lift access",
        "medium": "medium lift distance",
        "far": "farther from lifts",
    }[result.selected_stay_base_lift_distance]
    if result.budget_penalty > 0:
        budget_text = f"budget penalty {result.budget_penalty:.2f}"
    else:
        budget_text = "within budget"

    parts = [lift_text, budget_text]
    if result.travel_effort is not None:
        parts.append(f"{result.travel_effort.effort_label} travel effort")
    return "; ".join(parts) + "."


def _trip_option_from_result(result: SearchResult) -> TripOption:
    return TripOption(
        option_id=_trip_option_id(result),
        ski_area_id=result.selected_ski_area_id,
        ski_area_name=result.selected_ski_area_name,
        stay_base_name=result.selected_stay_base_name,
        stay_base_lift_distance=result.selected_stay_base_lift_distance,
        stay_base_price_range=result.stay_base_price_range,
        rental_name=result.rental_name,
        rental_price_range=result.rental_price_range,
        rating_estimate=result.rating_estimate,
        score=result.score,
        recommendation_confidence=result.recommendation_confidence,
        budget_penalty=result.budget_penalty,
        travel_effort=result.travel_effort,
        explanation=result.explanation,
        tradeoff_summary=_trip_option_tradeoff_summary(result),
    )


def _result_sort_key(result: SearchResult) -> tuple[float, float, str, str, str, str]:
    return (
        -result.score,
        -result.snow_confidence_score,
        result.resort_name,
        result.selected_stay_base_name,
        result.selected_ski_area_name,
        result.rental_name,
    )


def _normalized_stay_base_name(result: SearchResult) -> str:
    return result.selected_stay_base_name.strip().casefold()


def _option_has_material_difference(
    reference: SearchResult, option: SearchResult
) -> bool:
    return any(
        (
            option.selected_ski_area_id != reference.selected_ski_area_id,
            option.selected_stay_base_lift_distance
            != reference.selected_stay_base_lift_distance,
            option.stay_base_price_range != reference.stay_base_price_range,
            option.rating_estimate != reference.rating_estimate,
            option.rental_name != reference.rental_name,
            option.rental_price_range != reference.rental_price_range,
            option.budget_penalty != reference.budget_penalty,
            option.travel_effort != reference.travel_effort,
        )
    )


def _option_is_meaningfully_different(top: SearchResult, option: SearchResult) -> bool:
    if _normalized_stay_base_name(option) == _normalized_stay_base_name(top):
        return False
    if option.score >= top.score - MIN_ALTERNATIVE_SCORE_DELTA:
        return True
    return _option_has_material_difference(top, option)


def _select_alternative_options(
    top: SearchResult, remaining_options: list[SearchResult]
) -> list[TripOption]:
    alternatives: list[TripOption] = []
    selected_results: list[SearchResult] = []
    seen_stay_bases = {_normalized_stay_base_name(top)}

    for option in sorted(remaining_options, key=_result_sort_key):
        stay_base_name = _normalized_stay_base_name(option)
        if stay_base_name in seen_stay_bases:
            continue
        if not _option_is_meaningfully_different(top, option):
            continue
        if any(
            not _option_is_meaningfully_different(selected_option, option)
            for selected_option in selected_results
        ):
            continue

        alternatives.append(_trip_option_from_result(option))
        selected_results.append(option)
        seen_stay_bases.add(stay_base_name)
        if len(alternatives) == MAX_ALTERNATIVE_OPTIONS:
            break

    return alternatives


def _build_recommendation_group(options: list[SearchResult]) -> SearchResult | None:
    if not options:
        return None

    ordered_options = sorted(options, key=_result_sort_key)
    top = ordered_options[0]
    alternative_options = _select_alternative_options(top, ordered_options[1:])
    return top.model_copy(
        update={
            "top_option": _trip_option_from_result(top),
            "alternative_options": alternative_options,
        }
    )


def _build_result(
    destination: Destination,
    ski_area: SkiArea,
    stay_base: StayBase,
    rental: Rental,
    filters: SearchFilters,
    conditions: ResortConditions | None,
    conditions_provenance: ProvenanceInfo,
    planning_summary: str | None = None,
    planning_provenance: ProvenanceInfo | None = None,
    planning_evidence_count: int | None = None,
    planning_weather_metrics: WeatherEvidenceMetrics | None = None,
    best_travel_months: tuple[int, ...] = (),
    travel_effort: TravelEffort | None = None,
) -> SearchResult | None:
    active_conditions = conditions or _fallback_conditions(ski_area.name)
    price = stay_base_budget_price(stay_base)
    penalty = budget_range_penalty(
        price_min=stay_base.price_min,
        price_max=stay_base.price_max,
        min_price=filters.min_price,
        max_price=filters.max_price,
        budget_flex=filters.budget_flex,
    )
    if penalty is None:
        return None

    availability_score_penalty = availability_penalty(
        active_conditions.availability_status
    )
    if availability_score_penalty is None:
        return None

    quality = quality_score(stay_base.quality)
    skill_bonus = skill_fit_score(stay_base, filters.skill_level)
    lift_bonus = lift_distance_score(stay_base.lift_distance) / 10
    price_component = (1 / price) * 0.3
    conditions_score = active_conditions.conditions_score
    snow_confidence_score = active_conditions.snow_confidence_score
    score = (
        quality * 0.55
        + price_component
        + skill_bonus
        + lift_bonus
        + conditions_score * 0.35
        - penalty
        - availability_score_penalty
    )
    if travel_effort is not None:
        score -= (1 - travel_effort.score) * 0.35

    explanation = _build_explanation(
        stay_base=stay_base,
        ski_area=ski_area,
        filters=filters,
        penalty=penalty,
        conditions=active_conditions,
        travel_effort=travel_effort,
    )

    result = SearchResult(
        resort_id=destination.resort_id,
        resort_name=destination.name,
        region=destination.region,
        selected_ski_area_id=ski_area.ski_area_id,
        selected_ski_area_name=ski_area.name,
        selected_stay_base_name=stay_base.name,
        selected_stay_base_lift_distance=stay_base.lift_distance,
        stay_base_price_range=stay_base.price_range,
        selected_area_name=stay_base.name,
        selected_area_lift_distance=stay_base.lift_distance,
        area_price_range=stay_base.price_range,
        rental_name=rental.name,
        rental_price_range=rental.price_range,
        rating_estimate=quality,
        link=build_accommodation_link(
            resort_name=destination.name,
            country=destination.country,
        ),
        score=score,
        budget_penalty=penalty,
        conditions_summary=active_conditions.weather_summary,
        snow_confidence_score=snow_confidence_score,
        snow_confidence_label=active_conditions.snow_confidence_label,
        availability_status=active_conditions.availability_status,
        conditions_score=conditions_score,
        conditions_provenance=conditions_provenance,
        explanation=explanation,
        recommendation_confidence=min(
            (quality / 3) * 0.45
            + snow_confidence_score * 0.35
            + (1 - availability_score_penalty) * 0.2,
            1.0,
        ),
        planning_summary=planning_summary,
        planning_provenance=planning_provenance,
        planning_evidence_count=planning_evidence_count,
        planning_weather_metrics=planning_weather_metrics,
        best_travel_months=list(best_travel_months),
        travel_effort=travel_effort,
    )
    return result.model_copy(update={"top_option": _trip_option_from_result(result)})


def search_resorts(
    filters: SearchFilters,
    *,
    resorts: tuple[Destination, ...] | None = None,
    conditions_provider=None,
    condition_history_repository=None,
    raw_weather_history_repository=None,
    snow_climatology_repository=None,
    travel_cache_repository: TravelCacheProtocol | None = None,
) -> list[SearchResult]:
    normalized_location = filters.location.strip().lower()
    results: list[SearchResult] = []
    active_resorts = resorts or get_resort_repository().list_resorts()
    candidate_resorts = tuple(
        resort
        for resort in active_resorts
        if resort.country.lower() == normalized_location
    )
    search_started = time.perf_counter()
    with search_span(filters, candidate_resort_count=len(candidate_resorts)) as span:
        with search_phase("load_conditions_provider", filters):
            active_conditions_provider = (
                conditions_provider or get_conditions_provider()
            )

        with search_phase("load_history_repositories", filters):
            history_repository = (
                condition_history_repository or get_condition_history_repository()
            )
            active_raw_history_repository = (
                raw_weather_history_repository or get_raw_weather_history_repository()
            )
            active_snow_climatology_repository = (
                snow_climatology_repository or get_snow_climatology_repository()
            )

        raw_weather_cache: RawWeatherCache = {}
        snow_climatology_cache: SnowClimatologyCache = {}
        planning_snapshot_cache: PlanningSnapshotCache = {}
        planning_context_cache: dict[str, _SkiAreaPlanningContext] = {}
        if filters.travel_month is not None or (
            filters.trip_start_date is not None and filters.trip_end_date is not None
        ):
            with search_phase("preload_snow_climatology", filters):
                snow_climatology_cache = _preload_snow_climatology(
                    snow_climatology_repository=active_snow_climatology_repository,
                    resorts=candidate_resorts,
                    travel_month=filters.travel_month,
                    trip_start_date=filters.trip_start_date,
                    trip_end_date=filters.trip_end_date,
                )

            raw_ski_area_ids_to_load: list[str] = []
            for resort in candidate_resorts:
                for ski_area in resort.ski_areas:
                    if _has_preloaded_snow_climatology(
                        snow_climatology_cache=snow_climatology_cache,
                        ski_area=ski_area,
                    ):
                        continue
                    raw_ski_area_ids_to_load.append(ski_area.ski_area_id)

            with search_phase("preload_raw_weather", filters):
                raw_weather_cache = _preload_raw_weather_observations(
                    raw_history_repository=active_raw_history_repository,
                    resorts=candidate_resorts,
                    ski_area_ids=tuple(dict.fromkeys(raw_ski_area_ids_to_load)),
                    travel_month=filters.travel_month,
                    trip_start_date=filters.trip_start_date,
                    trip_end_date=filters.trip_end_date,
                )

            snapshot_resort_ids_to_load: list[str] = []
            for resort in candidate_resorts:
                for ski_area in resort.ski_areas:
                    if _has_preloaded_snow_climatology(
                        snow_climatology_cache=snow_climatology_cache,
                        ski_area=ski_area,
                    ):
                        continue
                    if _has_preloaded_raw_weather(
                        raw_weather_cache=raw_weather_cache,
                        ski_area=ski_area,
                    ):
                        continue
                    snapshot_resort_ids_to_load.extend(
                        (ski_area.ski_area_id, resort.resort_id)
                    )
            snapshot_resort_ids = tuple(dict.fromkeys(snapshot_resort_ids_to_load))
            with search_phase("preload_planning_snapshots", filters):
                planning_snapshot_cache = _preload_planning_snapshots(
                    history_repository=history_repository,
                    resort_ids=snapshot_resort_ids,
                )

        for resort in candidate_resorts:
            travel_effort: TravelEffort | None = None
            if filters.origin_text:
                with search_phase("assess_travel_effort", filters):
                    if travel_cache_repository is None:
                        travel_effort = assess_deterministic_travel_effort(
                            origin_text=filters.origin_text,
                            destination=resort,
                            max_drive_minutes=filters.max_drive_minutes,
                            tolerance=filters.travel_tolerance,
                        )
                    else:
                        travel_effort = assess_travel_effort(
                            origin_text=filters.origin_text,
                            destination=resort,
                            cache=travel_cache_repository,
                            max_drive_minutes=filters.max_drive_minutes,
                            tolerance=filters.travel_tolerance,
                        )
                if travel_effort is not None and travel_effort.exceeds_max_drive:
                    continue

            matching_groups: dict[tuple[str, str], list[SearchResult]] = {}
            for stay_base in resort.stay_bases:
                if quality_score(stay_base.quality) < filters.stars:
                    continue
                if not skill_level_matches(stay_base, filters.skill_level):
                    continue
                if not lift_distance_matches(
                    stay_base.lift_distance, filters.lift_distance
                ):
                    continue

                for ski_area in resort.ski_areas:
                    planning_context = planning_context_cache.get(ski_area.ski_area_id)
                    if planning_context is None:
                        with search_phase("build_planning_context", filters):
                            planning_context = _build_ski_area_planning_context(
                                filters=filters,
                                conditions_provider=active_conditions_provider,
                                history_repository=history_repository,
                                raw_history_repository=active_raw_history_repository,
                                raw_weather_cache=raw_weather_cache,
                                snow_climatology_cache=snow_climatology_cache,
                                planning_snapshot_cache=planning_snapshot_cache,
                                destination=resort,
                                ski_area=ski_area,
                            )
                        planning_context_cache[ski_area.ski_area_id] = planning_context

                    for rental in resort.rentals:
                        if filters.lift_distance and not lift_distance_matches(
                            rental.lift_distance, filters.lift_distance
                        ):
                            continue

                        result = _build_result(
                            destination=resort,
                            ski_area=ski_area,
                            stay_base=stay_base,
                            rental=rental,
                            filters=filters,
                            conditions=planning_context.conditions,
                            conditions_provenance=(
                                planning_context.conditions_provenance
                            ),
                            planning_summary=planning_context.planning_summary,
                            planning_provenance=planning_context.planning_provenance,
                            planning_evidence_count=(
                                planning_context.planning_evidence_count
                            ),
                            planning_weather_metrics=(
                                planning_context.planning_weather_metrics
                            ),
                            best_travel_months=planning_context.best_travel_months,
                            travel_effort=travel_effort,
                        )
                        if result is not None:
                            group_key = (
                                result.resort_id,
                                result.selected_ski_area_id,
                            )
                            matching_groups.setdefault(group_key, []).append(result)

            for matching_pairs in matching_groups.values():
                recommendation_group = _build_recommendation_group(matching_pairs)
                if recommendation_group is not None:
                    results.append(recommendation_group)

        with search_phase("rank_results", filters):
            ranked_results = sorted(results, key=_result_sort_key)[:3]

        record_search_completed(
            filters=filters,
            result_count=len(ranked_results),
            duration_seconds=time.perf_counter() - search_started,
            span=span,
        )
        return ranked_results
