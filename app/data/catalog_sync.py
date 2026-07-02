from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import psycopg

from app.data.database import _create_schema, connect
from app.data.repositories import clear_repository_caches
from app.domain.catalog import (
    CatalogSnapshot,
    LiftPassProduct,
    RentalDisplayFact,
    SkiArea,
    SkiAreaAccess,
    SkiRegion,
    StayBase,
    StayDestination,
    TerrainDomain,
)


@dataclass(frozen=True)
class CatalogSyncResult:
    ski_regions: int
    stay_destinations: int
    stay_bases: int
    ski_areas: int
    ski_area_access: int
    terrain_domains: int
    lift_pass_products: int
    rental_display_facts: int
    relationships: int

    @classmethod
    def from_snapshot(cls, snapshot: CatalogSnapshot) -> "CatalogSyncResult":
        return cls(
            ski_regions=len(snapshot.ski_regions),
            stay_destinations=len(snapshot.stay_destinations),
            stay_bases=len(snapshot.stay_bases),
            ski_areas=len(snapshot.ski_areas),
            ski_area_access=len(snapshot.ski_area_access),
            terrain_domains=len(snapshot.terrain_domains),
            lift_pass_products=len(snapshot.lift_pass_products),
            rental_display_facts=len(snapshot.rental_display_facts),
            relationships=sum(
                len(domain.ski_area_ids) for domain in snapshot.terrain_domains
            )
            + sum(
                len(product.valid_ski_area_ids)
                + len(product.terrain_domain_ids)
                + len(product.available_from_stay_destination_ids)
                for product in snapshot.lift_pass_products
            ),
        )


def sync_catalog_snapshot(
    snapshot: CatalogSnapshot,
    database_url: str | None = None,
) -> CatalogSyncResult:
    validated_snapshot = CatalogSnapshot.model_validate(snapshot)
    with connect(database_url) as connection:
        _create_schema(connection)
        _upsert_ski_regions(connection, validated_snapshot.ski_regions)
        _upsert_stay_destinations(connection, validated_snapshot.stay_destinations)
        _upsert_stay_bases(connection, validated_snapshot.stay_bases)
        _upsert_ski_areas_preserving_ids(
            connection,
            validated_snapshot.ski_areas,
        )
        _upsert_access(connection, validated_snapshot.ski_area_access)
        _upsert_terrain_domains(connection, validated_snapshot.terrain_domains)
        _upsert_passes(connection, validated_snapshot.lift_pass_products)
        _upsert_rentals(connection, validated_snapshot.rental_display_facts)
        _replace_relationships(connection, validated_snapshot)
        _retire_absent_entities(connection, validated_snapshot)
    clear_repository_caches()
    return CatalogSyncResult.from_snapshot(validated_snapshot)


def _json(value: Any) -> str:
    if isinstance(value, Mapping):
        value = dict(value)
    return json.dumps(value, sort_keys=True)


def _model_json(value: Any) -> str | None:
    if value is None:
        return None
    return _json(value.model_dump(mode="json"))


def _model_list_json(values: Any) -> str:
    return _json([value.model_dump(mode="json") for value in values])


def _upsert_ski_regions(
    connection: psycopg.Connection[Any],
    ski_regions: tuple[SkiRegion, ...],
) -> None:
    for region in ski_regions:
        connection.execute(
            """
            INSERT INTO ski_regions (
                ski_region_id, name, grouping_policy, parent_ski_region_id,
                source_urls_json, is_active
            ) VALUES (%s, %s, %s, NULL, %s, TRUE)
            ON CONFLICT (ski_region_id) DO UPDATE SET
                name = excluded.name,
                grouping_policy = excluded.grouping_policy,
                parent_ski_region_id = NULL,
                source_urls_json = excluded.source_urls_json,
                is_active = TRUE
            """,
            (
                region.ski_region_id,
                region.name,
                region.grouping_policy,
                _json(region.source_urls),
            ),
        )
    for region in ski_regions:
        if region.parent_ski_region_id is not None:
            connection.execute(
                """
                UPDATE ski_regions
                SET parent_ski_region_id = %s
                WHERE ski_region_id = %s
                """,
                (region.parent_ski_region_id, region.ski_region_id),
            )


