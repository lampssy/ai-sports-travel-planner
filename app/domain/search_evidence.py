from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.data.repositories import is_condition_fresh
from app.domain.catalog import SkiArea as CatalogSkiArea
from app.domain.models import (
    ProvenanceInfo,
    RawWeatherObservation,
    ResortConditions,
    ResortConditionSnapshot,
    SearchFilters,
    SkiArea,
    SnowClimatologyBaselinePeriod,
    SnowClimatologyDaily,
    WeatherElevationBand,
    WeatherEvidenceMetrics,
)
from app.domain.planning import (
    derive_climatology_weather_evidence_metrics,
    derive_planning_assessment,
    derive_weather_evidence_metrics,
)
from app.domain.planning_policy import DEFAULT_PLANNING_HEURISTIC_POLICY

POLICY = DEFAULT_PLANNING_HEURISTIC_POLICY
DEFAULT_PLANNING_WEATHER_BANDS: tuple[WeatherElevationBand, ...] = ("mid",)
DEFAULT_CLIMATOLOGY_BASELINE_PERIODS: tuple[
    SnowClimatologyBaselinePeriod,
    ...,
] = ("normal_30y", "recent_15y")
PlanningSkiArea = SkiArea | CatalogSkiArea
RawWeatherCache = dict[
    tuple[str, WeatherElevationBand], tuple[RawWeatherObservation, ...]
]
SnowClimatologyCache = dict[
    tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod],
    tuple[SnowClimatologyDaily, ...],
]
PlanningSnapshotCache = dict[str, tuple[ResortConditionSnapshot, ...]]


class ConditionsProviderProtocol(Protocol):
    def get_conditions_for_resort(
        self,
        resort_name: str,
    ) -> ResortConditions | None: ...


class ConditionHistoryProtocol(Protocol):
    def list_snapshots_for_ski_area(
        self,
        ski_area_id: str,
    ) -> tuple[ResortConditionSnapshot, ...]: ...


class RawWeatherHistoryProtocol(Protocol):
    def list_observations_for_ski_area(
        self,
        ski_area_id: str,
        *,
        elevation_band: WeatherElevationBand,
    ) -> tuple[RawWeatherObservation, ...]: ...


class SnowClimatologyProtocol(Protocol):
    def list_daily_rows_for_ski_areas_window(
        self,
        ski_area_ids: tuple[str, ...],
        *,
        elevation_bands: tuple[WeatherElevationBand, ...],
        baseline_periods: tuple[SnowClimatologyBaselinePeriod, ...],
        travel_month: int | None = None,
        trip_start_date: date | None = None,
        trip_end_date: date | None = None,
    ) -> dict[
        tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod],
        tuple[SnowClimatologyDaily, ...],
    ]: ...


@dataclass(frozen=True)
class SkiAreaPlanningContext:
    conditions: ResortConditions
    conditions_provenance: ProvenanceInfo
    planning_summary: str | None
    planning_provenance: ProvenanceInfo | None
    planning_evidence_count: int | None
    planning_weather_metrics: WeatherEvidenceMetrics | None
    best_travel_months: tuple[int, ...]


def load_planning_contexts(
    *,
    ski_areas: tuple[PlanningSkiArea, ...],
    filters: SearchFilters,
    conditions_provider: ConditionsProviderProtocol,
    condition_history_repository: ConditionHistoryProtocol,
    raw_weather_history_repository: RawWeatherHistoryProtocol,
    snow_climatology_repository: SnowClimatologyProtocol,
) -> dict[str, SkiAreaPlanningContext]:
    unique_areas = tuple({area.ski_area_id: area for area in ski_areas}.values())
    raw_weather_cache: RawWeatherCache = {}
    snow_climatology_cache: SnowClimatologyCache = {}
    planning_snapshot_cache: PlanningSnapshotCache = {}
    has_trip_window = filters.travel_month is not None or (
        filters.trip_start_date is not None and filters.trip_end_date is not None
    )
    if has_trip_window:
        area_ids = tuple(area.ski_area_id for area in unique_areas)
        snow_climatology_cache = _preload_snow_climatology(
            repository=snow_climatology_repository,
            ski_area_ids=area_ids,
            filters=filters,
        )
        raw_area_ids = tuple(
            area.ski_area_id
            for area in unique_areas
            if not _has_preloaded_snow_climatology(
                snow_climatology_cache, area.ski_area_id
            )
        )
        raw_weather_cache = _preload_raw_weather(
            repository=raw_weather_history_repository,
            ski_area_ids=raw_area_ids,
            filters=filters,
        )
        snapshot_area_ids = tuple(
            area_id
            for area_id in raw_area_ids
            if not _has_preloaded_raw_weather(raw_weather_cache, area_id)
        )
        planning_snapshot_cache = _preload_snapshots(
            repository=condition_history_repository,
            ski_area_ids=snapshot_area_ids,
        )

    return {
        area.ski_area_id: build_ski_area_planning_context(
            area=area,
            filters=filters,
            conditions_provider=conditions_provider,
            condition_history_repository=condition_history_repository,
            raw_weather_history_repository=raw_weather_history_repository,
            raw_weather_cache=raw_weather_cache,
            snow_climatology_cache=snow_climatology_cache,
            planning_snapshot_cache=planning_snapshot_cache,
        )
        for area in unique_areas
    }


