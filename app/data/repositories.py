from __future__ import annotations

import calendar
import hashlib
import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache

from app.data.catalog_repository import (
    CatalogRepository,
    clear_catalog_repository_instance_caches,
)
from app.data.database import (
    connect,
    ensure_catalog_schema,
    ensure_travel_cache_schema,
    resolve_database_url,
)
from app.domain.models import (
    AuthenticatedUser,
    AuthSessionResponse,
    CompanionEvent,
    CurrentTrip,
    Destination,
    RawWeatherObservation,
    RegisteredDevice,
    Rental,
    ResortConditions,
    ResortConditionSnapshot,
    SkiArea,
    SnowClimatologyBaselinePeriod,
    SnowClimatologyDaily,
    StayBase,
    TerrainDomain,
    WeatherElevationBand,
)
from app.domain.travel import PROVIDER, CachedRoute, TravelOrigin

FRESHNESS_WINDOW = timedelta(hours=24)
CONDITIONS_CACHE_TTL = timedelta(minutes=5)
SESSION_TTL = timedelta(days=30)


@dataclass(frozen=True)
class ArchiveCoverageStats:
    covered_days: int = 0
    first_observed_on: str | None = None
    last_observed_on: str | None = None


@dataclass(frozen=True)
class ClimatologyCoverageStats:
    row_count: int = 0
    min_evidence_seasons: int | None = None
    latest_archive_year: int | None = None


RAW_WEATHER_SELECT_COLUMNS = """
    ski_area_id, resort_name, observed_on::text AS observed_on,
    elevation_band, elevation_m, observed_at, snowfall_cm,
    snow_depth_m, precipitation_sum_mm, rain_sum_mm,
    precipitation_hours, snowfall_water_equivalent_sum_mm,
    temperature_2m_max_c, temperature_2m_min_c,
    apparent_temperature_2m_max_c,
    apparent_temperature_2m_min_c, cloud_cover_mean_pct,
    sunshine_duration_seconds, visibility_min_m,
    wind_speed_10m_max_kmh, wind_gusts_10m_max_kmh,
    weather_code, record_type, source, source_model
"""

SNOW_CLIMATOLOGY_SELECT_COLUMNS = """
    ski_area_id, resort_name, elevation_band, elevation_m, month, day,
    baseline_period, baseline_start_year, baseline_end_year, evidence_seasons,
    latest_archive_year, snow_depth_cm_p25, snow_depth_cm_p50,
    snow_depth_cm_p75, prob_snow_depth_ge_30cm, prob_snow_depth_ge_50cm,
    avg_daily_snowfall_cm, prob_rain_risk, prob_freeze_thaw,
    avg_max_temperature_c, avg_wind_gust_kmh, avg_snow_confidence_score,
    avg_conditions_score, source_model, computed_at
"""

CONDITION_SNAPSHOT_SELECT_COLUMNS = """
    ski_area_id, resort_name, observed_month, observed_at,
    snow_confidence_score, snow_confidence_label,
    availability_status, weather_summary, conditions_score, source
"""


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _coerce_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return None


def _archive_month_ranges(
    *,
    min_observed_on: date,
    max_observed_on: date,
    travel_month: int,
) -> tuple[tuple[date, date], ...]:
    ranges: list[tuple[date, date]] = []
    for year in range(min_observed_on.year, max_observed_on.year + 1):
        ranges.append(
            (
                date(year, travel_month, 1),
                date(year, travel_month, calendar.monthrange(year, travel_month)[1]),
            )
        )
    return tuple(ranges)


def _archive_recurring_date_ranges(
    *,
    min_observed_on: date,
    max_observed_on: date,
    trip_start_date: date,
    trip_end_date: date,
) -> tuple[tuple[date, date], ...]:
    ranges: list[tuple[date, date]] = []
    wraps_year = (trip_start_date.month, trip_start_date.day) > (
        trip_end_date.month,
        trip_end_date.day,
    )
    for year in range(min_observed_on.year, max_observed_on.year + 1):
        start = _safe_date(year, trip_start_date.month, trip_start_date.day)
        end = _safe_date(year, trip_end_date.month, trip_end_date.day)
        if not wraps_year:
            if start is not None and end is not None:
                ranges.append((start, end))
            continue

        if start is not None:
            ranges.append((start, date(year, 12, 31)))
        if end is not None:
            ranges.append((date(year, 1, 1), end))
    return tuple(ranges)


