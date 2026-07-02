from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.domain.catalog import SkiArea, SkiAreaAccess, TerrainDomain

FactorScope = Literal[
    "destination",
    "ski_area",
    "stay_base",
    "accommodation",
    "rental",
]
FactorTrustState = Literal[
    "source_backed",
    "derived_from_partial_data",
    "manual_estimate",
    "needs_source",
]
FactorLifecycleState = Literal["active", "measured_not_ranked", "planned", "disabled"]
FactorRankingRole = Literal["core", "preference_activated", "none"]

TrustManifestStatus = Literal[
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
]

TERRAIN_SCALE_FACTOR_ID = "terrain_scale"
SKILL_FIT_FACTOR_ID = "skill_fit_profile"
STAY_BASE_ACCESS_FACTOR_ID = "stay_base_access"

TRUST_RANKING_CAPS: dict[FactorTrustState, float] = {
    "source_backed": 1.0,
    "derived_from_partial_data": 0.7,
    "manual_estimate": 0.25,
    "needs_source": 0.0,
}
TERRAIN_SOURCE_LABELS = {
    "ski_area": "selected ski-area terrain",
    "terrain_group": "aggregate/pass-accessible terrain",
    "terrain_domain": "shared-domain/pass-accessible terrain",
}


@dataclass(frozen=True)
class ResortFitFactor:
    factor_id: str
    scope: FactorScope
    entity_id: str
    value: str | int | float | tuple[str, ...] | None
    trust_state: FactorTrustState
    lifecycle_state: FactorLifecycleState
    ranking_role: FactorRankingRole
    user_filter_role: str | None = None
    display_role: str | None = None
    raw_inputs: dict[str, Any] = field(default_factory=dict)
    missing_inputs: tuple[str, ...] = ()

    @property
    def ranking_cap(self) -> float:
        return ranking_cap_for_trust_state(self.trust_state)


def ranking_cap_for_trust_state(trust_state: FactorTrustState) -> float:
    return TRUST_RANKING_CAPS[trust_state]


def trust_state_for_manifest_status(
    status: TrustManifestStatus | str | None,
) -> FactorTrustState:
    if status in {"verified", "verified_with_adjustment"}:
        return "source_backed"
    if status == "estimated":
        return "manual_estimate"
    return "needs_source"


def terrain_scale_factor_for_ski_area(
    ski_area: SkiArea,
) -> ResortFitFactor:
    return _terrain_scale_factor(
        entity_id=ski_area.ski_area_id,
        total_piste_km=ski_area.total_piste_km,
        total_lift_count=ski_area.total_lift_count,
        terrain_source_scope="ski_area",
        terrain_source_id=ski_area.ski_area_id,
    )


def terrain_scale_factor_for_catalog_area(
    ski_area: SkiArea,
    terrain_domains: tuple[TerrainDomain, ...],
) -> ResortFitFactor:
    connected_domains = [
        domain
        for domain in terrain_domains
        if ski_area.ski_area_id in domain.ski_area_ids
        and domain.total_piste_km is not None
    ]
    if not connected_domains:
        return terrain_scale_factor_for_ski_area(ski_area)
    domain = max(
        connected_domains,
        key=lambda item: (item.total_piste_km or 0, item.terrain_domain_id),
    )
    if ski_area.total_piste_km is not None and ski_area.total_piste_km > (
        domain.total_piste_km or 0
    ):
        return terrain_scale_factor_for_ski_area(ski_area)
    return _terrain_scale_factor(
        entity_id=ski_area.ski_area_id,
        total_piste_km=domain.total_piste_km,
        total_lift_count=domain.total_lift_count,
        terrain_source_scope="terrain_domain",
        terrain_source_id=domain.terrain_domain_id,
    )


def _terrain_scale_factor(
    *,
    entity_id: str,
    total_piste_km: float | None,
    total_lift_count: int | None,
    terrain_source_scope: str,
    terrain_source_id: str,
) -> ResortFitFactor:
    if total_piste_km is None:
        return ResortFitFactor(
            factor_id=TERRAIN_SCALE_FACTOR_ID,
            scope="ski_area",
            entity_id=entity_id,
            value=None,
            trust_state="needs_source",
            lifecycle_state="planned",
            ranking_role="core",
            user_filter_role="large_ski_area",
            display_role="terrain_size",
            raw_inputs={
                "terrain_source_scope": terrain_source_scope,
                "terrain_source_id": terrain_source_id,
                "terrain_source_label": _terrain_source_label(terrain_source_scope),
                "total_piste_km": None,
                "total_lift_count": total_lift_count,
            },
            missing_inputs=("total_piste_km",),
        )

    if total_piste_km < 50:
        value = "small"
    elif total_piste_km < 150:
        value = "medium"
    elif total_piste_km < 300:
        value = "large"
    else:
        value = "mega"

    return ResortFitFactor(
        factor_id=TERRAIN_SCALE_FACTOR_ID,
        scope="ski_area",
        entity_id=entity_id,
        value=value,
        trust_state="source_backed",
        lifecycle_state="active",
        ranking_role="core",
        user_filter_role="large_ski_area",
        display_role="terrain_size",
        raw_inputs={
            "terrain_source_scope": terrain_source_scope,
            "terrain_source_id": terrain_source_id,
            "terrain_source_label": _terrain_source_label(terrain_source_scope),
            "total_piste_km": total_piste_km,
            "total_lift_count": total_lift_count,
        },
    )


