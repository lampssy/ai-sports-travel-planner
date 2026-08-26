from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping
from urllib.parse import quote, urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.domain.catalog import CatalogSnapshot, LiftPassProduct, SkiArea
from app.integrations.open_meteo import weather_elevation_points

CatalogTargetType = Literal[
    "ski_region",
    "stay_destination",
    "stay_base",
    "ski_area",
    "ski_area_access",
    "terrain_domain",
    "lift_pass_product",
    "rental_display_fact",
    "trust_manifest",
]
CatalogSourceType = Literal[
    "official",
    "open_data",
    "reviewed_editorial",
    "third_party",
]
CatalogTrustStatus = Literal[
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
]
CatalogFieldCoverageStatus = Literal[
    "changed",
    "reviewed-no-change",
    "unresolved",
    "not-applicable",
]
CatalogIssueSeverity = Literal["error", "warning"]
CatalogReviewScope = Literal["full", "narrow"]
CatalogResultingGraphRole = Literal["focus", "linked_dependency"]
CatalogReportSchemaVersion = Literal[1, 2, 3]
CatalogScopeCandidateKind = Literal[
    "stay_destination",
    "stay_base",
    "ski_area",
    "ski_area_access",
    "terrain_domain",
    "lift_pass_product",
]
CatalogScopeDisposition = Literal[
    "represented",
    "add_entity",
    "not_separate",
    "external_pass_context",
    "deferred",
    "unresolved",
]
CatalogGraphImpact = Literal["graph_blocking", "regional_followup"]
CatalogReviewSourceKind = Literal[
    "destination_booking",
    "ski_area_operator",
    "pass_tariff",
    "access_transport",
    "linked_pr_dependency",
    "other_official",
]
CatalogScopeSignalType = Literal[
    "official_independent_identity",
    "separate_operator",
    "independent_status_or_schedule",
    "independent_weather_presentation",
    "child_scoped_terrain_metrics",
    "full_local_pass",
    "official_map_sector",
    "webcam",
    "limited_area_ticket",
    "secondary_provider_listing",
    "disconnected_terrain",
    "ski_connected_terrain",
    "distinct_access",
    "distinct_elevation_or_season",
    "independent_stay_market",
    "direct_access_relationship",
    "official_product_identity",
    "official_complete_lift_inventory",
    "coordinated_status_or_schedule",
    "common_full_coverage_pass",
]
CatalogAssessmentStatus = Literal["pass", "fail", "unresolved"]
CatalogCoordinateDerivationAttemptMethod = Literal[
    "official_terrain_medoid",
    "osm_terrain_medoid",
    "official_central_on_mountain_point",
    "structured_lift_inventory_medoid",
]
CatalogCoordinateDerivationMethod = Literal[
    "official_terrain_medoid",
    "osm_terrain_medoid",
    "official_central_on_mountain_point",
    "structured_lift_inventory_medoid",
    "preserved_existing",
]
CatalogCoordinateDerivationAttemptOutcome = Literal[
    "selected",
    "rejected",
    "unavailable",
]
CatalogWeatherPostMergeHandoff = Literal[
    "scheduled_completion",
    "force_refetch_and_rebuild_climatology",
    "force_refetch_and_rebuild_after_activation",
]
COORDINATE_DERIVATION_HIERARCHY: tuple[
    CatalogCoordinateDerivationAttemptMethod, ...
] = (
    "official_terrain_medoid",
    "osm_terrain_medoid",
    "official_central_on_mountain_point",
    "structured_lift_inventory_medoid",
)
CatalogBoundaryGateName = Literal[
    "independent_stay_context",
    "independent_ski_access",
    "independent_recommendation_value",
    "complete_stay_market_scope",
    "independent_stay_market_ownership",
    "material_destination_level_separation_value",
]
CatalogIdentitySignalType = Literal[
    "local_pass",
    "separate_operator",
    "operating_schedule",
    "status_feed",
    "weather_presentation",
    "official_destination_treatment",
    "official_stay_market_treatment",
    "independent_accommodation_inventory",
    "independent_destination_management",
]
CatalogBoundaryFailureRoute = Literal[
    "stay_base",
    "ski_area",
    "ski_sub_area_backlog",
    "terrain_domain",
    "external_pass_context",
    "blocked",
]
CatalogSkiAreaTerrainScope = Literal["complete", "sector", "unresolved"]
CatalogSkiAreaParentConnectivity = Literal[
    "connected",
    "transfer_required",
    "disconnected",
    "not_applicable",
    "unknown",
]
CatalogSkiAreaOperationalScope = Literal[
    "independent",
    "parent_owned",
    "coordinated",
    "mixed",
    "unknown",
]
CatalogSkiAreaWeatherScope = Literal[
    "independent",
    "parent_owned",
    "mixed",
    "unknown",
]
CatalogSkiAreaPassScope = Literal[
    "full_local",
    "limited",
    "shared_only",
    "none",
    "unknown",
]
CatalogSkiAreaProviderConsensus = Literal[
    "separate",
    "aggregated",
    "mixed",
    "unknown",
]
CatalogSkiAreaSeparationValue = Literal["material", "redundant", "unresolved"]
CatalogSkiAreaCoordinationEvidenceFamilyType = Literal[
    "complete_terrain_lift_inventory",
    "exhaustive_component_operator_roster",
    "component_addressable_operations_status",
    "every_component_pass_coverage",
    "direct_component_parent_assignment",
]
JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]

SOURCE_BACKED_TRUST_STATUSES = {"verified", "verified_with_adjustment"}
VERIFICATION_SOURCE_TYPES = {"official", "open_data", "reviewed_editorial"}
GRAPH_SCOPE_TARGET_TYPES = frozenset(
    {
        "stay_destination",
        "stay_base",
        "ski_area",
        "ski_area_access",
        "terrain_domain",
        "lift_pass_product",
    }
)
SOURCE_BACKED_SCOPE_DISPOSITIONS = frozenset(
    {"represented", "add_entity", "not_separate"}
)
BACKLOG_REQUIRED_SCOPE_DISPOSITIONS = frozenset({"deferred", "unresolved"})
CATALOG_BACKLOG_REF_PREFIX = "docs/product-backlog.md#"
CATALOG_BACKLOG_REF_PATTERN = re.compile(
    rf"^{re.escape(CATALOG_BACKLOG_REF_PREFIX)}[a-z0-9]+(?:-[a-z0-9]+)*$"
)
LEGACY_INDEPENDENT_SKI_AREA_SIGNALS = frozenset(
    {
        "official_independent_identity",
        "separate_operator",
        "independent_status_or_schedule",
        "independent_weather_presentation",
        "child_scoped_terrain_metrics",
        "full_local_pass",
    }
)
SKI_AREA_TERRAIN_IDENTITY_SIGNALS = frozenset(
    {
        "official_independent_identity",
        "child_scoped_terrain_metrics",
        "official_complete_lift_inventory",
    }
)
SKI_AREA_COORDINATED_OPERATION_SIGNALS = frozenset(
    {
        "official_complete_lift_inventory",
        "coordinated_status_or_schedule",
        "common_full_coverage_pass",
    }
)
SKI_AREA_COORDINATED_EVIDENCE_FAMILY_ORDER: tuple[
    CatalogSkiAreaCoordinationEvidenceFamilyType, ...
] = (
    "complete_terrain_lift_inventory",
    "exhaustive_component_operator_roster",
    "component_addressable_operations_status",
    "every_component_pass_coverage",
    "direct_component_parent_assignment",
)
SKI_AREA_OPERATION_OWNER_SIGNALS = frozenset(
    {"separate_operator", "independent_status_or_schedule"}
)
SKI_AREA_WEATHER_OWNER_SIGNALS = frozenset({"independent_weather_presentation"})
SKI_AREA_PASS_OWNER_SIGNALS = frozenset({"full_local_pass"})
SCOPE_ID_FIELD_PATHS: Mapping[CatalogScopeCandidateKind, str] = MappingProxyType(
    {
        "stay_destination": "stay_destination_id",
        "stay_base": "stay_base_id",
        "ski_area": "ski_area_id",
        "ski_area_access": "ski_area_access_id",
        "terrain_domain": "terrain_domain_id",
        "lift_pass_product": "lift_pass_product_id",
    }
)
MARKDOWN_LINK_URL_SAFE_CHARS = ":/?#@!$&'*,;=%-._~"
LEGACY_DESTINATION_BOUNDARY_GATE_NAMES = frozenset(
    {
        "independent_stay_context",
        "independent_ski_access",
        "independent_recommendation_value",
    }
)
CURRENT_DESTINATION_BOUNDARY_GATE_NAMES = frozenset(
    {
        "complete_stay_market_scope",
        "independent_stay_market_ownership",
        "material_destination_level_separation_value",
    }
)
DESTINATION_BOUNDARY_GATE_NAME_SETS = frozenset(
    {
        LEGACY_DESTINATION_BOUNDARY_GATE_NAMES,
        CURRENT_DESTINATION_BOUNDARY_GATE_NAMES,
    }
)
CURRENT_STAY_MARKET_IDENTITY_SIGNALS = frozenset(
    {
        "official_stay_market_treatment",
        "independent_accommodation_inventory",
        "independent_destination_management",
    }
)
TRUST_MANIFEST_NAMESPACES = frozenset(
    {
        "ski_regions",
        "stay_destinations",
        "stay_bases",
        "ski_areas",
        "ski_area_access",
        "terrain_domains",
        "lift_pass_products",
        "rental_display_facts",
    }
)
TRUST_MANIFEST_TARGET_TYPES: Mapping[str, CatalogTargetType] = MappingProxyType(
    {
        "ski_regions": "ski_region",
        "stay_destinations": "stay_destination",
        "stay_bases": "stay_base",
        "ski_areas": "ski_area",
        "ski_area_access": "ski_area_access",
        "terrain_domains": "terrain_domain",
        "lift_pass_products": "lift_pass_product",
        "rental_display_facts": "rental_display_fact",
    }
)

CANONICAL_FIELD_PATHS: Mapping[CatalogTargetType, frozenset[str]] = MappingProxyType(
    {
        "ski_region": frozenset(
            {
                "ski_region_id",
                "name",
                "grouping_policy",
                "parent_ski_region_id",
                "source_urls",
            }
        ),
        "stay_destination": frozenset(
            {
                "stay_destination_id",
                "name",
                "country",
                "region",
                "price_level",
                "latitude",
                "longitude",
                "trip_market_region_id",
                "regional_data_ids",
            }
        ),
        "stay_base": frozenset(
            {
                "stay_base_id",
                "stay_destination_id",
                "name",
                "price_range",
                "price_min",
                "price_max",
                "quality",
                "latitude",
                "longitude",
                "elevation_m",
                "base_type",
                "base_character.development_style",
                "base_character.local_pace",
                "local_apres_profile.availability",
                "local_apres_profile.intensity",
                "local_apres_profile.season_label",
                "regional_data_ids",
            }
        ),
        "ski_area": frozenset(
            {
                "ski_area_id",
                "name",
                "weather_sampling_status",
                "latitude",
                "longitude",
                "base_elevation_m",
                "summit_elevation_m",
                "season_start_month",
                "season_end_month",
                "season_windows",
                "total_piste_km",
                "total_lift_count",
                "piste_km_by_difficulty.beginner",
                "piste_km_by_difficulty.intermediate",
                "piste_km_by_difficulty.advanced",
                "supported_skill_levels",
                "snowmaking.availability",
                "snowmaking.coverage_pct",
                "snowmaking.coverage_basis",
                "snowmaking.season_label",
                "glacier_terrain.availability",
                "snow_park.availability",
                "snow_park.park_count",
                "snow_park.season_label",
                "night_skiing.availability",
                "night_skiing.season_label",
                "marked_freeride_routes.availability",
                "marked_freeride_routes.route_count",
                "marked_freeride_routes.season_label",
                "official_trail_map.url",
                "official_trail_map.season_label",
                "ski_day_apres_profile.availability",
                "ski_day_apres_profile.intensity",
                "ski_day_apres_profile.season_label",
            }
        ),
        "ski_area_access": frozenset(
            {
                "ski_area_access_id",
                "stay_base_id",
                "ski_area_id",
                "access_mode",
                "lift_distance",
                "nearest_lift_name",
                "distance_m",
                "duration_minutes",
                "is_direct",
                "regional_data_ids",
                "source_urls",
            }
        ),
        "terrain_domain": frozenset(
            {
                "terrain_domain_id",
                "name",
                "ski_area_ids",
                "metric_scope",
                "total_piste_km",
                "total_lift_count",
                "base_elevation_m",
                "summit_elevation_m",
                "piste_km_by_difficulty.beginner",
                "piste_km_by_difficulty.intermediate",
                "piste_km_by_difficulty.advanced",
                "season_windows",
                "official_trail_map.url",
                "official_trail_map.season_label",
                "source_urls",
            }
        ),
        "lift_pass_product": frozenset(
            {
                "lift_pass_product_id",
                "name",
                "validity_scope",
                "available_from_stay_destination_ids",
                "default_for_stay_destination_ids",
                "valid_ski_area_ids",
                "terrain_domain_ids",
                "validity_windows",
                "external_validity_summary",
                "pass_accessible_terrain",
                "prices",
            }
        ),
        "rental_display_fact": frozenset(
            {
                "rental_display_fact_id",
                "stay_destination_id",
                "stay_base_id",
                "name",
                "price_range",
                "price_min",
                "price_max",
                "quality",
                "lift_distance",
            }
        ),
        "trust_manifest": frozenset(
            {"display_name", "field_statuses", "field_source_refs", "notes"}
        ),
    }
)

