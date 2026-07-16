from __future__ import annotations

import math
import statistics
import time
from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domain.models import SnowClimatologyDaily
from app.domain.search_factors.weather import (
    WeatherEvaluationContext,
    WeatherFactorCandidate,
)
from app.domain.search_policy import load_search_policy
from app.domain.search_ranking import FactorScoreBreakdown, GroupScoreBreakdown
from app.domain.search_v4_models import SearchConstraints, SearchIntent, TravelWindow
from app.domain.search_v4_service import (
    SearchV4AccessSummary,
    SearchV4Configuration,
    SearchV4PassPriceSummary,
    SearchV4PassSummary,
    SearchV4RecommendationGroup,
    SearchV4Response,
)
from app.domain.search_weather_evidence import build_search_weather_evidence
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
) -> SnowClimatologyDaily:
    return SnowClimatologyDaily(
        ski_area_id=ski_area_id,
        resort_name=ski_area_id.title(),
        elevation_band="mid",
        elevation_m=2000,
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
) -> ServedWeatherForecastDaily:
    run = _run(source_key, initialized_at=initialized_at, run_id=run_id)
    return ServedWeatherForecastDaily(
        run=run,
        daily=WeatherForecastDaily(
            forecast_run_id=run.forecast_run_id,
            ski_area_id=ski_area_id,
            valid_local_date=day,
            provider_timezone="Europe/Vienna",
            representative_elevation_m=2000,
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
    assert summary.historical.daily_profile[0].snow_depth_cm_p50 == 80


def test_month_summary_uses_recent_rows_only_when_normal_is_absent() -> None:
    day = date(2027, 1, 3)
    recent = _climatology(day, baseline="recent_15y", snow_depth_cm_p50=70)

    summary = build_search_weather_evidence(
        context=_context(TravelWindow(month=1)),
        candidate=_candidate(climatology_rows=(recent,)),
    )

    assert summary is not None
    assert summary.historical.source_label == "Recent 15-year snow climatology"
    assert summary.historical.daily_profile[0].snow_depth_cm_p50 == 70


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
    assert summary.historical is not None


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
    assert summary.forecast.freshness == "partial"
    assert summary.forecast.usable_date_count == 2
    assert len(summary.forecast.daily_profile) == 2
    assert any("2 of 3" in limitation for limitation in summary.limitations)


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
    assert any("stale" in limitation.lower() for limitation in summary.limitations)


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
    assert any("incomplete" in item.lower() for item in summary.limitations)


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


def _factor_rows() -> tuple[FactorScoreBreakdown, ...]:
    profile = tuple(
        {
            "valid_date": (date(2027, 1, 1) + timedelta(days=offset)).isoformat(),
            "climatology_utility": 0.72,
            "forecast_source_key": _PREFERRED_SOURCE if offset < 14 else None,
            "forecast_run_id": "run-ecmwf" if offset < 14 else None,
            "forecast_lead_days": offset if offset < 14 else None,
            "forecast_share": 0.8 if offset < 6 else 0.4 if offset < 14 else 0,
            "snowpack_outlook": 0.68 if offset < 14 else None,
            "snow_depth_cm": 60 if offset < 14 else None,
            "snow_depth_spread_cm": 8 if offset < 14 else None,
            "natural_snow_utility": 0.7,
            "snowmaking_uplift": 0,
            "managed_snow_utility": 0.7,
        }
        for offset in range(31)
    )
    return tuple(
        FactorScoreBreakdown(
            factor_id=f"factor-{index}",
            group_id=f"group-{index % 4}",
            direction="prefer",
            raw_value={"mode": "exact_dates", "utility": 0.7},
            raw_utility=0.7,
            neutral_utility=0.5,
            effective_evidence_cap=0.8,
            effective_utility=0.66,
            effective_weight=1,
            contribution_points=4,
            evidence_cap_components={"source_strength": 0.8},
            warnings=(),
            provenance_summary="Existing source-aware candidate evidence.",
            explanation_inputs={"mode": "exact_dates", "days": profile},
        )
        for index in range(18)
    )


def _configuration(
    *,
    region_index: int,
    configuration_index: int,
    weather_evidence: object | None,
) -> SearchV4Configuration:
    suffix = f"{region_index}-{configuration_index}"
    return SearchV4Configuration(
        candidate_id=f"candidate-{suffix}",
        ski_region_id=f"region-{region_index}",
        ski_region_name=f"Region {region_index}",
        stay_destination_id=f"destination-{suffix}",
        stay_destination_name=f"Destination {suffix}",
        stay_base_id=f"base-{suffix}",
        stay_base_name=f"Base {suffix}",
        ski_area_id=f"area-{suffix}",
        ski_area_name=f"Area {suffix}",
        access=SearchV4AccessSummary(
            ski_area_access_id=f"access-{suffix}",
            access_mode="walk",
            lift_distance="nearby",
            nearest_lift_name="Main lift",
            distance_m=250,
            duration_minutes=4,
            is_direct=True,
        ),
        selected_pass=SearchV4PassSummary(
            lift_pass_product_id=f"pass-{suffix}",
            name="Regional ski pass",
            validity_scope="ski_area",
            covered_ski_area_ids=(f"area-{suffix}",),
            accessible_piste_km=180,
            price=SearchV4PassPriceSummary(
                duration_days=6,
                audience="adult",
                amount=360,
                amount_min=None,
                amount_max=None,
                currency="EUR",
                price_kind="fixed",
                season_label="winter",
            ),
        ),
        lodging_estimate=None,
        ranking_status="ranked",
        fit_score=88 - region_index - configuration_index / 10,
        groups=tuple(
            GroupScoreBreakdown(
                group_id=f"group-{index}",
                normalized_share=0.25,
                group_utility=0.7,
                contribution_points=17.5,
            )
            for index in range(4)
        ),
        factors=_factor_rows(),
        weather_evidence=weather_evidence,
    )


def _response(
    summaries: tuple[object | None, ...],
) -> SearchV4Response:
    configurations = tuple(
        _configuration(
            region_index=region_index,
            configuration_index=configuration_index,
            weather_evidence=summaries[region_index * 4 + configuration_index],
        )
        for region_index in range(3)
        for configuration_index in range(4)
    )
    return SearchV4Response(
        search_model_version="search-v4",
        ranking_policy_version="search-v4-policy-1",
        ranking_status="ranked",
        applied_intent=SearchIntent(
            constraints=SearchConstraints(
                travel_window=TravelWindow(
                    start_date=date(2027, 1, 1),
                    end_date=date(2027, 1, 31),
                )
            )
        ),
        eligible_candidate_count=12,
        excluded_candidate_count=0,
        results=tuple(
            SearchV4RecommendationGroup(
                ski_region_id=f"region-{region_index}",
                ski_region_name=f"Region {region_index}",
                rank=region_index + 1,
                fit_score=configurations[region_index * 4].fit_score,
                top_configuration=configurations[region_index * 4],
                alternative_configurations=configurations[
                    region_index * 4 + 1 : region_index * 4 + 4
                ],
            )
            for region_index in range(3)
        ),
    )


def test_representative_grouped_response_cost() -> None:
    start = date(2027, 1, 1)
    window = TravelWindow(start_date=start, end_date=start + timedelta(days=30))
    context = _context(window)
    candidates = tuple(
        _candidate(
            ski_area_id=f"area-{region_index}-{configuration_index}",
            climatology_rows=tuple(
                _climatology(
                    start + timedelta(days=offset),
                    ski_area_id=f"area-{region_index}-{configuration_index}",
                )
                for offset in range(31)
            ),
            forecast_rows=tuple(
                _served(
                    start + timedelta(days=offset),
                    ski_area_id=f"area-{region_index}-{configuration_index}",
                    run_id=f"run-{region_index}-{configuration_index}",
                )
                for offset in range(14)
            ),
        )
        for region_index in range(3)
        for configuration_index in range(4)
    )

    def build_all() -> tuple[object | None, ...]:
        return tuple(
            build_search_weather_evidence(context=context, candidate=candidate)
            for candidate in candidates
        )

    warm = build_all()
    durations_ms: list[float] = []
    for _ in range(100):
        started = time.perf_counter()
        summaries = build_all()
        durations_ms.append((time.perf_counter() - started) * 1_000)
    p95_ms = statistics.quantiles(
        durations_ms,
        n=100,
        method="inclusive",
    )[94]

    baseline_bytes = len(_response((None,) * 12).model_dump_json().encode("utf-8"))
    complete_bytes = len(_response(warm).model_dump_json().encode("utf-8"))
    additive_bytes = complete_bytes - baseline_bytes

    assert all(summary is not None for summary in summaries)
    assert all(
        len(summary.historical.daily_profile) <= 31
        and summary.forecast is not None
        and len(summary.forecast.daily_profile) <= 31
        for summary in summaries
        if summary is not None
    )
    assert p95_ms <= 25
    assert additive_bytes <= 512 * 1024
    assert complete_bytes <= baseline_bytes * 2
    assert not math.isnan(p95_ms)
    print(
        "representative_grouped_response_cost "
        f"baseline_bytes={baseline_bytes} complete_bytes={complete_bytes} "
        f"additive_bytes={additive_bytes} p95_ms={p95_ms:.3f}"
    )
