from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.domain.models import (
    PlanningEvidenceProfile,
    RawWeatherObservation,
    ResortConditions,
    ResortConditionSnapshot,
    SkiArea,
    WeatherElevationBand,
    WeatherEvidenceMetrics,
)
from app.domain.planning_policy import DEFAULT_PLANNING_HEURISTIC_POLICY
from app.integrations.open_meteo import normalize_weather_observation

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
DISPLAY_SNOW_DEPTH_MAX_M = 8.0


@dataclass(frozen=True)
class PlanningEvidenceWindow:
    year: int
    month: int
    observation_days: int
    average_snow_confidence_score: float
    average_conditions_score: float
    latest_observed_at: str


@dataclass(frozen=True)
class PlanningAssessment:
    conditions: ResortConditions
    planning_summary: str
    evidence_count: int
    best_travel_months: tuple[int, ...]
    latest_snapshot_at: str | None
    evidence_source: str
    evidence_profile: PlanningEvidenceProfile


def derive_weather_evidence_metrics(
    *,
    raw_weather_observations: tuple[RawWeatherObservation, ...],
    travel_month: int | None = None,
    trip_start_date: date | None = None,
    trip_end_date: date | None = None,
    elevation_band: WeatherElevationBand = "mid",
) -> WeatherEvidenceMetrics | None:
    if (trip_start_date is None) != (trip_end_date is None):
        raise ValueError("trip_start_date and trip_end_date must be provided together")
    if (
        trip_start_date is not None
        and trip_end_date is not None
        and trip_end_date < trip_start_date
    ):
        raise ValueError("trip_end_date must be on or after trip_start_date")
    if trip_start_date is None and travel_month is None:
        return None

    band_observations = tuple(
        observation
        for observation in raw_weather_observations
        if observation.elevation_band == elevation_band
    )
    observations = _archive_observations_for_window(
        raw_weather_observations=band_observations,
        travel_month=travel_month,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
    )
    if not observations:
        return None

    snow_depth_values = [
        observation.snow_depth_m * 100
        for observation in observations
        if observation.snow_depth_m is not None
        and observation.snow_depth_m <= DISPLAY_SNOW_DEPTH_MAX_M
    ]
    average_snow_depth_cm = (
        round(sum(snow_depth_values) / len(snow_depth_values), 1)
        if snow_depth_values
        else None
    )

    return WeatherEvidenceMetrics(
        average_snow_depth_cm=average_snow_depth_cm,
        average_daily_snowfall_cm=round(
            sum(observation.snowfall_cm for observation in observations)
            / len(observations),
            1,
        ),
        average_max_temperature_c=round(
            sum(observation.temperature_2m_max_c for observation in observations)
            / len(observations),
            1,
        ),
        average_wind_gust_kmh=round(
            sum(observation.wind_gusts_10m_max_kmh for observation in observations)
            / len(observations),
            1,
        ),
        evidence_years=len(
            {
                date.fromisoformat(observation.observed_on).year
                for observation in observations
            }
        ),
        latest_observed_on=max(observation.observed_on for observation in observations),
        elevation_band=elevation_band,
        elevation_m=_representative_elevation_m(observations),
    )


