from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.models import SnowClimatologyDaily
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_factors.weather import (
    WeatherEvaluationContext,
    WeatherFactorCandidate,
    build_weather_factor_registry,
    forecast_share_for_lead_days,
    piecewise_linear_utility,
    snowpack_outlook,
)
from app.domain.search_policy import load_search_policy
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    SearchConstraints,
    SearchIntent,
    TravelWindow,
)
from app.domain.weather_forecast import (
    ServedWeatherForecastDaily,
    WeatherForecastDaily,
    WeatherForecastRun,
)

pytestmark = pytest.mark.db_free


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
        producer="ecmwf" if source_key.startswith("ecmwf") else "noaa-ncep",
        provider_model_id=source_key,
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
        provider_metadata={},
    )


def _served(
    day: date,
    source_key: str,
    *,
    depth_cm: float = 30,
    snowfall_cm: float = 15,
    rain_mm: float = 0,
    positive_degree_hours: float = 0,
    initialized_at: datetime = datetime(2027, 1, 1, tzinfo=UTC),
    run_id: str | None = None,
) -> ServedWeatherForecastDaily:
    run = _run(source_key, initialized_at=initialized_at, run_id=run_id)
    return ServedWeatherForecastDaily(
        run=run,
        daily=WeatherForecastDaily(
            forecast_run_id=run.forecast_run_id,
            ski_area_id="area",
            valid_local_date=day,
            provider_timezone="Europe/Vienna",
            representative_elevation_m=2000,
            request_latitude=47,
            request_longitude=11,
            snow_depth_cm=depth_cm,
            snow_depth_spread_cm=8,
            snowfall_cm=snowfall_cm,
            rain_mm=rain_mm,
            positive_degree_hours=positive_degree_hours,
            temperature_2m_min_c=-6,
            temperature_2m_max_c=1,
            wind_speed_10m_max_kmh=30,
            wind_gusts_10m_max_kmh=50,
            is_complete=True,
            completeness_metadata={"expected_hour_count": 24},
        ),
    )


def _climatology(
    day: date,
    score: float,
    *,
    baseline: str = "normal_30y",
) -> SnowClimatologyDaily:
    weather_policy = load_search_policy().weather
    median_depth_cm = _value_for_piecewise_utility(
        score,
        weather_policy.depth_curve_values,
        weather_policy.depth_curve_utilities,
    )
    return SnowClimatologyDaily(
        ski_area_id="area",
        resort_name="Area",
        elevation_band="mid",
        elevation_m=2000,
        month=day.month,
        day=day.day,
        baseline_period=baseline,
        baseline_start_year=1991,
        baseline_end_year=2020,
        evidence_seasons=25,
        latest_archive_year=2025,
        snow_depth_cm_p25=max(0, median_depth_cm - 10),
        snow_depth_cm_p50=median_depth_cm,
        snow_depth_cm_p75=median_depth_cm + 10,
        prob_snow_depth_ge_30cm=score,
        prob_snow_depth_ge_50cm=score,
        avg_daily_snowfall_cm=4,
        prob_rain_risk=0,
        prob_freeze_thaw=0,
        avg_max_temperature_c=-1,
        avg_wind_gust_kmh=30,
        avg_snow_confidence_score=score,
        avg_conditions_score=score,
        computed_at="2026-07-01T00:00:00+00:00",
    )


def _value_for_piecewise_utility(
    utility: float,
    values: tuple[float, ...],
    utilities: tuple[float, ...],
) -> float:
    if utility <= utilities[0]:
        return values[0]
    if utility >= utilities[-1]:
        return values[-1]
    for index, (left, right) in enumerate(zip(utilities, utilities[1:])):
        if left <= utility <= right:
            ratio = (utility - left) / (right - left)
            return values[index] + ratio * (values[index + 1] - values[index])
    raise AssertionError("utility curve did not contain value")


