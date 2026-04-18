from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.data.database import connect, resolve_database_url
from app.domain.models import (
    CurrentTrip,
    Destination,
    Rental,
    ResortConditions,
    ResortConditionSnapshot,
    SkiArea,
    StayBase,
)

FRESHNESS_WINDOW = timedelta(hours=24)


class ResortRepository:
    def __init__(self, database_url: str | os.PathLike[str] | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def list_resorts(self) -> tuple[Destination, ...]:
        with connect(self._database_url) as connection:
            resort_rows = connection.execute(
                """
                SELECT resort_id, name, country, region, price_level,
                       latitude, longitude, base_elevation_m, summit_elevation_m,
                       season_start_month, season_end_month
                FROM resorts
                ORDER BY name
                """
            ).fetchall()
            ski_area_rows = connection.execute(
                """
                SELECT resort_id, ski_area_id, name, latitude, longitude,
                       base_elevation_m, summit_elevation_m,
                       season_start_month, season_end_month
                FROM ski_areas
                ORDER BY resort_id, id
                """
            ).fetchall()
            stay_base_rows = connection.execute(
                """
                SELECT id, resort_id, name, price_range, price_min, price_max,
                       quality, lift_distance
                FROM stay_bases
                ORDER BY resort_id, id
                """
            ).fetchall()
            skill_rows = connection.execute(
                """
                SELECT stay_base_id, skill_level
                FROM stay_base_skill_levels
                ORDER BY stay_base_id, skill_level
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

        skills_by_stay_base: dict[int, list[str]] = {}
        for row in skill_rows:
            skills_by_stay_base.setdefault(row["stay_base_id"], []).append(
                row["skill_level"]
            )

        ski_areas_by_resort: dict[str, list[SkiArea]] = {}
        for row in ski_area_rows:
            ski_areas_by_resort.setdefault(row["resort_id"], []).append(
                SkiArea.model_validate(dict(row))
            )

        stay_bases_by_resort: dict[str, list[StayBase]] = {}
        for row in stay_base_rows:
            stay_bases_by_resort.setdefault(row["resort_id"], []).append(
                StayBase.model_validate(
                    {
                        "name": row["name"],
                        "price_range": row["price_range"],
                        "price_min": row["price_min"],
                        "price_max": row["price_max"],
                        "quality": row["quality"],
                        "lift_distance": row["lift_distance"],
                        "supported_skill_levels": skills_by_stay_base.get(
                            row["id"], []
                        ),
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
            Destination.model_validate(
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
                    "stay_bases": stay_bases_by_resort.get(row["resort_id"], []),
                    "ski_areas": ski_areas_by_resort.get(row["resort_id"], []),
                    "rentals": rentals_by_resort.get(row["resort_id"], []),
                }
            )
            for row in resort_rows
        )

    def get_resort_by_id(self, resort_id: str) -> Destination | None:
        return next(
            (resort for resort in self.list_resorts() if resort.resort_id == resort_id),
            None,
        )


class ResortConditionsRepository:
    def __init__(self, database_url: str | os.PathLike[str] | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def list_conditions(self) -> dict[str, ResortConditions]:
        with connect(self._database_url) as connection:
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
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT resort_name, snow_confidence_score, snow_confidence_label,
                       availability_status, weather_summary, conditions_score,
                       updated_at, source
                FROM resort_conditions
                WHERE resort_name = %s
                """,
                (resort_name,),
            ).fetchone()

        if row is None:
            return None
        return ResortConditions.model_validate(dict(row))

    def get_conditions_for_ski_area(
        self, ski_area_name: str
    ) -> ResortConditions | None:
        return self.get_conditions_for_resort(ski_area_name)

    def upsert_conditions(
        self,
        entity=None,
        conditions: ResortConditions | None = None,
        *,
        entity_id: str | None = None,
        entity_name: str | None = None,
    ) -> None:
        if entity_id is None or entity_name is None:
            if entity is None or conditions is None:
                raise TypeError(
                    "upsert_conditions requires either entity_id/entity_name or "
                    "a compatible entity plus conditions"
                )
            if hasattr(entity, "ski_area_id"):
                entity_id = entity.ski_area_id
                entity_name = entity.name
            elif hasattr(entity, "ski_areas") and len(entity.ski_areas) == 1:
                entity_id = entity.ski_areas[0].ski_area_id
                entity_name = entity.ski_areas[0].name
            else:
                entity_id = entity.resort_id
                entity_name = entity.name

        assert conditions is not None
        with connect(self._database_url) as connection:
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (resort_id) DO UPDATE SET
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
                    entity_id,
                    entity_name,
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
    def __init__(self, database_url: str | os.PathLike[str] | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def list_snapshots_for_resort(
        self, resort_id: str
    ) -> tuple[ResortConditionSnapshot, ...]:
        with connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT resort_id, resort_name, observed_month, observed_at,
                       snow_confidence_score, snow_confidence_label,
                       availability_status, weather_summary, conditions_score, source
                FROM resort_condition_history
                WHERE resort_id = %s
                ORDER BY observed_at
                """,
                (resort_id,),
            ).fetchall()
            if not rows:
                ski_area_rows = connection.execute(
                    """
                    SELECT ski_area_id
                    FROM ski_areas
                    WHERE resort_id = %s
                    ORDER BY id
                    """,
                    (resort_id,),
                ).fetchall()
                if len(ski_area_rows) == 1:
                    rows = connection.execute(
                        """
                        SELECT resort_id, resort_name, observed_month, observed_at,
                               snow_confidence_score, snow_confidence_label,
                               availability_status, weather_summary,
                               conditions_score, source
                        FROM resort_condition_history
                        WHERE resort_id = %s
                        ORDER BY observed_at
                        """,
                        (ski_area_rows[0]["ski_area_id"],),
                    ).fetchall()

        return tuple(ResortConditionSnapshot.model_validate(dict(row)) for row in rows)

    def append_snapshot(
        self,
        *,
        snapshot: ResortConditionSnapshot,
    ) -> None:
        with connect(self._database_url) as connection:
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (resort_id, observed_at) DO NOTHING
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
    def __init__(self, database_url: str | os.PathLike[str] | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def get_parse_cache(self, cache_key: str) -> dict | None:
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT response_json
                FROM llm_parse_cache
                WHERE cache_key = %s
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
        with connect(self._database_url) as connection:
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE SET
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
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT response_json
                FROM llm_narrative_cache
                WHERE cache_key = %s
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
        with connect(self._database_url) as connection:
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE SET
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
    def __init__(self, database_url: str | os.PathLike[str] | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def record_click(
        self,
        *,
        created_at: str,
        resort_id: str,
        selected_area_name: str,
        selected_ski_area_name: str | None,
        target_url: str,
        source_surface: str,
        request_id: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        with connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO outbound_booking_clicks (
                    created_at,
                    resort_id,
                    selected_area_name,
                    selected_ski_area_name,
                    target_url,
                    source_surface,
                    request_id,
                    user_agent
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    created_at,
                    resort_id,
                    selected_area_name,
                    selected_ski_area_name,
                    target_url,
                    source_surface,
                    request_id,
                    user_agent,
                ),
            )

    def list_clicks(self) -> list[dict]:
        with connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, resort_id, selected_area_name,
                       selected_ski_area_name, target_url,
                       source_surface, request_id, user_agent
                FROM outbound_booking_clicks
                ORDER BY id
                """
            ).fetchall()

        return [dict(row) for row in rows]


class CurrentTripRepository:
    def __init__(self, database_url: str | os.PathLike[str] | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def get_current_trip(self) -> CurrentTrip | None:
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT resort_id, resort_name, selected_area_name,
                       selected_ski_area_id, selected_ski_area_name, travel_month,
                       booking_status, created_at, updated_at, last_checked_at
                FROM current_trip
                WHERE singleton_id = 1
                """
            ).fetchone()

        if row is None:
            return None
        payload = dict(row)
        payload["selected_stay_base_name"] = payload["selected_area_name"]
        payload["selected_ski_area_id"] = (
            payload["selected_ski_area_id"] or payload["resort_id"]
        )
        payload["selected_ski_area_name"] = (
            payload["selected_ski_area_name"] or payload["resort_name"]
        )
        return CurrentTrip.model_validate(payload)

    def upsert_current_trip(self, trip: CurrentTrip) -> CurrentTrip:
        with connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO current_trip (
                    singleton_id,
                    resort_id,
                    resort_name,
                    selected_area_name,
                    selected_ski_area_id,
                    selected_ski_area_name,
                    travel_month,
                    booking_status,
                    created_at,
                    updated_at,
                    last_checked_at
                ) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (singleton_id) DO UPDATE SET
                    resort_id = excluded.resort_id,
                    resort_name = excluded.resort_name,
                    selected_area_name = excluded.selected_area_name,
                    selected_ski_area_id = excluded.selected_ski_area_id,
                    selected_ski_area_name = excluded.selected_ski_area_name,
                    travel_month = excluded.travel_month,
                    booking_status = excluded.booking_status,
                    created_at = current_trip.created_at,
                    updated_at = excluded.updated_at,
                    last_checked_at = excluded.last_checked_at
                """,
                (
                    trip.resort_id,
                    trip.resort_name,
                    trip.selected_stay_base_name,
                    trip.selected_ski_area_id,
                    trip.selected_ski_area_name,
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
        with connect(self._database_url) as connection:
            connection.execute("DELETE FROM current_trip WHERE singleton_id = 1")

    def mark_checked(self, *, checked_at: str) -> CurrentTrip | None:
        with connect(self._database_url) as connection:
            connection.execute(
                """
                UPDATE current_trip
                SET last_checked_at = %s
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
def get_resort_repository(
    database_url: str | os.PathLike[str] | None = None,
) -> ResortRepository:
    return ResortRepository(database_url)


@lru_cache
def get_conditions_repository(
    database_url: str | os.PathLike[str] | None = None,
) -> ResortConditionsRepository:
    return ResortConditionsRepository(database_url)


@lru_cache
def get_condition_history_repository(
    database_url: str | os.PathLike[str] | None = None,
) -> ResortConditionHistoryRepository:
    return ResortConditionHistoryRepository(database_url)


def clear_repository_caches() -> None:
    get_resort_repository.cache_clear()
    get_conditions_repository.cache_clear()
    get_condition_history_repository.cache_clear()
