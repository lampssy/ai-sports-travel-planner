from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import date

from app.data.database import connect, resolve_database_url

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RawWeatherRecordTypeCorrectionResult:
    archive_rows: int
    forecast_rows: int


def correct_raw_weather_record_types(
    *,
    database_url: str | None = None,
    forecast_after: date,
    source: str = "open-meteo",
) -> RawWeatherRecordTypeCorrectionResult:
    with connect(database_url) as connection:
        archive_rows = len(
            connection.execute(
                """
                UPDATE raw_weather_history
                SET record_type = 'archive'
                WHERE source = %s
                  AND observed_on <= %s::date
                  AND record_type <> 'archive'
                RETURNING 1
                """,
                (source, forecast_after.isoformat()),
            ).fetchall()
        )
        forecast_rows = len(
            connection.execute(
                """
                UPDATE raw_weather_history
                SET record_type = 'forecast'
                WHERE source = %s
                  AND observed_on > %s::date
                  AND record_type <> 'forecast'
                RETURNING 1
                """,
                (source, forecast_after.isoformat()),
            ).fetchall()
        )

    return RawWeatherRecordTypeCorrectionResult(
        archive_rows=archive_rows,
        forecast_rows=forecast_rows,
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
            "One-time maintenance command to mark raw weather rows before a cutoff "
            "date as archive and rows after it as forecast."
        )
    )
    parser.add_argument(
        "--database-url",
        help="Explicit Postgres database URL. Defaults to DATABASE_URL.",
    )
    parser.add_argument(
        "--forecast-after",
        required=True,
        help=(
            "ISO cutoff date. Rows with observed_on greater than this date are "
            "marked as forecast."
        ),
    )
    parser.add_argument(
        "--source",
        default="open-meteo",
        help="Source name to correct. Defaults to open-meteo.",
    )
    args = parser.parse_args()

    result = correct_raw_weather_record_types(
        database_url=args.database_url or resolve_database_url(),
        forecast_after=date.fromisoformat(args.forecast_after),
        source=args.source,
    )
    LOGGER.info(
        "Raw weather record type correction complete: archive_rows=%s "
        "forecast_rows=%s cutoff=%s source=%s",
        result.archive_rows,
        result.forecast_rows,
        args.forecast_after,
        args.source,
    )


if __name__ == "__main__":
    main()
