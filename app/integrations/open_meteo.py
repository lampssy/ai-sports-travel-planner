from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from statistics import fmean
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from app.domain.models import (
    RawWeatherObservation,
    ResortConditions,
    SkiArea,
    WeatherElevationBand,
    snow_confidence_label_for_score,
)

OPEN_METEO_SOURCE = "open-meteo"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SEVERE_WEATHER_CODES = {65, 67, 75, 82, 86, 95, 96, 99}
LIMITED_WEATHER_CODES = {45, 48, 63, 71, 73, 80, 81}


@dataclass(frozen=True)
class WeatherElevationPoint:
    band: WeatherElevationBand
    elevation_m: int


class OpenMeteoClient:
    def fetch_conditions(
        self,
        resort: SkiArea,
        *,
        elevation_m: int | None = None,
    ) -> dict[str, Any]:
        query = urlencode(
            {
                "latitude": resort.latitude,
                "longitude": resort.longitude,
                "elevation": elevation_m or resort.summit_elevation_m,
                "timezone": "auto",
                "forecast_days": 1,
                "hourly": ",".join(
                    [
                        "snow_depth",
                        "visibility",
                    ]
                ),
                "daily": ",".join(
                    [
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "snowfall_sum",
                        "precipitation_sum",
                        "rain_sum",
                        "precipitation_hours",
                        "snowfall_water_equivalent_sum",
                        "apparent_temperature_max",
                        "apparent_temperature_min",
                        "cloud_cover_mean",
                        "sunshine_duration",
                        "wind_speed_10m_max",
                        "wind_gusts_10m_max",
                    ]
                ),
                "current": ",".join(
                    [
                        "temperature_2m",
                        "weather_code",
                        "snowfall",
                        "wind_speed_10m",
                        "wind_gusts_10m",
                    ]
                ),
            }
        )
        with urlopen(f"{OPEN_METEO_FORECAST_URL}?{query}", timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_historical_weather(
        self,
        resort: SkiArea,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict[str, Any]:
        query = urlencode(
            {
                "latitude": resort.latitude,
                "longitude": resort.longitude,
                "elevation": elevation_m or resort.summit_elevation_m,
                "timezone": "auto",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "hourly": "snow_depth",
                "daily": ",".join(
                    [
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "snowfall_sum",
                        "precipitation_sum",
                        "rain_sum",
                        "precipitation_hours",
                        "snowfall_water_equivalent_sum",
                        "apparent_temperature_max",
                        "apparent_temperature_min",
                        "cloud_cover_mean",
                        "sunshine_duration",
                        "wind_speed_10m_max",
                        "wind_gusts_10m_max",
                    ]
                ),
            }
        )
        with urlopen(f"{OPEN_METEO_ARCHIVE_URL}?{query}", timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


def weather_elevation_points(resort: SkiArea) -> tuple[WeatherElevationPoint, ...]:
    base = int(resort.base_elevation_m)
    summit = int(resort.summit_elevation_m)
    return (
        WeatherElevationPoint(band="base", elevation_m=base),
        WeatherElevationPoint(band="mid", elevation_m=round((base + summit) / 2)),
        WeatherElevationPoint(
            band="upper",
            elevation_m=round(base + 0.9 * (summit - base)),
        ),
    )


def weather_elevation_point(
    resort: SkiArea,
    band: WeatherElevationBand,
) -> WeatherElevationPoint:
    for point in weather_elevation_points(resort):
        if point.band == band:
            return point
    raise ValueError(f"Unsupported weather elevation band: {band}")


def normalize_open_meteo_conditions(
    resort: SkiArea,
    payload: dict[str, Any],
    *,
    observed_at: datetime | None = None,
    elevation_band: WeatherElevationBand | None = None,
    elevation_m: int | None = None,
) -> ResortConditions:
    band = elevation_band or "mid"
    resolved_elevation_m = (
        elevation_m or weather_elevation_point(resort, band).elevation_m
    )
    observation = build_forecast_observation(
        resort,
        payload,
        observed_at=observed_at,
        elevation_band=band,
        elevation_m=resolved_elevation_m,
    )
    return normalize_weather_observation(resort, observation)


def build_forecast_observation(
    resort,
    payload: dict[str, Any],
    *,
    observed_at: datetime | None = None,
    elevation_band: WeatherElevationBand = "mid",
    elevation_m: int | None = None,
) -> RawWeatherObservation:
    reference = observed_at or datetime.now(UTC)
    daily = payload["daily"]
    observed_on = reference.date()
    snow_depth_by_day = _daily_snow_depth_lookup(payload)
    visibility_min_by_day = _daily_min_hourly_lookup(payload, "visibility")
    source_model = payload.get("model") or payload.get("generationtime_ms")
    resolved_elevation_m = (
        elevation_m or weather_elevation_point(resort, elevation_band).elevation_m
    )

    return RawWeatherObservation(
        resort_id=_resolve_resort_id(resort),
        resort_name=resort.name,
        elevation_band=elevation_band,
        elevation_m=resolved_elevation_m,
        observed_on=observed_on.isoformat(),
        observed_at=reference.isoformat(),
        snowfall_cm=float(daily["snowfall_sum"][0]),
        snow_depth_m=snow_depth_by_day.get(observed_on.isoformat()),
        precipitation_sum_mm=_daily_float(daily, "precipitation_sum", 0),
        rain_sum_mm=_daily_float(daily, "rain_sum", 0),
        precipitation_hours=_daily_float(daily, "precipitation_hours", 0),
        snowfall_water_equivalent_sum_mm=_daily_float(
            daily,
            "snowfall_water_equivalent_sum",
            0,
        ),
        temperature_2m_max_c=float(daily["temperature_2m_max"][0]),
        temperature_2m_min_c=float(daily["temperature_2m_min"][0]),
        apparent_temperature_2m_max_c=_daily_float(
            daily,
            "apparent_temperature_max",
            0,
        ),
        apparent_temperature_2m_min_c=_daily_float(
            daily,
            "apparent_temperature_min",
            0,
        ),
        cloud_cover_mean_pct=_daily_float(daily, "cloud_cover_mean", 0),
        sunshine_duration_seconds=_daily_float(daily, "sunshine_duration", 0),
        visibility_min_m=visibility_min_by_day.get(observed_on.isoformat()),
        wind_speed_10m_max_kmh=float(daily["wind_speed_10m_max"][0]),
        wind_gusts_10m_max_kmh=float(daily["wind_gusts_10m_max"][0]),
        weather_code=int(daily["weather_code"][0]),
        record_type="forecast",
        source=OPEN_METEO_SOURCE,
        source_model=str(source_model) if source_model is not None else None,
    )


def build_historical_observations(
    resort,
    payload: dict[str, Any],
    *,
    elevation_band: WeatherElevationBand = "mid",
    elevation_m: int | None = None,
) -> tuple[RawWeatherObservation, ...]:
    daily = payload["daily"]
    dates = daily["time"]
    snow_depth_by_day = _daily_snow_depth_lookup(payload)
    source_model = payload.get("model")
    resolved_elevation_m = (
        elevation_m or weather_elevation_point(resort, elevation_band).elevation_m
    )
    observations: list[RawWeatherObservation] = []

    for index, observed_on in enumerate(dates):
        observations.append(
            RawWeatherObservation(
                resort_id=_resolve_resort_id(resort),
                resort_name=resort.name,
                elevation_band=elevation_band,
                elevation_m=resolved_elevation_m,
                observed_on=observed_on,
                observed_at=datetime.combine(
                    date.fromisoformat(observed_on),
                    time(12, 0),
                    tzinfo=UTC,
                ).isoformat(),
                snowfall_cm=float(daily["snowfall_sum"][index]),
                snow_depth_m=snow_depth_by_day.get(observed_on),
                precipitation_sum_mm=_daily_float(
                    daily,
                    "precipitation_sum",
                    index,
                ),
                rain_sum_mm=_daily_float(daily, "rain_sum", index),
                precipitation_hours=_daily_float(
                    daily,
                    "precipitation_hours",
                    index,
                ),
                snowfall_water_equivalent_sum_mm=_daily_float(
                    daily,
                    "snowfall_water_equivalent_sum",
                    index,
                ),
                temperature_2m_max_c=float(daily["temperature_2m_max"][index]),
                temperature_2m_min_c=float(daily["temperature_2m_min"][index]),
                apparent_temperature_2m_max_c=_daily_float(
                    daily,
                    "apparent_temperature_max",
                    index,
                ),
                apparent_temperature_2m_min_c=_daily_float(
                    daily,
                    "apparent_temperature_min",
                    index,
                ),
                cloud_cover_mean_pct=_daily_float(
                    daily,
                    "cloud_cover_mean",
                    index,
                ),
                sunshine_duration_seconds=_daily_float(
                    daily,
                    "sunshine_duration",
                    index,
                ),
                wind_speed_10m_max_kmh=float(daily["wind_speed_10m_max"][index]),
                wind_gusts_10m_max_kmh=float(daily["wind_gusts_10m_max"][index]),
                weather_code=int(daily["weather_code"][index]),
                record_type="archive",
                source=OPEN_METEO_SOURCE,
                source_model=source_model,
            )
        )

    return tuple(observations)


def normalize_weather_observation(
    resort: SkiArea,
    observation: RawWeatherObservation,
) -> ResortConditions:
    observed_at = datetime.fromisoformat(observation.observed_at)
    current_month = observed_at.month

    if not _is_month_in_season(
        current_month, resort.season_start_month, resort.season_end_month
    ):
        return ResortConditions(
            resort_name=resort.name,
            snow_confidence_score=0.18,
            availability_status="out_of_season",
            weather_summary="Outside the typical ski season window for this resort.",
            conditions_score=0.08,
            updated_at=observation.observed_at,
            source=observation.source or OPEN_METEO_SOURCE,
        )

    snow_confidence_score = _derive_snow_confidence(
        resort=resort,
        snowfall_cm=observation.snowfall_cm,
        snow_depth_m=observation.snow_depth_m,
        temp_max=observation.temperature_2m_max_c,
        temp_min=observation.temperature_2m_min_c,
    )
    availability_status = _derive_availability_status(
        snow_confidence_score=snow_confidence_score,
        weather_code=observation.weather_code,
        wind_speed_max=observation.wind_speed_10m_max_kmh,
        wind_gusts_max=observation.wind_gusts_10m_max_kmh,
    )
    conditions_score = _derive_conditions_score(
        snow_confidence_score=snow_confidence_score,
        availability_status=availability_status,
    )

    return ResortConditions(
        resort_name=resort.name,
        snow_confidence_score=snow_confidence_score,
        availability_status=availability_status,
        weather_summary=_build_weather_summary(
            snow_confidence_score=snow_confidence_score,
            snowfall_cm=observation.snowfall_cm,
            snow_depth_m=observation.snow_depth_m,
            temp_max=observation.temperature_2m_max_c,
            wind_gusts_max=observation.wind_gusts_10m_max_kmh,
            availability_status=availability_status,
            weather_code=observation.weather_code,
        ),
        conditions_score=conditions_score,
        updated_at=observation.observed_at,
        source=observation.source or OPEN_METEO_SOURCE,
    )


def _daily_snow_depth_lookup(payload: dict[str, Any]) -> dict[str, float]:
    hourly = payload.get("hourly")
    if not hourly:
        return {}

    times = hourly.get("time", [])
    values = hourly.get("snow_depth", [])
    snow_depth_by_day: dict[str, list[float]] = {}
    for observed_at, value in zip(times, values, strict=False):
        if value is None:
            continue
        observed_on = str(observed_at).split("T", 1)[0]
        snow_depth_by_day.setdefault(observed_on, []).append(float(value))

    return {
        observed_on: round(fmean(day_values), 3)
        for observed_on, day_values in snow_depth_by_day.items()
        if day_values
    }


def _daily_min_hourly_lookup(
    payload: dict[str, Any],
    variable: str,
) -> dict[str, float]:
    hourly = payload.get("hourly")
    if not hourly:
        return {}

    times = hourly.get("time", [])
    values = hourly.get(variable, [])
    values_by_day: dict[str, list[float]] = {}
    for observed_at, value in zip(times, values, strict=False):
        if value is None:
            continue
        observed_on = str(observed_at).split("T", 1)[0]
        values_by_day.setdefault(observed_on, []).append(float(value))

    return {
        observed_on: min(day_values)
        for observed_on, day_values in values_by_day.items()
        if day_values
    }


def _daily_float(daily: dict[str, Any], variable: str, index: int) -> float | None:
    values = daily.get(variable)
    if values is None or index >= len(values):
        return None
    value = values[index]
    if value is None:
        return None
    return float(value)


def _resolve_resort_id(resort) -> str:
    if hasattr(resort, "ski_area_id"):
        return resort.ski_area_id
    return resort.resort_id


def _is_month_in_season(month: int, start_month: int, end_month: int) -> bool:
    if start_month <= end_month:
        return start_month <= month <= end_month
    return month >= start_month or month <= end_month


def _derive_snow_confidence(
    *,
    resort: SkiArea,
    snowfall_cm: float,
    snow_depth_m: float | None,
    temp_max: float,
    temp_min: float,
) -> float:
    snowfall_factor = min(snowfall_cm / 15, 1.0)
    snow_depth_factor = 0.0
    if snow_depth_m is not None:
        snow_depth_factor = min(snow_depth_m / 1.5, 1.0)

    if temp_max <= 0:
        temperature_factor = 1.0
    elif temp_max <= 3:
        temperature_factor = 0.8
    elif temp_max <= 6:
        temperature_factor = 0.55
    else:
        temperature_factor = 0.3

    if temp_min > 2:
        temperature_factor = max(temperature_factor - 0.15, 0.1)

    elevation_factor = min(resort.summit_elevation_m / 3500, 1.0)
    score = (
        snowfall_factor * 0.3
        + snow_depth_factor * 0.25
        + temperature_factor * 0.3
        + elevation_factor * 0.15
    )
    return round(min(max(score, 0.0), 1.0), 2)


def _derive_availability_status(
    *,
    snow_confidence_score: float,
    weather_code: int,
    wind_speed_max: float,
    wind_gusts_max: float,
) -> str:
    if (
        weather_code in SEVERE_WEATHER_CODES
        or wind_gusts_max >= 85
        or wind_speed_max >= 70
    ):
        return "temporarily_closed"
    if (
        weather_code in LIMITED_WEATHER_CODES
        or wind_gusts_max >= 60
        or wind_speed_max >= 45
        or snow_confidence_score < 0.4
    ):
        return "limited"
    return "open"


def _derive_conditions_score(
    *,
    snow_confidence_score: float,
    availability_status: str,
) -> float:
    availability_adjustment = {
        "open": 0.12,
        "limited": -0.08,
        "temporarily_closed": -0.28,
        "out_of_season": -0.5,
    }[availability_status]
    score = snow_confidence_score * 0.85 + availability_adjustment
    return round(min(max(score, 0.0), 1.0), 2)


def _build_weather_summary(
    *,
    snow_confidence_score: float,
    snowfall_cm: float,
    snow_depth_m: float | None,
    temp_max: float,
    wind_gusts_max: float,
    availability_status: str,
    weather_code: int,
) -> str:
    snow_label = snow_confidence_label_for_score(snow_confidence_score)
    status_text = {
        "open": "low weather disruption risk",
        "limited": "some weather disruption risk",
        "temporarily_closed": "high weather disruption risk",
        "out_of_season": "the resort is outside its typical ski season",
    }[availability_status]

    if weather_code in SEVERE_WEATHER_CODES:
        weather_text = "severe weather signal"
    elif weather_code in LIMITED_WEATHER_CODES:
        weather_text = "mixed weather signal"
    else:
        weather_text = "stable weather signal"

    snow_depth_text = ""
    if snow_depth_m is not None:
        snow_depth_text = f", average snow depth {snow_depth_m:.2f} m"

    return (
        f"{snow_label.capitalize()} snow outlook with {snowfall_cm:.1f} cm snowfall"
        f"{snow_depth_text}, max temperature {temp_max:.1f}°C, gusts up to "
        f"{wind_gusts_max:.0f} km/h; {weather_text} and {status_text}."
    )
