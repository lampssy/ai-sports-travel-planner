from __future__ import annotations

import pytest

from app.domain.search_intent_policy import (
    SearchIntentPolicyError,
    validate_search_intent,
)
from app.domain.search_policy import load_search_policy
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    FactorRequirement,
    GroupPriorityPatch,
    SearchConstraints,
    SearchIntent,
    SearchObjective,
)

pytestmark = pytest.mark.db_free


@pytest.mark.parametrize(
    "intent, message",
    [
        (
            SearchIntent(
                group_priorities=(GroupPriorityPatch(group_id="not_a_group"),)
            ),
            "unknown group ID",
        ),
        (
            SearchIntent(
                factor_preferences=(
                    FactorPreferencePatch(
                        factor_id="not_a_factor",
                        mode="prefer",
                    ),
                )
            ),
            "unknown factor ID",
        ),
        (
            SearchIntent(
                factor_preferences=(
                    FactorPreferencePatch(
                        factor_id="accessible_terrain_scale",
                        mode="avoid",
                    ),
                )
            ),
            "does not allow mode avoid",
        ),
        (
            SearchIntent(
                factor_preferences=(
                    FactorPreferencePatch(
                        factor_id="local_pace",
                        mode="prefer",
                        values=("rushed",),
                    ),
                )
            ),
            "unsupported values",
        ),
        (
            SearchIntent(objectives=(SearchObjective(factor_id="night_skiing"),)),
            "is not an objective-selected factor",
        ),
        (
            SearchIntent(
                constraints=SearchConstraints(
                    factor_requirements=(
                        FactorRequirement(
                            factor_id="accessible_terrain_scale",
                            minimum_trust="verified",
                        ),
                    )
                )
            ),
            "does not support a hard requirement",
        ),
    ],
)
def test_policy_validation_rejects_unregistered_or_unsupported_intent(
    intent: SearchIntent,
    message: str,
) -> None:
    with pytest.raises(SearchIntentPolicyError, match=message):
        validate_search_intent(intent, load_search_policy())


def test_policy_validation_accepts_registered_patches() -> None:
    validate_search_intent(
        SearchIntent(
            factor_preferences=(
                FactorPreferencePatch(
                    factor_id="night_skiing",
                    mode="require",
                ),
                FactorPreferencePatch(
                    factor_id="local_pace",
                    mode="prefer",
                    values=("quiet",),
                ),
            ),
            objectives=(SearchObjective(factor_id="pass_terrain_value"),),
        ),
        load_search_policy(),
    )