NESTED_FIELD_PATH_ROOTS: Mapping[CatalogTargetType, frozenset[str]] = MappingProxyType(
    {
        "ski_region": frozenset({"source_urls"}),
        "stay_destination": frozenset({"regional_data_ids"}),
        "stay_base": frozenset(
            {"base_character", "local_apres_profile", "regional_data_ids"}
        ),
        "ski_area": frozenset(
            {
                "season_windows",
                "supported_skill_levels",
                "snowmaking",
                "glacier_terrain",
                "snow_park",
                "night_skiing",
                "marked_freeride_routes",
                "official_trail_map",
                "ski_day_apres_profile",
            }
        ),
        "ski_area_access": frozenset({"regional_data_ids", "source_urls"}),
        "terrain_domain": frozenset(
            {"ski_area_ids", "season_windows", "official_trail_map", "source_urls"}
        ),
        "lift_pass_product": frozenset(
            {
                "available_from_stay_destination_ids",
                "default_for_stay_destination_ids",
                "valid_ski_area_ids",
                "terrain_domain_ids",
                "validity_windows",
                "pass_accessible_terrain",
                "prices",
            }
        ),
        "rental_display_fact": frozenset(),
        "trust_manifest": frozenset({"field_statuses", "field_source_refs", "notes"}),
    }
)


