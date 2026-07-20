from __future__ import annotations

import statistics
import time
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes import router
from app.data.audit_search_factor_readiness import DEFAULT_TRUST_MANIFEST_PATH
from app.data.catalog_loader import CATALOG_PATH, load_catalog_from_path
from app.domain.catalog_trust import CatalogTrustManifest
from app.domain.models import SnowClimatologyDaily
from app.domain.search_factors.weather import (
    WeatherEvaluationContext,
    WeatherFactorCandidate,
)
from app.domain.search_policy import load_search_policy
from app.domain.search_v4_models import SearchConstraints, SearchIntent, TravelWindow
from app.domain.search_v4_service import get_search_weather_evidence
from app.domain.search_weather_evidence import (
    SearchWeatherEvidenceAvailableResponse,
    SearchWeatherEvidenceRequest,
    SearchWeatherEvidenceUnavailableResponse,
    build_search_weather_evidence,
)
from app.domain.weather_forecast import (
    ServedWeatherForecastDaily,
    WeatherForecastDaily,
    WeatherForecastRun,
)

pytestmark = pytest.mark.db_free

_PREFERRED_SOURCE = "ecmwf_ifs025_ensemble_mean"
_FALLBACK_SOURCE = "ncep_gefs05_ensemble_mean"


def _climatology(
    day: date,
    *,
    ski_area_id: str = "area",
    baseline: str = "normal_30y",
    computed_at: str = "2026-07-01T00:00:00+00:00",
    source_model: str = "snowcast_empirical_v1",
    snow_depth_cm_p50: float | None = 80,
    elevation_m: int | None = 2000,
) -> SnowClimatologyDaily:
    return SnowClimatologyDaily(
        ski_area_id=ski_area_id,
        resort_name=ski_area_id.title(),
        elevation_band="mid",
        elevation_m=elevation_m,
        month=day.month,
        day=day.day,
        baseline_period=baseline,
        baseline_start_year=1991 if baseline == "normal_30y" else 2011,
        baseline_end_year=2020 if baseline == "normal_30y" else 2025,
        evidence_seasons=25 if baseline == "normal_30y" else 14,
        latest_archive_year=2025,
        snow_depth_cm_p25=(
            snow_depth_cm_p50 - 20 if snow_depth_cm_p50 is not None else None
        ),
        snow_depth_cm_p50=snow_depth_cm_p50,
        snow_depth_cm_p75=(
            snow_depth_cm_p50 + 20 if snow_depth_cm_p50 is not None else None
        ),
        prob_snow_depth_ge_30cm=0.8,
        prob_snow_depth_ge_50cm=0.65,
        avg_daily_snowfall_cm=4,
        prob_rain_risk=0.1,
        prob_freeze_thaw=0.2,
        avg_max_temperature_c=-1,
        avg_wind_gust_kmh=30,
        avg_snow_confidence_score=0.75,
        avg_conditions_score=0.7,
        source_model=source_model,
        computed_at=computed_at,
    )


def _run(
    source_key: str,
    *,
    initialized_at: datetime = datetime(2027, 1, 1, tzinfo=UTC),
    run_id: str | None = None,
) -> WeatherForecastRun:
    return WeatherForecastRun(
        forecast_run_id=run_id or f"run-{source_key}",
        forecast_source_key=source_key,
        provider_gateway="open-meteo",
        producer="ecmwf" if source_key == _PREFERRED_SOURCE else "noaa-ncep",
        provider_model_id=("ifs025" if source_key == _PREFERRED_SOURCE else "gefs05"),
        forecast_kind="ensemble_mean",
        model_initialization_time=initialized_at,
        provider_availability_time=initialized_at + timedelta(hours=7),
        ingested_at=initialized_at + timedelta(hours=7, minutes=15),
        completed_at=initialized_at + timedelta(hours=7, minutes=20),
        first_valid_date=initialized_at.date(),
        last_valid_date=initialized_at.date() + timedelta(days=30),
        status="complete",
        schema_version="forecast-v1",
        parser_version="open-meteo-v1",
        aggregation_policy_version="local-day-v1",
        provider_metadata={"update_interval_seconds": 21_600},
    )


