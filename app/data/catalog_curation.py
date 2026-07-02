from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping
from urllib.parse import quote, urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.catalog import SkiArea
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
CatalogAssessmentStatus = Literal["pass", "fail", "unresolved"]
CatalogBoundaryGateName = Literal[
    "independent_stay_context",
    "independent_ski_access",
    "independent_recommendation_value",
]
CatalogIdentitySignalType = Literal[
    "local_pass",
    "separate_operator",
    "operating_schedule",
    "status_feed",
    "weather_presentation",
    "official_destination_treatment",
]
CatalogBoundaryFailureRoute = Literal[
    "stay_base",
    "ski_area",
    "ski_sub_area_backlog",
    "terrain_domain",
    "external_pass_context",
    "blocked",
]
JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]

SOURCE_BACKED_TRUST_STATUSES = {"verified", "verified_with_adjustment"}
VERIFICATION_SOURCE_TYPES = {"official", "open_data", "reviewed_editorial"}
MARKDOWN_LINK_URL_SAFE_CHARS = ":/?#@!$&'*,;=%-._~"
BOUNDARY_GATE_NAMES = frozenset(
    {
        "independent_stay_context",
        "independent_ski_access",
        "independent_recommendation_value",
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
                "atmosphere_tags",
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
                "base_type",
                "atmosphere_tags",
                "regional_data_ids",
            }
        ),
        "ski_area": frozenset(
            {
                "ski_area_id",
                "name",
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
            {"display_name", "field_statuses", "source_refs", "notes"}
        ),
    }
)

