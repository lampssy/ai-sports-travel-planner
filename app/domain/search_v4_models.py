from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

GroupImportance = Literal[
    "ignore",
    "secondary",
    "normal",
    "important",
    "primary",
    "very_high",
]
FactorImportance = Literal["low", "normal", "high"]
PreferenceMode = Literal["prefer", "avoid", "ignore", "require"]
SkillLevel = Literal["beginner", "intermediate", "advanced"]
TravelMode = Literal["car", "rail", "public_transport", "flight"]

_NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
SearchIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]
_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")


class _SearchV4Model(BaseModel):
    model_config = _MODEL_CONFIG


class TravelWindow(_SearchV4Model):
    """A month-level or exact-date search window.

    Exact dates take precedence when both representations are supplied. The
    month remains useful as the original interpretation and for explanations.
    """

    month: int | None = Field(default=None, ge=1, le=12)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("start_date and end_date must be provided together")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must be on or after start_date")
        if (
            self.start_date is not None
            and self.end_date is not None
            and (self.end_date - self.start_date).days + 1 > 366
        ):
            raise ValueError("exact travel windows cannot exceed 366 days")
        if self.month is None and self.start_date is None:
            raise ValueError("travel window needs a month or exact dates")
        return self

    @property
    def mode(self) -> Literal["month", "exact_dates"]:
        return "exact_dates" if self.start_date is not None else "month"

    @property
    def ski_day_count(self) -> int | None:
        if self.start_date is None or self.end_date is None:
            return None
        return (self.end_date - self.start_date).days + 1


class LocationScope(_SearchV4Model):
    country: _NonBlankText | None = None
    region: _NonBlankText | None = None
    ski_region_ids: tuple[SearchIdentifier, ...] = Field(default=(), max_length=100)
    destination_ids: tuple[SearchIdentifier, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def require_scope(self) -> Self:
        if not any(
            (
                self.country,
                self.region,
                self.ski_region_ids,
                self.destination_ids,
            )
        ):
            raise ValueError("location scope must include at least one selector")
        return self


class LodgingBudgetConstraint(_SearchV4Model):
    mode: Literal["lodging_nightly", "total_trip"]
    maximum: float = Field(gt=0)
    currency: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3)
    ]
    budget_flex: float = Field(default=0, ge=0, le=0.5)

    @property
    def effective_flex(self) -> float:
        return max(0.10, self.budget_flex)

    @property
    def effective_maximum(self) -> float:
        return self.maximum * (1 + self.effective_flex)


class TravelLimitConstraint(_SearchV4Model):
    maximum_duration_hours: float = Field(gt=0)
    mode: TravelMode


class MinimumStayQualityConstraint(_SearchV4Model):
    minimum_score: float = Field(ge=0, le=10)


class FactorRequirement(_SearchV4Model):
    factor_id: SearchIdentifier
    values: tuple[_NonBlankText, ...] = Field(default=(), max_length=20)
    minimum_trust: Literal["estimated", "verified_with_adjustment", "verified"]


class PassPriceCeilingConstraint(_SearchV4Model):
    maximum: float = Field(gt=0)
    currency: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3)
    ]
    duration_days: int = Field(gt=0)
    audience: _NonBlankText
    season: _NonBlankText


class SearchConstraints(_SearchV4Model):
    location: LocationScope | None = None
    travel_window: TravelWindow | None = None
    lodging_budget: LodgingBudgetConstraint | None = None
    travel_limit: TravelLimitConstraint | None = None
    minimum_stay_quality: MinimumStayQualityConstraint | None = None
    factor_requirements: tuple[FactorRequirement, ...] = ()
    pass_price_ceiling: PassPriceCeilingConstraint | None = None

    @model_validator(mode="after")
    def validate_requirements(self) -> Self:
        ids = [requirement.factor_id for requirement in self.factor_requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("factor requirement IDs must be unique")
        return self


class PartyContext(_SearchV4Model):
    skill_levels: tuple[SkillLevel, ...] = ()

    @model_validator(mode="after")
    def validate_skill_levels(self) -> Self:
        if len(self.skill_levels) != len(set(self.skill_levels)):
            raise ValueError("party skill levels must be unique")
        return self


class TravelContext(_SearchV4Model):
    origin_text: _NonBlankText | None = None
    mode: TravelMode | None = None


class GroupPriorityPatch(_SearchV4Model):
    group_id: SearchIdentifier
    importance: GroupImportance = "normal"


class FactorPreferencePatch(_SearchV4Model):
    factor_id: SearchIdentifier
    mode: PreferenceMode
    values: tuple[_NonBlankText, ...] = Field(default=(), max_length=20)
    importance: FactorImportance = "normal"


class SearchObjective(_SearchV4Model):
    factor_id: SearchIdentifier
    importance: FactorImportance = "normal"


class SearchIntent(_SearchV4Model):
    constraints: SearchConstraints = Field(default_factory=SearchConstraints)
    party: PartyContext = Field(default_factory=PartyContext)
    travel_context: TravelContext = Field(default_factory=TravelContext)
    objectives: tuple[SearchObjective, ...] = Field(default=(), max_length=100)
    group_priorities: tuple[GroupPriorityPatch, ...] = Field(default=(), max_length=100)
    factor_preferences: tuple[FactorPreferencePatch, ...] = Field(
        default=(), max_length=100
    )
    assumptions: tuple[_NonBlankText, ...] = Field(default=(), max_length=20)

    @model_validator(mode="after")
    def validate_patches(self) -> Self:
        self._require_unique_ids(
            "group priority", [item.group_id for item in self.group_priorities]
        )
        self._require_unique_ids(
            "factor preference",
            [item.factor_id for item in self.factor_preferences],
        )
        self._require_unique_ids(
            "objective", [item.factor_id for item in self.objectives]
        )
        objective_ids = {item.factor_id for item in self.objectives}
        preference_ids = {item.factor_id for item in self.factor_preferences}
        overlap = sorted(objective_ids & preference_ids)
        if overlap:
            raise ValueError(
                "a factor cannot be both objective and preference: "
                + ", ".join(overlap)
            )
        return self

    @staticmethod
    def _require_unique_ids(kind: str, values: list[str]) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"{kind} IDs must be unique")
