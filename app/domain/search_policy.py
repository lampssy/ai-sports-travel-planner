from __future__ import annotations

import tomllib
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    field_validator,
    model_validator,
)

FactorLifecycle = Literal["planned", "diagnostic", "measured", "active", "retired"]
FactorRole = Literal[
    "constraint",
    "ranking",
    "clarification",
    "explanation",
    "diagnostic",
]
ActivationMode = Literal[
    "always",
    "context_available",
    "when_requested",
    "objective_selected",
    "never",
]
PreferenceMode = Literal["prefer", "avoid", "ignore", "require"]
EvidenceMode = Literal[
    "comparative",
    "positive_presence",
    "categorical_match",
    "objective_comparison",
    "composed_prediction",
    "measured_only",
    "planned",
]
InputSource = Literal["client", "llm", "system"]
CorrelationMode = Literal["informational", "capped"]

_NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")
DEFAULT_SEARCH_POLICY_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "search-ranking" / "search-v4.toml"
)
INVENTORY_START = "<!-- search-v4-policy-inventory:start -->"
INVENTORY_END = "<!-- search-v4-policy-inventory:end -->"


def _freeze_float_mapping(value: Mapping[str, float]) -> Mapping[str, float]:
    return MappingProxyType(dict(value))


def _serialize_float_mapping(value: Mapping[str, float]) -> dict[str, float]:
    return dict(value)


_FloatMapping = Annotated[
    Mapping[_NonBlankText, float],
    AfterValidator(_freeze_float_mapping),
    PlainSerializer(_serialize_float_mapping, return_type=dict[str, float]),
]


class _PolicyModel(BaseModel):
    model_config = _MODEL_CONFIG


class ReadinessPolicy(_PolicyModel):
    policy_id: _NonBlankText
    minimum_resolved_coverage: float | None = Field(default=None, ge=0, le=1)
    minimum_average_evidence_strength: float | None = Field(default=None, ge=0, le=1)
    minimum_verified_positive_count: int | None = Field(default=None, ge=1)
    minimum_distinct_trusted_utilities: int | None = Field(default=None, ge=2)


