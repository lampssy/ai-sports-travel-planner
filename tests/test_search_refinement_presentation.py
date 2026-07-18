from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

import app.domain.search_refinement_presentation as presentation_module
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import load_search_policy
from app.domain.search_refinement import (
    RefinementCandidateState,
    RefinementValidationError,
)
from app.domain.search_refinement_presentation import (
    RefinementPresentationPolicy,
    build_deterministic_refinement_fallback,
    load_refinement_presentation_policy,
    resolve_interaction_copy,
    semantic_refinement_question_id,
    validate_refinement_presentation_policy,
)
from app.domain.search_v4_models import SearchIntent

pytestmark = pytest.mark.db_free


def _evaluation(factor_id: str, utility: float, *, cap: float = 1) -> FactorEvaluation:
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


def _fallback_candidates() -> tuple[RefinementCandidateState, ...]:
    return tuple(
        RefinementCandidateState(
            candidate_id=candidate_id,
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.7),
                _evaluation("accessible_terrain_scale", terrain),
                _evaluation("stay_base_access", access),
                _evaluation("development_style", development),
            ),
        )
        for candidate_id, terrain, access, development in (
            ("traditional-base", 0.2, 0.3, 1.0),
            ("planned-base", 1.0, 0.9, 0.0),
            ("mixed-base", 0.6, 0.6, 0.5),
        )
    )


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


def test_default_registry_visible_copy_rejects_blocked_audience_terms() -> None:
    presentation = load_refinement_presentation_policy()
    visible_copy = [
        *(topic.fallback_question for topic in presentation.topics),
        *(topic.fallback_reason for topic in presentation.topics),
        *(answer.label for answer in presentation.answers),
        *(answer.description for answer in presentation.answers),
    ]

    for text in visible_copy:
        assert not presentation_module._contains_blocked_token(
            text, presentation.blocked_copy_terms
        ), text


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("topics", "fallback_question"),
        ("topics", "fallback_reason"),
        ("answers", "label"),
        ("answers", "description"),
    ],
)
def test_registry_validation_rejects_blocked_visible_copy(
    section: str,
    field: str,
) -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload[section][0][field] = "Internal optimisation objective"
    configured = RefinementPresentationPolicy.model_validate(payload)

    with pytest.raises(ValueError, match="blocked traveller-facing copy"):
        validate_refinement_presentation_policy(configured, load_search_policy())


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


def test_safe_dynamic_interaction_copy_survives_unchanged() -> None:
    presentation = load_refinement_presentation_policy()
    question = "What kind of place would you prefer to stay in?"
    reason = "Your preferred atmosphere can separate otherwise similar options."

    assert resolve_interaction_copy(
        question,
        reason,
        ("development_style",),
        ("candidate-a", "candidate-b"),
        presentation,
    ) == (question, reason)


@pytest.mark.parametrize(
    "question",
    [
        "How should trip viability influence your ranking?",
        "Should factor development_style have more weight?",
        "Would changing this score reorder candidate-a?",
        "Would 25% more evidence change the result?",
        "Would candidate-b suit you best?",
        "Would option 2 suit you best?",
        "Choose the atmosphere you want?",
        "What kind of place would you prefer to stay in",
        "What " + ("very " * 100) + "long preference matters?",
    ],
)
def test_unsafe_dynamic_question_uses_topic_fallback(question: str) -> None:
    presentation = load_refinement_presentation_policy()

    resolved = resolve_interaction_copy(
        question,
        "Your preferred atmosphere can separate otherwise similar options.",
        ("development_style",),
        ("candidate-a", "candidate-b"),
        presentation,
    )

    assert resolved == (
        "What kind of place would you prefer to stay in?",
        "Your preferred atmosphere can separate otherwise similar options.",
    )


def test_unsafe_reason_falls_back_without_discarding_safe_question() -> None:
    presentation = load_refinement_presentation_policy()
    question = "What kind of place would you prefer to stay in?"

    resolved = resolve_interaction_copy(
        question,
        "This ranking score separates candidate-a from candidate-b.",
        ("development_style",),
        ("candidate-a", "candidate-b"),
        presentation,
    )

    assert resolved == (
        question,
        "Your preferred village or resort style can change which stay base "
        "fits you best.",
    )


