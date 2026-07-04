from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

VERSION_1_GROUPS: dict[str, tuple[str, ...]] = {
    "ski_regions": ("identity", "membership_context"),
    "stay_destinations": (
        "identity_location",
        "coordinates",
        "price_level_atmosphere",
    ),
    "stay_bases": (
        "identity_ownership",
        "coordinates",
        "lodging_price_quality",
        "atmosphere",
    ),
    "ski_areas": (
        "identity_coordinates",
        "elevation_season",
        "terrain_metrics",
        "skill_fit",
    ),
    "ski_area_access": ("relationship", "access_mode_distance"),
    "terrain_domains": (
        "membership_connectivity",
        "aggregate_terrain",
        "season",
    ),
    "lift_pass_products": (
        "identity_scope_availability",
        "coverage",
        "prices",
        "pass_accessible_terrain",
    ),
    "rental_display_facts": ("identity_ownership", "price_quality_access"),
}

VERSION_2_GROUPS: dict[str, tuple[str, ...]] = {
    **VERSION_1_GROUPS,
    "stay_destinations": ("identity_location", "coordinates", "price_level"),
    "stay_bases": (
        "identity_ownership",
        "coordinates",
        "elevation",
        "lodging_price_quality",
        "base_type",
        "base_character",
        "local_apres",
    ),
    "ski_areas": VERSION_1_GROUPS["ski_areas"]
    + (
        "snowmaking",
        "glacier_terrain",
        "snow_park",
        "night_skiing",
        "marked_freeride_routes",
        "ski_day_apres",
        "official_documents",
    ),
    "terrain_domains": VERSION_1_GROUPS["terrain_domains"] + ("official_documents",),
}

_VERSION_2_LEGACY_GROUP: dict[str, dict[str, str]] = {
    entity_type: {group: group for group in groups}
    for entity_type, groups in VERSION_1_GROUPS.items()
}
_VERSION_2_LEGACY_GROUP["stay_destinations"] = {
    "identity_location": "identity_location",
    "coordinates": "coordinates",
    "price_level": "price_level_atmosphere",
}
_VERSION_2_LEGACY_GROUP["stay_bases"].pop("atmosphere")

_BASE_TYPE_MAPPING = {
    "town": "town",
    "village": "village",
    "traditional_village": "village",
    "lake_village": "village",
    "hamlet": "hamlet",
    "neighbourhood": "neighbourhood",
    "resort_station": "resort_station",
    "planned_village": "resort_station",
    "resort_centre": "resort_sector",
    "high_altitude_sector": "resort_sector",
    "village_sector": "resort_sector",
}

_UNKNOWN_BASE_CHARACTER = {
    "development_style": "unknown",
    "local_pace": "unknown",
}
_UNKNOWN_APRES = {
    "availability": "unknown",
    "intensity": None,
    "season_label": None,
}
_UNKNOWN_SNOWMAKING = {
    "availability": "unknown",
    "coverage_pct": None,
    "coverage_basis": "unknown",
    "season_label": None,
}
_UNKNOWN_AVAILABILITY = {"availability": "unknown"}
_UNKNOWN_SNOW_PARK = {
    "availability": "unknown",
    "park_count": None,
    "season_label": None,
}
_UNKNOWN_SEASONAL_FEATURE = {
    "availability": "unknown",
    "season_label": None,
}
_UNKNOWN_FREERIDE = {
    "availability": "unknown",
    "route_count": None,
    "season_label": None,
}


class _MigrationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RetiredAtmosphereTags(_MigrationModel):
    target_type: Literal["stay_destination", "stay_base"]
    target_id: str
    field_path: Literal["atmosphere_tags"] = "atmosphere_tags"
    values: tuple[str, ...]


class BaseTypeNormalization(_MigrationModel):
    stay_base_id: str
    before: str
    after: str


class CatalogV2MigrationAudit(_MigrationModel):
    retired_atmosphere_tags: tuple[RetiredAtmosphereTags, ...]
    base_type_normalizations: tuple[BaseTypeNormalization, ...]


class CatalogV2MigrationReport(_MigrationModel):
    from_schema_version: Literal[1] = 1
    to_schema_version: Literal[2] = 2
    catalog_before_sha256: str
    catalog_after_sha256: str
    trust_before_sha256: str
    trust_after_sha256: str
    retired_atmosphere_tags: tuple[RetiredAtmosphereTags, ...]
    base_type_normalizations: tuple[BaseTypeNormalization, ...]


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return value