def _validate_non_blank_string(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be blank")
    return normalized


def _validate_optional_non_blank_string(
    value: str | None,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return _validate_non_blank_string(value, field_name)


def _validate_string_list(values: list[str], field_name: str) -> list[str]:
    normalized = [_validate_non_blank_string(value, field_name) for value in values]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must be unique")
    return normalized


def _validate_field_path(value: str) -> str:
    value = _validate_non_blank_string(value, "field_path")
    segments = value.split(".")
    if any(not segment.strip() or segment != segment.strip() for segment in segments):
        raise ValueError("field_path cannot contain blank or padded segments")
    return value


def _is_supported_field_path(target_type: CatalogTargetType, field_path: str) -> bool:
    if field_path in CANONICAL_FIELD_PATHS[target_type]:
        return True
    return any(
        field_path.startswith(f"{root_path}[") or field_path.startswith(f"{root_path}.")
        for root_path in NESTED_FIELD_PATH_ROOTS[target_type]
    )


def _validate_target_identity(target_type: CatalogTargetType, target_id: str) -> str:
    target_id = _validate_non_blank_string(target_id, "target_id")
    if target_type != "trust_manifest":
        return target_id
    namespace, separator, entity_id = target_id.partition(":")
    if not separator or namespace not in TRUST_MANIFEST_NAMESPACES:
        raise ValueError(
            "trust_manifest target_id must use <catalog_entity_type>:<entity_id>"
        )
    _validate_non_blank_string(entity_id, "trust manifest entity id")
    return target_id


def _validate_target_field(
    target_type: CatalogTargetType,
    target_id: str,
    field_path: str,
) -> tuple[str, str]:
    target_id = _validate_target_identity(target_type, target_id)
    field_path = _validate_field_path(field_path)
    if not _is_supported_field_path(target_type, field_path):
        raise ValueError(f"unsupported {target_type} field_path {field_path!r}")
    return target_id, field_path


def _validate_json_value(value: JsonValue) -> JsonValue:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("value must be JSON-compatible") from error
    return value


def json_values_equal(left: JsonValue, right: JsonValue) -> bool:
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def _safe_source_url(value: str) -> str:
    value = _validate_non_blank_string(value, "source_url")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an http(s) URL")
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("source_url cannot contain whitespace or control characters")
    if any(character in value for character in "()[]|\\<>"):
        raise ValueError("source_url cannot contain markdown-closing characters")
    return value


class CatalogValidationError(ValueError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(issues))


class CatalogCurationContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CatalogReviewSourceFamily(CatalogCurationContractModel):
    family_id: str = Field(min_length=1)
    source_kind: CatalogReviewSourceKind
    source_urls: list[str] = Field(min_length=1)
    candidate_kinds: list[CatalogScopeCandidateKind] = Field(min_length=1)

    @field_validator("family_id")
    @classmethod
    def validate_family_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "review source family_id")

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(cls, values: list[str]) -> list[str]:
        urls = [_safe_source_url(value) for value in values]
        if len(urls) != len(set(urls)):
            raise ValueError("review source URLs must be unique")
        return urls

    @field_validator("candidate_kinds")
    @classmethod
    def validate_candidate_kinds(
        cls, values: list[CatalogScopeCandidateKind]
    ) -> list[CatalogScopeCandidateKind]:
        if len(values) != len(set(values)):
            raise ValueError("review candidate kinds must be unique")
        return values


class CatalogValidationIssue(CatalogCurationContractModel):
    severity: CatalogIssueSeverity
    message: str = Field(min_length=1)
    target_type: CatalogTargetType | None = None
    target_id: str | None = None
    field_path: str | None = None


class CatalogChangeSummary(CatalogCurationContractModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    before: JsonValue = None
    after: JsonValue = None
    trust_status: CatalogTrustStatus
    ranking_relevant: bool = False

    @field_validator("before", "after")
    @classmethod
    def validate_json_values(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)

    @model_validator(mode="after")
    def validate_target(self) -> CatalogChangeSummary:
        self.target_id, self.field_path = _validate_target_field(
            self.target_type,
            self.target_id,
            self.field_path,
        )
        return self

    @property
    def target_key(self) -> tuple[str, str, str]:
        return self.target_type, self.target_id, self.field_path


class CatalogFieldCoverage(CatalogCurationContractModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    status: CatalogFieldCoverageStatus
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank_string(value, "notes")

    @model_validator(mode="after")
    def validate_target(self) -> CatalogFieldCoverage:
        self.target_id, self.field_path = _validate_target_field(
            self.target_type,
            self.target_id,
            self.field_path,
        )
        return self

    @property
    def target_key(self) -> tuple[str, str, str]:
        return self.target_type, self.target_id, self.field_path


class CatalogEvidenceItem(CatalogCurationContractModel):
    evidence_id: str = Field(min_length=1)
    boundary_target_ids: list[str] = Field(default_factory=list)
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    source_type: CatalogSourceType
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_value: JsonValue
    evidence_summary: str = Field(min_length=1)
    normalization_note: str | None = None

    @field_validator("evidence_id", "source_title", "evidence_summary")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _validate_non_blank_string(value, "text")

    @field_validator("boundary_target_ids")
    @classmethod
    def validate_boundary_targets(cls, values: list[str]) -> list[str]:
        return _validate_string_list(values, "boundary_target_ids")

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return _safe_source_url(value)

    @field_validator("source_value")
    @classmethod
    def validate_source_value(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)

    @field_validator("normalization_note")
    @classmethod
    def validate_normalization_note(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank_string(value, "normalization_note")

    @model_validator(mode="after")
    def validate_target(self) -> CatalogEvidenceItem:
        self.target_id, self.field_path = _validate_target_field(
            self.target_type,
            self.target_id,
            self.field_path,
        )
        return self

    @property
    def target_key(self) -> tuple[str, str, str]:
        return self.target_type, self.target_id, self.field_path


class CatalogReviewedTarget(CatalogCurationContractModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    scope: CatalogReviewScope
    required_field_paths: list[str] = Field(default_factory=list)
    resulting_graph_role: CatalogResultingGraphRole = "focus"

    @field_validator("required_field_paths")
    @classmethod
    def validate_required_paths(cls, values: list[str]) -> list[str]:
        normalized = [_validate_field_path(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("required_field_paths must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_scope(self) -> CatalogReviewedTarget:
        self.target_id = _validate_target_identity(self.target_type, self.target_id)
        if self.scope == "full" and self.required_field_paths:
            raise ValueError("full reviewed targets forbid required_field_paths")
        if self.scope == "narrow" and not self.required_field_paths:
            raise ValueError("narrow reviewed targets require required_field_paths")
        if self.resulting_graph_role == "linked_dependency" and self.scope != "narrow":
            raise ValueError("linked_dependency reviewed targets require narrow scope")
        unsupported = sorted(
            set(self.required_field_paths) - CANONICAL_FIELD_PATHS[self.target_type]
        )
        if unsupported:
            raise ValueError(
                "required_field_paths contains unsupported canonical paths: "
                + ", ".join(unsupported)
            )
        return self

    @property
    def target_key(self) -> tuple[str, str]:
        return self.target_type, self.target_id

    @property
    def canonical_review_paths(self) -> frozenset[str]:
        if self.scope == "full":
            return CANONICAL_FIELD_PATHS[self.target_type]
        return frozenset(self.required_field_paths)


class CatalogBoundaryGateAssessment(CatalogCurationContractModel):
    gate_name: CatalogBoundaryGateName
    status: CatalogAssessmentStatus
    notes: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)


class CatalogIdentitySignalAssessment(CatalogCurationContractModel):
    signal_type: CatalogIdentitySignalType
    status: CatalogAssessmentStatus
    notes: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)


class CatalogDestinationBoundaryAssessment(CatalogCurationContractModel):
    candidate_id: str = Field(min_length=1)
    gates: list[CatalogBoundaryGateAssessment]
    identity_signals: list[CatalogIdentitySignalAssessment] = Field(min_length=1)
    failure_route: CatalogBoundaryFailureRoute | None = None

    @model_validator(mode="after")
    def validate_assessment(self) -> CatalogDestinationBoundaryAssessment:
        gate_names = frozenset(gate.gate_name for gate in self.gates)
        if gate_names not in DESTINATION_BOUNDARY_GATE_NAME_SETS:
            raise ValueError(
                "destination boundary assessment must contain exactly one complete "
                "three-gate policy set"
            )
        if len(self.gates) != len(gate_names):
            raise ValueError("destination boundary gates must be unique")
        signal_types = [signal.signal_type for signal in self.identity_signals]
        if len(signal_types) != len(set(signal_types)):
            raise ValueError("destination identity signals must be unique")
        if self.is_passing and self.failure_route is not None:
            raise ValueError("passing destination assessment forbids failure_route")
        if not self.is_passing and self.failure_route is None:
            raise ValueError(
                "non-passing destination assessment requires failure_route"
            )
        return self

    @property
    def is_passing(self) -> bool:
        if not all(gate.status == "pass" for gate in self.gates):
            return False
        if self.uses_current_policy:
            return any(
                signal.status == "pass"
                and signal.signal_type in CURRENT_STAY_MARKET_IDENTITY_SIGNALS
                for signal in self.identity_signals
            )
        return any(signal.status == "pass" for signal in self.identity_signals)

    @property
    def uses_current_policy(self) -> bool:
        return (
            frozenset(gate.gate_name for gate in self.gates)
            == CURRENT_DESTINATION_BOUNDARY_GATE_NAMES
        )

    @property
    def has_current_ownership_signal_assessment(self) -> bool:
        return any(
            signal.signal_type in CURRENT_STAY_MARKET_IDENTITY_SIGNALS
            for signal in self.identity_signals
        )


class CatalogEntityScopeTargetRef(CatalogCurationContractModel):
    target_type: CatalogScopeCandidateKind
    target_id: str = Field(min_length=1)

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "target_id")

    @property
    def target_key(self) -> tuple[str, str]:
        return self.target_type, self.target_id


class CatalogSkiAreaCoordinationEvidenceFamily(CatalogCurationContractModel):
    family: CatalogSkiAreaCoordinationEvidenceFamilyType
    evidence_refs: list[str] = Field(min_length=1)
    covered_component_candidate_ids: list[str] = Field(min_length=1)

    @field_validator("evidence_refs", "covered_component_candidate_ids")
    @classmethod
    def validate_reference_lists(
        cls, values: list[str], info: ValidationInfo
    ) -> list[str]:
        return _validate_string_list(
            values, f"coordination evidence family {info.field_name}"
        )


class CatalogSkiAreaBoundaryAssessment(CatalogCurationContractModel):
    parent_ski_area_id: str | None = None
    terrain_scope: CatalogSkiAreaTerrainScope
    connectivity_to_parent: CatalogSkiAreaParentConnectivity
    operational_scope: CatalogSkiAreaOperationalScope
    weather_scope: CatalogSkiAreaWeatherScope
    pass_scope: CatalogSkiAreaPassScope
    provider_consensus: CatalogSkiAreaProviderConsensus
    separation_value: CatalogSkiAreaSeparationValue
    component_candidate_ids: list[str] = Field(default_factory=list)
    coordination_evidence_refs: list[str] = Field(default_factory=list)
    coordination_evidence_families: list[CatalogSkiAreaCoordinationEvidenceFamily] = (
        Field(default_factory=list)
    )
    evidence_refs: list[str] = Field(min_length=1)

    @field_validator("parent_ski_area_id")
    @classmethod
    def validate_parent_ski_area_id(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank_string(value, "parent_ski_area_id")

    @field_validator(
        "component_candidate_ids",
        "coordination_evidence_refs",
        "evidence_refs",
    )
    @classmethod
    def validate_reference_lists(
        cls, values: list[str], info: ValidationInfo
    ) -> list[str]:
        return _validate_string_list(values, f"ski-area boundary {info.field_name}")

    @model_validator(mode="after")
    def validate_parent_reference(self) -> CatalogSkiAreaBoundaryAssessment:
        if self.connectivity_to_parent == "not_applicable":
            if self.parent_ski_area_id is not None:
                raise ValueError(
                    "not_applicable connectivity forbids parent_ski_area_id"
                )
        elif self.parent_ski_area_id is None:
            raise ValueError("ski-area parent connectivity requires parent_ski_area_id")
        return self

    @model_validator(mode="after")
    def validate_coordination_metadata(self) -> CatalogSkiAreaBoundaryAssessment:
        if self.operational_scope != "coordinated" and self.has_coordination_metadata:
            raise ValueError(
                "coordination metadata requires operational_scope=coordinated"
            )
        family_names = [
            evidence_family.family
            for evidence_family in self.coordination_evidence_families
        ]
        if len(family_names) != len(set(family_names)):
            raise ValueError("coordination evidence families must be unique")
        family_evidence_refs = {
            evidence_ref
            for evidence_family in self.coordination_evidence_families
            for evidence_ref in evidence_family.evidence_refs
        }
        if set(self.coordination_evidence_refs) != family_evidence_refs:
            raise ValueError(
                "coordination_evidence_refs must equal the union of coordination "
                "evidence family refs"
            )
        if not set(self.coordination_evidence_refs).issubset(self.evidence_refs):
            raise ValueError(
                "coordination_evidence_refs must be included in evidence_refs"
            )
        return self

    @property
    def has_coordination_metadata(self) -> bool:
        return bool(
            self.component_candidate_ids
            or self.coordination_evidence_refs
            or self.coordination_evidence_families
        )


class CatalogEntityScopeAssessment(CatalogCurationContractModel):
    candidate_id: str = Field(min_length=1)
    candidate_name: str = Field(min_length=1)
    candidate_kind: CatalogScopeCandidateKind
    disposition: CatalogScopeDisposition
    signals: list[CatalogScopeSignalType] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    target_refs: list[CatalogEntityScopeTargetRef] = Field(default_factory=list)
    backlog_ref: str | None = None
    rationale: str = Field(min_length=1)
    ski_area_boundary: CatalogSkiAreaBoundaryAssessment | None = None
    graph_impact: CatalogGraphImpact | None = None

    @field_validator("candidate_id", "candidate_name", "rationale")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _validate_non_blank_string(value, "scope assessment text")

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        return _validate_string_list(values, "evidence_refs")

    @field_validator("backlog_ref")
    @classmethod
    def validate_backlog_ref(cls, value: str | None) -> str | None:
        value = _validate_optional_non_blank_string(value, "backlog_ref")
        if value is not None and CATALOG_BACKLOG_REF_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "backlog_ref must be a canonical product backlog reference"
            )
        return value

    @field_validator("signals")
    @classmethod
    def validate_signals(
        cls, values: list[CatalogScopeSignalType]
    ) -> list[CatalogScopeSignalType]:
        if len(values) != len(set(values)):
            raise ValueError("signals must be unique")
        return values

    @model_validator(mode="after")
    def validate_target_refs(self) -> CatalogEntityScopeAssessment:
        target_keys = [target.target_key for target in self.target_refs]
        if len(target_keys) != len(set(target_keys)):
            raise ValueError("target_refs must be unique")
        mismatched = [
            target
            for target in self.target_refs
            if target.target_type != self.candidate_kind
        ]
        if mismatched:
            raise ValueError("target_refs must match candidate_kind")
        if self.disposition in SOURCE_BACKED_SCOPE_DISPOSITIONS:
            if not self.target_refs:
                raise ValueError(f"{self.disposition} requires target_refs")
        return self


class CatalogWeatherRequestGeometry(CatalogCurationContractModel):
    weather_sampling_status: Literal["active", "deferred"] = "active"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    base_elevation_m: int = Field(ge=0)
    mid_elevation_m: int = Field(ge=0)
    upper_elevation_m: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_elevation_order(self) -> CatalogWeatherRequestGeometry:
        if not (
            self.base_elevation_m <= self.mid_elevation_m <= self.upper_elevation_m
        ):
            raise ValueError(
                "weather elevation bands must satisfy base <= mid <= upper"
            )
        return self


class CatalogCoordinateDerivationAttempt(CatalogCurationContractModel):
    method: CatalogCoordinateDerivationAttemptMethod
    outcome: CatalogCoordinateDerivationAttemptOutcome
    evidence_refs: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        return _validate_string_list(values, "coordinate attempt evidence_refs")

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("coordinate attempt rationale must not be blank")
        return normalized


class CatalogWeatherRequestGeometryAssessment(CatalogCurationContractModel):
    ski_area_id: str = Field(min_length=1)
    before: CatalogWeatherRequestGeometry | None
    after: CatalogWeatherRequestGeometry
    coordinate_derivation_method: CatalogCoordinateDerivationMethod | None = None
    elevation_derivation_method: (
        Literal[
            "official_lift_served_range",
            "official_lift_inventory_range",
            "open_data_lift_inventory_range",
            "specialist_conflict_tiebreak",
            "preserved_existing",
        ]
        | None
    ) = None
    geometry_completeness: (
        Literal["complete", "sufficient", "partial", "unavailable"] | None
    ) = None
    derivation_status: (
        Literal["verified", "verified_with_adjustment", "deferred"] | None
    ) = None
    evidence_refs: list[str] = Field(default_factory=list)
    coordinate_derivation_attempts: list[CatalogCoordinateDerivationAttempt] = Field(
        default_factory=list
    )
    activation_prerequisite: str | None = None
    post_merge_handoff: CatalogWeatherPostMergeHandoff | None = None

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        return _validate_string_list(values, "weather geometry evidence_refs")

    @field_validator("activation_prerequisite")
    @classmethod
    def validate_activation_prerequisite(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank_string(value, "activation_prerequisite")

    @property
    def material_change(self) -> bool:
        return self.before != self.after

    @property
    def request_geometry_changed(self) -> bool:
        if self.before is None:
            return False
        return any(
            before_value != after_value
            for before_value, after_value in (
                (self.before.latitude, self.after.latitude),
                (self.before.longitude, self.after.longitude),
                (self.before.base_elevation_m, self.after.base_elevation_m),
                (self.before.mid_elevation_m, self.after.mid_elevation_m),
                (self.before.upper_elevation_m, self.after.upper_elevation_m),
            )
        )


class CatalogResultingGraph(CatalogCurationContractModel):
    focus_stay_destination_ids: list[str] = Field(min_length=1)

    @field_validator("focus_stay_destination_ids")
    @classmethod
    def validate_focus_stay_destination_ids(cls, values: list[str]) -> list[str]:
        return _validate_string_list(values, "focus_stay_destination_ids")


def catalog_weather_request_geometry(
    ski_area: SkiArea,
) -> CatalogWeatherRequestGeometry:
    elevation_by_band = {
        point.band: point.elevation_m for point in weather_elevation_points(ski_area)
    }
    return CatalogWeatherRequestGeometry(
        weather_sampling_status=ski_area.weather_sampling_status,
        latitude=ski_area.latitude,
        longitude=ski_area.longitude,
        base_elevation_m=elevation_by_band["base"],
        mid_elevation_m=elevation_by_band["mid"],
        upper_elevation_m=elevation_by_band["upper"],
    )


class CatalogCurationReport(CatalogCurationContractModel):
    report_schema_version: CatalogReportSchemaVersion = 1
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    changed_entities: list[str] = Field(default_factory=list)
    reviewed_targets: list[CatalogReviewedTarget]
    changes: list[CatalogChangeSummary] = Field(default_factory=list)
    field_coverage: list[CatalogFieldCoverage] = Field(default_factory=list)
    evidence: list[CatalogEvidenceItem] = Field(default_factory=list)
    destination_boundary_assessments: list[CatalogDestinationBoundaryAssessment] = (
        Field(default_factory=list)
    )
    entity_scope_assessments: list[CatalogEntityScopeAssessment] = Field(
        default_factory=list
    )
    review_evidence_envelope: list[CatalogReviewSourceFamily] = Field(
        default_factory=list
    )
    boundary_decision_targets: list[str] = Field(default_factory=list)
    weather_request_geometry_targets: list[str] = Field(default_factory=list)
    weather_request_geometry_assessments: list[
        CatalogWeatherRequestGeometryAssessment
    ] = Field(default_factory=list)
    resulting_graph: CatalogResultingGraph | None = None
    validation_commands: list[str] = Field(default_factory=list)
    ranking_impact_summary: str | None = None
    unresolved_caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_activity(self) -> CatalogCurationReport:
        if not (
            self.changes
            or self.boundary_decision_targets
            or self.weather_request_geometry_targets
            or self.field_coverage
            or self.entity_scope_assessments
        ):
            raise ValueError(
                "curation report must include a change or retained semantic decision"
            )
        return self

    @field_validator(
        "changed_entities",
        "boundary_decision_targets",
        "weather_request_geometry_targets",
        "validation_commands",
        "unresolved_caveats",
    )
    @classmethod
    def validate_string_lists(cls, values: list[str]) -> list[str]:
        return _validate_string_list(values, "report list")


def load_catalog_curation_report(path: Path) -> CatalogCurationReport:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CatalogValidationError(
            [f"Unable to read curation report at {path}: {error}"]
        ) from error
    except json.JSONDecodeError as error:
        raise CatalogValidationError(
            [f"Invalid JSON in curation report at {path}: {error}"]
        ) from error
    return CatalogCurationReport.model_validate(payload)


def validate_catalog_curation_report(
    report: CatalogCurationReport,
    *,
    require_resulting_graph: bool = False,
    require_current_destination_policy: bool = False,
    require_bounded_review_inventory: bool = False,
) -> None:
    issues: list[str] = []
    if require_bounded_review_inventory and not report.review_evidence_envelope:
        issues.append("bounded review inventory requires review_evidence_envelope")
    if report.resulting_graph is not None and report.report_schema_version < 3:
        issues.append("resulting_graph requires report schema version 3")
    if report.report_schema_version < 3 and any(
        target.resulting_graph_role == "linked_dependency"
        for target in report.reviewed_targets
    ):
        issues.append(
            "linked_dependency reviewed targets require report schema version 3"
        )
    if (
        require_resulting_graph
        and report.report_schema_version == 3
        and report.resulting_graph is None
    ):
        issues.append("schema version 3 requires resulting_graph")
    if any(change.ranking_relevant for change in report.changes):
        if not report.ranking_impact_summary:
            issues.append(
                "ranking_impact_summary is required when any change is ranking-relevant"
            )

    reviewed_by_key: dict[tuple[str, str], CatalogReviewedTarget] = {}
    for target in report.reviewed_targets:
        if target.target_key in reviewed_by_key:
            issues.append(f"{target.target_type}:{target.target_id}: duplicate target")
        reviewed_by_key[target.target_key] = target

    changes_by_key: dict[tuple[str, str, str], CatalogChangeSummary] = {}
    for change in report.changes:
        if change.target_key in changes_by_key:
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                "duplicate change"
            )
        changes_by_key[change.target_key] = change
        reviewed_target = reviewed_by_key.get((change.target_type, change.target_id))
        if reviewed_target is None:
            issues.append(
                f"{change.target_type}:{change.target_id}: target is not declared "
                "in reviewed_targets"
            )
        elif reviewed_target.resulting_graph_role == "linked_dependency":
            issues.append(
                f"{change.target_type}:{change.target_id}: linked_dependency "
                "reviewed target cannot own changes"
            )

    coverage_by_key: dict[tuple[str, str, str], CatalogFieldCoverage] = {}
    for coverage in report.field_coverage:
        if coverage.target_key in coverage_by_key:
            issues.append(
                f"{coverage.target_type}:{coverage.target_id} "
                f"{coverage.field_path}: duplicate field coverage"
            )
        coverage_by_key[coverage.target_key] = coverage
        if coverage.status == "unresolved" and not coverage.notes:
            issues.append(
                f"{coverage.target_type}:{coverage.target_id} "
                f"{coverage.field_path}: unresolved field coverage requires notes"
            )
        if coverage.status == "changed" and coverage.target_key not in changes_by_key:
            issues.append(
                f"{coverage.target_type}:{coverage.target_id} "
                f"{coverage.field_path}: changed field coverage has no matching change"
            )
        if (coverage.target_type, coverage.target_id) not in reviewed_by_key:
            issues.append(
                f"{coverage.target_type}:{coverage.target_id}: target is not declared "
                "in reviewed_targets"
            )

    for change in report.changes:
        coverage = coverage_by_key.get(change.target_key)
        if coverage is None:
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                "missing changed field coverage"
            )
        elif coverage.status != "changed":
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                "changed field must use status=changed"
            )

    evidence_by_id: dict[str, CatalogEvidenceItem] = {}
    evidence_by_key: dict[tuple[str, str, str], list[CatalogEvidenceItem]] = {}
    for evidence in report.evidence:
        if evidence.evidence_id in evidence_by_id:
            issues.append(f"{evidence.evidence_id}: duplicate evidence_id")
        evidence_by_id[evidence.evidence_id] = evidence
        evidence_by_key.setdefault(evidence.target_key, []).append(evidence)
        if (evidence.target_type, evidence.target_id) not in reviewed_by_key:
            issues.append(
                f"{evidence.target_type}:{evidence.target_id}: evidence target is "
                "not declared in reviewed_targets"
            )

    family_ids = [item.family_id for item in report.review_evidence_envelope]
    if len(family_ids) != len(set(family_ids)):
        issues.append("review_evidence_envelope contains a duplicate family")

    evidence_urls = {item.source_url for item in report.evidence}
    for family in report.review_evidence_envelope:
        for source_url in family.source_urls:
            if source_url not in evidence_urls:
                issues.append(
                    f"{family.family_id}: review source URL is not referenced "
                    "by evidence"
                )

    for assessment in report.entity_scope_assessments:
        if assessment.graph_impact == "regional_followup" and (
            assessment.disposition not in BACKLOG_REQUIRED_SCOPE_DISPOSITIONS
            or assessment.backlog_ref is None
        ):
            issues.append(
                f"{assessment.candidate_id}: regional_followup requires "
                "deferred or unresolved backlog scope"
            )
        if require_bounded_review_inventory and assessment.graph_impact is None:
            issues.append(
                f"{assessment.candidate_id}: bounded review inventory requires "
                "graph_impact"
            )

    _validate_boundary_assessments(
        report,
        reviewed_by_key,
        evidence_by_id,
        issues,
        require_current_destination_policy=require_current_destination_policy,
    )
    _validate_geometry_assessments(
        report,
        reviewed_by_key,
        evidence_by_id,
        issues,
    )
    _validate_entity_scope_assessments(
        report,
        reviewed_by_key,
        changes_by_key,
        evidence_by_id,
        issues,
        require_current_destination_policy=require_current_destination_policy,
    )

    unresolved_keys = {
        key
        for key, coverage in coverage_by_key.items()
        if coverage.status == "unresolved"
    }
    boundary_evidence_ids = {
        evidence_id
        for assessment in report.destination_boundary_assessments
        for item in (*assessment.gates, *assessment.identity_signals)
        for evidence_id in item.evidence_refs
    }
    scope_evidence_ids = {
        evidence_id
        for assessment in report.entity_scope_assessments
        for evidence_id in assessment.evidence_refs
    }
    geometry_evidence_ids = {
        evidence_id
        for assessment in report.weather_request_geometry_assessments
        for evidence_id in assessment.evidence_refs
    }
    for evidence in report.evidence:
        if (
            evidence.target_key not in changes_by_key
            and evidence.target_key not in unresolved_keys
            and evidence.evidence_id not in boundary_evidence_ids
            and evidence.evidence_id not in scope_evidence_ids
            and evidence.evidence_id not in geometry_evidence_ids
        ):
            issues.append(
                f"{evidence.target_type}:{evidence.target_id} "
                f"{evidence.field_path}: evidence has no matching change"
            )

    for change in report.changes:
        matching_evidence = evidence_by_key.get(change.target_key, [])
        if (
            report.report_schema_version == 3
            and change.target_type == "lift_pass_product"
            and change.field_path == "validity_windows"
            and isinstance(change.after, list)
            and change.after
            and not any(
                evidence.source_type == "official" for evidence in matching_evidence
            )
        ):
            issues.append(
                f"lift_pass_product:{change.target_id} validity_windows: "
                "non-empty change requires official root-path evidence"
            )
        if change.ranking_relevant and not matching_evidence:
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                "missing evidence for ranking-relevant change"
            )
        if change.trust_status in SOURCE_BACKED_TRUST_STATUSES:
            if not matching_evidence:
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    f"missing evidence for {change.trust_status}"
                )
            elif not any(
                evidence.source_type in VERIFICATION_SOURCE_TYPES
                for evidence in matching_evidence
            ):
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    f"source cannot verify {change.trust_status}"
                )
        for evidence in matching_evidence:
            if (
                not json_values_equal(evidence.source_value, change.after)
                and not evidence.normalization_note
            ):
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    "normalization_note is required when source_value differs "
                    "from after"
                )

    report_paths_by_target: dict[tuple[str, str], set[str]] = {}
    for item in (*report.changes, *report.evidence):
        report_paths_by_target.setdefault(
            (item.target_type, item.target_id), set()
        ).add(item.field_path)
    coverage_paths_by_target: dict[tuple[str, str], set[str]] = {}
    for coverage in report.field_coverage:
        coverage_paths_by_target.setdefault(
            (coverage.target_type, coverage.target_id), set()
        ).add(coverage.field_path)
    for target_key, target in reviewed_by_key.items():
        expected_paths = set(target.canonical_review_paths)
        nested_paths = {
            field_path
            for field_path in report_paths_by_target.get(target_key, set())
            if field_path not in CANONICAL_FIELD_PATHS[target.target_type]
        }
        expected_paths.update(nested_paths)
        actual_paths = coverage_paths_by_target.get(target_key, set())
        for field_path in sorted(expected_paths - actual_paths):
            issues.append(
                f"{target.target_type}:{target.target_id} {field_path}: "
                "missing field coverage"
            )
        for field_path in sorted(actual_paths - expected_paths):
            issues.append(
                f"{target.target_type}:{target.target_id} {field_path}: "
                "field coverage is outside declared review scope"
            )

    added_destinations = {
        change.target_id
        for change in report.changes
        if change.target_type == "stay_destination"
        and change.field_path == "stay_destination_id"
        and change.before is None
        and change.after is not None
    }
    passing_boundaries = {
        item.candidate_id
        for item in report.destination_boundary_assessments
        if item.is_passing
    }
    for destination_id in sorted(added_destinations):
        if destination_id not in set(report.boundary_decision_targets):
            issues.append(
                f"{destination_id}: new stay destination requires a boundary target"
            )
        elif destination_id not in passing_boundaries:
            issues.append(
                f"{destination_id}: new stay destination requires a passing "
                "boundary assessment"
            )

    if issues:
        raise CatalogValidationError(sorted(set(issues)))


