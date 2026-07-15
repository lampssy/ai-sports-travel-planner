from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import load_search_policy
from app.domain.search_ranking import (
    RankedScore,
    UnscoredAllocation,
    score_factor_evaluations,
)
from app.domain.search_v4_models import SearchIntent

pytestmark = pytest.mark.db_free
FIXTURE_PATH = Path("tests/fixtures/search_v4_golden/scenarios.json")


def _evaluation(payload: dict[str, object]) -> FactorEvaluation:
    factor_id = str(payload["factor_id"])
    utility = float(payload["utility"])
    cap = float(payload.get("evidence_cap", 1))
    return FactorEvaluation(
        factor_id=factor_id,
        scope="golden_fixture",
        entity_ids=("candidate",),
        raw_value=utility,
        raw_utility=utility,
        neutral_utility=0.5,
        effective_evidence_cap=cap,
        evidence_cap_components={"fixture": cap},
        warnings=(),
        provenance_summary="Reviewed Search V4 golden fixture.",
        explanation_inputs={},
    )


def test_reviewed_search_v4_golden_scenarios() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    policy = load_search_policy()

    for case in payload["cases"]:
        intent = SearchIntent.model_validate(case["intent"])
        results: dict[str, RankedScore | UnscoredAllocation] = {}
        for candidate in case["candidates"]:
            results[candidate["id"]] = score_factor_evaluations(
                evaluations=tuple(
                    _evaluation(item) for item in candidate["evaluations"]
                ),
                intent=intent,
                policy=policy,
            )

        if "expected_unscored_reason" in case:
            only_result = next(iter(results.values()))
            assert isinstance(only_result, UnscoredAllocation), case["name"]
            assert only_result.reason == case["expected_unscored_reason"]
            continue

        assert all(isinstance(result, RankedScore) for result in results.values())
        ranked = {
            candidate_id: result
            for candidate_id, result in results.items()
            if isinstance(result, RankedScore)
        }
        actual_order = [
            candidate_id
            for candidate_id, _ in sorted(
                ranked.items(),
                key=lambda item: (-item[1].fit_score, item[0]),
            )
        ]
        assert actual_order == case["expected_order"], case["name"]
        for candidate_id, expected_range in case["expected_fit_ranges"].items():
            assert (
                expected_range[0] <= ranked[candidate_id].fit_score <= expected_range[1]
            )
        if "expected_group_shares" in case:
            first = ranked[case["expected_order"][0]]
            shares = {group.group_id: group.normalized_share for group in first.groups}
            for group_id, expected in case["expected_group_shares"].items():
                assert shares[group_id] == pytest.approx(expected)
        if "expected_factor_ids" in case:
            first = ranked[case["expected_order"][0]]
            assert {factor.factor_id for factor in first.factors} == set(
                case["expected_factor_ids"]
            )
