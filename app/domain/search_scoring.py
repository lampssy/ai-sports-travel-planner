from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    Destination,
    SearchResult,
    SkiArea,
    StayBase,
    TerrainDomain,
)
from app.domain.resort_fit import (
    ResortFitFactor,
    accessible_terrain_factor_for_option,
    skill_fit_factor_for_ski_area,
    stay_base_access_factor,
)

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


def search_v2_score_for_result(
    result: SearchResult,
    *,
    destination: Destination,
    ski_area: SkiArea,
    stay_base: StayBase,
    terrain_domains: tuple[TerrainDomain, ...],
) -> CandidateScoreBreakdown:
    terrain_factor = accessible_terrain_factor_for_option(
        destination=destination,
        selected_ski_area_id=ski_area.ski_area_id,
        terrain_domains=terrain_domains,
    )
    skill_factor = skill_fit_factor_for_ski_area(ski_area)
    access_factor = stay_base_access_factor(stay_base)
    return candidate_score_for_result(
        result,
        terrain_scale=_string_value(terrain_factor),
        terrain_trust_cap=_candidate_cap(terrain_factor),
        skill_fit=_tuple_value(skill_factor),
        skill_trust_cap=_candidate_cap(skill_factor),
        stay_base_access=_string_value(access_factor),
        access_trust_cap=_candidate_cap(access_factor),
    )


def _skill_component(skill_fit: tuple[str, ...]) -> float:
    if not skill_fit:
        return 0.0
    return max(SKILL_COMPONENT.get(level, 0.0) for level in skill_fit)


def _travel_effort_component(result: SearchResult) -> float:
    if result.travel_effort is None:
        return 0.0
    return -(1 - result.travel_effort.score) * 0.35


def _candidate_cap(factor: ResortFitFactor | None) -> float:
    if factor is None or factor.lifecycle_state != "active":
        return 0.0
    return factor.ranking_cap


def _string_value(factor: ResortFitFactor | None) -> str | None:
    if factor is None or factor.value is None:
        return None
    if isinstance(factor.value, str):
        return factor.value
    return str(factor.value)


def _tuple_value(factor: ResortFitFactor | None) -> tuple[str, ...]:
    if factor is None or factor.value is None:
        return ()
    if isinstance(factor.value, tuple):
        return tuple(str(value) for value in factor.value)
    return (str(factor.value),)
