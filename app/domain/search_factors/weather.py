from __future__ import annotations

import calendar
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.domain.models import SnowClimatologyDaily
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_factors.registry import FactorRegistry
from app.domain.search_policy import SearchPolicy, WeatherRankingPolicy
from app.domain.search_v4_models import SearchIntent, TravelWindow
from app.domain.weather_forecast import (
    ServedWeatherForecastDaily,
    WeatherForecastDaily,
)


@dataclass(frozen=True)
class WeatherEvaluationContext:
    intent: SearchIntent
    policy: SearchPolicy
    stale_run_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class WeatherFactorCandidate:
    ski_area_id: str
    climatology_rows: tuple[SnowClimatologyDaily, ...]
    forecast_rows: tuple[ServedWeatherForecastDaily, ...]
    snowmaking_evaluation: FactorEvaluation | None = None

    def __post_init__(self) -> None:
        if not self.ski_area_id.strip():
            raise ValueError("ski_area_id must not be blank")
        if any(row.ski_area_id != self.ski_area_id for row in self.climatology_rows):
            raise ValueError("climatology row ski area must match candidate")
        if any(row.daily.ski_area_id != self.ski_area_id for row in self.forecast_rows):
            raise ValueError("forecast row ski area must match candidate")
        if (
            self.snowmaking_evaluation is not None
            and self.snowmaking_evaluation.factor_id != "snowmaking_availability"
        ):
            raise ValueError("snowmaking evaluation has the wrong factor ID")


@dataclass(frozen=True)
class SnowpackOutlook:
    utility: float
    depth_adequacy: float
    fresh_snow_benefit: float
    rain_risk: float
    thaw_risk: float
    rain_thaw_risk: float


@dataclass(frozen=True)
class _WeatherFactorEvaluator:
    factor_id: str
    function: Callable[
        [WeatherEvaluationContext, WeatherFactorCandidate],
        FactorEvaluation,
    ]

    def evaluate(self, context: object, candidate: object) -> FactorEvaluation:
        if not isinstance(context, WeatherEvaluationContext):
            raise TypeError("weather evaluator requires WeatherEvaluationContext")
        if not isinstance(candidate, WeatherFactorCandidate):
            raise TypeError("weather evaluator requires WeatherFactorCandidate")
        return self.function(context, candidate)


def build_weather_factor_registry() -> FactorRegistry:
    return FactorRegistry(
        _WeatherFactorEvaluator(factor_id=factor_id, function=function)
        for factor_id, function in _WEATHER_EVALUATORS.items()
    )


def piecewise_linear_utility(
    value: float,
    values: Sequence[float],
    utilities: Sequence[float],
) -> float:
    if len(values) < 2 or len(values) != len(utilities):
        raise ValueError(
            "piecewise curve needs matching arrays with at least two points"
        )
    if any(right <= left for left, right in zip(values, values[1:])):
        raise ValueError("piecewise curve values must strictly increase")
    if value <= values[0]:
        return float(utilities[0])
    if value >= values[-1]:
        return float(utilities[-1])
    for left_index, (left, right) in enumerate(zip(values, values[1:])):
        if left <= value <= right:
            ratio = (value - left) / (right - left)
            left_utility = utilities[left_index]
            right_utility = utilities[left_index + 1]
            return float(left_utility + ratio * (right_utility - left_utility))
    raise AssertionError("validated piecewise curve did not contain value")


def forecast_share_for_lead_days(
    lead_days: int,
    policy: WeatherRankingPolicy,
) -> float:
    if lead_days < 0:
        return 0
    for maximum_day, share in zip(
        policy.lead_time_max_days,
        policy.lead_time_forecast_shares,
        strict=True,
    ):
        if lead_days <= maximum_day:
            return share
    return 0


def snowpack_outlook(
    row: WeatherForecastDaily,
    policy: WeatherRankingPolicy,
) -> SnowpackOutlook:
    if row.snow_depth_cm is None:
        raise ValueError("snowpack outlook requires modelled snow depth")
    depth = piecewise_linear_utility(
        row.snow_depth_cm,
        policy.depth_curve_values,
        policy.depth_curve_utilities,
    )
    fresh_snow = piecewise_linear_utility(
        row.snowfall_cm,
        policy.fresh_snow_curve_values,
        policy.fresh_snow_curve_utilities,
    )
    rain = piecewise_linear_utility(
        row.rain_mm,
        policy.rain_curve_values,
        policy.rain_curve_utilities,
    )
    thaw = piecewise_linear_utility(
        row.positive_degree_hours,
        policy.thaw_curve_values,
        policy.thaw_curve_utilities,
    )
    combined_risk = max(rain, thaw)
    utility = _clamp(
        depth
        + policy.fresh_snow_coefficient * fresh_snow
        - policy.rain_thaw_risk_coefficient * combined_risk
    )
    return SnowpackOutlook(
        utility=utility,
        depth_adequacy=depth,
        fresh_snow_benefit=fresh_snow,
        rain_risk=rain,
        thaw_risk=thaw,
        rain_thaw_risk=combined_risk,
    )