NESTED_FIELD_PATH_ROOTS: Mapping[CatalogTargetType, frozenset[str]] = MappingProxyType(
    {
        "ski_region": frozenset({"source_urls"}),
        "stay_destination": frozenset({"atmosphere_tags", "regional_data_ids"}),
        "stay_base": frozenset({"atmosphere_tags", "regional_data_ids"}),
        "ski_area": frozenset({"season_windows", "supported_skill_levels"}),
        "ski_area_access": frozenset({"regional_data_ids", "source_urls"}),
        "terrain_domain": frozenset({"ski_area_ids", "season_windows", "source_urls"}),
        "lift_pass_product": frozenset(
            {
                "available_from_stay_destination_ids",
                "default_for_stay_destination_ids",
                "valid_ski_area_ids",
                "terrain_domain_ids",
                "pass_accessible_terrain",
                "prices",
            }
        ),
        "rental_display_fact": frozenset(),
        "trust_manifest": frozenset({"field_statuses", "source_refs", "notes"}),
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
        if {gate.gate_name for gate in self.gates} != BOUNDARY_GATE_NAMES:
            raise ValueError(
                "destination boundary assessment must contain exactly all three gates"
            )
        if len(self.gates) != len(BOUNDARY_GATE_NAMES):
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
        return all(gate.status == "pass" for gate in self.gates) and any(
            signal.status == "pass" for signal in self.identity_signals
        )


class CatalogWeatherRequestGeometry(CatalogCurationContractModel):
    latitude: float
    longitude: float
    base_elevation_m: int
    mid_elevation_m: int
    upper_elevation_m: int


class CatalogWeatherRequestGeometryAssessment(CatalogCurationContractModel):
    ski_area_id: str = Field(min_length=1)
    before: CatalogWeatherRequestGeometry
    after: CatalogWeatherRequestGeometry

    @property
    def material_change(self) -> bool:
        return self.before != self.after


def catalog_weather_request_geometry(
    ski_area: SkiArea,
) -> CatalogWeatherRequestGeometry:
    elevation_by_band = {
        point.band: point.elevation_m for point in weather_elevation_points(ski_area)
    }
    return CatalogWeatherRequestGeometry(
        latitude=ski_area.latitude,
        longitude=ski_area.longitude,
        base_elevation_m=elevation_by_band["base"],
        mid_elevation_m=elevation_by_band["mid"],
        upper_elevation_m=elevation_by_band["upper"],
    )


class CatalogCurationReport(CatalogCurationContractModel):
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
    boundary_decision_targets: list[str] = Field(default_factory=list)
    weather_request_geometry_targets: list[str] = Field(default_factory=list)
    weather_request_geometry_assessments: list[
        CatalogWeatherRequestGeometryAssessment
    ] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    ranking_comparison_summary: str | None = None
    unresolved_caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_activity(self) -> CatalogCurationReport:
        if not (
            self.changes
            or self.boundary_decision_targets
            or self.weather_request_geometry_targets
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


def validate_catalog_curation_report(report: CatalogCurationReport) -> None:
    issues: list[str] = []
    if any(change.ranking_relevant for change in report.changes):
        if not report.ranking_comparison_summary:
            issues.append(
                "ranking_comparison_summary is required when any change is "
                "ranking-relevant"
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
        if (change.target_type, change.target_id) not in reviewed_by_key:
            issues.append(
                f"{change.target_type}:{change.target_id}: target is not declared "
                "in reviewed_targets"
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

    _validate_boundary_assessments(report, reviewed_by_key, evidence_by_id, issues)
    _validate_geometry_assessments(report, reviewed_by_key, issues)

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
    for evidence in report.evidence:
        if (
            evidence.target_key not in changes_by_key
            and evidence.target_key not in unresolved_keys
            and evidence.evidence_id not in boundary_evidence_ids
        ):
            issues.append(
                f"{evidence.target_type}:{evidence.target_id} "
                f"{evidence.field_path}: evidence has no matching change"
            )

    for change in report.changes:
        matching_evidence = evidence_by_key.get(change.target_key, [])
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


def _validate_boundary_assessments(
    report: CatalogCurationReport,
    reviewed_by_key: Mapping[tuple[str, str], CatalogReviewedTarget],
    evidence_by_id: Mapping[str, CatalogEvidenceItem],
    issues: list[str],
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
                        "does not declare boundary ownership"
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


def _markdown_cell(value: str) -> str:
    return " ".join(line.strip() for line in value.splitlines()).replace("|", "\\|")


def _code_cell(value: str) -> str:
    return f"`{_markdown_cell(value)}`"


def _json_cell(value: JsonValue) -> str:
    return _code_cell(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _markdown_link(label: str, url: str) -> str:
    escaped_label = _markdown_cell(label).replace("[", "\\[").replace("]", "\\]")
    return f"[{escaped_label}]({quote(url, safe=MARKDOWN_LINK_URL_SAFE_CHARS)})"


def render_catalog_curation_report_markdown(report: CatalogCurationReport) -> str:
    lines = [
        f"# {report.title}",
        "",
        report.summary,
        "",
        "## Reviewed Targets",
        "",
        "| Target | Scope | Required Fields |",
        "| --- | --- | --- |",
    ]
    for target in report.reviewed_targets:
        required = (
            "all canonical fields"
            if target.scope == "full"
            else ", ".join(_code_cell(path) for path in target.required_field_paths)
        )
        lines.append(
            f"| {_code_cell(f'{target.target_type}:{target.target_id}')} | "
            f"{_code_cell(target.scope)} | {required} |"
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
            lines.append(
                f"- {_code_cell(assessment.ski_area_id)}: "
                f"{'material change' if assessment.material_change else 'unchanged'}"
            )
    if report.ranking_comparison_summary:
        lines.extend(["", "## Ranking Impact", "", report.ranking_comparison_summary])
    if report.validation_commands:
        lines.extend(["", "## Verification", ""])
        lines.extend(f"- `{command}`" for command in report.validation_commands)
    if report.unresolved_caveats:
        lines.extend(["", "## Caveats", ""])
        lines.extend(f"- {caveat}" for caveat in report.unresolved_caveats)
    lines.append("")
    return "\n".join(lines)
