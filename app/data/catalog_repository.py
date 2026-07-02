from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.data.database import connect, resolve_database_url
from app.domain.catalog import CatalogSnapshot, SkiArea, StayDestination


class CatalogRepositoryError(RuntimeError):
    """Raised when persisted normalized catalog rows cannot form a snapshot."""


class CatalogRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()
        self._snapshot: CatalogSnapshot | None = None

    def get_snapshot(self) -> CatalogSnapshot:
        if self._snapshot is None:
            self._snapshot = _read_active_catalog_snapshot(self._database_url)
        return self._snapshot

    def get_stay_destination(self, stay_destination_id: str) -> StayDestination | None:
        return next(
            (
                destination
                for destination in self.get_snapshot().stay_destinations
                if destination.stay_destination_id == stay_destination_id
            ),
            None,
        )

    def get_ski_area(self, ski_area_id: str) -> SkiArea | None:
        return next(
            (
                area
                for area in self.get_snapshot().ski_areas
                if area.ski_area_id == ski_area_id
            ),
            None,
        )


_NO_DEFAULT = object()


def _decode_json(
    row: Mapping[str, Any],
    column_name: str,
    *,
    table_name: str,
    default: Any = _NO_DEFAULT,
) -> Any:
    raw_value = row.get(column_name)
    if raw_value is None:
        return None if default is _NO_DEFAULT else default
    try:
        value = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    except json.JSONDecodeError as error:
        raise CatalogRepositoryError(
            f"malformed JSON in {table_name}.{column_name}"
        ) from error
    if value is None and default is not _NO_DEFAULT:
        return default
    return value


def _group_relationships(
    rows: list[dict[str, Any]],
    *,
    owner_column: str,
    value_column: str,
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row[owner_column], []).append(row[value_column])
    return grouped


