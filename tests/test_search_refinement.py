from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import load_search_policy
from app.domain.search_refinement import (
    RefinementCandidateState,
    RefinementOption,
    RefinementProposal,
    RefinementValidationError,
    apply_refinement_option,
    validate_refinement_proposal,
)
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    GroupPriorityPatch,
    SearchIntent,
    SearchObjective,
)

pytestmark = pytest.mark.db_free


def _evaluation(
    factor_id: str,
    utility: float,
    *,
    cap: float = 1,
) -> FactorEvaluation:
    return FactorEvaluation(
        factor_id=factor_id,
        scope="test",
        entity_ids=("candidate",),
        raw_value=utility,
        raw_utility=utility,
        neutral_utility=0.5,
        effective_evidence_cap=cap,
        evidence_cap_components={"test": cap},
        warnings=(),
        provenance_summary="Test evidence.",
        explanation_inputs={},
    )


def _candidates() -> tuple[RefinementCandidateState, ...]:
    return (
        RefinementCandidateState(
            candidate_id="large-far",
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.7),
                _evaluation("accessible_terrain_scale", 1.0),
                _evaluation("stay_base_access", 0.3),
                _evaluation("night_skiing", 1.0),
            ),
        ),
        RefinementCandidateState(
            candidate_id="small-near",
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.7),
                _evaluation("accessible_terrain_scale", 0.2),
                _evaluation("stay_base_access", 1.0),
                _evaluation("night_skiing", 0.0),
            ),
        ),
        RefinementCandidateState(
            candidate_id="balanced",
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.7),
                _evaluation("accessible_terrain_scale", 0.65),
                _evaluation("stay_base_access", 0.65),
                _evaluation("night_skiing", 0.5, cap=0),
            ),
        ),
    )


def _material_proposal() -> RefinementProposal:
    return RefinementProposal(
        question_id="terrain-vs-access",
        question="Would you prioritize a larger ski area or easier base access?",
        reason="The leading candidates trade terrain scale against access.",
        options=(
            RefinementOption(
                label="Larger terrain",
                description="Give the ski experience more influence.",
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="ski_experience",
                        importance="very_high",
                    ),
                ),
            ),
            RefinementOption(
                label="Easier access",
                description="Give stay practicality more influence.",
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="stay_practicality",
                        importance="very_high",
                    ),
                ),
            ),
        ),
    )


def test_material_group_question_passes_deterministic_impact_gate() -> None:
    result = validate_refinement_proposal(
        proposal=_material_proposal(),
        intent=SearchIntent(),
        candidates=_candidates(),
        policy=load_search_policy(),
    )

    assert result.proposal.question_id == "terrain-vs-access"
    assert result.impact.winner_changed is True
    assert result.impact.material is True


def test_apply_option_upserts_typed_patches_without_mutating_original() -> None:
    original = SearchIntent(
        group_priorities=(
            GroupPriorityPatch(group_id="ski_experience", importance="important"),
        ),
        factor_preferences=(
            FactorPreferencePatch(factor_id="night_skiing", mode="ignore"),
        ),
    )
    option = RefinementOption(
        label="Night skiing",
        description="Prefer areas with verified recurring night skiing.",
        group_priority_patches=(
            GroupPriorityPatch(group_id="ski_experience", importance="primary"),
        ),
        factor_preference_patches=(
            FactorPreferencePatch(factor_id="night_skiing", mode="prefer"),
        ),
    )

    updated = apply_refinement_option(original, option, load_search_policy())

    assert original.group_priorities[0].importance == "important"
    assert updated.group_priorities[0].importance == "primary"
    assert updated.factor_preferences[0].mode == "prefer"


def test_apply_option_excludes_computed_intent_fields_before_revalidation() -> None:
    original = SearchIntent.model_validate(
        {
            "constraints": {
                "travel_window": {"month": 3},
                "lodging_budget": {
                    "mode": "lodging_nightly",
                    "maximum": 300,
                    "currency": "EUR",
                },
            }
        }
    )
    option = RefinementOption(
        label="Prefer night skiing",
        description="Prefer verified recurring night skiing.",
        factor_preference_patches=(
            FactorPreferencePatch(factor_id="night_skiing", mode="prefer"),
        ),
    )

    updated = apply_refinement_option(original, option, load_search_policy())

    assert updated.constraints.travel_window is not None
    assert updated.constraints.travel_window.month == 3
    assert updated.constraints.lodging_budget is not None
    assert updated.constraints.lodging_budget.effective_flex == 0.10