def _representative_elevation_m(
    observations: tuple[RawWeatherObservation, ...],
) -> int | None:
    values = sorted(
        {
            observation.elevation_m
            for observation in observations
            if observation.elevation_m is not None
        }
    )
    if not values:
        return None
    return values[len(values) // 2]


def _profile_text(
    evidence_profile: PlanningEvidenceProfile,
):
    return getattr(POLICY.text, evidence_profile)


def derive_planning_assessment(
    *,
    resort: SkiArea,
    travel_month: int | None = None,
    snapshots: tuple[ResortConditionSnapshot, ...],
    raw_weather_observations: tuple[RawWeatherObservation, ...] = (),
    current_conditions: ResortConditions | None = None,
    reference_date: datetime | None = None,
    trip_start_date: date | None = None,
    trip_end_date: date | None = None,
) -> PlanningAssessment:
    if trip_start_date is None and trip_end_date is None and travel_month is None:
        raise ValueError(
            "travel_month or trip_start_date/trip_end_date must be provided"
        )
    if (trip_start_date is None) != (trip_end_date is None):
        raise ValueError("trip_start_date and trip_end_date must be provided together")
    if (
        trip_start_date is not None
        and trip_end_date is not None
        and trip_end_date < trip_start_date
    ):
        raise ValueError("trip_end_date must be on or after trip_start_date")

    planning_month = travel_month
    if trip_start_date is not None:
        planning_month = trip_start_date.month

    values = _planning_values(
        resort=resort,
        travel_month=planning_month,
        snapshots=snapshots,
        raw_weather_observations=raw_weather_observations,
        current_conditions=current_conditions,
        reference_date=reference_date,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
    )
    planning_label = _planning_window_label(
        travel_month=planning_month,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
    )
    best_months = _best_travel_months(
        resort=resort,
        snapshots=snapshots,
        raw_weather_observations=raw_weather_observations,
        current_conditions=current_conditions,
        reference_date=reference_date,
    )
    snow_label = _snow_label(values.snow_score)
    profile_text = _profile_text(values.evidence_profile)

    if values.availability_status == "out_of_season":
        summary = POLICY.text.out_of_season_summary_template.format(
            planning_label=planning_label
        )
    elif values.evidence_profile == "forecast_assisted":
        summary = profile_text.planning_summary_template.format(
            snow_label=snow_label.capitalize(),
            planning_label=planning_label,
            evidence_count=values.evidence_count,
        )
    elif values.evidence_profile == "archive_backed":
        summary = profile_text.planning_summary_template.format(
            snow_label=snow_label.capitalize(),
            planning_label=planning_label,
            evidence_count=values.evidence_count,
        )
    elif values.evidence_count == 1:
        summary = POLICY.text.single_legacy_window_summary_template.format(
            snow_label=snow_label.capitalize(),
            planning_label=planning_label,
        )
    else:
        summary = profile_text.planning_summary_template.format(
            snow_label=snow_label.capitalize(),
            planning_label=planning_label,
            evidence_count=values.evidence_count,
        )

    return PlanningAssessment(
        conditions=ResortConditions(
            resort_name=resort.name,
            snow_confidence_score=values.snow_score,
            snow_confidence_label=snow_label,
            availability_status=values.availability_status,
            weather_summary=summary,
            conditions_score=values.conditions_score,
        ),
        planning_summary=summary,
        evidence_count=values.evidence_count,
        best_travel_months=best_months,
        latest_snapshot_at=values.latest_observed_at,
        evidence_source=values.evidence_source,
        evidence_profile=values.evidence_profile,
    )


@dataclass(frozen=True)
class _PlanningValues:
    snow_score: float
    conditions_score: float
    availability_status: str
    evidence_count: int
    latest_observed_at: str | None
    evidence_source: str
    evidence_profile: PlanningEvidenceProfile


def _planning_values(
    *,
    resort: SkiArea,
    travel_month: int | None,
    snapshots: tuple[ResortConditionSnapshot, ...],
    raw_weather_observations: tuple[RawWeatherObservation, ...],
    current_conditions: ResortConditions | None,
    reference_date: datetime | None,
    trip_start_date: date | None = None,
    trip_end_date: date | None = None,
) -> _PlanningValues:
    assert travel_month is not None
    if not _is_planning_window_in_season(
        resort=resort,
        travel_month=travel_month,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
    ):
        return _PlanningValues(
            snow_score=POLICY.out_of_season_snow_score,
            conditions_score=POLICY.out_of_season_conditions_score,
            availability_status="out_of_season",
            evidence_count=0,
            latest_observed_at=None,
            evidence_source="heuristic_only",
            evidence_profile="fallback_heavy",
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

    if raw_weather_observations:
        raw_values = _raw_planning_values(
            resort=resort,
            travel_month=travel_month,
            raw_weather_observations=raw_weather_observations,
            heuristic_snow=heuristic_snow,
            heuristic_conditions=heuristic_conditions,
            current_conditions=current_conditions,
            reference_date=reference_date,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
        )
        if raw_values is not None:
            return raw_values

    return _snapshot_planning_values(
        resort=resort,
        travel_month=travel_month,
        snapshots=snapshots,
        heuristic_snow=heuristic_snow,
        heuristic_conditions=heuristic_conditions,
    )


def _raw_planning_values(
    *,
    resort: SkiArea,
    travel_month: int,
    raw_weather_observations: tuple[RawWeatherObservation, ...],
    heuristic_snow: float,
    heuristic_conditions: float,
    current_conditions: ResortConditions | None,
    reference_date: datetime | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> _PlanningValues | None:
    windows = (
        _date_range_evidence_windows(
            resort=resort,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
            raw_weather_observations=raw_weather_observations,
        )
        if trip_start_date is not None and trip_end_date is not None
        else _planning_evidence_windows(
            resort=resort,
            travel_month=travel_month,
            raw_weather_observations=raw_weather_observations,
        )
    )
    if not windows:
        sparse_penalty = _sparse_evidence_penalty(
            resort=resort,
            travel_month=travel_month,
            evidence_count=0,
        )
        snow_score = round(max(heuristic_snow - sparse_penalty, 0.0), 2)
        conditions_score = round(max(heuristic_conditions - sparse_penalty, 0.0), 2)
        availability_status = (
            "open"
            if conditions_score >= POLICY.open_conditions_threshold
            else "limited"
        )
        return _PlanningValues(
            snow_score=snow_score,
            conditions_score=conditions_score,
            availability_status=availability_status,
            evidence_count=0,
            latest_observed_at=None,
            evidence_source="heuristic_only",
            evidence_profile="fallback_heavy",
        )

    average_snow = round(
        sum(window.average_snow_confidence_score for window in windows) / len(windows),
        2,
    )
    average_conditions = round(
        sum(window.average_conditions_score for window in windows) / len(windows),
        2,
    )
    current_weight = _current_signal_weight(
        travel_month=travel_month,
        reference_date=reference_date,
        trip_start_date=trip_start_date,
    )
    history_weight = round((1 - current_weight) * 0.7, 2)
    heuristic_weight = round(1 - current_weight - history_weight, 2)

    snow_score = round(
        average_snow * history_weight + heuristic_snow * heuristic_weight,
        2,
    )
    conditions_score = round(
        average_conditions * history_weight + heuristic_conditions * heuristic_weight,
        2,
    )

    if current_weight > 0 and current_conditions is not None:
        snow_score = round(
            snow_score + current_conditions.snow_confidence_score * current_weight,
            2,
        )
        conditions_score = round(
            conditions_score + current_conditions.conditions_score * current_weight,
            2,
        )

    sparse_penalty = _sparse_evidence_penalty(
        resort=resort,
        travel_month=travel_month,
        evidence_count=len(windows),
    )
    if len(windows) == 1:
        snow_score = round(max(snow_score - POLICY.single_snapshot_penalty, 0.0), 2)
        conditions_score = round(
            max(conditions_score - POLICY.single_snapshot_penalty, 0.0),
            2,
        )

    if sparse_penalty > 0:
        snow_score = round(max(snow_score - sparse_penalty, 0.0), 2)
        conditions_score = round(max(conditions_score - sparse_penalty, 0.0), 2)

    availability_status = (
        "open" if conditions_score >= POLICY.open_conditions_threshold else "limited"
    )
    return _PlanningValues(
        snow_score=snow_score,
        conditions_score=conditions_score,
        availability_status=availability_status,
        evidence_count=len(windows),
        latest_observed_at=max(window.latest_observed_at for window in windows),
        evidence_source="raw_history",
        evidence_profile=(
            "forecast_assisted"
            if current_weight > 0 and current_conditions is not None
            else "archive_backed"
        ),
    )


def _archive_observations_for_window(
    *,
    raw_weather_observations: tuple[RawWeatherObservation, ...],
    travel_month: int | None = None,
    trip_start_date: date | None = None,
    trip_end_date: date | None = None,
) -> tuple[RawWeatherObservation, ...]:
    if trip_start_date is not None and trip_end_date is not None:
        return tuple(
            observation
            for observation in raw_weather_observations
            if observation.record_type == "archive"
            and _matches_trip_window(
                observed_on=date.fromisoformat(observation.observed_on),
                trip_start_date=trip_start_date,
                trip_end_date=trip_end_date,
            )
        )

    assert travel_month is not None
    return tuple(
        observation
        for observation in raw_weather_observations
        if observation.record_type == "archive"
        and date.fromisoformat(observation.observed_on).month == travel_month
    )


def _planning_evidence_windows(
    *,
    resort: SkiArea,
    travel_month: int,
    raw_weather_observations: tuple[RawWeatherObservation, ...],
) -> tuple[PlanningEvidenceWindow, ...]:
    monthly_observations = _archive_observations_for_window(
        raw_weather_observations=raw_weather_observations,
        travel_month=travel_month,
    )
    if not monthly_observations:
        return ()

    observations_by_window: dict[tuple[int, int], list[RawWeatherObservation]] = {}
    for observation in monthly_observations:
        observed_at = datetime.fromisoformat(observation.observed_at)
        observations_by_window.setdefault(
            (observed_at.year, observed_at.month),
            [],
        ).append(observation)

    windows: list[PlanningEvidenceWindow] = []
    for (year, month), window_observations in sorted(observations_by_window.items()):
        daily_conditions = [
            normalize_weather_observation(resort, observation)
            for observation in window_observations
        ]
        windows.append(
            PlanningEvidenceWindow(
                year=year,
                month=month,
                observation_days=len(window_observations),
                average_snow_confidence_score=round(
                    sum(
                        condition.snow_confidence_score
                        for condition in daily_conditions
                    )
                    / len(daily_conditions),
                    2,
                ),
                average_conditions_score=round(
                    sum(condition.conditions_score for condition in daily_conditions)
                    / len(daily_conditions),
                    2,
                ),
                latest_observed_at=max(
                    observation.observed_at for observation in window_observations
                ),
            )
        )

    return tuple(windows)


def _date_range_evidence_windows(
    *,
    resort: SkiArea,
    trip_start_date: date,
    trip_end_date: date,
    raw_weather_observations: tuple[RawWeatherObservation, ...],
) -> tuple[PlanningEvidenceWindow, ...]:
    window_observations = _archive_observations_for_window(
        raw_weather_observations=raw_weather_observations,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
    )
    if not window_observations:
        return ()

    observations_by_year: dict[int, list[RawWeatherObservation]] = {}
    for observation in window_observations:
        observations_by_year.setdefault(
            date.fromisoformat(observation.observed_on).year,
            [],
        ).append(observation)

    windows: list[PlanningEvidenceWindow] = []
    for year, annual_observations in sorted(observations_by_year.items()):
        daily_conditions = [
            normalize_weather_observation(resort, observation)
            for observation in annual_observations
        ]
        windows.append(
            PlanningEvidenceWindow(
                year=year,
                month=trip_start_date.month,
                observation_days=len(annual_observations),
                average_snow_confidence_score=round(
                    sum(
                        condition.snow_confidence_score
                        for condition in daily_conditions
                    )
                    / len(daily_conditions),
                    2,
                ),
                average_conditions_score=round(
                    sum(condition.conditions_score for condition in daily_conditions)
                    / len(daily_conditions),
                    2,
                ),
                latest_observed_at=max(
                    observation.observed_at for observation in annual_observations
                ),
            )
        )

    return tuple(windows)


def _snapshot_planning_values(
    *,
    resort: SkiArea,
    travel_month: int,
    snapshots: tuple[ResortConditionSnapshot, ...],
    heuristic_snow: float,
    heuristic_conditions: float,
) -> _PlanningValues:
    monthly_snapshots = tuple(
        snapshot for snapshot in snapshots if snapshot.observed_month == travel_month
    )
    evidence_count = len(monthly_snapshots)
    sparse_penalty = _sparse_evidence_penalty(
        resort=resort,
        travel_month=travel_month,
        evidence_count=evidence_count,
    )
    if not monthly_snapshots:
        heuristic_snow = round(max(heuristic_snow - sparse_penalty, 0.0), 2)
        heuristic_conditions = round(max(heuristic_conditions - sparse_penalty, 0.0), 2)
        availability_status = (
            "open"
            if heuristic_conditions >= POLICY.open_conditions_threshold
            else "limited"
        )
        return _PlanningValues(
            snow_score=heuristic_snow,
            conditions_score=heuristic_conditions,
            availability_status=availability_status,
            evidence_count=0,
            latest_observed_at=None,
            evidence_source="heuristic_only",
            evidence_profile="fallback_heavy",
        )

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

    if sparse_penalty > 0:
        snow_score = round(max(snow_score - sparse_penalty, 0.0), 2)
        conditions_score = round(max(conditions_score - sparse_penalty, 0.0), 2)

    availability_status = (
        "open" if conditions_score >= POLICY.open_conditions_threshold else "limited"
    )
    return _PlanningValues(
        snow_score=snow_score,
        conditions_score=conditions_score,
        availability_status=availability_status,
        evidence_count=len(monthly_snapshots),
        latest_observed_at=_latest_snapshot_at(
            travel_month=travel_month,
            snapshots=snapshots,
        ),
        evidence_source="snapshot_history",
        evidence_profile="fallback_heavy",
    )


def _best_travel_months(
    *,
    resort: SkiArea,
    snapshots: tuple[ResortConditionSnapshot, ...],
    raw_weather_observations: tuple[RawWeatherObservation, ...],
    current_conditions: ResortConditions | None,
    reference_date: datetime | None,
) -> tuple[int, ...]:
    scored_months: list[tuple[int, float]] = []
    for month in range(1, 13):
        values = _planning_values(
            resort=resort,
            travel_month=month,
            snapshots=snapshots,
            raw_weather_observations=raw_weather_observations,
            current_conditions=current_conditions,
            reference_date=reference_date,
        )
        if values.availability_status == "out_of_season":
            continue
        scored_months.append((month, values.snow_score + values.conditions_score))

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


def _heuristic_snow_score(resort: SkiArea, travel_month: int) -> float:
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


def _sparse_evidence_penalty(
    *,
    resort: SkiArea,
    travel_month: int,
    evidence_count: int,
) -> float:
    if evidence_count >= 2:
        return 0.0

    penalty = 0.0
    if evidence_count == 1:
        penalty += POLICY.single_snapshot_scarcity_penalty
    else:
        penalty += POLICY.no_history_penalty

    if travel_month in POLICY.late_spring_months:
        penalty += POLICY.late_spring_edge_penalty
        if resort.base_elevation_m <= POLICY.late_spring_low_base_threshold_m:
            penalty += POLICY.late_spring_low_base_penalty
        if (
            resort.summit_elevation_m
            >= POLICY.late_spring_high_summit_relief_threshold_m
        ):
            penalty = max(penalty - POLICY.late_spring_high_summit_relief, 0.0)

    return round(penalty, 2)


def _current_signal_weight(
    *,
    travel_month: int,
    reference_date: datetime | None,
    trip_start_date: date | None = None,
) -> float:
    if reference_date is None:
        reference_date = datetime.now(UTC)
    window_policy = POLICY.forecast_window

    if trip_start_date is not None:
        days_until_start = (trip_start_date - reference_date.date()).days
        if days_until_start < 0:
            return 0.0
        if days_until_start <= window_policy.near_trip_days:
            return window_policy.near_trip_weight
        if days_until_start <= window_policy.medium_trip_days:
            return window_policy.medium_trip_weight
        return 0.0

    month_distance = (travel_month - reference_date.month) % 12
    if month_distance == 0:
        return window_policy.same_month_weight
    if month_distance == 1:
        return window_policy.next_month_weight
    return 0.0


def _planning_window_label(
    *,
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> str:
    if trip_start_date is not None and trip_end_date is not None:
        if trip_start_date == trip_end_date:
            return trip_start_date.strftime("%-d %b")
        return (
            f"{trip_start_date.strftime('%-d %b')}–{trip_end_date.strftime('%-d %b')}"
        )

    assert travel_month is not None
    return MONTH_NAMES[travel_month]


def _matches_trip_window(
    *,
    observed_on: date,
    trip_start_date: date,
    trip_end_date: date,
) -> bool:
    normalized_observed = date(2000, observed_on.month, observed_on.day)
    normalized_start = date(2000, trip_start_date.month, trip_start_date.day)
    normalized_end = date(2000, trip_end_date.month, trip_end_date.day)
    if normalized_start <= normalized_end:
        return normalized_start <= normalized_observed <= normalized_end
    return (
        normalized_observed >= normalized_start or normalized_observed <= normalized_end
    )


def _season_months(start_month: int, end_month: int) -> list[int]:
    months = [start_month]
    current = start_month
    while current != end_month:
        current = 1 if current == 12 else current + 1
        months.append(current)
    return months


def _snow_label(score: float) -> str:
    if score >= POLICY.fair_snow_threshold:
        return "good"
    if score >= POLICY.poor_snow_threshold:
        return "fair"
    return "poor"


def _is_month_in_season(month: int, start_month: int, end_month: int) -> bool:
    if start_month <= end_month:
        return start_month <= month <= end_month
    return month >= start_month or month <= end_month


def _is_planning_window_in_season(
    *,
    resort: SkiArea,
    travel_month: int,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> bool:
    if trip_start_date is not None and trip_end_date is not None:
        if any(
            trip_start_date >= window.start_date and trip_end_date <= window.end_date
            for window in resort.season_windows
        ):
            return True
        trip_season_year = _season_year_for_date(
            trip_start_date,
            resort.season_start_month,
        )
        if any(
            window.start_date.year == trip_season_year
            for window in resort.season_windows
        ):
            return False
    return _is_month_in_season(
        travel_month, resort.season_start_month, resort.season_end_month
    )


def _season_year_for_date(value: date, season_start_month: int) -> int:
    if value.month >= season_start_month:
        return value.year
    return value.year - 1