def _upsert_stay_destinations(
    connection: psycopg.Connection[Any],
    stay_destinations: tuple[StayDestination, ...],
) -> None:
    for destination in stay_destinations:
        connection.execute(
            """
            INSERT INTO stay_destinations (
                stay_destination_id, name, country, region, price_level,
                latitude, longitude, trip_market_region_id,
                atmosphere_tags_json, regional_data_ids_json, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (stay_destination_id) DO UPDATE SET
                name = excluded.name,
                country = excluded.country,
                region = excluded.region,
                price_level = excluded.price_level,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                trip_market_region_id = excluded.trip_market_region_id,
                atmosphere_tags_json = excluded.atmosphere_tags_json,
                regional_data_ids_json = excluded.regional_data_ids_json,
                is_active = TRUE
            """,
            (
                destination.stay_destination_id,
                destination.name,
                destination.country,
                destination.region,
                destination.price_level,
                destination.latitude,
                destination.longitude,
                destination.trip_market_region_id,
                _json(destination.atmosphere_tags),
                _json(destination.regional_data_ids),
            ),
        )


def _upsert_stay_bases(
    connection: psycopg.Connection[Any],
    stay_bases: tuple[StayBase, ...],
) -> None:
    for stay_base in stay_bases:
        connection.execute(
            """
            INSERT INTO stay_bases (
                stay_base_id, stay_destination_id, name, price_range,
                price_min, price_max, quality, latitude, longitude, base_type,
                atmosphere_tags_json, regional_data_ids_json, is_active
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE
            )
            ON CONFLICT (stay_base_id) DO UPDATE SET
                stay_destination_id = excluded.stay_destination_id,
                name = excluded.name,
                price_range = excluded.price_range,
                price_min = excluded.price_min,
                price_max = excluded.price_max,
                quality = excluded.quality,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                base_type = excluded.base_type,
                atmosphere_tags_json = excluded.atmosphere_tags_json,
                regional_data_ids_json = excluded.regional_data_ids_json,
                is_active = TRUE
            """,
            (
                stay_base.stay_base_id,
                stay_base.stay_destination_id,
                stay_base.name,
                stay_base.price_range,
                stay_base.price_min,
                stay_base.price_max,
                stay_base.quality,
                stay_base.latitude,
                stay_base.longitude,
                stay_base.base_type,
                _json(stay_base.atmosphere_tags),
                _json(stay_base.regional_data_ids),
            ),
        )


def _upsert_ski_areas_preserving_ids(
    connection: psycopg.Connection[Any],
    ski_areas: tuple[SkiArea, ...],
) -> None:
    for ski_area in ski_areas:
        connection.execute(
            """
            INSERT INTO ski_areas (
                ski_area_id, name, latitude, longitude,
                base_elevation_m, summit_elevation_m, season_start_month,
                season_end_month, season_windows_json, total_piste_km,
                total_lift_count, piste_km_by_difficulty_json,
                supported_skill_levels_json, is_active
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                TRUE
            )
            ON CONFLICT (ski_area_id) DO UPDATE SET
                name = excluded.name,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                base_elevation_m = excluded.base_elevation_m,
                summit_elevation_m = excluded.summit_elevation_m,
                season_start_month = excluded.season_start_month,
                season_end_month = excluded.season_end_month,
                season_windows_json = excluded.season_windows_json,
                total_piste_km = excluded.total_piste_km,
                total_lift_count = excluded.total_lift_count,
                piste_km_by_difficulty_json = excluded.piste_km_by_difficulty_json,
                supported_skill_levels_json =
                    excluded.supported_skill_levels_json,
                is_active = TRUE
            """,
            (
                ski_area.ski_area_id,
                ski_area.name,
                ski_area.latitude,
                ski_area.longitude,
                ski_area.base_elevation_m,
                ski_area.summit_elevation_m,
                ski_area.season_start_month,
                ski_area.season_end_month,
                _model_list_json(ski_area.season_windows),
                ski_area.total_piste_km,
                ski_area.total_lift_count,
                _model_json(ski_area.piste_km_by_difficulty),
                _json(ski_area.supported_skill_levels),
            ),
        )


