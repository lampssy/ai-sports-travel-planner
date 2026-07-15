from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from app.data.database import connect, resolve_database_url
from app.domain.weather_forecast import (
    ForecastRetentionResult,
    ServedWeatherForecastDaily,
    WeatherForecastDaily,
    WeatherForecastHead,
    WeatherForecastRun,
)

_RUN_COLUMNS = """
    forecast_run_id, forecast_source_key, provider_gateway, producer,
    provider_model_id, forecast_kind, model_initialization_time,
    provider_availability_time, ingested_at, completed_at, first_valid_date,
    last_valid_date, status, schema_version, parser_version,
    aggregation_policy_version, provider_metadata_json, failure_reason
"""
_DAILY_COLUMNS = """
    forecast_run_id, ski_area_id, valid_local_date, provider_timezone,
    elevation_band, representative_elevation_m, request_latitude,
    request_longitude, snow_depth_cm, snow_depth_spread_cm, snowfall_cm,
    rain_mm, positive_degree_hours, temperature_2m_min_c,
    temperature_2m_max_c, freezing_level_mean_m, freezing_level_max_m,
    wind_speed_10m_max_kmh, wind_gusts_10m_max_kmh,
    ensemble_member_count, is_complete, completeness_metadata_json
"""
_QUALIFIED_RUN_COLUMNS = ", ".join(
    f"r.{column.strip()}" for column in _RUN_COLUMNS.split(",")
)
_QUALIFIED_DAILY_COLUMNS = ", ".join(
    f"d.{column.strip()}" for column in _DAILY_COLUMNS.split(",")
)


class ForecastRepositoryError(ValueError):
    pass


class ForecastPublicationError(ForecastRepositoryError):
    pass


class WeatherForecastRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def create_building_run(self, run: WeatherForecastRun) -> None:
        if run.status != "building":
            raise ForecastRepositoryError("new forecast run must be building")
        with connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO weather_forecast_runs (
                    forecast_run_id, forecast_source_key, provider_gateway,
                    producer, provider_model_id, forecast_kind,
                    model_initialization_time, provider_availability_time,
                    ingested_at, completed_at, first_valid_date, last_valid_date,
                    status, schema_version, parser_version,
                    aggregation_policy_version, provider_metadata_json,
                    failure_reason
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s,
                    'building', %s, %s, %s, %s, NULL
                )
                """,
                (
                    run.forecast_run_id,
                    run.forecast_source_key,
                    run.provider_gateway,
                    run.producer,
                    run.provider_model_id,
                    run.forecast_kind,
                    run.model_initialization_time,
                    run.provider_availability_time,
                    run.ingested_at,
                    run.first_valid_date,
                    run.last_valid_date,
                    run.schema_version,
                    run.parser_version,
                    run.aggregation_policy_version,
                    json.dumps(dict(run.provider_metadata), sort_keys=True),
                ),
            )

    def find_complete_run_id(
        self,
        source_key: str,
        model_initialization_time: datetime,
        ski_area_ids: Sequence[str],
    ) -> str | None:
        requested_area_ids = tuple(sorted(set(ski_area_ids)))
        if not requested_area_ids:
            raise ForecastRepositoryError(
                "complete forecast run lookup needs at least one ski area"
            )
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT r.forecast_run_id
                FROM weather_forecast_runs AS r
                WHERE r.forecast_source_key = %s
                  AND r.model_initialization_time = %s
                  AND r.status = 'complete'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM unnest(%s::text[]) AS requested(ski_area_id)
                      WHERE NOT EXISTS (
                          SELECT 1
                          FROM ski_area_weather_forecast_daily AS d
                          WHERE d.forecast_run_id = r.forecast_run_id
                            AND d.ski_area_id = requested.ski_area_id
                            AND d.is_complete
                      )
                  )
                ORDER BY r.ingested_at DESC, r.forecast_run_id
                LIMIT 1
                """,
                (source_key, model_initialization_time, list(requested_area_ids)),
            ).fetchone()
        return row["forecast_run_id"] if row is not None else None

    def insert_daily_rows(
        self,
        run_id: str,
        rows: Sequence[WeatherForecastDaily],
    ) -> None:
        if any(row.forecast_run_id != run_id for row in rows):
            raise ForecastRepositoryError("daily row run ID does not match")
        if any(not row.is_complete for row in rows):
            raise ForecastRepositoryError("only complete daily rows may be stored")
        if not rows:
            return
        with connect(self._database_url) as connection:
            run = connection.execute(
                """
                SELECT status
                FROM weather_forecast_runs
                WHERE forecast_run_id = %s
                FOR UPDATE
                """,
                (run_id,),
            ).fetchone()
            if run is None:
                raise ForecastRepositoryError(f"unknown forecast run: {run_id}")
            if run["status"] != "building":
                raise ForecastRepositoryError(
                    f"daily rows require building run: {run_id}"
                )
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO ski_area_weather_forecast_daily (
                        forecast_run_id, ski_area_id, valid_local_date,
                        provider_timezone, elevation_band,
                        representative_elevation_m, request_latitude,
                        request_longitude, snow_depth_cm, snow_depth_spread_cm,
                        snowfall_cm, rain_mm, positive_degree_hours,
                        temperature_2m_min_c, temperature_2m_max_c,
                        freezing_level_mean_m, freezing_level_max_m,
                        wind_speed_10m_max_kmh, wind_gusts_10m_max_kmh,
                        ensemble_member_count, is_complete,
                        completeness_metadata_json
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s
                    )
                    """,
                    [self._daily_insert_values(row) for row in rows],
                )

    def reject_or_fail_run(
        self,
        run_id: str,
        *,
        status: str,
        reason: str,
        completed_at: datetime,
    ) -> None:
        if status not in {"rejected", "failed"}:
            raise ForecastRepositoryError("terminal status must be rejected or failed")
        if not reason.strip():
            raise ForecastRepositoryError("terminal forecast reason must not be blank")
        with connect(self._database_url) as connection:
            cursor = connection.execute(
                """
                UPDATE weather_forecast_runs
                SET status = %s, completed_at = %s, failure_reason = %s
                WHERE forecast_run_id = %s AND status = 'building'
                """,
                (status, completed_at, reason.strip(), run_id),
            )
            if cursor.rowcount != 1:
                raise ForecastRepositoryError(f"forecast run is not building: {run_id}")

    def complete_run_and_advance_heads(
        self,
        run_id: str,
        *,
        publishable_ski_area_ids: Sequence[str],
        completed_at: datetime,
    ) -> None:
        area_ids = tuple(dict.fromkeys(publishable_ski_area_ids))
        if not area_ids:
            raise ForecastPublicationError(
                "at least one publishable ski area is required"
            )
        with connect(self._database_url) as connection:
            run = connection.execute(
                """
                SELECT forecast_source_key, status
                FROM weather_forecast_runs
                WHERE forecast_run_id = %s
                FOR UPDATE
                """,
                (run_id,),
            ).fetchone()
            if run is None:
                raise ForecastPublicationError(f"unknown forecast run: {run_id}")
            if run["status"] != "building":
                raise ForecastPublicationError(
                    f"forecast run is not building: {run_id}"
                )
            coverage_rows = connection.execute(
                """
                SELECT ski_area_id,
                       COUNT(*) FILTER (WHERE is_complete)::integer AS complete_rows,
                       COUNT(*) FILTER (
                           WHERE NOT is_complete
                       )::integer AS incomplete_rows
                FROM ski_area_weather_forecast_daily
                WHERE forecast_run_id = %s
                  AND ski_area_id = ANY(%s)
                GROUP BY ski_area_id
                """,
                (run_id, list(area_ids)),
            ).fetchall()
            coverage = {
                row["ski_area_id"]: (
                    int(row["complete_rows"]),
                    int(row["incomplete_rows"]),
                )
                for row in coverage_rows
            }
            invalid = [
                area_id
                for area_id in area_ids
                if area_id not in coverage
                or coverage[area_id][0] == 0
                or coverage[area_id][1] > 0
            ]
            if invalid:
                raise ForecastPublicationError(
                    "publishable areas need complete rows: " + ", ".join(invalid)
                )
            connection.execute(
                """
                UPDATE weather_forecast_runs
                SET status = 'complete', completed_at = %s
                WHERE forecast_run_id = %s
                """,
                (completed_at, run_id),
            )
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO ski_area_forecast_heads (
                        ski_area_id, forecast_source_key, forecast_run_id,
                        updated_at
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (ski_area_id, forecast_source_key) DO UPDATE SET
                        forecast_run_id = excluded.forecast_run_id,
                        updated_at = excluded.updated_at
                    """,
                    [
                        (
                            area_id,
                            run["forecast_source_key"],
                            run_id,
                            completed_at,
                        )
                        for area_id in area_ids
                    ],
                )

    def get_run(self, run_id: str) -> WeatherForecastRun | None:
        with connect(self._database_url) as connection:
            row = connection.execute(
                f"""
                SELECT {_RUN_COLUMNS}
                FROM weather_forecast_runs
                WHERE forecast_run_id = %s
                """,
                (run_id,),
            ).fetchone()
        return _run_from_row(row) if row is not None else None

    def list_heads(self) -> tuple[WeatherForecastHead, ...]:
        """Return every source-keyed ski-area serving head and its run."""

        with connect(self._database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT h.ski_area_id AS head_ski_area_id,
                       h.forecast_source_key AS head_source_key,
                       h.updated_at AS head_updated_at,
                       {_QUALIFIED_RUN_COLUMNS}
                FROM ski_area_forecast_heads h
                JOIN weather_forecast_runs r
                  ON r.forecast_run_id = h.forecast_run_id
                 AND r.status = 'complete'
                ORDER BY h.ski_area_id, h.forecast_source_key
                """
            ).fetchall()
        return tuple(
            WeatherForecastHead(
                ski_area_id=row["head_ski_area_id"],
                forecast_source_key=row["head_source_key"],
                run=_run_from_row(row),
                updated_at=row["head_updated_at"],
            )
            for row in rows
        )

    def list_latest_daily_rows(
        self,
        *,
        ski_area_ids: Sequence[str],
        start_date: date,
        end_date: date,
        source_keys: Sequence[str],
        elevation_band: str = "mid",
    ) -> tuple[ServedWeatherForecastDaily, ...]:
        if end_date < start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        if not ski_area_ids or not source_keys:
            return ()
        with connect(self._database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    {_QUALIFIED_RUN_COLUMNS},
                    {_QUALIFIED_DAILY_COLUMNS}
                FROM ski_area_forecast_heads h
                JOIN weather_forecast_runs r
                  ON r.forecast_run_id = h.forecast_run_id
                 AND r.status = 'complete'
                JOIN ski_area_weather_forecast_daily d
                  ON d.forecast_run_id = h.forecast_run_id
                 AND d.ski_area_id = h.ski_area_id
                WHERE h.ski_area_id = ANY(%s)
                  AND h.forecast_source_key = ANY(%s)
                  AND d.valid_local_date BETWEEN %s AND %s
                  AND d.elevation_band = %s
                  AND d.is_complete = TRUE
                ORDER BY d.ski_area_id, d.valid_local_date,
                         h.forecast_source_key
                """,
                (
                    list(dict.fromkeys(ski_area_ids)),
                    list(dict.fromkeys(source_keys)),
                    start_date,
                    end_date,
                    elevation_band,
                ),
            ).fetchall()
        return tuple(_served_from_joined_row(row) for row in rows)

    def apply_retention(self, now: datetime) -> ForecastRetentionResult:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("retention time must be timezone-aware")
        now_utc = now.astimezone(UTC)
        with connect(self._database_url) as connection:
            protected_ids = {
                row["forecast_run_id"]
                for row in connection.execute(
                    "SELECT DISTINCT forecast_run_id FROM ski_area_forecast_heads"
                ).fetchall()
            }
            rows = connection.execute(
                f"SELECT {_RUN_COLUMNS} FROM weather_forecast_runs"
            ).fetchall()
            runs = [_run_from_row(row) for row in rows]
            complete_runs = [run for run in runs if run.status == "complete"]
            keep_complete = set(protected_ids)
            daily_groups: dict[tuple[str, date], list[WeatherForecastRun]] = {}
            weekly_groups: dict[tuple[str, int, int], list[WeatherForecastRun]] = {}
            for run in complete_runs:
                age = now_utc - run.model_initialization_time.astimezone(UTC)
                if age <= timedelta(days=45):
                    keep_complete.add(run.forecast_run_id)
                elif age <= timedelta(days=365 * 2):
                    key = (
                        run.forecast_source_key,
                        run.model_initialization_time.astimezone(UTC).date(),
                    )
                    daily_groups.setdefault(key, []).append(run)
                elif age <= timedelta(days=365 * 5):
                    iso = run.model_initialization_time.astimezone(UTC).isocalendar()
                    key = (run.forecast_source_key, iso.year, iso.week)
                    weekly_groups.setdefault(key, []).append(run)
            for group in (*daily_groups.values(), *weekly_groups.values()):
                canonical = min(group, key=_canonical_run_sort_key)
                keep_complete.add(canonical.forecast_run_id)

            delete_complete = [
                run.forecast_run_id
                for run in complete_runs
                if run.forecast_run_id not in keep_complete
            ]
            delete_terminal = [
                run.forecast_run_id
                for run in runs
                if run.status in {"failed", "rejected"}
                and run.forecast_run_id not in protected_ids
                and run.completed_at is not None
                and now_utc - run.completed_at.astimezone(UTC) > timedelta(days=90)
            ]
            delete_ids = (*delete_complete, *delete_terminal)
            if delete_ids:
                connection.execute(
                    """
                    DELETE FROM weather_forecast_runs
                    WHERE forecast_run_id = ANY(%s)
                    """,
                    (list(delete_ids),),
                )
        return ForecastRetentionResult(
            deleted_complete_runs=len(delete_complete),
            deleted_failed_or_rejected_runs=len(delete_terminal),
            protected_head_runs=len(protected_ids),
        )

    @staticmethod
    def _daily_insert_values(row: WeatherForecastDaily) -> tuple[object, ...]:
        return (
            row.forecast_run_id,
            row.ski_area_id,
            row.valid_local_date,
            row.provider_timezone,
            row.elevation_band,
            row.representative_elevation_m,
            row.request_latitude,
            row.request_longitude,
            row.snow_depth_cm,
            row.snow_depth_spread_cm,
            row.snowfall_cm,
            row.rain_mm,
            row.positive_degree_hours,
            row.temperature_2m_min_c,
            row.temperature_2m_max_c,
            row.freezing_level_mean_m,
            row.freezing_level_max_m,
            row.wind_speed_10m_max_kmh,
            row.wind_gusts_10m_max_kmh,
            row.ensemble_member_count,
            json.dumps(dict(row.completeness_metadata), sort_keys=True),
        )


def _run_from_row(row: object) -> WeatherForecastRun:
    data = {
        column.strip(): row[column.strip()]  # type: ignore[index]
        for column in _RUN_COLUMNS.split(",")
    }
    data["provider_metadata"] = json.loads(data.pop("provider_metadata_json"))
    return WeatherForecastRun.model_validate(data)


def _daily_from_row(row: object) -> WeatherForecastDaily:
    data = {column.strip(): row[column.strip()] for column in _DAILY_COLUMNS.split(",")}  # type: ignore[index]
    data["completeness_metadata"] = json.loads(data.pop("completeness_metadata_json"))
    return WeatherForecastDaily.model_validate(data)


def _served_from_joined_row(row: object) -> ServedWeatherForecastDaily:
    return ServedWeatherForecastDaily(
        run=_run_from_row(row),
        daily=_daily_from_row(row),
    )


def _canonical_run_sort_key(run: WeatherForecastRun) -> tuple[bool, datetime]:
    initialized = run.model_initialization_time.astimezone(UTC)
    return initialized.hour != 0, initialized