class GroupPolicy(_PolicyModel):
    group_id: _NonBlankText
    label: _NonBlankText
    description: _NonBlankText
    default_budget: float = Field(gt=0)
    max_effective_share: float = Field(default=1, gt=0, le=1)
    allowed_importance_labels: tuple[_NonBlankText, ...]
    clarifiable: bool
    llm_description: _NonBlankText | None = None

    @field_validator("allowed_importance_labels")
    @classmethod
    def validate_importance_labels(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("allowed_importance_labels must not be empty")
        if len(value) != len(set(value)):
            raise ValueError("allowed_importance_labels must be unique")
        return value


class ConstraintPolicy(_PolicyModel):
    constraint_id: _NonBlankText
    label: _NonBlankText
    description: _NonBlankText
    value_type: _NonBlankText
    allowed_input_sources: tuple[InputSource, ...]
    required_context: tuple[_NonBlankText, ...] = ()
    minimum_trust: _NonBlankText | None = None
    clarifiable: bool = False


class CorrelationPolicy(_PolicyModel):
    correlation_group_id: _NonBlankText
    description: _NonBlankText
    mode: CorrelationMode
    max_combined_effective_weight: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_correlation_shape(self) -> Self:
        if self.mode == "capped" and self.max_combined_effective_weight is None:
            raise ValueError("capped correlation groups require a maximum weight")
        if (
            self.mode == "informational"
            and self.max_combined_effective_weight is not None
        ):
            raise ValueError("informational correlation groups cannot define a cap")
        return self


class FactorPolicy(_PolicyModel):
    factor_id: _NonBlankText
    label: _NonBlankText
    description: _NonBlankText
    group_id: _NonBlankText | None = None
    scope: _NonBlankText
    evidence_kind: _NonBlankText
    value_type: _NonBlankText
    evaluator_id: _NonBlankText | None = None
    lifecycle: FactorLifecycle
    activation: ActivationMode
    roles: tuple[FactorRole, ...]
    allowed_modes: tuple[PreferenceMode, ...] = ()
    allowed_values: tuple[_NonBlankText, ...] = ()
    base_weight: float = Field(default=0, ge=0)
    neutral_utility: float = Field(default=0.5, ge=0, le=1)
    evidence_mode: EvidenceMode
    readiness: ReadinessPolicy
    evidence_cap_policy: _NonBlankText
    correlation_group: _NonBlankText | None = None
    clarifiable: bool = False
    llm_description: _NonBlankText | None = None
    qualifier_policy: _NonBlankText | None = None
    composition_target: _NonBlankText | None = None
    composition_policy: _NonBlankText | None = None

    @field_validator("roles", "allowed_modes", "allowed_values")
    @classmethod
    def validate_unique_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("configured values must be unique")
        return value

    @model_validator(mode="after")
    def validate_factor_shape(self) -> Self:
        if self.clarifiable and "clarification" not in self.roles:
            raise ValueError("clarifiable factors require the clarification role")
        if self.clarifiable and self.llm_description is None:
            raise ValueError("clarifiable factors require an llm_description")
        if self.composition_target is None and self.composition_policy is not None:
            raise ValueError("composition_policy requires composition_target")
        if self.composition_target is not None and self.composition_policy is None:
            raise ValueError("composition_target requires composition_policy")
        if self.lifecycle not in {"planned", "retired"} and self.evaluator_id is None:
            raise ValueError("non-planned factors require evaluator_id")
        if self.lifecycle == "active" and "ranking" in self.roles:
            independent = self.composition_target is None
            if independent and self.base_weight <= 0:
                raise ValueError(
                    "active independent ranking factors need positive base_weight"
                )
            if independent and self.group_id is None:
                raise ValueError("active independent ranking factors require group_id")
        if self.base_weight > 0 and "ranking" not in self.roles:
            raise ValueError("positive base_weight requires ranking role")
        self._validate_readiness_shape()
        return self

    def _validate_readiness_shape(self) -> None:
        readiness = self.readiness
        if self.evidence_mode in {"comparative", "objective_comparison"}:
            if readiness.minimum_resolved_coverage is None:
                raise ValueError(
                    f"{self.evidence_mode} requires minimum_resolved_coverage"
                )
            if readiness.minimum_average_evidence_strength is None:
                raise ValueError(
                    f"{self.evidence_mode} requires minimum_average_evidence_strength"
                )
        if (
            self.evidence_mode == "positive_presence"
            and readiness.minimum_verified_positive_count is None
        ):
            raise ValueError(
                "positive_presence requires minimum_verified_positive_count"
            )
        if (
            self.evidence_mode == "categorical_match"
            and readiness.minimum_distinct_trusted_utilities is None
        ):
            raise ValueError(
                "categorical_match requires minimum_distinct_trusted_utilities"
            )


class RefinementPolicy(_PolicyModel):
    max_questions: int = Field(ge=0, le=3)
    max_options_per_question: int = Field(ge=2, le=5)
    max_factor_patches_per_option: int = Field(ge=1, le=5)
    max_candidate_summaries: int = Field(ge=1, le=50)
    max_clarifiable_factors: int = Field(ge=1, le=100)
    max_question_characters: int = Field(ge=40, le=1000)
    max_option_label_characters: int = Field(ge=10, le=200)
    max_option_description_characters: int = Field(ge=20, le=1000)
    max_llm_retries: int = Field(ge=0, le=1)
    eligibility_change_is_material: bool
    winner_change_is_material: bool
    top_three_membership_change_is_material: bool
    top_three_order_margin_points: float = Field(ge=0, le=100)
    top_five_candidate_difference_points: float = Field(ge=0, le=100)


class WeatherRankingPolicy(_PolicyModel):
    policy_version: _NonBlankText
    depth_curve_values: tuple[float, ...]
    depth_curve_utilities: tuple[float, ...]
    fresh_snow_curve_values: tuple[float, ...]
    fresh_snow_curve_utilities: tuple[float, ...]
    rain_curve_values: tuple[float, ...]
    rain_curve_utilities: tuple[float, ...]
    thaw_curve_values: tuple[float, ...]
    thaw_curve_utilities: tuple[float, ...]
    fresh_snow_coefficient: float = Field(ge=0, le=1)
    rain_thaw_risk_coefficient: float = Field(ge=0, le=1)
    climatology_typical_depth_coefficient: float = Field(ge=0, le=1)
    climatology_probability_30cm_coefficient: float = Field(ge=0, le=1)
    climatology_probability_50cm_coefficient: float = Field(ge=0, le=1)
    climatology_deterioration_coefficient: float = Field(ge=0, le=1)
    strong_snow_fit_threshold: float = Field(ge=0, le=1)
    minimum_snow_assessment_coverage: float = Field(gt=0, le=1)
    lead_time_max_days: tuple[int, ...]
    lead_time_forecast_shares: tuple[float, ...]
    preferred_short_range_source: _NonBlankText
    fallback_and_long_range_source: _NonBlankText
    preferred_short_range_max_lead_days: int = Field(ge=0)
    maximum_forecast_lead_days: int = Field(ge=0)
    snowmaking_need_full_below: float = Field(ge=0, le=1)
    snowmaking_need_zero_at: float = Field(ge=0, le=1)
    snowmaking_uplift_coefficient: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_weather_policy(self) -> Self:
        curves = (
            (
                "depth",
                self.depth_curve_values,
                self.depth_curve_utilities,
            ),
            (
                "fresh_snow",
                self.fresh_snow_curve_values,
                self.fresh_snow_curve_utilities,
            ),
            ("rain", self.rain_curve_values, self.rain_curve_utilities),
            ("thaw", self.thaw_curve_values, self.thaw_curve_utilities),
        )
        for name, values, utilities in curves:
            if len(values) < 2 or len(values) != len(utilities):
                raise ValueError(
                    f"{name} curve needs equally sized value and utility arrays"
                )
            if any(right <= left for left, right in zip(values, values[1:])):
                raise ValueError(f"{name} curve values must strictly increase")
            if any(utility < 0 or utility > 1 for utility in utilities):
                raise ValueError(f"{name} curve utilities must be between zero and one")
        if not self.lead_time_max_days or len(self.lead_time_max_days) != len(
            self.lead_time_forecast_shares
        ):
            raise ValueError(
                "lead-time boundaries and forecast shares must be equally sized"
            )
        if any(
            right <= left
            for left, right in zip(
                self.lead_time_max_days,
                self.lead_time_max_days[1:],
            )
        ):
            raise ValueError("lead-time boundaries must strictly increase")
        if any(share < 0 or share > 1 for share in self.lead_time_forecast_shares):
            raise ValueError("forecast shares must be between zero and one")
        if self.maximum_forecast_lead_days != self.lead_time_max_days[-1]:
            raise ValueError(
                "maximum forecast lead must match the final lead-time boundary"
            )
        if self.preferred_short_range_max_lead_days > self.maximum_forecast_lead_days:
            raise ValueError("preferred source lead cannot exceed forecast maximum")
        if self.snowmaking_need_full_below >= self.snowmaking_need_zero_at:
            raise ValueError(
                "snowmaking full-need threshold must be below zero-need threshold"
            )
        climatology_positive_weight = (
            self.climatology_typical_depth_coefficient
            + self.climatology_probability_30cm_coefficient
            + self.climatology_probability_50cm_coefficient
        )
        if abs(climatology_positive_weight - 1) > 1e-9:
            raise ValueError(
                "positive climatology reliability coefficients must sum to one"
            )
        return self


class SearchPolicy(_PolicyModel):
    search_model_version: Literal["search-v4"]
    ranking_policy_version: _NonBlankText
    group_importance_multipliers: _FloatMapping
    factor_importance_multipliers: _FloatMapping
    groups: tuple[GroupPolicy, ...]
    correlations: tuple[CorrelationPolicy, ...] = ()
    constraints: tuple[ConstraintPolicy, ...]
    factors: tuple[FactorPolicy, ...]
    refinement: RefinementPolicy
    weather: WeatherRankingPolicy

    @model_validator(mode="after")
    def validate_policy_relationships(self) -> Self:
        self._require_unique_ids("group", [group.group_id for group in self.groups])
        self._require_unique_ids(
            "constraint", [constraint.constraint_id for constraint in self.constraints]
        )
        self._require_unique_ids(
            "correlation group",
            [item.correlation_group_id for item in self.correlations],
        )
        self._require_unique_ids(
            "factor", [factor.factor_id for factor in self.factors]
        )
        group_ids = {group.group_id for group in self.groups}
        factor_ids = {factor.factor_id for factor in self.factors}
        correlation_group_ids = {
            item.correlation_group_id for item in self.correlations
        }
        importance_labels = set(self.group_importance_multipliers)
        if not self.groups:
            raise ValueError("at least one group is required")
        if sum(group.max_effective_share for group in self.groups) < 1:
            raise ValueError("group maximum shares cannot form a complete allocation")
        for group in self.groups:
            unsupported = set(group.allowed_importance_labels) - importance_labels
            if unsupported:
                raise ValueError(
                    f"group {group.group_id} uses unknown importance labels: "
                    f"{', '.join(sorted(unsupported))}"
                )
        for factor in self.factors:
            if factor.group_id is not None and factor.group_id not in group_ids:
                raise ValueError(
                    f"factor {factor.factor_id} references unknown group "
                    f"{factor.group_id}"
                )
            if (
                factor.composition_target is not None
                and factor.composition_target not in factor_ids
            ):
                raise ValueError(
                    f"factor {factor.factor_id} references unknown composition target "
                    f"{factor.composition_target}"
                )
            if (
                factor.correlation_group is not None
                and factor.correlation_group not in correlation_group_ids
            ):
                raise ValueError(
                    f"factor {factor.factor_id} references unknown correlation group "
                    f"{factor.correlation_group}"
                )
        if any(value < 0 for value in self.group_importance_multipliers.values()):
            raise ValueError("group importance multipliers must be non-negative")
        if any(value <= 0 for value in self.factor_importance_multipliers.values()):
            raise ValueError("factor importance multipliers must be positive")
        return self

    @staticmethod
    def _require_unique_ids(kind: str, values: list[str]) -> None:
        duplicates = sorted(
            value for value, count in Counter(values).items() if count > 1
        )
        if duplicates:
            raise ValueError(f"{kind} IDs must be unique: {', '.join(duplicates)}")

    def group(self, group_id: str) -> GroupPolicy:
        for group in self.groups:
            if group.group_id == group_id:
                return group
        raise KeyError(group_id)

    def factor(self, factor_id: str) -> FactorPolicy:
        for factor in self.factors:
            if factor.factor_id == factor_id:
                return factor
        raise KeyError(factor_id)

    @property
    def factors_requiring_evaluators(self) -> tuple[FactorPolicy, ...]:
        return tuple(
            factor
            for factor in self.factors
            if factor.lifecycle not in {"planned", "retired"}
        )


def load_search_policy(path: Path | None = None) -> SearchPolicy:
    policy_path = path or DEFAULT_SEARCH_POLICY_PATH
    with policy_path.open("rb") as policy_file:
        payload = tomllib.load(policy_file)
    return SearchPolicy.model_validate(payload)


def render_policy_inventory(
    policy: SearchPolicy,
    *,
    evaluator_statuses: Mapping[str, str],
) -> str:
    lifecycle_counts = Counter(factor.lifecycle for factor in policy.factors)
    total_group_budget = sum(group.default_budget for group in policy.groups)
    active_group_weight_totals = {
        group.group_id: sum(
            factor.base_weight
            for factor in policy.factors
            if factor.lifecycle == "active"
            and factor.group_id == group.group_id
            and factor.composition_target is None
            and "ranking" in factor.roles
        )
        for group in policy.groups
    }
    lines = [
        "#### Generated Search V4 Policy Inventory",
        "",
        f"- Search model: `{policy.search_model_version}`",
        f"- Ranking policy: `{policy.ranking_policy_version}`",
        f"- Active factors: `{lifecycle_counts['active']}`",
        "- Measured or diagnostic factors: "
        f"`{lifecycle_counts['measured'] + lifecycle_counts['diagnostic']}`",
        f"- Planned factors: `{lifecycle_counts['planned']}`",
        "",
        "##### Groups",
        "",
        "| Group | Default budget | Maximum effective share | Clarifiable |",
        "| --- | ---: | ---: | --- |",
    ]
    for group in policy.groups:
        lines.append(
            f"| `{group.group_id}` | {group.default_budget:g} | "
            f"{group.max_effective_share:.2f} | {_yes_no(group.clarifiable)} |"
        )
    lines.extend(
        [
            "",
            "##### Correlation Groups",
            "",
            "| Correlation group | Mode | Maximum combined effective weight |",
            "| --- | --- | ---: |",
        ]
    )
    if policy.correlations:
        for correlation in policy.correlations:
            maximum = (
                f"{correlation.max_combined_effective_weight:g}"
                if correlation.max_combined_effective_weight is not None
                else "—"
            )
            lines.append(
                f"| `{correlation.correlation_group_id}` | "
                f"`{correlation.mode}` | {maximum} |"
            )
    else:
        lines.append("| — | — | — |")
    lines.extend(
        [
            "",
            "##### Constraints",
            "",
            "| Constraint | Value type | Inputs | Clarifiable |",
            "| --- | --- | --- | --- |",
        ]
    )
    for constraint in policy.constraints:
        lines.append(
            f"| `{constraint.constraint_id}` | `{constraint.value_type}` | "
            f"{', '.join(constraint.allowed_input_sources)} | "
            f"{_yes_no(constraint.clarifiable)} |"
        )
    lines.extend(
        [
            "",
            "##### Factors",
            "",
            "| Factor | Lifecycle | Group | Weight | All-eligible default max | "
            "Activation | Evidence mode | Neutral | Readiness | Cap policy | "
            "Correlation | Clarifiable |",
            "| --- | --- | --- | ---: | ---: | --- | --- | ---: | --- | "
            "--- | --- | --- |",
        ]
    )
    for factor in policy.factors:
        composition = ""
        if factor.composition_target is not None:
            composition = (
                f"; composition `{factor.composition_policy}` -> "
                f"`{factor.composition_target}`"
            )
        default_maximum = _all_eligible_default_maximum(
            factor=factor,
            policy=policy,
            total_group_budget=total_group_budget,
            active_group_weight_totals=active_group_weight_totals,
        )
        lines.append(
            f"| `{factor.factor_id}` | `{factor.lifecycle}` | "
            f"{_code_or_dash(factor.group_id)} | {factor.base_weight:g} | "
            f"{default_maximum} | "
            f"`{factor.activation}` | `{factor.evidence_mode}` | "
            f"{factor.neutral_utility:g} | `{factor.readiness.policy_id}` | "
            f"`{factor.evidence_cap_policy}`{composition} | "
            f"{_code_or_dash(factor.correlation_group)} | "
            f"{_yes_no(factor.clarifiable)} |"
        )
    lines.extend(
        [
            "",
            "##### Roles, Values, And Evaluators",
            "",
            "| Factor | Roles | Allowed modes / values | Qualifier | Evaluator |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for factor in policy.factors:
        evaluator_status = evaluator_statuses.get(
            factor.factor_id,
            "not registered" if factor.evaluator_id is not None else "not required",
        )
        modes_and_values = ", ".join(factor.allowed_modes) or "—"
        if factor.allowed_values:
            modes_and_values += "; " + ", ".join(factor.allowed_values)
        lines.append(
            f"| `{factor.factor_id}` | {', '.join(factor.roles)} | "
            f"{modes_and_values} | {_code_or_dash(factor.qualifier_policy)} | "
            f"{evaluator_status} |"
        )
    lines.extend(
        [
            "",
            "Group importance: "
            + ", ".join(
                f"`{label}={value:g}`"
                for label, value in policy.group_importance_multipliers.items()
            )
            + ".",
            "",
            "Factor importance: "
            + ", ".join(
                f"`{label}={value:g}`"
                for label, value in policy.factor_importance_multipliers.items()
            )
            + ".",
            "",
            "Clarification impact: eligibility, winner, or top-three-membership "
            "change; top-three order requires a "
            f"`{policy.refinement.top_three_order_margin_points:g}`-point margin "
            "change; a top-five candidate difference requires "
            f"`{policy.refinement.top_five_candidate_difference_points:g}` points.",
        ]
    )
    return "\n".join(lines)


def replace_policy_inventory(document: str, inventory: str) -> str:
    if document.count(INVENTORY_START) != 1 or document.count(INVENTORY_END) != 1:
        raise ValueError("document must contain exactly one inventory marker pair")
    before, remainder = document.split(INVENTORY_START, 1)
    _, after = remainder.split(INVENTORY_END, 1)
    return (
        before
        + INVENTORY_START
        + "\n"
        + inventory.rstrip()
        + "\n"
        + INVENTORY_END
        + after
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _code_or_dash(value: str | None) -> str:
    return f"`{value}`" if value is not None else "—"


def _all_eligible_default_maximum(
    *,
    factor: FactorPolicy,
    policy: SearchPolicy,
    total_group_budget: float,
    active_group_weight_totals: Mapping[str, float],
) -> str:
    if (
        factor.lifecycle != "active"
        or factor.group_id is None
        or factor.base_weight <= 0
        or factor.composition_target is not None
        or "ranking" not in factor.roles
    ):
        return "—"
    group_weight_total = active_group_weight_totals[factor.group_id]
    if group_weight_total <= 0:
        return "—"
    group_share = policy.group(factor.group_id).default_budget / total_group_budget
    points = 100 * group_share * factor.base_weight / group_weight_total
    return f"{points:.2f} points"
