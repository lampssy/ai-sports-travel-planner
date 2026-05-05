from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]

PriceKind = Literal["fixed", "from", "range", "unknown"]
ExtractionMethod = Literal[
    "registry", "opendatahub", "opendatahub_discovery", "official_page_llm"
]
SourceType = Literal[
    "catalog", "official", "opendatahub", "osm", "wikidata", "provider"
]
ProposalStatus = Literal["new", "changed", "same", "rejected", "conflict"]
FetchStatus = Literal["success", "failed", "skipped"]
ProposalTargetEntityType = Literal["destination", "ski_area"]
OfficialUrlRole = Literal[
    "ski_area",
    "ski_pass",
    "rental",
    "season_dates",
    "trail_map",
    "official_status",
]


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


def _validate_optional_non_blank(value: str | None, field_name: str) -> str | None:
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} cannot be blank")
    return value


class SourceReference(BaseModel):
    source_type: SourceType
    source_url: str | None = None
    source_name: str | None = None
    license: str | None = None

    @field_validator("source_url")
    @classmethod
    def reject_blank_source_url(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank(value, "source_url")

    @field_validator("source_name")
    @classmethod
    def reject_blank_source_name(cls, value: str | None) -> str | None:
        return _validate_optional_non_blank(value, "source_name")

    @model_validator(mode="after")
    def require_url_or_name(self) -> "SourceReference":
        if not self.source_url and not self.source_name:
            raise ValueError("source_url or source_name is required")
        return self


class RegionalDataIds(BaseModel):
    opendatahub_ski_area_id: str | None = None
    osm_relation_id: str | None = None
    wikidata_id: str | None = None


class ResortSourceConfig(BaseModel):
    official_urls: dict[OfficialUrlRole, str] = Field(default_factory=dict)
    provider_urls: dict[str, str] = Field(default_factory=dict)
    regional_data_ids: RegionalDataIds = Field(default_factory=RegionalDataIds)


class SourceRegistry(BaseModel):
    version: int
    resorts: dict[str, ResortSourceConfig] = Field(default_factory=dict)


class LiftPassPriceCandidate(BaseModel):
    duration_days: int = Field(ge=1)
    audience: str = Field(min_length=1)
    amount: float | None = Field(default=None, ge=0)
    amount_min: float | None = Field(default=None, ge=0)
    amount_max: float | None = Field(default=None, ge=0)
    currency: str = Field(min_length=3, max_length=3)
    price_kind: PriceKind
    season_label: str | None = None
    source_url: str
    evidence: str | None = None
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def require_amount_shape(self) -> "LiftPassPriceCandidate":
        if self.price_kind == "range":
            if self.amount is not None:
                raise ValueError("range prices cannot include amount")
            if self.amount_min is None or self.amount_max is None:
                raise ValueError("range prices require amount_min and amount_max")
            if self.amount_min > self.amount_max:
                raise ValueError("amount_min cannot exceed amount_max")
            return self
        if self.price_kind in {"fixed", "from"}:
            if self.amount is None:
                raise ValueError("fixed and from prices require amount")
            if self.amount_min is not None or self.amount_max is not None:
                raise ValueError("fixed and from prices cannot include range amounts")
            return self
        if (
            self.amount is not None
            or self.amount_min is not None
            or self.amount_max is not None
        ):
            raise ValueError("unknown prices cannot include amount values")
        return self


class ProposalTarget(BaseModel):
    entity_type: ProposalTargetEntityType
    entity_id: str = Field(min_length=1)

    @field_validator("entity_id")
    @classmethod
    def reject_blank_entity_id(cls, value: str) -> str:
        return _validate_optional_non_blank(value, "entity_id") or value


class CandidateFact(BaseModel):
    resort_id: str = Field(min_length=1)
    target: ProposalTarget
    field_path: str = Field(min_length=1)
    proposed_value: JsonValue
    source: SourceReference
    extraction_method: ExtractionMethod
    fetched_at: datetime
    confidence: float = Field(ge=0, le=1)
    evidence: str | None = None
    validation_status: Literal["accepted", "rejected"] = "accepted"
    validation_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def default_target_to_destination(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("target") is not None:
            return data
        resort_id = data.get("resort_id")
        if isinstance(resort_id, str) and resort_id.strip():
            return {
                **data,
                "target": {
                    "entity_type": "destination",
                    "entity_id": resort_id,
                },
            }
        return data

    @field_validator("field_path")
    @classmethod
    def reject_blank_segments(cls, value: str) -> str:
        return _validate_field_path(value)

    @field_validator("proposed_value")
    @classmethod
    def reject_non_json_proposed_value(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)


class FetchLogEntry(BaseModel):
    resort_id: str
    url: str
    fetched_at: datetime
    status: FetchStatus
    status_code: int | None = None
    content_hash: str | None = None
    extraction_method: ExtractionMethod | None = None
    truncated: bool = False
    error: str | None = None


class Proposal(BaseModel):
    resort_id: str
    target: ProposalTarget
    field_path: str
    current_value: JsonValue
    proposed_value: JsonValue
    status: ProposalStatus
    source: SourceReference
    extraction_method: ExtractionMethod
    confidence: float = Field(ge=0, le=1)
    evidence: str | None = None
    validation_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def default_target_to_destination(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("target") is not None:
            return data
        resort_id = data.get("resort_id")
        if isinstance(resort_id, str) and resort_id.strip():
            return {
                **data,
                "target": {
                    "entity_type": "destination",
                    "entity_id": resort_id,
                },
            }
        return data

    @field_validator("field_path")
    @classmethod
    def reject_blank_segments(cls, value: str) -> str:
        return _validate_field_path(value)

    @field_validator("current_value", "proposed_value")
    @classmethod
    def reject_non_json_values(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)


class AcquisitionRunOutput(BaseModel):
    generated_at: datetime
    selected_resorts: list[str]
    proposals: list[Proposal]
    candidates: list[CandidateFact]
    fetch_log: list[FetchLogEntry]
