from __future__ import annotations

import argparse
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.data.catalog_loader import CATALOG_PATH
from app.data.catalog_repository import CatalogRepository, select_active_ski_areas
from app.data.database import bootstrap_database, resolve_database_url
from app.data.weather_forecast_repository import WeatherForecastRepository
from app.domain.weather_forecast import WeatherForecastDaily, WeatherForecastRun
from app.integrations.open_meteo import weather_elevation_point
from app.integrations.open_meteo_forecast import (
    FORECAST_SOURCES,
    ForecastProviderError,
    ForecastRequestPoint,
    ModelCycleChangedError,
    ModelCycleMetadata,
    OpenMeteoEnsembleMeanClient,
    assert_same_model_cycle,
    normalize_daily_forecast,
)
from app.observability.cli import configure_cli_observability
from app.observability.jobs import (
    job_span,
    record_weather_forecast_refresh_result,
)

PROVIDER_CONSISTENCY_DELAY = timedelta(minutes=10)
DEFAULT_BATCH_SIZE = 20


class ForecastRefreshRepository(Protocol):
    def find_complete_run_id(
        self,
        source_key: str,
        model_initialization_time: datetime,
        ski_area_ids: Sequence[str],
    ) -> str | None: ...

    def create_building_run(self, run: WeatherForecastRun) -> None: ...

    def insert_daily_rows(
        self,
        run_id: str,
        rows: Sequence[WeatherForecastDaily],
    ) -> None: ...

    def complete_run_and_advance_heads(
        self,
        run_id: str,
        *,
        publishable_ski_area_ids: Sequence[str],
        completed_at: datetime,
    ) -> None: ...

    def reject_or_fail_run(
        self,
        run_id: str,
        *,
        status: str,
        reason: str,
        completed_at: datetime,
    ) -> None: ...


class ForecastRefreshClient(Protocol):
    def fetch_model_cycle(self, source_key: str) -> ModelCycleMetadata: ...

    def fetch_hourly(
        self,
        source_key: str,
        points: Sequence[ForecastRequestPoint],
    ) -> tuple[dict[str, object], ...]: ...


@dataclass(frozen=True)
class ForecastRefreshResult:
    run_id: str
    source_key: str
    status: str
    published_ski_area_ids: tuple[str, ...]
    failed_ski_area_ids: tuple[str, ...]
    daily_row_count: int


