from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Protocol

from app.domain.models import (
    Destination,
    TravelEffort,
    TravelEffortLabel,
    TravelTolerance,
)

ROAD_DISTANCE_MULTIPLIER = 1.35
AVERAGE_CAR_SPEED_KMH = 93
PROVIDER = "approximate_haversine_v2"
CAVEAT = (
    "Approximate car estimate based on straight-line distance, a road multiplier, "
    "and calibrated long-distance drive speed."
)
EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class TravelOrigin:
    label: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class CachedRoute:
    distance_km: float
    duration_minutes: int


class TravelCacheProtocol(Protocol):
    def get_geocode(self, origin_key: str) -> TravelOrigin | None: ...

    def set_geocode(self, origin_key: str, origin: TravelOrigin) -> None: ...

    def get_route(
        self, origin_key: str, destination_key: str
    ) -> CachedRoute | None: ...

    def set_route(
        self,
        origin_key: str,
        destination_key: str,
        route: CachedRoute,
    ) -> None: ...


class InMemoryTravelCache:
    def __init__(self) -> None:
        self._geocodes: dict[str, TravelOrigin] = {}
        self._routes: dict[tuple[str, str], CachedRoute] = {}

    def get_geocode(self, origin_key: str) -> TravelOrigin | None:
        return self._geocodes.get(origin_key)

    def set_geocode(self, origin_key: str, origin: TravelOrigin) -> None:
        self._geocodes[origin_key] = origin

    def get_route(self, origin_key: str, destination_key: str) -> CachedRoute | None:
        return self._routes.get((origin_key, destination_key))

    def set_route(
        self,
        origin_key: str,
        destination_key: str,
        route: CachedRoute,
    ) -> None:
        self._routes[(origin_key, destination_key)] = route


KNOWN_ORIGINS: dict[str, TravelOrigin] = {
    "munich": TravelOrigin("Munich", 48.1372, 11.5755),
    "milan": TravelOrigin("Milan", 45.4642, 9.19),
    "zurich": TravelOrigin("Zurich", 47.3769, 8.5417),
    "vienna": TravelOrigin("Vienna", 48.2082, 16.3738),
    "berlin": TravelOrigin("Berlin", 52.52, 13.405),
    "paris": TravelOrigin("Paris", 48.8566, 2.3522),
    "lyon": TravelOrigin("Lyon", 45.764, 4.8357),
    "prague": TravelOrigin("Prague", 50.0755, 14.4378),
    "warsaw": TravelOrigin("Warsaw", 52.2297, 21.0122),
    "amsterdam": TravelOrigin("Amsterdam", 52.3676, 4.9041),
    "brussels": TravelOrigin("Brussels", 50.8503, 4.3517),
    "london": TravelOrigin("London", 51.5072, -0.1276),
}

ORIGIN_ALIASES: dict[str, str] = {
    "munchen": "munich",
    "munchen germany": "munich",
    "munich germany": "munich",
}


def normalize_origin_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lower_text = ascii_text.lower()
    without_punctuation = re.sub(r"[^a-z0-9\s]+", " ", lower_text)
    return " ".join(without_punctuation.split())


def assess_travel_effort(
    origin_text: str,
    destination: Destination,
    cache: TravelCacheProtocol,
    max_drive_minutes: int | None = None,
    tolerance: TravelTolerance | None = None,
) -> TravelEffort | None:
    origin_key = normalize_origin_text(origin_text)
    if not origin_key:
        return None
    origin_key = ORIGIN_ALIASES.get(origin_key, origin_key)

    origin = cache.get_geocode(origin_key)
    if origin is None:
        origin = KNOWN_ORIGINS.get(origin_key)
        if origin is None:
            return None
        cache.set_geocode(origin_key, origin)

    destination_key = _destination_cache_key(destination)
    route = cache.get_route(origin_key, destination_key)
    cache_hit = route is not None
    if route is None:
        route = _estimate_route(origin, destination)
        cache.set_route(origin_key, destination_key, route)

    effort_label = _effort_label(route.duration_minutes)
    exceeds_max_drive = (
        max_drive_minutes is not None and route.duration_minutes > max_drive_minutes
    )
    return TravelEffort(
        origin_label=origin.label,
        destination_label=destination.name,
        mode="car",
        distance_km=route.distance_km,
        duration_minutes=route.duration_minutes,
        effort_label=effort_label,
        score=_score_for_effort(effort_label, route.duration_minutes, tolerance),
        summary=f"Approx. {_format_duration(route.duration_minutes)} drive from "
        f"{origin.label}.",
        provenance="estimated_fallback",
        provider=PROVIDER,
        cache_hit=cache_hit,
        caveat=CAVEAT,
        exceeds_max_drive=exceeds_max_drive,
    )


