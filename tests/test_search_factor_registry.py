from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.domain.search_factors import build_factor_registry
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_factors.registry import (
    FactorRegistry,
    FactorRegistryError,
)
from app.domain.search_policy import load_search_policy

pytestmark = pytest.mark.db_free


@dataclass(frozen=True)
class NeutralEvaluator:
    factor_id: str

    def evaluate(self, context: object, candidate: object) -> FactorEvaluation:
        del context, candidate
        return FactorEvaluation(
            factor_id=self.factor_id,
            scope="test",
            entity_ids=(),
            raw_value=None,
            raw_utility=0.5,
            neutral_utility=0.5,
            effective_evidence_cap=0,
            evidence_cap_components={},
            warnings=(),
            provenance_summary="Test neutral evaluator.",
            explanation_inputs={},
        )


def _complete_registry() -> FactorRegistry:
    policy = load_search_policy()
    return FactorRegistry(
        NeutralEvaluator(factor_id=factor.factor_id)
        for factor in policy.factors_requiring_evaluators
    )


def test_registry_and_policy_are_bidirectionally_complete() -> None:
    policy = load_search_policy()
    registry = _complete_registry()

    registry.validate_policy(policy)

    assert registry.factor_ids == tuple(
        sorted(factor.factor_id for factor in policy.factors_requiring_evaluators)
    )


def test_production_registry_is_complete_for_policy() -> None:
    policy = load_search_policy()
    registry = build_factor_registry()

    registry.validate_policy(policy)


def test_registry_rejects_duplicate_factor_ids() -> None:
    with pytest.raises(FactorRegistryError, match="duplicate evaluator"):
        FactorRegistry(
            (
                NeutralEvaluator("accessible_terrain_scale"),
                NeutralEvaluator("accessible_terrain_scale"),
            )
        )


def test_registry_reports_missing_and_unconfigured_evaluators() -> None:
    policy = load_search_policy()
    complete = _complete_registry()
    evaluators = [
        complete.get(factor_id)
        for factor_id in complete.factor_ids
        if factor_id != "accessible_terrain_scale"
    ]
    evaluators.append(NeutralEvaluator("not_in_policy"))
    registry = FactorRegistry(evaluators)

    with pytest.raises(FactorRegistryError) as error:
        registry.validate_policy(policy)

    message = str(error.value)
    assert "missing evaluators: accessible_terrain_scale" in message
    assert "unconfigured evaluators: not_in_policy" in message


def test_factor_evaluation_is_frozen_and_bounded() -> None:
    evaluation = NeutralEvaluator("example").evaluate(object(), object())

    assert evaluation.effective_utility == pytest.approx(0.5)
    with pytest.raises(Exception):
        evaluation.raw_utility = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        evaluation.evidence_cap_components["trust"] = 1  # type: ignore[index]

    with pytest.raises(ValueError, match="effective_evidence_cap"):
        FactorEvaluation(
            factor_id="example",
            scope="test",
            entity_ids=(),
            raw_value=None,
            raw_utility=0.5,
            neutral_utility=0.5,
            effective_evidence_cap=1.1,
            evidence_cap_components={},
            warnings=(),
            provenance_summary="Invalid cap.",
            explanation_inputs={},
        )