def _climatology_month_day_clause(
    *,
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> tuple[str, tuple[object, ...]]:
    has_partial_dates = (trip_start_date is None) != (trip_end_date is None)
    if has_partial_dates:
        raise ValueError("trip_start_date and trip_end_date must be provided together")
    if trip_start_date is not None and trip_end_date is not None:
        if trip_end_date < trip_start_date:
            raise ValueError("trip_end_date cannot be earlier than trip_start_date")
        start = date(2000, trip_start_date.month, trip_start_date.day)
        end = date(2000, trip_end_date.month, trip_end_date.day)
        if start <= end:
            return (
                "make_date(2000, month, day) BETWEEN %s::date AND %s::date",
                (start.isoformat(), end.isoformat()),
            )
        return (
            "(make_date(2000, month, day) >= %s::date "
            "OR make_date(2000, month, day) <= %s::date)",
            (start.isoformat(), end.isoformat()),
        )

    if travel_month is None:
        raise ValueError("travel_month or exact trip dates are required")
    if not 1 <= travel_month <= 12:
        raise ValueError("travel_month must be between 1 and 12")
    return "month = %s", (travel_month,)


def _load_season_windows(value: object) -> list[object]:
    return _load_json_list(value)


def _load_json_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return parsed


def _load_json_object(value: object) -> object | None:
    if isinstance(value, dict):
        return value
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _load_json_string_dict(value: object) -> dict[str, str]:
    parsed = _load_json_object(value)
    if not isinstance(parsed, dict):
        return {}
    return {str(key): value for key, value in parsed.items() if isinstance(value, str)}


def _load_json_string_list(value: object) -> list[str]:
    return [item for item in _load_json_list(value) if isinstance(item, str)]


class ResortRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()
        self._schema_checked = False
        self._resorts_cache: tuple[Destination, ...] | None = None
        self._terrain_domains_cache: tuple[TerrainDomain, ...] | None = None

    def list_resorts(self) -> tuple[Destination, ...]:
        if self._resorts_cache is not None:
            return self._resorts_cache

        self._ensure_schema()
        with connect(self._database_url) as connection:
            resort_rows = connection.execute(
                """
                SELECT resort_id, name, country, region, price_level,
                       latitude, longitude, base_elevation_m, summit_elevation_m,
                       season_start_month, season_end_month, season_windows_json,
                       lift_pass_prices_json, lift_pass_products_json,
                       terrain_groups_json
                FROM resorts
                WHERE is_active = TRUE
                ORDER BY name
                """
            ).fetchall()
            ski_area_rows = connection.execute(
                """
                SELECT resort_id, ski_area_id, name, latitude, longitude,
                       base_elevation_m, summit_elevation_m,
                       season_start_month, season_end_month, season_windows_json,
                       total_piste_km, total_lift_count,
                       piste_km_by_difficulty_json
                FROM ski_areas
                WHERE is_active = TRUE
                ORDER BY resort_id, id
                """
            ).fetchall()
            stay_base_rows = connection.execute(
                """
                SELECT id, resort_id, stay_base_id, name, price_range, price_min,
                       price_max, quality, lift_distance, latitude, longitude,
                       nearest_lift_name, nearest_lift_distance_m, access_mode,
                       base_type, atmosphere_tags_json, regional_data_ids_json
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
            payload = dict(row)
            payload["season_windows"] = _load_season_windows(
                payload.pop("season_windows_json")
            )
            payload["piste_km_by_difficulty"] = _load_json_object(
                payload.pop("piste_km_by_difficulty_json")
            )
            ski_areas_by_resort.setdefault(row["resort_id"], []).append(
                SkiArea.model_validate(payload)
            )

        stay_bases_by_resort: dict[str, list[StayBase]] = {}
        for row in stay_base_rows:
            stay_bases_by_resort.setdefault(row["resort_id"], []).append(
                StayBase.model_validate(
                    {
                        "name": row["name"],
                        "stay_base_id": row["stay_base_id"],
                        "price_range": row["price_range"],
                        "price_min": row["price_min"],
                        "price_max": row["price_max"],
                        "quality": row["quality"],
                        "lift_distance": row["lift_distance"],
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                        "nearest_lift_name": row["nearest_lift_name"],
                        "nearest_lift_distance_m": row["nearest_lift_distance_m"],
                        "access_mode": row["access_mode"],
                        "base_type": row["base_type"],
                        "atmosphere_tags": _load_json_string_list(
                            row["atmosphere_tags_json"]
                        ),
                        "regional_data_ids": _load_json_string_dict(
                            row["regional_data_ids_json"]
                        ),
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

        resorts = tuple(
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
                    "season_windows": _load_season_windows(row["season_windows_json"]),
                    "lift_pass_products": _load_json_list(
                        row["lift_pass_products_json"]
                    ),
                    "terrain_groups": _load_json_list(row["terrain_groups_json"]),
                    "stay_bases": stay_bases_by_resort.get(row["resort_id"], []),
                    "ski_areas": ski_areas_by_resort.get(row["resort_id"], []),
                    "rentals": rentals_by_resort.get(row["resort_id"], []),
                }
            )
            for row in resort_rows
        )
        self._resorts_cache = resorts
        return resorts

    def list_terrain_domains(self) -> tuple[TerrainDomain, ...]:
        if self._terrain_domains_cache is not None:
            return self._terrain_domains_cache

        self._ensure_schema()
        with connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT terrain_domain_id, name, ski_area_refs_json, metric_scope,
                       total_piste_km, total_lift_count, base_elevation_m,
                       summit_elevation_m, piste_km_by_difficulty_json,
                       season_windows_json, source_urls_json
                FROM terrain_domains
                ORDER BY terrain_domain_id
                """
            ).fetchall()

        terrain_domains = tuple(
            TerrainDomain.model_validate(
                {
                    "terrain_domain_id": row["terrain_domain_id"],
                    "name": row["name"],
                    "ski_area_refs": _load_json_list(row["ski_area_refs_json"]),
                    "metric_scope": row["metric_scope"],
                    "total_piste_km": row["total_piste_km"],
                    "total_lift_count": row["total_lift_count"],
                    "base_elevation_m": row["base_elevation_m"],
                    "summit_elevation_m": row["summit_elevation_m"],
                    "piste_km_by_difficulty": _load_json_object(
                        row["piste_km_by_difficulty_json"]
                    ),
                    "season_windows": _load_season_windows(row["season_windows_json"]),
                    "source_urls": _load_json_string_list(row["source_urls_json"]),
                }
            )
            for row in rows
        )
        self._terrain_domains_cache = terrain_domains
        return terrain_domains

    def get_resort_by_id(self, resort_id: str) -> Destination | None:
        return next(
            (resort for resort in self.list_resorts() if resort.resort_id == resort_id),
            None,
        )

    def _ensure_schema(self) -> None:
        if self._schema_checked:
            return
        ensure_catalog_schema(self._database_url)
        self._schema_checked = True


class ResortConditionsRepository:
    def __init__(
        self,
        database_url: str | None = None,
        *,
        conditions_cache_ttl: timedelta = CONDITIONS_CACHE_TTL,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._database_url = database_url or resolve_database_url()
        self._conditions_cache: dict[str, ResortConditions] | None = None
        self._conditions_cache_loaded_at: datetime | None = None
        self._conditions_cache_ttl = conditions_cache_ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    def list_conditions(self) -> dict[str, ResortConditions]:
        if self._is_conditions_cache_valid():
            assert self._conditions_cache is not None
            return self._conditions_cache

        with connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT resort_conditions.ski_area_id, resort_name,
                       snow_confidence_score, snow_confidence_label,
                       availability_status, weather_summary, conditions_score,
                       updated_at, source
                FROM resort_conditions
                JOIN ski_areas
                  ON ski_areas.ski_area_id = resort_conditions.ski_area_id
                WHERE ski_areas.is_active = TRUE
                ORDER BY resort_conditions.resort_name
                """
            ).fetchall()

        conditions = {
            row["ski_area_id"]: ResortConditions.model_validate(dict(row))
            for row in rows
        }
        self._conditions_cache = conditions
        self._conditions_cache_loaded_at = self._clock()
        return conditions

    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions | None:
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT resort_conditions.resort_name, snow_confidence_score,
                       snow_confidence_label, availability_status, weather_summary,
                       conditions_score, updated_at, source
                FROM resort_conditions
                JOIN ski_areas
                  ON ski_areas.ski_area_id = resort_conditions.ski_area_id
                WHERE resort_name = %s
                  AND ski_areas.is_active = TRUE
                """,
                (resort_name,),
            ).fetchone()

        if row is None:
            return None
        return ResortConditions.model_validate(dict(row))

    def get_conditions_for_ski_area(self, ski_area_id: str) -> ResortConditions | None:
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT resort_conditions.resort_name, snow_confidence_score,
                       snow_confidence_label, availability_status, weather_summary,
                       conditions_score, updated_at, source
                FROM resort_conditions
                JOIN ski_areas
                  ON ski_areas.ski_area_id = resort_conditions.ski_area_id
                WHERE resort_conditions.ski_area_id = %s
                  AND ski_areas.is_active = TRUE
                """,
                (ski_area_id,),
            ).fetchone()

        if row is None:
            return None
        return ResortConditions.model_validate(dict(row))

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
                    ski_area_id,
                    resort_name,
                    snow_confidence_score,
                    snow_confidence_label,
                    availability_status,
                    weather_summary,
                    conditions_score,
                    updated_at,
                    source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ski_area_id) DO UPDATE SET
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
        self._conditions_cache = None
        self._conditions_cache_loaded_at = None

    def _is_conditions_cache_valid(self) -> bool:
        if self._conditions_cache is None or self._conditions_cache_loaded_at is None:
            return False
        if self._conditions_cache_ttl <= timedelta(0):
            return False
        cache_age = self._clock() - self._conditions_cache_loaded_at
        return cache_age <= self._conditions_cache_ttl


class ResortConditionHistoryRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def list_snapshots_for_ski_area(
        self, ski_area_id: str
    ) -> tuple[ResortConditionSnapshot, ...]:
        with connect(self._database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT {CONDITION_SNAPSHOT_SELECT_COLUMNS}
                FROM resort_condition_history
                WHERE ski_area_id = %s
                ORDER BY observed_at
                """,
                (ski_area_id,),
            ).fetchall()

        return tuple(ResortConditionSnapshot.model_validate(dict(row)) for row in rows)

    def list_snapshots_for_ski_areas(
        self,
        ski_area_ids: tuple[str, ...],
    ) -> dict[str, tuple[ResortConditionSnapshot, ...]]:
        grouped: dict[str, list[ResortConditionSnapshot]] = {
            ski_area_id: [] for ski_area_id in ski_area_ids
        }
        if not ski_area_ids:
            return {}

        with connect(self._database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT {CONDITION_SNAPSHOT_SELECT_COLUMNS}
                FROM resort_condition_history
                WHERE ski_area_id = ANY(%s)
                ORDER BY ski_area_id, observed_at
                """,
                (list(ski_area_ids),),
            ).fetchall()

        for row in rows:
            snapshot = ResortConditionSnapshot.model_validate(dict(row))
            grouped.setdefault(snapshot.ski_area_id, []).append(snapshot)
        return {key: tuple(value) for key, value in grouped.items()}

    def append_snapshot(
        self,
        *,
        snapshot: ResortConditionSnapshot,
    ) -> None:
        with connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO resort_condition_history (
                    ski_area_id,
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
                ON CONFLICT (ski_area_id, observed_at) DO NOTHING
                """,
                (
                    snapshot.ski_area_id,
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


class RawWeatherHistoryRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def latest_archive_observed_on(self) -> date | None:
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT MAX(observed_on) AS latest_observed_on
                FROM raw_weather_history
                WHERE record_type = 'archive'
                """
            ).fetchone()
        if row is None:
            return None
        return _coerce_date(row["latest_observed_on"])

    def has_complete_archive_coverage(
        self,
        *,
        ski_area_id: str,
        elevation_band: WeatherElevationBand,
        start_date: date,
        end_date: date,
    ) -> bool:
        expected_days = (end_date - start_date).days + 1
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT COUNT(DISTINCT observed_on) AS covered_days
                FROM raw_weather_history
                WHERE ski_area_id = %s
                  AND elevation_band = %s
                  AND observed_on BETWEEN %s::date AND %s::date
                  AND record_type = 'archive'
                """,
                (
                    ski_area_id,
                    elevation_band,
                    start_date.isoformat(),
                    end_date.isoformat(),
                ),
            ).fetchone()

        covered_days = int(row["covered_days"]) if row is not None else 0
        return covered_days == expected_days

    def list_archive_coverage(
        self,
        *,
        ski_area_ids: tuple[str, ...],
        elevation_bands: tuple[WeatherElevationBand, ...],
        start_date: date,
        end_date: date,
    ) -> dict[tuple[str, WeatherElevationBand], ArchiveCoverageStats]:
        if end_date < start_date:
            raise ValueError("end_date cannot be earlier than start_date")

        grouped: dict[tuple[str, WeatherElevationBand], ArchiveCoverageStats] = {
            (ski_area_id, elevation_band): ArchiveCoverageStats()
            for ski_area_id in ski_area_ids
            for elevation_band in elevation_bands
        }
        if not ski_area_ids or not elevation_bands:
            return grouped

        with connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT ski_area_id,
                       elevation_band,
                       COUNT(DISTINCT observed_on)::integer AS covered_days,
                       MIN(observed_on)::text AS first_observed_on,
                       MAX(observed_on)::text AS last_observed_on
                FROM raw_weather_history
                WHERE ski_area_id = ANY(%s)
                  AND elevation_band = ANY(%s)
                  AND observed_on BETWEEN %s::date AND %s::date
                  AND record_type = 'archive'
                GROUP BY ski_area_id, elevation_band
                """,
                (
                    list(ski_area_ids),
                    list(elevation_bands),
                    start_date.isoformat(),
                    end_date.isoformat(),
                ),
            ).fetchall()

        for row in rows:
            key = (row["ski_area_id"], row["elevation_band"])
            if key in grouped:
                grouped[key] = ArchiveCoverageStats(
                    covered_days=int(row["covered_days"]),
                    first_observed_on=row["first_observed_on"],
                    last_observed_on=row["last_observed_on"],
                )
        return grouped

    def list_observations_for_ski_area(
        self,
        ski_area_id: str,
        *,
        elevation_band: WeatherElevationBand | None = None,
    ) -> tuple[RawWeatherObservation, ...]:
        band_filter = "AND elevation_band = %s" if elevation_band is not None else ""
        params: tuple[str, ...] = (
            (ski_area_id, elevation_band)
            if elevation_band is not None
            else (ski_area_id,)
        )
        with connect(self._database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT {RAW_WEATHER_SELECT_COLUMNS}
                FROM raw_weather_history
                WHERE ski_area_id = %s
                {band_filter}
                ORDER BY observed_on
                """,
                params,
            ).fetchall()
        return tuple(RawWeatherObservation.model_validate(dict(row)) for row in rows)

    def list_observations_for_ski_areas(
        self,
        ski_area_ids: tuple[str, ...],
        *,
        elevation_bands: tuple[WeatherElevationBand, ...],
    ) -> dict[tuple[str, WeatherElevationBand], tuple[RawWeatherObservation, ...]]:
        grouped: dict[tuple[str, WeatherElevationBand], list[RawWeatherObservation]] = {
            (ski_area_id, elevation_band): []
            for ski_area_id in ski_area_ids
            for elevation_band in elevation_bands
        }
        if not ski_area_ids or not elevation_bands:
            return {key: tuple(value) for key, value in grouped.items()}

        with connect(self._database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT {RAW_WEATHER_SELECT_COLUMNS}
                FROM raw_weather_history
                WHERE ski_area_id = ANY(%s)
                  AND elevation_band = ANY(%s)
                ORDER BY ski_area_id, elevation_band, observed_on
                """,
                (list(ski_area_ids), list(elevation_bands)),
            ).fetchall()

        for row in rows:
            observation = RawWeatherObservation.model_validate(dict(row))
            grouped[(observation.ski_area_id, observation.elevation_band)].append(
                observation
            )
        return {key: tuple(value) for key, value in grouped.items()}

    def list_archive_observations_for_ski_areas_window(
        self,
        ski_area_ids: tuple[str, ...],
        *,
        elevation_bands: tuple[WeatherElevationBand, ...],
        travel_month: int | None = None,
        trip_start_date: date | None = None,
        trip_end_date: date | None = None,
    ) -> dict[tuple[str, WeatherElevationBand], tuple[RawWeatherObservation, ...]]:
        grouped: dict[tuple[str, WeatherElevationBand], list[RawWeatherObservation]] = {
            (ski_area_id, elevation_band): []
            for ski_area_id in ski_area_ids
            for elevation_band in elevation_bands
        }
        if not ski_area_ids or not elevation_bands:
            return {key: tuple(value) for key, value in grouped.items()}

        has_partial_dates = (trip_start_date is None) != (trip_end_date is None)
        if has_partial_dates:
            raise ValueError(
                "trip_start_date and trip_end_date must be provided together"
            )
        if trip_start_date is not None and trip_end_date is not None:
            if trip_end_date < trip_start_date:
                raise ValueError("trip_end_date cannot be earlier than trip_start_date")
            use_exact_dates = True
        else:
            use_exact_dates = False

        if not use_exact_dates:
            if travel_month is None:
                raise ValueError("travel_month or exact trip dates are required")
            if not 1 <= travel_month <= 12:
                raise ValueError("travel_month must be between 1 and 12")

        with connect(self._database_url) as connection:
            bounds = connection.execute(
                """
                SELECT MIN(observed_on) AS min_observed_on,
                       MAX(observed_on) AS max_observed_on
                FROM raw_weather_history
                WHERE ski_area_id = ANY(%s)
                  AND elevation_band = ANY(%s)
                  AND record_type = 'archive'
                """,
                (list(ski_area_ids), list(elevation_bands)),
            ).fetchone()

            min_observed_on = (
                _coerce_date(bounds["min_observed_on"]) if bounds is not None else None
            )
            max_observed_on = (
                _coerce_date(bounds["max_observed_on"]) if bounds is not None else None
            )
            if min_observed_on is None or max_observed_on is None:
                return {key: tuple(value) for key, value in grouped.items()}

            if use_exact_dates:
                assert trip_start_date is not None
                assert trip_end_date is not None
                date_ranges = _archive_recurring_date_ranges(
                    min_observed_on=min_observed_on,
                    max_observed_on=max_observed_on,
                    trip_start_date=trip_start_date,
                    trip_end_date=trip_end_date,
                )
            else:
                assert travel_month is not None
                date_ranges = _archive_month_ranges(
                    min_observed_on=min_observed_on,
                    max_observed_on=max_observed_on,
                    travel_month=travel_month,
                )

            if not date_ranges:
                return {key: tuple(value) for key, value in grouped.items()}

            range_clauses: list[str] = []
            params: list[object] = [list(ski_area_ids), list(elevation_bands)]
            for start_date, end_date in date_ranges:
                range_clauses.append("observed_on BETWEEN %s::date AND %s::date")
                params.extend((start_date.isoformat(), end_date.isoformat()))

            rows = connection.execute(
                f"""
                SELECT {RAW_WEATHER_SELECT_COLUMNS}
                FROM raw_weather_history
                WHERE ski_area_id = ANY(%s)
                  AND elevation_band = ANY(%s)
                  AND record_type = 'archive'
                  AND ({" OR ".join(range_clauses)})
                ORDER BY ski_area_id, elevation_band, observed_on
                """,
                tuple(params),
            ).fetchall()

        for row in rows:
            observation = RawWeatherObservation.model_validate(dict(row))
            grouped[(observation.ski_area_id, observation.elevation_band)].append(
                observation
            )
        return {key: tuple(value) for key, value in grouped.items()}

    def delete_observations_for_ski_area(
        self,
        *,
        ski_area_id: str,
        start_date: date,
        end_date: date,
        elevation_band: WeatherElevationBand | None = None,
        record_type: str | None = None,
    ) -> int:
        clauses = [
            "ski_area_id = %s",
            "observed_on BETWEEN %s::date AND %s::date",
        ]
        params: list[object] = [
            ski_area_id,
            start_date.isoformat(),
            end_date.isoformat(),
        ]
        if elevation_band is not None:
            clauses.append("elevation_band = %s")
            params.append(elevation_band)
        if record_type is not None:
            clauses.append("record_type = %s")
            params.append(record_type)

        with connect(self._database_url) as connection:
            result = connection.execute(
                f"""
                DELETE FROM raw_weather_history
                WHERE {" AND ".join(clauses)}
                """,
                tuple(params),
            )
            return result.rowcount or 0

    def upsert_observation(self, observation: RawWeatherObservation) -> None:
        self.upsert_observations((observation,))

    def upsert_observations(
        self,
        observations: tuple[RawWeatherObservation, ...],
    ) -> int:
        if not observations:
            return 0

        params = tuple(_raw_weather_observation_params(row) for row in observations)
        with connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO raw_weather_history (
                        ski_area_id,
                        resort_name,
                        elevation_band,
                        elevation_m,
                        observed_on,
                        observed_at,
                        snowfall_cm,
                        snow_depth_m,
                        precipitation_sum_mm,
                        rain_sum_mm,
                        precipitation_hours,
                        snowfall_water_equivalent_sum_mm,
                        temperature_2m_max_c,
                        temperature_2m_min_c,
                        apparent_temperature_2m_max_c,
                        apparent_temperature_2m_min_c,
                        cloud_cover_mean_pct,
                        sunshine_duration_seconds,
                        visibility_min_m,
                        wind_speed_10m_max_kmh,
                        wind_gusts_10m_max_kmh,
                        weather_code,
                        record_type,
                        source,
                        source_model
                    ) VALUES (
                        %s, %s, %s, %s, %s::date, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (ski_area_id, elevation_band, observed_on, source)
                    DO UPDATE SET
                        resort_name = excluded.resort_name,
                        elevation_m = excluded.elevation_m,
                        observed_at = excluded.observed_at,
                        snowfall_cm = excluded.snowfall_cm,
                        snow_depth_m = excluded.snow_depth_m,
                        precipitation_sum_mm = excluded.precipitation_sum_mm,
                        rain_sum_mm = excluded.rain_sum_mm,
                        precipitation_hours = excluded.precipitation_hours,
                        snowfall_water_equivalent_sum_mm =
                            excluded.snowfall_water_equivalent_sum_mm,
                        temperature_2m_max_c = excluded.temperature_2m_max_c,
                        temperature_2m_min_c = excluded.temperature_2m_min_c,
                        apparent_temperature_2m_max_c =
                            excluded.apparent_temperature_2m_max_c,
                        apparent_temperature_2m_min_c =
                            excluded.apparent_temperature_2m_min_c,
                        cloud_cover_mean_pct = excluded.cloud_cover_mean_pct,
                        sunshine_duration_seconds =
                            excluded.sunshine_duration_seconds,
                        visibility_min_m = excluded.visibility_min_m,
                        wind_speed_10m_max_kmh = excluded.wind_speed_10m_max_kmh,
                        wind_gusts_10m_max_kmh = excluded.wind_gusts_10m_max_kmh,
                        weather_code = excluded.weather_code,
                        record_type = excluded.record_type,
                        source_model = excluded.source_model
                    """,
                    params,
                )
        return len(observations)


