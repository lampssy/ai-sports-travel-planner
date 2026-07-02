from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

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
GLOBAL_SEARCH_V3_COMPONENTS = frozenset(
    {
        "legacy_base",
        "terrain",
        "skill_fit",
        "stay_base_access",
        "snow_evidence",
        "conditions",
        "budget",
        "travel_effort",
    }
)


@dataclass(frozen=True)
class SearchV3ScoreInputs:
    lodging_quality: int
    terrain_scale: str | None
    terrain_trust_cap: float
    skill_fit: tuple[str, ...]
    skill_trust_cap: float
    access_fit: str | None
    access_trust_cap: float
    snow_confidence_score: float
    conditions_score: float
    budget_penalty: float
    travel_effort_score: float | None


@dataclass(frozen=True)
class SearchV3ScoreBreakdown:
    components: Mapping[str, float]
    total: float


def score_search_v3_configuration(
    inputs: SearchV3ScoreInputs,
) -> SearchV3ScoreBreakdown:
    components = {
        "legacy_base": inputs.lodging_quality * 0.12,
        "terrain": TERRAIN_COMPONENT.get(inputs.terrain_scale or "", 0.0)
        * inputs.terrain_trust_cap,
        "skill_fit": _skill_component(inputs.skill_fit) * inputs.skill_trust_cap,
        "stay_base_access": ACCESS_COMPONENT.get(inputs.access_fit or "", 0.0)
        * inputs.access_trust_cap,
        "snow_evidence": inputs.snow_confidence_score * 0.35,
        "conditions": inputs.conditions_score * 0.25,
        "budget": -inputs.budget_penalty,
        "travel_effort": (
            0.0
            if inputs.travel_effort_score is None
            else -(1 - inputs.travel_effort_score) * 0.35
        ),
    }
    return SearchV3ScoreBreakdown(
        components=MappingProxyType(components),
        total=sum(components.values()),
    )


def active_factor_cap(lifecycle_state: str, ranking_cap: float) -> float:
    return ranking_cap if lifecycle_state == "active" else 0.0


def _skill_component(skill_fit: tuple[str, ...]) -> float:
    if not skill_fit:
        return 0.0
    return max(SKILL_COMPONENT.get(level, 0.0) for level in skill_fit)
