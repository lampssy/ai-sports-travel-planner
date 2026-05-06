from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urldefrag, urlparse

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
OSM_DISCOVERY_RADIUS_M = 12000
OSM_DISCOVERY_MIN_CONFIDENCE = 0.7
OSM_DISCOVERY_SEED_CONFIDENCE = 0.8

_DISCOVERY_URL_FIELD_PATHS = {
    "website": "ski_area_official_url",
    "contact:website": "ski_area_official_url",
    "operator:website": "ski_area_official_url",
    "brand:website": "ski_area_official_url",
    "website:map": "trail_map_url",
}
_DISCOVERY_SKI_FILTERS = (
    '["site"="piste"]',
    '["route"="piste"]',
    '["landuse"="winter_sports"]',
    '["sport"="skiing"]',
    '["piste:type"]',
    '["aerialway"]',
)
_REFERENCE_DOMAIN_RE = re.compile(
    r"(^|\.)("
    r"skiresort\.[a-z.]+|"
    r"outdooractive\.com|"
    r"schweizmobil\.ch|"
    r"leitner-ropeways\.com|"
    r"winterrodeln\.org"
    r")$"
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class _OsmDiscoveryEvidence:
    field_path: str
    proposed_value: str
    element_type: str
    element_id: int
    element_name: str | None
    url_tag: str
    distance_km: float | None
    tags: dict[str, str]
    confidence: float
    domain_support: int


def normalize_osm_relation_id(osm_relation_id: str) -> str | None:
    try:
        relation_id = int(osm_relation_id)
    except (TypeError, ValueError):
        return None
    if relation_id <= 0:
        return None
    return str(relation_id)


def overpass_relation_query(osm_relation_id: str) -> str:
    relation_id = normalize_osm_relation_id(osm_relation_id)
    if relation_id is None:
        raise ValueError("osm_relation_id must be a positive integer")
    return f"[out:json][timeout:25];relation({relation_id});out center tags;"


def overpass_discovery_query(
    *,
    latitude: float,
    longitude: float,
    radius_m: int = OSM_DISCOVERY_RADIUS_M,
) -> str:
    parsed_latitude = _coordinate_component(latitude, min_value=-90, max_value=90)
    parsed_longitude = _coordinate_component(longitude, min_value=-180, max_value=180)
    if parsed_latitude is None or parsed_longitude is None:
        raise ValueError("latitude and longitude must be finite coordinates")
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")

    selectors = [
        f"nwr(around:{radius_m},{parsed_latitude},{parsed_longitude})"
        f'["{url_tag}"]{ski_filter};'
        for url_tag in _DISCOVERY_URL_FIELD_PATHS
        for ski_filter in _DISCOVERY_SKI_FILTERS
    ]
    return (
        "[out:json][timeout:35];\n(\n  "
        + "\n  ".join(selectors)
        + "\n);\nout center tags 100;"
    )


def extract_osm_discovery_candidates(
    *,
    resort_id: str,
    payload: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    resort_payload: dict[str, Any],
    radius_m: int = OSM_DISCOVERY_RADIUS_M,
) -> list[CandidateFact]:
    catalog_latitude = _coordinate_component(
        resort_payload.get("latitude"),
        min_value=-90,
        max_value=90,
    )
    catalog_longitude = _coordinate_component(
        resort_payload.get("longitude"),
        min_value=-180,
        max_value=180,
    )
    if catalog_latitude is None or catalog_longitude is None:
        return []

    elements = payload.get("elements")
    if not isinstance(elements, list):
        return []

    resort_name = str(resort_payload.get("name") or resort_id)
    grouped_evidence: dict[tuple[str, str], list[_OsmDiscoveryEvidence]] = {}
    relation_evidence: dict[int, _OsmDiscoveryEvidence] = {}
    domain_counts: dict[str, int] = {}

    for element in elements:
        if not isinstance(element, dict):
            continue
        evidence_items = _discovery_evidence_for_element(
            element=element,
            resort_name=resort_name,
            catalog_latitude=catalog_latitude,
            catalog_longitude=catalog_longitude,
            radius_m=radius_m,
        )
        for evidence in evidence_items:
            domain = _url_domain(evidence.proposed_value)
            if domain is not None:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            grouped_evidence.setdefault(
                (evidence.field_path, evidence.proposed_value),
                [],
            ).append(evidence)

    candidates: list[CandidateFact] = []
    source = SourceReference(source_type="osm", source_url=source_url)
    for evidence_group in grouped_evidence.values():
        scored_group = [
            _with_domain_support(
                evidence,
                domain_counts.get(_url_domain(evidence.proposed_value) or "", 1),
            )
            for evidence in evidence_group
        ]
        best_evidence = max(scored_group, key=lambda evidence: evidence.confidence)
        if best_evidence.confidence < OSM_DISCOVERY_MIN_CONFIDENCE:
            continue
        candidates.append(
            _discovery_candidate(
                resort_id=resort_id,
                field_path=best_evidence.field_path,
                proposed_value=best_evidence.proposed_value,
                source=source,
                fetched_at=fetched_at,
                evidence=best_evidence,
            )
        )
        if best_evidence.element_type == "relation":
            existing_relation = relation_evidence.get(best_evidence.element_id)
            if (
                existing_relation is None
                or best_evidence.confidence > existing_relation.confidence
            ):
                relation_evidence[best_evidence.element_id] = best_evidence

    for relation_id, evidence in relation_evidence.items():
        candidates.append(
            _discovery_candidate(
                resort_id=resort_id,
                field_path="regional_data_ids.osm_relation_id",
                proposed_value=str(relation_id),
                source=source,
                fetched_at=fetched_at,
                evidence=evidence,
            )
        )

    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.confidence,
            candidate.field_path,
            str(candidate.proposed_value),
        ),
    )


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


