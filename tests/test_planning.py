from datetime import date

from app.domain.catalog import SkiArea
from app.domain.models import RawWeatherObservation, SnowClimatologyDaily
from app.domain.planning import (
    derive_climatology_weather_evidence_metrics,
    derive_planning_assessment,
)


def _ski_area() -> SkiArea:
    return SkiArea(
        ski_area_id="test-ski-area",
        name="Test Ski Area",
        weather_sampling_status="active",
        latitude=46.9,
        longitude=11.0,
        base_elevation_m=1700,
        summit_elevation_m=3200,
        season_start_month=11,
        season_end_month=5,
    )


def _raw_weather_observation(
    *,
    observed_on: str,
    snow_depth_m: float,
    max_temp_c: float = -4,
) -> RawWeatherObservation:
    return RawWeatherObservation(
        ski_area_id="test-ski-area",
        resort_name="Test Ski Area",
        elevation_band="mid",
        elevation_m=2450,
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
        snowfall_cm=6,
        snow_depth_m=snow_depth_m,
        temperature_2m_max_c=max_temp_c,
        temperature_2m_min_c=max_temp_c - 6,
        wind_speed_10m_max_kmh=18,
        wind_gusts_10m_max_kmh=26,
        weather_code=3,
        record_type="archive",
        source="open-meteo",
        source_model="best_match",
    )


def _snow_climatology_row(
    *,
    month: int = 3,
    day: int = 10,
    baseline_period: str = "normal_30y",
    evidence_seasons: int = 30,
    snow_score: float = 0.9,
    conditions_score: float = 0.86,
) -> SnowClimatologyDaily:
    return SnowClimatologyDaily(
        ski_area_id="test-ski-area",
        resort_name="Test Ski Area",
        elevation_band="mid",
        elevation_m=2450,
        month=month,
        day=day,
        baseline_period=baseline_period,
        baseline_start_year=1996 if baseline_period == "normal_30y" else 2011,
        baseline_end_year=2025,
        evidence_seasons=evidence_seasons,
        latest_archive_year=2025,
        snow_depth_cm_p25=80,
        snow_depth_cm_p50=130,
        snow_depth_cm_p75=170,
        prob_snow_depth_ge_30cm=0.95,
        prob_snow_depth_ge_50cm=0.9,
        avg_daily_snowfall_cm=5.5,
        prob_rain_risk=0.04,
        prob_freeze_thaw=0.08,
        avg_max_temperature_c=-3.5,
        avg_wind_gust_kmh=24,
        avg_snow_confidence_score=snow_score,
        avg_conditions_score=conditions_score,
        source_model="snowcast_empirical_v1",
        computed_at="2026-06-15T00:00:00+00:00",
    )


def test_exact_date_planning_uses_season_windows_before_month_fallback() -> None:
    resort = SkiArea(
        ski_area_id="test-glacier",
        name="Test Glacier",
        weather_sampling_status="active",
        latitude=46.9,
        longitude=11.0,
        base_elevation_m=1700,
        summit_elevation_m=3200,
        season_start_month=10,
        season_end_month=5,
        season_windows=[
            {
                "season_label": "2025-2026",
                "start_date": "2025-12-01",
                "end_date": "2026-04-15",
                "status": "planned",
            }
        ],
    )

    assessment = derive_planning_assessment(
        resort=resort,
        trip_start_date=date(2025, 11, 20),
        trip_end_date=date(2025, 11, 23),
        snapshots=(),
    )
    month_only = derive_planning_assessment(
        resort=resort,
        travel_month=11,
        snapshots=(),
    )

    assert assessment.conditions.availability_status == "out_of_season"
    assert month_only.conditions.availability_status != "out_of_season"


def test_exact_date_planning_accepts_trip_inside_known_area_window() -> None:
    resort = SkiArea(
        ski_area_id="test-glacier",
        name="Test Glacier",
        weather_sampling_status="active",
        latitude=46.9,
        longitude=11.0,
        base_elevation_m=1700,
        summit_elevation_m=3200,
        season_start_month=10,
        season_end_month=5,
        season_windows=[
            {
                "season_label": "2025-2026",
                "start_date": "2025-12-01",
                "end_date": "2026-04-15",
                "status": "planned",
            }
        ],
    )

    assessment = derive_planning_assessment(
        resort=resort,
        trip_start_date=date(2026, 2, 10),
        trip_end_date=date(2026, 2, 15),
        snapshots=(),
    )

    assert assessment.conditions.availability_status != "out_of_season"


