from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_intent_policy import (
    SearchIntentPolicyError,
    validate_search_intent,
)
from app.domain.search_policy import FactorPolicy, SearchPolicy
from app.domain.search_ranking import RankedScore, score_factor_evaluations
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    GroupPriorityPatch,
    SearchIntent,
    SearchObjective,
)

_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")
_EPSILON = 1e-9
_BoundedDisplayText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
_QuestionId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]


class RefinementValidationError(ValueError):
    pass


class _RefinementModel(BaseModel):
    model_config = _MODEL_CONFIG


class RefinementOption(_RefinementModel):
    label: _BoundedDisplayText
    description: _BoundedDisplayText
    group_priority_patches: tuple[GroupPriorityPatch, ...] = Field(
        default=(), max_length=10
    )
    factor_preference_patches: tuple[FactorPreferencePatch, ...] = Field(
        default=(), max_length=10
    )
    objective_patches: tuple[SearchObjective, ...] = Field(default=(), max_length=10)

    @model_validator(mode="after")
    def require_unique_patches(self) -> "RefinementOption":
        patch_count = (
            len(self.group_priority_patches)
            + len(self.factor_preference_patches)
            + len(self.objective_patches)
        )
        if patch_count == 0:
            raise ValueError("refinement option needs at least one typed patch")
        for kind, values in (
            (
                "group priority",
                [item.group_id for item in self.group_priority_patches],
            ),
            (
                "factor preference",
                [item.factor_id for item in self.factor_preference_patches],
            ),
            ("objective", [item.factor_id for item in self.objective_patches]),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {kind} patch")
        factor_ids = {item.factor_id for item in self.factor_preference_patches}
        objective_ids = {item.factor_id for item in self.objective_patches}
        if factor_ids & objective_ids:
            raise ValueError("an option cannot prefer and optimize the same factor")
        return self


class RefinementProposal(_RefinementModel):
    question_id: _QuestionId
    question: _BoundedDisplayText
    reason: _BoundedDisplayText
    options: tuple[RefinementOption, ...] = Field(min_length=2, max_length=10)


@dataclass(frozen=True)
class RefinementCandidateState:
    candidate_id: str
    evaluations: tuple[FactorEvaluation, ...]
    eligible: bool = True
    eligibility_evaluator: Callable[[SearchIntent], bool] | None = None
    evaluation_replayer: (
        Callable[[SearchIntent], tuple[FactorEvaluation, ...]] | None
    ) = None
    cohort_evaluation_replayer: (
        Callable[
            [SearchIntent, tuple[str, ...]],
            Mapping[str, tuple[FactorEvaluation, ...]],
        ]
        | None
    ) = None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must not be blank")
        factor_ids = [evaluation.factor_id for evaluation in self.evaluations]
        if len(factor_ids) != len(set(factor_ids)):
            raise ValueError("candidate factor evaluations must be unique")


class RefinementImpact(_RefinementModel):
    material: bool
    eligibility_changed: bool
    winner_changed: bool
    top_three_membership_changed: bool
    top_three_order_changed: bool
    top_five_score_changed: bool


class RefinementVariantOutcome(_RefinementModel):
    ordered_candidate_ids: tuple[str, ...]
    eligible_candidate_ids: frozenset[str]
    intent_changed: bool


class ValidatedRefinementProposal(_RefinementModel):
    proposal: RefinementProposal
    impact: RefinementImpact
    variant_outcomes: tuple[RefinementVariantOutcome, ...]


@dataclass(frozen=True)
class _VariantRanking:
    eligible_ids: frozenset[str]
    ordered_ids: tuple[str, ...]
    scores: Mapping[str, float]
    evaluations_by_candidate_id: Mapping[str, tuple[FactorEvaluation, ...]]


def apply_refinement_option(
    intent: SearchIntent,
    option: RefinementOption,
    policy: SearchPolicy,
) -> SearchIntent:
    group_priorities = _upsert(
        intent.group_priorities,
        option.group_priority_patches,
        key=lambda item: item.group_id,
    )
    touched_preferences = {item.factor_id for item in option.factor_preference_patches}
    touched_objectives = {item.factor_id for item in option.objective_patches}
    factor_preferences = tuple(
        item
        for item in intent.factor_preferences
        if item.factor_id not in touched_objectives
    )
    objectives = tuple(
        item for item in intent.objectives if item.factor_id not in touched_preferences
    )
    factor_preferences = _upsert(
        factor_preferences,
        option.factor_preference_patches,
        key=lambda item: item.factor_id,
    )
    objectives = _upsert(
        objectives,
        option.objective_patches,
        key=lambda item: item.factor_id,
    )
    updated = SearchIntent.model_validate(
        {
            **intent.model_dump(mode="python", exclude_computed_fields=True),
            "group_priorities": group_priorities,
            "factor_preferences": factor_preferences,
            "objectives": objectives,
        }
    )
    validate_search_intent(updated, policy)
    return updated


def validate_refinement_proposal(
    *,
    proposal: RefinementProposal,
    intent: SearchIntent,
    candidates: Sequence[RefinementCandidateState],
    policy: SearchPolicy,
    already_answered_question_ids: frozenset[str] = frozenset(),
) -> ValidatedRefinementProposal:
    if proposal.question_id in already_answered_question_ids:
        raise RefinementValidationError(
            f"refinement question already asked: {proposal.question_id}"
        )
    _validate_text_and_option_bounds(proposal, policy)
    if len(candidates) < 2:
        raise RefinementValidationError(
            "refinement needs at least two reusable candidate evaluations"
        )

    option_signatures: set[str] = set()
    variant_intents: list[SearchIntent] = []
    for option in proposal.options:
        _validate_option_targets(option, policy)
        if option_expands_synthesized_require(intent, option):
            raise RefinementValidationError(
                "refinement option would widen a synthesized require"
            )
        signature = _option_signature(option)
        if signature in option_signatures:
            raise RefinementValidationError("refinement options must be distinct")
        option_signatures.add(signature)
        try:
            variant_intents.append(apply_refinement_option(intent, option, policy))
        except SearchIntentPolicyError as error:
            raise RefinementValidationError(str(error)) from error

    if all(_same_intent(intent, variant) for variant in variant_intents):
        raise RefinementValidationError(
            "refinement options only repeat the current intent"
        )
    variants = tuple(
        _rank_variant(
            intent=variant_intent,
            candidates=candidates,
            policy=policy,
        )
        for variant_intent in variant_intents
    )
    _validate_factor_actionability(
        proposal,
        variants,
        policy,
    )
    impact = _measure_impact(variants, policy)
    if not impact.material:
        raise RefinementValidationError(
            "refinement answer variants do not have material impact"
        )
    return ValidatedRefinementProposal(
        proposal=proposal,
        impact=impact,
        variant_outcomes=tuple(
            RefinementVariantOutcome(
                ordered_candidate_ids=variant.ordered_ids,
                eligible_candidate_ids=variant.eligible_ids,
                intent_changed=not _same_intent(intent, variant_intent),
            )
            for variant, variant_intent in zip(variants, variant_intents, strict=True)
        ),
    )


def _validate_text_and_option_bounds(
    proposal: RefinementProposal,
    policy: SearchPolicy,
) -> None:
    limits = policy.refinement
    if len(proposal.question) > limits.max_question_characters:
        raise RefinementValidationError("refinement question is too long")
    if len(proposal.options) > limits.max_options_per_question:
        raise RefinementValidationError("refinement has too many options")
    for option in proposal.options:
        if len(option.label) > limits.max_option_label_characters:
            raise RefinementValidationError("refinement option label is too long")
        if len(option.description) > limits.max_option_description_characters:
            raise RefinementValidationError("refinement option description is too long")
        patch_count = (
            len(option.group_priority_patches)
            + len(option.factor_preference_patches)
            + len(option.objective_patches)
        )
        if patch_count > limits.max_factor_patches_per_option:
            raise RefinementValidationError("refinement option has too many patches")


def _validate_option_targets(option: RefinementOption, policy: SearchPolicy) -> None:
    groups = {group.group_id: group for group in policy.groups}
    factors = {factor.factor_id: factor for factor in policy.factors}
    for patch in option.group_priority_patches:
        group = groups.get(patch.group_id)
        if group is None:
            raise RefinementValidationError(f"unknown group ID: {patch.group_id}")
        if not group.clarifiable:
            raise RefinementValidationError(
                f"group is not clarifiable: {patch.group_id}"
            )
    for patch in option.factor_preference_patches:
        factor = factors.get(patch.factor_id)
        if factor is None:
            raise RefinementValidationError(f"unknown factor ID: {patch.factor_id}")
        _require_clarifiable_factor(factor)
    for patch in option.objective_patches:
        factor = factors.get(patch.factor_id)
        if factor is None:
            raise RefinementValidationError(f"unknown factor ID: {patch.factor_id}")
        _require_clarifiable_factor(factor)
        if factor.activation != "objective_selected":
            raise RefinementValidationError(
                f"factor is not an objective: {patch.factor_id}"
            )


def _require_clarifiable_factor(factor: FactorPolicy) -> None:
    if not factor.clarifiable or "clarification" not in factor.roles:
        raise RefinementValidationError(
            f"factor is not clarifiable: {factor.factor_id}"
        )
    if factor.lifecycle != "active":
        raise RefinementValidationError(
            f"factor is not runtime-active: {factor.factor_id}"
        )


def synthesized_require_factor_ids(intent: SearchIntent) -> frozenset[str]:
    explicit_requirement_ids = {
        requirement.factor_id for requirement in intent.constraints.factor_requirements
    }
    return frozenset(
        preference.factor_id
        for preference in intent.factor_preferences
        if preference.mode == "require"
        and preference.factor_id not in explicit_requirement_ids
    )


def option_expands_synthesized_require(
    intent: SearchIntent,
    option: RefinementOption,
) -> bool:
    synthesized_requires = {
        preference.factor_id: preference
        for preference in intent.factor_preferences
        if preference.factor_id in synthesized_require_factor_ids(intent)
    }
    if any(
        objective.factor_id in synthesized_requires
        for objective in option.objective_patches
    ):
        return True
    for patch in option.factor_preference_patches:
        existing = synthesized_requires.get(patch.factor_id)
        if existing is None:
            continue
        if patch.mode != "require":
            return True
        if existing.values and (
            not patch.values or not set(patch.values).issubset(existing.values)
        ):
            return True
    return False


def _validate_factor_actionability(
    proposal: RefinementProposal,
    variants: Sequence[_VariantRanking],
    policy: SearchPolicy,
) -> None:
    factor_ids = {
        patch.factor_id
        for option in proposal.options
        for patch in (
            *option.factor_preference_patches,
            *option.objective_patches,
        )
        if not (isinstance(patch, FactorPreferencePatch) and patch.mode == "ignore")
    }
    for factor_id in factor_ids:
        factor = policy.factor(factor_id)
        relevant_variants = (
            variant
            for option, variant in zip(
                proposal.options,
                variants,
                strict=True,
            )
            if any(
                patch.factor_id == factor_id and patch.mode != "ignore"
                for patch in option.factor_preference_patches
            )
            or any(
                objective.factor_id == factor_id
                for objective in option.objective_patches
            )
        )
        if not any(
            _factor_is_actionable(
                factor,
                tuple(
                    evaluation
                    for evaluations in variant.evaluations_by_candidate_id.values()
                    for evaluation in evaluations
                    if evaluation.factor_id == factor_id
                ),
            )
            for variant in relevant_variants
        ):
            raise RefinementValidationError(
                f"factor is not actionable for current candidates: {factor_id}"
            )


def _factor_is_actionable(
    factor: FactorPolicy,
    evaluations: Sequence[FactorEvaluation],
) -> bool:
    if not evaluations:
        return False
    caps = [evaluation.effective_evidence_cap for evaluation in evaluations]
    trusted = [
        evaluation
        for evaluation in evaluations
        if evaluation.effective_evidence_cap > 0
    ]
    utilities = {round(evaluation.effective_utility, 8) for evaluation in evaluations}
    trusted_non_neutral = any(
        abs(evaluation.effective_utility - evaluation.neutral_utility) > _EPSILON
        for evaluation in trusted
    )
    readiness = factor.readiness
    if factor.evidence_mode == "positive_presence":
        return trusted_non_neutral and len(utilities) >= 2
    if factor.evidence_mode == "categorical_match":
        return len({round(item.effective_utility, 8) for item in trusted}) >= 2
    if factor.evidence_mode in {"comparative", "objective_comparison"}:
        coverage = len(trusted) / len(evaluations)
        average_cap = sum(caps) / len(caps)
        return (
            coverage >= (readiness.minimum_resolved_coverage or 0)
            and (average_cap >= (readiness.minimum_average_evidence_strength or 0))
            and len(utilities) >= 2
        )
    return trusted_non_neutral and len(utilities) >= 2


def _rank_variant(
    *,
    intent: SearchIntent,
    candidates: Sequence[RefinementCandidateState],
    policy: SearchPolicy,
) -> _VariantRanking:
    eligible: list[RefinementCandidateState] = []
    for candidate in candidates:
        is_eligible = (
            candidate.eligibility_evaluator(intent)
            if candidate.eligibility_evaluator is not None
            else candidate.eligible
        )
        if is_eligible:
            eligible.append(candidate)
    cohort_replayers = [
        candidate.cohort_evaluation_replayer
        for candidate in eligible
        if candidate.cohort_evaluation_replayer is not None
    ]
    if cohort_replayers:
        cohort_replayer = cohort_replayers[0]
        if len(cohort_replayers) != len(eligible) or any(
            replayer is not cohort_replayer for replayer in cohort_replayers[1:]
        ):
            raise ValueError("eligible refinement candidates must share cohort replay")
        eligible_candidate_ids = tuple(candidate.candidate_id for candidate in eligible)
        evaluations_by_candidate_id = dict(
            cohort_replayer(intent, eligible_candidate_ids)
        )
        if set(evaluations_by_candidate_id) != set(eligible_candidate_ids):
            raise ValueError("cohort replay must evaluate every eligible candidate")
    else:
        evaluations_by_candidate_id = {
            candidate.candidate_id: (
                candidate.evaluation_replayer(intent)
                if candidate.evaluation_replayer is not None
                else candidate.evaluations
            )
            for candidate in eligible
        }
    scores: dict[str, float] = {}
    for candidate in eligible:
        result = score_factor_evaluations(
            evaluations=evaluations_by_candidate_id[candidate.candidate_id],
            intent=intent,
            policy=policy,
        )
        if isinstance(result, RankedScore):
            scores[candidate.candidate_id] = result.fit_score
    ordered = tuple(
        sorted(scores, key=lambda candidate_id: (-scores[candidate_id], candidate_id))
    )
    return _VariantRanking(
        eligible_ids=frozenset(candidate.candidate_id for candidate in eligible),
        ordered_ids=ordered,
        scores=scores,
        evaluations_by_candidate_id=evaluations_by_candidate_id,
    )


def _measure_impact(
    variants: Sequence[_VariantRanking],
    policy: SearchPolicy,
) -> RefinementImpact:
    eligibility_changed = False
    winner_changed = False
    top_three_membership_changed = False
    top_three_order_changed = False
    top_five_score_changed = False
    for left, right in combinations(variants, 2):
        eligibility_changed |= left.eligible_ids != right.eligible_ids
        left_winner = left.ordered_ids[0] if left.ordered_ids else None
        right_winner = right.ordered_ids[0] if right.ordered_ids else None
        winner_changed |= left_winner != right_winner
        left_top_three = left.ordered_ids[:3]
        right_top_three = right.ordered_ids[:3]
        top_three_membership_changed |= set(left_top_three) != set(right_top_three)
        top_three_order_changed |= _top_three_order_impact(
            left,
            right,
            threshold=policy.refinement.top_three_order_margin_points,
        )
        union_top_five = set(left.ordered_ids[:5]) | set(right.ordered_ids[:5])
        top_five_score_changed |= any(
            candidate_id in left.scores
            and candidate_id in right.scores
            and abs(left.scores[candidate_id] - right.scores[candidate_id])
            >= policy.refinement.top_five_candidate_difference_points
            for candidate_id in union_top_five
        )
    material = (
        eligibility_changed
        and policy.refinement.eligibility_change_is_material
        or winner_changed
        and policy.refinement.winner_change_is_material
        or top_three_membership_changed
        and policy.refinement.top_three_membership_change_is_material
        or top_three_order_changed
        or top_five_score_changed
    )
    return RefinementImpact(
        material=material,
        eligibility_changed=eligibility_changed,
        winner_changed=winner_changed,
        top_three_membership_changed=top_three_membership_changed,
        top_three_order_changed=top_three_order_changed,
        top_five_score_changed=top_five_score_changed,
    )


def _top_three_order_impact(
    left: _VariantRanking,
    right: _VariantRanking,
    *,
    threshold: float,
) -> bool:
    left_top = left.ordered_ids[:3]
    right_top = right.ordered_ids[:3]
    if set(left_top) != set(right_top) or left_top == right_top:
        return False
    for first, second in combinations(left_top, 2):
        left_margin = left.scores[first] - left.scores[second]
        right_margin = right.scores[first] - right.scores[second]
        order_changed = left_margin * right_margin <= 0
        margin_changed = abs(left_margin - right_margin) >= threshold
        if order_changed and margin_changed:
            return True
    return False


def _option_signature(option: RefinementOption) -> str:
    return json.dumps(
        option.model_dump(mode="json", exclude={"label", "description"}),
        sort_keys=True,
        separators=(",", ":"),
    )


def _same_intent(left: SearchIntent, right: SearchIntent) -> bool:
    return left.model_dump(mode="json") == right.model_dump(mode="json")


def _upsert(
    existing: Sequence[object],
    patches: Sequence[object],
    *,
    key: Callable[[object], str],
) -> tuple[object, ...]:
    by_id = {key(item): item for item in existing}
    order = [key(item) for item in existing]
    for patch in patches:
        item_id = key(patch)
        if item_id not in by_id:
            order.append(item_id)
        by_id[item_id] = patch
    return tuple(by_id[item_id] for item_id in order)
