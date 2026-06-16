from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean

from app.data.database import bootstrap_database, resolve_database_url
from app.data.repositories import (
    RawWeatherHistoryRepository,
    ResortRepository,
    SnowClimatologyRepository,
)
from app.domain.models import (
    Destination,
    RawWeatherObservation,
    SkiArea,
    SnowClimatologyBaselinePeriod,
    SnowClimatologyDaily,
    WeatherElevationBand,
)
from app.integrations.open_meteo import normalize_weather_observation

LOGGER = logging.getLogger(__name__)
DEFAULT_SOURCE_MODEL = "snowcast_empirical_v1"
SNOW_DEPTH_DISPLAY_MAX_CM = 800.0
BASELINE_PERIODS: tuple[
    tuple[SnowClimatologyBaselinePeriod, int],
    ...,
] = (("normal_30y", 30), ("recent_15y", 15))


@dataclass(frozen=True)
class SnowClimatologyRebuildResult:
    targeted_ski_areas: int = 0
    raw_rows_read: int = 0
    climatology_rows_written: int = 0
    weak_coverage_groups: int = 0


def rebuild_snow_climatology(
    *,
    database_url: str | None = None,
    targets: tuple[str, ...] | None = None,
    baseline_end_year: int | None = None,
    source_model: str = DEFAULT_SOURCE_MODEL,
    logger: logging.Logger | None = None,
) -> SnowClimatologyRebuildResult:
    effective_database_url = database_url or resolve_database_url()
    bootstrap_database(effective_database_url)
    resort_repository = ResortRepository(effective_database_url)
    raw_repository = RawWeatherHistoryRepository(effective_database_url)
    climatology_repository = SnowClimatologyRepository(effective_database_url)
    selected_ski_areas = _select_ski_areas(targets, resort_repository.list_resorts())
    active_logger = logger or LOGGER

    result = SnowClimatologyRebuildResult(targeted_ski_areas=len(selected_ski_areas))
    active_logger.info(
        "[START] snow climatology rebuild: ski_areas=%s source_model=%s",
        result.targeted_ski_areas,
        source_model,
    )
    computed_at = datetime.now(UTC).isoformat()
    for _, ski_area in selected_ski_areas:
        observations = raw_repository.list_observations_for_resort(ski_area.ski_area_id)
        effective_end_year = baseline_end_year or _latest_archive_year(observations)
        rows = build_snow_climatology_rows(
            ski_area=ski_area,
            observations=observations,
            baseline_end_year=effective_end_year,
            computed_at=computed_at,
            source_model=source_model,
        )
        climatology_repository.delete_rows_for_ski_area(
            ski_area_id=ski_area.ski_area_id,
            source_model=source_model,
        )
        written_rows = climatology_repository.upsert_daily_rows(rows)
        result = SnowClimatologyRebuildResult(
            targeted_ski_areas=result.targeted_ski_areas,
            raw_rows_read=result.raw_rows_read + len(observations),
            climatology_rows_written=result.climatology_rows_written + written_rows,
            weak_coverage_groups=(
                result.weak_coverage_groups
                + sum(1 for row in rows if row.evidence_seasons < 8)
            ),
        )
        active_logger.info(
            "[DONE] %s: raw_rows=%s climatology_rows=%s",
            ski_area.name,
            len(observations),
            written_rows,
        )

    return result


def build_snow_climatology_rows(
    *,
    ski_area: SkiArea,
    observations: tuple[RawWeatherObservation, ...],
    baseline_end_year: int | None,
    computed_at: str,
    source_model: str = DEFAULT_SOURCE_MODEL,
) -> tuple[SnowClimatologyDaily, ...]:
    if baseline_end_year is None:
        return ()
    archive_observations = tuple(
        observation
        for observation in observations
        if observation.record_type == "archive"
    )
    rows: list[SnowClimatologyDaily] = []
    for baseline_period, years in BASELINE_PERIODS:
        baseline_start_year = baseline_end_year - years + 1
        period_observations = tuple(
            observation
            for observation in archive_observations
            if baseline_start_year
            <= datetime.fromisoformat(observation.observed_at).year
            <= baseline_end_year
        )
        rows.extend(
            _rows_for_baseline_period(
                ski_area=ski_area,
                observations=period_observations,
                baseline_period=baseline_period,
                baseline_start_year=baseline_start_year,
                baseline_end_year=baseline_end_year,
                computed_at=computed_at,
                source_model=source_model,
            )
        )
    return tuple(rows)