def _discovery_evidence_for_element(
    *,
    element: dict[str, Any],
    resort_name: str,
    catalog_latitude: float,
    catalog_longitude: float,
    radius_m: int,
) -> list[_OsmDiscoveryEvidence]:
    tags = _string_tags(element.get("tags"))
    if not tags:
        return []

    element_type = element.get("type")
    element_id = element.get("id")
    if not isinstance(element_type, str) or not isinstance(element_id, int):
        return []

    center = element.get("center") if isinstance(element.get("center"), dict) else {}
    latitude = _coordinate_component(
        center.get("lat", element.get("lat")),
        min_value=-90,
        max_value=90,
    )
    longitude = _coordinate_component(
        center.get("lon", element.get("lon")),
        min_value=-180,
        max_value=180,
    )
    distance_km = (
        _distance_km(catalog_latitude, catalog_longitude, latitude, longitude)
        if latitude is not None and longitude is not None
        else None
    )

    element_name = tags.get("name") or tags.get("piste:name")
    if _is_sled_or_rodel_feature(tags):
        return []
    name_score = _name_score(resort_name, element_name)
    if element_name is not None and name_score <= 0:
        return []
    base_score = _element_type_score(element_type)
    base_score += _ski_feature_score(tags)
    base_score += name_score
    base_score += _distance_score(distance_km, radius_m)
    if base_score <= 0:
        return []

    evidence_items: list[_OsmDiscoveryEvidence] = []
    for url_tag, field_path in _DISCOVERY_URL_FIELD_PATHS.items():
        url = _normalize_url(tags.get(url_tag))
        if url is None or _is_reference_domain(url):
            continue
        confidence = min(0.95, base_score + _url_tag_score(url_tag))
        evidence_items.append(
            _OsmDiscoveryEvidence(
                field_path=field_path,
                proposed_value=url,
                element_type=element_type,
                element_id=element_id,
                element_name=element_name,
                url_tag=url_tag,
                distance_km=distance_km,
                tags=_evidence_tags(tags),
                confidence=confidence,
                domain_support=1,
            )
        )
    return evidence_items


def _with_domain_support(
    evidence: _OsmDiscoveryEvidence,
    domain_support: int,
) -> _OsmDiscoveryEvidence:
    support_bonus = min(0.15, max(0, domain_support - 1) * 0.05)
    return _OsmDiscoveryEvidence(
        field_path=evidence.field_path,
        proposed_value=evidence.proposed_value,
        element_type=evidence.element_type,
        element_id=evidence.element_id,
        element_name=evidence.element_name,
        url_tag=evidence.url_tag,
        distance_km=evidence.distance_km,
        tags=evidence.tags,
        confidence=min(0.95, evidence.confidence + support_bonus),
        domain_support=domain_support,
    )


def _discovery_candidate(
    *,
    resort_id: str,
    field_path: str,
    proposed_value: str,
    source: SourceReference,
    fetched_at: datetime,
    evidence: _OsmDiscoveryEvidence,
) -> CandidateFact:
    return CandidateFact(
        resort_id=resort_id,
        field_path=field_path,
        proposed_value=proposed_value,
        source=source,
        extraction_method="osm_discovery",
        fetched_at=fetched_at,
        confidence=evidence.confidence,
        evidence=_discovery_evidence_text(evidence),
    )


