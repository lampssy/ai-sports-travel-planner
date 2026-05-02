from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.data.database import resolve_database_url
from app.data.repositories import (
    RawWeatherHistoryRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    ResortRepository,
    is_condition_fresh,
)
from app.domain.models import ResortConditionSnapshot
from app.integrations.open_meteo import (
    OpenMeteoClient,
    build_forecast_observation,
    normalize_open_meteo_conditions,
    weather_elevation_points,
)

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


class UnknownRefreshTargetError(ValueError):
    def __init__(self, targets: tuple[str, ...]) -> None:
        self.targets = targets
        joined = ", ".join(targets)
        super().__init__(f"Unknown resort target(s): {joined}")


def _log(message: str) -> None:
    print(message)


def _select_ski_areas(
    requested_targets: tuple[str, ...] | None,
    available_resorts: tuple,
) -> tuple:
    available_ski_areas = tuple(
        (resort, ski_area)
        for resort in available_resorts
        for ski_area in resort.ski_areas
    )
    if not requested_targets:
        return available_ski_areas

    resorts_by_id = {resort.resort_id: resort for resort in available_resorts}
    resorts_by_name = {resort.name: resort for resort in available_resorts}
    ski_areas_by_id = {
        ski_area.ski_area_id: (resort, ski_area)
        for resort, ski_area in available_ski_areas
    }
    ski_areas_by_name = {
        ski_area.name: (resort, ski_area) for resort, ski_area in available_ski_areas
    }
    selected_ski_areas = []
    missing_targets: list[str] = []

    for target in requested_targets:
        selected = ski_areas_by_id.get(target) or ski_areas_by_name.get(target)
        if selected is not None:
            if selected not in selected_ski_areas:
                selected_ski_areas.append(selected)
            continue

        resort = resorts_by_id.get(target) or resorts_by_name.get(target)
        if resort is not None:
            for ski_area in resort.ski_areas:
                pair = (resort, ski_area)
                if pair not in selected_ski_areas:
                    selected_ski_areas.append(pair)
            continue

        missing_targets.append(target)

    if missing_targets:
        raise UnknownRefreshTargetError(tuple(missing_targets))

    return tuple(selected_ski_areas)


def refresh_conditions(
    *,
    database_url: str | None = None,
    client: OpenMeteoClient | None = None,
    now: datetime | None = None,
    force: bool = False,
    targets: tuple[str, ...] | None = None,
    retry_attempts: int = RETRY_ATTEMPTS,
    backoff_seconds: float = RETRY_BACKOFF_SECONDS,
) -> RefreshResult:
    weather_client = client or OpenMeteoClient()
    observed_at = now or datetime.now(UTC)
    effective_database_url = database_url or resolve_database_url()
    resort_repository = ResortRepository(effective_database_url)
    conditions_repository = ResortConditionsRepository(effective_database_url)
    history_repository = ResortConditionHistoryRepository(effective_database_url)
    raw_history_repository = RawWeatherHistoryRepository(effective_database_url)
    result = RefreshResult()
    requested_ski_areas = _select_ski_areas(targets, resort_repository.list_resorts())

    for resort, ski_area in requested_ski_areas:
        existing = conditions_repository.get_conditions_for_ski_area(ski_area.name)
        if not force and existing and is_condition_fresh(existing, now=observed_at):
            result.skipped_fresh += 1
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
                        resort_id=ski_area.ski_area_id,
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
            failure = RefreshFailure(resort_name=ski_area.name, error=str(last_error))
            result.failures.append(failure)
            _log(f"[FAIL] {ski_area.name}: {last_error}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh real resort conditions from Open-Meteo into Postgres."
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
        "--resort",
        action="append",
        default=[],
        help="Exact resort id or exact resort name to refresh. Repeatable.",
    )
    args = parser.parse_args()

    if args.resort:
        print("Selected resorts:", ", ".join(args.resort))

    try:
        result = refresh_conditions(
            database_url=args.database_url,
            force=args.force,
            targets=tuple(args.resort) or None,
        )
    except UnknownRefreshTargetError as error:
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
