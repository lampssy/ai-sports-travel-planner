from __future__ import annotations

import json
import math
import unicodedata
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping
from urllib.parse import quote, urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.models import SkiArea
from app.integrations.open_meteo import weather_elevation_points

CatalogTargetType = Literal[
    "destination",
    "ski_area",
    "stay_base",
    "rental",
    "lift_pass_product",
    "terrain_group",
    "terrain_domain",
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
UNSAFE_SOURCE_URL_MARKDOWN_CHARS = {"(", ")", "[", "]", "|", "\\", "<", ">"}
MARKDOWN_LINK_LABEL_ESCAPE_CHARS = {"\\", "[", "]", "(", ")", "|"}
MARKDOWN_LINK_URL_SAFE_CHARS = ":/?#@!$&'*,;=%-._~"

BOUNDARY_GATE_NAMES = frozenset(
    {
        "independent_stay_context",
        "independent_ski_access",
        "independent_recommendation_value",
    }
)

CANONICAL_FIELD_PATHS: Mapping[CatalogTargetType, frozenset[str]] = MappingProxyType(
    {
        "destination": frozenset(
            {
                "resort_id",
                "name",
                "country",
                "region",
                "price_level",
                "latitude",
                "longitude",
                "base_elevation_m",
                "summit_elevation_m",
                "season_start_month",
                "season_end_month",
                "season_windows",
                "lift_pass_products",
                "ski_areas",
                "terrain_groups",
                "stay_bases",
                "rentals",
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
            }
        ),
        "terrain_group": frozenset(
            {
                "terrain_group_id",
                "name",
                "ski_area_ids",
                "metric_scope",
                "total_piste_km",
                "total_lift_count",
                "piste_km_by_difficulty.beginner",
                "piste_km_by_difficulty.intermediate",
                "piste_km_by_difficulty.advanced",
                "source_urls",
            }
        ),
        "terrain_domain": frozenset(
            {
                "terrain_domain_id",
                "name",
                "ski_area_refs",
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
        "stay_base": frozenset(
            {
                "stay_base_id",
                "name",
                "price_range",
                "price_min",
                "price_max",
                "quality",
                "lift_distance",
                "supported_skill_levels",
                "latitude",
                "longitude",
                "nearest_lift_name",
                "nearest_lift_distance_m",
                "access_mode",
                "base_type",
                "atmosphere_tags",
                "regional_data_ids",
            }
        ),
        "rental": frozenset(
            {
                "name",
                "price_range",
                "price_min",
                "price_max",
                "quality",
                "lift_distance",
            }
        ),
        "lift_pass_product": frozenset(
            {
                "lift_pass_product_id",
                "name",
                "validity_scope",
                "is_default",
                "valid_ski_area_ids",
                "terrain_domain_ids",
                "external_validity_summary",
                "prices",
            }
        ),
        "trust_manifest": frozenset(
            {"display_name", "field_statuses", "source_refs", "notes"}
        ),
    }
)

NESTED_FIELD_PATH_ROOTS: Mapping[CatalogTargetType, frozenset[str]] = MappingProxyType(
    {
        "destination": frozenset(
            {
                "season_windows",
                "lift_pass_products",
                "ski_areas",
                "terrain_groups",
                "stay_bases",
                "rentals",
            }
        ),
        "ski_area": frozenset({"season_windows"}),
        "terrain_group": frozenset({"ski_area_ids", "source_urls"}),
        "terrain_domain": frozenset({"ski_area_refs", "season_windows", "source_urls"}),
        "stay_base": frozenset(
            {"supported_skill_levels", "atmosphere_tags", "regional_data_ids"}
        ),
        "rental": frozenset(),
        "lift_pass_product": frozenset(
            {"valid_ski_area_ids", "terrain_domain_ids", "prices"}
        ),
        "trust_manifest": frozenset({"field_statuses", "source_refs", "notes"}),
    }
)


def _validate_json_value(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            _validate_json_value(nested_value)
        return value
    if isinstance(value, list):
        for nested_value in value:
            _validate_json_value(nested_value)
        return value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON numbers must be finite")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise ValueError("value must be JSON-serializable")


def _validate_non_blank_string(value: str, field_name: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} cannot be blank")
    return trimmed


def _validate_optional_non_blank_string(
    value: str | None, field_name: str
) -> str | None:
    if value is None:
        return None
    return _validate_non_blank_string(value, field_name)


def _validate_non_blank_string_list(values: list[str], field_name: str) -> list[str]:
    return [_validate_non_blank_string(value, field_name) for value in values]


def _validate_field_path(value: str) -> str:
    value = _validate_non_blank_string(value, "field_path")
    segments = value.split(".")
    if any(not segment.strip() for segment in segments):
        raise ValueError("field_path cannot contain blank segments")
    if any(segment != segment.strip() for segment in segments):
        raise ValueError(
            "field_path segments cannot contain leading or trailing whitespace"
        )
    return value


def _is_supported_field_path(target_type: CatalogTargetType, field_path: str) -> bool:
    if field_path in CANONICAL_FIELD_PATHS[target_type]:
        return True
    return any(
        field_path.startswith(f"{root_path}[") or field_path.startswith(f"{root_path}.")
        for root_path in NESTED_FIELD_PATH_ROOTS[target_type]
    )


def rental_reconciliation_target_id(resort_id: str, rental_name: str) -> str:
    normalized_resort_id = _validate_non_blank_string(resort_id, "resort_id")
    normalized_name = unicodedata.normalize("NFKD", rental_name).casefold()
    slug_parts: list[str] = []
    pending_separator = False
    for character in normalized_name:
        if unicodedata.combining(character):
            continue
        if "a" <= character <= "z" or "0" <= character <= "9":
            if pending_separator and slug_parts:
                slug_parts.append("-")
            slug_parts.append(character)
            pending_separator = False
        else:
            pending_separator = True
    slug = "".join(slug_parts).strip("-")
    if not slug:
        raise ValueError("rental_name must produce a non-empty reconciliation slug")
    return f"{normalized_resort_id}:{slug}"


def _validate_target_identity(
    target_type: CatalogTargetType,
    target_id: str,
) -> str:
    normalized_target_id = _validate_non_blank_string(target_id, "target_id")
    if target_type == "rental":
        resort_id, separator, rental_slug = normalized_target_id.partition(":")
        if not separator or not resort_id or not rental_slug:
            raise ValueError(
                "rental target_id must be destination-qualified as resort_id:slug"
            )
        expected = rental_reconciliation_target_id(resort_id, rental_slug)
        if normalized_target_id != expected:
            raise ValueError(f"rental target_id must use canonical identity {expected}")
    elif target_type == "trust_manifest":
        namespace, separator, record_id = normalized_target_id.partition(":")
        if not separator or namespace not in {"destination", "terrain_domain"}:
            raise ValueError(
                "trust_manifest target_id must use destination:<id> or "
                "terrain_domain:<id>"
            )
        _validate_non_blank_string(record_id, "trust manifest record id")
    return normalized_target_id


def _validate_target_field(
    target_type: CatalogTargetType,
    target_id: str,
    field_path: str,
) -> tuple[str, str]:
    normalized_target_id = _validate_target_identity(target_type, target_id)
    normalized_field_path = _validate_field_path(field_path)
    if not _is_supported_field_path(target_type, normalized_field_path):
        raise ValueError(
            f"unsupported {target_type} field_path {normalized_field_path!r}"
        )
    return normalized_target_id, normalized_field_path


def _target_key(
    target_type: str, target_id: str, field_path: str
) -> tuple[str, str, str]:
    return (target_type, target_id, field_path)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _validate_safe_source_url(value: str) -> str:
    value = _validate_non_blank_string(value, "source_url")
    if not _is_http_url(value):
        raise ValueError("source_url must be an http(s) URL")
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("source_url cannot contain whitespace or control characters")
    if any(character in value for character in UNSAFE_SOURCE_URL_MARKDOWN_CHARS):
        raise ValueError("source_url cannot contain markdown-closing characters")
    return value


def _json_cell(value: JsonValue) -> str:
    return _code_cell(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _markdown_cell(value: str) -> str:
    single_line = " ".join(line.strip() for line in value.splitlines())
    return single_line.replace("|", "\\|")


def _markdown_link_label(value: str) -> str:
    single_line = " ".join(line.strip() for line in value.splitlines())
    return "".join(
        f"\\{character}" if character in MARKDOWN_LINK_LABEL_ESCAPE_CHARS else character
        for character in single_line
    )


def _markdown_link_url(value: str) -> str:
    return quote(value, safe=MARKDOWN_LINK_URL_SAFE_CHARS)


def _markdown_link(label: str, url: str) -> str:
    return f"[{_markdown_link_label(label)}]({_markdown_link_url(url)})"


def _code_cell(value: str) -> str:
    return f"`{_markdown_cell(value)}`"


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

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        return _validate_non_blank_string(value, "message")

    @field_validator("target_id")
    @classmethod
    def reject_blank_target_id(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank_string(value, "target_id")

    @field_validator("field_path")
    @classmethod
    def reject_blank_field_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_field_path(value)


class CatalogChangeSummary(CatalogCurationContractModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    before: JsonValue = None
    after: JsonValue = None
    trust_status: CatalogTrustStatus
    ranking_relevant: bool = False

    @field_validator("field_path")
    @classmethod
    def reject_blank_segments(cls, value: str) -> str:
        return _validate_field_path(value)

    @field_validator("target_id")
    @classmethod
    def reject_blank_target_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "target_id")

    @field_validator("before", "after")
    @classmethod
    def reject_non_json_value(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)

    @model_validator(mode="after")
    def validate_target_field_identity(self) -> CatalogChangeSummary:
        self.target_id, self.field_path = _validate_target_field(
            self.target_type,
            self.target_id,
            self.field_path,
        )
        if self.target_type == "rental" and self.field_path == "name":
            resort_id = self.target_id.split(":", maxsplit=1)[0]
            for value in (self.before, self.after):
                if isinstance(value, str):
                    expected = rental_reconciliation_target_id(resort_id, value)
                    if self.target_id != expected:
                        raise ValueError(
                            "rental name changes must use removal and addition "
                            f"targets; expected {expected}"
                        )
        return self

    @property
    def target_key(self) -> tuple[str, str, str]:
        return _target_key(self.target_type, self.target_id, self.field_path)


class CatalogFieldCoverage(CatalogCurationContractModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    status: CatalogFieldCoverageStatus
    notes: str | None = None

    @field_validator("field_path")
    @classmethod
    def reject_blank_segments(cls, value: str) -> str:
        return _validate_field_path(value)

    @field_validator("target_id")
    @classmethod
    def reject_blank_target_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "target_id")

    @field_validator("notes")
    @classmethod
    def reject_blank_notes(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank_string(value, "notes")

    @model_validator(mode="after")
    def validate_target_field_identity(self) -> CatalogFieldCoverage:
        self.target_id, self.field_path = _validate_target_field(
            self.target_type,
            self.target_id,
            self.field_path,
        )
        return self

    @property
    def target_key(self) -> tuple[str, str, str]:
        return _target_key(self.target_type, self.target_id, self.field_path)


class CatalogEvidenceItem(CatalogCurationContractModel):
    evidence_id: str = Field(min_length=1)
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    source_type: CatalogSourceType
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_value: JsonValue
    evidence_summary: str = Field(min_length=1)
    normalization_note: str | None = None

    @field_validator("field_path")
    @classmethod
    def reject_blank_segments(cls, value: str) -> str:
        return _validate_field_path(value)

    @field_validator("evidence_id")
    @classmethod
    def reject_blank_evidence_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "evidence_id")

    @field_validator("target_id")
    @classmethod
    def reject_blank_target_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "target_id")

    @field_validator("source_url")
    @classmethod
    def require_http_source_url(cls, value: str) -> str:
        return _validate_safe_source_url(value)

    @field_validator("source_title")
    @classmethod
    def reject_blank_source_title(cls, value: str) -> str:
        return _validate_non_blank_string(value, "source_title")

    @field_validator("evidence_summary")
    @classmethod
    def reject_blank_evidence_summary(cls, value: str) -> str:
        return _validate_non_blank_string(value, "evidence_summary")

    @field_validator("normalization_note")
    @classmethod
    def reject_blank_normalization_note(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank_string(value, "normalization_note")

    @field_validator("source_value")
    @classmethod
    def reject_non_json_source_value(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)

    @model_validator(mode="after")
    def validate_target_field_identity(self) -> CatalogEvidenceItem:
        self.target_id, self.field_path = _validate_target_field(
            self.target_type,
            self.target_id,
            self.field_path,
        )
        return self

    @property
    def target_key(self) -> tuple[str, str, str]:
        return _target_key(self.target_type, self.target_id, self.field_path)


class CatalogReviewedTarget(CatalogCurationContractModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    scope: CatalogReviewScope
    required_field_paths: list[str] = Field(default_factory=list)

    @field_validator("required_field_paths")
    @classmethod
    def validate_required_field_paths(cls, values: list[str]) -> list[str]:
        normalized = [_validate_field_path(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("required_field_paths must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_scope_and_fields(self) -> CatalogReviewedTarget:
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
        return (self.target_type, self.target_id)

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

    @field_validator("notes")
    @classmethod
    def reject_blank_notes(cls, value: str) -> str:
        return _validate_non_blank_string(value, "notes")

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        normalized = _validate_non_blank_string_list(values, "evidence_refs")
        if len(normalized) != len(set(normalized)):
            raise ValueError("evidence_refs must be unique")
        return normalized


class CatalogIdentitySignalAssessment(CatalogCurationContractModel):
    signal_type: CatalogIdentitySignalType
    status: CatalogAssessmentStatus
    notes: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)

    @field_validator("notes")
    @classmethod
    def reject_blank_notes(cls, value: str) -> str:
        return _validate_non_blank_string(value, "notes")

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        normalized = _validate_non_blank_string_list(values, "evidence_refs")
        if len(normalized) != len(set(normalized)):
            raise ValueError("evidence_refs must be unique")
        return normalized


class CatalogDestinationBoundaryAssessment(CatalogCurationContractModel):
    candidate_id: str = Field(min_length=1)
    gates: list[CatalogBoundaryGateAssessment]
    identity_signals: list[CatalogIdentitySignalAssessment] = Field(min_length=1)
    failure_route: CatalogBoundaryFailureRoute | None = None

    @field_validator("candidate_id")
    @classmethod
    def reject_blank_candidate_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "candidate_id")

    @model_validator(mode="after")
    def validate_gate_set_and_route(self) -> CatalogDestinationBoundaryAssessment:
        gate_names = [gate.gate_name for gate in self.gates]
        if len(gate_names) != len(set(gate_names)):
            raise ValueError("destination boundary gates must be unique")
        if set(gate_names) != BOUNDARY_GATE_NAMES:
            raise ValueError(
                "destination boundary assessment must contain exactly all three gates"
            )
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

    @field_validator("ski_area_id")
    @classmethod
    def reject_blank_ski_area_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "ski_area_id")

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
    def require_report_activity(self) -> CatalogCurationReport:
        if not (
            self.changes
            or self.boundary_decision_targets
            or self.weather_request_geometry_targets
        ):
            raise ValueError(
                "curation report must include a change or retained semantic decision"
            )
        return self

    @field_validator("title")
    @classmethod
    def reject_blank_title(cls, value: str) -> str:
        return _validate_non_blank_string(value, "title")

    @field_validator("summary")
    @classmethod
    def reject_blank_summary(cls, value: str) -> str:
        return _validate_non_blank_string(value, "summary")

    @field_validator("ranking_comparison_summary")
    @classmethod
    def reject_blank_ranking_comparison_summary(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank_string(value, "ranking_comparison_summary")

    @field_validator("changed_entities")
    @classmethod
    def reject_blank_changed_entities(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_string_list(values, "changed_entities")

    @field_validator(
        "boundary_decision_targets",
        "weather_request_geometry_targets",
    )
    @classmethod
    def reject_blank_decision_targets(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_string_list(values, "decision target")

    @field_validator("validation_commands")
    @classmethod
    def reject_blank_validation_commands(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_string_list(values, "validation_commands")

    @field_validator("unresolved_caveats")
    @classmethod
    def reject_blank_unresolved_caveats(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_string_list(values, "unresolved_caveats")


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
    for reviewed_target in report.reviewed_targets:
        if reviewed_target.target_key in reviewed_by_key:
            issues.append(
                f"{reviewed_target.target_type}:{reviewed_target.target_id}: "
                "duplicate reviewed target"
            )
        reviewed_by_key[reviewed_target.target_key] = reviewed_target

    change_keys: set[tuple[str, str, str]] = set()
    for change in report.changes:
        if change.target_key in change_keys:
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                "duplicate change for target field"
            )
        change_keys.add(change.target_key)
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
        if coverage.status == "changed" and coverage.target_key not in change_keys:
            issues.append(
                f"{coverage.target_type}:{coverage.target_id} "
                f"{coverage.field_path}: changed field coverage has no matching "
                "change"
            )
        if (coverage.target_type, coverage.target_id) not in reviewed_by_key:
            issues.append(
                f"{coverage.target_type}:{coverage.target_id}: target is not "
                "declared in reviewed_targets"
            )

    for change in report.changes:
        matching_coverage = coverage_by_key.get(change.target_key)
        if matching_coverage is None:
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                "missing changed field coverage"
            )
        elif matching_coverage.status != "changed":
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                "changed field must be covered with status=changed"
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
                f"{evidence.target_type}:{evidence.target_id}: target is not "
                "declared in reviewed_targets"
            )

    boundary_target_set = set(report.boundary_decision_targets)
    if len(boundary_target_set) != len(report.boundary_decision_targets):
        issues.append("boundary_decision_targets must be unique")
    boundary_assessments: dict[str, CatalogDestinationBoundaryAssessment] = {}
    boundary_evidence_refs: set[str] = set()
    for assessment in report.destination_boundary_assessments:
        if assessment.candidate_id in boundary_assessments:
            issues.append(
                f"{assessment.candidate_id}: duplicate destination boundary assessment"
            )
        boundary_assessments[assessment.candidate_id] = assessment
        for gate in assessment.gates:
            boundary_evidence_refs.update(gate.evidence_refs)
            referenced = [
                evidence_by_id[evidence_id]
                for evidence_id in gate.evidence_refs
                if evidence_id in evidence_by_id
            ]
            for evidence_id in set(gate.evidence_refs) - set(evidence_by_id):
                issues.append(
                    f"{assessment.candidate_id}/{gate.gate_name}: unknown evidence "
                    f"ref {evidence_id}"
                )
            if gate.status == "pass" and not any(
                evidence.source_type in VERIFICATION_SOURCE_TYPES
                for evidence in referenced
            ):
                issues.append(
                    f"{assessment.candidate_id}/{gate.gate_name}: passing gate "
                    "requires source-backed evidence"
                )
        for signal in assessment.identity_signals:
            boundary_evidence_refs.update(signal.evidence_refs)
            referenced = [
                evidence_by_id[evidence_id]
                for evidence_id in signal.evidence_refs
                if evidence_id in evidence_by_id
            ]
            for evidence_id in set(signal.evidence_refs) - set(evidence_by_id):
                issues.append(
                    f"{assessment.candidate_id}/{signal.signal_type}: unknown "
                    f"evidence ref {evidence_id}"
                )
            if signal.status != "pass":
                continue
            allowed_source_types = (
                {"official"}
                if signal.signal_type == "official_destination_treatment"
                else VERIFICATION_SOURCE_TYPES
            )
            if not any(
                evidence.source_type in allowed_source_types for evidence in referenced
            ):
                expected = (
                    "official evidence"
                    if signal.signal_type == "official_destination_treatment"
                    else "official, open_data, or reviewed_editorial evidence"
                )
                issues.append(
                    f"{assessment.candidate_id}/{signal.signal_type}: passing "
                    f"identity signal requires {expected}"
                )

    for candidate_id in sorted(boundary_target_set - set(boundary_assessments)):
        issues.append(f"{candidate_id}: missing destination boundary assessment")
    for candidate_id in sorted(set(boundary_assessments) - boundary_target_set):
        issues.append(f"{candidate_id}: undeclared destination boundary assessment")
    for candidate_id in sorted(boundary_target_set):
        if ("destination", candidate_id) not in reviewed_by_key:
            issues.append(
                f"destination:{candidate_id}: boundary decision target is not "
                "declared in reviewed_targets"
            )

    geometry_target_set = set(report.weather_request_geometry_targets)
    if len(geometry_target_set) != len(report.weather_request_geometry_targets):
        issues.append("weather_request_geometry_targets must be unique")
    geometry_assessments: dict[str, CatalogWeatherRequestGeometryAssessment] = {}
    for assessment in report.weather_request_geometry_assessments:
        if assessment.ski_area_id in geometry_assessments:
            issues.append(
                f"{assessment.ski_area_id}: duplicate weather request geometry "
                "assessment"
            )
        geometry_assessments[assessment.ski_area_id] = assessment
    for ski_area_id in sorted(geometry_target_set - set(geometry_assessments)):
        issues.append(f"{ski_area_id}: missing weather request geometry assessment")
    for ski_area_id in sorted(set(geometry_assessments) - geometry_target_set):
        issues.append(f"{ski_area_id}: undeclared weather request geometry assessment")
    for ski_area_id in sorted(geometry_target_set):
        if ("ski_area", ski_area_id) not in reviewed_by_key:
            issues.append(
                f"ski_area:{ski_area_id}: weather geometry target is not declared "
                "in reviewed_targets"
            )

    for evidence in report.evidence:
        if (
            evidence.target_key not in change_keys
            and evidence.evidence_id not in boundary_evidence_refs
        ):
            issues.append(
                f"{evidence.target_type}:{evidence.target_id} {evidence.field_path}: "
                "evidence has no matching change"
            )

    for change in report.changes:
        matching_evidence = evidence_by_key.get(change.target_key, [])
        if change.ranking_relevant and not matching_evidence:
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                "missing evidence for ranking-relevant change"
            )

        if change.trust_status in SOURCE_BACKED_TRUST_STATUSES:
            has_verification_source = any(
                evidence.source_type in VERIFICATION_SOURCE_TYPES
                for evidence in matching_evidence
            )
            if not matching_evidence:
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    f"missing evidence for {change.trust_status}"
                )
                continue
            if not has_verification_source:
                source_types = ", ".join(
                    sorted({evidence.source_type for evidence in matching_evidence})
                )
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    f"{source_types} source cannot verify {change.trust_status}; "
                    "expected at least one official, open_data, or "
                    "reviewed_editorial source"
                )

        for evidence in matching_evidence:
            if (
                evidence.source_value != change.after
                and not evidence.normalization_note
            ):
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    "normalization_note is required when source_value differs from "
                    "after"
                )

    report_paths_by_target: dict[tuple[str, str], set[str]] = {}
    for change in report.changes:
        report_paths_by_target.setdefault(
            (change.target_type, change.target_id), set()
        ).add(change.field_path)
    for evidence in report.evidence:
        report_paths_by_target.setdefault(
            (evidence.target_type, evidence.target_id), set()
        ).add(evidence.field_path)
    coverage_paths_by_target: dict[tuple[str, str], set[str]] = {}
    for coverage in report.field_coverage:
        coverage_paths_by_target.setdefault(
            (coverage.target_type, coverage.target_id), set()
        ).add(coverage.field_path)

    for target_key, reviewed_target in reviewed_by_key.items():
        expected_paths = set(reviewed_target.canonical_review_paths)
        nested_report_paths = {
            field_path
            for field_path in report_paths_by_target.get(target_key, set())
            if field_path not in CANONICAL_FIELD_PATHS[reviewed_target.target_type]
        }
        expected_paths.update(nested_report_paths)
        for field_path in nested_report_paths:
            expected_paths.update(
                canonical_path
                for canonical_path in CANONICAL_FIELD_PATHS[reviewed_target.target_type]
                if field_path.startswith(f"{canonical_path}[")
                or field_path.startswith(f"{canonical_path}.")
            )
        actual_paths = coverage_paths_by_target.get(target_key, set())
        for field_path in sorted(expected_paths - actual_paths):
            issues.append(
                f"{reviewed_target.target_type}:{reviewed_target.target_id} "
                f"{field_path}: missing field coverage"
            )
        for field_path in sorted(actual_paths - expected_paths):
            issues.append(
                f"{reviewed_target.target_type}:{reviewed_target.target_id} "
                f"{field_path}: field coverage is outside declared review scope"
            )

    added_destination_ids = {
        change.target_id
        for change in report.changes
        if change.target_type == "destination"
        and change.field_path == "resort_id"
        and change.before is None
        and change.after is not None
    }
    for destination_id in sorted(added_destination_ids):
        assessment = boundary_assessments.get(destination_id)
        if destination_id not in boundary_target_set:
            issues.append(
                f"{destination_id}: new destination requires a boundary decision target"
            )
        elif assessment is None:
            issues.append(
                f"{destination_id}: new destination requires a boundary assessment"
            )
        elif not assessment.is_passing:
            issues.append(
                f"{destination_id}: new destination requires a passing boundary "
                "assessment"
            )

    if issues:
        raise CatalogValidationError(sorted(set(issues)))


def render_catalog_curation_report_markdown(report: CatalogCurationReport) -> str:
    lines = [
        f"# {report.title}",
        "",
        report.summary,
        "",
        "## Changed Fields",
        "",
        "| Target | Field | Before | After | Trust | Ranking Relevant |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for change in report.changes:
        target = f"{change.target_type}:{change.target_id}"
        ranking_relevant = "yes" if change.ranking_relevant else "no"
        lines.append(
            "| "
            f"{_code_cell(target)} | "
            f"{_code_cell(change.field_path)} | "
            f"{_json_cell(change.before)} | "
            f"{_json_cell(change.after)} | "
            f"{_code_cell(change.trust_status)} | "
            f"{ranking_relevant} |"
        )

    if report.field_coverage:
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
            target = f"{coverage.target_type}:{coverage.target_id}"
            lines.append(
                "| "
                f"{_code_cell(target)} | "
                f"{_code_cell(coverage.field_path)} | "
                f"{_code_cell(coverage.status)} | "
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
        target = f"{evidence.target_type}:{evidence.target_id}"
        source = _markdown_link(evidence.source_title, evidence.source_url)
        lines.append(
            "| "
            f"{_code_cell(target)} | "
            f"{_code_cell(evidence.field_path)} | "
            f"{source} | "
            f"{_json_cell(evidence.source_value)} | "
            f"{_markdown_cell(evidence.evidence_summary)} | "
            f"{_markdown_cell(evidence.normalization_note or '')} |"
        )

    if report.ranking_comparison_summary:
        lines.extend(["", "## Ranking Impact", "", report.ranking_comparison_summary])

    if report.validation_commands:
        lines.extend(["", "## Verification", ""])
        for command in report.validation_commands:
            lines.append(f"- `{command}`")

    if report.unresolved_caveats:
        lines.extend(["", "## Caveats", ""])
        for caveat in report.unresolved_caveats:
            lines.append(f"- {caveat}")

    lines.append("")
    return "\n".join(lines)