def _trip_window_snow_fit(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
) -> FactorEvaluation:
    window = context.intent.constraints.travel_window
    if window is None:
        return _neutral_evaluation(
            context,
            candidate,
            factor_id="trip_window_snow_fit",
            warning="travel window unavailable",
        )
    if window.mode == "month":
        utility, coverage, details = _month_climatology(
            candidate.climatology_rows,
            window,
            context.policy.weather,
        )
        return _evaluation(
            context,
            candidate,
            factor_id="trip_window_snow_fit",
            raw_value={"mode": "month_climatology_only", "utility": utility},
            raw_utility=utility,
            evidence_cap=coverage,
            evidence_components={
                "climatology_date_coverage": coverage,
                "forecast_date_coverage": 0,
            },
            warnings=("climatology unavailable",) if coverage == 0 else (),
            explanation_inputs={
                "mode": "month_climatology_only",
                "climatology": details,
            },
            provenance=(
                "Derived daily climatology; exact-date forecast is not used for "
                "month-only searches."
            ),
        )

    requested_dates = _requested_dates(window)
    climatology = {
        valid_date: _climatology_for_date(
            candidate.climatology_rows,
            valid_date,
            context.policy.weather,
        )
        for valid_date in requested_dates
    }
    forecast_rows = _forecast_rows_by_date(context, candidate)
    snowmaking_support = _snowmaking_support(context, candidate)
    day_details: list[dict[str, Any]] = []
    day_utilities: list[float] = []
    forecast_covered = 0
    climatology_covered = 0
    any_evidence = False

    for valid_date in requested_dates:
        climate_utility = climatology[valid_date]
        if climate_utility is not None:
            climatology_covered += 1
            any_evidence = True
        else:
            climate_utility = 0.5
        forecast = forecast_rows.get(valid_date)
        share = 0.0
        outlook: SnowpackOutlook | None = None
        if forecast is not None:
            outlook = snowpack_outlook(forecast.daily, context.policy.weather)
            share = forecast_share_for_lead_days(
                forecast.lead_days,
                context.policy.weather,
            )
            if share > 0:
                forecast_covered += 1
                any_evidence = True
        natural_utility = (
            share * outlook.utility + (1 - share) * climate_utility
            if outlook is not None
            else climate_utility
        )
        managed_utility, snowmaking_uplift = _apply_snowmaking_uplift(
            natural_utility,
            snowmaking_support,
            context.policy.weather,
        )
        day_utilities.append(managed_utility)
        day_details.append(
            {
                "valid_date": valid_date.isoformat(),
                "climatology_utility": climate_utility,
                "forecast_source_key": (
                    forecast.run.forecast_source_key
                    if forecast is not None and share > 0
                    else None
                ),
                "forecast_run_id": (
                    forecast.run.forecast_run_id
                    if forecast is not None and share > 0
                    else None
                ),
                "forecast_lead_days": (
                    forecast.lead_days if forecast is not None and share > 0 else None
                ),
                "forecast_share": share,
                "snowpack_outlook": (
                    outlook.utility if outlook is not None and share > 0 else None
                ),
                "snow_depth_cm": (
                    forecast.daily.snow_depth_cm
                    if forecast is not None and share > 0
                    else None
                ),
                "snow_depth_spread_cm": (
                    forecast.daily.snow_depth_spread_cm
                    if forecast is not None and share > 0
                    else None
                ),
                "natural_snow_utility": natural_utility,
                "snowmaking_uplift": snowmaking_uplift,
                "managed_snow_utility": managed_utility,
            }
        )

    date_count = len(requested_dates)
    missing_forecast_count = date_count - forecast_covered
    warnings: list[str] = []
    if missing_forecast_count:
        warnings.append(
            f"forecast unavailable for {missing_forecast_count} requested day(s)"
        )
    if climatology_covered < date_count:
        warnings.append(
            "climatology unavailable for "
            f"{date_count - climatology_covered} requested day(s)"
        )
    raw_utility = sum(day_utilities) / date_count
    return _evaluation(
        context,
        candidate,
        factor_id="trip_window_snow_fit",
        raw_value={
            "mode": "exact_dates",
            "utility": raw_utility,
            "snowmaking_support": snowmaking_support,
        },
        raw_utility=raw_utility,
        evidence_cap=1 if any_evidence else 0,
        evidence_components={
            "climatology_date_coverage": climatology_covered / date_count,
            "forecast_date_coverage": forecast_covered / date_count,
            "composition_policy": context.policy.weather.policy_version,
        },
        warnings=tuple(warnings),
        explanation_inputs={"mode": "exact_dates", "days": tuple(day_details)},
        provenance=(
            "Versioned forecast-run evidence blended per local ski day with "
            "derived climatology."
        ),
    )