def test_objective_patch_activates_only_configured_objective_factor() -> None:
    option = RefinementOption(
        label="Pass value",
        description="Optimize pass-accessible terrain per comparable pass price.",
        objective_patches=(
            SearchObjective(factor_id="pass_terrain_value", importance="high"),
        ),
    )

    updated = apply_refinement_option(SearchIntent(), option, load_search_policy())

    assert updated.objectives == option.objective_patches


def test_unknown_or_non_clarifiable_patch_is_rejected() -> None:
    unknown = _material_proposal().model_copy(
        update={
            "options": (
                RefinementOption(
                    label="Invented",
                    description="Try to activate an unregistered factor.",
                    factor_preference_patches=(
                        FactorPreferencePatch(factor_id="secret_factor", mode="prefer"),
                    ),
                ),
                _material_proposal().options[1],
            )
        }
    )

    with pytest.raises(RefinementValidationError, match="unknown factor ID"):
        validate_refinement_proposal(
            proposal=unknown,
            intent=SearchIntent(),
            candidates=_candidates(),
            policy=load_search_policy(),
        )


def test_repeated_or_immaterial_question_is_rejected() -> None:
    with pytest.raises(RefinementValidationError, match="already asked"):
        validate_refinement_proposal(
            proposal=_material_proposal(),
            intent=SearchIntent(),
            candidates=_candidates(),
            policy=load_search_policy(),
            already_answered_question_ids=frozenset({"terrain-vs-access"}),
        )

    immaterial = RefinementProposal(
        question_id="minor-access",
        question="How much should access matter?",
        reason="This checks an access-priority distinction.",
        options=(
            RefinementOption(
                label="Normal access",
                description="Use the default access group importance.",
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="stay_practicality",
                        importance="normal",
                    ),
                ),
            ),
            RefinementOption(
                label="Slightly more access",
                description="Give the access group slightly more influence.",
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="stay_practicality",
                        importance="important",
                    ),
                ),
            ),
        ),
    )
    identical_candidates = tuple(
        RefinementCandidateState(
            candidate_id=f"same-{index}",
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.7),
                _evaluation("accessible_terrain_scale", 0.7),
                _evaluation("stay_base_access", 0.7),
            ),
        )
        for index in range(3)
    )

    with pytest.raises(RefinementValidationError, match="material impact"):
        validate_refinement_proposal(
            proposal=immaterial,
            intent=SearchIntent(),
            candidates=identical_candidates,
            policy=load_search_policy(),
        )


def test_positive_presence_question_requires_trusted_variation() -> None:
    proposal = RefinementProposal(
        question_id="night-skiing",
        question="Would recurring night skiing improve the trip?",
        reason="Some candidates may offer verified night skiing.",
        options=(
            RefinementOption(
                label="Prefer it",
                description="Prefer verified recurring night skiing.",
                factor_preference_patches=(
                    FactorPreferencePatch(factor_id="night_skiing", mode="prefer"),
                ),
            ),
            RefinementOption(
                label="Ignore it",
                description="Do not use night skiing in the ranking.",
                factor_preference_patches=(
                    FactorPreferencePatch(factor_id="night_skiing", mode="ignore"),
                ),
            ),
        ),
    )
    unknown_candidates = tuple(
        RefinementCandidateState(
            candidate_id=f"unknown-{index}",
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.7),
                _evaluation("accessible_terrain_scale", utility),
                _evaluation("night_skiing", 0.5, cap=0),
            ),
        )
        for index, utility in enumerate((0.3, 0.7, 1.0))
    )

    with pytest.raises(RefinementValidationError, match="not actionable"):
        validate_refinement_proposal(
            proposal=proposal,
            intent=SearchIntent(),
            candidates=unknown_candidates,
            policy=load_search_policy(),
        )


def test_refinement_display_text_and_question_ids_have_hard_schema_bounds() -> None:
    with pytest.raises(ValidationError):
        RefinementProposal.model_validate(
            {
                **_material_proposal().model_dump(),
                "question_id": "q" * 129,
            }
        )

    with pytest.raises(ValidationError):
        RefinementProposal(
            question_id="bounded-reason",
            question="A bounded question?",
            reason="r" * 501,
            options=_material_proposal().options,
        )
