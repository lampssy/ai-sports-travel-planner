from dataclasses import dataclass
from typing import Literal

from app.domain.catalog import CatalogPisteKmByDifficulty, CatalogSnapshot

CatalogPolicySeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class CatalogPolicyIssue:
    severity: CatalogPolicySeverity
    message: str


def catalog_policy_issues(snapshot: CatalogSnapshot) -> list[CatalogPolicyIssue]:
    issues: list[CatalogPolicyIssue] = []
    for ski_area in snapshot.ski_areas:
        _append_difficulty_total_issue(
            issues,
            label=f"ski_areas/{ski_area.ski_area_id}",
            total_piste_km=ski_area.total_piste_km,
            difficulty=ski_area.piste_km_by_difficulty,
            metric_label="difficulty piste total",
        )
    for terrain_domain in snapshot.terrain_domains:
        _append_difficulty_total_issue(
            issues,
            label=f"terrain_domains/{terrain_domain.terrain_domain_id}",
            total_piste_km=terrain_domain.total_piste_km,
            difficulty=terrain_domain.piste_km_by_difficulty,
            metric_label="terrain domain difficulty piste total",
        )
    for product in snapshot.lift_pass_products:
        aggregate = product.pass_accessible_terrain
        if aggregate is not None:
            _append_difficulty_total_issue(
                issues,
                label=f"lift_pass_products/{product.lift_pass_product_id}",
                total_piste_km=aggregate.total_piste_km,
                difficulty=aggregate.piste_km_by_difficulty,
                metric_label="pass-accessible difficulty piste total",
            )
    for access in snapshot.ski_area_access:
        if (
            access.access_mode == "walk"
            and access.distance_m is not None
            and access.distance_m > 1500
        ):
            issues.append(
                CatalogPolicyIssue(
                    severity="error",
                    message=(
                        f"ski_area_access/{access.ski_area_access_id}: "
                        "walk access conflicts with distance_m"
                    ),
                )
            )
    return issues


def _append_difficulty_total_issue(
    issues: list[CatalogPolicyIssue],
    *,
    label: str,
    total_piste_km: float | None,
    difficulty: CatalogPisteKmByDifficulty | None,
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
