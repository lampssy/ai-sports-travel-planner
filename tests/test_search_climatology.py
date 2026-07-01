from __future__ import annotations

from datetime import date

from app.domain.models import (
    Destination,
    RawWeatherObservation,
    Rental,
    ResortConditions,
    SearchFilters,
    SkiArea,
    SnowClimatologyDaily,
    StayBase,
)
from app.domain.search_service import search_resorts


def _destination() -> Destination:
    ski_area = SkiArea(
        ski_area_id="test-ski-area",
        name="Test Ski Area",
        latitude=46.9,
        longitude=11.0,
        base_elevation_m=1700,
        summit_elevation_m=3200,
        season_start_month=11,
        season_end_month=5,
    )
    return Destination(
        resort_id="test-destination",
        name="Test Destination",
        country="France",
        region="Test Region",
        price_level="medium",
        latitude=ski_area.latitude,
        longitude=ski_area.longitude,
        base_elevation_m=ski_area.base_elevation_m,
        summit_elevation_m=ski_area.summit_elevation_m,
        season_start_month=ski_area.season_start_month,
        season_end_month=ski_area.season_end_month,
        stay_bases=[
            StayBase(
                stay_base_id="test-base",
                name="Test Base",
                price_range="EUR 150-220",
                price_min=150,
                price_max=220,
                quality="standard",
                lift_distance="near",
                supported_skill_levels=["intermediate"],
            )
        ],
        ski_areas=[ski_area],
        rentals=[
            Rental(
                name="Test Rental",
                price_range="EUR 40-60",
                price_min=40,
                price_max=60,
                quality="standard",
                lift_distance="near",
            )
        ],
    )


def _filters() -> SearchFilters:
    return SearchFilters(
        location="France",
        min_price=100,
        max_price=260,
        stars=2,
        skill_level="intermediate",
        trip_start_date=date(2027, 3, 10),
        trip_end_date=date(2027, 3, 12),
    )


def _snow_climatology_row(
    *,
    day: int,
    baseline_period: str = "normal_30y",
    evidence_seasons: int = 30,
) -> SnowClimatologyDaily:
    return SnowClimatologyDaily(
        ski_area_id="test-ski-area",
        resort_name="Test Ski Area",
        elevation_band="mid",
        elevation_m=2450,
        month=3,
        day=day,
        baseline_period=baseline_period,
        baseline_start_year=1996 if baseline_period == "normal_30y" else 2011,
        baseline_end_year=2025,
        evidence_seasons=evidence_seasons,
        latest_archive_year=2025,
        snow_depth_cm_p25=90,
        snow_depth_cm_p50=135,
        snow_depth_cm_p75=180,
        prob_snow_depth_ge_30cm=0.95,
        prob_snow_depth_ge_50cm=0.9,
        avg_daily_snowfall_cm=5,
        prob_rain_risk=0.04,
        prob_freeze_thaw=0.08,
        avg_max_temperature_c=-4,
        avg_wind_gust_kmh=22,
        avg_snow_confidence_score=0.9,
        avg_conditions_score=0.86,
        source_model="snowcast_empirical_v1",
        computed_at="2026-06-15T00:00:00+00:00",
    )


def _raw_weather_observation(observed_on: str) -> RawWeatherObservation:
    return RawWeatherObservation(
        ski_area_id="test-ski-area",
        resort_name="Test Ski Area",
        elevation_band="mid",
        elevation_m=2450,
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
        snowfall_cm=6,
        snow_depth_m=1.2,
        temperature_2m_max_c=-4,
        temperature_2m_min_c=-10,
        wind_speed_10m_max_kmh=18,
        wind_gusts_10m_max_kmh=26,
        weather_code=3,
        record_type="archive",
        source="open-meteo",
        source_model="best_match",
    )


