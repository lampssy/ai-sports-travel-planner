from __future__ import annotations

import json

import pytest

from app.ai.llm_client import LLMClient, LLMClientError
from app.ai.search_refinement import (
    RefinementGenerationResult,
    generate_refinement_proposals,
)
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import load_search_policy
from app.domain.search_refinement import RefinementCandidateState
from app.domain.search_refinement_presentation import (
    build_deterministic_refinement_fallback,
    load_refinement_presentation_policy,
)
from app.domain.search_v4_models import SearchIntent

pytestmark = pytest.mark.db_free


class _Client(LLMClient):
    def __init__(self, response: str | Exception) -> None:
        self.response = response

    @property
    def model(self) -> str:
        return "scenario-model"

    def complete(self, **_kwargs: object) -> str:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _evaluation(factor_id: str, utility: float, *, cap: float = 1) -> FactorEvaluation:
    return FactorEvaluation(
        factor_id=factor_id,
        scope="scenario",
        entity_ids=("candidate",),
        raw_value=utility,
        raw_utility=utility,
        neutral_utility=0.5,
        effective_evidence_cap=cap,
        evidence_cap_components={"scenario": cap},
        warnings=(),
        provenance_summary="Scenario evidence.",
        explanation_inputs={},
    )


def _candidates(
    rows: tuple[tuple[str, dict[str, tuple[float, float]]], ...],
) -> tuple[RefinementCandidateState, ...]:
    return tuple(
        RefinementCandidateState(
            candidate_id=candidate_id,
            evaluations=tuple(
                _evaluation(factor_id, utility, cap=cap)
                for factor_id, (utility, cap) in factors.items()
            ),
        )
        for candidate_id, factors in rows
    )


def _generate(
    payload: dict[str, object] | Exception,
    candidates: tuple[RefinementCandidateState, ...],
) -> RefinementGenerationResult:
    response = payload if isinstance(payload, Exception) else json.dumps(payload)
    return generate_refinement_proposals(
        brief="Help me choose a ski trip.",
        intent=SearchIntent(),
        candidates=candidates,
        policy=load_search_policy(),
        presentation=load_refinement_presentation_policy(),
        client=_Client(response),
    )


def _development_candidates() -> tuple[RefinementCandidateState, ...]:
    return _candidates(
        (
            (
                "traditional-base",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (0.55, 1),
                    "stay_base_access": (0.55, 1),
                    "development_style": (1.0, 1),
                },
            ),
            (
                "planned-base",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (0.65, 1),
                    "stay_base_access": (0.65, 1),
                    "development_style": (0.0, 1),
                },
            ),
            (
                "mixed-base",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (0.6, 1),
                    "stay_base_access": (0.6, 1),
                    "development_style": (0.5, 1),
                },
            ),
        )
    )


def _development_payload(*, question: str | None = None) -> dict[str, object]:
    return {
        "questions": [
            {
                "topic_id": "development_style",
                "question": question
                or "What kind of place would you prefer to stay in?",
                "options": [
                    {"answer_id": "development_style.traditional"},
                    {"answer_id": "development_style.mixed"},
                    {"answer_id": "development_style.planned_resort"},
                    {"answer_id": "development_style.ignore"},
                ],
            }
        ]
    }


def test_development_style_variation_compiles_concrete_options_and_reorders() -> None:
    result = _generate(_development_payload(), _development_candidates())

    assert result.outcome == "proposals_generated"
    proposal = result.proposals[0]
    assert [option.label for option in proposal.proposal.options] == [
        "Traditional mountain village",
        "Mix of old and new",
        "Purpose-built ski resort",
        "Not important",
    ]
    assert (
        len({variant.ordered_candidate_ids for variant in proposal.variant_outcomes})
        > 1
    )