def _rows_for_baseline_period(
    *,
    ski_area: SkiArea,
    observations: tuple[RawWeatherObservation, ...],
    baseline_period: SnowClimatologyBaselinePeriod,
    baseline_start_year: int,
    baseline_end_year: int,
    computed_at: str,
    source_model: str,
) -> tuple[SnowClimatologyDaily, ...]:
    grouped: dict[
        tuple[WeatherElevationBand, int, int],
        list[RawWeatherObservation],
    ] = {}
    for observation in observations:
        observed_on = datetime.fromisoformat(observation.observed_at).date()
        grouped.setdefault(
            (observation.elevation_band, observed_on.month, observed_on.day),
            [],
        ).append(observation)

    rows: list[SnowClimatologyDaily] = []
    for (elevation_band, month, day), group in sorted(grouped.items()):
        evidence_years = {
            datetime.fromisoformat(observation.observed_at).year
            for observation in group
        }
        snow_depth_values = tuple(
            observation.snow_depth_m * 100
            for observation in group
            if observation.snow_depth_m is not None
            and observation.snow_depth_m * 100 <= SNOW_DEPTH_DISPLAY_MAX_CM
        )
        daily_conditions = [
            normalize_weather_observation(ski_area, observation)
            for observation in group
        ]
        rows.append(
            SnowClimatologyDaily(
                ski_area_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
                elevation_band=elevation_band,
                elevation_m=_representative_elevation_m(group),
                month=month,
                day=day,
                baseline_period=baseline_period,
                baseline_start_year=baseline_start_year,
                baseline_end_year=baseline_end_year,
                evidence_seasons=len(evidence_years),
                latest_archive_year=max(evidence_years) if evidence_years else None,
                snow_depth_cm_p25=_percentile(snow_depth_values, 0.25),
                snow_depth_cm_p50=_percentile(snow_depth_values, 0.5),
                snow_depth_cm_p75=_percentile(snow_depth_values, 0.75),
                prob_snow_depth_ge_30cm=_probability(
                    snow_depth_values,
                    lambda value: value >= 30,
                ),
                prob_snow_depth_ge_50cm=_probability(
                    snow_depth_values,
                    lambda value: value >= 50,
                ),
                avg_daily_snowfall_cm=round(
                    mean(observation.snowfall_cm for observation in group),
                    2,
                ),
                prob_rain_risk=_probability(
                    group,
                    lambda observation: (observation.rain_sum_mm or 0) > 0,
                ),
                prob_freeze_thaw=_probability(
                    group,
                    lambda observation: (
                        observation.temperature_2m_min_c < 0
                        and observation.temperature_2m_max_c > 0
                    ),
                ),
                avg_max_temperature_c=round(
                    mean(observation.temperature_2m_max_c for observation in group),
                    2,
                ),
                avg_wind_gust_kmh=round(
                    mean(observation.wind_gusts_10m_max_kmh for observation in group),
                    2,
                ),
                avg_snow_confidence_score=round(
                    mean(
                        condition.snow_confidence_score
                        for condition in daily_conditions
                    ),
                    2,
                ),
                avg_conditions_score=round(
                    mean(condition.conditions_score for condition in daily_conditions),
                    2,
                ),
                source_model=source_model,
                computed_at=computed_at,
            )
        )
    return tuple(rows)


def _latest_archive_year(
    observations: tuple[RawWeatherObservation, ...],
) -> int | None:
    years = [
        datetime.fromisoformat(observation.observed_at).year
        for observation in observations
        if observation.record_type == "archive"
    ]
    return max(years) if years else None


def _percentile(values: tuple[float, ...], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 1)
    position = (len(ordered) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index
    value = (
        ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction
    )
    return round(value, 1)


def _probability(
    values: Sequence[object],
    predicate: Callable[[object], bool],
) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if predicate(value)) / len(values), 4)


def _representative_elevation_m(
    observations: list[RawWeatherObservation],
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


def _select_ski_areas(
    targets: tuple[str, ...] | None,
    resorts: tuple[Destination, ...],
) -> tuple[tuple[Destination, SkiArea], ...]:
    pairs = tuple(
        (resort, ski_area) for resort in resorts for ski_area in resort.ski_areas
    )
    if not targets:
        return pairs

    normalized_targets = {target.strip().lower() for target in targets}
    return tuple(
        (resort, ski_area)
        for resort, ski_area in pairs
        if resort.resort_id.lower() in normalized_targets
        or ski_area.ski_area_id.lower() in normalized_targets
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild derived snow climatology from raw archive weather rows."
    )
    parser.add_argument(
        "--target",
        "--resort",
        dest="targets",
        action="append",
        default=None,
        help="Destination or ski-area id to rebuild. May be provided multiple times.",
    )
    parser.add_argument(
        "--baseline-end-year",
        type=int,
        default=None,
        help=(
            "Latest archive year to include. Defaults to latest available archive year."
        ),
    )
    parser.add_argument(
        "--source-model",
        default=DEFAULT_SOURCE_MODEL,
        help="Version label for the derived climatology rows.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL. Defaults to DATABASE_URL or local development settings.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = rebuild_snow_climatology(
        database_url=args.database_url,
        targets=tuple(args.targets) if args.targets else None,
        baseline_end_year=args.baseline_end_year,
        source_model=args.source_model,
    )
    LOGGER.info(
        "[SUMMARY] ski_areas=%s raw_rows=%s climatology_rows=%s weak_groups=%s",
        result.targeted_ski_areas,
        result.raw_rows_read,
        result.climatology_rows_written,
        result.weak_coverage_groups,
    )


if __name__ == "__main__":
    main()
