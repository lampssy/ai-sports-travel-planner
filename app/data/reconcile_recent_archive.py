from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from app.data.backfill_historical_weather import (
    HistoricalBackfillResult,
    backfill_historical_weather,
)
from app.data.database import resolve_database_url

LOGGER = logging.getLogger(__name__)
DEFAULT_LOOKBACK_DAYS = 7


@dataclass(frozen=True)
class RecentArchiveReconciliationResult:
    start_date: date
    end_date: date
    backfill_result: HistoricalBackfillResult


def reconcile_recent_archive(
    *,
    database_url: str | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    end_date: date | None = None,
    targets: tuple[str, ...] | None = None,
) -> RecentArchiveReconciliationResult:
    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")

    reconciliation_end = end_date or (datetime.now(UTC).date() - timedelta(days=1))
    reconciliation_start = reconciliation_end - timedelta(days=lookback_days - 1)

    result = backfill_historical_weather(
        database_url=database_url or resolve_database_url(),
        start_date=reconciliation_start,
        end_date=reconciliation_end,
        targets=targets,
        chunk_days=lookback_days,
        force_refetch=True,
    )
    return RecentArchiveReconciliationResult(
        start_date=reconciliation_start,
        end_date=reconciliation_end,
        backfill_result=result,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile recent forecast rows with archive weather truth using a "
            "rolling historical backfill window."
        )
    )
    parser.add_argument(
        "--database-url",
        default=resolve_database_url(),
        help="Postgres connection string for the planner database.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help="Number of completed recent days to reconcile from the archive API.",
    )
    parser.add_argument(
        "--end-date",
        help=(
            "Inclusive ISO end date for the reconciliation window. Defaults to "
            "yesterday in UTC."
        ),
    )
    parser.add_argument(
        "--resort",
        action="append",
        default=[],
        help="Exact resort id or exact resort name to reconcile. Repeatable.",
    )
    args = parser.parse_args()

    if args.resort:
        LOGGER.info("Selected resorts: %s", ", ".join(args.resort))

    try:
        result = reconcile_recent_archive(
            database_url=args.database_url,
            lookback_days=args.lookback_days,
            end_date=date.fromisoformat(args.end_date) if args.end_date else None,
            targets=tuple(args.resort) or None,
        )
    except ValueError as error:
        LOGGER.error("%s", error)
        raise SystemExit(1) from error

    LOGGER.info(
        "Recent archive reconciliation complete: start_date=%s end_date=%s "
        "targeted_ski_areas=%s rows=%s failed_chunks=%s skipped_chunks=%s",
        result.start_date.isoformat(),
        result.end_date.isoformat(),
        result.backfill_result.targeted_ski_areas,
        result.backfill_result.inserted_or_updated,
        result.backfill_result.failed_chunks,
        result.backfill_result.skipped_chunks,
    )
    if result.backfill_result.failures:
        LOGGER.error(
            "Failed chunks: %s",
            ", ".join(
                (
                    f"{failure.resort_name} "
                    f"{failure.chunk_start}->{failure.chunk_end}: {failure.error}"
                )
                for failure in result.backfill_result.failures
            ),
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