def build_ski_area_planning_context(
    *,
    area: PlanningSkiArea,
    filters: SearchFilters,
    conditions_provider: ConditionsProviderProtocol,
    condition_history_repository: ConditionHistoryProtocol,
    raw_weather_history_repository: RawWeatherHistoryProtocol,
    raw_weather_cache: RawWeatherCache,
    snow_climatology_cache: SnowClimatologyCache,
    planning_snapshot_cache: PlanningSnapshotCache,
) -> SkiAreaPlanningContext:
    current_conditions = _current_conditions(conditions_provider, area)
    conditions_provenance = _build_conditions_provenance(current_conditions)
    planning_summary: str | None = None
    planning_provenance: ProvenanceInfo | None = None
    planning_evidence_count: int | None = None
    planning_weather_metrics: WeatherEvidenceMetrics | None = None
    best_travel_months: tuple[int, ...] = ()

    if filters.travel_month is not None or (
        filters.trip_start_date is not None and filters.trip_end_date is not None
    ):
        climatology_rows = _list_snow_climatology_rows(
            snow_climatology_cache, area.ski_area_id
        )
        raw_observations = (
            ()
            if climatology_rows
            else _list_raw_weather_observations(
                repository=raw_weather_history_repository,
                cache=raw_weather_cache,
                ski_area_id=area.ski_area_id,
                filters=filters,
            )
        )
        snapshots = (
            ()
            if climatology_rows or raw_observations
            else _list_snapshots(
                repository=condition_history_repository,
                cache=planning_snapshot_cache,
                ski_area_id=area.ski_area_id,
            )
        )
        planning = derive_planning_assessment(
            resort=area,
            travel_month=filters.travel_month,
            snapshots=snapshots,
            raw_weather_observations=raw_observations,
            snow_climatology_rows=climatology_rows,
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
                snow_climatology_rows=climatology_rows,
                travel_month=filters.travel_month,
                trip_start_date=filters.trip_start_date,
                trip_end_date=filters.trip_end_date,
            )
            if climatology_rows
            else derive_weather_evidence_metrics(
                raw_weather_observations=raw_observations,
                travel_month=filters.travel_month,
                trip_start_date=filters.trip_start_date,
                trip_end_date=filters.trip_end_date,
            )
        )
    else:
        conditions = current_conditions or _fallback_conditions(area.name)

    return SkiAreaPlanningContext(
        conditions=conditions,
        conditions_provenance=conditions_provenance,
        planning_summary=planning_summary,
        planning_provenance=planning_provenance,
        planning_evidence_count=planning_evidence_count,
        planning_weather_metrics=planning_weather_metrics,
        best_travel_months=best_travel_months,
    )


def _current_conditions(
    provider: ConditionsProviderProtocol,
    area: PlanningSkiArea,
) -> ResortConditions | None:
    loader = getattr(provider, "get_conditions_for_ski_area", None)
    if loader is not None:
        return loader(area.ski_area_id)
    return provider.get_conditions_for_resort(area.name)