def _served(
    day: date,
    source_key: str = _PREFERRED_SOURCE,
    *,
    ski_area_id: str = "area",
    initialized_at: datetime = datetime(2027, 1, 1, tzinfo=UTC),
    run_id: str | None = None,
    depth_cm: float | None = 60,
    is_complete: bool = True,
    elevation_m: int = 2000,
) -> ServedWeatherForecastDaily:
    run = _run(source_key, initialized_at=initialized_at, run_id=run_id)
    return ServedWeatherForecastDaily(
        run=run,
        daily=WeatherForecastDaily(
            forecast_run_id=run.forecast_run_id,
            ski_area_id=ski_area_id,
            valid_local_date=day,
            provider_timezone="Europe/Vienna",
            representative_elevation_m=elevation_m,
            request_latitude=47,
            request_longitude=11,
            snow_depth_cm=depth_cm,
            snow_depth_spread_cm=8 if depth_cm is not None else None,
            snowfall_cm=10,
            rain_mm=5,
            positive_degree_hours=6,
            temperature_2m_min_c=-6,
            temperature_2m_max_c=1,
            wind_speed_10m_max_kmh=30,
            wind_gusts_10m_max_kmh=50,
            is_complete=is_complete,
            completeness_metadata={"expected_hour_count": 24},
        ),
    )


def _context(
    window: TravelWindow,
    *,
    stale_run_ids: frozenset[str] = frozenset(),
) -> WeatherEvaluationContext:
    return WeatherEvaluationContext(
        intent=SearchIntent(
            constraints=SearchConstraints(travel_window=window),
        ),
        policy=load_search_policy(),
        stale_run_ids=stale_run_ids,
    )


def _candidate(
    *,
    ski_area_id: str = "area",
    climatology_rows: tuple[SnowClimatologyDaily, ...],
    forecast_rows: tuple[ServedWeatherForecastDaily, ...] = (),
) -> WeatherFactorCandidate:
    return WeatherFactorCandidate(
        ski_area_id=ski_area_id,
        climatology_rows=climatology_rows,
        forecast_rows=forecast_rows,
    )


def test_month_summary_prefers_latest_normal_rows_and_preserves_provenance() -> None:
    day = date(2027, 1, 2)
    rows = (
        _climatology(
            day,
            baseline="normal_30y",
            computed_at="2026-06-01T00:00:00+00:00",
            source_model="normal-old",
            snow_depth_cm_p50=50,
        ),
        _climatology(
            day,
            baseline="normal_30y",
            computed_at="2026-07-01T00:00:00+00:00",
            source_model="normal-current",
            snow_depth_cm_p50=80,
        ),
        _climatology(
            day,
            baseline="recent_15y",
            computed_at="2026-07-02T00:00:00+00:00",
            source_model="recent-newer",
            snow_depth_cm_p50=100,
        ),
    )

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(month=1)),
        candidate=_candidate(climatology_rows=rows),
    )

    assert summary is not None
    assert summary.mode == "climatology"
    assert summary.window_label == "January"
    assert summary.forecast is None
    assert summary.historical.source_model == "normal-current"
    assert summary.historical.computed_at == "2026-07-01T00:00:00+00:00"
    assert summary.historical.baseline_start_year == 1991
    assert summary.historical.baseline_end_year == 2020
    assert summary.historical.evidence_seasons == 25
    assert summary.historical.daily_profile[1].snow_depth_cm_p50 == 80
    assert summary.historical.provenance_status == "homogeneous"
    assert len(summary.historical.sources) == 1
    assert summary.historical.sources[0].profile_dates == ("01-02",)
    assert summary.interpretation == (
        "Historical weather patterns describe the requested travel window."
    )


