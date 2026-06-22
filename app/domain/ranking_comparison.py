from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from app.domain.models import SearchResult

TERRAIN_COMPONENT = {
    "small": 0.05,
    "medium": 0.12,
    "large": 0.20,
    "mega": 0.28,
}
ACCESS_COMPONENT = {
    "walkable": 0.18,
    "shuttle_easy": 0.12,
    "car_recommended": 0.04,
}
SKILL_COMPONENT = {
    "beginner": 0.18,
    "intermediate": 0.16,
    "advanced": 0.16,
}


@dataclass(frozen=True)
class CandidateScoreBreakdown:
    components: dict[str, float]
    total: float


@dataclass(frozen=True)
class FactorComparisonInput:
    terrain_scale: str | None
    terrain_trust_cap: float
    skill_fit: tuple[str, ...]
    skill_trust_cap: float
    stay_base_access: str | None
    access_trust_cap: float


@dataclass(frozen=True)
class RankingComparisonRow:
    option_key: str
    resort_id: str
    resort_name: str
    selected_ski_area_id: str
    selected_ski_area_name: str
    selected_stay_base_name: str
    current_rank: int
    candidate_rank: int
    rank_delta: int
    current_score: float
    candidate_score: float
    top_candidate_components: dict[str, float]
    scenario_id: str = "default"


@dataclass(frozen=True)
class RankingComparisonReport:
    rows: list[RankingComparisonRow]


def candidate_score_for_result(
    result: SearchResult,
    *,
    terrain_scale: str | None,
    terrain_trust_cap: float,
    skill_fit: tuple[str, ...],
    skill_trust_cap: float,
    stay_base_access: str | None,
    access_trust_cap: float,
) -> CandidateScoreBreakdown:
    components = {
        "legacy_base": result.rating_estimate * 0.12,
        "terrain": TERRAIN_COMPONENT.get(terrain_scale or "", 0.0) * terrain_trust_cap,
        "skill_fit": _skill_component(skill_fit) * skill_trust_cap,
        "stay_base_access": ACCESS_COMPONENT.get(stay_base_access or "", 0.0)
        * access_trust_cap,
        "snow_evidence": result.snow_confidence_score * 0.35,
        "conditions": result.conditions_score * 0.25,
        "budget": -result.budget_penalty,
        "travel_effort": _travel_effort_component(result),
    }
    return CandidateScoreBreakdown(
        components=components,
        total=sum(components.values()),
    )


def _skill_component(skill_fit: tuple[str, ...]) -> float:
    if not skill_fit:
        return 0.0
    return max(SKILL_COMPONENT.get(level, 0.0) for level in skill_fit)


def _travel_effort_component(result: SearchResult) -> float:
    if result.travel_effort is None:
        return 0.0
    return -(1 - result.travel_effort.score) * 0.35


def compare_rankings(
    results: list[SearchResult],
    *,
    factor_inputs: Mapping[str, FactorComparisonInput],
    scenario_id: str = "default",
) -> RankingComparisonReport:
    current_order = sorted(
        results,
        key=lambda result: (-result.score, option_key_for_result(result)),
    )
    current_rank_by_option_key = {
        option_key_for_result(result): index
        for index, result in enumerate(current_order, start=1)
    }

    scored_results = [
        (
            result,
            candidate_score_for_result(
                result,
                **_factor_input_for_result(result, factor_inputs).__dict__,
            ),
        )
        for result in results
    ]
    candidate_order = sorted(
        scored_results,
        key=lambda item: (-item[1].total, option_key_for_result(item[0])),
    )
    candidate_rank_by_option_key = {
        option_key_for_result(result): index
        for index, (result, _) in enumerate(candidate_order, start=1)
    }

    rows = []
    for result, breakdown in scored_results:
        option_key = option_key_for_result(result)
        current_rank = current_rank_by_option_key[option_key]
        candidate_rank = candidate_rank_by_option_key[option_key]
        rows.append(
            RankingComparisonRow(
                option_key=option_key,
                resort_id=result.resort_id,
                resort_name=result.resort_name,
                selected_ski_area_id=result.selected_ski_area_id,
                selected_ski_area_name=result.selected_ski_area_name,
                selected_stay_base_name=result.selected_stay_base_name,
                current_rank=current_rank,
                candidate_rank=candidate_rank,
                rank_delta=candidate_rank - current_rank,
                current_score=result.score,
                candidate_score=breakdown.total,
                top_candidate_components=_top_positive_components(breakdown),
                scenario_id=scenario_id,
            )
        )
    return RankingComparisonReport(rows=sorted(rows, key=lambda row: row.current_rank))


def _factor_input_for_result(
    result: SearchResult,
    factor_inputs: Mapping[str, FactorComparisonInput],
) -> FactorComparisonInput:
    option_key = option_key_for_result(result)
    return factor_inputs.get(
        option_key,
        factor_inputs.get(
            result.resort_id,
            _empty_factor_input(),
        ),
    )


def option_key_for_result(result: SearchResult) -> str:
    return "--".join(
        (
            _slug_part(result.resort_id),
            _slug_part(result.selected_ski_area_id),
            _slug_part(result.selected_stay_base_name),
        )
    )


def _slug_part(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _empty_factor_input() -> FactorComparisonInput:
    return FactorComparisonInput(
        terrain_scale=None,
        terrain_trust_cap=0.0,
        skill_fit=(),
        skill_trust_cap=0.0,
        stay_base_access=None,
        access_trust_cap=0.0,
    )


def _top_positive_components(
    breakdown: CandidateScoreBreakdown,
) -> dict[str, float]:
    positive_components = (
        (name, value)
        for name, value in breakdown.components.items()
        if value > 0 and name != "legacy_base"
    )
    return dict(sorted(positive_components, key=lambda item: item[1], reverse=True)[:3])
