from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.search_factors.models import FactorEvaluation, FrozenMapping
from app.domain.search_intent_policy import validate_search_intent
from app.domain.search_policy import FactorPolicy, SearchPolicy
from app.domain.search_v4_models import SearchIntent

_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")
_EPSILON = 1e-12


class SearchRankingInputError(ValueError):
    pass


class _RankingModel(BaseModel):
    model_config = _MODEL_CONFIG


class FactorScoreBreakdown(_RankingModel):
    factor_id: str = Field(min_length=1)
    group_id: str = Field(min_length=1)
    direction: Literal["prefer", "avoid"]
    raw_value: object
    raw_utility: float = Field(ge=0, le=1)
    neutral_utility: float = Field(ge=0, le=1)
    effective_evidence_cap: float = Field(ge=0, le=1)
    effective_utility: float = Field(ge=0, le=1)
    effective_weight: float = Field(gt=0)
    contribution_points: float = Field(ge=0, le=100)
    evidence_cap_components: FrozenMapping
    warnings: tuple[str, ...]
    provenance_summary: str = Field(min_length=1)
    explanation_inputs: FrozenMapping


class GroupScoreBreakdown(_RankingModel):
    group_id: str = Field(min_length=1)
    normalized_share: float = Field(ge=0, le=1)
    group_utility: float = Field(ge=0, le=1)
    contribution_points: float = Field(ge=0, le=100)


class RankedScore(_RankingModel):
    fit_score: float = Field(ge=0, le=100)
    groups: tuple[GroupScoreBreakdown, ...]
    factors: tuple[FactorScoreBreakdown, ...]


class UnscoredAllocation(_RankingModel):
    reason: Literal["no_active_groups", "infeasible_group_caps"]
    active_group_ids: tuple[str, ...]


class _ActiveFactor:
    def __init__(
        self,
        *,
        policy: FactorPolicy,
        evaluation: FactorEvaluation,
        direction: Literal["prefer", "avoid"],
        effective_weight: float,
    ) -> None:
        self.policy = policy
        self.evaluation = evaluation
        self.direction = direction
        self.effective_weight = effective_weight

    @property
    def raw_utility(self) -> float:
        if self.direction == "avoid":
            return 1 - self.evaluation.raw_utility
        return self.evaluation.raw_utility

    @property
    def effective_utility(self) -> float:
        return self.evaluation.neutral_utility + (
            self.evaluation.effective_evidence_cap
            * (self.raw_utility - self.evaluation.neutral_utility)
        )


def capped_normalize(
    raw_budgets: Mapping[str, float],
    maximum_shares: Mapping[str, float],
) -> dict[str, float] | None:
    """Normalize positive budgets while enforcing per-group maximum shares."""

    budgets = {
        group_id: float(budget)
        for group_id, budget in raw_budgets.items()
        if budget > 0
    }
    if not budgets:
        return None
    caps = {
        group_id: min(1.0, maximum_shares.get(group_id, 1.0)) for group_id in budgets
    }
    if sum(caps.values()) < 1 - _EPSILON:
        return None

    remaining = set(budgets)
    shares: dict[str, float] = {}
    remaining_share = 1.0
    while remaining:
        total_budget = sum(budgets[group_id] for group_id in remaining)
        if total_budget <= 0:
            return None
        proposed = {
            group_id: remaining_share * budgets[group_id] / total_budget
            for group_id in remaining
        }
        over_cap = {
            group_id
            for group_id, share in proposed.items()
            if share > caps[group_id] + _EPSILON
        }
        if not over_cap:
            shares.update(proposed)
            break
        for group_id in over_cap:
            shares[group_id] = caps[group_id]
            remaining_share -= caps[group_id]
            remaining.remove(group_id)
        if remaining_share < -_EPSILON:
            return None

    total = sum(shares.values())
    if total <= 0 or abs(total - 1) > 1e-9:
        return None
    return shares


