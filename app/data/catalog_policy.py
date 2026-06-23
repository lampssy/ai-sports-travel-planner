from dataclasses import dataclass
from typing import Literal

from app.domain.models import Destination

CatalogPolicySeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class CatalogPolicyIssue:
    severity: CatalogPolicySeverity
    message: str


def catalog_policy_issues(resorts: list[Destination]) -> list[CatalogPolicyIssue]:
    issues: list[CatalogPolicyIssue] = []
    for resort in resorts:
        for ski_area in resort.ski_areas:
            total_piste_km = ski_area.total_piste_km
            difficulty = ski_area.piste_km_by_difficulty
            if total_piste_km is not None and difficulty is not None:
                difficulty_total = (
                    difficulty.beginner + difficulty.intermediate + difficulty.advanced
                )
                tolerance = max(1.0, total_piste_km * 0.05)
                if abs(difficulty_total - total_piste_km) > tolerance:
                    issues.append(
                        CatalogPolicyIssue(
                            severity="error",
                            message=(
                                f"{resort.resort_id}/{ski_area.ski_area_id}: "
                                "difficulty piste total does not match total_piste_km"
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
