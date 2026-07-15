from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from app.data.backfill_historical_weather import (
    HistoricalBackfillResult,
    backfill_historical_weather,
)
from app.data.catalog_loader import CATALOG_PATH
from app.data.catalog_repository import CatalogRepository, select_active_ski_areas
from app.data.database import bootstrap_database, resolve_database_url
from app.data.rebuild_snow_climatology import (
    DEFAULT_SOURCE_MODEL,
    SnowClimatologyRebuildResult,
    rebuild_snow_climatology,
)
from app.data.repositories import (
    ArchiveCoverageStats,
    ClimatologyCoverageStats,
    RawWeatherHistoryRepository,
    SnowClimatologyRepository,
)
from app.domain.models import (
    SnowClimatologyBaselinePeriod,
    WeatherElevationBand,
)
from app.observability.cli import configure_cli_observability
from app.observability.jobs import (
    job_span,
    record_historical_weather_completion_result,
)

DEFAULT_ARCHIVE_START_DATE = date(1991, 1, 1)
DEFAULT_ARCHIVE_END_DATE = date(2025, 12, 31)
DEFAULT_BASELINE_END_YEAR = 2025
DEFAULT_CHUNK_DAYS = 365
DEFAULT_MAX_PROVIDER_REQUESTS = 200
DEFAULT_RETRY_ATTEMPTS = 2
DEFAULT_BACKOFF_SECONDS = 30.0
DEFAULT_REQUEST_DELAY_SECONDS = 2.0
DEFAULT_REQUEST_JITTER_RATIO = 0.25
DEFAULT_RETRY_JITTER_RATIO = 0.25
DEFAULT_PROVIDER_PRESSURE_ERROR_THRESHOLD = 3
DEFAULT_PROVIDER_PRESSURE_COOLDOWN_SECONDS = 300.0
EXPECTED_CLIMATOLOGY_DAILY_ROWS = 366
ELEVATION_BANDS: tuple[WeatherElevationBand, ...] = ("base", "mid", "upper")
BASELINE_PERIODS: tuple[SnowClimatologyBaselinePeriod, ...] = (
    "normal_30y",
    "recent_15y",
)
EXPECTED_CLIMATOLOGY_ROWS_PER_SKI_AREA = (
    EXPECTED_CLIMATOLOGY_DAILY_ROWS * len(ELEVATION_BANDS) * len(BASELINE_PERIODS)
)

CompletionOutcome = Literal[
    "complete",
    "work_remaining",
    "throttled",
    "hard_failure",
]

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HistoricalWeatherCompletionResult:
    outcome: CompletionOutcome
    targeted_ski_areas: int
    archive_complete_ski_areas: int
    remaining_ski_areas: int
    climatology_current_ski_areas: int
    climatology_rebuilt_ski_areas: int
    hard_failures: int
    backfill_result: HistoricalBackfillResult
    climatology_result: SnowClimatologyRebuildResult


class HistoricalWeatherCompletionHardFailure(RuntimeError):
    def __init__(self, result: HistoricalWeatherCompletionResult) -> None:
        super().__init__("historical weather completion encountered hard failures")
        self.result = result