def score_factor_evaluations(
    *,
    evaluations: Sequence[FactorEvaluation],
    intent: SearchIntent,
    policy: SearchPolicy,
) -> RankedScore | UnscoredAllocation:
    """Apply the generic Search V4 equation to precomputed factor evaluations."""

    validate_search_intent(intent, policy)
    _validate_evaluations(evaluations, policy)
    evaluation_by_id = {evaluation.factor_id: evaluation for evaluation in evaluations}
    preference_by_id = {
        preference.factor_id: preference for preference in intent.factor_preferences
    }
    objective_by_id = {
        objective.factor_id: objective for objective in intent.objectives
    }
    group_priority_by_id = {
        priority.group_id: priority for priority in intent.group_priorities
    }

    active_factors: list[_ActiveFactor] = []
    for factor in policy.factors:
        evaluation = evaluation_by_id.get(factor.factor_id)
        if evaluation is None or not _is_independent_ranking_factor(factor):
            continue
        preference = preference_by_id.get(factor.factor_id)
        objective = objective_by_id.get(factor.factor_id)
        if not _factor_is_active(
            factor=factor,
            preference_mode=preference.mode if preference is not None else None,
            objective_selected=objective is not None,
            context_available=evaluation.effective_evidence_cap > 0,
        ):
            continue
        importance = (
            preference.importance
            if preference is not None
            else objective.importance
            if objective is not None
            else "normal"
        )
        direction: Literal["prefer", "avoid"] = (
            "avoid"
            if preference is not None and preference.mode == "avoid"
            else "prefer"
        )
        active_factors.append(
            _ActiveFactor(
                policy=factor,
                evaluation=evaluation,
                direction=direction,
                effective_weight=(
                    factor.base_weight
                    * policy.factor_importance_multipliers[importance]
                ),
            )
        )

    _apply_correlation_caps(active_factors, policy)
    factors_by_group: dict[str, list[_ActiveFactor]] = defaultdict(list)
    for factor in active_factors:
        if factor.policy.group_id is not None:
            factors_by_group[factor.policy.group_id].append(factor)

    group_order = [group.group_id for group in policy.groups]
    raw_group_budgets: dict[str, float] = {}
    maximum_shares: dict[str, float] = {}
    for group in policy.groups:
        if not factors_by_group.get(group.group_id):
            continue
        priority = group_priority_by_id.get(group.group_id)
        importance = priority.importance if priority is not None else "normal"
        multiplier = policy.group_importance_multipliers[importance]
        if multiplier <= 0:
            continue
        raw_group_budgets[group.group_id] = group.default_budget * multiplier
        maximum_shares[group.group_id] = group.max_effective_share

    active_group_ids = tuple(
        group_id for group_id in group_order if group_id in raw_group_budgets
    )
    if not active_group_ids:
        return UnscoredAllocation(
            reason="no_active_groups",
            active_group_ids=(),
        )
    group_shares = capped_normalize(raw_group_budgets, maximum_shares)
    if group_shares is None:
        return UnscoredAllocation(
            reason="infeasible_group_caps",
            active_group_ids=active_group_ids,
        )

    group_breakdowns: list[GroupScoreBreakdown] = []
    factor_breakdowns: list[FactorScoreBreakdown] = []
    for group_id in active_group_ids:
        group_factors = factors_by_group[group_id]
        total_factor_weight = sum(item.effective_weight for item in group_factors)
        group_utility = (
            sum(
                item.effective_weight * item.effective_utility for item in group_factors
            )
            / total_factor_weight
        )
        group_share = group_shares[group_id]
        group_contribution = 100 * group_share * group_utility
        group_breakdowns.append(
            GroupScoreBreakdown(
                group_id=group_id,
                normalized_share=group_share,
                group_utility=group_utility,
                contribution_points=group_contribution,
            )
        )
        for item in group_factors:
            evaluation = item.evaluation
            factor_breakdowns.append(
                FactorScoreBreakdown(
                    factor_id=item.policy.factor_id,
                    group_id=group_id,
                    direction=item.direction,
                    raw_value=evaluation.raw_value,
                    raw_utility=item.raw_utility,
                    neutral_utility=evaluation.neutral_utility,
                    effective_evidence_cap=evaluation.effective_evidence_cap,
                    effective_utility=item.effective_utility,
                    effective_weight=item.effective_weight,
                    contribution_points=(
                        100
                        * group_share
                        * item.effective_weight
                        / total_factor_weight
                        * item.effective_utility
                    ),
                    evidence_cap_components=evaluation.evidence_cap_components,
                    warnings=evaluation.warnings,
                    provenance_summary=evaluation.provenance_summary,
                    explanation_inputs=evaluation.explanation_inputs,
                )
            )

    fit_score = sum(group.contribution_points for group in group_breakdowns)
    return RankedScore(
        fit_score=min(100.0, max(0.0, fit_score)),
        groups=tuple(group_breakdowns),
        factors=tuple(factor_breakdowns),
    )


def _validate_evaluations(
    evaluations: Sequence[FactorEvaluation], policy: SearchPolicy
) -> None:
    factor_ids = [evaluation.factor_id for evaluation in evaluations]
    if len(factor_ids) != len(set(factor_ids)):
        raise SearchRankingInputError("duplicate factor evaluations")
    configured_ids = {factor.factor_id for factor in policy.factors}
    unknown = sorted(set(factor_ids) - configured_ids)
    if unknown:
        raise SearchRankingInputError(
            "unconfigured factor evaluations: " + ", ".join(unknown)
        )
    for evaluation in evaluations:
        expected = policy.factor(evaluation.factor_id).neutral_utility
        if abs(evaluation.neutral_utility - expected) > _EPSILON:
            raise SearchRankingInputError(
                f"factor {evaluation.factor_id} neutral utility "
                f"{evaluation.neutral_utility} does not match policy {expected}"
            )


def _is_independent_ranking_factor(factor: FactorPolicy) -> bool:
    return (
        factor.lifecycle == "active"
        and "ranking" in factor.roles
        and factor.composition_target is None
        and factor.group_id is not None
        and factor.base_weight > 0
    )


def _factor_is_active(
    *,
    factor: FactorPolicy,
    preference_mode: str | None,
    objective_selected: bool,
    context_available: bool,
) -> bool:
    if preference_mode in {"ignore", "require"}:
        return False
    if factor.activation == "always":
        return True
    if factor.activation == "context_available":
        return context_available
    if factor.activation == "when_requested":
        return preference_mode in {"prefer", "avoid"}
    if factor.activation == "objective_selected":
        return objective_selected
    return False


def _apply_correlation_caps(
    active_factors: Sequence[_ActiveFactor], policy: SearchPolicy
) -> None:
    correlation_by_id = {
        correlation.correlation_group_id: correlation
        for correlation in policy.correlations
    }
    factors_by_correlation: dict[str, list[_ActiveFactor]] = defaultdict(list)
    for factor in active_factors:
        correlation_group = factor.policy.correlation_group
        if correlation_group is not None:
            factors_by_correlation[correlation_group].append(factor)
    for correlation_group_id, group_factors in factors_by_correlation.items():
        correlation = correlation_by_id[correlation_group_id]
        maximum = correlation.max_combined_effective_weight
        if correlation.mode != "capped" or maximum is None:
            continue
        current = sum(factor.effective_weight for factor in group_factors)
        if current <= maximum:
            continue
        scale = maximum / current
        for factor in group_factors:
            factor.effective_weight *= scale