def test_mixed_historical_rows_expose_exact_sources_without_synthetic_metadata() -> (
    None
):
    first_day = date(2027, 1, 2)
    second_day = first_day + timedelta(days=1)
    rows = (
        _climatology(
            first_day,
            baseline="normal_30y",
            computed_at="2026-07-01T00:00:00+00:00",
            source_model="normal-model",
        ),
        _climatology(
            second_day,
            baseline="recent_15y",
            computed_at="2026-07-02T00:00:00+00:00",
            source_model="recent-model",
        ),
    )

    summary = build_search_weather_evidence(
        context=_context(
            TravelWindow(start_date=first_day, end_date=second_day),
        ),
        candidate=_candidate(climatology_rows=rows),
    )

    assert summary is not None
    historical = summary.historical
    assert historical.provenance_status == "mixed"
    assert historical.source_label == "Mixed historical climatology sources"
    assert historical.source_model is None
    assert historical.computed_at is None
    assert historical.baseline_start_year is None
    assert historical.baseline_end_year is None
    assert historical.evidence_seasons is None
    assert historical.latest_archive_year is None
    assert {
        (
            source.source_model,
            source.computed_at,
            source.baseline_period,
            source.baseline_start_year,
            source.baseline_end_year,
            source.profile_dates,
        )
        for source in historical.sources
    } == {
        (
            "normal-model",
            "2026-07-01T00:00:00+00:00",
            "normal_30y",
            1991,
            2020,
            ("01-02",),
        ),
        (
            "recent-model",
            "2026-07-02T00:00:00+00:00",
            "recent_15y",
            2011,
            2025,
            ("01-03",),
        ),
    }


def test_mixed_elevations_are_exposed_without_synthetic_top_level_value() -> None:
    first_day = date(2027, 1, 2)
    second_day = first_day + timedelta(days=1)

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(month=1)),
        candidate=_candidate(
            climatology_rows=(
                _climatology(first_day, elevation_m=1800),
                _climatology(second_day, elevation_m=2200),
            ),
        ),
    )

    assert summary is not None
    assert summary.elevation_status == "mixed"
    assert summary.elevation_m is None
    assert {source.elevation_m for source in summary.historical.sources} == {
        1800,
        2200,
    }


def test_known_and_unknown_elevations_are_mixed() -> None:
    first_day = date(2027, 1, 2)
    second_day = first_day + timedelta(days=1)

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(month=1)),
        candidate=_candidate(
            climatology_rows=(
                _climatology(first_day, elevation_m=1800),
                _climatology(second_day, elevation_m=None),
            ),
        ),
    )

    assert summary is not None
    assert summary.elevation_status == "mixed"
    assert summary.elevation_m is None
    assert {source.elevation_m for source in summary.historical.sources} == {
        1800,
        None,
    }


def test_month_summary_uses_recent_rows_only_when_normal_is_absent() -> None:
    day = date(2027, 1, 3)
    recent = _climatology(day, baseline="recent_15y", snow_depth_cm_p50=70)

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(month=1)),
        candidate=_candidate(climatology_rows=(recent,)),
    )

    assert summary is not None
    assert summary.historical.source_label == "Recent 15-year snow climatology"
    assert summary.historical.daily_profile[2].snow_depth_cm_p50 == 70


def test_exact_dates_weight_repeated_calendar_dates_in_historical_evidence() -> None:
    start = date(2027, 1, 1)
    requested_dates = tuple(start + timedelta(days=offset) for offset in range(366))
    rows = tuple(
        _climatology(
            day,
            snow_depth_cm_p50=373.5 if day == start else 282,
        )
        for day in requested_dates
    )

    summary = build_search_weather_evidence(
        context=_context(
            TravelWindow(start_date=start, end_date=date(2028, 1, 1)),
        ),
        candidate=_candidate(climatology_rows=rows),
    )

    assert summary is not None
    assert summary.historical.snow_depth_cm_p50 == pytest.approx(282.5)
    assert summary.historical.sources[0].row_count == 366
    assert not any("365 of 366" in limitation for limitation in summary.limitations)
    assert "Daily details are shown for the first 31 dates." in summary.limitations


