from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ops.maintainer.errors import (
    ErrorCheck,
    ErrorKind,
    ErrorReason,
    ErrorStage,
    MaintainerError,
)

_CANDIDATE_ID_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class BoundaryGateAssessment(_StrictModel):
    status: Literal["pass", "fail", "evidence_insufficient"]
    evidence_refs: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1, max_length=1000)

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("gate evidence refs must not be blank")
        if len(set(values)) != len(values):
            raise ValueError("gate evidence refs must be unique")
        return values


class MaterialTripConsequence(_StrictModel):
    consequence_type: Literal[
        "pass_price_or_coverage",
        "stay_access_or_transfer_mechanics",
        "weather_or_season_suitability",
        "terrain_character_or_party_skill_fit",
    ]
    decision_effect: Literal[
        "selected_ski_area",
        "stay_to_ski_configuration",
        "lift_pass_choice",
        "conditions_evidence_profile",
    ]
    comparison_basis: Literal[
        "parent_ski_area",
        "sibling_ski_area",
        "stay_market_baseline",
    ]
    comparison_target_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_CANDIDATE_ID_PATTERN,
    )
    evidence_refs: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1, max_length=1000)

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("material consequence evidence refs must not be blank")
        if len(set(values)) != len(values):
            raise ValueError("material consequence evidence refs must be unique")
        return values


class SkiAreaBoundaryCandidate(_StrictModel):
    candidate_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=_CANDIDATE_ID_PATTERN,
    )
    decision: Literal[
        "separate_ski_area",
        "fold_into_parent",
        "evidence_insufficient",
    ]
    parent_ski_area_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=_CANDIDATE_ID_PATTERN,
    )
    stay_destination_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=_CANDIDATE_ID_PATTERN,
    )
    terrain_gate: BoundaryGateAssessment
    evidence_ownership_gate: BoundaryGateAssessment
    materiality_gate: BoundaryGateAssessment
    material_trip_consequence: MaterialTripConsequence | None = None

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        gates = (
            self.terrain_gate,
            self.evidence_ownership_gate,
            self.materiality_gate,
        )
        all_gates_pass = all(gate.status == "pass" for gate in gates)

        if self.decision == "separate_ski_area":
            if not all_gates_pass:
                raise ValueError("separate ski area requires all three gates to pass")
            if self.material_trip_consequence is None:
                raise ValueError(
                    "separate ski area requires a material trip consequence"
                )
        elif self.decision == "fold_into_parent":
            if self.parent_ski_area_id is None:
                raise ValueError("folded candidate requires a parent ski area")
            if self.parent_ski_area_id == self.candidate_id:
                raise ValueError("folded candidate cannot name itself as parent")
            if all_gates_pass:
                raise ValueError(
                    "candidate with all three gates passing cannot be folded"
                )
        else:
            if not any(gate.status == "evidence_insufficient" for gate in gates):
                raise ValueError(
                    "evidence-insufficient candidate requires an insufficient gate"
                )

        if (
            self.materiality_gate.status == "pass"
            and self.material_trip_consequence is None
        ):
            raise ValueError(
                "passed materiality gate requires a material trip consequence"
            )
        if (
            self.materiality_gate.status != "pass"
            and self.material_trip_consequence is not None
        ):
            raise ValueError(
                "material trip consequence requires a passed materiality gate"
            )
        return self


class BoundaryAdjudication(_StrictModel):
    outcome: Literal[
        "policy_determined",
        "owner_choice_required",
        "evidence_insufficient",
    ]
    candidates: list[SkiAreaBoundaryCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_candidates(self) -> Self:
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("boundary adjudication candidate IDs must be unique")

        candidates_by_id = {
            candidate.candidate_id: candidate for candidate in self.candidates
        }
        if self.outcome == "policy_determined" and any(
            candidate.decision == "evidence_insufficient"
            for candidate in self.candidates
        ):
            raise ValueError(
                "policy-determined adjudication cannot retain an "
                "evidence-insufficient candidate"
            )
        if self.outcome == "evidence_insufficient" and not any(
            candidate.decision == "evidence_insufficient"
            for candidate in self.candidates
        ):
            raise ValueError(
                "evidence-insufficient adjudication requires an insufficient candidate"
            )

        for candidate in self.candidates:
            consequence = candidate.material_trip_consequence
            if consequence is None:
                continue
            if consequence.comparison_basis == "parent_ski_area":
                if consequence.comparison_target_id != candidate.parent_ski_area_id:
                    raise ValueError(
                        "parent comparison target must equal the declared "
                        "parent ski area"
                    )
            elif consequence.comparison_basis == "sibling_ski_area":
                target = candidates_by_id.get(consequence.comparison_target_id)
                if (
                    target is None
                    or target.candidate_id == candidate.candidate_id
                    or target.decision != "separate_ski_area"
                    or target.parent_ski_area_id != candidate.parent_ski_area_id
                ):
                    raise ValueError(
                        "sibling comparison target must be a distinct separate "
                        "ski area with the same parent"
                    )
            elif consequence.comparison_target_id != candidate.stay_destination_id:
                raise ValueError(
                    "stay-market comparison target must equal the declared "
                    "stay destination"
                )
        return self


class BoundaryAdjudicationValidationResult(_StrictModel):
    outcome: Literal[
        "policy_determined",
        "owner_choice_required",
        "evidence_insufficient",
    ]
    separate_ski_area_ids: tuple[str, ...]
    folded_candidate_ids: tuple[str, ...]
    evidence_insufficient_candidate_ids: tuple[str, ...]


def validate_boundary_adjudication(
    path: Path,
) -> BoundaryAdjudicationValidationResult:
    """Validate a run-local ski-area boundary decision before fixer authority."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        adjudication = BoundaryAdjudication.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise MaintainerError(
            ErrorReason.VALIDATION_FAILED,
            ErrorStage.VALIDATE,
            check=ErrorCheck.BOUNDARY_ADJUDICATION,
            kind=ErrorKind.MISMATCH,
            detail="Boundary adjudication does not satisfy ski-area gate policy",
        ) from exc

    return BoundaryAdjudicationValidationResult(
        outcome=adjudication.outcome,
        separate_ski_area_ids=tuple(
            sorted(
                candidate.candidate_id
                for candidate in adjudication.candidates
                if candidate.decision == "separate_ski_area"
            )
        ),
        folded_candidate_ids=tuple(
            sorted(
                candidate.candidate_id
                for candidate in adjudication.candidates
                if candidate.decision == "fold_into_parent"
            )
        ),
        evidence_insufficient_candidate_ids=tuple(
            sorted(
                candidate.candidate_id
                for candidate in adjudication.candidates
                if candidate.decision == "evidence_insufficient"
            )
        ),
    )
