from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.search_v4_models import (
    FactorPreferencePatch,
    GroupPriorityPatch,
    LodgingBudgetConstraint,
    SearchIntent,
    SearchObjective,
    TravelWindow,
)
from app.domain.search_v4_service import (
    SearchV4RefinementRequest,
    SearchV4RefinementResponse,
    SearchV4Request,
)

pytestmark = pytest.mark.db_free


def test_exact_dates_take_precedence_over_month() -> None:
    window = TravelWindow(
        month=3,
        start_date=date(2027, 3, 10),
        end_date=date(2027, 3, 15),
    )

    assert window.mode == "exact_dates"
    assert window.ski_day_count == 6


def test_travel_window_requires_complete_ordered_date_pair() -> None:
    with pytest.raises(ValidationError, match="provided together"):
        TravelWindow(start_date=date(2027, 3, 10))

    with pytest.raises(ValidationError, match="on or after"):
        TravelWindow(
            start_date=date(2027, 3, 15),
            end_date=date(2027, 3, 10),
        )

    with pytest.raises(ValidationError, match="month or exact dates"):
        TravelWindow()

    with pytest.raises(ValidationError, match="366 days"):
        TravelWindow(
            start_date=date(2027, 1, 1),
            end_date=date(2028, 1, 2),
        )


def test_lodging_budget_uses_minimum_estimate_flexibility() -> None:
    default = LodgingBudgetConstraint(
        mode="lodging_nightly",
        maximum=250,
        currency="EUR",
    )
    explicit = default.model_copy(update={"budget_flex": 0.25})

    assert default.effective_flex == pytest.approx(0.10)
    assert explicit.effective_flex == pytest.approx(0.25)
    assert default.effective_maximum == pytest.approx(275)


def test_search_intent_rejects_duplicate_or_ambiguous_patches() -> None:
    duplicate_group = GroupPriorityPatch(
        group_id="ski_experience", importance="important"
    )
    with pytest.raises(ValidationError, match="group priority IDs must be unique"):
        SearchIntent(group_priorities=(duplicate_group, duplicate_group))

    preference = FactorPreferencePatch(
        factor_id="night_skiing",
        mode="prefer",
        importance="normal",
    )
    with pytest.raises(ValidationError, match="factor preference IDs must be unique"):
        SearchIntent(factor_preferences=(preference, preference))

    with pytest.raises(ValidationError, match="both objective and preference"):
        SearchIntent(
            factor_preferences=(
                FactorPreferencePatch(
                    factor_id="pass_terrain_value",
                    mode="prefer",
                    importance="normal",
                ),
            ),
            objectives=(
                SearchObjective(
                    factor_id="pass_terrain_value",
                    importance="normal",
                ),
            ),
        )


def test_search_intent_is_frozen() -> None:
    intent = SearchIntent()

    with pytest.raises(ValidationError):
        intent.assumptions = ("changed",)


def test_search_request_bounds_prompt_context_and_answered_question_ids() -> None:
    with pytest.raises(ValidationError):
        SearchIntent(assumptions=tuple(f"assumption-{index}" for index in range(21)))

    with pytest.raises(ValidationError):
        SearchIntent(assumptions=("x" * 501,))

    with pytest.raises(ValidationError):
        SearchV4Request(
            intent=SearchIntent(),
            already_answered_question_ids=tuple(
                f"question-{index}" for index in range(51)
            ),
        )

    with pytest.raises(ValidationError, match="must be unique"):
        SearchV4Request(
            intent=SearchIntent(),
            already_answered_question_ids=("same-question", "same-question"),
        )


def test_search_v4_requests_accept_unique_resolved_topic_ids() -> None:
    refinement_request = SearchV4RefinementRequest(
        intent=SearchIntent(),
        baseline_fingerprint="a" * 64,
        resolved_topic_ids=("night_skiing", "glacier_terrain"),
    )
    search_request = SearchV4Request(
        intent=SearchIntent(),
        resolved_topic_ids=("night_skiing", "retired_or_unknown_topic"),
    )

    assert refinement_request.resolved_topic_ids == (
        "night_skiing",
        "glacier_terrain",
    )
    assert search_request.resolved_topic_ids == (
        "night_skiing",
        "retired_or_unknown_topic",
    )


@pytest.mark.parametrize("request_type", [SearchV4Request, SearchV4RefinementRequest])
def test_search_v4_requests_reject_duplicate_resolved_topic_ids(
    request_type: type,
) -> None:
    kwargs: dict[str, object] = {
        "intent": SearchIntent(),
        "resolved_topic_ids": ("night_skiing", "night_skiing"),
    }
    if request_type is SearchV4RefinementRequest:
        kwargs["baseline_fingerprint"] = "a" * 64

    with pytest.raises(ValidationError, match="resolved topic IDs must be unique"):
        request_type(**kwargs)


def test_search_v4_requests_bound_resolved_topic_history() -> None:
    with pytest.raises(ValidationError):
        SearchV4Request(
            intent=SearchIntent(),
            resolved_topic_ids=tuple(f"topic-{index}" for index in range(51)),
        )


def test_public_refinement_response_rejects_multiple_proposals() -> None:
    proposal = {
        "topic_id": "night_skiing",
        "target_factor_id": "night_skiing",
        "question_id": "night-skiing-priority",
        "question": "How important is night skiing for your trip?",
        "reason": "Your answer can change which trip option fits you best.",
        "options": (
            {
                "label": "Nice to have",
                "description": "Prefer recurring night skiing.",
                "intent_changed": True,
            },
            {
                "label": "Not important for this trip",
                "description": "Do not use night skiing as an extra preference.",
                "intent_changed": True,
            },
        ),
    }

    with pytest.raises(ValidationError):
        SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version="search-refinement-presentation-2",
            refinement_status="questions_available",
            refinements=(proposal, proposal),
        )