def test_exact_dates_use_fresh_complete_preferred_source_forecasts() -> None:
    requested = tuple(date(2027, 1, 2) + timedelta(days=offset) for offset in range(3))
    forecasts = (
        _served(requested[0], _FALLBACK_SOURCE, depth_cm=20),
        *(
            _served(day, _PREFERRED_SOURCE, depth_cm=60 + index)
            for index, day in enumerate(requested)
        ),
    )

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(start_date=requested[0], end_date=requested[-1])),
        candidate=_candidate(
            climatology_rows=tuple(_climatology(day) for day in requested),
            forecast_rows=forecasts,
        ),
    )

    assert summary is not None
    assert summary.mode == "forecast_assisted"
    assert summary.forecast is not None
    assert summary.forecast.usable_date_count == 3
    assert summary.forecast.requested_date_count == 3
    assert summary.forecast.average_forecast_share == pytest.approx(0.8)
    assert [point.snow_depth_cm for point in summary.forecast.daily_profile] == [
        60,
        61,
        62,
    ]
    assert summary.forecast.daily_profile[0].rain_risk is not None
    assert summary.forecast.daily_profile[0].thaw_risk is not None
    assert summary.forecast.provenance_status == "homogeneous"
    assert len(summary.forecast.sources) == 1
    assert summary.forecast.sources[0].profile_dates == tuple(
        day.isoformat() for day in requested
    )
    assert summary.historical is not None
    assert summary.interpretation == (
        "Fresh forecast data adds to historical weather patterns for 3 of 3 "
        "requested days."
    )


def test_mixed_forecast_rows_expose_exact_sources_without_synthetic_issuance() -> None:
    first_day = date(2027, 1, 2)
    second_day = first_day + timedelta(days=1)
    preferred_issued_at = datetime(2027, 1, 1, tzinfo=UTC)
    fallback_issued_at = preferred_issued_at + timedelta(hours=6)

    summary = build_search_weather_evidence(
        context=_context(
            TravelWindow(start_date=first_day, end_date=second_day),
        ),
        candidate=_candidate(
            climatology_rows=(
                _climatology(first_day),
                _climatology(second_day),
            ),
            forecast_rows=(
                _served(
                    first_day,
                    _PREFERRED_SOURCE,
                    initialized_at=preferred_issued_at,
                    run_id="preferred-run",
                ),
                _served(
                    second_day,
                    _FALLBACK_SOURCE,
                    initialized_at=fallback_issued_at,
                    run_id="fallback-run",
                ),
            ),
        ),
    )

    assert summary is not None
    assert summary.forecast is not None
    forecast = summary.forecast
    assert forecast.provenance_status == "mixed"
    assert forecast.source_label == "Mixed forecast sources"
    assert forecast.source_model is None
    assert forecast.issued_at is None
    assert {
        (
            source.forecast_run_id,
            source.forecast_source_key,
            source.source_label,
            source.source_model,
            source.issued_at,
            source.profile_dates,
        )
        for source in forecast.sources
    } == {
        (
            "preferred-run",
            _PREFERRED_SOURCE,
            "ecmwf",
            "ifs025",
            preferred_issued_at.isoformat(),
            (first_day.isoformat(),),
        ),
        (
            "fallback-run",
            _FALLBACK_SOURCE,
            "noaa-ncep",
            "gefs05",
            fallback_issued_at.isoformat(),
            (second_day.isoformat(),),
        ),
    }


def test_exact_dates_report_partial_usable_forecast_coverage() -> None:
    requested = tuple(date(2027, 1, 2) + timedelta(days=offset) for offset in range(3))

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(start_date=requested[0], end_date=requested[-1])),
        candidate=_candidate(
            climatology_rows=tuple(_climatology(day) for day in requested),
            forecast_rows=tuple(_served(day) for day in requested[:2]),
        ),
    )

    assert summary is not None
    assert summary.mode == "forecast_assisted"
    assert summary.forecast is not None
    assert summary.forecast.coverage_status == "partial"
    assert summary.forecast.usable_date_count == 2
    assert len(summary.forecast.daily_profile) == 3
    assert summary.forecast.daily_profile[2].snow_depth_cm is None
    assert (
        "Up-to-date forecast coverage is available for 2 of 3 days."
        in summary.limitations
    )


