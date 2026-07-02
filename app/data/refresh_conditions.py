from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.data.catalog_loader import CATALOG_PATH
from app.data.catalog_repository import CatalogRepository, select_active_ski_areas
from app.data.database import bootstrap_database, resolve_database_url
from app.data.repositories import (
    RawWeatherHistoryRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    is_condition_fresh,
)
from app.domain.models import ResortConditionSnapshot
from app.integrations.open_meteo import (
    OpenMeteoClient,
    build_forecast_observation,
    normalize_open_meteo_conditions,
    weather_elevation_points,
)
from app.observability.cli import configure_cli_observability
from app.observability.jobs import job_span, record_conditions_refresh_result

RETRY_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.2


@dataclass
class RefreshFailure:
    resort_name: str
    error: str


@dataclass
class RefreshResult:
    refreshed: int = 0
    skipped_fresh: int = 0
    failed: int = 0
    failures: list[RefreshFailure] = field(default_factory=list)


def _log(message: str) -> None:
    print(message)


def refresh_conditions(
    *,
    database_url: str | None = None,
    client: OpenMeteoClient | None = None,
    now: datetime | None = None,
    force: bool = False,
    ski_area_ids: tuple[str, ...] = (),
    stay_destination_ids: tuple[str, ...] = (),
    retry_attempts: int = RETRY_ATTEMPTS,
    backoff_seconds: float = RETRY_BACKOFF_SECONDS,
) -> RefreshResult:
    weather_client = client or OpenMeteoClient()
    observed_at = now or datetime.now(UTC)
    effective_database_url = database_url or resolve_database_url()
    bootstrap_database(effective_database_url, catalog_path=CATALOG_PATH)
    conditions_repository = ResortConditionsRepository(effective_database_url)
    history_repository = ResortConditionHistoryRepository(effective_database_url)
    raw_history_repository = RawWeatherHistoryRepository(effective_database_url)
    result = RefreshResult()
    requested_ski_areas = select_active_ski_areas(
        CatalogRepository(effective_database_url).get_snapshot(),
        ski_area_ids=ski_area_ids,
        stay_destination_ids=stay_destination_ids,
    )

    for ski_area in requested_ski_areas:
        existing = conditions_repository.get_conditions_for_ski_area(
            ski_area.ski_area_id
        )
        if not force and existing and is_condition_fresh(existing, now=observed_at):
            result.skipped_fresh += 1
            record_conditions_refresh_result(
                source=existing.source or "open-meteo",
                status="success",
                updated_at=existing.updated_at,
                now=observed_at,
            )
            _log(f"[SKIP] {ski_area.name}: existing conditions are still fresh")
            continue

        _log(f"[REFRESH] {ski_area.name}: fetching Open-Meteo data")
        last_error: Exception | None = None
        for attempt in range(retry_attempts + 1):
            try:
                raw_observations = []
                mid_payload = None
                mid_point = None
                for elevation_point in weather_elevation_points(ski_area):
                    payload = weather_client.fetch_conditions(
                        ski_area,
                        elevation_m=elevation_point.elevation_m,
                    )
                    raw_observations.append(
                        build_forecast_observation(
                            ski_area,
                            payload,
                            observed_at=observed_at,
                            elevation_band=elevation_point.band,
                            elevation_m=elevation_point.elevation_m,
                        )
                    )
                    if elevation_point.band == "mid":
                        mid_payload = payload
                        mid_point = elevation_point

                assert mid_payload is not None
                assert mid_point is not None
                normalized = normalize_open_meteo_conditions(
                    ski_area,
                    mid_payload,
                    observed_at=observed_at,
                    elevation_band=mid_point.band,
                    elevation_m=mid_point.elevation_m,
                )
                conditions_repository.upsert_conditions(
                    entity_id=ski_area.ski_area_id,
                    entity_name=ski_area.name,
                    conditions=normalized,
                )
                for raw_observation in raw_observations:
                    raw_history_repository.upsert_observation(raw_observation)
                history_repository.append_snapshot(
                    snapshot=ResortConditionSnapshot(
                        ski_area_id=ski_area.ski_area_id,
                        resort_name=ski_area.name,
                        observed_month=observed_at.month,
                        observed_at=normalized.updated_at or observed_at.isoformat(),
                        snow_confidence_score=normalized.snow_confidence_score,
                        snow_confidence_label=normalized.snow_confidence_label,
                        availability_status=normalized.availability_status,
                        weather_summary=normalized.weather_summary,
                        conditions_score=normalized.conditions_score,
                        source=normalized.source,
                    )
                )
                result.refreshed += 1
                record_conditions_refresh_result(
                    source=normalized.source or "open-meteo",
                    status="success",
                    updated_at=normalized.updated_at,
                )
                _log(f"[DONE] {ski_area.name}: refreshed successfully")
                last_error = None
                break
            except Exception as error:  # pragma: no cover - exercised via tests
                last_error = error
                if attempt < retry_attempts:
                    _log(
                        "[RETRY] "
                        f"{ski_area.name}: attempt {attempt + 1} failed: {error}"
                    )
                    time.sleep(backoff_seconds)

        if last_error is not None:
            result.failed += 1
            record_conditions_refresh_result(
                source="open-meteo",
                status="failure",
                reason=last_error.__class__.__name__,
            )
            failure = RefreshFailure(resort_name=ski_area.name, error=str(last_error))
            result.failures.append(failure)
            _log(f"[FAIL] {ski_area.name}: {last_error}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh ski-area conditions from Open-Meteo into Postgres."
    )
    parser.add_argument(
        "--database-url",
        default=resolve_database_url(),
        help="Postgres connection string for the planner database.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass freshness checks and recompute selected rows.",
    )
    parser.add_argument(
        "--ski-area",
        action="append",
        default=[],
        help="Exact ski-area ID to refresh. Repeatable.",
    )
    parser.add_argument(
        "--stay-destination",
        action="append",
        default=[],
        help="Refresh every ski area reachable from this destination ID. Repeatable.",
    )
    args = parser.parse_args()

    if args.ski_area:
        print("Selected ski areas:", ", ".join(args.ski_area))
    if args.stay_destination:
        print("Selected stay destinations:", ", ".join(args.stay_destination))

    with configure_cli_observability(job_name="refresh_conditions"):
        try:
            with job_span("conditions_refresh"):
                result = refresh_conditions(
                    database_url=args.database_url,
                    force=args.force,
                    ski_area_ids=tuple(args.ski_area),
                    stay_destination_ids=tuple(args.stay_destination),
                )
        except ValueError as error:
            print(error)
            raise SystemExit(1) from error

    summary = (
        "Refreshed conditions:",
        f"refreshed={result.refreshed}",
        f"skipped_fresh={result.skipped_fresh}",
        f"failed={result.failed}",
    )
    print(*summary)
    if result.failures:
        print(
            "Failed resorts:",
            ", ".join(
                f"{failure.resort_name} ({failure.error})"
                for failure in result.failures
            ),
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
