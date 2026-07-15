from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.domain.weather_forecast import (
    ServedWeatherForecastDaily,
    WeatherForecastDaily,
    WeatherForecastRun,
)

pytestmark = pytest.mark.db_free


def _run(**updates: object) -> WeatherForecastRun:
    values: dict[str, object] = {
        "forecast_run_id": "run",
        "forecast_source_key": "ecmwf_ifs025_ensemble_mean",
        "provider_gateway": "open-meteo",
        "producer": "ecmwf",
        "provider_model_id": "ifs025",
        "forecast_kind": "ensemble_mean",
        "model_initialization_time": datetime(2027, 1, 1, 0, tzinfo=UTC),
        "provider_availability_time": datetime(2027, 1, 1, 7, tzinfo=UTC),
        "ingested_at": datetime(2027, 1, 1, 7, 15, tzinfo=UTC),
        "first_valid_date": date(2027, 1, 1),
        "last_valid_date": date(2027, 1, 16),
        "status": "building",
        "schema_version": "forecast-v1",
        "parser_version": "open-meteo-v1",
        "aggregation_policy_version": "local-day-v1",
        "provider_metadata": {},
    }
    values.update(updates)
    return WeatherForecastRun.model_validate(values)


def _daily() -> WeatherForecastDaily:
    return WeatherForecastDaily(
        forecast_run_id="run",
        ski_area_id="area",
        valid_local_date=date(2027, 1, 2),
        provider_timezone="Europe/Warsaw",
        elevation_band="mid",
        representative_elevation_m=2000,
        request_latitude=46,
        request_longitude=7,
        snow_depth_cm=40,
        snow_depth_spread_cm=8,
        snowfall_cm=10,
        rain_mm=0,
        positive_degree_hours=2,
        temperature_2m_min_c=-5,
        temperature_2m_max_c=1,
        freezing_level_mean_m=1500,
        freezing_level_max_m=2100,
        wind_speed_10m_max_kmh=30,
        wind_gusts_10m_max_kmh=55,
        ensemble_member_count=51,
        is_complete=True,
        completeness_metadata={"hour_count": 24},
    )


def test_run_state_requires_matching_completion_fields() -> None:
    with pytest.raises(ValidationError, match="complete run needs completed_at"):
        _run(status="complete")

    completed = _run(
        status="complete",
        completed_at=datetime(2027, 1, 1, 8, tzinfo=UTC),
    )
    assert completed.failure_reason is None


def test_daily_lead_days_use_model_initialization_local_calendar_date() -> None:
    served = ServedWeatherForecastDaily(
        run=_run(
            model_initialization_time=datetime(2027, 1, 1, 23, tzinfo=UTC),
            provider_availability_time=datetime(2027, 1, 2, 6, tzinfo=UTC),
            ingested_at=datetime(2027, 1, 2, 6, 15, tzinfo=UTC),
        ),
        daily=_daily(),
    )

    assert served.lead_days == 0


def test_forecast_models_require_timezone_aware_run_times() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _run(model_initialization_time=datetime(2027, 1, 1, 0))
