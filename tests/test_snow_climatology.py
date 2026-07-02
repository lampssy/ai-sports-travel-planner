from contextlib import nullcontext

import pytest

from app.data.rebuild_snow_climatology import (
    SnowClimatologyRebuildResult,
    build_snow_climatology_rows,
)
from app.data.rebuild_snow_climatology import main as rebuild_climatology_main
from app.domain.catalog import SkiArea
from app.domain.models import RawWeatherObservation


def _ski_area() -> SkiArea:
    return SkiArea(
        ski_area_id="tignes-ski-area",
        name="Tignes",
        latitude=45.47,
        longitude=6.9,
        base_elevation_m=1550,
        summit_elevation_m=3450,
        season_start_month=11,
        season_end_month=5,
    )


def _raw_weather_observation(
    observed_on: str,
    *,
    snow_depth_m: float | None,
    rain_sum_mm: float | None,
    min_temp: float,
    max_temp: float,
    snowfall_cm: float = 4.0,
    elevation_band: str = "mid",
) -> RawWeatherObservation:
    return RawWeatherObservation(
        ski_area_id="tignes-ski-area",
        resort_name="Tignes",
        elevation_band=elevation_band,
        elevation_m=2500,
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
        snowfall_cm=snowfall_cm,
        snow_depth_m=snow_depth_m,
        precipitation_sum_mm=rain_sum_mm,
        rain_sum_mm=rain_sum_mm,
        precipitation_hours=2.0 if rain_sum_mm else 0.0,
        snowfall_water_equivalent_sum_mm=3.0,
        temperature_2m_max_c=max_temp,
        temperature_2m_min_c=min_temp,
        apparent_temperature_2m_max_c=max_temp - 2,
        apparent_temperature_2m_min_c=min_temp - 2,
        cloud_cover_mean_pct=65.0,
        sunshine_duration_seconds=12000.0,
        visibility_min_m=None,
        wind_speed_10m_max_kmh=18,
        wind_gusts_10m_max_kmh=24,
        weather_code=3,
        record_type="archive",
        source="open-meteo",
        source_model="best_match",
    )


def test_build_snow_climatology_rows_computes_daily_baseline_features() -> None:
    rows = build_snow_climatology_rows(
        ski_area=_ski_area(),
        observations=(
            _raw_weather_observation(
                "2020-03-10",
                snow_depth_m=0.2,
                rain_sum_mm=0,
                min_temp=-5,
                max_temp=-1,
            ),
            _raw_weather_observation(
                "2021-03-10",
                snow_depth_m=0.4,
                rain_sum_mm=2,
                min_temp=-2,
                max_temp=2,
            ),
            _raw_weather_observation(
                "2022-03-10",
                snow_depth_m=0.8,
                rain_sum_mm=0,
                min_temp=-6,
                max_temp=-2,
            ),
        ),
        baseline_end_year=2022,
        computed_at="2026-06-15T00:00:00+00:00",
    )

    normal = next(row for row in rows if row.baseline_period == "normal_30y")
    recent = next(row for row in rows if row.baseline_period == "recent_15y")
    assert normal.evidence_seasons == 3
    assert normal.baseline_start_year == 1993
    assert normal.baseline_end_year == 2022
    assert normal.snow_depth_cm_p25 == 30.0
    assert normal.snow_depth_cm_p50 == 40.0
    assert normal.snow_depth_cm_p75 == 60.0
    assert normal.prob_snow_depth_ge_30cm == pytest.approx(2 / 3, abs=0.0001)
    assert normal.prob_snow_depth_ge_50cm == pytest.approx(1 / 3, abs=0.0001)
    assert normal.prob_rain_risk == pytest.approx(1 / 3, abs=0.0001)
    assert normal.prob_freeze_thaw == pytest.approx(1 / 3, abs=0.0001)
    assert normal.avg_daily_snowfall_cm == 4.0
    assert normal.elevation_m == 2500
    assert recent.evidence_seasons == 3
    assert recent.baseline_start_year == 2008


