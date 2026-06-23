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


def _target_key(
    target_type: str, target_id: str, field_path: str
) -> tuple[str, str, str]:
    return (target_type, target_id, field_path)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _json_cell(value: JsonValue) -> str:
    return _code_cell(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _markdown_cell(value: str) -> str:
    single_line = " ".join(line.strip() for line in value.splitlines())
    return single_line.replace("|", "\\|")


def _code_cell(value: str) -> str:
    return f"`{_markdown_cell(value)}`"


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

    @field_validator("target_id")
    @classmethod
    def reject_blank_target_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "target_id")

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
    source_value: JsonValue
    evidence_summary: str = Field(min_length=1)
    normalization_note: str | None = None

    @field_validator("field_path")
    @classmethod
    def reject_blank_segments(cls, value: str) -> str:
        return _validate_field_path(value)

    @field_validator("target_id")
    @classmethod
    def reject_blank_target_id(cls, value: str) -> str:
        return _validate_non_blank_string(value, "target_id")

    @field_validator("source_url")
    @classmethod
    def require_http_source_url(cls, value: str) -> str:
        value = _validate_non_blank_string(value, "source_url")
        if not _is_http_url(value):
            raise ValueError("source_url must be an http(s) URL")
        return value

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
    evidence_by_key: dict[tuple[str, str, str], list[CatalogEvidenceItem]] = {}
    for evidence in report.evidence:
        evidence_by_key.setdefault(evidence.target_key, []).append(evidence)

    for change in report.changes:
        matching_evidence = evidence_by_key.get(change.target_key, [])
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
        source = f"[{_markdown_cell(evidence.source_title)}]({evidence.source_url})"
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