def _upsert_access(
    connection: psycopg.Connection[Any],
    accesses: tuple[SkiAreaAccess, ...],
) -> None:
    for access in accesses:
        connection.execute(
            """
            INSERT INTO ski_area_access (
                ski_area_access_id, stay_base_id, ski_area_id, access_mode,
                lift_distance, nearest_lift_name, distance_m,
                duration_minutes, is_direct, regional_data_ids_json,
                source_urls_json, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (ski_area_access_id) DO UPDATE SET
                stay_base_id = excluded.stay_base_id,
                ski_area_id = excluded.ski_area_id,
                access_mode = excluded.access_mode,
                lift_distance = excluded.lift_distance,
                nearest_lift_name = excluded.nearest_lift_name,
                distance_m = excluded.distance_m,
                duration_minutes = excluded.duration_minutes,
                is_direct = excluded.is_direct,
                regional_data_ids_json = excluded.regional_data_ids_json,
                source_urls_json = excluded.source_urls_json,
                is_active = TRUE
            """,
            (
                access.ski_area_access_id,
                access.stay_base_id,
                access.ski_area_id,
                access.access_mode,
                access.lift_distance,
                access.nearest_lift_name,
                access.distance_m,
                access.duration_minutes,
                access.is_direct,
                _json(access.regional_data_ids),
                _json(access.source_urls),
            ),
        )


def _upsert_terrain_domains(
    connection: psycopg.Connection[Any],
    terrain_domains: tuple[TerrainDomain, ...],
) -> None:
    for domain in terrain_domains:
        connection.execute(
            """
            INSERT INTO terrain_domains (
                terrain_domain_id, name, metric_scope, total_piste_km,
                total_lift_count, base_elevation_m,
                summit_elevation_m, piste_km_by_difficulty_json,
                season_windows_json, source_urls_json, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (terrain_domain_id) DO UPDATE SET
                name = excluded.name,
                metric_scope = excluded.metric_scope,
                total_piste_km = excluded.total_piste_km,
                total_lift_count = excluded.total_lift_count,
                base_elevation_m = excluded.base_elevation_m,
                summit_elevation_m = excluded.summit_elevation_m,
                piste_km_by_difficulty_json = excluded.piste_km_by_difficulty_json,
                season_windows_json = excluded.season_windows_json,
                source_urls_json = excluded.source_urls_json,
                is_active = TRUE
            """,
            (
                domain.terrain_domain_id,
                domain.name,
                domain.metric_scope,
                domain.total_piste_km,
                domain.total_lift_count,
                domain.base_elevation_m,
                domain.summit_elevation_m,
                _model_json(domain.piste_km_by_difficulty),
                _model_list_json(domain.season_windows),
                _json(domain.source_urls),
            ),
        )


def _upsert_passes(
    connection: psycopg.Connection[Any],
    lift_pass_products: tuple[LiftPassProduct, ...],
) -> None:
    for product in lift_pass_products:
        connection.execute(
            """
            INSERT INTO lift_pass_products (
                lift_pass_product_id, name, validity_scope,
                external_validity_summary, pass_accessible_terrain_json,
                prices_json, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (lift_pass_product_id) DO UPDATE SET
                name = excluded.name,
                validity_scope = excluded.validity_scope,
                external_validity_summary = excluded.external_validity_summary,
                pass_accessible_terrain_json =
                    excluded.pass_accessible_terrain_json,
                prices_json = excluded.prices_json,
                is_active = TRUE
            """,
            (
                product.lift_pass_product_id,
                product.name,
                product.validity_scope,
                product.external_validity_summary,
                _model_json(product.pass_accessible_terrain),
                _model_list_json(product.prices),
            ),
        )


def _upsert_rentals(
    connection: psycopg.Connection[Any],
    rentals: tuple[RentalDisplayFact, ...],
) -> None:
    for rental in rentals:
        connection.execute(
            """
            INSERT INTO rental_display_facts (
                rental_display_fact_id, stay_destination_id, stay_base_id,
                name, price_range, price_min, price_max, quality,
                lift_distance, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (rental_display_fact_id) DO UPDATE SET
                stay_destination_id = excluded.stay_destination_id,
                stay_base_id = excluded.stay_base_id,
                name = excluded.name,
                price_range = excluded.price_range,
                price_min = excluded.price_min,
                price_max = excluded.price_max,
                quality = excluded.quality,
                lift_distance = excluded.lift_distance,
                is_active = TRUE
            """,
            (
                rental.rental_display_fact_id,
                rental.stay_destination_id,
                rental.stay_base_id,
                rental.name,
                rental.price_range,
                rental.price_min,
                rental.price_max,
                rental.quality,
                rental.lift_distance,
            ),
        )


