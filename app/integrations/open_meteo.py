from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from app.domain.models import Resort, ResortConditions, snow_confidence_label_for_score

OPEN_METEO_SOURCE = "open-meteo"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
SEVERE_WEATHER_CODES = {65, 67, 75, 82, 86, 95, 96, 99}
LIMITED_WEATHER_CODES = {45, 48, 63, 71, 73, 80, 81}


class OpenMeteoClient:
    def fetch_conditions(self, resort: Resort) -> dict[str, Any]:
        query = urlencode(
            {
                "latitude": resort.latitude,
                "longitude": resort.longitude,
                "elevation": resort.summit_elevation_m,
                "timezone": "auto",
                "forecast_days": 1,
                "daily": ",".join(
                    [
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "snowfall_sum",
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
        with urlopen(f"{OPEN_METEO_URL}?{query}", timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))


def normalize_open_meteo_conditions(
    resort: Resort,
    payload: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> ResortConditions:
    reference = observed_at or datetime.now(UTC)
    current_month = reference.month

    if not _is_month_in_season(
        current_month, resort.season_start_month, resort.season_end_month
    ):
        return ResortConditions(
            resort_name=resort.name,
            snow_confidence_score=0.18,
            availability_status="out_of_season",
            weather_summary="Outside the typical ski season window for this resort.",
            conditions_score=0.08,
            updated_at=reference.isoformat(),
            source=OPEN_METEO_SOURCE,
        )

    daily = payload["daily"]
    current = payload.get("current", {})

    snowfall_sum = float(daily["snowfall_sum"][0])
    temp_max = float(daily["temperature_2m_max"][0])
    temp_min = float(daily["temperature_2m_min"][0])
    wind_speed_max = float(daily["wind_speed_10m_max"][0])
    wind_gusts_max = float(daily["wind_gusts_10m_max"][0])
    weather_code = int(daily["weather_code"][0])
    current_weather_code = int(current.get("weather_code", weather_code))

    snow_confidence_score = _derive_snow_confidence(
        resort=resort,
        snowfall_sum=snowfall_sum,
        temp_max=temp_max,
        temp_min=temp_min,
    )
    availability_status = _derive_availability_status(
        snow_confidence_score=snow_confidence_score,
        weather_code=current_weather_code,
        wind_speed_max=wind_speed_max,
        wind_gusts_max=wind_gusts_max,
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
            snowfall_sum=snowfall_sum,
            temp_max=temp_max,
            wind_gusts_max=wind_gusts_max,
            availability_status=availability_status,
            weather_code=weather_code,
        ),
        conditions_score=conditions_score,
        updated_at=reference.isoformat(),
        source=OPEN_METEO_SOURCE,
    )


def _is_month_in_season(month: int, start_month: int, end_month: int) -> bool:
    if start_month <= end_month:
        return start_month <= month <= end_month
    return month >= start_month or month <= end_month


def _derive_snow_confidence(
    *,
    resort: Resort,
    snowfall_sum: float,
    temp_max: float,
    temp_min: float,
) -> float:
    snowfall_factor = min(snowfall_sum / 15, 1.0)

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
    score = snowfall_factor * 0.45 + temperature_factor * 0.35 + elevation_factor * 0.2
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
    snowfall_sum: float,
    temp_max: float,
    wind_gusts_max: float,
    availability_status: str,
    weather_code: int,
) -> str:
    snow_label = snow_confidence_label_for_score(snow_confidence_score)
    status_text = {
        "open": "operations look normal",
        "limited": "some operations may be limited",
        "temporarily_closed": "weather may disrupt lift operations",
        "out_of_season": "the resort is outside its typical ski season",
    }[availability_status]

    if weather_code in SEVERE_WEATHER_CODES:
        weather_text = "severe weather signal"
    elif weather_code in LIMITED_WEATHER_CODES:
        weather_text = "mixed weather signal"
    else:
        weather_text = "stable weather signal"

    return (
        f"{snow_label.capitalize()} snow outlook with {snowfall_sum:.1f} mm snowfall, "
        f"max temperature {temp_max:.1f}°C, gusts up to {wind_gusts_max:.0f} km/h; "
        f"{weather_text} and {status_text}."
    )
