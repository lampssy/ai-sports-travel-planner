from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.data.resort_acquisition.models import (
    CandidateFact,
    ProposalTarget,
    SourceReference,
)
from app.data.resort_acquisition.targeting import (
    proposal_targets_for_single_area_source,
)

OVERPASS_INTERPRETER_URL = "https://overpass-api.de/api/interpreter"
OSM_CONFIDENCE = 0.8


def overpass_relation_query(osm_relation_id: str) -> str:
    return f"[out:json][timeout:25];relation({osm_relation_id});out center tags;"


def extract_osm_relation_candidates(
    *,
    resort_id: str,
    osm_relation_id: str,
    payload: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    resort_payload: dict[str, Any],
) -> list[CandidateFact]:
    relation_id = _relation_id(osm_relation_id)
    if relation_id is None:
        return []

    element = _relation_element(payload, relation_id)
    if element is None:
        return []

    center = element.get("center")
    if not isinstance(center, dict):
        return []

    latitude = _coordinate_component(center.get("lat"), min_value=-90, max_value=90)
    longitude = _coordinate_component(center.get("lon"), min_value=-180, max_value=180)
    if latitude is None or longitude is None:
        return []

    source = SourceReference(source_type="osm", source_url=source_url)
    evidence = (
        f"OpenStreetMap relation {relation_id} center lat={latitude}, lon={longitude}"
    )

    return _coordinate_candidates(
        resort_id=resort_id,
        resort_payload=resort_payload,
        latitude=latitude,
        longitude=longitude,
        source=source,
        fetched_at=fetched_at,
        evidence=evidence,
    )


def _relation_id(osm_relation_id: str) -> int | None:
    try:
        return int(osm_relation_id)
    except (TypeError, ValueError):
        return None


def _relation_element(
    payload: Any,
    relation_id: int,
) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    elements = payload.get("elements")
    if not isinstance(elements, list):
        return None
    for element in elements:
        if not isinstance(element, dict):
            continue
        if element.get("type") == "relation" and element.get("id") == relation_id:
            return element
    return None


def _coordinate_component(
    value: Any,
    *,
    min_value: float,
    max_value: float,
) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < min_value or parsed > max_value:
        return None
    return parsed


def _coordinate_candidates(
    *,
    resort_id: str,
    resort_payload: dict[str, Any],
    latitude: float,
    longitude: float,
    source: SourceReference,
    fetched_at: datetime,
    evidence: str,
) -> list[CandidateFact]:
    candidates: list[CandidateFact] = []
    for field_path, proposed_value in (
        ("latitude", latitude),
        ("longitude", longitude),
    ):
        targets = proposal_targets_for_single_area_source(
            resort_id=resort_id,
            resort_payload=resort_payload,
            field_path=field_path,
            primary_entity_type="destination",
        )
        for target in targets:
            candidates.append(
                _candidate(
                    resort_id=resort_id,
                    target=target,
                    field_path=field_path,
                    proposed_value=proposed_value,
                    source=source,
                    fetched_at=fetched_at,
                    evidence=evidence,
                )
            )
    return candidates


def _candidate(
    *,
    resort_id: str,
    target: ProposalTarget,
    field_path: str,
    proposed_value: float,
    source: SourceReference,
    fetched_at: datetime,
    evidence: str,
) -> CandidateFact:
    return CandidateFact(
        resort_id=resort_id,
        target=target,
        field_path=field_path,
        proposed_value=proposed_value,
        source=source,
        extraction_method="osm",
        fetched_at=fetched_at,
        confidence=OSM_CONFIDENCE,
        evidence=evidence,
    )