def _read_active_catalog_snapshot(database_url: str) -> CatalogSnapshot:
    with connect(database_url) as connection:
        ski_region_rows = connection.execute(
            """
            SELECT ski_region_id, name, grouping_policy,
                   parent_ski_region_id, source_urls_json
            FROM ski_regions
            WHERE is_active
            ORDER BY ski_region_id
            """
        ).fetchall()
        stay_destination_rows = connection.execute(
            """
            SELECT stay_destination_id, name, country, region, price_level,
                   latitude, longitude, trip_market_region_id,
                   atmosphere_tags_json, regional_data_ids_json
            FROM stay_destinations
            WHERE is_active
            ORDER BY stay_destination_id
            """
        ).fetchall()
        stay_base_rows = connection.execute(
            """
            SELECT stay_base.stay_base_id, stay_base.stay_destination_id,
                   stay_base.name, stay_base.price_range,
                   stay_base.price_min, stay_base.price_max,
                   stay_base.quality, stay_base.latitude,
                   stay_base.longitude, stay_base.base_type,
                   stay_base.atmosphere_tags_json,
                   stay_base.regional_data_ids_json
            FROM stay_bases AS stay_base
            JOIN stay_destinations AS destination
              ON destination.stay_destination_id =
                 stay_base.stay_destination_id
             AND destination.is_active
            WHERE stay_base.is_active
              AND stay_base.stay_destination_id IS NOT NULL
            ORDER BY stay_base.stay_base_id
            """
        ).fetchall()
        ski_area_rows = connection.execute(
            """
            SELECT ski_area_id, name, latitude, longitude,
                   base_elevation_m, summit_elevation_m,
                   season_start_month, season_end_month,
                   season_windows_json, total_piste_km,
                   total_lift_count, piste_km_by_difficulty_json,
                   supported_skill_levels_json
            FROM ski_areas
            WHERE is_active
            ORDER BY ski_area_id
            """
        ).fetchall()
        ski_area_access_rows = connection.execute(
            """
            SELECT access.ski_area_access_id, access.stay_base_id,
                   access.ski_area_id, access.access_mode,
                   access.lift_distance, access.nearest_lift_name,
                   access.distance_m, access.duration_minutes,
                   access.is_direct, access.regional_data_ids_json,
                   access.source_urls_json
            FROM ski_area_access AS access
            JOIN stay_bases AS stay_base
              ON stay_base.stay_base_id = access.stay_base_id
             AND stay_base.is_active
            JOIN stay_destinations AS destination
              ON destination.stay_destination_id =
                 stay_base.stay_destination_id
             AND destination.is_active
            JOIN ski_areas AS ski_area
              ON ski_area.ski_area_id = access.ski_area_id
             AND ski_area.is_active
            WHERE access.is_active
            ORDER BY access.ski_area_access_id
            """
        ).fetchall()
        terrain_domain_rows = connection.execute(
            """
            SELECT terrain_domain_id, name, metric_scope,
                   total_piste_km, total_lift_count,
                   base_elevation_m, summit_elevation_m,
                   piste_km_by_difficulty_json, season_windows_json,
                   source_urls_json
            FROM terrain_domains
            WHERE is_active
            ORDER BY terrain_domain_id
            """
        ).fetchall()
        lift_pass_product_rows = connection.execute(
            """
            SELECT lift_pass_product_id, name, validity_scope,
                   external_validity_summary,
                   pass_accessible_terrain_json, prices_json
            FROM lift_pass_products
            WHERE is_active
            ORDER BY lift_pass_product_id
            """
        ).fetchall()
        rental_display_fact_rows = connection.execute(
            """
            SELECT rental.rental_display_fact_id,
                   rental.stay_destination_id, rental.stay_base_id,
                   rental.name, rental.price_range, rental.price_min,
                   rental.price_max, rental.quality,
                   rental.lift_distance
            FROM rental_display_facts AS rental
            JOIN stay_destinations AS destination
              ON destination.stay_destination_id =
                 rental.stay_destination_id
             AND destination.is_active
            LEFT JOIN stay_bases AS stay_base
              ON stay_base.stay_base_id = rental.stay_base_id
             AND stay_base.is_active
            WHERE rental.is_active
              AND (
                rental.stay_base_id IS NULL
                OR stay_base.stay_base_id IS NOT NULL
              )
            ORDER BY rental.rental_display_fact_id
            """
        ).fetchall()
        terrain_domain_ski_area_rows = connection.execute(
            """
            SELECT relationship.terrain_domain_id,
                   relationship.ski_area_id, relationship.ordinal
            FROM terrain_domain_ski_areas AS relationship
            JOIN terrain_domains AS terrain_domain
              ON terrain_domain.terrain_domain_id =
                 relationship.terrain_domain_id
             AND terrain_domain.is_active
            JOIN ski_areas AS ski_area
              ON ski_area.ski_area_id = relationship.ski_area_id
             AND ski_area.is_active
            ORDER BY relationship.terrain_domain_id,
                     relationship.ordinal
            """
        ).fetchall()
        lift_pass_ski_area_rows = connection.execute(
            """
            SELECT relationship.lift_pass_product_id,
                   relationship.ski_area_id, relationship.ordinal
            FROM lift_pass_ski_areas AS relationship
            JOIN lift_pass_products AS product
              ON product.lift_pass_product_id =
                 relationship.lift_pass_product_id
             AND product.is_active
            JOIN ski_areas AS ski_area
              ON ski_area.ski_area_id = relationship.ski_area_id
             AND ski_area.is_active
            ORDER BY relationship.lift_pass_product_id,
                     relationship.ordinal
            """
        ).fetchall()
        lift_pass_terrain_domain_rows = connection.execute(
            """
            SELECT relationship.lift_pass_product_id,
                   relationship.terrain_domain_id,
                   relationship.ordinal
            FROM lift_pass_terrain_domains AS relationship
            JOIN lift_pass_products AS product
              ON product.lift_pass_product_id =
                 relationship.lift_pass_product_id
             AND product.is_active
            JOIN terrain_domains AS terrain_domain
              ON terrain_domain.terrain_domain_id =
                 relationship.terrain_domain_id
             AND terrain_domain.is_active
            ORDER BY relationship.lift_pass_product_id,
                     relationship.ordinal
            """
        ).fetchall()
        lift_pass_stay_destination_rows = connection.execute(
            """
            SELECT relationship.lift_pass_product_id,
                   relationship.stay_destination_id,
                   relationship.ordinal, relationship.is_default
            FROM lift_pass_stay_destinations AS relationship
            JOIN lift_pass_products AS product
              ON product.lift_pass_product_id =
                 relationship.lift_pass_product_id
             AND product.is_active
            JOIN stay_destinations AS destination
              ON destination.stay_destination_id =
                 relationship.stay_destination_id
             AND destination.is_active
            ORDER BY relationship.lift_pass_product_id,
                     relationship.ordinal
            """
        ).fetchall()

    terrain_ski_areas = _group_relationships(
        terrain_domain_ski_area_rows,
        owner_column="terrain_domain_id",
        value_column="ski_area_id",
    )
    pass_ski_areas = _group_relationships(
        lift_pass_ski_area_rows,
        owner_column="lift_pass_product_id",
        value_column="ski_area_id",
    )
    pass_terrain_domains = _group_relationships(
        lift_pass_terrain_domain_rows,
        owner_column="lift_pass_product_id",
        value_column="terrain_domain_id",
    )
    pass_destinations = _group_relationships(
        lift_pass_stay_destination_rows,
        owner_column="lift_pass_product_id",
        value_column="stay_destination_id",
    )
    default_pass_destinations: dict[str, list[str]] = {}
    for relationship in lift_pass_stay_destination_rows:
        if relationship["is_default"]:
            default_pass_destinations.setdefault(
                relationship["lift_pass_product_id"], []
            ).append(relationship["stay_destination_id"])

    try:
        return CatalogSnapshot.model_validate(
            {
                "schema_version": 1,
                "ski_regions": [
                    {
                        "ski_region_id": row["ski_region_id"],
                        "name": row["name"],
                        "grouping_policy": row["grouping_policy"],
                        "parent_ski_region_id": row["parent_ski_region_id"],
                        "source_urls": _decode_json(
                            row,
                            "source_urls_json",
                            table_name="ski_regions",
                            default=[],
                        ),
                    }
                    for row in ski_region_rows
                ],
                "stay_destinations": [
                    {
                        "stay_destination_id": row["stay_destination_id"],
                        "name": row["name"],
                        "country": row["country"],
                        "region": row["region"],
                        "price_level": row["price_level"],
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                        "trip_market_region_id": row["trip_market_region_id"],
                        "atmosphere_tags": _decode_json(
                            row,
                            "atmosphere_tags_json",
                            table_name="stay_destinations",
                            default=[],
                        ),
                        "regional_data_ids": _decode_json(
                            row,
                            "regional_data_ids_json",
                            table_name="stay_destinations",
                            default={},
                        ),
                    }
                    for row in stay_destination_rows
                ],
                "stay_bases": [
                    {
                        "stay_base_id": row["stay_base_id"],
                        "stay_destination_id": row["stay_destination_id"],
                        "name": row["name"],
                        "price_range": row["price_range"],
                        "price_min": row["price_min"],
                        "price_max": row["price_max"],
                        "quality": row["quality"],
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                        "base_type": row["base_type"],
                        "atmosphere_tags": _decode_json(
                            row,
                            "atmosphere_tags_json",
                            table_name="stay_bases",
                            default=[],
                        ),
                        "regional_data_ids": _decode_json(
                            row,
                            "regional_data_ids_json",
                            table_name="stay_bases",
                            default={},
                        ),
                    }
                    for row in stay_base_rows
                ],
                "ski_areas": [
                    {
                        "ski_area_id": row["ski_area_id"],
                        "name": row["name"],
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                        "base_elevation_m": row["base_elevation_m"],
                        "summit_elevation_m": row["summit_elevation_m"],
                        "season_start_month": row["season_start_month"],
                        "season_end_month": row["season_end_month"],
                        "season_windows": _decode_json(
                            row,
                            "season_windows_json",
                            table_name="ski_areas",
                            default=[],
                        ),
                        "total_piste_km": row["total_piste_km"],
                        "total_lift_count": row["total_lift_count"],
                        "piste_km_by_difficulty": _decode_json(
                            row,
                            "piste_km_by_difficulty_json",
                            table_name="ski_areas",
                        ),
                        "supported_skill_levels": _decode_json(
                            row,
                            "supported_skill_levels_json",
                            table_name="ski_areas",
                            default=[],
                        ),
                    }
                    for row in ski_area_rows
                ],
                "ski_area_access": [
                    {
                        "ski_area_access_id": row["ski_area_access_id"],
                        "stay_base_id": row["stay_base_id"],
                        "ski_area_id": row["ski_area_id"],
                        "access_mode": row["access_mode"],
                        "lift_distance": row["lift_distance"],
                        "nearest_lift_name": row["nearest_lift_name"],
                        "distance_m": row["distance_m"],
                        "duration_minutes": row["duration_minutes"],
                        "is_direct": row["is_direct"],
                        "regional_data_ids": _decode_json(
                            row,
                            "regional_data_ids_json",
                            table_name="ski_area_access",
                            default={},
                        ),
                        "source_urls": _decode_json(
                            row,
                            "source_urls_json",
                            table_name="ski_area_access",
                        ),
                    }
                    for row in ski_area_access_rows
                ],
                "terrain_domains": [
                    {
                        "terrain_domain_id": row["terrain_domain_id"],
                        "name": row["name"],
                        "ski_area_ids": terrain_ski_areas.get(
                            row["terrain_domain_id"], []
                        ),
                        "metric_scope": row["metric_scope"],
                        "total_piste_km": row["total_piste_km"],
                        "total_lift_count": row["total_lift_count"],
                        "base_elevation_m": row["base_elevation_m"],
                        "summit_elevation_m": row["summit_elevation_m"],
                        "piste_km_by_difficulty": _decode_json(
                            row,
                            "piste_km_by_difficulty_json",
                            table_name="terrain_domains",
                        ),
                        "season_windows": _decode_json(
                            row,
                            "season_windows_json",
                            table_name="terrain_domains",
                            default=[],
                        ),
                        "source_urls": _decode_json(
                            row,
                            "source_urls_json",
                            table_name="terrain_domains",
                        ),
                    }
                    for row in terrain_domain_rows
                ],
                "lift_pass_products": [
                    {
                        "lift_pass_product_id": row["lift_pass_product_id"],
                        "name": row["name"],
                        "validity_scope": row["validity_scope"],
                        "available_from_stay_destination_ids": (
                            pass_destinations.get(row["lift_pass_product_id"], [])
                        ),
                        "default_for_stay_destination_ids": (
                            default_pass_destinations.get(
                                row["lift_pass_product_id"], []
                            )
                        ),
                        "valid_ski_area_ids": pass_ski_areas.get(
                            row["lift_pass_product_id"], []
                        ),
                        "terrain_domain_ids": pass_terrain_domains.get(
                            row["lift_pass_product_id"], []
                        ),
                        "external_validity_summary": row["external_validity_summary"],
                        "pass_accessible_terrain": _decode_json(
                            row,
                            "pass_accessible_terrain_json",
                            table_name="lift_pass_products",
                        ),
                        "prices": _decode_json(
                            row,
                            "prices_json",
                            table_name="lift_pass_products",
                            default=[],
                        ),
                    }
                    for row in lift_pass_product_rows
                ],
                "rental_display_facts": [dict(row) for row in rental_display_fact_rows],
            }
        )
    except CatalogRepositoryError:
        raise
    except ValidationError as error:
        raise CatalogRepositoryError(
            "normalized catalog graph failed validation"
        ) from error