def _discovery_evidence_text(evidence: _OsmDiscoveryEvidence) -> str:
    tag_text = ", ".join(
        f"{key}={value}" for key, value in sorted(evidence.tags.items())
    )
    distance_text = (
        f"{evidence.distance_km:.1f}km"
        if evidence.distance_km is not None
        else "unknown"
    )
    return (
        f"OpenStreetMap {evidence.element_type}/{evidence.element_id} "
        f"name={evidence.element_name!r}; url_tag={evidence.url_tag}; "
        f"tags={tag_text}; distance={distance_text}; "
        f"domain_support={evidence.domain_support}; "
        f"score={evidence.confidence:.2f}"
    )


def _relation_id(osm_relation_id: str) -> int | None:
    normalized_relation_id = normalize_osm_relation_id(osm_relation_id)
    if normalized_relation_id is None:
        return None
    return int(normalized_relation_id)


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


def _string_tags(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    tags: dict[str, str] = {}
    for key, nested_value in value.items():
        if isinstance(key, str) and isinstance(nested_value, str) and nested_value:
            tags[key] = nested_value
    return tags


def _normalize_url(value: str | None) -> str | None:
    if value is None:
        return None
    url = value.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(urldefrag(url).url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed.geturl()


def _url_domain(url: str) -> str | None:
    hostname = urlparse(url).hostname
    if hostname is None:
        return None
    return hostname.lower().removeprefix("www.")


def _is_reference_domain(url: str) -> bool:
    domain = _url_domain(url)
    return domain is not None and _REFERENCE_DOMAIN_RE.search(domain) is not None


def _element_type_score(element_type: str) -> float:
    if element_type == "relation":
        return 0.25
    if element_type == "way":
        return 0.15
    if element_type == "node":
        return 0.05
    return 0.0


def _ski_feature_score(tags: dict[str, str]) -> float:
    score = 0.0
    if tags.get("landuse") == "winter_sports":
        score += 0.25
    if tags.get("site") == "piste":
        score += 0.25
    if tags.get("route") == "piste":
        score += 0.20
    if tags.get("sport") == "skiing":
        score += 0.10
    if "piste:type" in tags:
        score += 0.05
    if "aerialway" in tags:
        score += 0.05
    return min(score, 0.45)


def _is_sled_or_rodel_feature(tags: dict[str, str]) -> bool:
    piste_type = tags.get("piste:type", "").lower()
    return any(term in piste_type for term in ("sled", "sledge", "rodel"))


def _name_score(resort_name: str, element_name: str | None) -> float:
    if element_name is None:
        return 0.0
    resort_tokens = _normalized_tokens(resort_name)
    element_tokens = _normalized_tokens(element_name)
    if not resort_tokens or not element_tokens:
        return 0.0
    if resort_tokens == element_tokens:
        return 0.30
    resort_text = " ".join(resort_tokens)
    element_text = " ".join(element_tokens)
    if resort_text in element_text or element_text in resort_text:
        return 0.20
    overlap = len(set(resort_tokens).intersection(element_tokens))
    overlap_ratio = overlap / max(len(set(resort_tokens)), 1)
    if overlap_ratio >= 0.5:
        return 0.10
    return 0.0


def _normalized_tokens(value: str) -> list[str]:
    normalized = value.lower()
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
    return _TOKEN_RE.findall(normalized)


def _distance_score(distance_km: float | None, radius_m: int) -> float:
    if distance_km is None:
        return 0.0
    radius_km = radius_m / 1000
    if distance_km <= 3:
        return 0.20
    if distance_km <= 8:
        return 0.10
    if distance_km <= radius_km:
        return 0.05
    return 0.0


def _url_tag_score(url_tag: str) -> float:
    if url_tag in {"operator:website", "brand:website"}:
        return 0.12
    return 0.10


def _distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius_km = 6371.0
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius_km * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def _evidence_tags(tags: dict[str, str]) -> dict[str, str]:
    evidence_keys = (
        "landuse",
        "site",
        "route",
        "sport",
        "piste:type",
        "aerialway",
        "operator",
        "brand",
        "wikidata",
    )
    return {key: tags[key] for key in evidence_keys if key in tags}


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