def _terrain_source_label(terrain_source_scope: str) -> str:
    return TERRAIN_SOURCE_LABELS.get(terrain_source_scope, terrain_source_scope)


def skill_fit_factor_for_ski_area(
    ski_area: SkiArea,
) -> ResortFitFactor:
    if ski_area.piste_km_by_difficulty is None:
        if ski_area.total_piste_km is not None and ski_area.total_piste_km >= 50:
            return ResortFitFactor(
                factor_id=SKILL_FIT_FACTOR_ID,
                scope="ski_area",
                entity_id=ski_area.ski_area_id,
                value=("intermediate",),
                trust_state="derived_from_partial_data",
                lifecycle_state="measured_not_ranked",
                ranking_role="core",
                user_filter_role="skill_level",
                display_role="skill_fit",
                raw_inputs={
                    "total_piste_km": ski_area.total_piste_km,
                    "summit_elevation_m": ski_area.summit_elevation_m,
                    "piste_km_by_difficulty": None,
                },
                missing_inputs=("piste_km_by_difficulty",),
            )
        return ResortFitFactor(
            factor_id=SKILL_FIT_FACTOR_ID,
            scope="ski_area",
            entity_id=ski_area.ski_area_id,
            value=None,
            trust_state="needs_source",
            lifecycle_state="planned",
            ranking_role="core",
            user_filter_role="skill_level",
            display_role="skill_fit",
            raw_inputs={
                "total_piste_km": ski_area.total_piste_km,
                "summit_elevation_m": ski_area.summit_elevation_m,
                "piste_km_by_difficulty": None,
            },
            missing_inputs=("piste_km_by_difficulty",),
        )

    difficulty = ski_area.piste_km_by_difficulty
    difficulty_total_km = max(
        difficulty.beginner + difficulty.intermediate + difficulty.advanced,
        1,
    )
    terrain_total_km = (
        ski_area.total_piste_km
        if ski_area.total_piste_km is not None
        else difficulty_total_km
    )
    beginner_share = difficulty.beginner / difficulty_total_km
    intermediate_share = difficulty.intermediate / difficulty_total_km
    advanced_share = difficulty.advanced / difficulty_total_km

    values: list[str] = []
    if beginner_share >= 0.3 or difficulty.beginner >= 40:
        values.append("beginner")
    if intermediate_share >= 0.25 or terrain_total_km >= 50:
        values.append("intermediate")
    if (
        advanced_share >= 0.2
        or difficulty.advanced >= 35
        or (terrain_total_km >= 150 and ski_area.summit_elevation_m >= 2800)
    ):
        values.append("advanced")
    if not values:
        values.append("intermediate")

    return ResortFitFactor(
        factor_id=SKILL_FIT_FACTOR_ID,
        scope="ski_area",
        entity_id=ski_area.ski_area_id,
        value=tuple(values),
        trust_state="source_backed",
        lifecycle_state="active",
        ranking_role="core",
        user_filter_role="skill_level",
        display_role="skill_fit",
        raw_inputs={
            "total_piste_km": ski_area.total_piste_km,
            "summit_elevation_m": ski_area.summit_elevation_m,
            "piste_km_by_difficulty": {
                "beginner": difficulty.beginner,
                "intermediate": difficulty.intermediate,
                "advanced": difficulty.advanced,
            },
        },
    )


def ski_area_access_factor(access: SkiAreaAccess) -> ResortFitFactor:
    value_by_mode = {
        "walk": "walkable",
        "ski_in_ski_out": "walkable",
        "ski_bus": "shuttle_easy",
        "drive": "car_recommended",
    }
    value = value_by_mode.get(access.access_mode)
    if value is None and access.distance_m is not None:
        if access.distance_m <= 500:
            value = "walkable"
        elif access.distance_m <= 1500:
            value = "shuttle_easy"
        else:
            value = "car_recommended"
    if value is not None:
        return ResortFitFactor(
            factor_id=STAY_BASE_ACCESS_FACTOR_ID,
            scope="stay_base",
            entity_id=access.ski_area_access_id,
            value=value,
            trust_state="source_backed",
            lifecycle_state="active",
            ranking_role="core",
            user_filter_role="stay_base_access",
            display_role="access",
            raw_inputs={
                "distance_m": access.distance_m,
                "duration_minutes": access.duration_minutes,
                "access_mode": access.access_mode,
                "lift_distance": access.lift_distance,
            },
        )

    fallback_by_bucket = {
        "near": "walkable",
        "medium": "shuttle_easy",
        "far": "car_recommended",
    }
    return ResortFitFactor(
        factor_id=STAY_BASE_ACCESS_FACTOR_ID,
        scope="stay_base",
        entity_id=access.ski_area_access_id,
        value=fallback_by_bucket[access.lift_distance],
        trust_state="derived_from_partial_data",
        lifecycle_state="measured_not_ranked",
        ranking_role="core",
        user_filter_role="stay_base_access",
        display_role="access",
        raw_inputs={
            "distance_m": None,
            "duration_minutes": access.duration_minutes,
            "access_mode": access.access_mode,
            "lift_distance": access.lift_distance,
        },
        missing_inputs=("distance_m", "access_mode"),
    )
