from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

CatalogTargetType = Literal["destination", "ski_area", "stay_base", "rental"]
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
CatalogIssueSeverity = Literal["error", "warning"]
JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]

SOURCE_BACKED_TRUST_STATUSES = {"verified", "verified_with_adjustment"}
VERIFICATION_SOURCE_TYPES = {"official", "open_data", "reviewed_editorial"}


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


def _validate_field_path(value: str) -> str:
    segments = value.split(".")
    if any(not segment.strip() for segment in segments):
        raise ValueError("field_path cannot contain blank segments")
    if any(segment != segment.strip() for segment in segments):
        raise ValueError(
            "field_path segments cannot contain leading or trailing whitespace"
        )
    return value


def _target_key(
    target_type: str, target_id: str, field_path: str
) -> tuple[str, str, str]:
    return (target_type, target_id, field_path)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _json_cell(value: JsonValue) -> str:
    return f"`{json.dumps(value, ensure_ascii=False, sort_keys=True)}`"


class CatalogValidationError(ValueError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(issues))


class CatalogValidationIssue(BaseModel):
    severity: CatalogIssueSeverity
    message: str = Field(min_length=1)
    target_type: CatalogTargetType | None = None
    target_id: str | None = None
    field_path: str | None = None


class CatalogChangeSummary(BaseModel):
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

    @field_validator("before", "after")
    @classmethod
    def reject_non_json_value(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)

    @property
    def target_key(self) -> tuple[str, str, str]:
        return _target_key(self.target_type, self.target_id, self.field_path)


class CatalogEvidenceItem(BaseModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    source_type: CatalogSourceType
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_value: JsonValue = None
    evidence_summary: str = Field(min_length=1)
    normalization_note: str | None = None

    @field_validator("field_path")
    @classmethod
    def reject_blank_segments(cls, value: str) -> str:
        return _validate_field_path(value)

    @field_validator("source_url")
    @classmethod
    def require_http_source_url(cls, value: str) -> str:
        if not _is_http_url(value):
            raise ValueError("source_url must be an http(s) URL")
        return value

    @field_validator("source_value")
    @classmethod
    def reject_non_json_source_value(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)

    @property
    def target_key(self) -> tuple[str, str, str]:
        return _target_key(self.target_type, self.target_id, self.field_path)


class CatalogCurationReport(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    changed_entities: list[str] = Field(default_factory=list)
    changes: list[CatalogChangeSummary] = Field(default_factory=list)
    evidence: list[CatalogEvidenceItem] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    ranking_comparison_summary: str | None = None
    unresolved_caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_changes(self) -> CatalogCurationReport:
        if not self.changes:
            raise ValueError("curation report must include at least one change")
        return self


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
    evidence_by_key: dict[tuple[str, str, str], list[CatalogEvidenceItem]] = {}
    for evidence in report.evidence:
        evidence_by_key.setdefault(evidence.target_key, []).append(evidence)

    for change in report.changes:
        matching_evidence = evidence_by_key.get(change.target_key, [])
        if (
            change.trust_status in SOURCE_BACKED_TRUST_STATUSES
            and not matching_evidence
        ):
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: "
                f"missing evidence for {change.trust_status}"
            )
            continue

        for evidence in matching_evidence:
            if (
                change.trust_status in SOURCE_BACKED_TRUST_STATUSES
                and evidence.source_type not in VERIFICATION_SOURCE_TYPES
            ):
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    f"{evidence.source_type} source cannot verify "
                    f"{change.trust_status}"
                )
            if (
                evidence.source_value != change.after
                and not evidence.normalization_note
            ):
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    "normalization_note is required when source_value differs from "
                    "after"
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
            f"`{target}` | "
            f"`{change.field_path}` | "
            f"{_json_cell(change.before)} | "
            f"{_json_cell(change.after)} | "
            f"`{change.trust_status}` | "
            f"{ranking_relevant} |"
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
        source = f"[{evidence.source_title}]({evidence.source_url})"
        lines.append(
            "| "
            f"`{target}` | "
            f"`{evidence.field_path}` | "
            f"{source} | "
            f"{_json_cell(evidence.source_value)} | "
            f"{evidence.evidence_summary} | "
            f"{evidence.normalization_note or ''} |"
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