def _validate_ski_area_boundary_assessment(
    assessment: CatalogEntityScopeAssessment,
    evidence_by_id: Mapping[str, CatalogEvidenceItem],
    issues: list[str],
) -> None:
    boundary = assessment.ski_area_boundary
    if boundary is None:
        return

    candidate_id = assessment.candidate_id
    signals = set(assessment.signals)
    if assessment.candidate_kind != "ski_area":
        issues.append(
            f"{candidate_id}: ski_area_boundary is only valid for ski-area candidates"
        )
        return

    if not set(boundary.evidence_refs).issubset(assessment.evidence_refs):
        issues.append(
            f"{candidate_id}: ski-area boundary evidence must also appear in "
            "scope evidence_refs"
        )

    if boundary.has_coordination_metadata and assessment.disposition not in {
        "represented",
        "add_entity",
    }:
        issues.append(
            f"{candidate_id}: coordination metadata is only valid on a "
            "represented or added parent"
        )

    if assessment.disposition == "not_separate":
        target_ids = {target.target_id for target in assessment.target_refs}
        if (
            boundary.parent_ski_area_id is None
            or boundary.parent_ski_area_id not in target_ids
        ):
            issues.append(
                f"{candidate_id}: not_separate ski area requires its parent "
                "as the catalog target"
            )
        if boundary.separation_value != "redundant":
            issues.append(
                f"{candidate_id}: not_separate ski area requires redundant "
                "separation value"
            )
        return

    if assessment.disposition not in {"represented", "add_entity"}:
        return

    if boundary.terrain_scope != "complete":
        issues.append(
            f"{candidate_id}: separate ski area requires complete terrain scope"
        )
    if not SKI_AREA_TERRAIN_IDENTITY_SIGNALS.intersection(signals):
        issues.append(
            f"{candidate_id}: separate ski area requires complete terrain "
            "identity evidence"
        )
    if boundary.separation_value != "material":
        issues.append(
            f"{candidate_id}: separate ski area requires material separation value"
        )
    if boundary.connectivity_to_parent == "unknown":
        issues.append(
            f"{candidate_id}: separate ski area requires resolved parent connectivity"
        )

    if boundary.operational_scope == "coordinated":
        for required_signal in sorted(SKI_AREA_COORDINATED_OPERATION_SIGNALS):
            if required_signal not in signals:
                issues.append(
                    f"{candidate_id}: coordinated ski area requires signal "
                    f"{required_signal}"
                )
        if boundary.pass_scope not in {"full_local", "shared_only"}:
            issues.append(
                f"{candidate_id}: coordinated ski area requires "
                "pass_scope=full_local or shared_only"
            )
        if len(boundary.component_candidate_ids) < 2:
            issues.append(
                f"{candidate_id}: coordinated ski area requires at least two "
                "component candidates"
            )
        if not boundary.coordination_evidence_refs:
            issues.append(
                f"{candidate_id}: coordinated ski area requires coordination "
                "evidence refs"
            )
        families_by_name = {
            family.family: family for family in boundary.coordination_evidence_families
        }
        for family_name in SKI_AREA_COORDINATED_EVIDENCE_FAMILY_ORDER:
            family = families_by_name.get(family_name)
            if family is None:
                issues.append(
                    f"{candidate_id}: coordinated ski area requires evidence "
                    f"family {family_name}"
                )
                continue
            expected_components = set(boundary.component_candidate_ids)
            covered_components = set(family.covered_component_candidate_ids)
            if covered_components != expected_components:
                missing = ", ".join(sorted(expected_components - covered_components))
                extra = ", ".join(sorted(covered_components - expected_components))
                issues.append(
                    f"{candidate_id}: evidence family {family_name} must cover "
                    "exactly coordinated components; "
                    f"missing={missing or 'none'}; extra={extra or 'none'}"
                )
            for evidence_ref in family.evidence_refs:
                evidence = evidence_by_id.get(evidence_ref)
                if evidence is None or evidence.source_type != "official":
                    issues.append(
                        f"{candidate_id}: evidence family {family_name} requires "
                        f"official evidence {evidence_ref}"
                    )
        return

    independent_operations = boundary.operational_scope == "independent" and bool(
        SKI_AREA_OPERATION_OWNER_SIGNALS.intersection(signals)
    )
    independent_weather = boundary.weather_scope == "independent" and bool(
        SKI_AREA_WEATHER_OWNER_SIGNALS.intersection(signals)
    )
    independent_pass = boundary.pass_scope == "full_local" and bool(
        SKI_AREA_PASS_OWNER_SIGNALS.intersection(signals)
    )
    owner_categories = sum(
        (independent_operations, independent_weather, independent_pass)
    )
    if owner_categories == 0:
        issues.append(
            f"{candidate_id}: separate ski area requires independent operations, "
            "weather, or full local pass evidence"
        )
        return

    if boundary.connectivity_to_parent == "connected" and (
        owner_categories < 2 or not (independent_operations or independent_weather)
    ):
        issues.append(
            f"{candidate_id}: connected ski area requires two independent owner "
            "categories, including operations or weather"
        )


