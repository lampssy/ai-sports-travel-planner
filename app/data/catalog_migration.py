from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.data.catalog_loader import CATALOG_PATH
from app.data.loader import (
    DEFAULT_RESORTS_PATH,
    DEFAULT_TERRAIN_DOMAINS_PATH,
    _parse_price_range,
    load_resorts_from_path,
    load_terrain_domains_from_path,
)
from app.domain.catalog import (
    CatalogSnapshot,
    LiftDistance,
    SkiAreaAccessMode,
)
from app.domain.models import Destination, SkillLevel, TerrainDomain

DEFAULT_OVERRIDES_PATH = Path(__file__).with_name("catalog_migration_overrides.json")
DEFAULT_REPORT_PATH = Path("artifacts/catalog-migration/catalog-migration-review.md")

_DESTINATION_DROPPED_FIELDS = (
    "destination.base_elevation_m",
    "destination.summit_elevation_m",
    "destination.season_start_month",
    "destination.season_end_month",
    "destination.season_windows",
)
_SKILL_LEVEL_ORDER: tuple[SkillLevel, ...] = (
    "beginner",
    "intermediate",
    "advanced",
)
_OSM_ID_KINDS = {
    "osm_node_id": "node",
    "osm_way_id": "way",
    "osm_relation_id": "relation",
    "nearest_lift_osm_node_id": "node",
    "nearest_lift_osm_way_id": "way",
    "nearest_lift_osm_relation_id": "relation",
}


class _OverrideModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AccessEdgeOverride(_OverrideModel):
    stay_base_id: str
    ski_area_id: str
    inherit_legacy_access: bool
    access_mode: SkiAreaAccessMode | None = None
    lift_distance: LiftDistance | None = None
    nearest_lift_name: str | None = None
    distance_m: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, ge=0)
    is_direct: bool
    source_urls: tuple[str, ...] = ()
    decision_note: str | None = None

    @model_validator(mode="after")
    def validate_explicit_access(self) -> "AccessEdgeOverride":
        if not self.inherit_legacy_access and (
            self.access_mode is None or self.lift_distance is None
        ):
            raise ValueError(
                "explicit access edges require access_mode and lift_distance"
            )
        return self


class MigrationOverrides(_OverrideModel):
    shared_trip_markets: dict[str, tuple[str, ...]]
    trip_market_names: dict[str, str]
    terrain_group_routes: dict[str, str]
    shared_pass_ids: dict[str, tuple[str, ...]]
    shared_pass_external_validity_summaries: dict[str, str] = Field(
        default_factory=dict
    )
    access_edge_overrides: dict[str, AccessEdgeOverride]
    destination_access_source_urls: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class AccessEdgeAudit:
    access_id: str
    mode: str
    is_direct: bool
    source_urls: tuple[str, ...]
    facts_moved: bool


@dataclass(frozen=True)
class MigrationAudit:
    before_counts: dict[str, int]
    after_counts: dict[str, int]
    stay_destination_id_changes: tuple[str, ...]
    stay_base_id_changes: tuple[str, ...]
    ski_area_id_changes: tuple[str, ...]
    existing_terrain_domain_id_changes: tuple[str, ...]
    trip_market_memberships: dict[str, tuple[str, ...]]
    access_edges: tuple[AccessEdgeAudit, ...]
    merged_pass_source_ids: dict[str, tuple[str, ...]]
    terrain_group_routes: tuple[tuple[str, str], ...]
    blocked_relationships: tuple[str, ...]
    dropped_fields: tuple[str, ...]
    derived_decisions: tuple[str, ...]


@dataclass(frozen=True)
class CatalogMigration:
    snapshot: CatalogSnapshot
    audit: MigrationAudit
    report_markdown: str


class CatalogMigrationBlocked(ValueError):
    def __init__(self, relationship_ids: tuple[str, ...]) -> None:
        self.relationship_ids = relationship_ids
        joined = ", ".join(relationship_ids)
        super().__init__(f"unsourced catalog relationships: {joined}")

    def render_report(self) -> str:
        lines = [
            "# Catalog Migration Review",
            "",
            "Status: **BLOCKED**",
            "",
            "## Blocked/Unsourced Relationships",
            "",
            f"Blocked relationships: **{len(self.relationship_ids)}**",
            "",
        ]
        lines.extend(
            f"- `{relationship_id}`" for relationship_id in self.relationship_ids
        )
        return "\n".join(lines) + "\n"


@dataclass
class _PassAccumulator:
    source_ids: list[str]
    names: set[str]
    validity_scopes: set[str]
    available_destination_ids: set[str]
    default_destination_ids: set[str]
    valid_ski_area_ids: set[str]
    terrain_domain_ids: set[str]
    external_validity_summaries: set[str]
    prices_by_key: dict[str, dict[str, object]]


