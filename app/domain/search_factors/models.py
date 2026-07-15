from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    computed_field,
)


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


def _serialize_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return dict(value)


FrozenMapping = Annotated[
    Mapping[str, Any],
    AfterValidator(_freeze_mapping),
    PlainSerializer(_serialize_mapping, return_type=dict[str, Any]),
]


class FactorEvaluation(BaseModel):
    """One factor's source-aware, pre-scoring evaluation for one candidate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    factor_id: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    entity_ids: tuple[str, ...]
    raw_value: Any
    raw_utility: float = Field(ge=0, le=1)
    neutral_utility: float = Field(ge=0, le=1)
    effective_evidence_cap: float = Field(ge=0, le=1)
    evidence_cap_components: FrozenMapping
    warnings: tuple[str, ...]
    provenance_summary: str = Field(min_length=1)
    explanation_inputs: FrozenMapping

    @computed_field  # type: ignore[prop-decorator]
    @property
    def effective_utility(self) -> float:
        return self.neutral_utility + self.effective_evidence_cap * (
            self.raw_utility - self.neutral_utility
        )
