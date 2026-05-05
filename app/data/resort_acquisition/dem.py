from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from app.data.resort_acquisition.models import (
    CandidateFact,
    ProposalTarget,
    SourceReference,
)

OPENTOPODATA_BASE_URL = "https://api.opentopodata.org/v1"
DEFAULT_DEM_DATASET_STACK = "eudem25m,mapzen,srtm90m"
DEM_BASE_ELEVATION_WARNING_THRESHOLD_M = 500
DEM_CONFIDENCE = 0.6


@dataclass(frozen=True)
class CoordinatePoint:
    target_key: str
    latitude: float
    longitude: float


def catalog_ski_area_points(resort_payload: dict[str, Any]) -> list[CoordinatePoint]:
    return [point for point, _entry in _catalog_ski_area_point_entries(resort_payload)]


def opentopodata_url(*, dataset_stack: str, points: list[CoordinatePoint]) -> str:
    locations = "|".join(f"{point.latitude},{point.longitude}" for point in points)
    query = urlencode({"locations": locations}, safe=",")
    return f"{OPENTOPODATA_BASE_URL}/{dataset_stack}?{query}"


def extract_dem_sanity_candidates(
    *,
    resort_id: str,
    payload: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    resort_payload: dict[str, Any],
    dataset_stack: str = DEFAULT_DEM_DATASET_STACK,
) -> list[CandidateFact]:
    if not isinstance(payload, dict):
        return []

    results = payload.get("results")
    if not isinstance(results, list):
        return []

    source = SourceReference(source_type="dem", source_url=source_url)
    candidates: list[CandidateFact] = []
    point_entries = _catalog_ski_area_point_entries(resort_payload)

    for index, (point, ski_area) in enumerate(point_entries):
        if index >= len(results):
            break

        result = results[index]
        if not isinstance(result, dict):
            continue

        dem_elevation = _finite_number(result.get("elevation"))
        base_elevation = _finite_number(ski_area.get("base_elevation_m"))
        if dem_elevation is None or base_elevation is None:
            continue

        rounded_dem_elevation = int(round(dem_elevation))
        if (
            abs(rounded_dem_elevation - base_elevation)
            <= DEM_BASE_ELEVATION_WARNING_THRESHOLD_M
        ):
            continue

        base_value = ski_area["base_elevation_m"]
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                target=ProposalTarget(
                    entity_type="ski_area",
                    entity_id=point.target_key,
                ),
                field_path="base_elevation_m",
                proposed_value=base_value,
                source=source,
                extraction_method="dem",
                fetched_at=fetched_at,
                confidence=DEM_CONFIDENCE,
                evidence=(
                    "OpenTopoData point elevation="
                    f"{rounded_dem_elevation}m at {point.latitude},{point.longitude}; "
                    f"dataset={dataset_stack}"
                ),
                validation_status="warning",
                validation_notes=[
                    "DEM point elevation "
                    f"{rounded_dem_elevation}m is far from catalog base elevation "
                    f"{_format_number(base_elevation)}m"
                ],
            )
        )

    return candidates


def _catalog_ski_area_point_entries(
    resort_payload: dict[str, Any],
) -> list[tuple[CoordinatePoint, dict[str, Any]]]:
    if not isinstance(resort_payload, dict):
        return []

    ski_areas = resort_payload.get("ski_areas")
    if not isinstance(ski_areas, list):
        return []

    entries: list[tuple[CoordinatePoint, dict[str, Any]]] = []
    for ski_area in ski_areas:
        if not isinstance(ski_area, dict):
            continue

        ski_area_id = ski_area.get("ski_area_id")
        if not isinstance(ski_area_id, str) or not ski_area_id.strip():
            continue

        latitude = _coordinate_component(
            ski_area.get("latitude"), min_value=-90, max_value=90
        )
        longitude = _coordinate_component(
            ski_area.get("longitude"), min_value=-180, max_value=180
        )
        if latitude is None or longitude is None:
            continue

        entries.append(
            (
                CoordinatePoint(
                    target_key=ski_area_id,
                    latitude=latitude,
                    longitude=longitude,
                ),
                ski_area,
            )
        )

    return entries


def _coordinate_component(
    value: Any,
    *,
    min_value: float,
    max_value: float,
) -> float | None:
    parsed = _finite_number(value)
    if parsed is None or parsed < min_value or parsed > max_value:
        return None
    return parsed


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed):
        return None
    return parsed


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value)
