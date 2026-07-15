from __future__ import annotations

from app.domain.search_policy import SearchPolicy
from app.domain.search_v4_models import SearchIntent


class SearchIntentPolicyError(ValueError):
    pass


def validate_search_intent(intent: SearchIntent, policy: SearchPolicy) -> None:
    group_by_id = {group.group_id: group for group in policy.groups}
    factor_by_id = {factor.factor_id: factor for factor in policy.factors}

    for priority in intent.group_priorities:
        group = group_by_id.get(priority.group_id)
        if group is None:
            raise SearchIntentPolicyError(f"unknown group ID: {priority.group_id}")
        if priority.importance not in group.allowed_importance_labels:
            raise SearchIntentPolicyError(
                f"group {priority.group_id} does not allow importance "
                f"{priority.importance}"
            )

    for preference in intent.factor_preferences:
        factor = factor_by_id.get(preference.factor_id)
        if factor is None:
            raise SearchIntentPolicyError(f"unknown factor ID: {preference.factor_id}")
        if preference.mode not in factor.allowed_modes:
            raise SearchIntentPolicyError(
                f"factor {preference.factor_id} does not allow mode {preference.mode}"
            )
        _validate_values(
            factor_id=preference.factor_id,
            requested=preference.values,
            allowed=factor.allowed_values,
        )
        if preference.mode == "require" and "constraint" not in factor.roles:
            raise SearchIntentPolicyError(
                f"factor {preference.factor_id} does not support a hard requirement"
            )

    for objective in intent.objectives:
        factor = factor_by_id.get(objective.factor_id)
        if factor is None:
            raise SearchIntentPolicyError(f"unknown factor ID: {objective.factor_id}")
        if factor.activation != "objective_selected":
            raise SearchIntentPolicyError(
                f"factor {objective.factor_id} is not an objective-selected factor"
            )

    for requirement in intent.constraints.factor_requirements:
        factor = factor_by_id.get(requirement.factor_id)
        if factor is None:
            raise SearchIntentPolicyError(f"unknown factor ID: {requirement.factor_id}")
        if "constraint" not in factor.roles:
            raise SearchIntentPolicyError(
                f"factor {requirement.factor_id} does not support a hard requirement"
            )
        _validate_values(
            factor_id=requirement.factor_id,
            requested=requirement.values,
            allowed=factor.allowed_values,
        )


def _validate_values(
    *, factor_id: str, requested: tuple[str, ...], allowed: tuple[str, ...]
) -> None:
    unsupported = sorted(set(requested) - set(allowed))
    if unsupported:
        raise SearchIntentPolicyError(
            f"factor {factor_id} has unsupported values: " + ", ".join(unsupported)
        )