def test_terrain_priority_compiles_distinct_typed_variants() -> None:
    candidates = _candidates(
        (
            (
                "large",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (1.0, 1),
                    "party_skill_coverage": (0.0, 1),
                    "stay_base_access": (0.2, 1),
                },
            ),
            (
                "easy",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (0.2, 1),
                    "party_skill_coverage": (1.0, 1),
                    "stay_base_access": (1.0, 1),
                },
            ),
            (
                "balanced",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (0.6, 1),
                    "party_skill_coverage": (0.4, 1),
                    "stay_base_access": (0.6, 1),
                },
            ),
        )
    )
    payload = {
        "questions": [
            {
                "topic_id": "accessible_terrain_scale",
                "question": "How much terrain would you like your pass to cover?",
                "options": [
                    {"answer_id": "accessible_terrain_scale.as_much_as_possible"},
                    {"answer_id": "accessible_terrain_scale.low"},
                ],
            }
        ]
    }

    result = _generate(payload, candidates)

    assert result.outcome == "proposals_generated"
    options = result.proposals[0].proposal.options
    assert options[0].factor_preference_patches[0].factor_id == (
        "accessible_terrain_scale"
    )
    assert options[1].factor_preference_patches[0].factor_id == (
        "accessible_terrain_scale"
    )
    assert options[0].factor_preference_patches != options[1].factor_preference_patches
    assert all(
        variant.intent_changed for variant in result.proposals[0].variant_outcomes
    )


def test_requested_glacier_feature_can_produce_material_question() -> None:
    candidates = _candidates(
        (
            (
                "glacier",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (0.4, 1),
                    "glacier_terrain": (1.0, 1),
                },
            ),
            (
                "large-non-glacier",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (1.0, 1),
                    "glacier_terrain": (0.0, 1),
                },
            ),
            (
                "unknown",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (0.6, 1),
                    "glacier_terrain": (0.5, 0),
                },
            ),
        )
    )
    payload = {
        "questions": [
            {
                "topic_id": "glacier_terrain",
                "question": "Does glacier terrain matter for this trip?",
                "options": [
                    {"answer_id": "glacier_terrain.prefer"},
                    {"answer_id": "glacier_terrain.ignore"},
                ],
            }
        ]
    }

    result = _generate(payload, candidates)

    assert result.outcome == "proposals_generated"
    assert result.proposals[0].impact.material is True


def test_no_trusted_factor_variation_produces_no_validated_question() -> None:
    candidates = _candidates(
        tuple(
            (
                f"unknown-{index}",
                {
                    "trip_window_snow_fit": (0.7, 1),
                    "accessible_terrain_scale": (utility, 0),
                },
            )
            for index, utility in enumerate((0.2, 0.6, 1.0))
        )
    )
    payload = {
        "questions": [
            {
                "topic_id": "accessible_terrain_scale",
                "question": "How much terrain would you like your pass to cover?",
                "options": [
                    {"answer_id": "accessible_terrain_scale.as_much_as_possible"},
                    {"answer_id": "accessible_terrain_scale.low"},
                ],
            }
        ]
    }

    result = _generate(payload, candidates)

    assert result == RefinementGenerationResult(
        outcome="provider_unavailable",
        proposals=(),
    )


def test_unsafe_internal_wording_uses_configured_safe_fallback_copy() -> None:
    result = _generate(
        _development_payload(
            question="How should trip viability influence your ranking?"
        ),
        _development_candidates(),
    )

    assert result.proposals[0].proposal.question == (
        "What building and development style do you prefer where you stay?"
    )


def test_provider_failure_allows_first_material_registry_fallback() -> None:
    candidates = _development_candidates()
    generated = _generate(
        LLMClientError("provider failed", reason="provider_error"),
        candidates,
    )

    assert generated.outcome == "provider_unavailable"
    fallback = build_deterministic_refinement_fallback(
        intent=SearchIntent(),
        candidates=candidates,
        policy=load_search_policy(),
        presentation=load_refinement_presentation_policy(),
    )
    assert fallback is not None
    assert (
        fallback.proposal.question
        == "What building and development style do you prefer where you stay?"
    )
