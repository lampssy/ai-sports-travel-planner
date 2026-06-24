from dataclasses import dataclass
from typing import Literal

from app.domain.models import Destination, PisteKmByDifficulty, TerrainDomain

CatalogPolicySeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class CatalogPolicyIssue:
    severity: CatalogPolicySeverity
    message: str


def catalog_policy_issues(
    resorts: list[Destination],
    terrain_domains: list[TerrainDomain] | tuple[TerrainDomain, ...] = (),
) -> list[CatalogPolicyIssue]:
    issues: list[CatalogPolicyIssue] = []
    terrain_domain_ids = {
        terrain_domain.terrain_domain_id for terrain_domain in terrain_domains
    }
    for terrain_domain in terrain_domains:
        _append_difficulty_total_issue(
            issues,
            label=terrain_domain.terrain_domain_id,
            total_piste_km=terrain_domain.total_piste_km,
            difficulty=terrain_domain.piste_km_by_difficulty,
            metric_label="terrain domain difficulty piste total",
        )

    for resort in resorts:
        for ski_area in resort.ski_areas:
            total_piste_km = ski_area.total_piste_km
            difficulty = ski_area.piste_km_by_difficulty
            _append_difficulty_total_issue(
                issues,
                label=f"{resort.resort_id}/{ski_area.ski_area_id}",
                total_piste_km=total_piste_km,
                difficulty=difficulty,
                metric_label="difficulty piste total",
            )

        for terrain_group in resort.terrain_groups:
            _append_difficulty_total_issue(
                issues,
                label=f"{resort.resort_id}/{terrain_group.terrain_group_id}",
                total_piste_km=terrain_group.total_piste_km,
                difficulty=terrain_group.piste_km_by_difficulty,
                metric_label="terrain group difficulty piste total",
            )

        ski_area_ids = {ski_area.ski_area_id for ski_area in resort.ski_areas}
        for product in resort.lift_pass_products:
            unknown_ids = sorted(set(product.valid_ski_area_ids) - ski_area_ids)
            if unknown_ids:
                issues.append(
                    CatalogPolicyIssue(
                        severity="error",
                        message=(
                            f"{resort.resort_id}/{product.lift_pass_product_id}: "
                            "lift pass product references unknown ski_area_id "
                            f"{', '.join(unknown_ids)}"
                        ),
                    )
                )
            unknown_domain_ids = sorted(
                set(product.terrain_domain_ids) - terrain_domain_ids
            )
            if unknown_domain_ids:
                issues.append(
                    CatalogPolicyIssue(
                        severity="error",
                        message=(
                            f"{resort.resort_id}/{product.lift_pass_product_id}: "
                            "lift pass product references unknown terrain_domain_id "
                            f"{', '.join(unknown_domain_ids)}"
                        ),
                    )
                )

        for terrain_group in resort.terrain_groups:
            unknown_ids = sorted(set(terrain_group.ski_area_ids) - ski_area_ids)
            if unknown_ids:
                issues.append(
                    CatalogPolicyIssue(
                        severity="error",
                        message=(
                            f"{resort.resort_id}/{terrain_group.terrain_group_id}: "
                            "terrain group references unknown ski_area_id "
                            f"{', '.join(unknown_ids)}"
                        ),
                    )
                )

        for stay_base in resort.stay_bases:
            if (
                stay_base.access_mode == "walk"
                and stay_base.nearest_lift_distance_m is not None
                and stay_base.nearest_lift_distance_m > 1500
            ):
                issues.append(
                    CatalogPolicyIssue(
                        severity="error",
                        message=(
                            f"{resort.resort_id}/{stay_base.stay_base_id}: "
                            "walk access conflicts with nearest lift distance"
                        ),
                    )
                )

    return issues


def _append_difficulty_total_issue(
    issues: list[CatalogPolicyIssue],
    *,
    label: str,
    total_piste_km: float | None,
    difficulty: PisteKmByDifficulty | None,
    metric_label: str,
) -> None:
    if total_piste_km is None or difficulty is None:
        return
    difficulty_total = (
        difficulty.beginner + difficulty.intermediate + difficulty.advanced
    )
    tolerance = max(1.0, total_piste_km * 0.05)
    if abs(difficulty_total - total_piste_km) <= tolerance:
        return
    issues.append(
        CatalogPolicyIssue(
            severity="error",
            message=f"{label}: {metric_label} does not match total_piste_km",
        )
    )