def _fallback_conditions(area_name: str) -> ResortConditions:
    return ResortConditions(
        resort_name=area_name,
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
    return ProvenanceInfo(
        source_name=source_name,
        source_type="estimated",
        updated_at=latest_snapshot_at if evidence_count > 0 else None,
        freshness_status="historical" if evidence_count > 0 else "unknown",
        basis_summary=basis_summary,
        evidence_profile=evidence_profile,
    )


def _preload_snow_climatology(
    *,
    repository: SnowClimatologyProtocol,
    ski_area_ids: tuple[str, ...],
    filters: SearchFilters,
) -> SnowClimatologyCache:
    loader = getattr(repository, "list_daily_rows_for_ski_areas_window", None)
    if loader is None or not ski_area_ids:
        return {}
    grouped = loader(
        ski_area_ids,
        elevation_bands=DEFAULT_PLANNING_WEATHER_BANDS,
        baseline_periods=DEFAULT_CLIMATOLOGY_BASELINE_PERIODS,
        travel_month=filters.travel_month,
        trip_start_date=filters.trip_start_date,
        trip_end_date=filters.trip_end_date,
    )
    return {
        (area_id, band, period): grouped.get((area_id, band, period), ())
        for area_id in ski_area_ids
        for band in DEFAULT_PLANNING_WEATHER_BANDS
        for period in DEFAULT_CLIMATOLOGY_BASELINE_PERIODS
    }


def _preload_raw_weather(
    *,
    repository: RawWeatherHistoryProtocol,
    ski_area_ids: tuple[str, ...],
    filters: SearchFilters,
) -> RawWeatherCache:
    if not ski_area_ids:
        return {}
    loader = getattr(
        repository,
        "list_archive_observations_for_ski_areas_window",
        None,
    )
    if loader is not None:
        grouped = loader(
            ski_area_ids,
            elevation_bands=DEFAULT_PLANNING_WEATHER_BANDS,
            travel_month=filters.travel_month,
            trip_start_date=filters.trip_start_date,
            trip_end_date=filters.trip_end_date,
        )
    else:
        loader = getattr(repository, "list_observations_for_ski_areas", None)
        if loader is None:
            return {}
        grouped = loader(
            ski_area_ids,
            elevation_bands=DEFAULT_PLANNING_WEATHER_BANDS,
        )
    return {
        (area_id, band): grouped.get((area_id, band), ())
        for area_id in ski_area_ids
        for band in DEFAULT_PLANNING_WEATHER_BANDS
    }


def _preload_snapshots(
    *,
    repository: ConditionHistoryProtocol,
    ski_area_ids: tuple[str, ...],
) -> PlanningSnapshotCache:
    if not ski_area_ids:
        return {}
    loader = getattr(repository, "list_snapshots_for_ski_areas", None)
    if loader is None:
        return {}
    grouped = loader(ski_area_ids)
    return {area_id: grouped.get(area_id, ()) for area_id in ski_area_ids}


def _has_preloaded_snow_climatology(
    cache: SnowClimatologyCache,
    ski_area_id: str,
) -> bool:
    return any(
        cache.get((ski_area_id, band, period))
        for band in DEFAULT_PLANNING_WEATHER_BANDS
        for period in DEFAULT_CLIMATOLOGY_BASELINE_PERIODS
    )


def _has_preloaded_raw_weather(
    cache: RawWeatherCache,
    ski_area_id: str,
) -> bool:
    return any(
        cache.get((ski_area_id, band)) for band in DEFAULT_PLANNING_WEATHER_BANDS
    )


def _list_snow_climatology_rows(
    cache: SnowClimatologyCache,
    ski_area_id: str,
) -> tuple[SnowClimatologyDaily, ...]:
    for band in DEFAULT_PLANNING_WEATHER_BANDS:
        rows = tuple(
            row
            for period in DEFAULT_CLIMATOLOGY_BASELINE_PERIODS
            for row in cache.get((ski_area_id, band, period), ())
        )
        if rows:
            return rows
    return ()


def _list_raw_weather_observations(
    *,
    repository: RawWeatherHistoryProtocol,
    cache: RawWeatherCache,
    ski_area_id: str,
    filters: SearchFilters,
) -> tuple[RawWeatherObservation, ...]:
    for band in DEFAULT_PLANNING_WEATHER_BANDS:
        key = (ski_area_id, band)
        if key not in cache:
            cache[key] = repository.list_observations_for_ski_area(
                ski_area_id,
                elevation_band=band,
            )
        observations = cache[key]
        if _has_archive_observations_for_window(observations, filters):
            return observations
    return ()


def _has_archive_observations_for_window(
    observations: tuple[RawWeatherObservation, ...],
    filters: SearchFilters,
) -> bool:
    for observation in observations:
        if observation.record_type != "archive":
            continue
        observed_on = date.fromisoformat(observation.observed_on)
        if filters.trip_start_date is not None and filters.trip_end_date is not None:
            if _matches_month_day_window(
                observed_on,
                filters.trip_start_date,
                filters.trip_end_date,
            ):
                return True
        elif filters.travel_month is not None:
            if observed_on.month == filters.travel_month:
                return True
    return False


def _matches_month_day_window(
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


def _list_snapshots(
    *,
    repository: ConditionHistoryProtocol,
    cache: PlanningSnapshotCache,
    ski_area_id: str,
) -> tuple[ResortConditionSnapshot, ...]:
    if ski_area_id not in cache:
        cache[ski_area_id] = repository.list_snapshots_for_ski_area(ski_area_id)
    return cache[ski_area_id]