def test_build_snow_climatology_rows_filters_baseline_periods() -> None:
    rows = build_snow_climatology_rows(
        ski_area=_ski_area(),
        observations=(
            _raw_weather_observation(
                "1990-03-10",
                snow_depth_m=3.0,
                rain_sum_mm=0,
                min_temp=-8,
                max_temp=-4,
            ),
            _raw_weather_observation(
                "2022-03-10",
                snow_depth_m=0.4,
                rain_sum_mm=0,
                min_temp=-4,
                max_temp=-1,
            ),
        ),
        baseline_end_year=2022,
        computed_at="2026-06-15T00:00:00+00:00",
    )

    normal = next(row for row in rows if row.baseline_period == "normal_30y")
    recent = next(row for row in rows if row.baseline_period == "recent_15y")
    assert normal.evidence_seasons == 1
    assert normal.snow_depth_cm_p50 == 40.0
    assert recent.evidence_seasons == 1
    assert recent.snow_depth_cm_p50 == 40.0


def test_climatology_command_main_forwards_stay_destinations_and_baseline(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def _stub_rebuild(**kwargs):
        captured.update(kwargs)
        return SnowClimatologyRebuildResult(targeted_ski_areas=2)

    monkeypatch.setattr(
        "app.data.rebuild_snow_climatology.rebuild_snow_climatology",
        _stub_rebuild,
    )
    monkeypatch.setattr(
        "app.data.rebuild_snow_climatology.configure_cli_observability",
        lambda **_kwargs: nullcontext(),
    )
    monkeypatch.setattr(
        "app.data.rebuild_snow_climatology.job_span",
        lambda *_args, **_kwargs: nullcontext(),
    )
    monkeypatch.setattr(
        "app.data.rebuild_snow_climatology.record_snow_climatology_rebuild_result",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "rebuild_snow_climatology",
            "--database-url",
            "postgresql://unused",
            "--ski-area",
            "tignes-ski-area",
            "--stay-destination",
            "pinzolo",
            "--stay-destination",
            "folgarida-marilleva",
            "--baseline-end-year",
            "2025",
            "--source-model",
            "snowcast_empirical_v1",
        ],
    )

    rebuild_climatology_main()

    assert captured["ski_area_ids"] == ("tignes-ski-area",)
    assert captured["stay_destination_ids"] == (
        "pinzolo",
        "folgarida-marilleva",
    )
    assert captured["baseline_end_year"] == 2025


def test_climatology_command_unknown_target_records_failure_and_raises(
    monkeypatch,
) -> None:
    telemetry: list[dict[str, object]] = []

    def _raise_unknown_target(**_kwargs) -> None:
        raise ValueError(
            "unknown catalog targets: areas=[], "
            "stay_destinations=['unknown-destination']"
        )

    monkeypatch.setattr(
        "app.data.rebuild_snow_climatology.rebuild_snow_climatology",
        _raise_unknown_target,
    )
    monkeypatch.setattr(
        "app.data.rebuild_snow_climatology.configure_cli_observability",
        lambda **_kwargs: nullcontext(),
    )
    monkeypatch.setattr(
        "app.data.rebuild_snow_climatology.job_span",
        lambda *_args, **_kwargs: nullcontext(),
    )
    monkeypatch.setattr(
        "app.data.rebuild_snow_climatology.record_snow_climatology_rebuild_result",
        lambda **kwargs: telemetry.append(kwargs),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "rebuild_snow_climatology",
            "--database-url",
            "postgresql://unused",
            "--stay-destination",
            "unknown-destination",
        ],
    )

    with pytest.raises(ValueError, match="unknown catalog targets"):
        rebuild_climatology_main()

    assert telemetry == [
        {
            "source_model": "snowcast_empirical_v1",
            "status": "failure",
            "targeted_ski_areas": 0,
            "raw_rows_read": 0,
            "climatology_rows_written": 0,
            "weak_coverage_groups": 0,
        }
    ]
