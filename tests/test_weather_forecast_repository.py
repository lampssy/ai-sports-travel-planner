from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.data.weather_forecast_repository import (
    ForecastPublicationError,
    WeatherForecastRepository,
)
from app.domain.weather_forecast import WeatherForecastDaily, WeatherForecastRun

AREA_ONE = "kitzbuhel-ski-area"
AREA_TWO = "mayrhofen-ski-area"


def _run(
    run_id: str,
    *,
    initialized_at: datetime,
    source_key: str = "ecmwf_ifs025_ensemble_mean",
) -> WeatherForecastRun:
    return WeatherForecastRun(
        forecast_run_id=run_id,
        forecast_source_key=source_key,
        provider_gateway="open-meteo",
        producer="ecmwf" if source_key.startswith("ecmwf") else "noaa",
        provider_model_id="ifs025" if source_key.startswith("ecmwf") else "gefs05",
        forecast_kind="ensemble_mean",
        model_initialization_time=initialized_at,
        provider_availability_time=initialized_at + timedelta(hours=7),
        ingested_at=initialized_at + timedelta(hours=7, minutes=15),
        first_valid_date=initialized_at.date(),
        last_valid_date=initialized_at.date() + timedelta(days=30),
        status="building",
        schema_version="forecast-v1",
        parser_version="open-meteo-v1",
        aggregation_policy_version="local-day-v1",
        provider_metadata={"cycle": initialized_at.isoformat()},
    )


def _daily(run_id: str, ski_area_id: str, valid_date: date) -> WeatherForecastDaily:
    return WeatherForecastDaily(
        forecast_run_id=run_id,
        ski_area_id=ski_area_id,
        valid_local_date=valid_date,
        provider_timezone="Europe/Vienna",
        elevation_band="mid",
        representative_elevation_m=2000,
        request_latitude=47,
        request_longitude=12,
        snow_depth_cm=50,
        snow_depth_spread_cm=10,
        snowfall_cm=5,
        rain_mm=0,
        positive_degree_hours=0,
        temperature_2m_min_c=-8,
        temperature_2m_max_c=-1,
        wind_speed_10m_max_kmh=20,
        wind_gusts_10m_max_kmh=35,
        ensemble_member_count=51,
        is_complete=True,
        completeness_metadata={"hour_count": 24},
    )


def test_complete_run_advances_heads_and_bulk_reads_latest_rows() -> None:
    repository = WeatherForecastRepository()
    initialized_at = datetime(2027, 1, 1, tzinfo=UTC)
    run = _run("run-1", initialized_at=initialized_at)
    repository.create_building_run(run)
    repository.insert_daily_rows(
        run.forecast_run_id,
        (
            _daily("run-1", AREA_ONE, date(2027, 1, 2)),
            _daily("run-1", AREA_TWO, date(2027, 1, 2)),
        ),
    )

    repository.complete_run_and_advance_heads(
        "run-1",
        publishable_ski_area_ids=(AREA_ONE, AREA_TWO),
        completed_at=datetime(2027, 1, 1, 8, tzinfo=UTC),
    )
    assert (
        repository.find_complete_run_id(
            "ecmwf_ifs025_ensemble_mean",
            initialized_at,
            (AREA_ONE, AREA_TWO),
        )
        == "run-1"
    )
    rows = repository.list_latest_daily_rows(
        ski_area_ids=(AREA_ONE, AREA_TWO),
        start_date=date(2027, 1, 2),
        end_date=date(2027, 1, 2),
        source_keys=("ecmwf_ifs025_ensemble_mean",),
    )

    assert {item.daily.ski_area_id for item in rows} == {AREA_ONE, AREA_TWO}
    assert {item.run.forecast_run_id for item in rows} == {"run-1"}
    assert all(item.run.status == "complete" for item in rows)
    heads = repository.list_heads()
    assert {(item.ski_area_id, item.forecast_source_key) for item in heads} == {
        (AREA_ONE, "ecmwf_ifs025_ensemble_mean"),
        (AREA_TWO, "ecmwf_ifs025_ensemble_mean"),
    }
    assert {item.run.forecast_run_id for item in heads} == {"run-1"}


