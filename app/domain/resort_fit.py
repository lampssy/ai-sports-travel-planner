from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.domain.catalog import SkiArea as CatalogSkiArea
from app.domain.catalog import SkiAreaAccess
from app.domain.catalog import TerrainDomain as CatalogTerrainDomain
from app.domain.models import (
    Destination,
    SkiArea,
    StayBase,
    TerrainDomain,
    TerrainGroup,
)

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
    ski_area: SkiArea | CatalogSkiArea,
) -> ResortFitFactor:
    return _terrain_scale_factor(
        entity_id=ski_area.ski_area_id,
        total_piste_km=ski_area.total_piste_km,
        total_lift_count=ski_area.total_lift_count,
        terrain_source_scope="ski_area",
        terrain_source_id=ski_area.ski_area_id,
    )


def terrain_scale_factor_for_catalog_area(
    ski_area: CatalogSkiArea,
    terrain_domains: tuple[CatalogTerrainDomain, ...],
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


def accessible_terrain_factor_for_option(
    *,
    destination: Destination,
    selected_ski_area_id: str,
    terrain_domains: tuple[TerrainDomain, ...] = (),
) -> ResortFitFactor:
    selected_ski_area = _find_ski_area(destination, selected_ski_area_id)
    if selected_ski_area is None:
        return ResortFitFactor(
            factor_id=TERRAIN_SCALE_FACTOR_ID,
            scope="ski_area",
            entity_id=selected_ski_area_id,
            value=None,
            trust_state="needs_source",
            lifecycle_state="planned",
            ranking_role="core",
            user_filter_role="large_ski_area",
            display_role="terrain_size",
            raw_inputs={
                "terrain_source_scope": "ski_area",
                "terrain_source_id": selected_ski_area_id,
                "terrain_source_label": _terrain_source_label("ski_area"),
                "total_piste_km": None,
                "total_lift_count": None,
            },
            missing_inputs=("selected_ski_area", "total_piste_km"),
        )

    default_pass = next(
        (product for product in destination.lift_pass_products if product.is_default),
        None,
    )
    if default_pass is not None:
        terrain_domain = _default_pass_terrain_domain(
            destination=destination,
            selected_ski_area_id=selected_ski_area_id,
            terrain_domain_ids=tuple(default_pass.terrain_domain_ids),
            terrain_domains=terrain_domains,
        )
        if terrain_domain is not None:
            return _terrain_scale_factor(
                entity_id=selected_ski_area_id,
                total_piste_km=terrain_domain.total_piste_km,
                total_lift_count=terrain_domain.total_lift_count,
                terrain_source_scope="terrain_domain",
                terrain_source_id=terrain_domain.terrain_domain_id,
            )

        terrain_group = _default_pass_terrain_group(
            destination=destination,
            selected_ski_area_id=selected_ski_area_id,
            valid_ski_area_ids=tuple(default_pass.valid_ski_area_ids),
        )
        if terrain_group is not None:
            return _terrain_scale_factor(
                entity_id=selected_ski_area_id,
                total_piste_km=terrain_group.total_piste_km,
                total_lift_count=terrain_group.total_lift_count,
                terrain_source_scope="terrain_group",
                terrain_source_id=terrain_group.terrain_group_id,
            )

    return terrain_scale_factor_for_ski_area(selected_ski_area)


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


def _find_ski_area(destination: Destination, ski_area_id: str) -> SkiArea | None:
    return next(
        (
            ski_area
            for ski_area in destination.ski_areas
            if ski_area.ski_area_id == ski_area_id
        ),
        None,
    )


def _default_pass_terrain_domain(
    *,
    destination: Destination,
    selected_ski_area_id: str,
    terrain_domain_ids: tuple[str, ...],
    terrain_domains: tuple[TerrainDomain, ...],
) -> TerrainDomain | None:
    if not terrain_domain_ids:
        return None
    domain_by_id = {
        terrain_domain.terrain_domain_id: terrain_domain
        for terrain_domain in terrain_domains
    }
    for terrain_domain_id in terrain_domain_ids:
        terrain_domain = domain_by_id.get(terrain_domain_id)
        if terrain_domain is None:
            continue
        if _terrain_domain_contains_ski_area(
            terrain_domain,
            resort_id=destination.resort_id,
            ski_area_id=selected_ski_area_id,
        ):
            return terrain_domain
    return None


def _terrain_domain_contains_ski_area(
    terrain_domain: TerrainDomain,
    *,
    resort_id: str,
    ski_area_id: str,
) -> bool:
    return any(
        ref.resort_id == resort_id and ref.ski_area_id == ski_area_id
        for ref in terrain_domain.ski_area_refs
    )


def _default_pass_terrain_group(
    *,
    destination: Destination,
    selected_ski_area_id: str,
    valid_ski_area_ids: tuple[str, ...],
) -> TerrainGroup | None:
    if selected_ski_area_id not in valid_ski_area_ids or len(valid_ski_area_ids) < 2:
        return None
    valid_ski_area_id_set = set(valid_ski_area_ids)
    return next(
        (
            terrain_group
            for terrain_group in destination.terrain_groups
            if selected_ski_area_id in terrain_group.ski_area_ids
            and set(terrain_group.ski_area_ids).issubset(valid_ski_area_id_set)
        ),
        None,
    )


def skill_fit_factor_for_ski_area(
    ski_area: SkiArea | CatalogSkiArea,
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


def stay_base_access_factor(stay_base: StayBase) -> ResortFitFactor:
    if stay_base.access_mode == "walk":
        return _stay_base_access_source_backed(stay_base, "walkable")
    if stay_base.access_mode == "ski_bus":
        return _stay_base_access_source_backed(stay_base, "shuttle_easy")
    if stay_base.access_mode == "car_recommended":
        return _stay_base_access_source_backed(stay_base, "car_recommended")

    distance_m = stay_base.nearest_lift_distance_m
    if distance_m is not None:
        if distance_m <= 500:
            return _stay_base_access_source_backed(stay_base, "walkable")
        if distance_m <= 1500:
            return _stay_base_access_source_backed(stay_base, "shuttle_easy")
        return _stay_base_access_source_backed(stay_base, "car_recommended")

    fallback_by_legacy_bucket = {
        "near": "walkable",
        "medium": "shuttle_easy",
        "far": "car_recommended",
    }
    return ResortFitFactor(
        factor_id=STAY_BASE_ACCESS_FACTOR_ID,
        scope="stay_base",
        entity_id=stay_base.stay_base_id,
        value=fallback_by_legacy_bucket.get(stay_base.lift_distance, "unknown"),
        trust_state="derived_from_partial_data",
        lifecycle_state="measured_not_ranked",
        ranking_role="core",
        user_filter_role="stay_base_access",
        display_role="access",
        raw_inputs={
            "nearest_lift_distance_m": None,
            "access_mode": stay_base.access_mode,
            "lift_distance": stay_base.lift_distance,
        },
        missing_inputs=("nearest_lift_distance_m", "access_mode"),
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


def _stay_base_access_source_backed(
    stay_base: StayBase,
    value: str,
) -> ResortFitFactor:
    return ResortFitFactor(
        factor_id=STAY_BASE_ACCESS_FACTOR_ID,
        scope="stay_base",
        entity_id=stay_base.stay_base_id,
        value=value,
        trust_state="source_backed",
        lifecycle_state="active",
        ranking_role="core",
        user_filter_role="stay_base_access",
        display_role="access",
        raw_inputs={
            "nearest_lift_distance_m": stay_base.nearest_lift_distance_m,
            "access_mode": stay_base.access_mode,
            "lift_distance": stay_base.lift_distance,
        },
    )
