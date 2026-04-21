from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from datetime import date, timedelta

from app.data.database import bootstrap_database, resolve_database_url
from app.data.refresh_conditions import UnknownRefreshTargetError, _select_ski_areas
from app.data.repositories import RawWeatherHistoryRepository, ResortRepository
from app.integrations.open_meteo import OpenMeteoClient, build_historical_observations

RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 1.0


@dataclass(frozen=True)
class HistoricalBackfillFailure:
    resort_name: str
    chunk_start: str
    chunk_end: str
    error: str


@dataclass
class HistoricalBackfillResult:
    inserted_or_updated: int = 0
    requested_chunks: int = 0
    targeted_ski_areas: int = 0
    failed_chunks: int = 0
    skipped_chunks: int = 0
    failures: list[HistoricalBackfillFailure] = None

    def __post_init__(self) -> None:
        if self.failures is None:
            self.failures = []


LOGGER = logging.getLogger(__name__)


def _iter_date_chunks(
    *,
    start_date: date,
    end_date: date,
    chunk_days: int,
) -> tuple[tuple[date, date], ...]:
    chunks: list[tuple[date, date]] = []
    current_start = start_date
    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=chunk_days - 1), end_date)
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)
    return tuple(chunks)


def backfill_historical_weather(
    *,
    database_url: str | None = None,
    client: OpenMeteoClient | None = None,
    start_date: date,
    end_date: date,
    targets: tuple[str, ...] | None = None,
    chunk_days: int = 365,
    logger: logging.Logger | None = None,
    retry_attempts: int = RETRY_ATTEMPTS,
    backoff_seconds: float = RETRY_BACKOFF_SECONDS,
    force_refetch: bool = False,
) -> HistoricalBackfillResult:
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    if chunk_days <= 0:
        raise ValueError("chunk_days must be positive")
    if retry_attempts < 0:
        raise ValueError("retry_attempts must be non-negative")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds must be non-negative")

    effective_database_url = database_url or resolve_database_url()
    bootstrap_database(effective_database_url)
    weather_client = client or OpenMeteoClient()
    resort_repository = ResortRepository(effective_database_url)
    raw_history_repository = RawWeatherHistoryRepository(effective_database_url)
    selected_ski_areas = _select_ski_areas(targets, resort_repository.list_resorts())
    chunks = _iter_date_chunks(
        start_date=start_date,
        end_date=end_date,
        chunk_days=chunk_days,
    )
    active_logger = logger or LOGGER

    result = HistoricalBackfillResult(
        requested_chunks=len(chunks),
        targeted_ski_areas=len(selected_ski_areas),
    )
    active_logger.info(
        "[START] historical backfill: "
        f"ski_areas={result.targeted_ski_areas} "
        f"chunks_per_area={result.requested_chunks} "
        f"start_date={start_date.isoformat()} "
        f"end_date={end_date.isoformat()}"
    )

    for resort, ski_area in selected_ski_areas:
        active_logger.info("[AREA] %s: backfilling for %s", ski_area.name, resort.name)
        for chunk_index, (chunk_start, chunk_end) in enumerate(chunks, start=1):
            active_logger.info(
                "[CHUNK] %s: %s -> %s (%s/%s)",
                ski_area.name,
                chunk_start.isoformat(),
                chunk_end.isoformat(),
                chunk_index,
                len(chunks),
            )
            chunk_already_backfilled = (
                not force_refetch
                and raw_history_repository.has_complete_archive_coverage(
                    resort_id=ski_area.ski_area_id,
                    start_date=chunk_start,
                    end_date=chunk_end,
                )
            )
            if chunk_already_backfilled:
                result.skipped_chunks += 1
                active_logger.info(
                    "[SKIP] %s: %s -> %s already fully backfilled",
                    ski_area.name,
                    chunk_start.isoformat(),
                    chunk_end.isoformat(),
                )
                continue
            last_error: Exception | None = None
            for attempt in range(retry_attempts + 1):
                try:
                    payload = weather_client.fetch_historical_weather(
                        ski_area,
                        start_date=chunk_start,
                        end_date=chunk_end,
                    )
                    observations = build_historical_observations(ski_area, payload)
                    for observation in observations:
                        raw_history_repository.upsert_observation(observation)
                    result.inserted_or_updated += len(observations)
                    active_logger.info(
                        "[DONE] %s: stored %s daily rows for %s -> %s",
                        ski_area.name,
                        len(observations),
                        chunk_start.isoformat(),
                        chunk_end.isoformat(),
                    )
                    last_error = None
                    break
                except Exception as error:  # pragma: no cover - exercised via tests
                    last_error = error
                    if attempt < retry_attempts:
                        active_logger.warning(
                            "[RETRY] %s: %s -> %s attempt %s/%s failed: %s",
                            ski_area.name,
                            chunk_start.isoformat(),
                            chunk_end.isoformat(),
                            attempt + 1,
                            retry_attempts + 1,
                            error,
                        )
                        time.sleep(backoff_seconds)

            if last_error is not None:
                result.failed_chunks += 1
                result.failures.append(
                    HistoricalBackfillFailure(
                        resort_name=ski_area.name,
                        chunk_start=chunk_start.isoformat(),
                        chunk_end=chunk_end.isoformat(),
                        error=str(last_error),
                    )
                )
                active_logger.error(
                    "[FAIL] %s: %s -> %s failed after %s attempts: %s",
                    ski_area.name,
                    chunk_start.isoformat(),
                    chunk_end.isoformat(),
                    retry_attempts + 1,
                    last_error,
                )

    return result


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )
    parser = argparse.ArgumentParser(
        description=(
            "Backfill raw daily weather history from Open-Meteo into the planner "
            "database."
        )
    )
    parser.add_argument(
        "--database-url",
        default=resolve_database_url(),
        help="Postgres connection string for the planner database.",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Inclusive ISO start date, for example 2021-01-01.",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="Inclusive ISO end date, for example 2026-01-01.",
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=365,
        help="Maximum date-range size per provider request.",
    )
    parser.add_argument(
        "--resort",
        action="append",
        default=[],
        help=(
            "Exact ski-area id, ski-area name, resort id, or resort name to backfill. "
            "Repeatable."
        ),
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=RETRY_ATTEMPTS,
        help="Number of retry attempts for each failed provider request.",
    )
    parser.add_argument(
        "--backoff-seconds",
        type=float,
        default=RETRY_BACKOFF_SECONDS,
        help="Seconds to wait between retries for failed provider requests.",
    )
    parser.add_argument(
        "--force-refetch",
        action="store_true",
        help=(
            "Fetch every chunk even if archive rows for the full date range "
            "already exist."
        ),
    )
    args = parser.parse_args()

    if args.resort:
        LOGGER.info("Selected resorts: %s", ", ".join(args.resort))

    try:
        result = backfill_historical_weather(
            database_url=args.database_url,
            start_date=date.fromisoformat(args.start_date),
            end_date=date.fromisoformat(args.end_date),
            targets=tuple(args.resort) or None,
            chunk_days=args.chunk_days,
            logger=LOGGER,
            retry_attempts=args.retry_attempts,
            backoff_seconds=args.backoff_seconds,
            force_refetch=args.force_refetch,
        )
    except (UnknownRefreshTargetError, ValueError) as error:
        LOGGER.error("%s", error)
        raise SystemExit(1) from error

    LOGGER.info(
        "Historical backfill complete: targeted_ski_areas=%s requested_chunks=%s "
        "rows=%s failed_chunks=%s skipped_chunks=%s",
        result.targeted_ski_areas,
        result.requested_chunks,
        result.inserted_or_updated,
        result.failed_chunks,
        result.skipped_chunks,
    )
    if result.failures:
        LOGGER.error(
            "Failed chunks: %s",
            ", ".join(
                (
                    f"{failure.resort_name} "
                    f"({failure.chunk_start} -> {failure.chunk_end}: {failure.error})"
                )
                for failure in result.failures
            ),
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