def _climatological_snow_reliability(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
) -> FactorEvaluation:
    window = context.intent.constraints.travel_window
    if window is None:
        return _neutral_evaluation(
            context,
            candidate,
            factor_id="climatological_snow_reliability",
            warning="travel window unavailable",
        )
    if window.mode == "month":
        utility, coverage, details = _month_climatology(
            candidate.climatology_rows,
            window,
            context.policy.weather,
        )
    else:
        requested_dates = _requested_dates(window)
        values = tuple(
            _climatology_for_date(
                candidate.climatology_rows,
                valid_date,
                context.policy.weather,
            )
            for valid_date in requested_dates
        )
        resolved = tuple(value for value in values if value is not None)
        coverage = len(resolved) / len(values)
        utility = sum(resolved) / len(resolved) if resolved else 0.5
        details = {"resolved_dates": len(resolved), "requested_dates": len(values)}
    return _evaluation(
        context,
        candidate,
        factor_id="climatological_snow_reliability",
        raw_value=details,
        raw_utility=utility,
        evidence_cap=coverage,
        evidence_components={"climatology_date_coverage": coverage},
        warnings=("climatology unavailable",) if coverage == 0 else (),
        explanation_inputs={"climatology": details},
        provenance="Derived snow climatology rows for the requested recurring dates.",
    )


def _trip_window_snowpack_outlook(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
) -> FactorEvaluation:
    window = context.intent.constraints.travel_window
    if window is None or window.mode != "exact_dates":
        return _neutral_evaluation(
            context,
            candidate,
            factor_id="trip_window_snowpack_outlook",
            warning="exact travel dates unavailable",
        )
    requested_dates = _requested_dates(window)
    selected = _forecast_rows_by_date(context, candidate)
    outlooks = tuple(
        snowpack_outlook(selected[item].daily, context.policy.weather)
        for item in requested_dates
        if item in selected
    )
    coverage = len(outlooks) / len(requested_dates)
    utility = (
        sum(outlook.utility for outlook in outlooks) / len(outlooks)
        if outlooks
        else 0.5
    )
    return _evaluation(
        context,
        candidate,
        factor_id="trip_window_snowpack_outlook",
        raw_value={"covered_dates": len(outlooks)},
        raw_utility=utility,
        evidence_cap=coverage,
        evidence_components={"forecast_date_coverage": coverage},
        warnings=("eligible forecast unavailable",) if coverage == 0 else (),
        explanation_inputs={
            "selected_sources": {
                item.isoformat(): selected[item].run.forecast_source_key
                for item in requested_dates
                if item in selected
            }
        },
        provenance="Latest complete source-keyed forecast heads for exact dates.",
    )


def _forecast_rows_by_date(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
) -> dict[date, ServedWeatherForecastDaily]:
    by_date_source: dict[
        tuple[date, str],
        ServedWeatherForecastDaily,
    ] = {}
    for item in candidate.forecast_rows:
        if item.run.forecast_run_id in context.stale_run_ids:
            continue
        if item.run.status != "complete" or not item.daily.is_complete:
            continue
        if item.daily.elevation_band != "mid":
            continue
        if (
            item.lead_days < 0
            or item.lead_days > context.policy.weather.maximum_forecast_lead_days
        ):
            continue
        key = (item.daily.valid_local_date, item.run.forecast_source_key)
        existing = by_date_source.get(key)
        if (
            existing is None
            or item.run.model_initialization_time
            > existing.run.model_initialization_time
        ):
            by_date_source[key] = item

    result: dict[date, ServedWeatherForecastDaily] = {}
    dates = {valid_date for valid_date, _source in by_date_source}
    weather = context.policy.weather
    for valid_date in dates:
        preferred = by_date_source.get(
            (valid_date, weather.preferred_short_range_source)
        )
        fallback = by_date_source.get(
            (valid_date, weather.fallback_and_long_range_source)
        )
        selected: ServedWeatherForecastDaily | None
        if (
            preferred is not None
            and preferred.lead_days <= weather.preferred_short_range_max_lead_days
        ):
            selected = preferred
        else:
            selected = fallback
        if selected is not None:
            result[valid_date] = selected
    return result


