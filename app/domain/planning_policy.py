from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import PlanningEvidenceProfile

PLANNING_HEURISTIC_VERSION = "v2"


@dataclass(frozen=True)
class ForecastWindowPolicy:
    near_trip_days: int = 14
    medium_trip_days: int = 30
    near_trip_weight: float = 0.35
    medium_trip_weight: float = 0.15
    same_month_weight: float = 0.2
    next_month_weight: float = 0.08


@dataclass(frozen=True)
class PlanningEvidenceProfileText:
    profile: PlanningEvidenceProfile
    source_name: str
    planning_summary_template: str
    provenance_summary: str


@dataclass(frozen=True)
class PlanningTextPolicy:
    forecast_assisted: PlanningEvidenceProfileText = PlanningEvidenceProfileText(
        profile="forecast_assisted",
        source_name="archive_history+forecast+seasonality",
        planning_summary_template=(
            "{snow_label} fit for {planning_label}, backed by "
            "{evidence_count} archive weather windows with current forecast "
            "assistance."
        ),
        provenance_summary=(
            "Using archive weather history together with current forecast "
            "signal because the requested trip window is close."
        ),
    )
    archive_backed: PlanningEvidenceProfileText = PlanningEvidenceProfileText(
        profile="archive_backed",
        source_name="archive_history+seasonality",
        planning_summary_template=(
            "{snow_label} fit for {planning_label}, backed by "
            "{evidence_count} archive weather windows."
        ),
        provenance_summary=(
            "Using stored archive weather history together with seasonal patterns."
        ),
    )
    fallback_heavy: PlanningEvidenceProfileText = PlanningEvidenceProfileText(
        profile="fallback_heavy",
        source_name="seasonality_fallback",
        planning_summary_template=(
            "{snow_label} fit for {planning_label}, based mostly on seasonal "
            "patterns. Historical weather data is limited."
        ),
        provenance_summary=(
            "Using seasonal patterns and elevation because historical weather "
            "data is limited."
        ),
    )
    snapshot_fallback_source_name: str = "snapshot_history+seasonality"
    snapshot_fallback_provenance_summary: str = (
        "Using legacy snapshot history together with seasonal patterns "
        "because archive evidence is limited."
    )
    out_of_season_summary_template: str = (
        "{planning_label} sits outside the typical ski season window for this resort."
    )
    single_legacy_window_summary_template: str = (
        "{snow_label} fit for {planning_label}, with only one legacy evidence window."
    )


@dataclass(frozen=True)
class PlanningHeuristicPolicy:
    # Out-of-season months should remain valid numeric results, but clearly weak.
    out_of_season_snow_score: float = 0.18
    out_of_season_conditions_score: float = 0.08

    # Mid-season months should score strongest,
    # shoulder months next, edge months weakest.
    seasonality_core_month_score: float = 0.92
    seasonality_shoulder_month_score: float = 0.74
    seasonality_edge_month_score: float = 0.48

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
    single_snapshot_penalty: float = 0.06
    no_history_penalty: float = 0.06
    single_snapshot_scarcity_penalty: float = 0.03

    # Late-spring closing months need extra caution when the product lacks evidence.
    late_spring_months: tuple[int, ...] = (5,)
    late_spring_edge_penalty: float = 0.18
    late_spring_low_base_threshold_m: int = 1500
    late_spring_low_base_penalty: float = 0.08
    late_spring_high_summit_relief_threshold_m: int = 3400
    late_spring_high_summit_relief: float = 0.06

    # Disruption compatibility status is "open" once conditions clear this threshold.
    open_conditions_threshold: float = 0.5

    # Snow labels keep a simple poor/fair/good interpretation.
    poor_snow_threshold: float = 0.35
    fair_snow_threshold: float = 0.7

    # Forecast weighting becomes material only for near trip windows.
    forecast_window: ForecastWindowPolicy = ForecastWindowPolicy()

    # User-facing summary and provenance wording for planning evidence profiles.
    text: PlanningTextPolicy = PlanningTextPolicy()


DEFAULT_PLANNING_HEURISTIC_POLICY = PlanningHeuristicPolicy()
