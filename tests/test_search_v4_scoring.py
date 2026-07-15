from __future__ import annotations

from copy import deepcopy

import pytest

from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import SearchPolicy, load_search_policy
from app.domain.search_ranking import (
    RankedScore,
    SearchRankingInputError,
    UnscoredAllocation,
    capped_normalize,
    score_factor_evaluations,
)
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    GroupPriorityPatch,
    SearchIntent,
)

pytestmark = pytest.mark.db_free


def _evaluation(
    factor_id: str,
    utility: float,
    *,
    evidence_cap: float = 1,
    neutral: float = 0.5,
) -> FactorEvaluation:
    return FactorEvaluation(
        factor_id=factor_id,
        scope="test",
        entity_ids=("candidate",),
        raw_value=utility,
        raw_utility=utility,
        neutral_utility=neutral,
        effective_evidence_cap=evidence_cap,
        evidence_cap_components={"source": evidence_cap},
        warnings=(),
        provenance_summary="Test evidence.",
        explanation_inputs={},
    )


def _all_group_evaluations(*, utility: float = 1) -> tuple[FactorEvaluation, ...]:
    return (
        _evaluation("trip_window_snow_fit", utility),
        _evaluation("accessible_terrain_scale", utility),
        _evaluation("stay_base_access", utility),
        _evaluation("pass_terrain_value", utility),
        _evaluation("local_pace", utility),
        _evaluation("travel_effort", utility),
    )


def _all_group_intent(**kwargs) -> SearchIntent:
    preferences = (
        FactorPreferencePatch(
            factor_id="local_pace",
            mode="prefer",
            values=("quiet",),
            importance="normal",
        ),
    )
    from app.domain.search_v4_models import SearchObjective

    return SearchIntent(
        factor_preferences=preferences,
        objectives=(
            SearchObjective(
                factor_id="pass_terrain_value",
                importance="normal",
            ),
        ),
        **kwargs,
    )


def test_score_normalizes_only_active_groups_and_factors() -> None:
    result = score_factor_evaluations(
        evaluations=(
            _evaluation("accessible_terrain_scale", 0.8),
            _evaluation("party_skill_coverage", 0.6),
            _evaluation("stay_base_access", 0.7),
        ),
        intent=SearchIntent(),
        policy=load_search_policy(),
    )

    assert isinstance(result, RankedScore)
    assert result.fit_score == pytest.approx(71.3333333333)
    groups = {group.group_id: group for group in result.groups}
    assert groups["ski_experience"].normalized_share == pytest.approx(2 / 3)
    assert groups["stay_practicality"].normalized_share == pytest.approx(1 / 3)
    assert groups["ski_experience"].group_utility == pytest.approx(0.72)
    assert sum(item.contribution_points for item in result.factors) == pytest.approx(
        result.fit_score
    )


def test_evidence_cap_shrinks_toward_declared_neutral() -> None:
    result = score_factor_evaluations(
        evaluations=(
            _evaluation(
                "accessible_terrain_scale",
                1,
                evidence_cap=0.25,
                neutral=0.5,
            ),
        ),
        intent=SearchIntent(),
        policy=load_search_policy(),
    )

    assert isinstance(result, RankedScore)
    assert result.fit_score == pytest.approx(62.5)
    assert result.factors[0].effective_utility == pytest.approx(0.625)


def test_factor_importance_reallocates_only_inside_group() -> None:
    result = score_factor_evaluations(
        evaluations=(
            _evaluation("accessible_terrain_scale", 1),
            _evaluation("party_skill_coverage", 0),
            _evaluation("stay_base_access", 1),
        ),
        intent=SearchIntent(
            factor_preferences=(
                FactorPreferencePatch(
                    factor_id="accessible_terrain_scale",
                    mode="prefer",
                    importance="high",
                ),
            )
        ),
        policy=load_search_policy(),
    )

    assert isinstance(result, RankedScore)
    groups = {group.group_id: group for group in result.groups}
    assert groups["ski_experience"].normalized_share == pytest.approx(2 / 3)
    assert groups["ski_experience"].group_utility == pytest.approx(0.75)


def test_avoid_direction_inverts_raw_utility_before_trust_shrink() -> None:
    result = score_factor_evaluations(
        evaluations=(
            _evaluation("night_skiing", 1, evidence_cap=0.5),
            _evaluation("accessible_terrain_scale", 0.5),
        ),
        intent=SearchIntent(
            factor_preferences=(
                FactorPreferencePatch(
                    factor_id="night_skiing",
                    mode="avoid",
                    importance="normal",
                ),
            )
        ),
        policy=load_search_policy(),
    )

    assert isinstance(result, RankedScore)
    night = next(item for item in result.factors if item.factor_id == "night_skiing")
    assert night.direction == "avoid"
    assert night.raw_utility == 0
    assert night.effective_utility == pytest.approx(0.25)