def _climatology_v2(
    day: date,
    *,
    median_depth_cm: float,
    probability_30cm: float,
    probability_50cm: float,
    rain_risk: float,
    freeze_thaw_risk: float,
    legacy_score: float,
    average_snowfall_cm: float = 4,
    average_max_temperature_c: float = -1,
) -> SnowClimatologyDaily:
    return SnowClimatologyDaily(
        ski_area_id="area",
        resort_name="Area",
        elevation_band="mid",
        elevation_m=2000,
        month=day.month,
        day=day.day,
        baseline_period="normal_30y",
        baseline_start_year=1991,
        baseline_end_year=2020,
        evidence_seasons=30,
        latest_archive_year=2025,
        snow_depth_cm_p25=max(0, median_depth_cm - 27.7),
        snow_depth_cm_p50=median_depth_cm,
        snow_depth_cm_p75=median_depth_cm + 37.8,
        prob_snow_depth_ge_30cm=probability_30cm,
        prob_snow_depth_ge_50cm=probability_50cm,
        avg_daily_snowfall_cm=average_snowfall_cm,
        prob_rain_risk=rain_risk,
        prob_freeze_thaw=freeze_thaw_risk,
        avg_max_temperature_c=average_max_temperature_c,
        avg_wind_gust_kmh=30,
        avg_snow_confidence_score=legacy_score,
        avg_conditions_score=legacy_score,
        computed_at="2026-07-01T00:00:00+00:00",
    )


def _context(
    start: date,
    end: date | None = None,
    *,
    snowmaking: bool = False,
    stale_run_ids: frozenset[str] = frozenset(),
    reference_date: date = date(2027, 1, 1),
) -> WeatherEvaluationContext:
    preferences = (
        (
            FactorPreferencePatch(
                factor_id="snowmaking_availability",
                mode="prefer",
            ),
        )
        if snowmaking
        else ()
    )
    return WeatherEvaluationContext(
        intent=SearchIntent(
            constraints=SearchConstraints(
                travel_window=TravelWindow(start_date=start, end_date=end or start)
            ),
            factor_preferences=preferences,
        ),
        policy=load_search_policy(),
        stale_run_ids=stale_run_ids,
        reference_date=reference_date,
    )


def _snowmaking(availability: str, cap: float) -> FactorEvaluation:
    utility = {"available": 1.0, "unavailable": 0.0, "unknown": 0.5}[availability]
    return FactorEvaluation(
        factor_id="snowmaking_availability",
        scope="ski_area_window",
        entity_ids=("area",),
        raw_value={"availability": availability},
        raw_utility=utility,
        neutral_utility=0.5,
        effective_evidence_cap=cap,
        evidence_cap_components={"catalog": cap},
        warnings=(),
        provenance_summary="Catalog snowmaking evidence.",
        explanation_inputs={"availability": availability},
    )


def test_piecewise_curves_and_forecast_share_use_policy_boundaries() -> None:
    weather = load_search_policy().weather

    assert piecewise_linear_utility(15, (10, 20), (0.2, 0.6)) == pytest.approx(0.4)
    assert piecewise_linear_utility(-1, (10, 20), (0.2, 0.6)) == 0.2
    assert piecewise_linear_utility(30, (10, 20), (0.2, 0.6)) == 0.6
    boundaries = (5, 6, 10, 11, 16, 17, 30, 31)
    assert [forecast_share_for_lead_days(day, weather) for day in boundaries] == [
        0.8,
        0.6,
        0.6,
        0.4,
        0.4,
        0.15,
        0.15,
        0,
    ]


def test_physical_outlook_uses_depth_fresh_snow_and_max_correlated_risk() -> None:
    policy = load_search_policy().weather
    row = _served(
        date(2027, 1, 2),
        "ecmwf_ifs025_ensemble_mean",
        depth_cm=30,
        snowfall_cm=15,
        rain_mm=15,
        positive_degree_hours=12,
    ).daily

    result = snowpack_outlook(row, policy)

    assert result.depth_adequacy == pytest.approx(0.6)
    assert result.fresh_snow_benefit == pytest.approx(0.7)
    assert result.rain_risk == pytest.approx(0.75)
    assert result.thaw_risk == pytest.approx(0.2)
    assert result.utility == pytest.approx(0.6 + 0.15 * 0.7 - 0.25 * 0.75)