def _require_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array")
    return value


def migrate_catalog_payload(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], CatalogV2MigrationAudit]:
    if payload.get("schema_version") != 1:
        raise ValueError("expected catalog schema version 1")

    migrated = deepcopy(dict(payload))
    retired_tags: list[RetiredAtmosphereTags] = []
    base_type_normalizations: list[BaseTypeNormalization] = []

    for destination in _require_list(migrated, "stay_destinations"):
        if not isinstance(destination, dict):
            raise ValueError("stay_destinations entries must be objects")
        tags = destination.pop("atmosphere_tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("stay destination atmosphere_tags must be strings")
        if tags:
            retired_tags.append(
                RetiredAtmosphereTags(
                    target_type="stay_destination",
                    target_id=str(destination.get("stay_destination_id", "")),
                    values=tuple(tags),
                )
            )

    for stay_base in _require_list(migrated, "stay_bases"):
        if not isinstance(stay_base, dict):
            raise ValueError("stay_bases entries must be objects")
        tags = stay_base.pop("atmosphere_tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("stay base atmosphere_tags must be strings")
        if tags:
            retired_tags.append(
                RetiredAtmosphereTags(
                    target_type="stay_base",
                    target_id=str(stay_base.get("stay_base_id", "")),
                    values=tuple(tags),
                )
            )

        legacy_base_type = stay_base.get("base_type")
        if legacy_base_type is not None:
            normalized = _BASE_TYPE_MAPPING.get(legacy_base_type)
            if normalized is None:
                raise ValueError(f"unknown legacy base_type: {legacy_base_type!r}")
            stay_base["base_type"] = normalized
            if normalized != legacy_base_type:
                base_type_normalizations.append(
                    BaseTypeNormalization(
                        stay_base_id=str(stay_base.get("stay_base_id", "")),
                        before=legacy_base_type,
                        after=normalized,
                    )
                )
        stay_base["elevation_m"] = None
        stay_base["base_character"] = deepcopy(_UNKNOWN_BASE_CHARACTER)
        stay_base["local_apres_profile"] = deepcopy(_UNKNOWN_APRES)

    for ski_area in _require_list(migrated, "ski_areas"):
        if not isinstance(ski_area, dict):
            raise ValueError("ski_areas entries must be objects")
        ski_area["snowmaking"] = deepcopy(_UNKNOWN_SNOWMAKING)
        ski_area["glacier_terrain"] = deepcopy(_UNKNOWN_AVAILABILITY)
        ski_area["snow_park"] = deepcopy(_UNKNOWN_SNOW_PARK)
        ski_area["night_skiing"] = deepcopy(_UNKNOWN_SEASONAL_FEATURE)
        ski_area["marked_freeride_routes"] = deepcopy(_UNKNOWN_FREERIDE)
        ski_area["official_trail_map"] = None
        ski_area["ski_day_apres_profile"] = deepcopy(_UNKNOWN_APRES)

    for terrain_domain in _require_list(migrated, "terrain_domains"):
        if not isinstance(terrain_domain, dict):
            raise ValueError("terrain_domains entries must be objects")
        terrain_domain["official_trail_map"] = None

    migrated["schema_version"] = 2
    return migrated, CatalogV2MigrationAudit(
        retired_atmosphere_tags=tuple(retired_tags),
        base_type_normalizations=tuple(base_type_normalizations),
    )


def _migrate_trust_entry(
    entry: Mapping[str, Any],
    *,
    entity_type: str,
) -> dict[str, Any]:
    allowed_keys = {"display_name", "field_statuses", "source_refs", "notes"}
    unexpected_keys = set(entry) - allowed_keys
    if unexpected_keys:
        raise ValueError(
            f"{entity_type} trust entry has unexpected keys: "
            + ", ".join(sorted(unexpected_keys))
        )
    legacy_statuses = _require_mapping(entry, "field_statuses")
    expected_legacy_groups = set(VERSION_1_GROUPS[entity_type])
    if set(legacy_statuses) != expected_legacy_groups:
        raise ValueError(f"{entity_type} field_statuses do not match version 1")
    legacy_source_refs = entry.get("source_refs")
    if not isinstance(legacy_source_refs, list) or not all(
        isinstance(source_ref, str) for source_ref in legacy_source_refs
    ):
        raise ValueError(f"{entity_type} source_refs must be an array of strings")

    group_mappings = _VERSION_2_LEGACY_GROUP[entity_type]
    field_statuses: dict[str, Any] = {}
    field_source_refs: dict[str, list[str]] = {}
    for group in VERSION_2_GROUPS[entity_type]:
        legacy_group = group_mappings.get(group)
        if legacy_group is None:
            field_statuses[group] = "needs_source"
            field_source_refs[group] = []
        else:
            field_statuses[group] = legacy_statuses[legacy_group]
            field_source_refs[group] = list(legacy_source_refs)

    return {
        "display_name": entry.get("display_name"),
        "field_statuses": field_statuses,
        "field_source_refs": field_source_refs,
        "notes": deepcopy(entry.get("notes", [])),
    }


def migrate_trust_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("catalog_schema_version") != 1:
        raise ValueError("expected trust catalog schema version 1")
    legacy_field_groups = _require_mapping(payload, "field_groups")
    if {
        entity_type: tuple(groups) if isinstance(groups, list) else groups
        for entity_type, groups in legacy_field_groups.items()
    } != VERSION_1_GROUPS:
        raise ValueError("trust field_groups do not match version 1")
    legacy_entities = _require_mapping(payload, "entities")
    if set(legacy_entities) != set(VERSION_1_GROUPS):
        raise ValueError("trust entities namespaces do not match version 1")

    entities: dict[str, dict[str, Any]] = {}
    for entity_type in VERSION_1_GROUPS:
        entries = _require_mapping(legacy_entities, entity_type)
        entities[entity_type] = {
            entity_id: _migrate_trust_entry(entry, entity_type=entity_type)
            for entity_id, entry in entries.items()
            if isinstance(entry, Mapping)
        }
        if len(entities[entity_type]) != len(entries):
            raise ValueError(f"{entity_type} trust entries must be objects")

    return {
        "version": "2026-07-04",
        "catalog_schema_version": 2,
        "status_values": deepcopy(payload.get("status_values")),
        "field_groups": {
            entity_type: list(groups)
            for entity_type, groups in VERSION_2_GROUPS.items()
        },
        "entities": entities,
    }


def payload_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_migration_report(
    *,
    before_catalog: Mapping[str, Any],
    after_catalog: Mapping[str, Any],
    before_trust: Mapping[str, Any],
    after_trust: Mapping[str, Any],
    audit: CatalogV2MigrationAudit,
) -> CatalogV2MigrationReport:
    return CatalogV2MigrationReport(
        catalog_before_sha256=payload_sha256(before_catalog),
        catalog_after_sha256=payload_sha256(after_catalog),
        trust_before_sha256=payload_sha256(before_trust),
        trust_after_sha256=payload_sha256(after_trust),
        retired_atmosphere_tags=audit.retired_atmosphere_tags,
        base_type_normalizations=audit.base_type_normalizations,
    )


def reconcile_migration_report(
    report: CatalogV2MigrationReport,
    *,
    before_catalog: Mapping[str, Any],
    after_catalog: Mapping[str, Any],
    before_trust: Mapping[str, Any],
    after_trust: Mapping[str, Any],
) -> None:
    hash_checks = (
        ("catalog before hash", report.catalog_before_sha256, before_catalog),
        ("catalog after hash", report.catalog_after_sha256, after_catalog),
        ("trust before hash", report.trust_before_sha256, before_trust),
        ("trust after hash", report.trust_after_sha256, after_trust),
    )
    for label, expected_hash, payload in hash_checks:
        if payload_sha256(payload) != expected_hash:
            raise ValueError(f"{label} does not match migration report")

    expected_catalog, expected_audit = migrate_catalog_payload(before_catalog)
    expected_trust = migrate_trust_payload(before_trust)
    if expected_catalog != after_catalog:
        raise ValueError("catalog output does not match deterministic migration")
    if expected_trust != after_trust:
        raise ValueError("trust output does not match deterministic migration")
    expected_report = build_migration_report(
        before_catalog=before_catalog,
        after_catalog=after_catalog,
        before_trust=before_trust,
        after_trust=after_trust,
        audit=expected_audit,
    )
    if report != expected_report:
        raise ValueError("migration report does not match deterministic migration")
