from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any

from app.data.resort_acquisition.models import (
    CandidateFact,
    ProposalTarget,
    SourceReference,
)

EARTH_RADIUS_M = 6_371_000
WIKIDATA_COORDINATE_LOCATION = "P625"

BASE_TYPES = {
    "resort_center",
    "satellite_village",
    "quiet_village",
    "family_base",
    "premium_base",
    "budget_base",
    "nightlife_base",
}
ACCESS_MODES = {"walk", "ski_bus", "car_recommended", "unknown"}
ATMOSPHERE_TAGS = {
    "quiet",
    "lively",
    "family_friendly",
    "premium",
    "budget_friendly",
    "beginner_friendly",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def extract_osm_stay_base_candidates(
    *,
    resort_id: str,
    stay_base: dict[str, Any],
    osm_elements: Any,
    fetched_at: datetime,
    source_url: str = "https://overpass-api.de/api/interpreter",
) -> list[CandidateFact]:
    target = _stay_base_target(stay_base)
    stay_base_name = _non_blank_string(stay_base.get("name"))
    if target is None or stay_base_name is None:
        return []

    match = _exact_name_matched_osm_element(stay_base_name, _elements(osm_elements))
    if match is None:
        return []

    element_type = match["type"]
    element_id = match["id"]
    element_name = match["name"]
    latitude = match["latitude"]
    longitude = match["longitude"]
    source = SourceReference(source_type="osm", source_url=source_url)
    evidence = (
        f"OpenStreetMap {element_type}/{element_id} name='{element_name}' "
        f"matched stay base '{stay_base_name}'"
    )

    return [
        _candidate(
            resort_id=resort_id,
            target=target,
            field_path="latitude",
            proposed_value=latitude,
            source=source,
            extraction_method="stay_base_osm",
            fetched_at=fetched_at,
            confidence=0.82,
            evidence=evidence,
        ),
        _candidate(
            resort_id=resort_id,
            target=target,
            field_path="longitude",
            proposed_value=longitude,
            source=source,
            extraction_method="stay_base_osm",
            fetched_at=fetched_at,
            confidence=0.82,
            evidence=evidence,
        ),
        _candidate(
            resort_id=resort_id,
            target=target,
            field_path="regional_data_ids.osm_object_id",
            proposed_value=f"{element_type}/{element_id}",
            source=source,
            extraction_method="stay_base_osm",
            fetched_at=fetched_at,
            confidence=0.82,
            evidence=evidence,
        ),
    ]


def extract_lift_distance_candidates(
    *,
    resort_id: str,
    stay_base: dict[str, Any],
    lift_elements: Any,
    fetched_at: datetime,
    source_url: str = "https://overpass-api.de/api/interpreter",
) -> list[CandidateFact]:
    target = _stay_base_target(stay_base)
    stay_base_name = _non_blank_string(stay_base.get("name"))
    stay_latitude = _coordinate(stay_base.get("latitude"), min_value=-90, max_value=90)
    stay_longitude = _coordinate(
        stay_base.get("longitude"),
        min_value=-180,
        max_value=180,
    )
    if (
        target is None
        or stay_base_name is None
        or stay_latitude is None
        or stay_longitude is None
    ):
        return []

    nearest = _nearest_lift_point(
        stay_latitude,
        stay_longitude,
        _elements(lift_elements),
    )
    if nearest is None:
        return []

    distance_m = round(
        _haversine_m(
            stay_latitude,
            stay_longitude,
            nearest["latitude"],
            nearest["longitude"],
        )
    )
    source = SourceReference(source_type="osm", source_url=source_url)
    evidence = (
        f"Nearest OSM lift/station '{nearest['name']}' "
        f"({nearest['type']}/{nearest['id']}) is {distance_m}m from "
        f"stay base '{stay_base_name}'"
    )

    return [
        _candidate(
            resort_id=resort_id,
            target=target,
            field_path="nearest_lift_name",
            proposed_value=nearest["name"],
            source=source,
            extraction_method="stay_base_lift_distance",
            fetched_at=fetched_at,
            confidence=0.78,
            evidence=evidence,
        ),
        _candidate(
            resort_id=resort_id,
            target=target,
            field_path="nearest_lift_distance_m",
            proposed_value=distance_m,
            source=source,
            extraction_method="stay_base_lift_distance",
            fetched_at=fetched_at,
            confidence=0.78,
            evidence=evidence,
        ),
        _candidate(
            resort_id=resort_id,
            target=target,
            field_path="lift_distance",
            proposed_value=_lift_distance_bucket(distance_m),
            source=source,
            extraction_method="stay_base_lift_distance",
            fetched_at=fetched_at,
            confidence=0.72,
            evidence=evidence,
        ),
    ]


def extract_wikidata_stay_base_candidates(
    *,
    resort_id: str,
    stay_base: dict[str, Any],
    entity: dict[str, Any],
    fetched_at: datetime,
) -> list[CandidateFact]:
    target = _stay_base_target(stay_base)
    stay_base_name = _non_blank_string(stay_base.get("name"))
    wikidata_id = _non_blank_string(entity.get("id"))
    label = _wikidata_english_label(entity)
    if (
        target is None
        or stay_base_name is None
        or wikidata_id is None
        or label is None
        or _normalize_name(label) != _normalize_name(stay_base_name)
    ):
        return []

    source = SourceReference(
        source_type="wikidata",
        source_url=f"https://www.wikidata.org/wiki/{wikidata_id}",
    )
    evidence = (
        f"Wikidata {wikidata_id} label '{label}' matched stay base '{stay_base_name}'"
    )
    candidates = [
        _candidate(
            resort_id=resort_id,
            target=target,
            field_path="regional_data_ids.wikidata_id",
            proposed_value=wikidata_id,
            source=source,
            extraction_method="stay_base_wikidata",
            fetched_at=fetched_at,
            confidence=0.8,
            evidence=evidence,
        )
    ]

    coordinate = _wikidata_coordinate(entity)
    if coordinate is not None:
        latitude, longitude = coordinate
        candidates.extend(
            [
                _candidate(
                    resort_id=resort_id,
                    target=target,
                    field_path="latitude",
                    proposed_value=latitude,
                    source=source,
                    extraction_method="stay_base_wikidata",
                    fetched_at=fetched_at,
                    confidence=0.72,
                    evidence=evidence,
                ),
                _candidate(
                    resort_id=resort_id,
                    target=target,
                    field_path="longitude",
                    proposed_value=longitude,
                    source=source,
                    extraction_method="stay_base_wikidata",
                    fetched_at=fetched_at,
                    confidence=0.72,
                    evidence=evidence,
                ),
            ]
        )
    return candidates


def profile_candidates_from_llm_output(
    *,
    resort_id: str,
    stay_base: dict[str, Any],
    output: dict[str, Any],
    fetched_at: datetime,
) -> list[CandidateFact]:
    target = _stay_base_target(stay_base)
    if target is None:
        return []

    confidence = _confidence(output.get("confidence"))
    if confidence is None or confidence < 0.6:
        return []

    base_type = output.get("base_type")
    access_mode = output.get("access_mode")
    atmosphere_tags = output.get("atmosphere_tags") or []
    if base_type is not None and base_type not in BASE_TYPES:
        return []
    if access_mode is not None and access_mode not in ACCESS_MODES:
        return []
    if not isinstance(atmosphere_tags, list):
        return []
    if any(tag not in ATMOSPHERE_TAGS for tag in atmosphere_tags):
        return []

    source = SourceReference(
        source_type="official",
        source_name="stay-base profile LLM review packet",
    )
    evidence = _profile_evidence_text(output)
    candidates: list[CandidateFact] = []
    for field_path, proposed_value in (
        ("base_type", base_type),
        ("access_mode", access_mode),
        ("atmosphere_tags", atmosphere_tags if atmosphere_tags else None),
    ):
        if proposed_value is None:
            continue
        candidates.append(
            _candidate(
                resort_id=resort_id,
                target=target,
                field_path=field_path,
                proposed_value=proposed_value,
                source=source,
                extraction_method="stay_base_profile_llm",
                fetched_at=fetched_at,
                confidence=confidence,
                evidence=evidence,
                validation_status="warning",
            )
        )
    return candidates


def _stay_base_target(stay_base: dict[str, Any]) -> ProposalTarget | None:
    stay_base_id = _non_blank_string(stay_base.get("stay_base_id"))
    if stay_base_id is None:
        return None
    return ProposalTarget(entity_type="stay_base", entity_id=stay_base_id)


def _elements(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        elements = value.get("elements")
    else:
        elements = value
    if not isinstance(elements, list):
        return []
    return [element for element in elements if isinstance(element, dict)]


def _exact_name_matched_osm_element(
    stay_base_name: str,
    elements: list[dict[str, Any]],
) -> dict[str, Any] | None:
    normalized_name = _normalize_name(stay_base_name)
    matches: list[dict[str, Any]] = []
    for element in elements:
        parsed = _element_point(element)
        if parsed is None:
            continue
        element_name = parsed["name"]
        if _normalize_name(element_name) == normalized_name:
            matches.append(parsed)
    if not matches:
        return None
    return sorted(matches, key=_osm_match_sort_key)[0]


def _osm_match_sort_key(match: dict[str, Any]) -> tuple[int, int]:
    type_rank = {"node": 0, "way": 1, "relation": 2}
    return (
        type_rank.get(str(match.get("type")), len(type_rank)),
        int(match["id"]),
    )


def _nearest_lift_point(
    latitude: float,
    longitude: float,
    elements: list[dict[str, Any]],
) -> dict[str, Any] | None:
    nearest: dict[str, Any] | None = None
    nearest_distance: float | None = None
    for element in elements:
        parsed = _element_point(element)
        if parsed is None or not _is_lift_or_station(element):
            continue
        distance_m = _haversine_m(
            latitude,
            longitude,
            parsed["latitude"],
            parsed["longitude"],
        )
        if nearest_distance is None or distance_m < nearest_distance:
            nearest = parsed
            nearest_distance = distance_m
    return nearest


def _element_point(element: dict[str, Any]) -> dict[str, Any] | None:
    tags = element.get("tags") if isinstance(element.get("tags"), dict) else {}
    name = _non_blank_string(tags.get("name"))
    element_type = _non_blank_string(element.get("type"))
    element_id = element.get("id")
    center = element.get("center") if isinstance(element.get("center"), dict) else {}
    latitude = _coordinate(
        element.get("lat", center.get("lat")),
        min_value=-90,
        max_value=90,
    )
    longitude = _coordinate(
        element.get("lon", center.get("lon")),
        min_value=-180,
        max_value=180,
    )
    if (
        name is None
        or element_type is None
        or not isinstance(element_id, int)
        or latitude is None
        or longitude is None
    ):
        return None
    return {
        "type": element_type,
        "id": element_id,
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
    }


def _is_lift_or_station(element: dict[str, Any]) -> bool:
    tags = element.get("tags") if isinstance(element.get("tags"), dict) else {}
    if not all(isinstance(key, str) for key in tags):
        return False
    return any(
        key == "aerialway" or key.startswith("aerialway:")
        for key, value in tags.items()
        if isinstance(value, str) and value.strip()
    )


def _wikidata_english_label(entity: dict[str, Any]) -> str | None:
    labels = entity.get("labels")
    if not isinstance(labels, dict):
        return None
    english_label = labels.get("en")
    if not isinstance(english_label, dict):
        return None
    return _non_blank_string(english_label.get("value"))


def _wikidata_coordinate(entity: dict[str, Any]) -> tuple[float, float] | None:
    claims = entity.get("claims")
    if not isinstance(claims, dict):
        return None
    coordinate_claims = claims.get(WIKIDATA_COORDINATE_LOCATION)
    if not isinstance(coordinate_claims, list):
        return None
    for claim in coordinate_claims:
        if not isinstance(claim, dict) or claim.get("rank") == "deprecated":
            continue
        value = _wikidata_claim_value(claim)
        if not isinstance(value, dict):
            continue
        latitude = _coordinate(value.get("latitude"), min_value=-90, max_value=90)
        longitude = _coordinate(value.get("longitude"), min_value=-180, max_value=180)
        if latitude is not None and longitude is not None:
            return latitude, longitude
    return None


def _wikidata_claim_value(claim: dict[str, Any]) -> Any:
    mainsnak = claim.get("mainsnak")
    if not isinstance(mainsnak, dict):
        return None
    datavalue = mainsnak.get("datavalue")
    if not isinstance(datavalue, dict):
        return None
    return datavalue.get("value")


def _profile_evidence_text(output: dict[str, Any]) -> str:
    summary = _non_blank_string(output.get("evidence_summary")) or "No summary"
    source_claims = output.get("source_claims")
    if not isinstance(source_claims, list):
        return f"Summary: {summary}"

    claims: list[str] = []
    for source_claim in source_claims:
        if not isinstance(source_claim, dict):
            continue
        url = _non_blank_string(source_claim.get("url"))
        claim = _non_blank_string(source_claim.get("claim"))
        if url is None and claim is None:
            continue
        if url is None:
            claims.append(claim or "")
        elif claim is None:
            claims.append(url)
        else:
            claims.append(f"{url}: {claim}")
    if not claims:
        return f"Summary: {summary}"
    return f"Summary: {summary}; Source claims: {' | '.join(claims)}"


def _candidate(
    *,
    resort_id: str,
    target: ProposalTarget,
    field_path: str,
    proposed_value: Any,
    source: SourceReference,
    extraction_method: str,
    fetched_at: datetime,
    confidence: float,
    evidence: str,
    validation_status: str = "accepted",
) -> CandidateFact:
    return CandidateFact(
        resort_id=resort_id,
        target=target,
        field_path=field_path,
        proposed_value=proposed_value,
        source=source,
        extraction_method=extraction_method,
        fetched_at=fetched_at,
        confidence=confidence,
        evidence=evidence,
        validation_status=validation_status,
    )


def _lift_distance_bucket(distance_m: int) -> str:
    if distance_m <= 300:
        return "near"
    if distance_m <= 900:
        return "medium"
    return "far"


def _haversine_m(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    delta_latitude = math.radians(latitude_b - latitude_a)
    delta_longitude = math.radians(longitude_b - longitude_a)
    origin_latitude = math.radians(latitude_a)
    destination_latitude = math.radians(latitude_b)
    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(origin_latitude)
        * math.cos(destination_latitude)
        * math.sin(delta_longitude / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(haversine))


def _coordinate(value: Any, *, min_value: float, max_value: float) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < min_value or parsed > max_value:
        return None
    return parsed


def _confidence(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < 0 or parsed > 1:
        return None
    return parsed


def _non_blank_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_name(value: str) -> str:
    normalized = value.casefold()
    replacements = {
        "ä": "a",
        "ö": "o",
        "ü": "u",
        "ß": "ss",
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "á": "a",
        "í": "i",
        "ì": "i",
        "ó": "o",
        "ò": "o",
        "ú": "u",
        "ù": "u",
    }
    for original, replacement in replacements.items():
        normalized = normalized.replace(original, replacement)
    return " ".join(_TOKEN_RE.findall(normalized))