def test_climatology_reliability_uses_depth_distribution_not_legacy_score() -> None:
    day = date(2027, 12, 12)
    evaluator = build_weather_factor_registry().get("climatological_snow_reliability")
    row = _climatology_v2(
        day,
        median_depth_cm=99.7,
        probability_30cm=0.99,
        probability_50cm=0.95,
        rain_risk=0.05,
        freeze_thaw_risk=0.04,
        legacy_score=0.58,
    )

    result = evaluator.evaluate(
        _context(day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(row,),
            forecast_rows=(),
        ),
    )

    expected_depth = piecewise_linear_utility(
        99.7,
        load_search_policy().weather.depth_curve_values,
        load_search_policy().weather.depth_curve_utilities,
    )
    expected = 0.5 * expected_depth + 0.3 * 0.99 + 0.2 * 0.95 - 0.25 * 0.05
    assert result.raw_utility == pytest.approx(expected)
    assert result.raw_utility > 0.9


def test_climatology_concern_names_historical_rain_or_thaw_risk() -> None:
    day = date(2027, 12, 12)
    row = _climatology_v2(
        day,
        median_depth_cm=100,
        probability_30cm=0.99,
        probability_50cm=0.99,
        rain_risk=1,
        freeze_thaw_risk=0.2,
        legacy_score=0.7,
    )

    result = (
        build_weather_factor_registry()
        .get("trip_window_snow_fit")
        .evaluate(
            _context(day),
            WeatherFactorCandidate(
                ski_area_id="area",
                climatology_rows=(row,),
                forecast_rows=(),
            ),
        )
    )

    assert result.raw_value["assessment_state"] == "some_concerns"
    assert result.raw_value["assessment_reason"] == "historical_rain_or_thaw_risk"


def test_climatology_concern_attribution_uses_active_policy_coefficients() -> None:
    day = date(2027, 12, 12)
    row = _climatology_v2(
        day,
        median_depth_cm=0,
        probability_30cm=1,
        probability_50cm=1,
        rain_risk=0.2,
        freeze_thaw_risk=0,
        legacy_score=0.7,
    )
    base_context = _context(day)
    weather_policy = base_context.policy.weather.model_copy(
        update={
            "climatology_typical_depth_coefficient": 0.1,
            "climatology_probability_30cm_coefficient": 0.45,
            "climatology_probability_50cm_coefficient": 0.45,
            "climatology_deterioration_coefficient": 0.9,
        }
    )
    context = replace(
        base_context,
        policy=base_context.policy.model_copy(update={"weather": weather_policy}),
    )

    result = (
        build_weather_factor_registry()
        .get("trip_window_snow_fit")
        .evaluate(
            context,
            WeatherFactorCandidate(
                ski_area_id="area",
                climatology_rows=(row,),
                forecast_rows=(),
            ),
        )
    )

    assert result.raw_value["assessment_state"] == "some_concerns"
    assert result.raw_value["assessment_reason"] == "historical_rain_or_thaw_risk"


def test_exact_trip_concern_compares_sources_over_the_same_date_window() -> None:
    start = date(2027, 1, 2)
    end = start + timedelta(days=5)
    forecast_days = tuple(start + timedelta(days=offset) for offset in range(1, 6))
    historical_row = _climatology_v2(
        start,
        median_depth_cm=0,
        probability_30cm=1,
        probability_50cm=1,
        rain_risk=0,
        freeze_thaw_risk=0,
        legacy_score=0.5,
    )

    result = (
        build_weather_factor_registry()
        .get("trip_window_snow_fit")
        .evaluate(
            _context(start, end),
            WeatherFactorCandidate(
                ski_area_id="area",
                climatology_rows=(historical_row,),
                forecast_rows=tuple(
                    _served(
                        day,
                        "ecmwf_ifs025_ensemble_mean",
                        depth_cm=0,
                        snowfall_cm=0,
                    )
                    for day in forecast_days
                ),
            ),
        )
    )

    assert result.effective_evidence_cap == 1
    assert result.raw_value["assessment_state"] == "some_concerns"
    assert result.raw_value["assessment_reason"] == "weaker_forecast_outlook"


