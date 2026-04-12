from __future__ import annotations

from dataclasses import dataclass

PLANNING_HEURISTIC_VERSION = "v1"


@dataclass(frozen=True)
class PlanningHeuristicPolicy:
    # Out-of-season months should remain valid numeric results, but clearly weak.
    out_of_season_snow_score: float = 0.18
    out_of_season_conditions_score: float = 0.08

    # Mid-season months should score strongest,
    # shoulder months next, edge months weakest.
    seasonality_core_month_score: float = 0.92
    seasonality_shoulder_month_score: float = 0.74
    seasonality_edge_month_score: float = 0.52

    # Seasonality drives the heuristic more than elevation, but both matter.
    seasonality_weight: float = 0.6
    elevation_weight: float = 0.4

    # Summit elevation is normalized into a 0..1 factor above this baseline.
    elevation_baseline_m: int = 1500
    elevation_normalization_span_m: int = 1700
    elevation_floor_score: float = 0.35
    elevation_variable_score: float = 0.65

    # Conditions score is derived from snow score with a mild positive offset.
    heuristic_conditions_weight: float = 0.9
    heuristic_conditions_offset: float = 0.05

    # Snapshot history should dominate when available,
    # but heuristics still stabilize it.
    snapshot_weight: float = 0.7
    heuristic_backstop_weight: float = 0.3

    # One monthly snapshot is useful but should be slightly discounted.
    single_snapshot_penalty: float = 0.04

    # Availability should be open once the conditions score clears this threshold.
    open_conditions_threshold: float = 0.5

    # Snow labels keep a simple poor/fair/good interpretation.
    poor_snow_threshold: float = 0.35
    fair_snow_threshold: float = 0.7


DEFAULT_PLANNING_HEURISTIC_POLICY = PlanningHeuristicPolicy()
