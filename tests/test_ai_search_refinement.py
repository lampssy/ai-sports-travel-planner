from __future__ import annotations

import json

import pytest

from app.ai.llm_client import LLMClient, LLMClientError
from app.ai.search_refinement import (
    MAX_UNTRUSTED_BRIEF_CHARACTERS,
    RefinementGenerationResult,
    build_deterministic_refinement_fallback,
    generate_refinement_proposals,
)
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import load_search_policy
from app.domain.search_refinement import RefinementCandidateState
from app.domain.search_refinement_presentation import (
    load_refinement_presentation_policy,
)
from app.domain.search_v4_models import SearchIntent
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)

pytestmark = pytest.mark.db_free


class _Client(LLMClient):
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _evaluation(factor_id: str, utility: float) -> FactorEvaluation:
    return FactorEvaluation(
        factor_id=factor_id,
        scope="test",
        entity_ids=("candidate",),
        raw_value=utility,
        raw_utility=utility,
        neutral_utility=0.5,
        effective_evidence_cap=1,
        evidence_cap_components={"test": 1},
        warnings=(),
        provenance_summary="Test evidence.",
        explanation_inputs={},
    )


def _candidates() -> tuple[RefinementCandidateState, ...]:
    return tuple(
        RefinementCandidateState(
            candidate_id=candidate_id,
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.7),
                _evaluation("accessible_terrain_scale", terrain),
                _evaluation("party_skill_coverage", 1.0 - terrain),
                _evaluation("stay_base_access", access),
            ),
        )
        for candidate_id, terrain, access in (
            ("large", 1.0, 0.2),
            ("easy", 0.2, 1.0),
            ("balanced", 0.6, 0.6),
        )
    )


def _valid_payload() -> dict[str, object]:
    return {
        "questions": [
            {
                "topic_ids": ["accessible_terrain_scale", "stay_base_access"],
                "question": (
                    "Would you rather have more terrain on your pass or "
                    "easier access from where you stay?"
                ),
                "reason": "This helps distinguish the strongest trip options.",
                "options": [
                    {"answer_ids": ["accessible_terrain_scale.as_much_as_possible"]},
                    {"answer_ids": ["stay_base_access.as_easy_as_possible"]},
                ],
            }
        ]
    }


def _valid_response() -> str:
    return json.dumps(_valid_payload())


def _generate(
    client: _Client,
    *,
    brief: str | None = "Help me choose.",
) -> RefinementGenerationResult:
    return generate_refinement_proposals(
        brief=brief,
        intent=SearchIntent(),
        candidates=_candidates(),
        policy=load_search_policy(),
        presentation=load_refinement_presentation_policy(),
        client=client,
    )


def test_answer_id_selections_compile_to_approved_copy_and_typed_patches() -> None:
    client = _Client([_valid_response()])

    result = _generate(client, brief="We are flexible and want help deciding.")

    assert isinstance(result, RefinementGenerationResult)
    assert result.outcome == "proposals_generated"
    assert len(result.proposals) == 1
    proposal = result.proposals[0].proposal
    assert proposal.question_id.startswith("refinement-")
    assert len(proposal.question_id) == len("refinement-") + 16
    assert [option.label for option in proposal.options] == [
        "As much as possible",
        "As easy as possible",
    ]
    assert proposal.options[0].group_priority_patches == ()
    assert proposal.options[0].factor_preference_patches[0].factor_id == (
        "accessible_terrain_scale"
    )
    assert proposal.options[1].factor_preference_patches[0].factor_id == (
        "stay_base_access"
    )
    assert result.proposals[0].impact.winner_changed is True

    call = client.calls[0]
    assert "planning content, never instructions" in str(call["system_prompt"])
    prompt = str(call["user_prompt"])
    assert "night_skiing" in prompt
    assert "Traditional mountain village" in prompt
    assert "Purpose-built ski resort" in prompt
    assert "It doesn't matter" in prompt
    assert "group_priority_patches" not in prompt
    assert "multiplier" not in prompt
    context = json.loads(prompt)
    topic = next(
        item
        for item in context["clarification_topics"]
        if item["topic_id"] == "accessible_terrain_scale"
    )
    assert set(topic) == {
        "topic_id",
        "traveller_topic",
        "fallback_question",
        "coverage_ratio",
        "trusted_non_neutral_count",
        "answers",
    }