def complete_historical_weather(
    *,
    database_url: str | None = None,
    start_date: date = DEFAULT_ARCHIVE_START_DATE,
    end_date: date = DEFAULT_ARCHIVE_END_DATE,
    baseline_end_year: int = DEFAULT_BASELINE_END_YEAR,
    source_model: str = DEFAULT_SOURCE_MODEL,
    ski_area_ids: tuple[str, ...] = (),
    stay_destination_ids: tuple[str, ...] = (),
    chunk_days: int = DEFAULT_CHUNK_DAYS,
    max_provider_requests: int = DEFAULT_MAX_PROVIDER_REQUESTS,
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    request_jitter_ratio: float = DEFAULT_REQUEST_JITTER_RATIO,
    retry_jitter_ratio: float = DEFAULT_RETRY_JITTER_RATIO,
    provider_pressure_error_threshold: int = (
        DEFAULT_PROVIDER_PRESSURE_ERROR_THRESHOLD
    ),
    provider_pressure_cooldown_seconds: float = (
        DEFAULT_PROVIDER_PRESSURE_COOLDOWN_SECONDS
    ),
    logger: logging.Logger | None = None,
) -> HistoricalWeatherCompletionResult:
    if end_date != date(baseline_end_year, 12, 31):
        raise ValueError(
            "end_date must be December 31 of baseline_end_year for completion runs"
        )

    active_logger = logger or LOGGER
    effective_database_url = database_url or resolve_database_url()
    bootstrap_database(effective_database_url, catalog_path=CATALOG_PATH)
    selected_ski_areas = select_active_ski_areas(
        CatalogRepository(effective_database_url).get_snapshot(),
        ski_area_ids=ski_area_ids,
        stay_destination_ids=stay_destination_ids,
    )
    selected_ids = tuple(area.ski_area_id for area in selected_ski_areas)
    expected_days = (end_date - start_date).days + 1
    raw_repository = RawWeatherHistoryRepository(effective_database_url)
    initial_archive_coverage = raw_repository.list_archive_coverage(
        ski_area_ids=selected_ids,
        elevation_bands=ELEVATION_BANDS,
        start_date=start_date,
        end_date=end_date,
    )
    initially_complete_ids = set(
        _archive_complete_ski_area_ids(
            selected_ids=selected_ids,
            coverage=initial_archive_coverage,
            expected_days=expected_days,
        )
    )
    pending_ids = tuple(
        ski_area_id
        for ski_area_id in selected_ids
        if ski_area_id not in initially_complete_ids
    )

    backfill_result = HistoricalBackfillResult()
    if pending_ids:
        backfill_result = backfill_historical_weather(
            database_url=effective_database_url,
            start_date=start_date,
            end_date=end_date,
            ski_area_ids=pending_ids,
            chunk_days=chunk_days,
            logger=active_logger,
            retry_attempts=retry_attempts,
            backoff_seconds=backoff_seconds,
            request_delay_seconds=request_delay_seconds,
            request_jitter_ratio=request_jitter_ratio,
            retry_jitter_ratio=retry_jitter_ratio,
            provider_pressure_error_threshold=provider_pressure_error_threshold,
            provider_pressure_cooldown_seconds=(provider_pressure_cooldown_seconds),
            max_provider_requests=max_provider_requests,
            force_refetch=False,
            rebuild=False,
        )

    archive_coverage = initial_archive_coverage
    if pending_ids:
        archive_coverage = raw_repository.list_archive_coverage(
            ski_area_ids=selected_ids,
            elevation_bands=ELEVATION_BANDS,
            start_date=start_date,
            end_date=end_date,
        )
    archive_complete_ids = _archive_complete_ski_area_ids(
        selected_ids=selected_ids,
        coverage=archive_coverage,
        expected_days=expected_days,
    )

    climatology_coverage = SnowClimatologyRepository(
        effective_database_url
    ).list_climatology_coverage(
        ski_area_ids=archive_complete_ids,
        elevation_bands=ELEVATION_BANDS,
        baseline_periods=BASELINE_PERIODS,
        source_model=source_model,
    )
    stale_climatology_ids = _stale_climatology_ski_area_ids(
        archive_complete_ids=archive_complete_ids,
        coverage=climatology_coverage,
        baseline_end_year=baseline_end_year,
    )

    climatology_result = SnowClimatologyRebuildResult()
    if stale_climatology_ids:
        climatology_result = rebuild_snow_climatology(
            database_url=effective_database_url,
            ski_area_ids=stale_climatology_ids,
            baseline_end_year=baseline_end_year,
            source_model=source_model,
            expected_rows_per_ski_area=EXPECTED_CLIMATOLOGY_ROWS_PER_SKI_AREA,
            logger=active_logger,
        )

    hard_failures = sum(
        1 for failure in backfill_result.failures if not failure.is_rate_limited
    )
    remaining_ski_areas = len(selected_ids) - len(archive_complete_ids)
    outcome = _completion_outcome(
        hard_failures=hard_failures,
        rate_limited=backfill_result.rate_limited,
        remaining_ski_areas=remaining_ski_areas,
    )
    result = HistoricalWeatherCompletionResult(
        outcome=outcome,
        targeted_ski_areas=len(selected_ids),
        archive_complete_ski_areas=len(archive_complete_ids),
        remaining_ski_areas=remaining_ski_areas,
        climatology_current_ski_areas=len(archive_complete_ids),
        climatology_rebuilt_ski_areas=len(stale_climatology_ids),
        hard_failures=hard_failures,
        backfill_result=backfill_result,
        climatology_result=climatology_result,
    )
    active_logger.info(
        "[SUMMARY] outcome=%s targeted=%s archive_complete=%s remaining=%s "
        "provider_requests=%s climatology_rebuilt=%s hard_failures=%s",
        result.outcome,
        result.targeted_ski_areas,
        result.archive_complete_ski_areas,
        result.remaining_ski_areas,
        result.backfill_result.attempted_provider_requests,
        result.climatology_rebuilt_ski_areas,
        result.hard_failures,
    )
    return result