def test_exact_date_planning_falls_back_to_months_for_unknown_future_season() -> None:
    resort = SkiArea(
        ski_area_id="test-glacier",
        name="Test Glacier",
        weather_sampling_status="active",
        latitude=46.9,
        longitude=11.0,
        base_elevation_m=1700,
        summit_elevation_m=3200,
        season_start_month=10,
        season_end_month=5,
        season_windows=[
            {
                "season_label": "2025-2026",
                "start_date": "2025-10-03",
                "end_date": "2026-05-17",
                "status": "planned",
            }
        ],
    )

    assessment = derive_planning_assessment(
        resort=resort,
        trip_start_date=date(2026, 10, 20),
        trip_end_date=date(2026, 10, 23),
        snapshots=(),
    )

    assert assessment.conditions.availability_status != "out_of_season"


def test_planning_prefers_snow_climatology_when_available() -> None:
    assessment = derive_planning_assessment(
        resort=_ski_area(),
        travel_month=3,
        snapshots=(),
        raw_weather_observations=(
            _raw_weather_observation(
                observed_on="2025-03-10",
                snow_depth_m=0.05,
                max_temp_c=5,
            ),
        ),
        snow_climatology_rows=(
            _snow_climatology_row(day=10),
            _snow_climatology_row(day=11, baseline_period="recent_15y", snow_score=0.8),
        ),
    )

    assert assessment.evidence_source == "snow_climatology"
    assert assessment.evidence_count == 30
    assert assessment.conditions.snow_confidence_label == "good"
    assert assessment.latest_snapshot_at == "2025-03-10T00:00:00+00:00"


def test_planning_falls_back_to_raw_history_when_climatology_is_missing() -> None:
    assessment = derive_planning_assessment(
        resort=_ski_area(),
        travel_month=3,
        snapshots=(),
        raw_weather_observations=(
            _raw_weather_observation(observed_on="2024-03-10", snow_depth_m=1.1),
            _raw_weather_observation(observed_on="2025-03-11", snow_depth_m=1.2),
        ),
        snow_climatology_rows=(),
    )

    assert assessment.evidence_source == "raw_history"
    assert assessment.evidence_count == 2
    assert assessment.latest_snapshot_at == "2025-03-11T12:00:00+00:00"


def test_planning_uses_climatology_for_exact_date_windows() -> None:
    assessment = derive_planning_assessment(
        resort=_ski_area(),
        snapshots=(),
        trip_start_date=date(2027, 3, 9),
        trip_end_date=date(2027, 3, 11),
        snow_climatology_rows=(
            _snow_climatology_row(day=8),
            _snow_climatology_row(day=9),
            _snow_climatology_row(day=11),
            _snow_climatology_row(day=12),
        ),
    )

    assert assessment.evidence_source == "snow_climatology"
    assert assessment.evidence_count == 30
    assert assessment.conditions.snow_confidence_label == "good"


def test_planning_marks_low_coverage_climatology_as_fallback_heavy() -> None:
    assessment = derive_planning_assessment(
        resort=_ski_area(),
        travel_month=3,
        snapshots=(),
        snow_climatology_rows=(
            _snow_climatology_row(day=10, evidence_seasons=5),
            _snow_climatology_row(day=11, evidence_seasons=5),
        ),
    )

    assert assessment.evidence_source == "snow_climatology"
    assert assessment.evidence_count == 5
    assert assessment.evidence_profile == "fallback_heavy"


def test_climatology_weather_evidence_metrics_use_normal_baseline_rows() -> None:
    metrics = derive_climatology_weather_evidence_metrics(
        snow_climatology_rows=(
            _snow_climatology_row(day=10, snow_score=0.9),
            _snow_climatology_row(day=11, snow_score=0.85),
            _snow_climatology_row(
                day=11,
                baseline_period="recent_15y",
                evidence_seasons=15,
                snow_score=0.7,
            ),
        ),
        trip_start_date=date(2027, 3, 10),
        trip_end_date=date(2027, 3, 11),
    )

    assert metrics is not None
    assert metrics.average_snow_depth_cm == 130.0
    assert metrics.average_daily_snowfall_cm == 5.5
    assert metrics.evidence_years == 30
    assert metrics.latest_observed_on == "2025-03-11"
    assert metrics.elevation_band == "mid"
    assert metrics.elevation_m == 2450