class StaticConditionsProvider:
    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions:
        return ResortConditions(
            resort_name=resort_name,
            snow_confidence_score=0.72,
            snow_confidence_label="good",
            availability_status="open",
            weather_summary="Good current signal.",
            conditions_score=0.72,
            updated_at="2026-06-15T00:00:00+00:00",
            source="test",
        )


class EmptySnapshotRepository:
    def __init__(self) -> None:
        self.batch_calls = 0

    def list_snapshots_for_ski_areas(self, ski_area_ids: tuple[str, ...]) -> dict:
        self.batch_calls += 1
        return {ski_area_id: () for ski_area_id in ski_area_ids}


class CountingRawRepository:
    def __init__(self, observations: tuple[RawWeatherObservation, ...] = ()) -> None:
        self.observations = observations
        self.window_batch_calls = 0

    def list_archive_observations_for_ski_areas_window(
        self,
        ski_area_ids: tuple[str, ...],
        *,
        elevation_bands: tuple[str, ...],
        travel_month: int | None = None,
        trip_start_date: date | None = None,
        trip_end_date: date | None = None,
    ) -> dict[tuple[str, str], tuple[RawWeatherObservation, ...]]:
        self.window_batch_calls += 1
        return {
            (ski_area_id, elevation_band): self.observations
            for ski_area_id in ski_area_ids
            for elevation_band in elevation_bands
        }


class StaticSnowClimatologyRepository:
    def __init__(self, rows: tuple[SnowClimatologyDaily, ...]) -> None:
        self.rows = rows

    def list_daily_rows_for_ski_areas_window(
        self,
        ski_area_ids: tuple[str, ...],
        *,
        elevation_bands: tuple[str, ...],
        baseline_periods: tuple[str, ...],
        travel_month: int | None = None,
        trip_start_date: date | None = None,
        trip_end_date: date | None = None,
    ) -> dict[tuple[str, str, str], tuple[SnowClimatologyDaily, ...]]:
        return {
            (ski_area_id, elevation_band, baseline_period): tuple(
                row
                for row in self.rows
                if row.ski_area_id == ski_area_id
                and row.elevation_band == elevation_band
                and row.baseline_period == baseline_period
            )
            for ski_area_id in ski_area_ids
            for elevation_band in elevation_bands
            for baseline_period in baseline_periods
        }


def test_search_uses_snow_climatology_without_loading_raw_history() -> None:
    raw_repository = CountingRawRepository()
    snapshot_repository = EmptySnapshotRepository()

    results = search_resorts(
        _filters(),
        resorts=(_destination(),),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=snapshot_repository,
        raw_weather_history_repository=raw_repository,
        snow_climatology_repository=StaticSnowClimatologyRepository(
            (
                _snow_climatology_row(day=10),
                _snow_climatology_row(day=11),
                _snow_climatology_row(day=12),
            )
        ),
    )

    assert len(results) == 1
    assert raw_repository.window_batch_calls == 0
    assert snapshot_repository.batch_calls == 0
    assert results[0].planning_evidence_count == 30
    assert results[0].planning_provenance is not None
    assert results[0].planning_provenance.evidence_profile == "archive_backed"
    assert results[0].planning_weather_metrics is not None
    assert results[0].planning_weather_metrics.evidence_years == 30


def test_search_loads_raw_history_when_snow_climatology_is_missing() -> None:
    raw_repository = CountingRawRepository(
        (
            _raw_weather_observation("2024-03-10"),
            _raw_weather_observation("2025-03-11"),
        )
    )
    snapshot_repository = EmptySnapshotRepository()

    results = search_resorts(
        _filters(),
        resorts=(_destination(),),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=snapshot_repository,
        raw_weather_history_repository=raw_repository,
        snow_climatology_repository=StaticSnowClimatologyRepository(()),
    )

    assert len(results) == 1
    assert raw_repository.window_batch_calls == 1
    assert snapshot_repository.batch_calls == 0
    assert results[0].planning_evidence_count == 2
    assert results[0].planning_provenance is not None
    assert results[0].planning_provenance.source_name == "archive_history+seasonality"
