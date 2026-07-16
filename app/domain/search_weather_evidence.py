from __future__ import annotations

import calendar
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models import SnowClimatologyDaily
from app.domain.search_factors.weather import (
    WeatherEvaluationContext,
    WeatherFactorCandidate,
    forecast_share_for_lead_days,
    select_usable_forecast_rows_by_date,
    snowpack_outlook,
)
from app.domain.search_v4_models import TravelWindow
from app.domain.weather_forecast import ServedWeatherForecastDaily

_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")
_PROFILE_LIMIT = 31


class _WeatherEvidenceModel(BaseModel):
    model_config = _MODEL_CONFIG


class WeatherEvidencePoint(_WeatherEvidenceModel):
    date_or_month_day: str
    snow_depth_cm: float | None = None
    snow_depth_cm_p25: float | None = None
    snow_depth_cm_p50: float | None = None
    snow_depth_cm_p75: float | None = None
    snowfall_cm: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    rain_risk: float | None = None
    thaw_risk: float | None = None
    wind_gust_kmh: float | None = None


class HistoricalWeatherEvidence(_WeatherEvidenceModel):
    source_label: str
    source_model: str
    computed_at: str
    baseline_start_year: int
    baseline_end_year: int
    evidence_seasons: int = Field(ge=0)
    latest_archive_year: int | None = None
    snow_depth_cm_p25: float | None = Field(default=None, ge=0)
    snow_depth_cm_p50: float | None = Field(default=None, ge=0)
    snow_depth_cm_p75: float | None = Field(default=None, ge=0)
    probability_snow_depth_ge_30cm: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    average_daily_snowfall_cm: float | None = Field(default=None, ge=0)
    average_max_temperature_c: float | None = None
    daily_profile: tuple[WeatherEvidencePoint, ...] = Field(
        min_length=1,
        max_length=_PROFILE_LIMIT,
    )


class ForecastWeatherEvidence(_WeatherEvidenceModel):
    source_label: str
    source_model: str
    issued_at: str
    freshness: Literal["fresh", "partial"]
    usable_date_count: int = Field(gt=0)
    requested_date_count: int = Field(gt=0)
    average_forecast_share: float = Field(gt=0, le=1)
    daily_profile: tuple[WeatherEvidencePoint, ...] = Field(
        min_length=1,
        max_length=_PROFILE_LIMIT,
    )

    @model_validator(mode="after")
    def validate_coverage(self) -> Self:
        if self.usable_date_count > self.requested_date_count:
            raise ValueError("usable forecast dates cannot exceed requested dates")
        return self


class SearchWeatherEvidence(_WeatherEvidenceModel):
    mode: Literal["climatology", "forecast_assisted"]
    window_label: str
    elevation_band: Literal["mid_mountain"] = "mid_mountain"
    elevation_m: int | None = None
    interpretation: str
    limitations: tuple[str, ...] = ()
    historical: HistoricalWeatherEvidence
    forecast: ForecastWeatherEvidence | None = None

    @model_validator(mode="after")
    def validate_mode(self) -> Self:
        if self.mode == "climatology" and self.forecast is not None:
            raise ValueError("climatology mode cannot include forecast evidence")
        if self.mode == "forecast_assisted" and self.forecast is None:
            raise ValueError("forecast-assisted mode requires forecast evidence")
        return self


def build_search_weather_evidence(
    *,
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
) -> SearchWeatherEvidence | None:
    window = context.intent.constraints.travel_window
    if window is None:
        return None

    selected_historical = _select_historical_rows(
        candidate.climatology_rows,
        window,
    )
    if not selected_historical:
        return None

    historical = _historical_evidence(selected_historical)
    limitations = list(
        _historical_limitations(
            selected_historical,
            window,
        )
    )
    forecast = (
        _forecast_evidence(context, candidate, window)
        if window.mode == "exact_dates"
        else None
    )
    if window.mode == "exact_dates":
        limitations.extend(
            _forecast_limitations(
                context,
                candidate,
                window,
                forecast,
            )
        )

    mode: Literal["climatology", "forecast_assisted"] = (
        "forecast_assisted" if forecast is not None else "climatology"
    )
    return SearchWeatherEvidence(
        mode=mode,
        window_label=_window_label(window),
        elevation_m=_representative_elevation(selected_historical),
        interpretation=_interpretation(mode, forecast),
        limitations=tuple(dict.fromkeys(limitations)),
        historical=historical,
        forecast=forecast,
    )