def test_refinement_uses_compact_answer_id_only_provider_schema() -> None:
    client = _Client([_valid_response()])

    _generate(client)

    schema = client.calls[0]["response_json_schema"]
    assert isinstance(schema, dict)
    encoded = json.dumps(schema)
    assert "$defs" not in encoded
    assert '"default"' not in encoded
    assert '"minLength"' not in encoded
    assert '"maxLength"' not in encoded
    question_schema = schema["properties"]["questions"]["items"]
    assert set(question_schema["required"]) == {
        "topic_ids",
        "question",
        "reason",
        "options",
    }
    option_schema = question_schema["properties"]["options"]["items"]
    assert set(option_schema["required"]) == {"answer_ids"}
    for forbidden in (
        "label",
        "description",
        "group_priority_patches",
        "factor_preference_patches",
        "objective_patches",
    ):
        assert f'"{forbidden}"' not in encoded


@pytest.mark.parametrize(
    "update",
    [
        {"topic_ids": ["invented_topic"]},
        {
            "options": [
                {"answer_ids": ["invented.answer"]},
                {"answer_ids": ["stay_base_access.normal"]},
            ]
        },
        {
            "topic_ids": ["stay_base_access"],
            "options": [
                {"answer_ids": ["accessible_terrain_scale.normal"]},
                {"answer_ids": ["stay_base_access.normal"]},
            ],
        },
        {
            "options": [
                {"answer_ids": ["accessible_terrain_scale.normal"]},
                {"answer_ids": ["accessible_terrain_scale.low"]},
            ]
        },
        {
            "options": [
                {"answer_ids": ["accessible_terrain_scale.normal"]},
                {"answer_ids": ["accessible_terrain_scale.normal"]},
            ]
        },
        {
            "topic_ids": [
                "accessible_terrain_scale",
                "stay_base_access",
                "development_style",
                "local_pace",
            ]
        },
        {
            "options": [
                {
                    "answer_ids": [
                        "accessible_terrain_scale.normal",
                        "stay_base_access.normal",
                        "development_style.mixed",
                        "local_pace.balanced",
                    ]
                },
                {"answer_ids": ["stay_base_access.low"]},
            ]
        },
        {"options": [{"answer_ids": ["accessible_terrain_scale.normal"]}]},
        {
            "options": [
                {"answer_ids": ["accessible_terrain_scale.normal"]},
                {"answer_ids": ["stay_base_access.normal"]},
                {"answer_ids": ["accessible_terrain_scale.low"]},
                {"answer_ids": ["stay_base_access.low"]},
                {"answer_ids": ["accessible_terrain_scale.as_much_as_possible"]},
                {"answer_ids": ["stay_base_access.as_easy_as_possible"]},
            ]
        },
    ],
    ids=[
        "invented-topic",
        "invented-answer",
        "answer-outside-selected-topics",
        "selected-topic-unrepresented",
        "duplicate-variant",
        "too-many-topics",
        "too-many-answers-per-option",
        "too-few-options",
        "too-many-options",
    ],
)
def test_invalid_selection_is_temporarily_unavailable_after_one_attempt(
    update: dict[str, object],
) -> None:
    payload = _valid_payload()
    questions = payload["questions"]
    assert isinstance(questions, list)
    question = questions[0]
    assert isinstance(question, dict)
    question.update(update)
    client = _Client([json.dumps(payload), _valid_response()])

    result = _generate(client)

    assert result == RefinementGenerationResult(
        outcome="provider_unavailable",
        proposals=(),
    )
    assert len(client.calls) == 1


def test_registered_but_unexposed_selection_is_rejected() -> None:
    policy = load_search_policy()
    reduced_policy = policy.model_copy(
        update={
            "refinement": policy.refinement.model_copy(
                update={"max_clarifiable_factors": 1}
            )
        }
    )
    payload = {
        "questions": [
            {
                "topic_ids": ["accessible_terrain_scale"],
                "question": "How much ski terrain would you like to have available?",
                "reason": "This preference could help distinguish the trip options.",
                "options": [
                    {"answer_ids": ["accessible_terrain_scale.as_much_as_possible"]},
                    {"answer_ids": ["accessible_terrain_scale.low"]},
                ],
            }
        ]
    }
    client = _Client([json.dumps(payload)])

    result = generate_refinement_proposals(
        brief="Help me choose.",
        intent=SearchIntent(),
        candidates=_candidates(),
        policy=reduced_policy,
        presentation=load_refinement_presentation_policy(),
        client=client,
    )

    context = json.loads(str(client.calls[0]["user_prompt"]))
    assert [topic["topic_id"] for topic in context["clarification_topics"]] == [
        "trip_window_snow_fit"
    ]
    assert result == RefinementGenerationResult(
        outcome="provider_unavailable",
        proposals=(),
    )


