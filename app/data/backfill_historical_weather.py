from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from app.data.database import bootstrap_database, resolve_database_url
from app.data.refresh_conditions import UnknownRefreshTargetError, _select_ski_areas
from app.data.repositories import RawWeatherHistoryRepository, ResortRepository
from app.integrations.open_meteo import OpenMeteoClient, build_historical_observations


@dataclass
class HistoricalBackfillResult:
    inserted_or_updated: int = 0
    requested_chunks: int = 0
    targeted_ski_areas: int = 0


def _log(message: str) -> None:
    print(message)


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
    database_url: str | os.PathLike[str] | None = None,
    client: OpenMeteoClient | None = None,
    start_date: date,
    end_date: date,
    targets: tuple[str, ...] | None = None,
    chunk_days: int = 365,
    logger: Callable[[str], None] | None = None,
) -> HistoricalBackfillResult:
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    if chunk_days <= 0:
        raise ValueError("chunk_days must be positive")

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
    emit = logger or (lambda message: None)

    result = HistoricalBackfillResult(
        requested_chunks=len(chunks),
        targeted_ski_areas=len(selected_ski_areas),
    )
    emit(
        "[START] historical backfill: "
        f"ski_areas={result.targeted_ski_areas} "
        f"chunks_per_area={result.requested_chunks} "
        f"start_date={start_date.isoformat()} "
        f"end_date={end_date.isoformat()}"
    )

    for resort, ski_area in selected_ski_areas:
        emit(f"[AREA] {ski_area.name}: backfilling for {resort.name}")
        for chunk_index, (chunk_start, chunk_end) in enumerate(chunks, start=1):
            emit(
                "[CHUNK] "
                f"{ski_area.name}: "
                f"{chunk_start.isoformat()} -> {chunk_end.isoformat()} "
                f"({chunk_index}/{len(chunks)})"
            )
            payload = weather_client.fetch_historical_weather(
                ski_area,
                start_date=chunk_start,
                end_date=chunk_end,
            )
            observations = build_historical_observations(ski_area, payload)
            for observation in observations:
                raw_history_repository.upsert_observation(observation)
            result.inserted_or_updated += len(observations)
            emit(
                "[DONE] "
                f"{ski_area.name}: stored {len(observations)} daily rows for "
                f"{chunk_start.isoformat()} -> {chunk_end.isoformat()}"
            )

    return result


def main() -> None:
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
    args = parser.parse_args()

    if args.resort:
        print("Selected resorts:", ", ".join(args.resort))

    try:
        result = backfill_historical_weather(
            database_url=args.database_url,
            start_date=date.fromisoformat(args.start_date),
            end_date=date.fromisoformat(args.end_date),
            targets=tuple(args.resort) or None,
            chunk_days=args.chunk_days,
            logger=_log,
        )
    except (UnknownRefreshTargetError, ValueError) as error:
        print(error)
        raise SystemExit(1) from error

    print(
        "Historical backfill complete:",
        f"targeted_ski_areas={result.targeted_ski_areas}",
        f"requested_chunks={result.requested_chunks}",
        f"rows={result.inserted_or_updated}",
    )


if __name__ == "__main__":
    main()