def _coordinated_child_independently_satisfies_separate_ski_area_gates(
    assessment: CatalogEntityScopeAssessment,
) -> bool:
    boundary = assessment.ski_area_boundary
    if boundary is None or boundary.terrain_scope != "complete":
        return False

    signals = set(assessment.signals)
    if not SKI_AREA_TERRAIN_IDENTITY_SIGNALS.intersection(signals):
        return False

    independent_operations = bool(
        SKI_AREA_OPERATION_OWNER_SIGNALS.intersection(signals)
    )
    independent_weather = bool(SKI_AREA_WEATHER_OWNER_SIGNALS.intersection(signals))
    independent_pass = boundary.pass_scope == "full_local" and bool(
        SKI_AREA_PASS_OWNER_SIGNALS.intersection(signals)
    )
    owner_categories = sum(
        (independent_operations, independent_weather, independent_pass)
    )

    if boundary.connectivity_to_parent == "connected":
        return owner_categories >= 2 and (independent_operations or independent_weather)
    if boundary.connectivity_to_parent in {"transfer_required", "disconnected"}:
        return owner_categories >= 1
    return False


def _validate_coordinated_ski_area_components(
    assessments: list[CatalogEntityScopeAssessment],
    issues: list[str],
) -> None:
    by_candidate_id = {
        assessment.candidate_id: assessment for assessment in assessments
    }
    component_parent_by_id: dict[str, str] = {}
    coordinated_parent_by_target_id: dict[str, CatalogEntityScopeAssessment] = {}

    for parent in assessments:
        boundary = parent.ski_area_boundary
        if boundary is None or boundary.operational_scope != "coordinated":
            continue
        if parent.disposition not in {"represented", "add_entity"}:
            continue
        parent_target_ids = [target.target_id for target in parent.target_refs]
        if len(parent_target_ids) != 1:
            issues.append(
                f"{parent.candidate_id}: coordinated ski area must target exactly "
                "one catalog ski area"
            )
            continue
        parent_target_id = parent_target_ids[0]
        existing_parent = coordinated_parent_by_target_id.get(parent_target_id)
        if existing_parent is not None:
            issues.append(
                f"ski_area:{parent_target_id}: coordinated parent is represented "
                "by multiple candidates"
            )
            continue
        coordinated_parent_by_target_id[parent_target_id] = parent
        for component_id in boundary.component_candidate_ids:
            if component_id == parent.candidate_id:
                issues.append(
                    f"{parent.candidate_id}: coordinated parent cannot list itself "
                    "as a component"
                )
                continue
            prior_parent = component_parent_by_id.setdefault(
                component_id, parent_target_id
            )
            if prior_parent != parent_target_id:
                issues.append(
                    f"coordinated component {component_id} belongs to multiple parents"
                )
            component = by_candidate_id.get(component_id)
            if component is None:
                issues.append(
                    f"{parent.candidate_id}: coordinated component {component_id} "
                    "has no scope assessment"
                )
                continue
            component_boundary = component.ski_area_boundary
            if component.candidate_kind != "ski_area":
                issues.append(
                    f"{component_id}: coordinated component must be a ski-area "
                    "candidate"
                )
            if component.disposition != "not_separate":
                issues.append(
                    f"{component_id}: coordinated component must use "
                    "disposition=not_separate"
                )
            if component_boundary is None:
                continue
            if component_boundary.operational_scope != "coordinated":
                issues.append(
                    f"{component_id}: coordinated component must use "
                    "operational_scope=coordinated"
                )
            if component_boundary.parent_ski_area_id != parent_target_id:
                issues.append(
                    f"{component_id}: coordinated component must name coordinated "
                    f"parent {parent_target_id}"
                )
            if component_boundary.weather_scope == "independent":
                issues.append(
                    f"{component_id}: coordinated component cannot retain "
                    "independent weather scope"
                )
            if {target.target_id for target in component.target_refs} != {
                parent_target_id
            }:
                issues.append(
                    f"{component_id}: coordinated component must target coordinated "
                    f"parent ski_area:{parent_target_id}"
                )

    for child in assessments:
        boundary = child.ski_area_boundary
        if (
            child.disposition != "not_separate"
            or boundary is None
            or boundary.operational_scope != "coordinated"
            or boundary.parent_ski_area_id is None
        ):
            continue
        if _coordinated_child_independently_satisfies_separate_ski_area_gates(child):
            issues.append(
                f"{child.candidate_id}: coordinated component independently "
                "satisfies ordinary separate-ski-area evidence gates"
            )
        parent = coordinated_parent_by_target_id.get(boundary.parent_ski_area_id)
        if parent is None:
            issues.append(
                f"{child.candidate_id}: coordinated child has no represented or "
                "added coordinated parent"
            )
            continue
        parent_boundary = parent.ski_area_boundary
        assert parent_boundary is not None
        if child.candidate_id not in parent_boundary.component_candidate_ids:
            issues.append(
                f"coordinated child {child.candidate_id} is not listed by parent "
                f"{boundary.parent_ski_area_id}"
            )


def _validate_entity_scope_assessments(
    report: CatalogCurationReport,
    reviewed_by_key: Mapping[tuple[str, str], CatalogReviewedTarget],
    changes_by_key: Mapping[tuple[str, str, str], CatalogChangeSummary],
    evidence_by_id: Mapping[str, CatalogEvidenceItem],
    issues: list[str],
    *,
    require_current_destination_policy: bool = False,
) -> None:
    assessments = report.entity_scope_assessments
    if report.report_schema_version >= 2 and not assessments:
        issues.append(
            f"schema version {report.report_schema_version} requires "
            "entity_scope_assessments"
        )
        return

    candidate_ids = [assessment.candidate_id for assessment in assessments]
    if len(candidate_ids) != len(set(candidate_ids)):
        issues.append("entity_scope_assessments contain a duplicate scope candidate")

    referenced_target_keys: set[tuple[str, str]] = set()
    passing_destination_boundaries = {
        assessment.candidate_id
        for assessment in report.destination_boundary_assessments
        if assessment.is_passing
    }
    for assessment in assessments:
        boundary = assessment.ski_area_boundary
        if (
            report.report_schema_version < 3
            and boundary is not None
            and (
                boundary.operational_scope == "coordinated"
                or boundary.has_coordination_metadata
            )
        ):
            issues.append(
                f"{assessment.candidate_id}: coordinated ski area requires "
                "report schema version 3"
            )
        if report.report_schema_version >= 2:
            if assessment.disposition in BACKLOG_REQUIRED_SCOPE_DISPOSITIONS:
                if assessment.backlog_ref is None:
                    issues.append(
                        f"{assessment.candidate_id}: {assessment.disposition} "
                        "requires backlog_ref"
                    )
            elif assessment.backlog_ref is not None:
                issues.append(
                    f"{assessment.candidate_id}: {assessment.disposition} "
                    "forbids backlog_ref"
                )
        referenced_evidence = [
            evidence_by_id[evidence_id]
            for evidence_id in assessment.evidence_refs
            if evidence_id in evidence_by_id
        ]
        for evidence_id in sorted(set(assessment.evidence_refs) - set(evidence_by_id)):
            issues.append(
                f"{assessment.candidate_id}: unknown scope evidence {evidence_id}"
            )
        if (
            report.report_schema_version == 3
            and assessment.candidate_kind == "ski_area"
            and assessment.ski_area_boundary is None
        ):
            issues.append(
                f"{assessment.candidate_id}: schema version 3 ski-area "
                "assessment requires boundary contract"
            )
        if report.report_schema_version == 3:
            _validate_ski_area_boundary_assessment(
                assessment,
                evidence_by_id,
                issues,
            )
        for target_ref in assessment.target_refs:
            referenced_target_keys.add(target_ref.target_key)
            if target_ref.target_key not in reviewed_by_key:
                issues.append(
                    f"{target_ref.target_type}:{target_ref.target_id}: "
                    "scope target is not reviewed"
                )
            if assessment.disposition == "add_entity":
                identity_change = changes_by_key.get(
                    (
                        target_ref.target_type,
                        target_ref.target_id,
                        SCOPE_ID_FIELD_PATHS[target_ref.target_type],
                    )
                )
                if (
                    identity_change is None
                    or identity_change.before is not None
                    or not json_values_equal(
                        identity_change.after, target_ref.target_id
                    )
                ):
                    issues.append(
                        f"{target_ref.target_type}:{target_ref.target_id}: "
                        "add_entity requires a matching identity-field "
                        "creation change"
                    )
        if assessment.disposition in SOURCE_BACKED_SCOPE_DISPOSITIONS and not any(
            evidence.source_type in VERIFICATION_SOURCE_TYPES
            for evidence in referenced_evidence
        ):
            issues.append(
                f"{assessment.candidate_id}: {assessment.disposition} requires "
                "verification-capable evidence"
            )
        if (
            assessment.candidate_kind == "ski_area"
            and assessment.disposition == "add_entity"
            and report.report_schema_version < 3
            and not LEGACY_INDEPENDENT_SKI_AREA_SIGNALS.intersection(assessment.signals)
        ):
            issues.append(
                f"{assessment.candidate_id}: new ski area requires an "
                "independent-owner signal"
            )
        if (
            require_current_destination_policy
            and assessment.candidate_kind == "stay_destination"
            and assessment.disposition in {"represented", "add_entity"}
            and not all(
                target_ref.target_id in passing_destination_boundaries
                for target_ref in assessment.target_refs
            )
        ):
            issues.append(
                f"{assessment.candidate_id}: current stay destination requires "
                "a passing boundary assessment"
            )
        elif (
            assessment.candidate_kind == "stay_destination"
            and assessment.disposition == "add_entity"
            and not all(
                target_ref.target_id in passing_destination_boundaries
                for target_ref in assessment.target_refs
            )
        ):
            issues.append(
                f"{assessment.candidate_id}: new stay destination requires a "
                "passing boundary assessment"
            )
        if (
            assessment.candidate_kind == "terrain_domain"
            and assessment.disposition == "add_entity"
            and "ski_connected_terrain" not in assessment.signals
        ):
            issues.append(
                f"{assessment.candidate_id}: new terrain domain requires "
                "ski_connected_terrain"
            )

    if report.report_schema_version == 3:
        _validate_coordinated_ski_area_components(assessments, issues)

    if report.report_schema_version < 2:
        return
    for target_key, target in reviewed_by_key.items():
        if (
            target.scope == "full"
            and target.target_type in GRAPH_SCOPE_TARGET_TYPES
            and target_key not in referenced_target_keys
        ):
            issues.append(
                f"{target.target_type}:{target.target_id}: full graph target is "
                "missing from entity scope assessments"
            )


