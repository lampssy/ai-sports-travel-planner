from __future__ import annotations

import argparse
from datetime import UTC, datetime

from app.data.database import bootstrap_database, resolve_database_url
from app.data.weather_forecast_repository import WeatherForecastRepository
from app.observability.cli import configure_cli_observability
from app.observability.jobs import job_span


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply tiered retention to immutable weather forecast runs."
    )
    parser.add_argument(
        "--database-url",
        default=resolve_database_url(),
        help="Postgres connection string for the planner database.",
    )
    args = parser.parse_args()

    bootstrap_database(args.database_url)
    with configure_cli_observability(job_name="retain_weather_forecasts"):
        with job_span("weather_forecast_retention"):
            result = WeatherForecastRepository(args.database_url).apply_retention(
                datetime.now(UTC)
            )
    print(
        "Weather forecast retention:",
        f"deleted_complete={result.deleted_complete_runs}",
        f"deleted_failed_or_rejected={result.deleted_failed_or_rejected_runs}",
        f"protected_heads={result.protected_head_runs}",
    )


if __name__ == "__main__":
    main()