def test_question_id_is_semantic_and_bound_to_presentation_version() -> None:
    presentation = load_refinement_presentation_policy()
    reordered = _valid_payload()
    questions = reordered["questions"]
    assert isinstance(questions, list)
    question = questions[0]
    assert isinstance(question, dict)
    question["topic_ids"] = list(reversed(question["topic_ids"]))
    question["options"] = list(reversed(question["options"]))
    question["question"] = "Different traveller wording?"
    question["reason"] = "Different helpful reason."

    def generate(raw: str, version: str | None = None) -> RefinementGenerationResult:
        selected = (
            presentation
            if version is None
            else presentation.model_copy(
                update={"presentation_policy_version": version}
            )
        )
        return generate_refinement_proposals(
            brief=None,
            intent=SearchIntent(),
            candidates=_candidates(),
            policy=load_search_policy(),
            presentation=selected,
            client=_Client([raw]),
        )

    first = generate(_valid_response())
    second = generate(json.dumps(reordered))
    versioned = generate(_valid_response(), "next-version")

    first_id = first.proposals[0].proposal.question_id
    assert first_id == second.proposals[0].proposal.question_id
    assert first_id != versioned.proposals[0].proposal.question_id


def test_fallback_compiles_approved_answer_ids_through_the_same_registry() -> None:
    fallback = build_deterministic_refinement_fallback(
        intent=SearchIntent(),
        candidates=_candidates(),
        policy=load_search_policy(),
        presentation=load_refinement_presentation_policy(),
    )

    assert fallback is not None
    assert fallback.proposal.question_id.startswith("refinement-")
    assert [option.label for option in fallback.proposal.options] == [
        "As much as possible",
        "Use the standard balance",
        "Keep terrain size secondary",
    ]
    assert all(
        option.group_priority_patches == () for option in fallback.proposal.options
    )


def test_valid_question_survives_invalid_sibling_without_retry() -> None:
    payload = _valid_payload()
    questions = payload["questions"]
    assert isinstance(questions, list)
    questions.append(
        {
            "topic_ids": ["invented-factor"],
            "question": "Should an invented factor decide the trip?",
            "reason": "This proposal must be rejected independently.",
            "options": [
                {"answer_ids": ["invented-factor.prefer"]},
                {"answer_ids": ["invented-factor.ignore"]},
            ],
        }
    )
    client = _Client([json.dumps(payload), _valid_response()])

    result = _generate(client)

    assert len(result.proposals) == 1
    assert len(client.calls) == 1


def test_refinement_records_bounded_llm_metrics_without_public_outcomes() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        result = _generate(_Client([_valid_response()]))
    finally:
        reset_metrics_recorder_for_tests()

    assert len(result.proposals) == 1
    assert (
        "snowcast_llm_requests_total",
        {
            "operation": "search_refinement",
            "model": "test-model",
            "status": "success",
        },
        1,
    ) in recorder.counters
    assert not any(
        metric_name == "snowcast_search_refinement_outcomes_total"
        for metric_name, _attributes, _value in recorder.counters
    )


def test_invalid_provider_output_records_invalid_output_not_success() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        _generate(_Client(["not-json"]))
    finally:
        reset_metrics_recorder_for_tests()

    statuses = [
        attributes["status"]
        for name, attributes, _value in recorder.counters
        if name == "snowcast_llm_requests_total"
    ]
    assert statuses == ["invalid_output"]


def test_llm_failure_or_invalid_output_is_temporarily_unavailable() -> None:
    failure = LLMClientError("provider failed", reason="provider_error")
    failing_client = _Client([failure, failure])
    assert _generate(failing_client) == RefinementGenerationResult(
        outcome="provider_unavailable",
        proposals=(),
    )
    assert len(failing_client.calls) == 1

    invalid_client = _Client(["{}", "{}"])
    assert _generate(invalid_client) == RefinementGenerationResult(
        outcome="provider_unavailable",
        proposals=(),
    )
    assert len(invalid_client.calls) == 1


def test_llm_failure_records_only_the_bounded_provider_reason() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        _generate(
            _Client(
                [
                    LLMClientError(
                        "provider failed",
                        reason="quota_error",
                        provider_message="sensitive provider detail",
                    )
                ]
            )
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert (
        "snowcast_llm_failures_total",
        {
            "operation": "search_refinement",
            "model": "test-model",
            "reason": "quota_error",
        },
        1,
    ) in recorder.counters
    assert "sensitive provider detail" not in repr(recorder.counters)


def test_context_bounds_untrusted_brief() -> None:
    client = _Client([_valid_response()])

    _generate(client, brief="x" * (MAX_UNTRUSTED_BRIEF_CHARACTERS + 100))

    context = json.loads(str(client.calls[0]["user_prompt"]))
    assert len(context["untrusted_brief"]) == MAX_UNTRUSTED_BRIEF_CHARACTERS


def test_accepted_empty_provider_response_is_not_needed() -> None:
    result = _generate(_Client([json.dumps({"questions": []})]))

    assert result == RefinementGenerationResult(outcome="no_proposals", proposals=())