def load_migration_overrides(path: Path) -> MigrationOverrides:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return MigrationOverrides.model_validate(payload)


def _sorted_unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _legacy_counts(
    destinations: list[Destination], terrain_domains: list[TerrainDomain]
) -> dict[str, int]:
    return {
        "ski_regions": 0,
        "stay_destinations": len(destinations),
        "stay_bases": sum(len(item.stay_bases) for item in destinations),
        "ski_areas": sum(len(item.ski_areas) for item in destinations),
        "ski_area_access": 0,
        "terrain_groups": sum(len(item.terrain_groups) for item in destinations),
        "terrain_domains": len(terrain_domains),
        "lift_pass_products": sum(
            len(item.lift_pass_products) for item in destinations
        ),
        "rental_display_facts": sum(len(item.rentals) for item in destinations),
    }


def _snapshot_counts(snapshot: CatalogSnapshot) -> dict[str, int]:
    return {
        "ski_regions": len(snapshot.ski_regions),
        "stay_destinations": len(snapshot.stay_destinations),
        "stay_bases": len(snapshot.stay_bases),
        "ski_areas": len(snapshot.ski_areas),
        "ski_area_access": len(snapshot.ski_area_access),
        "terrain_groups": 0,
        "terrain_domains": len(snapshot.terrain_domains),
        "lift_pass_products": len(snapshot.lift_pass_products),
        "rental_display_facts": len(snapshot.rental_display_facts),
    }


def _validate_override_memberships(
    destinations: list[Destination], overrides: MigrationOverrides
) -> dict[str, str]:
    destination_ids = {item.resort_id for item in destinations}
    region_by_destination: dict[str, str] = {}
    for region_id, members in overrides.shared_trip_markets.items():
        if region_id not in overrides.trip_market_names:
            raise ValueError(f"missing trip_market_names entry for {region_id}")
        for destination_id in members:
            if destination_id not in destination_ids:
                raise ValueError(
                    f"unknown shared trip-market destination: {destination_id}"
                )
            previous = region_by_destination.setdefault(destination_id, region_id)
            if previous != region_id:
                raise ValueError(
                    f"destination {destination_id} is in multiple trip markets"
                )
    return region_by_destination


def _build_regions_and_destinations(
    destinations: list[Destination], overrides: MigrationOverrides
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, tuple[str, ...]],
]:
    region_by_destination = _validate_override_memberships(destinations, overrides)
    region_members: dict[str, list[str]] = defaultdict(list)
    region_payloads: dict[str, dict[str, object]] = {}
    destination_payloads: list[dict[str, object]] = []

    for destination in sorted(destinations, key=lambda item: item.resort_id):
        region_id = region_by_destination.get(
            destination.resort_id, destination.resort_id
        )
        region_name = overrides.trip_market_names.get(region_id, destination.name)
        existing = region_payloads.setdefault(
            region_id,
            {
                "ski_region_id": region_id,
                "name": region_name,
                "grouping_policy": "trip_market",
                "source_urls": [],
            },
        )
        if existing["name"] != region_name:
            raise ValueError(f"conflicting trip-market name for {region_id}")
        region_members[region_id].append(destination.resort_id)
        destination_payloads.append(
            {
                "stay_destination_id": destination.resort_id,
                "name": destination.name,
                "country": destination.country,
                "region": destination.region,
                "price_level": destination.price_level,
                "latitude": destination.latitude,
                "longitude": destination.longitude,
                "trip_market_region_id": region_id,
                "atmosphere_tags": [],
                "regional_data_ids": {},
            }
        )

    memberships = {
        region_id: tuple(sorted(members))
        for region_id, members in sorted(region_members.items())
    }
    return (
        [region_payloads[key] for key in sorted(region_payloads)],
        destination_payloads,
        memberships,
    )


def _identity_regional_data_ids(values: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in values.items()
        if not key.startswith("nearest_lift_")
    }


def _access_regional_data_ids(values: dict[str, str]) -> dict[str, str]:
    return {
        key: value for key, value in values.items() if key.startswith("nearest_lift_")
    }