def test_historical_profile_preserves_missing_middle_requested_day() -> None:
    requested = tuple(date(2027, 1, 1) + timedelta(days=offset) for offset in range(3))

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(month=1)),
        candidate=_candidate(
            climatology_rows=(
                _climatology(requested[0], snow_depth_cm_p50=70),
                _climatology(requested[2], snow_depth_cm_p50=90),
            ),
        ),
    )

    assert summary is not None
    assert len(summary.historical.daily_profile) == 31
    assert [
        point.date_or_month_day for point in summary.historical.daily_profile[:3]
    ] == [
        "01-01",
        "01-02",
        "01-03",
    ]
    assert [
        point.snow_depth_cm_p50 for point in summary.historical.daily_profile[:3]
    ] == [
        70,
        None,
        90,
    ]
    assert all(
        value is None
        for key, value in summary.historical.daily_profile[1].model_dump().items()
        if key != "date_or_month_day"
    )
    assert summary.historical.sources[0].row_count == 2
    assert summary.historical.sources[0].profile_dates == ("01-01", "01-03")
    assert "Historical weather patterns cover 2 of 31 requested days." in (
        summary.limitations
    )


def test_forecast_profile_preserves_missing_middle_requested_day() -> None:
    requested = tuple(date(2027, 1, 2) + timedelta(days=offset) for offset in range(3))

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(start_date=requested[0], end_date=requested[-1])),
        candidate=_candidate(
            climatology_rows=tuple(_climatology(day) for day in requested),
            forecast_rows=(
                _served(requested[0], depth_cm=60),
                _served(requested[2], depth_cm=62),
            ),
        ),
    )

    assert summary is not None
    assert summary.mode == "forecast_assisted"
    assert summary.forecast is not None
    assert [point.date_or_month_day for point in summary.forecast.daily_profile] == [
        requested[0].isoformat(),
        requested[1].isoformat(),
        requested[2].isoformat(),
    ]
    assert [point.snow_depth_cm for point in summary.forecast.daily_profile] == [
        60,
        None,
        62,
    ]
    assert all(
        value is None
        for key, value in summary.forecast.daily_profile[1].model_dump().items()
        if key != "date_or_month_day"
    )
    assert summary.forecast.usable_date_count == 2
    assert summary.forecast.requested_date_count == 3
    assert summary.forecast.sources[0].row_count == 2
    assert summary.forecast.sources[0].profile_dates == (
        requested[0].isoformat(),
        requested[2].isoformat(),
    )


def test_stale_forecast_falls_back_to_climatology_with_explicit_limitation() -> None:
    day = date(2027, 1, 2)
    stale = _served(day, run_id="stale-run")

    summary = build_search_weather_evidence(
        context=_context(
            TravelWindow(start_date=day, end_date=day),
            stale_run_ids=frozenset({"stale-run"}),
        ),
        candidate=_candidate(
            climatology_rows=(_climatology(day),),
            forecast_rows=(stale,),
        ),
    )

    assert summary is not None
    assert summary.mode == "climatology"
    assert summary.forecast is None
    assert "Older forecasts were not used." in summary.limitations
    assert (
        "No up-to-date forecast is available for the requested dates."
        in summary.limitations
    )


def test_incomplete_forecast_falls_back_without_exposing_values() -> None:
    day = date(2027, 1, 2)

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(start_date=day, end_date=day)),
        candidate=_candidate(
            climatology_rows=(_climatology(day),),
            forecast_rows=(_served(day, is_complete=False),),
        ),
    )

    assert summary is not None
    assert summary.mode == "climatology"
    assert summary.forecast is None
    assert "Incomplete forecast days were not used." in summary.limitations
    assert (
        "No up-to-date forecast is available for the requested dates."
        in summary.limitations
    )