def test_group_importance_matches_accepted_ski_and_travel_examples() -> None:
    policy = load_search_policy()
    ski = score_factor_evaluations(
        evaluations=_all_group_evaluations(),
        intent=_all_group_intent(
            group_priorities=(
                GroupPriorityPatch(group_id="ski_experience", importance="very_high"),
            )
        ),
        policy=policy,
    )
    travel = score_factor_evaluations(
        evaluations=_all_group_evaluations(),
        intent=_all_group_intent(
            group_priorities=(
                GroupPriorityPatch(group_id="travel_effort", importance="very_high"),
            )
        ),
        policy=policy,
    )

    assert isinstance(ski, RankedScore)
    assert isinstance(travel, RankedScore)
    ski_groups = {group.group_id: group for group in ski.groups}
    travel_groups = {group.group_id: group for group in travel.groups}
    assert ski_groups["ski_experience"].normalized_share == pytest.approx(240 / 310)
    assert travel_groups["travel_effort"].normalized_share == pytest.approx(40 / 135)


def test_travel_effort_cap_redistributes_excess() -> None:
    result = score_factor_evaluations(
        evaluations=(
            _evaluation("accessible_terrain_scale", 1),
            _evaluation("travel_effort", 1),
        ),
        intent=SearchIntent(
            group_priorities=(
                GroupPriorityPatch(group_id="travel_effort", importance="very_high"),
            )
        ),
        policy=load_search_policy(),
    )

    assert isinstance(result, RankedScore)
    groups = {group.group_id: group for group in result.groups}
    assert groups["travel_effort"].normalized_share == pytest.approx(0.30)
    assert groups["ski_experience"].normalized_share == pytest.approx(0.70)


def test_context_factor_does_not_consume_budget_without_evidence() -> None:
    result = score_factor_evaluations(
        evaluations=(
            _evaluation("accessible_terrain_scale", 0.8),
            _evaluation("travel_effort", 0.5, evidence_cap=0),
        ),
        intent=SearchIntent(),
        policy=load_search_policy(),
    )

    assert isinstance(result, RankedScore)
    assert [group.group_id for group in result.groups] == ["ski_experience"]


def test_only_capped_travel_group_returns_typed_unscored_result() -> None:
    result = score_factor_evaluations(
        evaluations=(_evaluation("travel_effort", 0.8),),
        intent=SearchIntent(),
        policy=load_search_policy(),
    )

    assert isinstance(result, UnscoredAllocation)
    assert result.reason == "infeasible_group_caps"
    assert result.active_group_ids == ("travel_effort",)


def test_capped_normalize_rejects_empty_or_infeasible_allocations() -> None:
    assert capped_normalize({}, {}) is None
    assert capped_normalize({"travel": 5}, {"travel": 0.3}) is None
    assert capped_normalize(
        {"ski": 30, "travel": 40},
        {"ski": 1, "travel": 0.3},
    ) == pytest.approx({"ski": 0.7, "travel": 0.3})


def test_declared_correlation_cap_changes_only_effective_weights() -> None:
    payload = load_search_policy().model_dump(mode="python")
    correlation = next(
        item
        for item in payload["correlations"]
        if item["correlation_group_id"] == "terrain_scale"
    )
    correlation["mode"] = "capped"
    correlation["max_combined_effective_weight"] = 4
    policy = SearchPolicy.model_validate(deepcopy(payload))
    result = score_factor_evaluations(
        evaluations=(
            _evaluation("accessible_terrain_scale", 1),
            _evaluation("terrain_potential_scale", 1),
            _evaluation("party_skill_coverage", 0),
        ),
        intent=SearchIntent(
            factor_preferences=(
                FactorPreferencePatch(
                    factor_id="terrain_potential_scale",
                    mode="prefer",
                    importance="high",
                ),
            )
        ),
        policy=policy,
    )

    assert isinstance(result, RankedScore)
    by_factor = {factor.factor_id: factor for factor in result.factors}
    assert by_factor["accessible_terrain_scale"].effective_weight == pytest.approx(
        12 / 7
    )
    assert by_factor["terrain_potential_scale"].effective_weight == pytest.approx(
        16 / 7
    )
    assert by_factor["party_skill_coverage"].effective_weight == 2


def test_scorer_rejects_duplicate_or_policy_inconsistent_evaluations() -> None:
    evaluation = _evaluation("accessible_terrain_scale", 0.5)
    with pytest.raises(SearchRankingInputError, match="duplicate factor evaluations"):
        score_factor_evaluations(
            evaluations=(evaluation, evaluation),
            intent=SearchIntent(),
            policy=load_search_policy(),
        )

    with pytest.raises(SearchRankingInputError, match="neutral utility"):
        score_factor_evaluations(
            evaluations=(
                _evaluation(
                    "accessible_terrain_scale",
                    0.5,
                    neutral=0.25,
                ),
            ),
            intent=SearchIntent(),
            policy=load_search_policy(),
        )