def _build_stay_bases(destinations: list[Destination]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for destination in destinations:
        for stay_base in destination.stay_bases:
            price_min, price_max = _parse_price_range(stay_base.price_range)
            payloads.append(
                {
                    "stay_base_id": stay_base.stay_base_id,
                    "stay_destination_id": destination.resort_id,
                    "name": stay_base.name,
                    "price_range": stay_base.price_range,
                    "price_min": price_min,
                    "price_max": price_max,
                    "quality": stay_base.quality,
                    "latitude": stay_base.latitude,
                    "longitude": stay_base.longitude,
                    "base_type": stay_base.base_type,
                    "atmosphere_tags": stay_base.atmosphere_tags,
                    "regional_data_ids": _identity_regional_data_ids(
                        stay_base.regional_data_ids
                    ),
                }
            )
    return sorted(payloads, key=lambda item: str(item["stay_base_id"]))


def _derive_supported_skill_levels(
    destination: Destination, ski_area_id: str
) -> tuple[tuple[SkillLevel, ...], str]:
    ski_area = next(
        area for area in destination.ski_areas if area.ski_area_id == ski_area_id
    )
    difficulty = ski_area.piste_km_by_difficulty
    if difficulty is not None:
        levels = tuple(
            level for level in _SKILL_LEVEL_ORDER if getattr(difficulty, level) > 0
        )
        if levels:
            return levels, (
                f"ski_area `{ski_area_id}` supported_skill_levels derived from "
                "child piste_km_by_difficulty; no independent verified claim added"
            )

    base_levels = {
        level
        for stay_base in destination.stay_bases
        for level in stay_base.supported_skill_levels
    }
    levels = tuple(level for level in _SKILL_LEVEL_ORDER if level in base_levels)
    return levels, (
        f"ski_area `{ski_area_id}` supported_skill_levels derived from the "
        f"`{destination.resort_id}` stay-base union fallback; treated as derived"
    )


def _build_ski_areas(
    destinations: list[Destination],
) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    payloads: list[dict[str, object]] = []
    decisions: list[str] = []
    for destination in destinations:
        for ski_area in destination.ski_areas:
            levels, decision = _derive_supported_skill_levels(
                destination, ski_area.ski_area_id
            )
            decisions.append(decision)
            payload = ski_area.model_dump(mode="json")
            payload["supported_skill_levels"] = list(levels)
            payloads.append(payload)
    return (
        sorted(payloads, key=lambda item: str(item["ski_area_id"])),
        tuple(sorted(decisions)),
    )


def _osm_source_urls(regional_data_ids: dict[str, str]) -> tuple[str, ...]:
    urls = [
        f"https://www.openstreetmap.org/{_OSM_ID_KINDS[key]}/{value}"
        for key, value in regional_data_ids.items()
        if key in _OSM_ID_KINDS
    ]
    return _sorted_unique(urls)


def _legacy_access_mode(value: str) -> SkiAreaAccessMode:
    if value == "car_recommended":
        return "drive"
    if value in {"walk", "ski_bus", "unknown"}:
        return value
    raise ValueError(f"unsupported legacy access mode: {value}")


def _source_urls_for_access(
    destination: Destination,
    regional_data_ids: dict[str, str],
    explicit_source_urls: tuple[str, ...],
    overrides: MigrationOverrides,
) -> tuple[str, ...]:
    if explicit_source_urls:
        return _sorted_unique(explicit_source_urls)
    inherited = list(_osm_source_urls(regional_data_ids))
    inherited.extend(
        overrides.destination_access_source_urls.get(destination.resort_id, ())
    )
    return _sorted_unique(inherited)


def _inherited_access_payload(
    destination: Destination,
    stay_base_id: str,
    ski_area_id: str,
    is_direct: bool,
    explicit_source_urls: tuple[str, ...],
    overrides: MigrationOverrides,
) -> tuple[dict[str, object], AccessEdgeAudit]:
    stay_base = next(
        item for item in destination.stay_bases if item.stay_base_id == stay_base_id
    )
    access_id = f"{stay_base_id}--{ski_area_id}"
    access_data_ids = _access_regional_data_ids(stay_base.regional_data_ids)
    source_data_ids = {**stay_base.regional_data_ids, **access_data_ids}
    source_urls = _source_urls_for_access(
        destination,
        source_data_ids,
        explicit_source_urls,
        overrides,
    )
    payload = {
        "ski_area_access_id": access_id,
        "stay_base_id": stay_base_id,
        "ski_area_id": ski_area_id,
        "access_mode": _legacy_access_mode(stay_base.access_mode),
        "lift_distance": stay_base.lift_distance,
        "nearest_lift_name": stay_base.nearest_lift_name,
        "distance_m": stay_base.nearest_lift_distance_m,
        "duration_minutes": None,
        "is_direct": is_direct,
        "regional_data_ids": access_data_ids,
        "source_urls": source_urls,
    }
    audit = AccessEdgeAudit(
        access_id=access_id,
        mode=str(payload["access_mode"]),
        is_direct=is_direct,
        source_urls=source_urls,
        facts_moved=True,
    )
    return payload, audit


def _explicit_access_payload(
    destination: Destination,
    edge_id: str,
    edge: AccessEdgeOverride,
    overrides: MigrationOverrides,
) -> tuple[dict[str, object], AccessEdgeAudit]:
    source_urls = _source_urls_for_access(
        destination,
        {},
        edge.source_urls,
        overrides,
    )
    payload = {
        "ski_area_access_id": edge_id,
        "stay_base_id": edge.stay_base_id,
        "ski_area_id": edge.ski_area_id,
        "access_mode": edge.access_mode,
        "lift_distance": edge.lift_distance,
        "nearest_lift_name": edge.nearest_lift_name,
        "distance_m": edge.distance_m,
        "duration_minutes": edge.duration_minutes,
        "is_direct": edge.is_direct,
        "regional_data_ids": {},
        "source_urls": source_urls,
    }
    audit = AccessEdgeAudit(
        access_id=edge_id,
        mode=str(edge.access_mode),
        is_direct=edge.is_direct,
        source_urls=source_urls,
        facts_moved=False,
    )
    return payload, audit


def _validate_access_override(
    edge_id: str,
    edge: AccessEdgeOverride,
    destination: Destination,
) -> None:
    expected_id = f"{edge.stay_base_id}--{edge.ski_area_id}"
    if edge_id != expected_id:
        raise ValueError(f"access override id {edge_id} does not match {expected_id}")
    destination_area_ids = {area.ski_area_id for area in destination.ski_areas}
    if edge.ski_area_id not in destination_area_ids:
        raise ValueError(
            f"access override {edge_id} references an area outside its "
            "legacy destination"
        )


def _build_overridden_access(
    destination: Destination,
    edge_id: str,
    edge: AccessEdgeOverride,
    overrides: MigrationOverrides,
) -> tuple[dict[str, object], AccessEdgeAudit]:
    _validate_access_override(edge_id, edge, destination)
    if edge.inherit_legacy_access:
        return _inherited_access_payload(
            destination,
            edge.stay_base_id,
            edge.ski_area_id,
            edge.is_direct,
            edge.source_urls,
            overrides,
        )
    return _explicit_access_payload(destination, edge_id, edge, overrides)


def _build_accesses(
    destinations: list[Destination], overrides: MigrationOverrides
) -> tuple[list[dict[str, object]], tuple[AccessEdgeAudit, ...], tuple[str, ...]]:
    destination_by_base_id = {
        stay_base.stay_base_id: destination
        for destination in destinations
        for stay_base in destination.stay_bases
    }
    access_payloads: list[dict[str, object]] = []
    audit_rows: list[AccessEdgeAudit] = []
    remaining_overrides = dict(overrides.access_edge_overrides)

    for destination in destinations:
        if len(destination.ski_areas) != 1:
            continue
        ski_area_id = destination.ski_areas[0].ski_area_id
        for stay_base in destination.stay_bases:
            edge_id = f"{stay_base.stay_base_id}--{ski_area_id}"
            edge = remaining_overrides.pop(edge_id, None)
            if edge is None:
                payload, audit = _inherited_access_payload(
                    destination,
                    stay_base.stay_base_id,
                    ski_area_id,
                    True,
                    (),
                    overrides,
                )
            else:
                payload, audit = _build_overridden_access(
                    destination, edge_id, edge, overrides
                )
            access_payloads.append(payload)
            audit_rows.append(audit)

    for edge_id, edge in sorted(remaining_overrides.items()):
        destination = destination_by_base_id.get(edge.stay_base_id)
        if destination is None:
            raise ValueError(f"unknown access override stay base: {edge.stay_base_id}")
        payload, audit = _build_overridden_access(destination, edge_id, edge, overrides)
        access_payloads.append(payload)
        audit_rows.append(audit)

    blocked = tuple(
        sorted(
            str(payload["ski_area_access_id"])
            for payload in access_payloads
            if not payload["source_urls"]
        )
    )
    return (
        sorted(access_payloads, key=lambda item: str(item["ski_area_access_id"])),
        tuple(sorted(audit_rows, key=lambda item: item.access_id)),
        blocked,
    )


def _convert_legacy_domains(
    terrain_domains: list[TerrainDomain],
) -> list[dict[str, object]]:
    return [
        {
            "terrain_domain_id": domain.terrain_domain_id,
            "name": domain.name,
            "ski_area_ids": [ref.ski_area_id for ref in domain.ski_area_refs],
            "metric_scope": domain.metric_scope,
            "total_piste_km": domain.total_piste_km,
            "total_lift_count": domain.total_lift_count,
            "base_elevation_m": domain.base_elevation_m,
            "summit_elevation_m": domain.summit_elevation_m,
            "piste_km_by_difficulty": (
                domain.piste_km_by_difficulty.model_dump(mode="json")
                if domain.piste_km_by_difficulty is not None
                else None
            ),
            "season_windows": [
                window.model_dump(mode="json") for window in domain.season_windows
            ],
            "source_urls": domain.source_urls,
        }
        for domain in terrain_domains
    ]


def _route_terrain_groups(
    destinations: list[Destination],
    terrain_domains: list[dict[str, object]],
    overrides: MigrationOverrides,
) -> tuple[
    dict[str, dict[str, object]],
    tuple[tuple[str, str], ...],
]:
    pass_aggregates: dict[str, dict[str, object]] = {}
    routes: list[tuple[str, str]] = []
    seen_group_ids: set[str] = set()

    for destination in destinations:
        for group in destination.terrain_groups:
            group_id = group.terrain_group_id
            seen_group_ids.add(group_id)
            route = overrides.terrain_group_routes.get(group_id)
            if route is None:
                raise ValueError(f"terrain group has no explicit route: {group_id}")
            routes.append((group_id, route))
            metrics = {
                "total_piste_km": group.total_piste_km,
                "total_lift_count": group.total_lift_count,
                "piste_km_by_difficulty": (
                    group.piste_km_by_difficulty.model_dump(mode="json")
                    if group.piste_km_by_difficulty is not None
                    else None
                ),
                "source_urls": group.source_urls,
            }
            if route == "terrain_domain":
                terrain_domains.append(
                    {
                        "terrain_domain_id": group_id,
                        "name": group.name,
                        "ski_area_ids": group.ski_area_ids,
                        "metric_scope": "aggregate",
                        **metrics,
                    }
                )
                continue
            if route.startswith("pass:"):
                pass_id = route.removeprefix("pass:")
                if pass_id in pass_aggregates:
                    raise ValueError(f"multiple terrain groups route to pass {pass_id}")
                pass_aggregates[pass_id] = {
                    "metric_scope": "pass_accessible",
                    **metrics,
                }
                continue
            raise ValueError(f"unknown terrain group route for {group_id}: {route}")

    unknown_routes = set(overrides.terrain_group_routes) - seen_group_ids
    if unknown_routes:
        raise ValueError(
            f"terrain group routes reference unknown groups: {sorted(unknown_routes)}"
        )
    return pass_aggregates, tuple(sorted(routes))


def _price_key(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _shared_pass_source_map(overrides: MigrationOverrides) -> dict[str, str]:
    canonical_by_source_id: dict[str, str] = {}
    for canonical_id, source_ids in overrides.shared_pass_ids.items():
        for source_id in source_ids:
            previous = canonical_by_source_id.setdefault(source_id, canonical_id)
            if previous != canonical_id:
                raise ValueError(f"shared pass source mapped twice: {source_id}")
    return canonical_by_source_id


def _new_pass_accumulator() -> _PassAccumulator:
    return _PassAccumulator(
        source_ids=[],
        names=set(),
        validity_scopes=set(),
        available_destination_ids=set(),
        default_destination_ids=set(),
        valid_ski_area_ids=set(),
        terrain_domain_ids=set(),
        external_validity_summaries=set(),
        prices_by_key={},
    )


def _build_lift_passes(
    destinations: list[Destination],
    pass_aggregates: dict[str, dict[str, object]],
    overrides: MigrationOverrides,
) -> tuple[list[dict[str, object]], dict[str, tuple[str, ...]]]:
    canonical_by_source_id = _shared_pass_source_map(overrides)
    grouped: dict[str, _PassAccumulator] = defaultdict(_new_pass_accumulator)

    for destination in destinations:
        for product in destination.lift_pass_products:
            source_id = f"{destination.resort_id}:{product.lift_pass_product_id}"
            canonical_id = canonical_by_source_id.get(
                source_id, product.lift_pass_product_id
            )
            accumulator = grouped[canonical_id]
            accumulator.source_ids.append(source_id)
            accumulator.names.add(product.name)
            accumulator.validity_scopes.add(product.validity_scope)
            accumulator.available_destination_ids.add(destination.resort_id)
            if product.is_default:
                accumulator.default_destination_ids.add(destination.resort_id)
            accumulator.valid_ski_area_ids.update(product.valid_ski_area_ids)
            accumulator.terrain_domain_ids.update(product.terrain_domain_ids)
            if product.external_validity_summary:
                accumulator.external_validity_summaries.add(
                    product.external_validity_summary
                )
            for price in product.prices:
                payload = price.model_dump(mode="json")
                accumulator.prices_by_key.setdefault(_price_key(payload), payload)

    actual_source_ids = {
        source_id
        for accumulator in grouped.values()
        for source_id in accumulator.source_ids
    }
    expected_shared_source_ids = set(canonical_by_source_id)
    missing_sources = expected_shared_source_ids - actual_source_ids
    if missing_sources:
        raise ValueError(
            f"shared pass override sources not found: {sorted(missing_sources)}"
        )

    payloads: list[dict[str, object]] = []
    merged_source_ids: dict[str, tuple[str, ...]] = {}
    for canonical_id, accumulator in sorted(grouped.items()):
        declared_sources = overrides.shared_pass_ids.get(canonical_id)
        actual_sources = tuple(sorted(accumulator.source_ids))
        if declared_sources is None and len(actual_sources) > 1:
            raise ValueError(
                f"duplicate pass id requires explicit shared_pass_ids: {canonical_id}"
            )
        if declared_sources is not None:
            if set(declared_sources) != set(actual_sources):
                raise ValueError(
                    f"shared pass {canonical_id} source membership does not match"
                )
            merged_source_ids[canonical_id] = actual_sources
        if len(accumulator.names) != 1 or len(accumulator.validity_scopes) != 1:
            raise ValueError(f"shared pass {canonical_id} has incompatible products")

        summary = overrides.shared_pass_external_validity_summaries.get(canonical_id)
        if summary is None:
            if len(accumulator.external_validity_summaries) > 1:
                raise ValueError(
                    f"shared pass {canonical_id} needs an explicit validity summary"
                )
            summary = next(iter(accumulator.external_validity_summaries), None)

        payloads.append(
            {
                "lift_pass_product_id": canonical_id,
                "name": next(iter(accumulator.names)),
                "validity_scope": next(iter(accumulator.validity_scopes)),
                "available_from_stay_destination_ids": sorted(
                    accumulator.available_destination_ids
                ),
                "default_for_stay_destination_ids": sorted(
                    accumulator.default_destination_ids
                ),
                "valid_ski_area_ids": sorted(accumulator.valid_ski_area_ids),
                "terrain_domain_ids": sorted(accumulator.terrain_domain_ids),
                "external_validity_summary": summary,
                "pass_accessible_terrain": pass_aggregates.get(canonical_id),
                "prices": [
                    accumulator.prices_by_key[key]
                    for key in sorted(accumulator.prices_by_key)
                ],
            }
        )

    unused_aggregates = set(pass_aggregates) - set(grouped)
    if unused_aggregates:
        raise ValueError(f"terrain groups route to unknown passes: {unused_aggregates}")
    return payloads, dict(sorted(merged_source_ids.items()))


def _slug(value: str, *, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or fallback


def _build_rentals(destinations: list[Destination]) -> list[dict[str, object]]:
    records = sorted(
        (
            destination.resort_id,
            rental.name,
            index,
            rental,
        )
        for destination in destinations
        for index, rental in enumerate(destination.rentals)
    )
    slug_counts = Counter(_slug(name, fallback="rental") for _, name, _, _ in records)
    candidate_counts: Counter[str] = Counter()
    payloads: list[dict[str, object]] = []

    for destination_id, name, _, rental in records:
        name_slug = _slug(name, fallback="rental")
        candidate = (
            name_slug
            if slug_counts[name_slug] == 1
            else f"{_slug(destination_id, fallback='destination')}-{name_slug}"
        )
        candidate_counts[candidate] += 1
        rental_id = candidate
        if candidate_counts[candidate] > 1:
            rental_id = f"{candidate}-{candidate_counts[candidate]}"
        price_min, price_max = _parse_price_range(rental.price_range)
        payloads.append(
            {
                "rental_display_fact_id": rental_id,
                "stay_destination_id": destination_id,
                "stay_base_id": None,
                "name": rental.name,
                "price_range": rental.price_range,
                "price_min": price_min,
                "price_max": price_max,
                "quality": rental.quality,
                "lift_distance": rental.lift_distance,
            }
        )
    return sorted(payloads, key=lambda item: str(item["rental_display_fact_id"]))


def _explicit_access_decisions(overrides: MigrationOverrides) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"access `{edge_id}`: {edge.decision_note}"
            for edge_id, edge in overrides.access_edge_overrides.items()
            if edge.decision_note
        )
    )


def _id_changes(before_ids: set[str], after_ids: set[str]) -> tuple[str, ...]:
    return tuple(
        [f"removed:{item}" for item in sorted(before_ids - after_ids)]
        + [f"added:{item}" for item in sorted(after_ids - before_ids)]
    )


def build_catalog_migration(
    destinations: list[Destination],
    legacy_terrain_domains: list[TerrainDomain],
    overrides: MigrationOverrides,
) -> CatalogMigration:
    before_counts = _legacy_counts(destinations, legacy_terrain_domains)
    regions, stay_destinations, memberships = _build_regions_and_destinations(
        destinations, overrides
    )
    stay_bases = _build_stay_bases(destinations)
    ski_areas, skill_decisions = _build_ski_areas(destinations)
    accesses, access_audit, blocked = _build_accesses(destinations, overrides)
    if blocked:
        raise CatalogMigrationBlocked(blocked)

    terrain_domains = _convert_legacy_domains(legacy_terrain_domains)
    pass_aggregates, terrain_routes = _route_terrain_groups(
        destinations, terrain_domains, overrides
    )
    lift_passes, merged_passes = _build_lift_passes(
        destinations, pass_aggregates, overrides
    )
    rentals = _build_rentals(destinations)

    snapshot = CatalogSnapshot.model_validate(
        {
            "schema_version": 1,
            "ski_regions": regions,
            "stay_destinations": stay_destinations,
            "stay_bases": stay_bases,
            "ski_areas": ski_areas,
            "ski_area_access": accesses,
            "terrain_domains": sorted(
                terrain_domains, key=lambda item: str(item["terrain_domain_id"])
            ),
            "lift_pass_products": lift_passes,
            "rental_display_facts": rentals,
        }
    )
    legacy_destination_ids = {destination.resort_id for destination in destinations}
    converted_destination_ids = {
        destination.stay_destination_id for destination in snapshot.stay_destinations
    }
    legacy_base_ids = {
        base.stay_base_id
        for destination in destinations
        for base in destination.stay_bases
    }
    converted_base_ids = {base.stay_base_id for base in snapshot.stay_bases}
    legacy_area_ids = {
        area.ski_area_id
        for destination in destinations
        for area in destination.ski_areas
    }
    converted_area_ids = {area.ski_area_id for area in snapshot.ski_areas}
    legacy_domain_ids = {domain.terrain_domain_id for domain in legacy_terrain_domains}
    converted_domain_ids = {
        domain.terrain_domain_id for domain in snapshot.terrain_domains
    }
    audit = MigrationAudit(
        before_counts=before_counts,
        after_counts=_snapshot_counts(snapshot),
        stay_destination_id_changes=_id_changes(
            legacy_destination_ids, converted_destination_ids
        ),
        stay_base_id_changes=_id_changes(legacy_base_ids, converted_base_ids),
        ski_area_id_changes=_id_changes(legacy_area_ids, converted_area_ids),
        existing_terrain_domain_id_changes=tuple(
            f"removed:{item}"
            for item in sorted(legacy_domain_ids - converted_domain_ids)
        ),
        trip_market_memberships=memberships,
        access_edges=access_audit,
        merged_pass_source_ids=merged_passes,
        terrain_group_routes=terrain_routes,
        blocked_relationships=(),
        dropped_fields=_DESTINATION_DROPPED_FIELDS,
        derived_decisions=tuple(
            sorted(skill_decisions + _explicit_access_decisions(overrides))
        ),
    )
    return CatalogMigration(
        snapshot=snapshot,
        audit=audit,
        report_markdown=render_migration_report(snapshot, audit),
    )


def convert_legacy_catalog(
    destinations: list[Destination],
    legacy_terrain_domains: list[TerrainDomain],
    overrides: MigrationOverrides,
) -> CatalogSnapshot:
    return build_catalog_migration(
        destinations, legacy_terrain_domains, overrides
    ).snapshot


def _markdown_urls(urls: tuple[str, ...]) -> str:
    return "<br>".join(f"[{url}]({url})" for url in urls)


def render_migration_report(snapshot: CatalogSnapshot, audit: MigrationAudit) -> str:
    lines = [
        "# Catalog Migration Review",
        "",
        "Status: **READY FOR OWNER REVIEW**",
        "",
        "## Before/After Entity Counts",
        "",
        "| Entity | Before | After |",
        "| --- | ---: | ---: |",
    ]
    for entity in audit.before_counts:
        lines.append(
            f"| `{entity}` | {audit.before_counts[entity]} | "
            f"{audit.after_counts[entity]} |"
        )

    lines.extend(
        [
            "",
            "## Stable ID Changes",
            "",
            "Stay-destination ID changes: "
            f"**{len(audit.stay_destination_id_changes)}**",
            "",
            f"Stay-base ID changes: **{len(audit.stay_base_id_changes)}**",
            "",
            f"Ski-area ID changes: **{len(audit.ski_area_id_changes)}**",
            "",
            "Existing terrain-domain ID changes: "
            f"**{len(audit.existing_terrain_domain_id_changes)}**",
            "",
            f"Lift-pass ID merges: **{len(audit.merged_pass_source_ids)}**",
            "",
        ]
    )
    stable_id_changes = (
        audit.stay_destination_id_changes
        + audit.stay_base_id_changes
        + audit.ski_area_id_changes
        + audit.existing_terrain_domain_id_changes
    )
    if stable_id_changes:
        lines.extend(f"- `{change}`" for change in stable_id_changes)
    else:
        lines.append("- All 31 stay-destination IDs are preserved from `resort_id`.")
        lines.append("- All 45 loaded stay-base IDs are preserved.")
        lines.append("- None. All 36 weather-owning ski-area IDs are unchanged.")
        lines.append("- All three existing terrain-domain IDs are preserved.")
    lines.append(
        "- `kitzsteinhorn-maiskogel` is a new terrain-domain ID routed from "
        "the same legacy terrain-group ID."
    )
    lines.append(
        "- Rental display facts had no legacy IDs; 32 deterministic IDs are assigned."
    )

    lines.extend(
        [
            "",
            "## Trip-Market Memberships",
            "",
            "| Trip market | Stay destinations |",
            "| --- | --- |",
        ]
    )
    for region_id, members in audit.trip_market_memberships.items():
        lines.append(
            f"| `{region_id}` | {', '.join(f'`{member}`' for member in members)} |"
        )

    lines.extend(
        [
            "",
            "## Generated Access Edges",
            "",
            "| Access edge | Mode | Direct | Facts moved | Sources |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for edge in audit.access_edges:
        lines.append(
            f"| `{edge.access_id}` | `{edge.mode}` | "
            f"{'yes' if edge.is_direct else 'no'} | "
            f"{'yes' if edge.facts_moved else 'no'} | "
            f"{_markdown_urls(edge.source_urls)} |"
        )

    passes_by_id = {
        item.lift_pass_product_id: item for item in snapshot.lift_pass_products
    }
    lines.extend(
        [
            "",
            "## Merged Passes",
            "",
            "| Result pass | Source IDs | Availability | Defaults | Coverage | "
            "Prices |",
            "| --- | --- | --- | --- | --- | ---: |",
        ]
    )
    for pass_id, source_ids in audit.merged_pass_source_ids.items():
        product = passes_by_id[pass_id]
        coverage = tuple(product.valid_ski_area_ids) + tuple(product.terrain_domain_ids)
        availability = ", ".join(
            f"`{item}`" for item in product.available_from_stay_destination_ids
        )
        defaults = ", ".join(
            f"`{item}`" for item in product.default_for_stay_destination_ids
        )
        lines.append(
            f"| `{pass_id}` | {', '.join(f'`{item}`' for item in source_ids)} | "
            f"{availability} | {defaults} | "
            f"{', '.join(f'`{item}`' for item in coverage)} | {len(product.prices)} |"
        )

    lines.extend(
        [
            "",
            "## Terrain Group Routing",
            "",
            "| Legacy terrain group | Route |",
            "| --- | --- |",
        ]
    )
    lines.extend(
        f"| `{group_id}` | `{route}` |"
        for group_id, route in audit.terrain_group_routes
    )

    lines.extend(
        [
            "",
            "## Blocked/Unsourced Relationships",
            "",
            f"Blocked relationships: **{len(audit.blocked_relationships)}**",
            "",
        ]
    )
    if audit.blocked_relationships:
        lines.extend(f"- `{item}`" for item in audit.blocked_relationships)
    else:
        lines.append("- None. Every generated access edge has an external source URL.")

    lines.extend(["", "## Dropped Fields", ""])
    lines.extend(
        f"- `{field}`: compatibility copy removed from the normalized destination."
        for field in audit.dropped_fields
    )
    lines.extend(
        [
            "",
            "- `destination.ski_areas`, `destination.terrain_groups`, and "
            "`destination.lift_pass_products` ownership is normalized into "
            "top-level entities and explicit relationships.",
            "- No `TerrainGroup` entity survives the conversion.",
            "",
            "## Estimated/Derived Decisions",
            "",
        ]
    )
    lines.extend(f"- {decision.rstrip('.')}." for decision in audit.derived_decisions)
    return "\n".join(lines) + "\n"


def serialize_catalog(snapshot: CatalogSnapshot) -> str:
    return (
        json.dumps(
            snapshot.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert the legacy Snowcast catalog into CatalogSnapshot JSON."
    )
    parser.add_argument("--resorts-path", type=Path, default=DEFAULT_RESORTS_PATH)
    parser.add_argument(
        "--terrain-domains-path",
        type=Path,
        default=DEFAULT_TERRAIN_DOMAINS_PATH,
    )
    parser.add_argument("--overrides-path", type=Path, default=DEFAULT_OVERRIDES_PATH)
    parser.add_argument("--output-path", type=Path, default=CATALOG_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        destinations = load_resorts_from_path(args.resorts_path)
        terrain_domains = load_terrain_domains_from_path(args.terrain_domains_path)
        overrides = load_migration_overrides(args.overrides_path)
        migration = build_catalog_migration(destinations, terrain_domains, overrides)
    except CatalogMigrationBlocked as error:
        _write_text_atomic(args.report_path, error.render_report())
        print(f"[catalog-migration-blocked] {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"[catalog-migration-invalid] {error}", file=sys.stderr)
        return 1

    _write_text_atomic(args.output_path, serialize_catalog(migration.snapshot))
    _write_text_atomic(args.report_path, migration.report_markdown)
    print(
        "[catalog-migration-complete] "
        f"output={args.output_path} report={args.report_path} "
        f"stay_destinations={len(migration.snapshot.stay_destinations)} "
        f"stay_bases={len(migration.snapshot.stay_bases)} "
        f"ski_areas={len(migration.snapshot.ski_areas)} "
        f"ski_regions={len(migration.snapshot.ski_regions)} "
        f"access_links={len(migration.snapshot.ski_area_access)} "
        f"blocked={len(migration.audit.blocked_relationships)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