def test_climatology_reliability_excludes_snowfall_and_average_temperature() -> None:
    day = date(2027, 12, 12)
    evaluator = build_weather_factor_registry().get("climatological_snow_reliability")
    common = {
        "median_depth_cm": 80,
        "probability_30cm": 0.9,
        "probability_50cm": 0.8,
        "rain_risk": 0.1,
        "freeze_thaw_risk": 0.2,
    }
    cold_snowy = _climatology_v2(
        day,
        **common,
        legacy_score=0.9,
        average_snowfall_cm=12,
        average_max_temperature_c=-8,
    )
    warm_dry = _climatology_v2(
        day,
        **common,
        legacy_score=0.3,
        average_snowfall_cm=0,
        average_max_temperature_c=4,
    ).model_copy(update={"computed_at": "2026-07-02T00:00:00+00:00"})

    cold_result = evaluator.evaluate(
        _context(day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(cold_snowy,),
            forecast_rows=(),
        ),
    )
    warm_result = evaluator.evaluate(
        _context(day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(warm_dry,),
            forecast_rows=(),
        ),
    )

    assert cold_result.raw_utility == pytest.approx(warm_result.raw_utility)


def test_climatology_reliability_uses_normal_without_a_hidden_recent_adjustment() -> (
    None
):
    day = date(2027, 12, 12)
    evaluator = build_weather_factor_registry().get("climatological_snow_reliability")
    normal = _climatology_v2(
        day,
        median_depth_cm=90,
        probability_30cm=0.95,
        probability_50cm=0.85,
        rain_risk=0.05,
        freeze_thaw_risk=0.05,
        legacy_score=0.8,
    )
    recent = _climatology_v2(
        day,
        median_depth_cm=10,
        probability_30cm=0.1,
        probability_50cm=0.05,
        rain_risk=0.8,
        freeze_thaw_risk=0.8,
        legacy_score=0.2,
    ).model_copy(
        update={
            "baseline_period": "recent_15y",
            "baseline_start_year": 2011,
            "baseline_end_year": 2025,
            "computed_at": "2026-07-02T00:00:00+00:00",
        }
    )

    normal_only = evaluator.evaluate(
        _context(day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(normal,),
            forecast_rows=(),
        ),
    )
    with_recent = evaluator.evaluate(
        _context(day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(normal, recent),
            forecast_rows=(),
        ),
    )

    assert with_recent.raw_utility == pytest.approx(normal_only.raw_utility)


def test_trip_fit_prefers_ecmwf_then_uses_gefs_for_fallback_and_long_range() -> None:
    registry = build_weather_factor_registry()
    evaluator = registry.get("trip_window_snow_fit")
    short_day = date(2027, 1, 2)
    long_day = date(2027, 1, 18)
    forecasts = (
        _served(short_day, "ecmwf_ifs025_ensemble_mean", depth_cm=60),
        _served(short_day, "ncep_gefs05_ensemble_mean", depth_cm=10),
        _served(long_day, "ncep_gefs05_ensemble_mean", depth_cm=30),
    )
    candidate = WeatherFactorCandidate(
        ski_area_id="area",
        climatology_rows=(
            _climatology(short_day, 0.6),
            _climatology(long_day, 0.6),
        ),
        forecast_rows=forecasts,
    )

    short = evaluator.evaluate(_context(short_day), candidate)
    long = evaluator.evaluate(_context(long_day), candidate)

    short_day_inputs = short.explanation_inputs["days"][0]
    long_day_inputs = long.explanation_inputs["days"][0]
    assert short_day_inputs["forecast_source_key"] == ("ecmwf_ifs025_ensemble_mean")
    assert short_day_inputs["forecast_share"] == 0.8
    assert short.raw_value["forecast_status"] == "available"
    assert long_day_inputs["forecast_source_key"] == ("ncep_gefs05_ensemble_mean")
    assert long_day_inputs["forecast_share"] == 0.15

    stale_ecmwf = _context(
        short_day,
        stale_run_ids=frozenset({forecasts[0].run.forecast_run_id}),
    )
    fallback = evaluator.evaluate(stale_ecmwf, candidate)
    assert fallback.explanation_inputs["days"][0]["forecast_source_key"] == (
        "ncep_gefs05_ensemble_mean"
    )


