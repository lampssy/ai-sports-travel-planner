from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.data.database import DEFAULT_DB_PATH
from app.data.repositories import (
    ResortConditionsRepository,
    ResortRepository,
    is_condition_fresh,
)
from app.integrations.open_meteo import OpenMeteoClient, normalize_open_meteo_conditions

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


def _select_resorts(
    requested_targets: tuple[str, ...] | None,
    available_resorts: tuple,
) -> tuple:
    if not requested_targets:
        return available_resorts

    resorts_by_id = {resort.resort_id: resort for resort in available_resorts}
    resorts_by_name = {resort.name: resort for resort in available_resorts}
    selected_resorts = []
    missing_targets: list[str] = []

    for target in requested_targets:
        resort = resorts_by_id.get(target) or resorts_by_name.get(target)
        if resort is None:
            missing_targets.append(target)
            continue
        if resort not in selected_resorts:
            selected_resorts.append(resort)

    if missing_targets:
        raise UnknownRefreshTargetError(tuple(missing_targets))

    return tuple(selected_resorts)


def refresh_conditions(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    client: OpenMeteoClient | None = None,
    now: datetime | None = None,
    force: bool = False,
    targets: tuple[str, ...] | None = None,
    retry_attempts: int = RETRY_ATTEMPTS,
    backoff_seconds: float = RETRY_BACKOFF_SECONDS,
) -> RefreshResult:
    weather_client = client or OpenMeteoClient()
    observed_at = now or datetime.now(UTC)
    resort_repository = ResortRepository(db_path)
    conditions_repository = ResortConditionsRepository(db_path)
    result = RefreshResult()
    requested_resorts = _select_resorts(targets, resort_repository.list_resorts())

    for resort in requested_resorts:
        existing = conditions_repository.get_conditions_for_resort(resort.name)
        if not force and existing and is_condition_fresh(existing, now=observed_at):
            result.skipped_fresh += 1
            _log(f"[SKIP] {resort.name}: existing conditions are still fresh")
            continue

        _log(f"[REFRESH] {resort.name}: fetching Open-Meteo data")
        last_error: Exception | None = None
        for attempt in range(retry_attempts + 1):
            try:
                payload = weather_client.fetch_conditions(resort)
                normalized = normalize_open_meteo_conditions(
                    resort,
                    payload,
                    observed_at=observed_at,
                )
                conditions_repository.upsert_conditions(resort, normalized)
                result.refreshed += 1
                _log(f"[DONE] {resort.name}: refreshed successfully")
                last_error = None
                break
            except Exception as error:  # pragma: no cover - exercised via tests
                last_error = error
                if attempt < retry_attempts:
                    _log(
                        f"[RETRY] {resort.name}: attempt {attempt + 1} failed: {error}"
                    )
                    time.sleep(backoff_seconds)

        if last_error is not None:
            result.failed += 1
            failure = RefreshFailure(resort_name=resort.name, error=str(last_error))
            result.failures.append(failure)
            _log(f"[FAIL] {resort.name}: {last_error}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh real resort conditions from Open-Meteo into SQLite."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to the SQLite planner database.",
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
            db_path=Path(args.db_path),
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