def test_multiple_topics_use_generic_copy_only_for_unsafe_fields() -> None:
    presentation = load_refinement_presentation_policy()
    safe_reason = "Your preferred balance can separate otherwise similar options."

    assert resolve_interaction_copy(
        "How should ranking weight affect candidate-a?",
        safe_reason,
        ("accessible_terrain_scale", "stay_base_access"),
        ("candidate-a",),
        presentation,
    ) == (
        "Which of these trip preferences matters most to you?",
        safe_reason,
    )


def test_blocked_terms_and_candidate_ids_match_whole_tokens_only() -> None:
    presentation = load_refinement_presentation_policy()
    question = "What kind of factory town or larger village would suit you?"
    reason = "Your answer can distinguish otherwise similar trip options."

    assert resolve_interaction_copy(
        question,
        reason,
        ("development_style",),
        ("large",),
        presentation,
    ) == (question, reason)


def test_registry_fallback_uses_first_material_topic_and_authoritative_copy() -> None:
    presentation = load_refinement_presentation_policy()
    fallback = build_deterministic_refinement_fallback(
        intent=SearchIntent(),
        candidates=_fallback_candidates(),
        policy=load_search_policy(),
        presentation=presentation,
    )

    assert fallback is not None
    development_topic = presentation.topic_by_id["development_style"]
    assert fallback.proposal.question_id == semantic_refinement_question_id(
        topic_ids=(development_topic.topic_id,),
        answer_id_sets=tuple(
            (answer_id,) for answer_id in development_topic.fallback_answer_ids
        ),
        presentation=presentation,
    )
    assert (
        fallback.proposal.question == "What kind of place would you prefer to stay in?"
    )
    assert fallback.proposal.reason == (
        "Your preferred village or resort style can change which stay base "
        "fits you best."
    )
    assert [option.label for option in fallback.proposal.options] == [
        "Traditional mountain village",
        "A mix of old and new",
        "Purpose-built ski resort",
        "It doesn't matter",
    ]
    assert fallback.impact.material is True


def test_registry_fallback_returns_none_without_actionable_trusted_variation() -> None:
    candidates = tuple(
        RefinementCandidateState(
            candidate_id=f"unknown-{index}",
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.5, cap=0),
                _evaluation("accessible_terrain_scale", utility, cap=0),
                _evaluation("stay_base_access", 1 - utility, cap=0),
                _evaluation("development_style", utility, cap=0),
            ),
        )
        for index, utility in enumerate((0.2, 0.6, 1.0))
    )

    assert (
        build_deterministic_refinement_fallback(
            intent=SearchIntent(),
            candidates=candidates,
            policy=load_search_policy(),
            presentation=load_refinement_presentation_policy(),
        )
        is None
    )


def test_registry_fallback_suppresses_answered_semantic_id() -> None:
    presentation = load_refinement_presentation_policy()
    first = build_deterministic_refinement_fallback(
        intent=SearchIntent(),
        candidates=_fallback_candidates(),
        policy=load_search_policy(),
        presentation=presentation,
    )
    assert first is not None

    next_fallback = build_deterministic_refinement_fallback(
        intent=SearchIntent(),
        candidates=_fallback_candidates(),
        policy=load_search_policy(),
        presentation=presentation,
        already_answered_question_ids=frozenset({first.proposal.question_id}),
    )

    assert next_fallback is None or next_fallback.proposal.question_id != (
        first.proposal.question_id
    )


def test_registry_fallback_tries_every_topic_before_returning_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted_ids: list[str] = []

    def reject(*, proposal: object, **_kwargs: object) -> None:
        attempted_ids.append(getattr(proposal, "question_id"))
        raise RefinementValidationError("not material")

    monkeypatch.setattr(presentation_module, "validate_refinement_proposal", reject)
    presentation = load_refinement_presentation_policy()

    assert (
        build_deterministic_refinement_fallback(
            intent=SearchIntent(),
            candidates=_fallback_candidates(),
            policy=load_search_policy(),
            presentation=presentation,
        )
        is None
    )
    assert len(attempted_ids) == len(presentation.topics)