def _select_historical_rows(
    rows: Sequence[SnowClimatologyDaily],
    window: TravelWindow,
) -> tuple[SnowClimatologyDaily, ...]:
    rows_by_month_day: dict[tuple[int, int], list[SnowClimatologyDaily]] = {}
    for row in rows:
        if row.elevation_band != "mid":
            continue
        rows_by_month_day.setdefault((row.month, row.day), []).append(row)

    if window.mode == "month":
        assert window.month is not None
        requested_month_days = tuple(
            sorted(key for key in rows_by_month_day if key[0] == window.month)
        )
    else:
        requested_month_days = tuple(
            (item.month, item.day) for item in _requested_dates(window)
        )

    selected: list[SnowClimatologyDaily] = []
    seen: set[tuple[int, int]] = set()
    for month_day in requested_month_days:
        if month_day in seen:
            continue
        seen.add(month_day)
        matching = rows_by_month_day.get(month_day, ())
        normal = _latest_historical_row(matching, "normal_30y")
        recent = _latest_historical_row(matching, "recent_15y")
        selected_row = normal if normal is not None else recent
        if selected_row is not None:
            selected.append(selected_row)
    return tuple(selected)


def _latest_historical_row(
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


def _historical_evidence(
    rows: tuple[SnowClimatologyDaily, ...],
) -> HistoricalWeatherEvidence:
    profile_rows = rows[:_PROFILE_LIMIT]
    return HistoricalWeatherEvidence(
        source_label=_historical_source_label(rows),
        source_model=", ".join(sorted({row.source_model for row in rows})),
        computed_at=max(row.computed_at for row in rows),
        baseline_start_year=min(row.baseline_start_year for row in rows),
        baseline_end_year=max(row.baseline_end_year for row in rows),
        evidence_seasons=min(row.evidence_seasons for row in rows),
        latest_archive_year=_maximum_optional(
            tuple(row.latest_archive_year for row in rows)
        ),
        snow_depth_cm_p25=_average_optional(
            tuple(row.snow_depth_cm_p25 for row in rows)
        ),
        snow_depth_cm_p50=_average_optional(
            tuple(row.snow_depth_cm_p50 for row in rows)
        ),
        snow_depth_cm_p75=_average_optional(
            tuple(row.snow_depth_cm_p75 for row in rows)
        ),
        probability_snow_depth_ge_30cm=(
            sum(row.prob_snow_depth_ge_30cm for row in rows) / len(rows)
        ),
        average_daily_snowfall_cm=(
            sum(row.avg_daily_snowfall_cm for row in rows) / len(rows)
        ),
        average_max_temperature_c=(
            sum(row.avg_max_temperature_c for row in rows) / len(rows)
        ),
        daily_profile=tuple(_historical_point(row) for row in profile_rows),
    )


def _historical_point(row: SnowClimatologyDaily) -> WeatherEvidencePoint:
    return WeatherEvidencePoint(
        date_or_month_day=f"{row.month:02d}-{row.day:02d}",
        snow_depth_cm_p25=row.snow_depth_cm_p25,
        snow_depth_cm_p50=row.snow_depth_cm_p50,
        snow_depth_cm_p75=row.snow_depth_cm_p75,
        snowfall_cm=row.avg_daily_snowfall_cm,
        temperature_max_c=row.avg_max_temperature_c,
        rain_risk=row.prob_rain_risk,
        thaw_risk=row.prob_freeze_thaw,
        wind_gust_kmh=row.avg_wind_gust_kmh,
    )


def _forecast_evidence(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
    window: TravelWindow,
) -> ForecastWeatherEvidence | None:
    requested_dates = _requested_dates(window)
    selected = select_usable_forecast_rows_by_date(context, candidate)
    usable: list[tuple[date, ServedWeatherForecastDaily, float]] = []
    for valid_date in requested_dates:
        row = selected.get(valid_date)
        if row is None:
            continue
        share = forecast_share_for_lead_days(row.lead_days, context.policy.weather)
        if share > 0:
            usable.append((valid_date, row, share))
    if not usable:
        return None

    rows = tuple(row for _valid_date, row, _share in usable)
    return ForecastWeatherEvidence(
        source_label=", ".join(sorted({row.run.producer for row in rows})),
        source_model=", ".join(sorted({row.run.provider_model_id for row in rows})),
        issued_at=max(row.run.model_initialization_time for row in rows).isoformat(),
        freshness=("fresh" if len(usable) == len(requested_dates) else "partial"),
        usable_date_count=len(usable),
        requested_date_count=len(requested_dates),
        average_forecast_share=(
            sum(share for _valid_date, _row, share in usable) / len(usable)
        ),
        daily_profile=tuple(
            _forecast_point(valid_date, row, context)
            for valid_date, row, _share in usable[:_PROFILE_LIMIT]
        ),
    )


def _forecast_point(
    valid_date: date,
    row: ServedWeatherForecastDaily,
    context: WeatherEvaluationContext,
) -> WeatherEvidencePoint:
    outlook = (
        snowpack_outlook(row.daily, context.policy.weather)
        if row.daily.is_complete and row.daily.snow_depth_cm is not None
        else None
    )
    return WeatherEvidencePoint(
        date_or_month_day=valid_date.isoformat(),
        snow_depth_cm=row.daily.snow_depth_cm,
        snowfall_cm=row.daily.snowfall_cm,
        temperature_min_c=row.daily.temperature_2m_min_c,
        temperature_max_c=row.daily.temperature_2m_max_c,
        rain_risk=outlook.rain_risk if outlook is not None else None,
        thaw_risk=outlook.thaw_risk if outlook is not None else None,
        wind_gust_kmh=row.daily.wind_gusts_10m_max_kmh,
    )


def _historical_source_label(rows: Sequence[SnowClimatologyDaily]) -> str:
    baselines = {row.baseline_period for row in rows}
    if baselines == {"normal_30y"}:
        return "30-year snow climatology"
    if baselines == {"recent_15y"}:
        return "Recent 15-year snow climatology"
    return "30-year snow climatology with recent 15-year fallback"


def _historical_limitations(
    rows: Sequence[SnowClimatologyDaily],
    window: TravelWindow,
) -> tuple[str, ...]:
    limitations: list[str] = []
    expected_count = (
        calendar.monthrange(2024, window.month)[1]
        if window.mode == "month" and window.month is not None
        else len(_requested_dates(window))
    )
    if len(rows) < expected_count:
        limitations.append(
            "Historical climatology is available for "
            f"{len(rows)} of {expected_count} requested days."
        )
    if any(row.baseline_period == "recent_15y" for row in rows):
        limitations.append(
            "The recent 15-year baseline is used where the 30-year normal is "
            "unavailable."
        )
    if len(rows) > _PROFILE_LIMIT:
        limitations.append("Daily profiles are limited to the first 31 dates.")
    return tuple(limitations)


def _forecast_limitations(
    context: WeatherEvaluationContext,
    candidate: WeatherFactorCandidate,
    window: TravelWindow,
    forecast: ForecastWeatherEvidence | None,
) -> tuple[str, ...]:
    requested_dates = frozenset(_requested_dates(window))
    relevant = tuple(
        row
        for row in candidate.forecast_rows
        if row.daily.valid_local_date in requested_dates
    )
    limitations: list[str] = []
    if any(row.run.forecast_run_id in context.stale_run_ids for row in relevant):
        limitations.append("Stale forecast runs were excluded.")
    if any(
        row.run.status != "complete" or not row.daily.is_complete for row in relevant
    ):
        limitations.append("Incomplete forecast rows were excluded.")
    if forecast is None:
        limitations.append(
            "No fresh usable forecast is available for the requested dates."
        )
    elif forecast.usable_date_count < forecast.requested_date_count:
        limitations.append(
            "Fresh usable forecast coverage is available for "
            f"{forecast.usable_date_count} of {forecast.requested_date_count} "
            "requested days."
        )
    return tuple(limitations)


def _interpretation(
    mode: Literal["climatology", "forecast_assisted"],
    forecast: ForecastWeatherEvidence | None,
) -> str:
    if mode == "forecast_assisted":
        assert forecast is not None
        return (
            "Fresh forecast evidence supplements the historical climatology for "
            f"{forecast.usable_date_count} of {forecast.requested_date_count} "
            "requested days."
        )
    return "Historical climatology describes the requested travel window."


def _window_label(window: TravelWindow) -> str:
    if window.mode == "month":
        assert window.month is not None
        return calendar.month_name[window.month]
    assert window.start_date is not None and window.end_date is not None
    return f"{window.start_date.isoformat()} to {window.end_date.isoformat()}"


def _requested_dates(window: TravelWindow) -> tuple[date, ...]:
    assert window.start_date is not None and window.end_date is not None
    return tuple(
        window.start_date + timedelta(days=offset)
        for offset in range((window.end_date - window.start_date).days + 1)
    )


def _representative_elevation(
    rows: Sequence[SnowClimatologyDaily],
) -> int | None:
    values = tuple(row.elevation_m for row in rows if row.elevation_m is not None)
    return round(sum(values) / len(values)) if values else None


def _average_optional(values: Sequence[float | None]) -> float | None:
    present = tuple(value for value in values if value is not None)
    return sum(present) / len(present) if present else None


def _maximum_optional(values: Sequence[int | None]) -> int | None:
    present = tuple(value for value in values if value is not None)
    return max(present) if present else None