def test_missing_forecast_returns_its_share_to_climatology() -> None:
    day = date(2027, 1, 2)
    evaluator = build_weather_factor_registry().get("trip_window_snow_fit")
    candidate = WeatherFactorCandidate(
        ski_area_id="area",
        climatology_rows=(_climatology(day, 0.7),),
        forecast_rows=(),
    )

    result = evaluator.evaluate(_context(day), candidate)

    assert result.raw_utility == pytest.approx(0.7)
    assert result.explanation_inputs["days"][0]["forecast_share"] == 0
    assert result.raw_value["forecast_status"] == "unexpectedly_unavailable"
    assert "forecast unavailable for 1 requested day(s)" in result.warnings


def test_forecast_only_concern_names_limited_historical_context() -> None:
    day = date(2027, 1, 2)
    evaluator = build_weather_factor_registry().get("trip_window_snow_fit")

    result = evaluator.evaluate(
        _context(day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(),
            forecast_rows=(
                _served(
                    day,
                    "ecmwf_ifs025_ensemble_mean",
                    depth_cm=50,
                    snowfall_cm=0,
                ),
            ),
        ),
    )

    assert result.raw_utility == pytest.approx(0.74)
    assert result.raw_value["assessment_state"] == "some_concerns"
    assert result.raw_value["assessment_reason"] == "limited_historical_context"


def test_weak_forecast_only_concern_names_the_forecast_without_comparison() -> None:
    day = date(2027, 1, 2)
    evaluator = build_weather_factor_registry().get("trip_window_snow_fit")

    result = evaluator.evaluate(
        _context(day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(),
            forecast_rows=(
                _served(
                    day,
                    "ecmwf_ifs025_ensemble_mean",
                    depth_cm=20,
                    snowfall_cm=0,
                ),
            ),
        ),
    )

    assert result.raw_value["assessment_state"] == "some_concerns"
    assert result.raw_value["assessment_reason"] == "weaker_forecast_outlook"


def test_forecast_outside_horizon_is_expected_neutral_context() -> None:
    day = date(2027, 12, 12)
    evaluator = build_weather_factor_registry().get("trip_window_snow_fit")

    result = evaluator.evaluate(
        _context(day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(_climatology(day, 0.9),),
            forecast_rows=(),
        ),
    )

    assert result.raw_utility == pytest.approx(0.9)
    assert result.raw_value["forecast_status"] == "not_yet_available"
    assert result.raw_value["assessment_reason"] == "strong_snow_reliability"
    assert not any("forecast unavailable" in warning for warning in result.warnings)


def test_exact_trip_requires_evidence_for_every_date_before_claiming_snow_fit() -> None:
    first_day = date(2027, 1, 2)
    second_day = first_day + timedelta(days=1)
    evaluator = build_weather_factor_registry().get("trip_window_snow_fit")

    result = evaluator.evaluate(
        _context(first_day, second_day),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(_climatology(first_day, 0.9),),
            forecast_rows=(),
        ),
    )

    assert result.effective_evidence_cap == pytest.approx(0.5)
    assert result.raw_value["assessment_state"] == "not_enough_evidence"