def test_complete_run_lookup_requires_coverage_for_every_requested_area() -> None:
    repository = WeatherForecastRepository()
    initialized_at = datetime(2027, 1, 1, tzinfo=UTC)
    run = _run("run-partial", initialized_at=initialized_at)
    repository.create_building_run(run)
    repository.insert_daily_rows(
        run.forecast_run_id,
        (_daily("run-partial", AREA_ONE, date(2027, 1, 2)),),
    )
    repository.complete_run_and_advance_heads(
        "run-partial",
        publishable_ski_area_ids=(AREA_ONE,),
        completed_at=datetime(2027, 1, 1, 8, tzinfo=UTC),
    )

    assert (
        repository.find_complete_run_id(
            "ecmwf_ifs025_ensemble_mean",
            initialized_at,
            (AREA_ONE,),
        )
        == "run-partial"
    )
    assert (
        repository.find_complete_run_id(
            "ecmwf_ifs025_ensemble_mean",
            initialized_at,
            (AREA_ONE, AREA_TWO),
        )
        is None
    )


def test_partial_new_run_preserves_previous_head_for_missing_area() -> None:
    repository = WeatherForecastRepository()
    first = _run("run-old", initialized_at=datetime(2027, 1, 1, tzinfo=UTC))
    repository.create_building_run(first)
    repository.insert_daily_rows(
        "run-old",
        (
            _daily("run-old", AREA_ONE, date(2027, 1, 2)),
            _daily("run-old", AREA_TWO, date(2027, 1, 2)),
        ),
    )
    repository.complete_run_and_advance_heads(
        "run-old",
        publishable_ski_area_ids=(AREA_ONE, AREA_TWO),
        completed_at=datetime(2027, 1, 1, 8, tzinfo=UTC),
    )

    second = _run("run-new", initialized_at=datetime(2027, 1, 2, tzinfo=UTC))
    repository.create_building_run(second)
    repository.insert_daily_rows(
        "run-new",
        (_daily("run-new", AREA_ONE, date(2027, 1, 2)),),
    )
    repository.complete_run_and_advance_heads(
        "run-new",
        publishable_ski_area_ids=(AREA_ONE,),
        completed_at=datetime(2027, 1, 2, 8, tzinfo=UTC),
    )

    rows = repository.list_latest_daily_rows(
        ski_area_ids=(AREA_ONE, AREA_TWO),
        start_date=date(2027, 1, 2),
        end_date=date(2027, 1, 2),
        source_keys=("ecmwf_ifs025_ensemble_mean",),
    )
    run_by_area = {item.daily.ski_area_id: item.run.forecast_run_id for item in rows}
    assert run_by_area == {AREA_ONE: "run-new", AREA_TWO: "run-old"}


def test_publication_rejects_area_without_complete_rows_and_keeps_run_building() -> (
    None
):
    repository = WeatherForecastRepository()
    run = _run("run-incomplete", initialized_at=datetime(2027, 1, 1, tzinfo=UTC))
    repository.create_building_run(run)
    repository.insert_daily_rows(
        "run-incomplete",
        (_daily("run-incomplete", AREA_ONE, date(2027, 1, 2)),),
    )

    with pytest.raises(ForecastPublicationError, match=AREA_TWO):
        repository.complete_run_and_advance_heads(
            "run-incomplete",
            publishable_ski_area_ids=(AREA_ONE, AREA_TWO),
            completed_at=datetime(2027, 1, 1, 8, tzinfo=UTC),
        )

    assert repository.get_run("run-incomplete").status == "building"


def test_retention_never_purges_a_head_referenced_run() -> None:
    repository = WeatherForecastRepository()
    now = datetime(2027, 1, 1, tzinfo=UTC)
    old_time = now - timedelta(days=365 * 6)
    protected = _run("old-head", initialized_at=old_time)
    purgeable = _run("old-unreferenced", initialized_at=old_time + timedelta(hours=6))
    for run, area in ((protected, AREA_ONE), (purgeable, AREA_TWO)):
        repository.create_building_run(run)
        repository.insert_daily_rows(
            run.forecast_run_id,
            (_daily(run.forecast_run_id, area, old_time.date()),),
        )
        repository.complete_run_and_advance_heads(
            run.forecast_run_id,
            publishable_ski_area_ids=(area,),
            completed_at=run.ingested_at + timedelta(minutes=15),
        )

    result = repository.apply_retention(now)

    assert result.protected_head_runs == 2
    assert repository.get_run("old-head") is not None
    assert repository.get_run("old-unreferenced") is not None

    replacement = _run("replacement", initialized_at=now - timedelta(days=1))
    repository.create_building_run(replacement)
    repository.insert_daily_rows(
        "replacement",
        (_daily("replacement", AREA_TWO, now.date()),),
    )
    repository.complete_run_and_advance_heads(
        "replacement",
        publishable_ski_area_ids=(AREA_TWO,),
        completed_at=replacement.ingested_at + timedelta(minutes=15),
    )
    result = repository.apply_retention(now)

    assert result.deleted_complete_runs == 1
    assert repository.get_run("old-unreferenced") is None
    assert repository.get_run("old-head") is not None