def test_summary_is_omitted_without_trustworthy_historical_evidence() -> None:
    day = date(2027, 1, 2)
    context = _context(TravelWindow(start_date=day, end_date=day))

    assert (
        build_search_weather_evidence(
            context=context,
            candidate=_candidate(climatology_rows=()),
        )
        is None
    )
    assert (
        build_search_weather_evidence(
            context=context,
            candidate=_candidate(
                climatology_rows=(),
                forecast_rows=(_served(day),),
            ),
        )
        is None
    )


def test_profiles_preserve_null_depth_and_are_bounded_to_31_points() -> None:
    start = date(2027, 1, 1)
    requested = tuple(start + timedelta(days=offset) for offset in range(40))
    climate = tuple(
        _climatology(
            day,
            snow_depth_cm_p50=None if index == 0 else 80,
        )
        for index, day in enumerate(requested)
    )
    forecasts = tuple(
        _served(
            day,
            (_PREFERRED_SOURCE if index <= 15 else _FALLBACK_SOURCE),
            depth_cm=None if index == 0 else 60,
        )
        for index, day in enumerate(requested[:31])
    )

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(start_date=start, end_date=requested[-1])),
        candidate=_candidate(climatology_rows=climate, forecast_rows=forecasts),
    )

    assert summary is not None
    assert summary.mode == "forecast_assisted"
    assert summary.forecast is not None
    assert len(summary.historical.daily_profile) == 31
    assert len(summary.forecast.daily_profile) == 31
    assert summary.historical.daily_profile[0].snow_depth_cm_p50 is None
    assert summary.forecast.daily_profile[0].snow_depth_cm is None
    assert summary.forecast.daily_profile[0].rain_risk is None
    assert summary.forecast.daily_profile[0].thaw_risk is None
    with pytest.raises(ValidationError):
        summary.mode = "climatology"


def test_forecast_coverage_is_named_independently_from_freshness() -> None:
    requested = tuple(date(2027, 1, 2) + timedelta(days=offset) for offset in range(3))

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(start_date=requested[0], end_date=requested[-1])),
        candidate=_candidate(
            climatology_rows=tuple(_climatology(day) for day in requested),
            forecast_rows=tuple(_served(day) for day in requested[:2]),
        ),
    )

    assert summary is not None
    assert summary.forecast is not None
    assert summary.forecast.coverage_status == "partial"
    assert not hasattr(summary.forecast, "freshness")


def test_weather_evidence_request_and_status_responses_are_frozen() -> None:
    request = SearchWeatherEvidenceRequest(
        ski_area_id="area",
        intent=SearchIntent(
            constraints=SearchConstraints(travel_window=TravelWindow(month=1))
        ),
    )
    unavailable = SearchWeatherEvidenceUnavailableResponse(
        weather_evidence_version="search-weather-evidence-v1",
        ski_area_id=request.ski_area_id,
        evaluated_at="2027-01-01T00:00:00+00:00",
        cache_valid_until="2027-01-01T00:05:00+00:00",
        unavailable_reason="historical_evidence_unavailable",
        limitations=("No trustworthy mid-mountain historical evidence is available.",),
    )

    assert unavailable.status == "unavailable"
    with pytest.raises(ValidationError):
        SearchWeatherEvidenceAvailableResponse(
            weather_evidence_version="search-weather-evidence-v1",
            ski_area_id="area",
            evaluated_at="2027-01-01T00:00:00+00:00",
            cache_valid_until="2027-01-01T00:05:00+00:00",
        )