def test_provider_local_day_30_forecast_is_never_reported_as_not_yet_available() -> (
    None
):
    reference_date = date(2027, 1, 1)
    valid_date = date(2027, 2, 1)
    provider_day_two_initialization = datetime(
        2027,
        1,
        1,
        23,
        30,
        tzinfo=UTC,
    )
    forecast = _served(
        valid_date,
        "ncep_gefs05_ensemble_mean",
        initialized_at=provider_day_two_initialization,
    )
    assert forecast.lead_days == 30

    result = (
        build_weather_factor_registry()
        .get("trip_window_snow_fit")
        .evaluate(
            _context(valid_date, reference_date=reference_date),
            WeatherFactorCandidate(
                ski_area_id="area",
                climatology_rows=(_climatology(valid_date, 0.8),),
                forecast_rows=(forecast,),
            ),
        )
    )

    assert result.raw_value["forecast_status"] == "available"
    assert result.evidence_cap_components["forecast_date_coverage"] == 1


def test_snowmaking_uplift_only_applies_when_requested_available_and_needed() -> None:
    day = date(2027, 1, 2)
    evaluator = build_weather_factor_registry().get("trip_window_snow_fit")
    base_candidate = WeatherFactorCandidate(
        ski_area_id="area",
        climatology_rows=(_climatology(day, 0.3),),
        forecast_rows=(),
        snowmaking_evaluation=_snowmaking("available", 1),
    )

    without_preference = evaluator.evaluate(_context(day), base_candidate)
    with_preference = evaluator.evaluate(
        _context(day, snowmaking=True),
        base_candidate,
    )
    unknown = evaluator.evaluate(
        _context(day, snowmaking=True),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(_climatology(day, 0.3),),
            forecast_rows=(),
            snowmaking_evaluation=_snowmaking("unknown", 0),
        ),
    )
    strong_natural = evaluator.evaluate(
        _context(day, snowmaking=True),
        WeatherFactorCandidate(
            ski_area_id="area",
            climatology_rows=(_climatology(day, 0.8),),
            forecast_rows=(),
            snowmaking_evaluation=_snowmaking("available", 1),
        ),
    )

    assert without_preference.raw_utility == pytest.approx(0.3)
    assert with_preference.raw_utility == pytest.approx(0.475)
    assert unknown.raw_utility == pytest.approx(0.3)
    assert strong_natural.raw_utility == pytest.approx(0.8)


def test_month_only_uses_climatology_and_never_forecast() -> None:
    day = date(2027, 1, 2)
    context = WeatherEvaluationContext(
        intent=SearchIntent(
            constraints=SearchConstraints(travel_window=TravelWindow(month=1))
        ),
        policy=load_search_policy(),
        reference_date=date(2027, 1, 1),
    )
    candidate = WeatherFactorCandidate(
        ski_area_id="area",
        climatology_rows=(_climatology(day, 0.65),),
        forecast_rows=(_served(day, "ecmwf_ifs025_ensemble_mean", depth_cm=100),),
    )

    result = (
        build_weather_factor_registry()
        .get("trip_window_snow_fit")
        .evaluate(
            context,
            candidate,
        )
    )

    assert result.raw_utility == pytest.approx(0.65)
    assert result.explanation_inputs["mode"] == "month_climatology_only"


def test_month_climatology_caps_influence_by_calendar_day_coverage() -> None:
    day = date(2027, 1, 2)
    context = WeatherEvaluationContext(
        intent=SearchIntent(
            constraints=SearchConstraints(travel_window=TravelWindow(month=1))
        ),
        policy=load_search_policy(),
        reference_date=date(2027, 1, 1),
    )
    candidate = WeatherFactorCandidate(
        ski_area_id="area",
        climatology_rows=(_climatology(day, 0.9),),
        forecast_rows=(),
    )

    result = (
        build_weather_factor_registry()
        .get("trip_window_snow_fit")
        .evaluate(
            context,
            candidate,
        )
    )

    assert result.raw_utility == pytest.approx(0.9)
    assert result.effective_evidence_cap == pytest.approx(1 / 31)
    assert result.evidence_cap_components["climatology_date_coverage"] == (
        pytest.approx(1 / 31)
    )