def assess_deterministic_travel_effort(
    origin_text: str,
    destination: Destination,
    max_drive_minutes: int | None = None,
    tolerance: TravelTolerance | None = None,
) -> TravelEffort | None:
    origin_key = normalize_origin_text(origin_text)
    if not origin_key:
        return None
    origin_key = ORIGIN_ALIASES.get(origin_key, origin_key)

    origin = KNOWN_ORIGINS.get(origin_key)
    if origin is None:
        return None

    route = _estimate_route(origin, destination)
    effort_label = _effort_label(route.duration_minutes)
    exceeds_max_drive = (
        max_drive_minutes is not None and route.duration_minutes > max_drive_minutes
    )
    return TravelEffort(
        origin_label=origin.label,
        destination_label=destination.name,
        mode="car",
        distance_km=route.distance_km,
        duration_minutes=route.duration_minutes,
        effort_label=effort_label,
        score=_score_for_effort(effort_label, route.duration_minutes, tolerance),
        summary=f"Approx. {_format_duration(route.duration_minutes)} drive from "
        f"{origin.label}.",
        provenance="estimated_fallback",
        provider=PROVIDER,
        cache_hit=False,
        caveat=CAVEAT,
        exceeds_max_drive=exceeds_max_drive,
    )


def _destination_cache_key(destination: Destination) -> str:
    return (
        f"{destination.resort_id}|{destination.latitude:.5f}|"
        f"{destination.longitude:.5f}"
    )


def _estimate_route(origin: TravelOrigin, destination: Destination) -> CachedRoute:
    straight_line_km = _haversine_km(
        origin.latitude,
        origin.longitude,
        destination.latitude,
        destination.longitude,
    )
    distance_km = straight_line_km * ROAD_DISTANCE_MULTIPLIER
    duration_minutes = round(distance_km / AVERAGE_CAR_SPEED_KMH * 60)
    return CachedRoute(
        distance_km=round(distance_km, 1),
        duration_minutes=duration_minutes,
    )


def _haversine_km(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> float:
    lat_delta = radians(destination_latitude - origin_latitude)
    lon_delta = radians(destination_longitude - origin_longitude)
    origin_lat = radians(origin_latitude)
    destination_lat = radians(destination_latitude)

    haversine = (
        sin(lat_delta / 2) ** 2
        + cos(origin_lat) * cos(destination_lat) * sin(lon_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def _effort_label(duration_minutes: int) -> TravelEffortLabel:
    if duration_minutes <= 180:
        return "easy"
    if duration_minutes <= 360:
        return "moderate"
    if duration_minutes <= 540:
        return "long"
    return "very_long"


def _score_for_effort(
    effort_label: TravelEffortLabel,
    duration_minutes: int,
    tolerance: TravelTolerance | None,
) -> float:
    base_scores: dict[TravelEffortLabel, float] = {
        "easy": 0.95,
        "moderate": 0.78,
        "long": 0.48,
        "very_long": 0.2,
    }
    score = base_scores[effort_label]
    if tolerance == "short" and duration_minutes > 180:
        score -= 0.1 if duration_minutes <= 360 else 0.16
    elif tolerance == "medium" and duration_minutes > 360:
        score -= 0.06
    elif tolerance == "flexible" and duration_minutes > 180:
        score += 0.04 if duration_minutes <= 540 else 0.06
    return min(1.0, max(0.0, score))


def _format_duration(duration_minutes: int) -> str:
    hours, minutes = divmod(duration_minutes, 60)
    if hours == 0:
        return f"{minutes}m"
    if minutes == 0:
        return f"{hours}h"
    return f"{hours}h {minutes}m"
