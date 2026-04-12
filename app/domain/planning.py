from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    Resort,
    ResortConditions,
    ResortConditionSnapshot,
)
from app.domain.planning_policy import DEFAULT_PLANNING_HEURISTIC_POLICY

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

POLICY = DEFAULT_PLANNING_HEURISTIC_POLICY


@dataclass(frozen=True)
class PlanningAssessment:
    conditions: ResortConditions
    planning_summary: str
    evidence_count: int
    best_travel_months: tuple[int, ...]
    latest_snapshot_at: str | None


def derive_planning_assessment(
    *,
    resort: Resort,
    travel_month: int,
    snapshots: tuple[ResortConditionSnapshot, ...],
) -> PlanningAssessment:
    score, conditions_score, availability_status, evidence_count = _planning_values(
        resort=resort,
        travel_month=travel_month,
        snapshots=snapshots,
    )
    month_name = MONTH_NAMES[travel_month]
    best_months = _best_travel_months(resort=resort, snapshots=snapshots)
    snow_label = _snow_label(score)

    if availability_status == "out_of_season":
        summary = (
            f"{month_name} sits outside the typical ski season window for this resort."
        )
    elif evidence_count > 1:
        summary = (
            f"{month_name} looks {snow_label} for planning based on {evidence_count} "
            "stored conditions snapshots plus resort seasonality."
        )
    elif evidence_count == 1:
        summary = (
            f"{month_name} looks {snow_label} for planning, but the signal is based on "
            "limited recent history plus resort seasonality."
        )
    else:
        summary = (
            f"{month_name} looks {snow_label} for planning based on resort seasonality "
            "and elevation while snapshot history is still sparse."
        )

    return PlanningAssessment(
        conditions=ResortConditions(
            resort_name=resort.name,
            snow_confidence_score=score,
            snow_confidence_label=snow_label,
            availability_status=availability_status,
            weather_summary=summary,
            conditions_score=conditions_score,
        ),
        planning_summary=summary,
        evidence_count=evidence_count,
        best_travel_months=best_months,
        latest_snapshot_at=_latest_snapshot_at(
            travel_month=travel_month,
            snapshots=snapshots,
        ),
    )


def _planning_values(
    *,
    resort: Resort,
    travel_month: int,
    snapshots: tuple[ResortConditionSnapshot, ...],
) -> tuple[float, float, str, int]:
    if not _is_month_in_season(
        travel_month, resort.season_start_month, resort.season_end_month
    ):
        out_of_season_snow_score = POLICY.out_of_season_snow_score
        out_of_season_conditions_score = POLICY.out_of_season_conditions_score
        return (
            out_of_season_snow_score,
            out_of_season_conditions_score,
            "out_of_season",
            0,
        )

    heuristic_snow = _heuristic_snow_score(resort, travel_month)
    heuristic_conditions = round(
        min(
            max(
                heuristic_snow * POLICY.heuristic_conditions_weight
                + POLICY.heuristic_conditions_offset,
                0.0,
            ),
            1.0,
        ),
        2,
    )

    monthly_snapshots = tuple(
        snapshot for snapshot in snapshots if snapshot.observed_month == travel_month
    )
    if not monthly_snapshots:
        availability_status = (
            "open"
            if heuristic_conditions >= POLICY.open_conditions_threshold
            else "limited"
        )
        return heuristic_snow, heuristic_conditions, availability_status, 0

    average_snow = round(
        sum(snapshot.snow_confidence_score for snapshot in monthly_snapshots)
        / len(monthly_snapshots),
        2,
    )
    average_conditions = round(
        sum(snapshot.conditions_score for snapshot in monthly_snapshots)
        / len(monthly_snapshots),
        2,
    )
    snow_score = round(
        average_snow * POLICY.snapshot_weight
        + heuristic_snow * POLICY.heuristic_backstop_weight,
        2,
    )
    conditions_score = round(
        average_conditions * POLICY.snapshot_weight
        + heuristic_conditions * POLICY.heuristic_backstop_weight,
        2,
    )

    if len(monthly_snapshots) == 1:
        snow_score = round(max(snow_score - POLICY.single_snapshot_penalty, 0.0), 2)
        conditions_score = round(
            max(conditions_score - POLICY.single_snapshot_penalty, 0.0),
            2,
        )

    availability_status = (
        "open" if conditions_score >= POLICY.open_conditions_threshold else "limited"
    )
    return snow_score, conditions_score, availability_status, len(monthly_snapshots)


def _best_travel_months(
    *,
    resort: Resort,
    snapshots: tuple[ResortConditionSnapshot, ...],
) -> tuple[int, ...]:
    scored_months: list[tuple[int, float]] = []
    for month in range(1, 13):
        score, conditions_score, availability_status, _ = _planning_values(
            resort=resort,
            travel_month=month,
            snapshots=snapshots,
        )
        if availability_status == "out_of_season":
            continue
        scored_months.append((month, score + conditions_score))

    scored_months.sort(key=lambda item: (-item[1], item[0]))
    return tuple(month for month, _ in scored_months[:3])


def _latest_snapshot_at(
    *,
    travel_month: int,
    snapshots: tuple[ResortConditionSnapshot, ...],
) -> str | None:
    observed_at_values = [
        snapshot.observed_at
        for snapshot in snapshots
        if snapshot.observed_month == travel_month
    ]
    if not observed_at_values:
        return None
    return max(observed_at_values)


def _heuristic_snow_score(resort: Resort, travel_month: int) -> float:
    season_months = _season_months(resort.season_start_month, resort.season_end_month)
    index = season_months.index(travel_month)
    edge_distance = min(index, len(season_months) - 1 - index)
    if edge_distance >= 2:
        seasonality_score = POLICY.seasonality_core_month_score
    elif edge_distance == 1:
        seasonality_score = POLICY.seasonality_shoulder_month_score
    else:
        seasonality_score = POLICY.seasonality_edge_month_score

    elevation_factor = min(
        max(
            (resort.summit_elevation_m - POLICY.elevation_baseline_m)
            / POLICY.elevation_normalization_span_m,
            0.0,
        ),
        1.0,
    )
    elevation_score = (
        POLICY.elevation_floor_score
        + elevation_factor * POLICY.elevation_variable_score
    )
    return round(
        min(
            max(
                seasonality_score * POLICY.seasonality_weight
                + elevation_score * POLICY.elevation_weight,
                0.0,
            ),
            1.0,
        ),
        2,
    )


def _is_month_in_season(month: int, start_month: int, end_month: int) -> bool:
    if start_month <= end_month:
        return start_month <= month <= end_month
    return month >= start_month or month <= end_month


def _season_months(start_month: int, end_month: int) -> list[int]:
    months = [start_month]
    current = start_month
    while current != end_month:
        current = 1 if current == 12 else current + 1
        months.append(current)
    return months


def _snow_label(score: float) -> str:
    if score < POLICY.poor_snow_threshold:
        return "poor"
    if score < POLICY.fair_snow_threshold:
        return "fair"
    return "good"
