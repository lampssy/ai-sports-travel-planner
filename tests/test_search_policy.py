from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.data.explain_search_policy import main as explain_policy_main
from app.domain.search_policy import (
    DEFAULT_SEARCH_POLICY_PATH,
    SearchPolicy,
    load_search_policy,
    render_policy_inventory,
    replace_policy_inventory,
)

pytestmark = pytest.mark.db_free


def test_default_search_v4_policy_loads_accepted_numeric_policy() -> None:
    policy = load_search_policy()

    assert policy.search_model_version == "search-v4"
    assert policy.ranking_policy_version == "search-v4-policy-1"
    assert {group.group_id: group.default_budget for group in policy.groups} == {
        "trip_viability": 30,
        "ski_experience": 30,
        "stay_practicality": 15,
        "value": 10,
        "character": 10,
        "travel_effort": 5,
    }
    assert policy.group("travel_effort").max_effective_share == pytest.approx(0.30)
    assert {constraint.constraint_id for constraint in policy.constraints} >= {
        "season_viability",
        "lodging_budget",
        "travel_limit",
    }
    assert dict(policy.group_importance_multipliers) == {
        "ignore": 0,
        "secondary": 0.5,
        "normal": 1,
        "important": 2,
        "primary": 4,
        "very_high": 8,
    }
    assert dict(policy.factor_importance_multipliers) == {
        "low": 0.5,
        "normal": 1,
        "high": 2,
    }
    with pytest.raises(TypeError):
        policy.group_importance_multipliers["normal"] = 9  # type: ignore[index]
    assert {item.correlation_group_id: item.mode for item in policy.correlations} == {
        "terrain_scale": "informational",
        "terrain_fit": "informational",
        "pass_value": "informational",
    }
    assert policy.weather.policy_version == "trip-window-snow-v1"
    assert policy.weather.depth_curve_values == (0, 10, 20, 30, 60, 100)
    assert policy.weather.lead_time_forecast_shares == (0.8, 0.6, 0.4, 0.15)
    assert policy.weather.preferred_short_range_max_lead_days == 15


def test_default_policy_keeps_lodging_measured_and_snowmaking_composed() -> None:
    policy = load_search_policy()

    lodging = policy.factor("lodging_budget_fit")
    assert lodging.lifecycle == "measured"
    assert lodging.base_weight == 0
    assert "ranking" not in lodging.roles

    snowmaking = policy.factor("snowmaking_availability")
    assert snowmaking.lifecycle == "active"
    assert snowmaking.base_weight == 0
    assert snowmaking.composition_target == "trip_window_snow_fit"
    assert snowmaking.composition_policy == "conditional_snowmaking_resilience_v1"
    assert snowmaking.allowed_modes == ("prefer", "ignore", "require")

    refinement = policy.refinement
    assert refinement.max_questions == 3
    assert refinement.top_three_order_margin_points == 2
    assert refinement.top_five_candidate_difference_points == 5


def test_policy_rejects_duplicate_ids_and_invalid_independent_weights() -> None:
    payload = load_search_policy().model_dump(mode="python")
    duplicate = deepcopy(payload)
    duplicate["groups"] = (
        *duplicate["groups"],
        deepcopy(duplicate["groups"][0]),
    )
    with pytest.raises(ValidationError, match="group IDs must be unique"):
        SearchPolicy.model_validate(duplicate)

    invalid_weight = deepcopy(payload)
    factor = next(
        item
        for item in invalid_weight["factors"]
        if item["factor_id"] == "accessible_terrain_scale"
    )
    factor["base_weight"] = 0
    with pytest.raises(ValidationError, match="positive base_weight"):
        SearchPolicy.model_validate(invalid_weight)


def test_policy_rejects_invalid_evidence_readiness_shape() -> None:
    payload = load_search_policy().model_dump(mode="python")
    positive = next(
        item for item in payload["factors"] if item["factor_id"] == "night_skiing"
    )
    positive["readiness"]["minimum_verified_positive_count"] = None

    with pytest.raises(
        ValidationError,
        match="positive_presence requires minimum_verified_positive_count",
    ):
        SearchPolicy.model_validate(payload)


def test_rendered_inventory_is_deterministic_and_replaceable() -> None:
    policy = load_search_policy()

    first = render_policy_inventory(policy, evaluator_statuses={})
    second = render_policy_inventory(policy, evaluator_statuses={})

    assert first == second
    assert "Search model: `search-v4`" in first
    assert "Ranking policy: `search-v4-policy-1`" in first
    assert "`snowmaking_availability`" in first
    assert "conditional_snowmaking_resilience_v1" in first
    assert "##### Correlation Groups" in first
    assert "##### Roles, Values, And Evaluators" in first
    assert "All-eligible default max" in first

    document = (
        "before\n"
        "<!-- search-v4-policy-inventory:start -->\n"
        "old\n"
        "<!-- search-v4-policy-inventory:end -->\n"
        "after\n"
    )
    replaced = replace_policy_inventory(document, first)

    assert replaced.startswith("before\n<!-- search-v4-policy-inventory:start -->")
    assert first in replaced
    assert replaced.endswith("<!-- search-v4-policy-inventory:end -->\nafter\n")


def test_replace_inventory_requires_exactly_one_marker_pair() -> None:
    with pytest.raises(ValueError, match="exactly one inventory marker pair"):
        replace_policy_inventory("no markers", "inventory")


def test_policy_inventory_cli_detects_and_repairs_drift(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    document_path = tmp_path / "ranking.md"
    document_path.write_text(
        "before\n"
        "<!-- search-v4-policy-inventory:start -->\n"
        "stale\n"
        "<!-- search-v4-policy-inventory:end -->\n"
        "after\n",
        encoding="utf-8",
    )
    common_args = [
        "--policy-path",
        str(DEFAULT_SEARCH_POLICY_PATH),
        "--document-path",
        str(document_path),
    ]

    assert explain_policy_main([*common_args, "--check"]) == 1
    assert "inventory is stale" in capsys.readouterr().err
    assert explain_policy_main(common_args) == 0
    capsys.readouterr()
    assert explain_policy_main([*common_args, "--check"]) == 0
    assert "inventory is current" in capsys.readouterr().out