def refresh_forecast_source(
    *,
    source_key: str,
    points: Sequence[ForecastRequestPoint],
    repository: ForecastRefreshRepository,
    client: ForecastRefreshClient,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
    run_id_factory: Callable[[], str] = lambda: str(uuid4()),
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> ForecastRefreshResult:
    try:
        source = FORECAST_SOURCES[source_key]
    except KeyError as error:
        raise ValueError(f"unknown forecast source: {source_key}") from error
    if not points:
        raise ValueError("forecast refresh needs at least one request point")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    first_cycle = client.fetch_model_cycle(source_key)
    existing_run_id = repository.find_complete_run_id(
        source_key,
        first_cycle.initialization_time,
        tuple(sorted({point.ski_area_id for point in points})),
    )
    if existing_run_id is not None:
        return ForecastRefreshResult(
            run_id=existing_run_id,
            source_key=source_key,
            status="unchanged",
            published_ski_area_ids=(),
            failed_ski_area_ids=(),
            daily_row_count=0,
        )
    ready_at = first_cycle.availability_time + PROVIDER_CONSISTENCY_DELAY
    now = _aware_now(clock)
    if now < ready_at:
        sleep((ready_at - now).total_seconds())
    ingested_at = _aware_now(clock)
    run_id = run_id_factory()
    if not run_id.strip():
        raise ValueError("forecast run ID must not be blank")
    first_valid_date = first_cycle.initialization_time.astimezone(UTC).date()
    run = WeatherForecastRun(
        forecast_run_id=run_id,
        forecast_source_key=source_key,
        provider_gateway="open-meteo",
        producer=source.producer,
        provider_model_id=source.provider_model_id,
        forecast_kind="ensemble_mean",
        model_initialization_time=first_cycle.initialization_time,
        provider_availability_time=first_cycle.availability_time,
        ingested_at=ingested_at,
        first_valid_date=first_valid_date,
        last_valid_date=first_valid_date + timedelta(days=source.maximum_lead_days),
        status="building",
        schema_version="forecast-v1",
        parser_version="open-meteo-ensemble-mean-v1",
        aggregation_policy_version="local-day-v1",
        provider_metadata={
            **dict(first_cycle.raw_metadata),
            "provider_model_parameter": source.provider_model_parameter,
            "batch_size": batch_size,
        },
    )
    repository.create_building_run(run)

    successful_area_ids: set[str] = set()
    failed_area_ids: set[str] = set()
    daily_row_count = 0
    try:
        for offset in range(0, len(points), batch_size):
            batch = tuple(points[offset : offset + batch_size])
            try:
                payloads = client.fetch_hourly(source_key, batch)
            except Exception:
                failed_area_ids.update(point.ski_area_id for point in batch)
                continue
            for point, payload in zip(batch, payloads, strict=True):
                try:
                    rows = normalize_daily_forecast(
                        run_id=run_id,
                        source_key=source_key,
                        point=point,
                        payload=payload,
                    )
                    eligible_rows = tuple(
                        row
                        for row in rows
                        if _lead_days(row, first_cycle) <= source.maximum_lead_days
                        and _lead_days(row, first_cycle) >= 0
                    )
                except (ForecastProviderError, ValueError):
                    failed_area_ids.add(point.ski_area_id)
                    continue
                if not eligible_rows:
                    failed_area_ids.add(point.ski_area_id)
                    continue
                repository.insert_daily_rows(run_id, eligible_rows)
                daily_row_count += len(eligible_rows)
                successful_area_ids.add(point.ski_area_id)

        second_cycle = client.fetch_model_cycle(source_key)
        assert_same_model_cycle(first_cycle, second_cycle)
    except ModelCycleChangedError as error:
        completed_at = _aware_now(clock)
        repository.reject_or_fail_run(
            run_id,
            status="rejected",
            reason=str(error),
            completed_at=completed_at,
        )
        return ForecastRefreshResult(
            run_id=run_id,
            source_key=source_key,
            status="rejected",
            published_ski_area_ids=(),
            failed_ski_area_ids=tuple(sorted({point.ski_area_id for point in points})),
            daily_row_count=daily_row_count,
        )
    except Exception as error:
        repository.reject_or_fail_run(
            run_id,
            status="failed",
            reason=error.__class__.__name__,
            completed_at=_aware_now(clock),
        )
        return ForecastRefreshResult(
            run_id=run_id,
            source_key=source_key,
            status="failed",
            published_ski_area_ids=(),
            failed_ski_area_ids=tuple(sorted({point.ski_area_id for point in points})),
            daily_row_count=daily_row_count,
        )

    published_ids = tuple(sorted(successful_area_ids))
    if not published_ids:
        repository.reject_or_fail_run(
            run_id,
            status="failed",
            reason="no_complete_ski_area_forecasts",
            completed_at=_aware_now(clock),
        )
        return ForecastRefreshResult(
            run_id=run_id,
            source_key=source_key,
            status="failed",
            published_ski_area_ids=(),
            failed_ski_area_ids=tuple(sorted(failed_area_ids)),
            daily_row_count=0,
        )

    repository.complete_run_and_advance_heads(
        run_id,
        publishable_ski_area_ids=published_ids,
        completed_at=_aware_now(clock),
    )
    return ForecastRefreshResult(
        run_id=run_id,
        source_key=source_key,
        status="complete",
        published_ski_area_ids=published_ids,
        failed_ski_area_ids=tuple(sorted(failed_area_ids - successful_area_ids)),
        daily_row_count=daily_row_count,
    )


def _lead_days(
    row: WeatherForecastDaily,
    cycle: ModelCycleMetadata,
) -> int:
    initialization_date = cycle.initialization_time.astimezone(
        ZoneInfo(row.provider_timezone)
    ).date()
    return (row.valid_local_date - initialization_date).days


def _aware_now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("forecast refresh clock must be timezone-aware")
    return value


def _request_points(
    database_url: str, ski_area_ids: tuple[str, ...]
) -> tuple[ForecastRequestPoint, ...]:
    snapshot = CatalogRepository(database_url).get_snapshot()
    areas = select_active_ski_areas(snapshot, ski_area_ids=ski_area_ids)
    return tuple(
        ForecastRequestPoint(
            ski_area_id=area.ski_area_id,
            latitude=area.latitude,
            longitude=area.longitude,
            elevation_m=weather_elevation_point(area, "mid").elevation_m,
        )
        for area in areas
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh versioned ski-area ensemble forecasts."
    )
    parser.add_argument(
        "--database-url",
        default=resolve_database_url(),
        help="Postgres connection string for the planner database.",
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=sorted(FORECAST_SOURCES),
        help="Forecast source key to refresh. Repeatable; defaults to both.",
    )
    parser.add_argument(
        "--ski-area",
        action="append",
        default=[],
        help="Exact ski-area ID to refresh. Repeatable.",
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    bootstrap_database(args.database_url, catalog_path=CATALOG_PATH)
    points = _request_points(args.database_url, tuple(args.ski_area))
    repository = WeatherForecastRepository(args.database_url)
    source_keys = tuple(args.source or sorted(FORECAST_SOURCES))
    failed = False
    with configure_cli_observability(job_name="refresh_weather_forecasts"):
        with job_span("weather_forecast_refresh"):
            with OpenMeteoEnsembleMeanClient() as client:
                for source_key in source_keys:
                    result = refresh_forecast_source(
                        source_key=source_key,
                        points=points,
                        repository=repository,
                        client=client,
                        batch_size=args.batch_size,
                    )
                    run = repository.get_run(result.run_id)
                    now = datetime.now(UTC)
                    head_age = (
                        (now - run.provider_availability_time).total_seconds()
                        if run is not None
                        else None
                    )
                    valid_dates = (
                        (run.last_valid_date - run.first_valid_date).days + 1
                        if run is not None
                        else None
                    )
                    record_weather_forecast_refresh_result(
                        source_key=source_key,
                        status=result.status,
                        published_ski_areas=len(result.published_ski_area_ids),
                        incomplete_ski_areas=len(result.failed_ski_area_ids),
                        daily_rows=result.daily_row_count,
                        head_age_seconds=head_age,
                        valid_date_count=valid_dates,
                    )
                    print(
                        source_key,
                        f"status={result.status}",
                        f"areas={len(result.published_ski_area_ids)}",
                        f"failed_areas={len(result.failed_ski_area_ids)}",
                        f"daily_rows={result.daily_row_count}",
                    )
                    failed = failed or result.status not in {
                        "complete",
                        "unchanged",
                    }
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