def _validate_boundary_assessments(
    report: CatalogCurationReport,
    reviewed_by_key: Mapping[tuple[str, str], CatalogReviewedTarget],
    evidence_by_id: Mapping[str, CatalogEvidenceItem],
    issues: list[str],
    *,
    require_current_destination_policy: bool = False,
) -> None:
    declared = set(report.boundary_decision_targets)
    if len(declared) != len(report.boundary_decision_targets):
        issues.append("boundary_decision_targets must be unique")
    assessments = {
        assessment.candidate_id: assessment
        for assessment in report.destination_boundary_assessments
    }
    if len(assessments) != len(report.destination_boundary_assessments):
        issues.append("destination boundary assessments must be unique")
    for candidate_id in sorted(declared):
        if ("stay_destination", candidate_id) not in reviewed_by_key:
            issues.append(
                f"stay_destination:{candidate_id}: boundary target is not reviewed"
            )
        if candidate_id not in assessments:
            issues.append(f"{candidate_id}: missing destination boundary assessment")
    for candidate_id in sorted(set(assessments) - declared):
        issues.append(f"{candidate_id}: undeclared destination boundary assessment")
    for assessment in assessments.values():
        if require_current_destination_policy and not assessment.uses_current_policy:
            issues.append(
                f"{assessment.candidate_id}: destination boundary assessment "
                "must use current stay-market policy gates"
            )
        if (
            require_current_destination_policy
            and not assessment.has_current_ownership_signal_assessment
        ):
            issues.append(
                f"{assessment.candidate_id}: current destination boundary "
                "assessment requires a direct stay-market ownership signal "
                "assessment"
            )
        if require_current_destination_policy and assessment.is_passing:
            ownership_evidence_ids = {
                evidence_id
                for signal in assessment.identity_signals
                if signal.status == "pass"
                and signal.signal_type in CURRENT_STAY_MARKET_IDENTITY_SIGNALS
                for evidence_id in signal.evidence_refs
            }
            if not any(
                evidence_by_id[evidence_id].source_type == "official"
                for evidence_id in ownership_evidence_ids
                if evidence_id in evidence_by_id
            ):
                issues.append(
                    f"{assessment.candidate_id}: passing stay-market ownership "
                    "requires official evidence"
                )
        for item in (*assessment.gates, *assessment.identity_signals):
            referenced = [
                evidence_by_id[evidence_id]
                for evidence_id in item.evidence_refs
                if evidence_id in evidence_by_id
            ]
            missing = set(item.evidence_refs) - set(evidence_by_id)
            for evidence_id in sorted(missing):
                issues.append(
                    f"{assessment.candidate_id}: unknown boundary evidence "
                    f"{evidence_id}"
                )
            for evidence in referenced:
                if assessment.candidate_id not in evidence.boundary_target_ids:
                    issues.append(
                        f"{assessment.candidate_id}: evidence {evidence.evidence_id} "
                        f"must include {assessment.candidate_id} in "
                        "boundary_target_ids"
                    )
            if item.status == "pass" and not any(
                evidence.source_type in VERIFICATION_SOURCE_TYPES
                for evidence in referenced
            ):
                issues.append(
                    f"{assessment.candidate_id}: passing boundary item requires "
                    "source-backed evidence"
                )


def _validate_geometry_assessments(
    report: CatalogCurationReport,
    reviewed_by_key: Mapping[tuple[str, str], CatalogReviewedTarget],
    evidence_by_id: Mapping[str, CatalogEvidenceItem],
    issues: list[str],
) -> None:
    declared = set(report.weather_request_geometry_targets)
    if len(declared) != len(report.weather_request_geometry_targets):
        issues.append("weather_request_geometry_targets must be unique")
    assessments = {
        assessment.ski_area_id: assessment
        for assessment in report.weather_request_geometry_assessments
    }
    if len(assessments) != len(report.weather_request_geometry_assessments):
        issues.append("weather request geometry assessments must be unique")
    for ski_area_id in sorted(declared):
        if ("ski_area", ski_area_id) not in reviewed_by_key:
            issues.append(f"ski_area:{ski_area_id}: geometry target is not reviewed")
        if ski_area_id not in assessments:
            issues.append(f"{ski_area_id}: missing weather request geometry assessment")
    for ski_area_id in sorted(set(assessments) - declared):
        issues.append(f"{ski_area_id}: undeclared weather request geometry assessment")
    for assessment in report.weather_request_geometry_assessments:
        if report.report_schema_version < 3:
            continue
        _validate_weather_geometry_derivation(
            assessment,
            evidence_by_id,
            issues,
        )


def _validate_weather_geometry_derivation(
    assessment: CatalogWeatherRequestGeometryAssessment,
    evidence_by_id: Mapping[str, CatalogEvidenceItem],
    issues: list[str],
) -> None:
    ski_area_id = assessment.ski_area_id
    missing_evidence = set(assessment.evidence_refs) - set(evidence_by_id)
    for evidence_id in sorted(missing_evidence):
        issues.append(f"{ski_area_id}: unknown weather geometry evidence {evidence_id}")
    for evidence_id in assessment.evidence_refs:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is not None and evidence.target_key[:2] != (
            "ski_area",
            ski_area_id,
        ):
            issues.append(
                f"{ski_area_id}: weather geometry evidence {evidence_id} "
                "must target the assessed ski area"
            )
    _validate_coordinate_derivation_attempts(
        assessment,
        evidence_by_id,
        issues,
    )

    if assessment.geometry_completeness is None:
        issues.append(f"{ski_area_id}: weather geometry requires geometry_completeness")
    if assessment.derivation_status is None:
        issues.append(f"{ski_area_id}: weather geometry requires derivation_status")

    if (
        assessment.before is None
        and assessment.after.weather_sampling_status == "active"
    ):
        if assessment.post_merge_handoff != "scheduled_completion":
            issues.append(
                f"{ski_area_id}: new active weather geometry requires "
                "post_merge_handoff=scheduled_completion"
            )
    elif assessment.request_geometry_changed:
        required_handoff = (
            "force_refetch_and_rebuild_climatology"
            if assessment.after.weather_sampling_status == "active"
            else "force_refetch_and_rebuild_after_activation"
        )
        if assessment.post_merge_handoff != required_handoff:
            issues.append(
                f"{ski_area_id}: retained weather geometry changes require "
                f"post_merge_handoff={required_handoff}"
            )

    if assessment.after.weather_sampling_status == "deferred":
        if assessment.derivation_status != "deferred":
            issues.append(
                f"{ski_area_id}: deferred weather sampling requires "
                "derivation_status=deferred"
            )
        if not assessment.activation_prerequisite:
            issues.append(
                f"{ski_area_id}: deferred weather sampling requires "
                "activation_prerequisite"
            )
        return

    if assessment.activation_prerequisite is not None:
        issues.append(
            f"{ski_area_id}: active weather sampling cannot retain an "
            "activation_prerequisite"
        )
    if assessment.coordinate_derivation_method is None:
        issues.append(
            f"{ski_area_id}: active weather sampling requires "
            "coordinate_derivation_method"
        )
    if assessment.elevation_derivation_method is None:
        issues.append(
            f"{ski_area_id}: active weather sampling requires "
            "elevation_derivation_method"
        )
    if not assessment.evidence_refs:
        issues.append(
            f"{ski_area_id}: active weather sampling requires source evidence"
        )

    coordinate_method = assessment.coordinate_derivation_method
    completeness = assessment.geometry_completeness
    if coordinate_method == "official_terrain_medoid" and completeness != "complete":
        issues.append(
            f"{ski_area_id}: official terrain medoid requires complete geometry"
        )
    if coordinate_method == "osm_terrain_medoid" and completeness not in {
        "complete",
        "sufficient",
    }:
        issues.append(
            f"{ski_area_id}: OSM terrain medoid requires complete or sufficient "
            "geometry"
        )
    if (
        coordinate_method == "structured_lift_inventory_medoid"
        and completeness != "complete"
    ):
        issues.append(
            f"{ski_area_id}: structured lift inventory medoid requires complete "
            "geometry"
        )

    adjusted_methods = {
        "osm_terrain_medoid",
        "official_central_on_mountain_point",
        "structured_lift_inventory_medoid",
        "open_data_lift_inventory_range",
        "specialist_conflict_tiebreak",
    }
    methods = {
        assessment.coordinate_derivation_method,
        assessment.elevation_derivation_method,
    }
    expected_status = (
        "verified_with_adjustment" if methods & adjusted_methods else "verified"
    )
    allowed_statuses = {expected_status, None}
    if "preserved_existing" in methods:
        allowed_statuses.add("verified_with_adjustment")
    if assessment.derivation_status not in allowed_statuses:
        issues.append(
            f"{ski_area_id}: derivation_status must be {expected_status} for the "
            "selected methods"
        )


def _validate_coordinate_derivation_attempts(
    assessment: CatalogWeatherRequestGeometryAssessment,
    evidence_by_id: Mapping[str, CatalogEvidenceItem],
    issues: list[str],
) -> None:
    ski_area_id = assessment.ski_area_id
    attempts = assessment.coordinate_derivation_attempts
    methods = [attempt.method for attempt in attempts]
    if len(methods) != len(set(methods)):
        issues.append(f"{ski_area_id}: coordinate derivation attempts must be unique")

    hierarchy_order = {
        method: index for index, method in enumerate(COORDINATE_DERIVATION_HIERARCHY)
    }
    hierarchy_methods = [method for method in methods if method in hierarchy_order]
    if hierarchy_methods != sorted(
        hierarchy_methods,
        key=hierarchy_order.__getitem__,
    ):
        issues.append(
            f"{ski_area_id}: coordinate derivation attempts must follow the "
            "source hierarchy"
        )

    assessment_evidence_refs = set(assessment.evidence_refs)
    for attempt in attempts:
        for evidence_id in attempt.evidence_refs:
            if evidence_id not in assessment_evidence_refs:
                issues.append(
                    f"{ski_area_id}: coordinate attempt evidence {evidence_id} "
                    "must also appear in weather geometry evidence_refs"
                )
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                issues.append(
                    f"{ski_area_id}: unknown coordinate attempt evidence {evidence_id}"
                )
            elif evidence.target_key[:2] != ("ski_area", ski_area_id):
                issues.append(
                    f"{ski_area_id}: coordinate attempt evidence {evidence_id} "
                    "must target the assessed ski area"
                )

    if assessment.after.weather_sampling_status != "deferred":
        return

    selected_method = assessment.coordinate_derivation_method
    if selected_method == "preserved_existing":
        return
    if selected_method is None:
        required_methods = list(COORDINATE_DERIVATION_HIERARCHY)
        selected_attempt_method = None
    else:
        selected_index = hierarchy_order[selected_method]
        required_methods = list(COORDINATE_DERIVATION_HIERARCHY[: selected_index + 1])
        selected_attempt_method = selected_method

    if not attempts:
        issues.append(
            f"{ski_area_id}: deferred weather sampling requires documented "
            "coordinate attempts"
        )
        return

    missing_methods = [method for method in required_methods if method not in methods]
    if missing_methods:
        issues.append(
            f"{ski_area_id}: missing coordinate derivation attempts: "
            f"{', '.join(missing_methods)}"
        )

    attempts_by_method = {attempt.method: attempt for attempt in attempts}
    selected_attempt_methods = [
        attempt.method for attempt in attempts if attempt.outcome == "selected"
    ]
    expected_selected_methods = (
        [] if selected_attempt_method is None else [selected_attempt_method]
    )
    if selected_attempt_methods != expected_selected_methods:
        expected = selected_attempt_method or "none"
        issues.append(
            f"{ski_area_id}: selected coordinate attempt must match {expected}"
        )
    for method in required_methods:
        attempt = attempts_by_method.get(method)
        if attempt is None:
            continue
        expected_outcomes = (
            {"selected"}
            if method == selected_attempt_method
            else {"rejected", "unavailable"}
        )
        if attempt.outcome not in expected_outcomes:
            allowed = " or ".join(sorted(expected_outcomes))
            issues.append(
                f"{ski_area_id}: {method} coordinate attempt must be {allowed}"
            )


def _markdown_cell(value: str) -> str:
    return " ".join(line.strip() for line in value.splitlines()).replace("|", "\\|")


def _code_cell(value: str) -> str:
    return f"`{_markdown_cell(value)}`"