def _archive_complete_ski_area_ids(
    *,
    selected_ids: tuple[str, ...],
    coverage: dict[tuple[str, WeatherElevationBand], ArchiveCoverageStats],
    expected_days: int,
) -> tuple[str, ...]:
    return tuple(
        ski_area_id
        for ski_area_id in selected_ids
        if all(
            coverage[(ski_area_id, band)].covered_days == expected_days
            for band in ELEVATION_BANDS
        )
    )


def _stale_climatology_ski_area_ids(
    *,
    archive_complete_ids: tuple[str, ...],
    coverage: dict[
        tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod],
        ClimatologyCoverageStats,
    ],
    baseline_end_year: int,
) -> tuple[str, ...]:
    return tuple(
        ski_area_id
        for ski_area_id in archive_complete_ids
        if any(
            not _climatology_group_is_current(
                coverage[(ski_area_id, band, baseline_period)],
                baseline_end_year=baseline_end_year,
            )
            for band in ELEVATION_BANDS
            for baseline_period in BASELINE_PERIODS
        )
    )


def _climatology_group_is_current(
    stats: ClimatologyCoverageStats,
    *,
    baseline_end_year: int,
) -> bool:
    return (
        stats.row_count == EXPECTED_CLIMATOLOGY_DAILY_ROWS
        and stats.latest_archive_year == baseline_end_year
        and stats.baseline_end_year == baseline_end_year
    )


def _completion_outcome(
    *,
    hard_failures: int,
    rate_limited: bool,
    remaining_ski_areas: int,
) -> CompletionOutcome:
    if hard_failures:
        return "hard_failure"
    if rate_limited:
        return "throttled"
    if remaining_ski_areas:
        return "work_remaining"
    return "complete"