def test_one_area_endpoint_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = load_catalog_from_path(CATALOG_PATH)
    manifest = CatalogTrustManifest.model_validate_json(
        DEFAULT_TRUST_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    ski_area_id = snapshot.ski_areas[0].ski_area_id
    start = date(2027, 2, 1)
    requested_dates = tuple(start + timedelta(days=offset) for offset in range(31))
    climatology_rows = tuple(
        _climatology(
            valid_date,
            ski_area_id=ski_area_id,
            baseline="normal_30y" if index < 16 else "recent_15y",
            computed_at=f"2026-07-{index + 1:02d}T00:00:00+00:00",
            source_model=f"maximum-history-{index}",
        )
        for index, valid_date in enumerate(requested_dates)
    )
    forecast_rows = tuple(
        _served(
            valid_date,
            _PREFERRED_SOURCE if index < 16 else _FALLBACK_SOURCE,
            ski_area_id=ski_area_id,
            initialized_at=datetime(2027, 2, 1, tzinfo=UTC),
            run_id=f"maximum-forecast-{index}",
        )
        for index, valid_date in enumerate(requested_dates)
    )

    class ClimatologyRepository:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def list_daily_rows_for_ski_areas_window(self, ski_area_ids, **kwargs):
            self.calls.append({"ski_area_ids": ski_area_ids, **kwargs})
            return {
                (ski_area_id, "mid", "normal_30y"): tuple(
                    row
                    for row in climatology_rows
                    if row.baseline_period == "normal_30y"
                ),
                (ski_area_id, "mid", "recent_15y"): tuple(
                    row
                    for row in climatology_rows
                    if row.baseline_period == "recent_15y"
                ),
            }

    class ForecastRepository:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def list_latest_daily_rows(self, **kwargs):
            self.calls.append(kwargs)
            return forecast_rows

    climatology_repository = ClimatologyRepository()
    forecast_repository = ForecastRepository()
    intent = SearchIntent(
        constraints=SearchConstraints(
            travel_window=TravelWindow(start_date=start, end_date=requested_dates[-1]),
        ),
    )
    reference_time = datetime(2027, 2, 1, 12, tzinfo=UTC)

    def build_response():
        return get_search_weather_evidence(
            intent=intent,
            ski_area_id=ski_area_id,
            catalog_snapshot=snapshot,
            trust_manifest=manifest,
            climatology_repository=climatology_repository,
            forecast_repository=forecast_repository,
            reference_time=reference_time,
        )

    warm_response = build_response()
    durations_ms: list[float] = []
    for _ in range(100):
        started = time.perf_counter()
        response = build_response()
        durations_ms.append((time.perf_counter() - started) * 1_000)
    p95_ms = statistics.quantiles(durations_ms, n=100, method="inclusive")[94]

    route_app = FastAPI()
    route_app.include_router(router, prefix="/api")
    monkeypatch.setattr(
        "app.api.routes.get_search_weather_evidence",
        lambda **_kwargs: response,
    )
    with TestClient(route_app) as route_client:
        route_response = route_client.post(
            "/api/search/weather-evidence",
            json={
                "ski_area_id": ski_area_id,
                "intent": {
                    "constraints": {
                        "travel_window": {
                            "start_date": start.isoformat(),
                            "end_date": requested_dates[-1].isoformat(),
                        }
                    }
                },
            },
        )
    serialized_bytes = len(route_response.content)

    assert warm_response.status == "available"
    assert response.status == "available"
    assert response.evidence.forecast is not None
    assert len(response.evidence.historical.daily_profile) == 31
    assert len(response.evidence.forecast.daily_profile) == 31
    assert len(response.evidence.historical.sources) == 31
    assert len(response.evidence.forecast.sources) == 31
    assert route_response.status_code == 200
    assert all(
        call["ski_area_ids"] == (ski_area_id,) for call in climatology_repository.calls
    )
    assert all(
        call["ski_area_ids"] == (ski_area_id,) for call in forecast_repository.calls
    )
    print(
        "one_area_endpoint_cost "
        f"route_envelope_bytes={serialized_bytes} p95_ms={p95_ms:.3f} iterations=100"
    )
    assert serialized_bytes <= 131_072
    assert p95_ms <= 25
