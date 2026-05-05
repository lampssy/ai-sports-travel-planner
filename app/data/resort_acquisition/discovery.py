from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.data.resort_acquisition.models import (
    CandidateFact,
    SourceReference,
    SourceRegistry,
)

OPENDATAHUB_SKI_AREA_INDEX_URL = (
    "https://tourism.api.opendatahub.com/v1/SkiArea"
    "?language=en&fields=Id,Detail.en.Title,Shortname,Latitude,Longitude,"
    "TotalSlopeKm,LicenseInfo&pagesize=500"
)
OPENDATAHUB_DISCOVERY_RESORT_ID = "opendatahub-discovery"

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_SKI_AREA_SUFFIX_RE = re.compile(r"\b(?:ski\s*area|skiarea)\s*$")


@dataclass(frozen=True)
class OpenDataHubSkiAreaMatch:
    ski_area_id: str
    title: str
    license_name: str | None
    latitude: float | None
    longitude: float | None
    total_slope_km: str | int | float | None


def normalize_ski_area_name(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    lowered = ascii_value.lower().strip()
    without_suffix = _SKI_AREA_SUFFIX_RE.sub("", lowered).strip()
    return _NON_ALNUM_RE.sub(" ", without_suffix).strip()


def discover_opendatahub_id_candidates(
    *,
    raw_catalog_by_resort: dict[str, dict[str, Any]],
    selected_resorts: list[str],
    registry: SourceRegistry,
    payload: Any,
    fetched_at: datetime,
    source_url: str,
) -> list[CandidateFact]:
    matches_by_name = _open_match_index(payload)
    candidates: list[CandidateFact] = []

    for resort_id in selected_resorts:
        resort_payload = raw_catalog_by_resort.get(resort_id)
        if resort_payload is None:
            continue

        matches_by_id: dict[str, OpenDataHubSkiAreaMatch] = {}
        for name in _catalog_match_names(resort_payload):
            normalized_name = normalize_ski_area_name(name)
            if not normalized_name:
                continue
            for match in matches_by_name.get(normalized_name, []):
                matches_by_id[match.ski_area_id] = match

        if len(matches_by_id) != 1:
            continue

        match = next(iter(matches_by_id.values()))
        configured_id = (
            registry.resorts.get(resort_id).regional_data_ids.opendatahub_ski_area_id
            if resort_id in registry.resorts
            else None
        )
        if configured_id == match.ski_area_id:
            continue

        catalog_name = _catalog_display_name(resort_payload)
        evidence = (
            f"Matched catalog name '{catalog_name}' to OpenDataHub title "
            f"'{match.title}'; Id={match.ski_area_id}; "
            f"License={match.license_name or 'unknown'}; ClosedData=false"
        )
        if configured_id is not None:
            evidence = f"{evidence}; configured OpenDataHub ID={configured_id}"

        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                field_path="regional_data_ids.opendatahub_ski_area_id",
                proposed_value=match.ski_area_id,
                source=SourceReference(
                    source_type="opendatahub",
                    source_url=source_url,
                    license=match.license_name,
                ),
                extraction_method="opendatahub_discovery",
                fetched_at=fetched_at,
                confidence=0.9,
                evidence=evidence,
            )
        )

    return candidates


def _open_match_index(payload: Any) -> dict[str, list[OpenDataHubSkiAreaMatch]]:
    records = _payload_records(payload)
    matches_by_name: dict[str, list[OpenDataHubSkiAreaMatch]] = defaultdict(list)
    for record in records:
        match = _open_match(record)
        if match is None:
            continue
        normalized_title = normalize_ski_area_name(match.title)
        if normalized_title:
            matches_by_name[normalized_title].append(match)
    return matches_by_name


def _payload_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("Items"), list):
        return [record for record in payload["Items"] if isinstance(record, dict)]
    return []


def _open_match(record: dict[str, Any]) -> OpenDataHubSkiAreaMatch | None:
    license_info = record.get("LicenseInfo")
    if (
        not isinstance(license_info, dict)
        or license_info.get("ClosedData") is not False
    ):
        return None

    ski_area_id = record.get("Id")
    title = _record_title(record)
    if not isinstance(ski_area_id, str) or not ski_area_id.strip() or title is None:
        return None

    license_name = license_info.get("License")
    return OpenDataHubSkiAreaMatch(
        ski_area_id=ski_area_id,
        title=title,
        license_name=license_name if isinstance(license_name, str) else None,
        latitude=_optional_float(record.get("Latitude")),
        longitude=_optional_float(record.get("Longitude")),
        total_slope_km=_optional_scalar(record.get("TotalSlopeKm")),
    )


def _record_title(record: dict[str, Any]) -> str | None:
    flattened_title = record.get("Detail.en.Title")
    if isinstance(flattened_title, str) and flattened_title.strip():
        return flattened_title

    detail = record.get("Detail")
    if not isinstance(detail, dict):
        return None
    english_detail = detail.get("en")
    if not isinstance(english_detail, dict):
        return None
    title = english_detail.get("Title")
    if isinstance(title, str) and title.strip():
        return title
    return None


def _catalog_match_names(resort_payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    if isinstance(resort_payload.get("name"), str):
        names.append(resort_payload["name"])

    aliases = resort_payload.get("aliases")
    if isinstance(aliases, list):
        names.extend(alias for alias in aliases if isinstance(alias, str))

    ski_areas = resort_payload.get("ski_areas")
    if isinstance(ski_areas, list):
        for ski_area in ski_areas:
            if isinstance(ski_area, dict) and isinstance(ski_area.get("name"), str):
                names.append(ski_area["name"])

    return names


def _catalog_display_name(resort_payload: dict[str, Any]) -> str:
    name = resort_payload.get("name")
    return name if isinstance(name, str) and name.strip() else "(unknown)"


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_scalar(value: Any) -> str | int | float | None:
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        return value
    return None