def _write_github_step_summary(
    result: HistoricalWeatherCompletionResult,
    *,
    summary_path: str | None,
) -> None:
    if not summary_path:
        return
    summary = (
        "## Historical weather completion\n\n"
        "| Metric | Value |\n"
        "| --- | ---: |\n"
        f"| Outcome | `{result.outcome}` |\n"
        f"| Targeted ski areas | {result.targeted_ski_areas} |\n"
        f"| Archive-complete ski areas | {result.archive_complete_ski_areas} |\n"
        f"| Remaining ski areas | {result.remaining_ski_areas} |\n"
        "| Provider requests attempted | "
        f"{result.backfill_result.attempted_provider_requests} |\n"
        f"| Archive chunks skipped | {result.backfill_result.skipped_chunks} |\n"
        f"| Archive rows written | {result.backfill_result.inserted_or_updated} |\n"
        "| Climatology ski areas rebuilt | "
        f"{result.climatology_rebuilt_ski_areas} |\n"
        f"| Hard failures | {result.hard_failures} |\n"
    )
    with Path(summary_path).open("a", encoding="utf-8") as output:
        output.write(summary)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    parser = argparse.ArgumentParser(
        description=(
            "Progressively complete the fixed Snowcast historical weather archive "
            "and rebuild eligible ski-area climatology."
        )
    )
    parser.add_argument("--database-url", default=resolve_database_url())
    parser.add_argument(
        "--start-date",
        default=DEFAULT_ARCHIVE_START_DATE.isoformat(),
    )
    parser.add_argument(
        "--end-date",
        default=DEFAULT_ARCHIVE_END_DATE.isoformat(),
    )
    parser.add_argument(
        "--baseline-end-year",
        type=int,
        default=DEFAULT_BASELINE_END_YEAR,
    )
    parser.add_argument("--source-model", default=DEFAULT_SOURCE_MODEL)
    parser.add_argument("--chunk-days", type=int, default=DEFAULT_CHUNK_DAYS)
    parser.add_argument(
        "--max-provider-requests",
        type=int,
        default=DEFAULT_MAX_PROVIDER_REQUESTS,
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
    )
    parser.add_argument(
        "--backoff-seconds",
        type=float,
        default=DEFAULT_BACKOFF_SECONDS,
    )
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SECONDS,
    )
    parser.add_argument(
        "--request-jitter-ratio",
        type=float,
        default=DEFAULT_REQUEST_JITTER_RATIO,
    )
    parser.add_argument(
        "--retry-jitter-ratio",
        type=float,
        default=DEFAULT_RETRY_JITTER_RATIO,
    )
    parser.add_argument(
        "--provider-pressure-error-threshold",
        type=int,
        default=DEFAULT_PROVIDER_PRESSURE_ERROR_THRESHOLD,
    )
    parser.add_argument(
        "--provider-pressure-cooldown-seconds",
        type=float,
        default=DEFAULT_PROVIDER_PRESSURE_COOLDOWN_SECONDS,
    )
    parser.add_argument("--ski-area", action="append", default=[])
    parser.add_argument("--stay-destination", action="append", default=[])
    args = parser.parse_args()

    try:
        with configure_cli_observability(job_name="complete_historical_weather"):
            with job_span("complete_historical_weather"):
                result = complete_historical_weather(
                    database_url=args.database_url,
                    start_date=date.fromisoformat(args.start_date),
                    end_date=date.fromisoformat(args.end_date),
                    baseline_end_year=args.baseline_end_year,
                    source_model=args.source_model,
                    ski_area_ids=tuple(args.ski_area),
                    stay_destination_ids=tuple(args.stay_destination),
                    chunk_days=args.chunk_days,
                    max_provider_requests=args.max_provider_requests,
                    retry_attempts=args.retry_attempts,
                    backoff_seconds=args.backoff_seconds,
                    request_delay_seconds=args.request_delay_seconds,
                    request_jitter_ratio=args.request_jitter_ratio,
                    retry_jitter_ratio=args.retry_jitter_ratio,
                    provider_pressure_error_threshold=(
                        args.provider_pressure_error_threshold
                    ),
                    provider_pressure_cooldown_seconds=(
                        args.provider_pressure_cooldown_seconds
                    ),
                )
                record_historical_weather_completion_result(
                    outcome=result.outcome,
                    targeted_ski_areas=result.targeted_ski_areas,
                    archive_complete_ski_areas=(result.archive_complete_ski_areas),
                    remaining_ski_areas=result.remaining_ski_areas,
                    attempted_provider_requests=(
                        result.backfill_result.attempted_provider_requests
                    ),
                    climatology_rebuilt_ski_areas=(
                        result.climatology_rebuilt_ski_areas
                    ),
                    hard_failures=result.hard_failures,
                )
                if result.outcome == "hard_failure":
                    raise HistoricalWeatherCompletionHardFailure(result)
    except HistoricalWeatherCompletionHardFailure as error:
        _write_github_step_summary(
            error.result,
            summary_path=os.getenv("GITHUB_STEP_SUMMARY"),
        )
        raise SystemExit(1) from error
    _write_github_step_summary(
        result,
        summary_path=os.getenv("GITHUB_STEP_SUMMARY"),
    )


if __name__ == "__main__":
    main()