def _replace_relationships(
    connection: psycopg.Connection[Any],
    snapshot: CatalogSnapshot,
) -> None:
    connection.execute("DELETE FROM terrain_domain_ski_areas")
    connection.execute("DELETE FROM lift_pass_ski_areas")
    connection.execute("DELETE FROM lift_pass_terrain_domains")
    connection.execute("DELETE FROM lift_pass_stay_destinations")

    for domain in snapshot.terrain_domains:
        for ordinal, ski_area_id in enumerate(domain.ski_area_ids):
            connection.execute(
                """
                INSERT INTO terrain_domain_ski_areas (
                    terrain_domain_id, ski_area_id, ordinal
                ) VALUES (%s, %s, %s)
                """,
                (domain.terrain_domain_id, ski_area_id, ordinal),
            )
    for product in snapshot.lift_pass_products:
        for ordinal, ski_area_id in enumerate(product.valid_ski_area_ids):
            connection.execute(
                """
                INSERT INTO lift_pass_ski_areas (
                    lift_pass_product_id, ski_area_id, ordinal
                ) VALUES (%s, %s, %s)
                """,
                (product.lift_pass_product_id, ski_area_id, ordinal),
            )
        for ordinal, terrain_domain_id in enumerate(product.terrain_domain_ids):
            connection.execute(
                """
                INSERT INTO lift_pass_terrain_domains (
                    lift_pass_product_id, terrain_domain_id, ordinal
                ) VALUES (%s, %s, %s)
                """,
                (product.lift_pass_product_id, terrain_domain_id, ordinal),
            )
        default_destination_ids = set(product.default_for_stay_destination_ids)
        default_ordinals = {
            destination_id: ordinal
            for ordinal, destination_id in enumerate(
                product.default_for_stay_destination_ids
            )
        }
        for ordinal, destination_id in enumerate(
            product.available_from_stay_destination_ids
        ):
            connection.execute(
                """
                INSERT INTO lift_pass_stay_destinations (
                    lift_pass_product_id, stay_destination_id, ordinal,
                    is_default, default_ordinal
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    product.lift_pass_product_id,
                    destination_id,
                    ordinal,
                    destination_id in default_destination_ids,
                    default_ordinals.get(destination_id),
                ),
            )


def _retire_absent_entities(
    connection: psycopg.Connection[Any],
    snapshot: CatalogSnapshot,
) -> None:
    entity_ids = {
        "ski_regions": (
            "ski_region_id",
            [region.ski_region_id for region in snapshot.ski_regions],
        ),
        "stay_destinations": (
            "stay_destination_id",
            [
                destination.stay_destination_id
                for destination in snapshot.stay_destinations
            ],
        ),
        "stay_bases": (
            "stay_base_id",
            [stay_base.stay_base_id for stay_base in snapshot.stay_bases],
        ),
        "ski_areas": (
            "ski_area_id",
            [area.ski_area_id for area in snapshot.ski_areas],
        ),
        "ski_area_access": (
            "ski_area_access_id",
            [access.ski_area_access_id for access in snapshot.ski_area_access],
        ),
        "terrain_domains": (
            "terrain_domain_id",
            [domain.terrain_domain_id for domain in snapshot.terrain_domains],
        ),
        "lift_pass_products": (
            "lift_pass_product_id",
            [product.lift_pass_product_id for product in snapshot.lift_pass_products],
        ),
        "rental_display_facts": (
            "rental_display_fact_id",
            [rental.rental_display_fact_id for rental in snapshot.rental_display_facts],
        ),
    }
    for table_name, (id_column, active_ids) in entity_ids.items():
        if active_ids:
            connection.execute(
                f"UPDATE {table_name} SET is_active = FALSE "
                f"WHERE NOT ({id_column} = ANY(%s))",
                (active_ids,),
            )
        else:
            connection.execute(f"UPDATE {table_name} SET is_active = FALSE")