def _render_coordination_evidence_families(
    boundary: CatalogSkiAreaBoundaryAssessment,
) -> str:
    families_by_name = {
        family.family: family for family in boundary.coordination_evidence_families
    }
    rendered_families: list[str] = []
    for family_name in SKI_AREA_COORDINATED_EVIDENCE_FAMILY_ORDER:
        family = families_by_name.get(family_name)
        if family is None:
            continue
        components = ", ".join(
            _code_cell(component_id)
            for component_id in family.covered_component_candidate_ids
        )
        evidence = ", ".join(
            _code_cell(evidence_id) for evidence_id in family.evidence_refs
        )
        rendered_families.append(
            f"{_code_cell(family_name)}: components {components}; evidence {evidence}"
        )
    return "<br>".join(rendered_families)


def _json_cell(value: JsonValue) -> str:
    return _code_cell(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _markdown_link(label: str, url: str) -> str:
    escaped_label = _markdown_cell(label).replace("[", "\\[").replace("]", "\\]")
    return f"[{escaped_label}]({quote(url, safe=MARKDOWN_LINK_URL_SAFE_CHARS)})"


def validate_catalog_resulting_graph(
    report: CatalogCurationReport,
    catalog: CatalogSnapshot,
    *,
    require: bool = False,
) -> None:
    validate_catalog_curation_report(
        report,
        require_resulting_graph=require,
    )
    graph = report.resulting_graph
    if graph is None:
        return
    known_destination_ids = {
        destination.stay_destination_id for destination in catalog.stay_destinations
    }
    issues = [
        f"unknown focus stay destination {destination_id}"
        for destination_id in graph.focus_stay_destination_ids
        if destination_id not in known_destination_ids
    ]
    if issues:
        raise CatalogValidationError(issues)
    required_destination_ids = _required_resulting_graph_destination_ids(
        report,
        catalog,
    )
    issues.extend(
        f"missing required focus stay destination {destination_id}"
        for destination_id in sorted(
            required_destination_ids - set(graph.focus_stay_destination_ids)
        )
    )
    if issues:
        raise CatalogValidationError(issues)


@dataclass(frozen=True)
class CatalogResultingGraphScope:
    destination_ids: frozenset[str]
    region_ids: frozenset[str]
    base_ids: frozenset[str]
    access_ids: frozenset[str]
    area_ids: frozenset[str]
    domain_ids: frozenset[str]
    pass_ids: frozenset[str]


def catalog_resulting_graph_scope(
    catalog: CatalogSnapshot,
    focus_destination_ids: set[str] | frozenset[str],
) -> CatalogResultingGraphScope:
    """Return the deterministic entity closure rendered for focused destinations."""
    destinations_by_id = {
        destination.stay_destination_id: destination
        for destination in catalog.stay_destinations
    }
    passes_by_id = {
        product.lift_pass_product_id: product for product in catalog.lift_pass_products
    }
    domains_by_id = {
        domain.terrain_domain_id: domain for domain in catalog.terrain_domains
    }

    destination_ids = frozenset(focus_destination_ids)
    region_ids = frozenset(
        destinations_by_id[destination_id].trip_market_region_id
        for destination_id in destination_ids
    )
    base_ids = frozenset(
        base.stay_base_id
        for base in catalog.stay_bases
        if base.stay_destination_id in destination_ids
    )
    access_ids = frozenset(
        access.ski_area_access_id
        for access in catalog.ski_area_access
        if access.stay_base_id in base_ids
    )
    area_ids = {
        access.ski_area_id
        for access in catalog.ski_area_access
        if access.ski_area_access_id in access_ids
    }
    pass_ids = frozenset(
        product.lift_pass_product_id
        for product in catalog.lift_pass_products
        if destination_ids
        & (
            set(product.available_from_stay_destination_ids)
            | set(product.default_for_stay_destination_ids)
        )
    )
    domain_ids = {
        domain_id
        for pass_id in pass_ids
        for domain_id in passes_by_id[pass_id].terrain_domain_ids
    }
    area_ids.update(
        area_id
        for pass_id in pass_ids
        for area_id in passes_by_id[pass_id].valid_ski_area_ids
    )

    while True:
        expanded_domain_ids = domain_ids | {
            domain.terrain_domain_id
            for domain in catalog.terrain_domains
            if area_ids & set(domain.ski_area_ids)
        }
        expanded_area_ids = area_ids | {
            area_id
            for domain_id in expanded_domain_ids
            for area_id in domains_by_id[domain_id].ski_area_ids
        }
        if expanded_domain_ids == domain_ids and expanded_area_ids == area_ids:
            break
        domain_ids = expanded_domain_ids
        area_ids = expanded_area_ids

    return CatalogResultingGraphScope(
        destination_ids=destination_ids,
        region_ids=region_ids,
        base_ids=base_ids,
        access_ids=access_ids,
        area_ids=frozenset(area_ids),
        domain_ids=frozenset(domain_ids),
        pass_ids=pass_ids,
    )


def _required_resulting_graph_destination_ids(
    report: CatalogCurationReport,
    catalog: CatalogSnapshot,
) -> set[str]:
    destinations_by_region: dict[str, set[str]] = {}
    for destination in catalog.stay_destinations:
        destinations_by_region.setdefault(
            destination.trip_market_region_id,
            set(),
        ).add(destination.stay_destination_id)
    destination_by_base = {
        base.stay_base_id: base.stay_destination_id for base in catalog.stay_bases
    }
    destinations_by_area: dict[str, set[str]] = {}
    destination_by_access: dict[str, str] = {}
    for access in catalog.ski_area_access:
        destination_id = destination_by_base[access.stay_base_id]
        destination_by_access[access.ski_area_access_id] = destination_id
        destinations_by_area.setdefault(access.ski_area_id, set()).add(destination_id)
    destinations_by_pass = {
        product.lift_pass_product_id: set(product.available_from_stay_destination_ids)
        | set(product.default_for_stay_destination_ids)
        for product in catalog.lift_pass_products
    }
    destinations_by_domain: dict[str, set[str]] = {}
    for domain in catalog.terrain_domains:
        destinations_by_domain[domain.terrain_domain_id] = {
            destination_id
            for area_id in domain.ski_area_ids
            for destination_id in destinations_by_area.get(area_id, set())
        }
    for product in catalog.lift_pass_products:
        for domain_id in product.terrain_domain_ids:
            destinations_by_domain.setdefault(domain_id, set()).update(
                destinations_by_pass[product.lift_pass_product_id]
            )
    destination_by_rental = {
        rental.rental_display_fact_id: rental.stay_destination_id
        for rental in catalog.rental_display_facts
    }

    direct_destination_ids = {
        destination.stay_destination_id for destination in catalog.stay_destinations
    }
    target_destinations: dict[str, Mapping[str, set[str]]] = {
        "ski_region": destinations_by_region,
        "stay_destination": {
            destination_id: {destination_id}
            for destination_id in direct_destination_ids
        },
        "stay_base": {
            base_id: {destination_id}
            for base_id, destination_id in destination_by_base.items()
        },
        "ski_area": destinations_by_area,
        "ski_area_access": {
            access_id: {destination_id}
            for access_id, destination_id in destination_by_access.items()
        },
        "terrain_domain": destinations_by_domain,
        "lift_pass_product": destinations_by_pass,
        "rental_display_fact": {
            rental_id: {destination_id}
            for rental_id, destination_id in destination_by_rental.items()
        },
    }

    assert report.resulting_graph is not None
    declared_scope = catalog_resulting_graph_scope(
        catalog,
        set(report.resulting_graph.focus_stay_destination_ids),
    )
    required: set[str] = set()
    for target in report.reviewed_targets:
        if target.resulting_graph_role == "linked_dependency":
            continue
        target_type: CatalogTargetType = target.target_type
        target_id = target.target_id
        if target_type == "trust_manifest":
            namespace, _, target_id = target_id.partition(":")
            target_type = TRUST_MANIFEST_TARGET_TYPES[namespace]
        if target_type == "terrain_domain" and target_id in declared_scope.domain_ids:
            continue
        required.update(target_destinations[target_type].get(target_id, set()))
    return required


def _mermaid_label(entity_type: str, name: str) -> str:
    return f"{escape(entity_type, quote=True)}<br/>{escape(name, quote=True)}"


def _mermaid_edge_label(value: str) -> str:
    return escape(value, quote=True)


def _mermaid_pass_label(
    product: LiftPassProduct,
    *,
    no_separate_window_modeled: bool,
) -> str:
    label = _mermaid_label("Lift pass", product.name)
    for window in sorted(
        product.validity_windows,
        key=lambda item: (item.start_date, item.end_date, item.season_label),
    ):
        label += (
            f"<br/>valid {window.start_date.isoformat()} to "
            f"{window.end_date.isoformat()} ({window.status})"
        )
    if no_separate_window_modeled:
        label += "<br/>no separate pass window modeled"
    return label


def render_catalog_resulting_graph_markdown(
    report: CatalogCurationReport,
    catalog: CatalogSnapshot,
) -> str:
    validate_catalog_resulting_graph(report, catalog, require=True)
    assert report.resulting_graph is not None

    destinations_by_id = {
        destination.stay_destination_id: destination
        for destination in catalog.stay_destinations
    }
    regions_by_id = {region.ski_region_id: region for region in catalog.ski_regions}
    bases_by_id = {base.stay_base_id: base for base in catalog.stay_bases}
    areas_by_id = {area.ski_area_id: area for area in catalog.ski_areas}
    domains_by_id = {
        domain.terrain_domain_id: domain for domain in catalog.terrain_domains
    }
    passes_by_id = {
        product.lift_pass_product_id: product for product in catalog.lift_pass_products
    }
    cleared_pass_window_ids = {
        change.target_id
        for change in report.changes
        if change.target_type == "lift_pass_product"
        and change.field_path == "validity_windows"
        and json_values_equal(change.after, [])
    }

    scope = catalog_resulting_graph_scope(
        catalog,
        set(report.resulting_graph.focus_stay_destination_ids),
    )
    destination_ids = set(scope.destination_ids)
    region_ids = set(scope.region_ids)
    base_ids = set(scope.base_ids)
    access_links = tuple(
        sorted(
            (
                access
                for access in catalog.ski_area_access
                if access.ski_area_access_id in scope.access_ids
            ),
            key=lambda access: access.ski_area_access_id,
        )
    )
    area_ids = set(scope.area_ids)
    pass_ids = set(scope.pass_ids)
    domain_ids = set(scope.domain_ids)

    node_ids: dict[tuple[str, str], str] = {}
    lines = ["## Resulting Graph", "", "```mermaid", "flowchart LR"]

    def add_nodes(
        kind: str,
        entity_type: str,
        entity_ids: set[str],
        names: Mapping[str, str],
    ) -> None:
        for index, entity_id in enumerate(sorted(entity_ids), start=1):
            node_id = f"{kind}_{index}"
            node_ids[(kind, entity_id)] = node_id
            lines.append(
                f'  {node_id}["{_mermaid_label(entity_type, names[entity_id])}"]'
            )

    add_nodes(
        "region",
        "Trip market",
        region_ids,
        {entity_id: regions_by_id[entity_id].name for entity_id in region_ids},
    )
    add_nodes(
        "destination",
        "Stay destination",
        destination_ids,
        {
            entity_id: destinations_by_id[entity_id].name
            for entity_id in destination_ids
        },
    )
    add_nodes(
        "base",
        "Stay base",
        base_ids,
        {entity_id: bases_by_id[entity_id].name for entity_id in base_ids},
    )
    add_nodes(
        "area",
        "Ski area",
        area_ids,
        {entity_id: areas_by_id[entity_id].name for entity_id in area_ids},
    )
    add_nodes(
        "domain",
        "Terrain domain",
        domain_ids,
        {entity_id: domains_by_id[entity_id].name for entity_id in domain_ids},
    )
    for index, pass_id in enumerate(sorted(pass_ids), start=1):
        node_id = f"pass_{index}"
        node_ids[("pass", pass_id)] = node_id
        pass_label = _mermaid_pass_label(
            passes_by_id[pass_id],
            no_separate_window_modeled=pass_id in cleared_pass_window_ids,
        )
        lines.append(f'  {node_id}["{pass_label}"]')

    def add_edge(
        source_kind: str,
        source_id: str,
        target_kind: str,
        target_id: str,
        label: str,
    ) -> None:
        lines.append(
            f"  {node_ids[(source_kind, source_id)]} "
            f'-->|"{_mermaid_edge_label(label)}"| '
            f"{node_ids[(target_kind, target_id)]}"
        )

    for destination_id in sorted(destination_ids):
        destination = destinations_by_id[destination_id]
        add_edge(
            "region",
            destination.trip_market_region_id,
            "destination",
            destination_id,
            "trip market",
        )
    for base_id in sorted(base_ids):
        base = bases_by_id[base_id]
        add_edge(
            "destination",
            base.stay_destination_id,
            "base",
            base_id,
            "stay base",
        )
    for access in access_links:
        label = f"access: {access.access_mode}"
        if access.nearest_lift_name is not None:
            label += f" via {access.nearest_lift_name}"
        if access.distance_m is not None:
            label += f", {access.distance_m} m"
        elif access.duration_minutes is not None:
            label += f", {access.duration_minutes} min"
        add_edge(
            "base",
            access.stay_base_id,
            "area",
            access.ski_area_id,
            label,
        )
    for domain_id in sorted(domain_ids):
        domain = domains_by_id[domain_id]
        for area_id in sorted(set(domain.ski_area_ids) & area_ids):
            add_edge("domain", domain_id, "area", area_id, "contains")
    for pass_id in sorted(pass_ids):
        product = passes_by_id[pass_id]
        for destination_id in sorted(destination_ids):
            if destination_id in product.default_for_stay_destination_ids:
                add_edge(
                    "destination",
                    destination_id,
                    "pass",
                    pass_id,
                    "default pass",
                )
            elif destination_id in product.available_from_stay_destination_ids:
                add_edge(
                    "destination",
                    destination_id,
                    "pass",
                    pass_id,
                    "pass available",
                )
        for area_id in sorted(set(product.valid_ski_area_ids) & area_ids):
            add_edge("pass", pass_id, "area", area_id, "covers area")
        for domain_id in sorted(set(product.terrain_domain_ids) & domain_ids):
            add_edge(
                "pass",
                pass_id,
                "domain",
                domain_id,
                "covers terrain domain",
            )
    lines.extend(["```", ""])
    return "\n".join(lines)


def render_catalog_curation_report_markdown(
    report: CatalogCurationReport,
    catalog: CatalogSnapshot | None = None,
) -> str:
    lines = [
        f"# {report.title}",
        "",
        report.summary,
    ]
    if report.resulting_graph is not None:
        if catalog is None:
            raise CatalogValidationError(
                ["current catalog is required to render resulting_graph"]
            )
        lines.extend(
            ["", *render_catalog_resulting_graph_markdown(report, catalog).splitlines()]
        )
    lines.extend(
        [
            "",
            "## Reviewed Targets",
            "",
            "| Target | Scope | Graph Role | Required Fields |",
            "| --- | --- | --- | --- |",
        ]
    )
    for target in report.reviewed_targets:
        required = (
            "all canonical fields"
            if target.scope == "full"
            else ", ".join(_code_cell(path) for path in target.required_field_paths)
        )
        lines.append(
            f"| {_code_cell(f'{target.target_type}:{target.target_id}')} | "
            f"{_code_cell(target.scope)} | "
            f"{_code_cell(target.resulting_graph_role)} | {required} |"
        )
    if report.review_evidence_envelope:
        lines.extend(
            [
                "",
                "## Review Evidence Envelope",
                "",
                "| Family | Source Kind | Source URLs | Candidate Kinds |",
                "| --- | --- | --- | --- |",
            ]
        )
        for family in report.review_evidence_envelope:
            source_urls = ", ".join(
                _markdown_link(source_url, source_url)
                for source_url in family.source_urls
            )
            candidate_kinds = ", ".join(
                _code_cell(candidate_kind) for candidate_kind in family.candidate_kinds
            )
            lines.append(
                f"| {_code_cell(family.family_id)} | "
                f"{_code_cell(family.source_kind)} | {source_urls} | "
                f"{candidate_kinds} |"
            )
    if report.entity_scope_assessments:
        includes_graph_impact = any(
            assessment.graph_impact is not None
            for assessment in report.entity_scope_assessments
        )
        scope_header = (
            "| Candidate | Kind | Disposition | Signals | Catalog Targets | "
            "Evidence | Backlog"
        )
        scope_divider = "| --- | --- | --- | --- | --- | --- | ---"
        if includes_graph_impact:
            scope_header += " | Graph Impact"
            scope_divider += " | ---"
        scope_header += " | Rationale |"
        scope_divider += " | --- |"
        lines.extend(
            [
                "",
                "## Entity Scope Assessments",
                "",
                scope_header,
                scope_divider,
            ]
        )
        for assessment in report.entity_scope_assessments:
            targets = ", ".join(
                _code_cell(f"{target.target_type}:{target.target_id}")
                for target in assessment.target_refs
            )
            signals = ", ".join(_code_cell(signal) for signal in assessment.signals)
            evidence = ", ".join(
                _code_cell(evidence_id) for evidence_id in assessment.evidence_refs
            )
            backlog = (
                _code_cell(assessment.backlog_ref)
                if assessment.backlog_ref is not None
                else ""
            )
            graph_impact = (
                _code_cell(assessment.graph_impact)
                if assessment.graph_impact is not None
                else ""
            )
            graph_impact_cell = f" | {graph_impact}" if includes_graph_impact else ""
            lines.append(
                f"| {_code_cell(assessment.candidate_id)} "
                f"({_markdown_cell(assessment.candidate_name)}) | "
                f"{_code_cell(assessment.candidate_kind)} | "
                f"{_code_cell(assessment.disposition)} | {signals} | {targets} | "
                f"{evidence} | {backlog}{graph_impact_cell} | "
                f"{_markdown_cell(assessment.rationale)} |"
            )
        ski_area_assessments = [
            assessment
            for assessment in report.entity_scope_assessments
            if assessment.ski_area_boundary is not None
        ]
        if ski_area_assessments:
            includes_coordination = any(
                bool(
                    assessment.ski_area_boundary
                    and (
                        assessment.ski_area_boundary.component_candidate_ids
                        or assessment.ski_area_boundary.coordination_evidence_refs
                        or assessment.ski_area_boundary.coordination_evidence_families
                    )
                )
                for assessment in ski_area_assessments
            )
            boundary_header = (
                "| Candidate | Parent | Terrain | Connectivity | Operations | "
                "Weather | Pass | Provider Consensus | Separation Value | "
            )
            boundary_divider = (
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | "
            )
            if includes_coordination:
                boundary_header += (
                    "Components | Coordination Evidence | Evidence Families | "
                )
                boundary_divider += "--- | --- | --- | "
            boundary_header += "Evidence |"
            boundary_divider += "--- |"
            lines.extend(
                [
                    "",
                    "## Ski-Area Boundary Assessments",
                    "",
                    boundary_header,
                    boundary_divider,
                ]
            )
            for assessment in ski_area_assessments:
                boundary = assessment.ski_area_boundary
                assert boundary is not None
                parent = (
                    _code_cell(boundary.parent_ski_area_id)
                    if boundary.parent_ski_area_id is not None
                    else ""
                )
                evidence = ", ".join(
                    _code_cell(evidence_id) for evidence_id in boundary.evidence_refs
                )
                coordination_cells = ""
                if includes_coordination:
                    components = ", ".join(
                        _code_cell(component_id)
                        for component_id in boundary.component_candidate_ids
                    )
                    coordination_evidence = ", ".join(
                        _code_cell(evidence_id)
                        for evidence_id in boundary.coordination_evidence_refs
                    )
                    family_ownership = _render_coordination_evidence_families(boundary)
                    coordination_cells = (
                        f" | {components} | {coordination_evidence} | "
                        f"{family_ownership}"
                    )
                lines.append(
                    f"| {_code_cell(assessment.candidate_id)} | {parent} | "
                    f"{_code_cell(boundary.terrain_scope)} | "
                    f"{_code_cell(boundary.connectivity_to_parent)} | "
                    f"{_code_cell(boundary.operational_scope)} | "
                    f"{_code_cell(boundary.weather_scope)} | "
                    f"{_code_cell(boundary.pass_scope)} | "
                    f"{_code_cell(boundary.provider_consensus)} | "
                    f"{_code_cell(boundary.separation_value)}{coordination_cells} | "
                    f"{evidence} |"
                )
    lines.extend(
        [
            "",
            "## Changed Fields",
            "",
            "| Target | Field | Before | After | Trust | Ranking Relevant |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for change in report.changes:
        lines.append(
            f"| {_code_cell(f'{change.target_type}:{change.target_id}')} | "
            f"{_code_cell(change.field_path)} | {_json_cell(change.before)} | "
            f"{_json_cell(change.after)} | {_code_cell(change.trust_status)} | "
            f"{'yes' if change.ranking_relevant else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Field Coverage",
            "",
            "| Target | Field | Status | Notes |",
            "| --- | --- | --- | --- |",
        ]
    )
    for coverage in report.field_coverage:
        lines.append(
            f"| {_code_cell(f'{coverage.target_type}:{coverage.target_id}')} | "
            f"{_code_cell(coverage.field_path)} | {_code_cell(coverage.status)} | "
            f"{_markdown_cell(coverage.notes or '')} |"
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "| Target | Field | Source | Source Value | Evidence | Normalization |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for evidence in report.evidence:
        lines.append(
            f"| {_code_cell(f'{evidence.target_type}:{evidence.target_id}')} | "
            f"{_code_cell(evidence.field_path)} | "
            f"{_markdown_link(evidence.source_title, evidence.source_url)} | "
            f"{_json_cell(evidence.source_value)} | "
            f"{_markdown_cell(evidence.evidence_summary)} | "
            f"{_markdown_cell(evidence.normalization_note or '')} |"
        )
    if report.destination_boundary_assessments:
        lines.extend(["", "## Boundary Decisions", ""])
        for assessment in report.destination_boundary_assessments:
            lines.append(
                f"- {_code_cell(assessment.candidate_id)}: "
                f"{_code_cell('pass' if assessment.is_passing else 'unresolved')}"
            )
    if report.weather_request_geometry_assessments:
        lines.extend(["", "## Weather Request Geometry", ""])
        for assessment in report.weather_request_geometry_assessments:
            coordinate_method = assessment.coordinate_derivation_method or "unresolved"
            elevation_method = assessment.elevation_derivation_method or "unresolved"
            geometry_completeness = assessment.geometry_completeness or "unresolved"
            lines.append(
                f"- {_code_cell(assessment.ski_area_id)}: "
                f"{_code_cell(assessment.after.weather_sampling_status)}; "
                f"{'material change' if assessment.material_change else 'unchanged'}; "
                f"coordinate={_code_cell(coordinate_method)}; "
                f"elevation={_code_cell(elevation_method)}; "
                f"geometry={_code_cell(geometry_completeness)}; "
                f"derivation={_code_cell(assessment.derivation_status or 'unresolved')}"
            )
            if assessment.activation_prerequisite:
                lines.append(
                    f"  - Activation prerequisite: "
                    f"{_markdown_cell(assessment.activation_prerequisite)}"
                )
            if assessment.coordinate_derivation_attempts:
                lines.append("  - Coordinate derivation attempts:")
                for attempt in assessment.coordinate_derivation_attempts:
                    evidence_refs = ", ".join(
                        _code_cell(evidence_ref)
                        for evidence_ref in attempt.evidence_refs
                    )
                    lines.append(
                        f"    - {_code_cell(attempt.method)}: "
                        f"{_code_cell(attempt.outcome)}; "
                        f"evidence={evidence_refs}; "
                        f"{_markdown_cell(attempt.rationale)}"
                    )
            if assessment.post_merge_handoff:
                handoff_labels = {
                    "scheduled_completion": ("scheduled historical-weather completion"),
                    "force_refetch_and_rebuild_climatology": (
                        "targeted forced historical refetch and climatology rebuild"
                    ),
                    "force_refetch_and_rebuild_after_activation": (
                        "after activation, targeted forced historical refetch and "
                        "climatology rebuild"
                    ),
                }
                lines.append(
                    "  - Post-merge weather handoff: "
                    f"{handoff_labels[assessment.post_merge_handoff]}."
                )
    if report.ranking_impact_summary:
        lines.extend(["", "## Ranking Impact", "", report.ranking_impact_summary])
    if report.validation_commands:
        lines.extend(["", "## Verification", ""])
        lines.extend(f"- `{command}`" for command in report.validation_commands)
    if report.unresolved_caveats:
        lines.extend(["", "## Caveats", ""])
        lines.extend(f"- {caveat}" for caveat in report.unresolved_caveats)
    lines.append("")
    return "\n".join(lines)
