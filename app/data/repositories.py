import json
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from app.data.database import bootstrap_database, connect, resolve_db_path
from app.domain.models import (
    Area,
    CurrentTrip,
    Rental,
    Resort,
    ResortConditions,
    ResortConditionSnapshot,
)

FRESHNESS_WINDOW = timedelta(hours=24)


class ResortRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or resolve_db_path()
        bootstrap_database(self._db_path)

    def list_resorts(self) -> tuple[Resort, ...]:
        with connect(self._db_path) as connection:
            resort_rows = connection.execute(
                """
                SELECT resort_id, name, country, region, price_level
                       , latitude, longitude, base_elevation_m, summit_elevation_m,
                         season_start_month, season_end_month
                FROM resorts
                ORDER BY name
                """
            ).fetchall()
            area_rows = connection.execute(
                """
                SELECT id, resort_id, name, price_range, price_min, price_max,
                       quality, lift_distance
                FROM areas
                ORDER BY resort_id, id
                """
            ).fetchall()
            skill_rows = connection.execute(
                """
                SELECT area_id, skill_level
                FROM area_skill_levels
                ORDER BY area_id, skill_level
                """
            ).fetchall()
            rental_rows = connection.execute(
                """
                SELECT resort_id, name, price_range, price_min, price_max,
                       quality, lift_distance
                FROM rentals
                ORDER BY resort_id, id
                """
            ).fetchall()

        skills_by_area: dict[int, list[str]] = {}
        for row in skill_rows:
            skills_by_area.setdefault(row["area_id"], []).append(row["skill_level"])

        areas_by_resort: dict[str, list[Area]] = {}
        for row in area_rows:
            areas_by_resort.setdefault(row["resort_id"], []).append(
                Area.model_validate(
                    {
                        "name": row["name"],
                        "price_range": row["price_range"],
                        "price_min": row["price_min"],
                        "price_max": row["price_max"],
                        "quality": row["quality"],
                        "lift_distance": row["lift_distance"],
                        "supported_skill_levels": skills_by_area.get(row["id"], []),
                    }
                )
            )

        rentals_by_resort: dict[str, list[Rental]] = {}
        for row in rental_rows:
            rentals_by_resort.setdefault(row["resort_id"], []).append(
                Rental.model_validate(
                    {
                        "name": row["name"],
                        "price_range": row["price_range"],
                        "price_min": row["price_min"],
                        "price_max": row["price_max"],
                        "quality": row["quality"],
                        "lift_distance": row["lift_distance"],
                    }
                )
            )

        return tuple(
            Resort.model_validate(
                {
                    "resort_id": row["resort_id"],
                    "name": row["name"],
                    "country": row["country"],
                    "region": row["region"],
                    "price_level": row["price_level"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "base_elevation_m": row["base_elevation_m"],
                    "summit_elevation_m": row["summit_elevation_m"],
                    "season_start_month": row["season_start_month"],
                    "season_end_month": row["season_end_month"],
                    "areas": areas_by_resort.get(row["resort_id"], []),
                    "rentals": rentals_by_resort.get(row["resort_id"], []),
                }
            )
            for row in resort_rows
        )

    def get_resort_by_id(self, resort_id: str) -> Resort | None:
        return next(
            (resort for resort in self.list_resorts() if resort.resort_id == resort_id),
            None,
        )


class ResortConditionsRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or resolve_db_path()
        bootstrap_database(self._db_path)

    def list_conditions(self) -> dict[str, ResortConditions]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT resort_name, snow_confidence_score, snow_confidence_label,
                       availability_status, weather_summary, conditions_score,
                       updated_at, source
                FROM resort_conditions
                ORDER BY resort_name
                """
            ).fetchall()

        return {
            row["resort_name"]: ResortConditions.model_validate(dict(row))
            for row in rows
        }

    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                """
                SELECT resort_name, snow_confidence_score, snow_confidence_label,
                       availability_status, weather_summary, conditions_score,
                       updated_at, source
                FROM resort_conditions
                WHERE resort_name = ?
                """,
                (resort_name,),
            ).fetchone()

        if row is None:
            return None
        return ResortConditions.model_validate(dict(row))

    def upsert_conditions(self, resort: Resort, conditions: ResortConditions) -> None:
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO resort_conditions (
                    resort_id,
                    resort_name,
                    snow_confidence_score,
                    snow_confidence_label,
                    availability_status,
                    weather_summary,
                    conditions_score,
                    updated_at,
                    source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(resort_id) DO UPDATE SET
                    resort_name = excluded.resort_name,
                    snow_confidence_score = excluded.snow_confidence_score,
                    snow_confidence_label = excluded.snow_confidence_label,
                    availability_status = excluded.availability_status,
                    weather_summary = excluded.weather_summary,
                    conditions_score = excluded.conditions_score,
                    updated_at = excluded.updated_at,
                    source = excluded.source
                """,
                (
                    resort.resort_id,
                    conditions.resort_name,
                    conditions.snow_confidence_score,
                    conditions.snow_confidence_label,
                    conditions.availability_status,
                    conditions.weather_summary,
                    conditions.conditions_score,
                    conditions.updated_at,
                    conditions.source,
                ),
            )


class ResortConditionHistoryRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or resolve_db_path()
        bootstrap_database(self._db_path)

    def list_snapshots_for_resort(
        self, resort_id: str
    ) -> tuple[ResortConditionSnapshot, ...]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT resort_id, resort_name, observed_month, observed_at,
                       snow_confidence_score, snow_confidence_label,
                       availability_status, weather_summary, conditions_score, source
                FROM resort_condition_history
                WHERE resort_id = ?
                ORDER BY observed_at
                """,
                (resort_id,),
            ).fetchall()

        return tuple(ResortConditionSnapshot.model_validate(dict(row)) for row in rows)

    def append_snapshot(
        self,
        *,
        snapshot: ResortConditionSnapshot,
    ) -> None:
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO resort_condition_history (
                    resort_id,
                    resort_name,
                    observed_month,
                    observed_at,
                    snow_confidence_score,
                    snow_confidence_label,
                    availability_status,
                    weather_summary,
                    conditions_score,
                    source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(resort_id, observed_at) DO NOTHING
                """,
                (
                    snapshot.resort_id,
                    snapshot.resort_name,
                    snapshot.observed_month,
                    snapshot.observed_at,
                    snapshot.snow_confidence_score,
                    snapshot.snow_confidence_label,
                    snapshot.availability_status,
                    snapshot.weather_summary,
                    snapshot.conditions_score,
                    snapshot.source,
                ),
            )


class LLMCacheRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or resolve_db_path()
        bootstrap_database(self._db_path)

    def get_parse_cache(self, cache_key: str) -> dict | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                """
                SELECT response_json
                FROM llm_parse_cache
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()

        if row is None:
            return None
        return json.loads(row["response_json"])

    def set_parse_cache(
        self,
        *,
        cache_key: str,
        query_text: str,
        model: str,
        prompt_version: str,
        schema_version: str,
        response: dict,
        created_at: str,
    ) -> None:
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO llm_parse_cache (
                    cache_key,
                    query_text,
                    model,
                    prompt_version,
                    schema_version,
                    response_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_json = excluded.response_json,
                    created_at = excluded.created_at
                """,
                (
                    cache_key,
                    query_text,
                    model,
                    prompt_version,
                    schema_version,
                    json.dumps(response, sort_keys=True),
                    created_at,
                ),
            )

    def get_narrative_cache(self, cache_key: str) -> dict | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                """
                SELECT response_json
                FROM llm_narrative_cache
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()

        if row is None:
            return None
        return json.loads(row["response_json"])

    def set_narrative_cache(
        self,
        *,
        cache_key: str,
        result_signature: str,
        model: str,
        prompt_version: str,
        schema_version: str,
        response: dict,
        created_at: str,
    ) -> None:
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO llm_narrative_cache (
                    cache_key,
                    result_signature,
                    model,
                    prompt_version,
                    schema_version,
                    response_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_json = excluded.response_json,
                    created_at = excluded.created_at
                """,
                (
                    cache_key,
                    result_signature,
                    model,
                    prompt_version,
                    schema_version,
                    json.dumps(response, sort_keys=True),
                    created_at,
                ),
            )


class OutboundBookingClickRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or resolve_db_path()
        bootstrap_database(self._db_path)

    def record_click(
        self,
        *,
        created_at: str,
        resort_id: str,
        selected_area_name: str,
        target_url: str,
        source_surface: str,
        request_id: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO outbound_booking_clicks (
                    created_at,
                    resort_id,
                    selected_area_name,
                    target_url,
                    source_surface,
                    request_id,
                    user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    resort_id,
                    selected_area_name,
                    target_url,
                    source_surface,
                    request_id,
                    user_agent,
                ),
            )

    def list_clicks(self) -> list[dict]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, resort_id, selected_area_name, target_url,
                       source_surface, request_id, user_agent
                FROM outbound_booking_clicks
                ORDER BY id
                """
            ).fetchall()

        return [dict(row) for row in rows]


class CurrentTripRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or resolve_db_path()
        bootstrap_database(self._db_path)

    def get_current_trip(self) -> CurrentTrip | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                """
                SELECT resort_id, resort_name, selected_area_name, travel_month,
                       booking_status, created_at, updated_at, last_checked_at
                FROM current_trip
                WHERE singleton_id = 1
                """
            ).fetchone()

        if row is None:
            return None
        return CurrentTrip.model_validate(dict(row))

    def upsert_current_trip(self, trip: CurrentTrip) -> CurrentTrip:
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO current_trip (
                    singleton_id,
                    resort_id,
                    resort_name,
                    selected_area_name,
                    travel_month,
                    booking_status,
                    created_at,
                    updated_at,
                    last_checked_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    resort_id = excluded.resort_id,
                    resort_name = excluded.resort_name,
                    selected_area_name = excluded.selected_area_name,
                    travel_month = excluded.travel_month,
                    booking_status = excluded.booking_status,
                    created_at = current_trip.created_at,
                    updated_at = excluded.updated_at,
                    last_checked_at = excluded.last_checked_at
                """,
                (
                    trip.resort_id,
                    trip.resort_name,
                    trip.selected_area_name,
                    trip.travel_month,
                    trip.booking_status,
                    trip.created_at,
                    trip.updated_at,
                    trip.last_checked_at,
                ),
            )

        saved = self.get_current_trip()
        assert saved is not None
        return saved

    def clear_current_trip(self) -> None:
        with connect(self._db_path) as connection:
            connection.execute("DELETE FROM current_trip WHERE singleton_id = 1")

    def mark_checked(self, *, checked_at: str) -> CurrentTrip | None:
        with connect(self._db_path) as connection:
            connection.execute(
                """
                UPDATE current_trip
                SET last_checked_at = ?
                WHERE singleton_id = 1
                """,
                (checked_at,),
            )

        return self.get_current_trip()


def is_condition_fresh(
    condition: ResortConditions,
    *,
    now: datetime | None = None,
) -> bool:
    if not condition.updated_at:
        return False
    reference = now or datetime.now(UTC)
    updated_at = datetime.fromisoformat(condition.updated_at)
    return reference - updated_at <= FRESHNESS_WINDOW


@lru_cache
def get_resort_repository(db_path: Path | None = None) -> ResortRepository:
    return ResortRepository(db_path)


@lru_cache
def get_conditions_repository(
    db_path: Path | None = None,
) -> ResortConditionsRepository:
    return ResortConditionsRepository(db_path)


@lru_cache
def get_condition_history_repository(
    db_path: Path | None = None,
) -> ResortConditionHistoryRepository:
    return ResortConditionHistoryRepository(db_path)


def clear_repository_caches() -> None:
    get_resort_repository.cache_clear()
    get_conditions_repository.cache_clear()
    get_condition_history_repository.cache_clear()
