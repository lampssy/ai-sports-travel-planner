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

WIKIDATA_ENTITY_URL = (
    "https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"
)
WIKIDATA_OFFICIAL_WEBSITE = "P856"
WIKIDATA_COORDINATE_LOCATION = "P625"
WIKIDATA_OSM_RELATION_ID = "P402"

WIKIDATA_CONFIDENCE = 0.85


def wikidata_entity_url(wikidata_id: str) -> str:
    return WIKIDATA_ENTITY_URL.format(wikidata_id=wikidata_id)


def extract_wikidata_candidates(
    *,
    resort_id: str,
    wikidata_id: str,
    payload: dict[str, Any],
    fetched_at: datetime,
    source_url: str,
    resort_payload: dict[str, Any],
) -> list[CandidateFact]:
    claims = _entity_claims(payload, wikidata_id)
    if claims is None:
        return []

    source = SourceReference(source_type="wikidata", source_url=source_url)
    candidates: list[CandidateFact] = []

    official_url = _string_claim_value(claims, WIKIDATA_OFFICIAL_WEBSITE)
    if official_url is not None:
        candidates.append(
            _candidate(
                resort_id=resort_id,
                target=ProposalTarget(
                    entity_type="destination",
                    entity_id=resort_id,
                ),
                field_path="ski_area_official_url",
                proposed_value=official_url,
                source=source,
                fetched_at=fetched_at,
                evidence=(
                    f"Wikidata {WIKIDATA_OFFICIAL_WEBSITE} official website="
                    f"{official_url}"
                ),
            )
        )

    osm_relation_id = _string_or_int_claim_value(claims, WIKIDATA_OSM_RELATION_ID)
    if osm_relation_id is not None:
        candidates.append(
            _candidate(
                resort_id=resort_id,
                target=ProposalTarget(
                    entity_type="destination",
                    entity_id=resort_id,
                ),
                field_path="regional_data_ids.osm_relation_id",
                proposed_value=osm_relation_id,
                source=source,
                fetched_at=fetched_at,
                evidence=(
                    f"Wikidata {WIKIDATA_OSM_RELATION_ID} OSM relation ID="
                    f"{osm_relation_id}"
                ),
            )
        )

    coordinates = _coordinate_claim_value(claims, WIKIDATA_COORDINATE_LOCATION)
    if coordinates is not None:
        latitude, longitude = coordinates
        evidence = (
            f"Wikidata {WIKIDATA_COORDINATE_LOCATION} coordinate location "
            f"latitude={latitude}, longitude={longitude}"
        )
        candidates.extend(
            _coordinate_candidates(
                resort_id=resort_id,
                resort_payload=resort_payload,
                latitude=latitude,
                longitude=longitude,
                source=source,
                fetched_at=fetched_at,
                evidence=evidence,
            )
        )

    return candidates


def _entity_claims(
    payload: dict[str, Any],
    wikidata_id: str,
) -> dict[str, Any] | None:
    entities = payload.get("entities")
    if not isinstance(entities, dict):
        return None
    entity = entities.get(wikidata_id)
    if not isinstance(entity, dict):
        return None
    claims = entity.get("claims")
    return claims if isinstance(claims, dict) else None


def _string_claim_value(claims: dict[str, Any], property_id: str) -> str | None:
    for values in _ranked_claim_values(claims, property_id):
        for value in values:
            if not isinstance(value, str):
                continue
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _string_or_int_claim_value(claims: dict[str, Any], property_id: str) -> str | None:
    for values in _ranked_claim_values(claims, property_id):
        for value in values:
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return str(value)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
    return None


def _coordinate_claim_value(
    claims: dict[str, Any],
    property_id: str,
) -> tuple[float, float] | None:
    for values in _ranked_claim_values(claims, property_id):
        for value in values:
            if not isinstance(value, dict):
                continue
            latitude = _coordinate_component(
                value.get("latitude"),
                min_value=-90,
                max_value=90,
            )
            longitude = _coordinate_component(
                value.get("longitude"),
                min_value=-180,
                max_value=180,
            )
            if latitude is not None and longitude is not None:
                return latitude, longitude
    return None


def _ranked_claim_values(
    claims: dict[str, Any],
    property_id: str,
) -> tuple[list[Any], list[Any]]:
    property_claims = claims.get(property_id)
    if not isinstance(property_claims, list):
        return [], []
    preferred_values: list[Any] = []
    fallback_values: list[Any] = []
    for claim in property_claims:
        if not isinstance(claim, dict) or claim.get("rank") == "deprecated":
            continue
        value = _claim_datavalue_value(claim)
        if value is None:
            continue
        if claim.get("rank") == "preferred":
            preferred_values.append(value)
        else:
            fallback_values.append(value)
    return preferred_values, fallback_values


def _claim_datavalue_value(claim: dict[str, Any]) -> Any | None:
    mainsnak = claim.get("mainsnak")
    if not isinstance(mainsnak, dict):
        return None
    datavalue = mainsnak.get("datavalue")
    if not isinstance(datavalue, dict):
        return None
    return datavalue.get("value")


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
    proposed_value: str | float,
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
        extraction_method="wikidata",
        fetched_at=fetched_at,
        confidence=WIKIDATA_CONFIDENCE,
        evidence=evidence,
    )