def _climatology_for_date(
    rows: Sequence[SnowClimatologyDaily],
    valid_date: date,
    policy: WeatherRankingPolicy,
) -> float | None:
    matching = tuple(
        row
        for row in rows
        if row.elevation_band == "mid"
        and row.month == valid_date.month
        and row.day == valid_date.day
    )
    if not matching:
        return None
    normal = _latest_climatology_row(matching, "normal_30y")
    recent = _latest_climatology_row(matching, "recent_15y")
    primary = normal or recent
    if primary is None:
        return None
    utility = primary.avg_snow_confidence_score
    if normal is not None and recent is not None:
        utility += policy.recent_climatology_adjustment_weight * (
            recent.avg_snow_confidence_score - normal.avg_snow_confidence_score
        )
    return _clamp(utility)


def _latest_climatology_row(
    rows: Sequence[SnowClimatologyDaily],
    baseline_period: str,
) -> SnowClimatologyDaily | None:
    matching = tuple(row for row in rows if row.baseline_period == baseline_period)
    return (
        max(
            matching,
            key=lambda row: (
                row.computed_at,
                row.evidence_seasons,
                row.source_model,
            ),
        )
        if matching
        else None
    )


def _month_climatology(
    rows: Sequence[SnowClimatologyDaily],
    window: TravelWindow,
    policy: WeatherRankingPolicy,
) -> tuple[float, float, Mapping[str, object]]:
    assert window.month is not None
    month_days = sorted(
        {(row.month, row.day) for row in rows if row.month == window.month}
    )
    values = tuple(
        _climatology_for_date(
            rows,
            date(2024, month, day),
            policy,
        )
        for month, day in month_days
    )
    resolved = tuple(value for value in values if value is not None)
    expected_days = calendar.monthrange(2024, window.month)[1]
    coverage = len(resolved) / expected_days
    utility = sum(resolved) / len(resolved) if resolved else 0.5
    return (
        utility,
        coverage,
        {
            "month": window.month,
            "resolved_calendar_days": len(resolved),
            "expected_calendar_days": expected_days,
        },
    )


def _requested_dates(window: TravelWindow) -> tuple[date, ...]:
    assert window.start_date is not None and window.end_date is not None
    return tuple(
        window.start_date + timedelta(days=offset)
        for offset in range((window.end_date - window.start_date).days + 1)
    )


def _snowmaking_support(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
) -> float:
    preference = next(
        (
            item
            for item in context.intent.factor_preferences
            if item.factor_id == "snowmaking_availability"
        ),
        None,
    )
    if preference is None or preference.mode not in {"prefer", "require"}:
        return 0
    evaluation = candidate.snowmaking_evaluation
    if evaluation is None or not isinstance(evaluation.raw_value, Mapping):
        return 0
    if evaluation.raw_value.get("availability") != "available":
        return 0
    return evaluation.effective_evidence_cap


def _apply_snowmaking_uplift(
    natural_utility: float,
    support: float,
    policy: WeatherRankingPolicy,
) -> tuple[float, float]:
    if support <= 0 or natural_utility >= policy.snowmaking_need_zero_at:
        return natural_utility, 0
    need = _clamp(
        (policy.snowmaking_need_zero_at - natural_utility)
        / (policy.snowmaking_need_zero_at - policy.snowmaking_need_full_below)
    )
    uplift = (
        policy.snowmaking_uplift_coefficient * need * (1 - natural_utility) * support
    )
    return _clamp(natural_utility + uplift), uplift


def _neutral_evaluation(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
    *,
    factor_id: str,
    warning: str,
) -> FactorEvaluation:
    return _evaluation(
        context,
        candidate,
        factor_id=factor_id,
        raw_value=None,
        raw_utility=context.policy.factor(factor_id).neutral_utility,
        evidence_cap=0,
        evidence_components={},
        warnings=(warning,),
        explanation_inputs={},
        provenance="No applicable weather evidence.",
    )


def _evaluation(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
    *,
    factor_id: str,
    raw_value: object,
    raw_utility: float,
    evidence_cap: float,
    evidence_components: Mapping[str, object],
    warnings: tuple[str, ...],
    explanation_inputs: Mapping[str, object],
    provenance: str,
) -> FactorEvaluation:
    return FactorEvaluation(
        factor_id=factor_id,
        scope=context.policy.factor(factor_id).scope,
        entity_ids=(candidate.ski_area_id,),
        raw_value=raw_value,
        raw_utility=_clamp(raw_utility),
        neutral_utility=context.policy.factor(factor_id).neutral_utility,
        effective_evidence_cap=evidence_cap,
        evidence_cap_components=evidence_components,
        warnings=warnings,
        provenance_summary=provenance,
        explanation_inputs=explanation_inputs,
    )


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


_WEATHER_EVALUATORS: Mapping[
    str,
    Callable[[WeatherEvaluationContext, WeatherFactorCandidate], FactorEvaluation],
] = {
    "trip_window_snow_fit": _trip_window_snow_fit,
    "climatological_snow_reliability": _climatological_snow_reliability,
    "trip_window_snowpack_outlook": _trip_window_snowpack_outlook,
}