def _raw_weather_observation_params(row: RawWeatherObservation) -> tuple[object, ...]:
    return (
        row.ski_area_id,
        row.resort_name,
        row.elevation_band,
        row.elevation_m,
        row.observed_on,
        row.observed_at,
        row.snowfall_cm,
        row.snow_depth_m,
        row.precipitation_sum_mm,
        row.rain_sum_mm,
        row.precipitation_hours,
        row.snowfall_water_equivalent_sum_mm,
        row.temperature_2m_max_c,
        row.temperature_2m_min_c,
        row.apparent_temperature_2m_max_c,
        row.apparent_temperature_2m_min_c,
        row.cloud_cover_mean_pct,
        row.sunshine_duration_seconds,
        row.visibility_min_m,
        row.wind_speed_10m_max_kmh,
        row.wind_gusts_10m_max_kmh,
        row.weather_code,
        row.record_type,
        row.source,
        row.source_model,
    )


def _snow_climatology_params(row: SnowClimatologyDaily) -> tuple[object, ...]:
    return (
        row.ski_area_id,
        row.resort_name,
        row.elevation_band,
        row.elevation_m,
        row.month,
        row.day,
        row.baseline_period,
        row.baseline_start_year,
        row.baseline_end_year,
        row.evidence_seasons,
        row.latest_archive_year,
        row.snow_depth_cm_p25,
        row.snow_depth_cm_p50,
        row.snow_depth_cm_p75,
        row.prob_snow_depth_ge_30cm,
        row.prob_snow_depth_ge_50cm,
        row.avg_daily_snowfall_cm,
        row.prob_rain_risk,
        row.prob_freeze_thaw,
        row.avg_max_temperature_c,
        row.avg_wind_gust_kmh,
        row.avg_snow_confidence_score,
        row.avg_conditions_score,
        row.source_model,
        row.computed_at,
    )


class SnowClimatologyRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def upsert_daily_rows(
        self,
        rows: tuple[SnowClimatologyDaily, ...],
    ) -> int:
        if not rows:
            return 0
        params = tuple(_snow_climatology_params(row) for row in rows)
        with connect(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO ski_area_snow_climatology_daily (
                        ski_area_id,
                        resort_name,
                        elevation_band,
                        elevation_m,
                        month,
                        day,
                        baseline_period,
                        baseline_start_year,
                        baseline_end_year,
                        evidence_seasons,
                        latest_archive_year,
                        snow_depth_cm_p25,
                        snow_depth_cm_p50,
                        snow_depth_cm_p75,
                        prob_snow_depth_ge_30cm,
                        prob_snow_depth_ge_50cm,
                        avg_daily_snowfall_cm,
                        prob_rain_risk,
                        prob_freeze_thaw,
                        avg_max_temperature_c,
                        avg_wind_gust_kmh,
                        avg_snow_confidence_score,
                        avg_conditions_score,
                        source_model,
                        computed_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (
                        ski_area_id,
                        elevation_band,
                        month,
                        day,
                        baseline_period,
                        source_model
                    )
                    DO UPDATE SET
                        resort_name = excluded.resort_name,
                        elevation_m = excluded.elevation_m,
                        baseline_start_year = excluded.baseline_start_year,
                        baseline_end_year = excluded.baseline_end_year,
                        evidence_seasons = excluded.evidence_seasons,
                        latest_archive_year = excluded.latest_archive_year,
                        snow_depth_cm_p25 = excluded.snow_depth_cm_p25,
                        snow_depth_cm_p50 = excluded.snow_depth_cm_p50,
                        snow_depth_cm_p75 = excluded.snow_depth_cm_p75,
                        prob_snow_depth_ge_30cm =
                            excluded.prob_snow_depth_ge_30cm,
                        prob_snow_depth_ge_50cm =
                            excluded.prob_snow_depth_ge_50cm,
                        avg_daily_snowfall_cm = excluded.avg_daily_snowfall_cm,
                        prob_rain_risk = excluded.prob_rain_risk,
                        prob_freeze_thaw = excluded.prob_freeze_thaw,
                        avg_max_temperature_c = excluded.avg_max_temperature_c,
                        avg_wind_gust_kmh = excluded.avg_wind_gust_kmh,
                        avg_snow_confidence_score =
                            excluded.avg_snow_confidence_score,
                        avg_conditions_score = excluded.avg_conditions_score,
                        computed_at = excluded.computed_at
                    """,
                    params,
                )
        return len(rows)

    def delete_rows_for_ski_area(
        self,
        *,
        ski_area_id: str,
        source_model: str | None = None,
    ) -> int:
        clauses = ["ski_area_id = %s"]
        params: list[object] = [ski_area_id]
        if source_model is not None:
            clauses.append("source_model = %s")
            params.append(source_model)
        with connect(self._database_url) as connection:
            result = connection.execute(
                f"""
                DELETE FROM ski_area_snow_climatology_daily
                WHERE {" AND ".join(clauses)}
                """,
                tuple(params),
            )
            return result.rowcount or 0

    def list_climatology_coverage(
        self,
        *,
        ski_area_ids: tuple[str, ...],
        elevation_bands: tuple[WeatherElevationBand, ...],
        baseline_periods: tuple[SnowClimatologyBaselinePeriod, ...],
        source_model: str,
    ) -> dict[
        tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod],
        ClimatologyCoverageStats,
    ]:
        grouped: dict[
            tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod],
            ClimatologyCoverageStats,
        ] = {
            (ski_area_id, elevation_band, baseline_period): ClimatologyCoverageStats()
            for ski_area_id in ski_area_ids
            for elevation_band in elevation_bands
            for baseline_period in baseline_periods
        }
        if not ski_area_ids or not elevation_bands or not baseline_periods:
            return grouped

        with connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT ski_area_id,
                       elevation_band,
                       baseline_period,
                       COUNT(*)::integer AS row_count,
                       MIN(evidence_seasons)::integer AS min_evidence_seasons,
                       MAX(latest_archive_year)::integer AS latest_archive_year
                FROM ski_area_snow_climatology_daily
                WHERE ski_area_id = ANY(%s)
                  AND elevation_band = ANY(%s)
                  AND baseline_period = ANY(%s)
                  AND source_model = %s
                GROUP BY ski_area_id, elevation_band, baseline_period
                """,
                (
                    list(ski_area_ids),
                    list(elevation_bands),
                    list(baseline_periods),
                    source_model,
                ),
            ).fetchall()

        for row in rows:
            key = (row["ski_area_id"], row["elevation_band"], row["baseline_period"])
            if key in grouped:
                grouped[key] = ClimatologyCoverageStats(
                    row_count=int(row["row_count"]),
                    min_evidence_seasons=row["min_evidence_seasons"],
                    latest_archive_year=row["latest_archive_year"],
                )
        return grouped

    def list_daily_rows_for_ski_areas_window(
        self,
        ski_area_ids: tuple[str, ...],
        *,
        elevation_bands: tuple[WeatherElevationBand, ...],
        baseline_periods: tuple[SnowClimatologyBaselinePeriod, ...],
        travel_month: int | None = None,
        trip_start_date: date | None = None,
        trip_end_date: date | None = None,
    ) -> dict[
        tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod],
        tuple[SnowClimatologyDaily, ...],
    ]:
        grouped: dict[
            tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod],
            list[SnowClimatologyDaily],
        ] = {
            (ski_area_id, elevation_band, baseline_period): []
            for ski_area_id in ski_area_ids
            for elevation_band in elevation_bands
            for baseline_period in baseline_periods
        }
        if not ski_area_ids or not elevation_bands or not baseline_periods:
            return {key: tuple(value) for key, value in grouped.items()}

        window_clause, window_params = _climatology_month_day_clause(
            travel_month=travel_month,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
        )
        with connect(self._database_url) as connection:
            rows = connection.execute(
                f"""
                SELECT {SNOW_CLIMATOLOGY_SELECT_COLUMNS}
                FROM ski_area_snow_climatology_daily
                WHERE ski_area_id = ANY(%s)
                  AND elevation_band = ANY(%s)
                  AND baseline_period = ANY(%s)
                  AND {window_clause}
                ORDER BY ski_area_id, elevation_band, baseline_period, month, day
                """,
                (
                    list(ski_area_ids),
                    list(elevation_bands),
                    list(baseline_periods),
                    *window_params,
                ),
            ).fetchall()

        for row in rows:
            climatology = SnowClimatologyDaily.model_validate(dict(row))
            grouped[
                (
                    climatology.ski_area_id,
                    climatology.elevation_band,
                    climatology.baseline_period,
                )
            ].append(climatology)
        return {key: tuple(value) for key, value in grouped.items()}