def test_registry_fallback_does_not_swallow_configuration_errors() -> None:
    presentation = load_refinement_presentation_policy()
    development_topic = next(
        topic for topic in presentation.topics if topic.topic_id == "development_style"
    ).model_copy(update={"fallback_answer_ids": ("missing.answer", "also.missing")})
    broken = presentation.model_copy(
        update={
            "topics": tuple(
                development_topic if topic.topic_id == "development_style" else topic
                for topic in presentation.topics
            )
        }
    )

    with pytest.raises(KeyError, match="unknown refinement answer ID"):
        build_deterministic_refinement_fallback(
            intent=SearchIntent(),
            candidates=_fallback_candidates(),
            policy=load_search_policy(),
            presentation=broken,
        )


def test_registry_fallback_does_not_swallow_pydantic_construction_errors() -> None:
    presentation = load_refinement_presentation_policy()
    broken = presentation.model_copy(
        update={
            "topics": tuple(
                topic.model_copy(update={"fallback_question": "x" * 501})
                for topic in presentation.topics
            )
        }
    )

    with pytest.raises(ValidationError, match="question"):
        build_deterministic_refinement_fallback(
            intent=SearchIntent(),
            candidates=_fallback_candidates(),
            policy=load_search_policy(),
            presentation=broken,
        )


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("label", 80),
        ("description", 240),
    ],
)
def test_registry_rejects_fallback_option_copy_exceeding_search_policy_bounds(
    field: str,
    maximum: int,
) -> None:
    presentation = load_refinement_presentation_policy()
    payload = presentation.model_dump(mode="python")
    payload["answers"][0][field] = "x" * (maximum + 1)
    configured = RefinementPresentationPolicy.model_validate(payload)

    with pytest.raises(ValueError, match=f"max_option_{field}_characters"):
        validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("label", 80),
        ("description", 240),
    ],
)
def test_registry_accepts_fallback_option_copy_at_search_policy_bounds(
    field: str,
    maximum: int,
) -> None:
    presentation = load_refinement_presentation_policy()
    payload = presentation.model_dump(mode="python")
    payload["answers"][0][field] = "x" * maximum
    configured = RefinementPresentationPolicy.model_validate(payload)

    validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field", "maximum"),
    [
        ("topics", "fallback_question", 280),
        ("topics", "fallback_reason", 500),
        ("answers", "label", 500),
        ("answers", "description", 500),
    ],
)
def test_registry_rejects_copy_exceeding_public_bounds(
    section: str,
    field: str,
    maximum: int,
) -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload[section][0][field] = "x" * (maximum + 1)

    with pytest.raises(ValidationError, match=field):
        RefinementPresentationPolicy.model_validate(payload)


def test_registry_resolves_task_2_provider_answer_ids() -> None:
    presentation = load_refinement_presentation_policy()

    resolved = presentation.resolve_answer_ids(
        [
            "accessible_terrain_scale.as_much_as_possible",
            "stay_base_access.as_easy_as_possible",
        ]
    )

    assert resolved.answer_ids == (
        "accessible_terrain_scale.as_much_as_possible",
        "stay_base_access.as_easy_as_possible",
    )
    assert [item.factor_id for item in resolved.factor_preferences] == [
        "accessible_terrain_scale",
        "stay_base_access",
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


def test_registry_rejects_more_than_three_distinct_answer_ids() -> None:
    presentation = load_refinement_presentation_policy()

    with pytest.raises(ValueError, match="at most 3 answer IDs"):
        presentation.resolve_answer_ids(
            [
                "trip_window_snow_fit.high",
                "accessible_terrain_scale.as_much_as_possible",
                "terrain_potential_scale.high",
                "lift_network_scale.high",
            ]
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
