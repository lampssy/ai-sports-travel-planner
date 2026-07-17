from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domain.search_policy import load_search_policy
from app.domain.search_refinement_presentation import (
    RefinementPresentationPolicy,
    load_refinement_presentation_policy,
    validate_refinement_presentation_policy,
)

pytestmark = pytest.mark.db_free


def test_default_registry_covers_every_active_clarifiable_factor() -> None:
    search_policy = load_search_policy()
    presentation = load_refinement_presentation_policy()
    expected = {
        factor.factor_id
        for factor in search_policy.factors
        if factor.lifecycle == "active"
        and factor.clarifiable
        and "clarification" in factor.roles
    }
    assert {topic.factor_id for topic in presentation.topics} == expected


def test_registry_copy_resolves_to_typed_actions() -> None:
    presentation = load_refinement_presentation_policy()
    resolved = presentation.resolve_answer_ids(
        ["development_style.traditional", "local_pace.quiet"]
    )
    assert resolved.label == "Traditional mountain village + Quiet and relaxed"
    assert resolved.description == (
        "Prefer a base with traditional settlement character. "
        "Prefer a calm base rather than a lively one."
    )
    assert [item.factor_id for item in resolved.factor_preferences] == [
        "development_style",
        "local_pace",
    ]


def test_provider_topics_expose_only_approved_copy_for_allowed_factors() -> None:
    presentation = load_refinement_presentation_policy()

    assert presentation.provider_topics(frozenset({"development_style"})) == (
        {
            "topic_id": "development_style",
            "traveller_topic": "the village or resort development style",
            "fallback_question": "What kind of place would you prefer to stay in?",
            "answers": (
                {
                    "answer_id": "development_style.traditional",
                    "label": "Traditional mountain village",
                    "description": (
                        "Prefer a base with traditional settlement character."
                    ),
                },
                {
                    "answer_id": "development_style.mixed",
                    "label": "A mix of old and new",
                    "description": (
                        "Prefer a base with a mix of old and new settlement character."
                    ),
                },
                {
                    "answer_id": "development_style.planned_resort",
                    "label": "Purpose-built ski resort",
                    "description": "Prefer a purpose-built ski resort base.",
                },
                {
                    "answer_id": "development_style.ignore",
                    "label": "It doesn't matter",
                    "description": (
                        "Do not use the village or resort development style as an "
                        "extra preference."
                    ),
                },
            ),
        },
    )


def test_registry_rejects_duplicate_topic_and_answer_ids() -> None:
    search_policy = load_search_policy()
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    duplicate_topic = deepcopy(payload)
    duplicate_topic["topics"] = (
        *duplicate_topic["topics"],
        duplicate_topic["topics"][0],
    )
    with pytest.raises(ValueError, match="topic IDs must be unique"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(duplicate_topic), search_policy
        )

    duplicate_answer = deepcopy(payload)
    duplicate_answer["answers"] = (
        *duplicate_answer["answers"],
        duplicate_answer["answers"][0],
    )
    with pytest.raises(ValueError, match="answer IDs must be unique"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(duplicate_answer), search_policy
        )


def test_registry_rejects_unknown_or_repeated_answers() -> None:
    presentation = load_refinement_presentation_policy()
    with pytest.raises(KeyError, match="unknown refinement answer ID"):
        presentation.resolve_answer_ids(["unknown.answer"])
    with pytest.raises(ValueError, match="must be unique"):
        presentation.resolve_answer_ids(
            ["development_style.traditional", "development_style.traditional"]
        )


def test_registry_rejects_illegal_actions_and_objective_targets() -> None:
    search_policy = load_search_policy()
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    illegal_mode = deepcopy(payload)
    illegal_mode["answers"][0]["factor_preference_patch"]["mode"] = "require"
    with pytest.raises(ValueError, match="does not allow mode"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(illegal_mode), search_policy
        )

    illegal_value = deepcopy(payload)
    categorical = next(
        answer
        for answer in illegal_value["answers"]
        if answer["answer_id"] == "local_pace.quiet"
    )
    categorical["factor_preference_patch"]["values"] = ("unknown",)
    with pytest.raises(ValueError, match="does not allow values"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(illegal_value), search_policy
        )

    objective = deepcopy(payload)
    objective["answers"][0].pop("factor_preference_patch")
    objective["answers"][0]["objective_patch"] = {
        "factor_id": "trip_window_snow_fit",
        "importance": "high",
    }
    with pytest.raises(ValueError, match="objective_selected"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(objective), search_policy
        )


def test_registry_rejects_invalid_topic_ownership_and_fallback_shape() -> None:
    search_policy = load_search_policy()
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    foreign_answer = deepcopy(payload)
    foreign_answer["topics"][0]["answer_ids"] = (
        foreign_answer["topics"][0]["answer_ids"][0],
        "local_pace.quiet",
    )
    with pytest.raises(ValueError, match="belongs to factor"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(foreign_answer), search_policy
        )

    presentation = load_refinement_presentation_policy()
    with pytest.raises(ValueError, match="multiple answers target factor"):
        presentation.resolve_answer_ids(
            ["trip_window_snow_fit.high", "trip_window_snow_fit.normal"]
        )

    too_many_fallbacks = deepcopy(payload)
    topic = too_many_fallbacks["topics"][0]
    topic["fallback_answer_ids"] = topic["fallback_answer_ids"] * 2
    with pytest.raises(ValidationError, match="at most 5 items"):
        RefinementPresentationPolicy.model_validate(too_many_fallbacks)

    foreign_fallback = deepcopy(payload)
    foreign_fallback["topics"][0]["fallback_answer_ids"] = (
        foreign_fallback["topics"][0]["fallback_answer_ids"][0],
        "local_pace.quiet",
    )
    with pytest.raises(ValueError, match="fallback answer"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(foreign_fallback), search_policy
        )