class LLMCacheRepository:
    def __init__(self, database_url: str | None = None) -> None:
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


class TravelCacheRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()
        self._schema_checked = False

    def get_geocode(self, origin_key: str) -> TravelOrigin | None:
        self._ensure_schema()
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT resolved_label, latitude, longitude
                FROM travel_geocode_cache
                WHERE normalized_origin = %s AND provider = %s
                """,
                (origin_key, PROVIDER),
            ).fetchone()

        if row is None:
            return None
        return TravelOrigin(
            label=row["resolved_label"],
            latitude=row["latitude"],
            longitude=row["longitude"],
        )

    def set_geocode(self, origin_key: str, origin: TravelOrigin) -> None:
        self._ensure_schema()
        with connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO travel_geocode_cache (
                    normalized_origin,
                    provider,
                    resolved_label,
                    latitude,
                    longitude,
                    fetched_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (normalized_origin, provider) DO UPDATE SET
                    resolved_label = excluded.resolved_label,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    fetched_at = excluded.fetched_at
                """,
                (
                    origin_key,
                    PROVIDER,
                    origin.label,
                    origin.latitude,
                    origin.longitude,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get_route(self, origin_key: str, destination_key: str) -> CachedRoute | None:
        self._ensure_schema()
        destination_entity_id, destination_coord_key = self._destination_parts(
            destination_key
        )
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT distance_km, duration_minutes
                FROM travel_route_cache
                WHERE origin_key = %s
                  AND destination_entity_type = 'destination'
                  AND destination_entity_id = %s
                  AND destination_coord_key = %s
                  AND mode = 'car'
                  AND provider = %s
                """,
                (
                    origin_key,
                    destination_entity_id,
                    destination_coord_key,
                    PROVIDER,
                ),
            ).fetchone()

        if row is None:
            return None
        return CachedRoute(
            distance_km=row["distance_km"],
            duration_minutes=row["duration_minutes"],
        )

    def set_route(
        self,
        origin_key: str,
        destination_key: str,
        route: CachedRoute,
    ) -> None:
        self._ensure_schema()
        destination_entity_id, destination_coord_key = self._destination_parts(
            destination_key
        )
        with connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO travel_route_cache (
                    origin_key,
                    destination_entity_type,
                    destination_entity_id,
                    destination_coord_key,
                    mode,
                    provider,
                    distance_km,
                    duration_minutes,
                    provenance,
                    fetched_at
                ) VALUES (%s, 'destination', %s, %s, 'car', %s, %s, %s, %s, %s)
                ON CONFLICT (
                    origin_key,
                    destination_entity_type,
                    destination_entity_id,
                    destination_coord_key,
                    mode,
                    provider
                ) DO UPDATE SET
                    distance_km = excluded.distance_km,
                    duration_minutes = excluded.duration_minutes,
                    provenance = excluded.provenance,
                    fetched_at = excluded.fetched_at
                """,
                (
                    origin_key,
                    destination_entity_id,
                    destination_coord_key,
                    PROVIDER,
                    route.distance_km,
                    route.duration_minutes,
                    "estimated_fallback",
                    datetime.now(UTC).isoformat(),
                ),
            )

    def _ensure_schema(self) -> None:
        if self._schema_checked:
            return
        ensure_travel_cache_schema(self._database_url)
        self._schema_checked = True

    @staticmethod
    def _destination_parts(destination_key: str) -> tuple[str, str]:
        parts = destination_key.split("|")
        if len(parts) == 4:
            return parts[0], f"{parts[2]}|{parts[3]}"
        return destination_key, destination_key


class OutboundBookingClickRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def record_click(
        self,
        *,
        created_at: str,
        stay_destination_id: str,
        stay_base_id: str,
        focus_ski_area_id: str,
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
                    stay_destination_id,
                    stay_base_id,
                    focus_ski_area_id,
                    target_url,
                    source_surface,
                    request_id,
                    user_agent
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    created_at,
                    stay_destination_id,
                    stay_base_id,
                    focus_ski_area_id,
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
                SELECT id, created_at, stay_destination_id, stay_base_id,
                       focus_ski_area_id, target_url,
                       source_surface, request_id, user_agent
                FROM outbound_booking_clicks
                ORDER BY id
                """
            ).fetchall()

        return [dict(row) for row in rows]


class CurrentTripRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def get_current_trip(self, *, user_id: str) -> CurrentTrip | None:
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT ski_region_id, ski_region_name,
                       stay_destination_id, stay_destination_name,
                       stay_base_id, stay_base_name,
                       focus_ski_area_id, focus_ski_area_name,
                       lift_pass_product_id, lift_pass_product_name, travel_month,
                       trip_start_date, trip_end_date,
                       booking_status, created_at, updated_at, last_checked_at
                FROM user_current_trip
                WHERE user_id = %s
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return None
        return CurrentTrip.model_validate(dict(row))

    def upsert_current_trip(self, *, user_id: str, trip: CurrentTrip) -> CurrentTrip:
        with connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO user_current_trip (
                    user_id,
                    ski_region_id,
                    ski_region_name,
                    stay_destination_id,
                    stay_destination_name,
                    stay_base_id,
                    stay_base_name,
                    focus_ski_area_id,
                    focus_ski_area_name,
                    lift_pass_product_id,
                    lift_pass_product_name,
                    travel_month,
                    trip_start_date,
                    trip_end_date,
                    booking_status,
                    created_at,
                    updated_at,
                    last_checked_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    ski_region_id = excluded.ski_region_id,
                    ski_region_name = excluded.ski_region_name,
                    stay_destination_id = excluded.stay_destination_id,
                    stay_destination_name = excluded.stay_destination_name,
                    stay_base_id = excluded.stay_base_id,
                    stay_base_name = excluded.stay_base_name,
                    focus_ski_area_id = excluded.focus_ski_area_id,
                    focus_ski_area_name = excluded.focus_ski_area_name,
                    lift_pass_product_id = excluded.lift_pass_product_id,
                    lift_pass_product_name = excluded.lift_pass_product_name,
                    travel_month = excluded.travel_month,
                    trip_start_date = excluded.trip_start_date,
                    trip_end_date = excluded.trip_end_date,
                    booking_status = excluded.booking_status,
                    created_at = user_current_trip.created_at,
                    updated_at = excluded.updated_at,
                    last_checked_at = excluded.last_checked_at
                """,
                (
                    user_id,
                    trip.ski_region_id,
                    trip.ski_region_name,
                    trip.stay_destination_id,
                    trip.stay_destination_name,
                    trip.stay_base_id,
                    trip.stay_base_name,
                    trip.focus_ski_area_id,
                    trip.focus_ski_area_name,
                    trip.lift_pass_product_id,
                    trip.lift_pass_product_name,
                    trip.travel_month,
                    trip.trip_start_date,
                    trip.trip_end_date,
                    trip.booking_status,
                    trip.created_at,
                    trip.updated_at,
                    trip.last_checked_at,
                ),
            )

        saved = self.get_current_trip(user_id=user_id)
        assert saved is not None
        return saved

    def clear_current_trip(self, *, user_id: str) -> None:
        with connect(self._database_url) as connection:
            connection.execute(
                "DELETE FROM user_current_trip WHERE user_id = %s",
                (user_id,),
            )

    def mark_checked(self, *, user_id: str, checked_at: str) -> CurrentTrip | None:
        with connect(self._database_url) as connection:
            connection.execute(
                """
                UPDATE user_current_trip
                SET last_checked_at = %s
                WHERE user_id = %s
                """,
                (checked_at, user_id),
            )

        return self.get_current_trip(user_id=user_id)


class DeviceRegistrationRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def register_device(
        self,
        *,
        user_id: str,
        installation_id: str,
        platform: str,
        push_token: str | None,
        push_enabled: bool,
        now: str | None = None,
    ) -> RegisteredDevice:
        timestamp = now or datetime.now(UTC).isoformat()
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                INSERT INTO user_devices (
                    user_id,
                    installation_id,
                    platform,
                    push_token,
                    push_enabled,
                    created_at,
                    updated_at,
                    last_seen_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, installation_id) DO UPDATE SET
                    platform = excluded.platform,
                    push_token = excluded.push_token,
                    push_enabled = excluded.push_enabled,
                    updated_at = excluded.updated_at,
                    last_seen_at = excluded.last_seen_at
                RETURNING installation_id, platform, push_token, push_enabled,
                          created_at, updated_at, last_seen_at
                """,
                (
                    user_id,
                    installation_id,
                    platform,
                    push_token,
                    push_enabled,
                    timestamp,
                    timestamp,
                    timestamp,
                ),
            ).fetchone()
        assert row is not None
        return RegisteredDevice.model_validate(dict(row))


class CompanionEventRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def record_event(
        self,
        *,
        user_id: str,
        ski_region_id: str,
        stay_destination_id: str,
        stay_base_id: str,
        focus_ski_area_id: str,
        lift_pass_product_id: str,
        event_type: str,
        event_signature: str,
        actionable: bool,
        summary: str,
        changes: list[str],
        trip_window_status: str,
        conditions_updated_at: str | None,
        recorded_at: str | None = None,
    ) -> CompanionEvent | None:
        timestamp = recorded_at or datetime.now(UTC).isoformat()
        event_id = str(uuid.uuid4())
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                INSERT INTO companion_events (
                    event_id,
                    user_id,
                    ski_region_id,
                    stay_destination_id,
                    stay_base_id,
                    focus_ski_area_id,
                    lift_pass_product_id,
                    event_type,
                    event_signature,
                    actionable,
                    summary,
                    changes_json,
                    trip_window_status,
                    conditions_updated_at,
                    recorded_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (user_id, event_signature) DO NOTHING
                RETURNING event_id, event_type, recorded_at, actionable,
                          summary, changes_json, trip_window_status,
                          conditions_updated_at
                """,
                (
                    event_id,
                    user_id,
                    ski_region_id,
                    stay_destination_id,
                    stay_base_id,
                    focus_ski_area_id,
                    lift_pass_product_id,
                    event_type,
                    event_signature,
                    actionable,
                    summary,
                    json.dumps(changes),
                    trip_window_status,
                    conditions_updated_at,
                    timestamp,
                ),
            ).fetchone()

        if row is None:
            return None
        return self._row_to_event(dict(row))

    def list_events_for_user(self, *, user_id: str) -> list[CompanionEvent]:
        with connect(self._database_url) as connection:
            rows = connection.execute(
                """
                SELECT event_id, event_type, recorded_at, actionable,
                       summary, changes_json, trip_window_status,
                       conditions_updated_at
                FROM companion_events
                WHERE user_id = %s
                ORDER BY recorded_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._row_to_event(dict(row)) for row in rows]

    def _row_to_event(self, row: dict) -> CompanionEvent:
        row["changes"] = json.loads(row.pop("changes_json"))
        return CompanionEvent.model_validate(row)


class AppUserRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def upsert_google_user(
        self,
        *,
        provider_subject: str,
        email: str,
        display_name: str | None,
        now: str | None = None,
    ) -> AuthenticatedUser:
        timestamp = now or datetime.now(UTC).isoformat()
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                INSERT INTO app_users (
                    user_id,
                    auth_provider,
                    provider_subject,
                    email,
                    display_name,
                    created_at,
                    updated_at
                ) VALUES (%s, 'google', %s, %s, %s, %s, %s)
                ON CONFLICT (auth_provider, provider_subject) DO UPDATE SET
                    email = excluded.email,
                    display_name = excluded.display_name,
                    updated_at = excluded.updated_at
                RETURNING user_id, email, display_name, auth_provider
                """,
                (
                    str(uuid.uuid4()),
                    provider_subject,
                    email,
                    display_name,
                    timestamp,
                    timestamp,
                ),
            ).fetchone()

        assert row is not None
        return AuthenticatedUser.model_validate(dict(row))

    def get_user_by_id(self, *, user_id: str) -> AuthenticatedUser | None:
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT user_id, email, display_name, auth_provider
                FROM app_users
                WHERE user_id = %s
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return None
        return AuthenticatedUser.model_validate(dict(row))


class AppSessionRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()

    def create_session(
        self,
        *,
        user: AuthenticatedUser,
        now: datetime | None = None,
        ttl: timedelta = SESSION_TTL,
    ) -> AuthSessionResponse:
        created_at = now or datetime.now(UTC)
        expires_at = created_at + ttl
        access_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(access_token)
        with connect(self._database_url) as connection:
            connection.execute(
                """
                INSERT INTO auth_sessions (
                    session_id,
                    user_id,
                    token_hash,
                    created_at,
                    expires_at,
                    last_used_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    user.user_id,
                    token_hash,
                    created_at.isoformat(),
                    expires_at.isoformat(),
                    created_at.isoformat(),
                ),
            )

        return AuthSessionResponse(
            access_token=access_token,
            expires_at=expires_at.isoformat(),
            user=user,
        )

    def get_user_for_access_token(
        self, *, access_token: str
    ) -> AuthenticatedUser | None:
        token_hash = self._hash_token(access_token)
        now = datetime.now(UTC).isoformat()
        with connect(self._database_url) as connection:
            row = connection.execute(
                """
                SELECT u.user_id, u.email, u.display_name, u.auth_provider
                FROM auth_sessions s
                JOIN app_users u ON u.user_id = s.user_id
                WHERE s.token_hash = %s
                  AND s.expires_at > %s
                """,
                (token_hash, now),
            ).fetchone()
            if row is not None:
                connection.execute(
                    """
                    UPDATE auth_sessions
                    SET last_used_at = %s
                    WHERE token_hash = %s
                    """,
                    (now, token_hash),
                )

        if row is None:
            return None
        return AuthenticatedUser.model_validate(dict(row))

    @staticmethod
    def _hash_token(access_token: str) -> str:
        return hashlib.sha256(access_token.encode("utf-8")).hexdigest()


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
def get_catalog_repository(
    database_url: str | None = None,
) -> CatalogRepository:
    return CatalogRepository(database_url)


@lru_cache
def get_resort_repository(
    database_url: str | None = None,
) -> ResortRepository:
    return ResortRepository(database_url)


@lru_cache
def get_conditions_repository(
    database_url: str | None = None,
) -> ResortConditionsRepository:
    return ResortConditionsRepository(database_url)


@lru_cache
def get_condition_history_repository(
    database_url: str | None = None,
) -> ResortConditionHistoryRepository:
    return ResortConditionHistoryRepository(database_url)


@lru_cache
def get_raw_weather_history_repository(
    database_url: str | None = None,
) -> RawWeatherHistoryRepository:
    return RawWeatherHistoryRepository(database_url)


@lru_cache
def get_snow_climatology_repository(
    database_url: str | None = None,
) -> SnowClimatologyRepository:
    return SnowClimatologyRepository(database_url)


@lru_cache
def get_travel_cache_repository(
    database_url: str | None = None,
) -> TravelCacheRepository:
    return TravelCacheRepository(database_url)


def clear_repository_caches() -> None:
    clear_catalog_repository_instance_caches()
    get_catalog_repository.cache_clear()
    get_resort_repository.cache_clear()
    get_conditions_repository.cache_clear()
    get_condition_history_repository.cache_clear()
    get_raw_weather_history_repository.cache_clear()
    get_snow_climatology_repository.cache_clear()
    get_travel_cache_repository.cache_clear()
