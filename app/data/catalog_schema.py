from __future__ import annotations

from typing import Any

import psycopg
from psycopg import sql

from app.data.database import connect


def ensure_normalized_catalog_schema(database_url: str | None = None) -> None:
    with connect(database_url) as connection:
        from app.data.database import _create_schema

        _create_schema(connection)


def _ensure_normalized_catalog_schema(
    connection: psycopg.Connection[Any],
) -> None:
    _create_normalized_catalog_owner_tables(connection)
    _expand_legacy_catalog_tables(connection)
    _create_normalized_catalog_relationship_tables(connection)
    _rename_ski_area_evidence_keys(connection)
    _recreate_ski_area_evidence_keys_and_indexes(connection)
    _protect_ski_area_evidence_foreign_keys(connection)


def _create_normalized_catalog_owner_tables(
    connection: psycopg.Connection[Any],
) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ski_regions (
            ski_region_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            grouping_policy TEXT NOT NULL,
            parent_ski_region_id TEXT REFERENCES ski_regions(ski_region_id)
                ON DELETE RESTRICT,
            source_urls_json TEXT NOT NULL DEFAULT '[]',
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS stay_destinations (
            stay_destination_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            region TEXT NOT NULL,
            price_level TEXT NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            trip_market_region_id TEXT NOT NULL
                REFERENCES ski_regions(ski_region_id) ON DELETE RESTRICT,
            regional_data_ids_json TEXT NOT NULL DEFAULT '{}',
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS lift_pass_products (
            lift_pass_product_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            validity_scope TEXT NOT NULL,
            validity_windows_json TEXT NOT NULL DEFAULT '[]',
            external_validity_summary TEXT,
            pass_accessible_terrain_json TEXT,
            prices_json TEXT NOT NULL DEFAULT '[]',
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS rental_display_facts (
            rental_display_fact_id TEXT PRIMARY KEY,
            stay_destination_id TEXT NOT NULL
                REFERENCES stay_destinations(stay_destination_id)
                ON DELETE RESTRICT,
            stay_base_id TEXT,
            name TEXT NOT NULL,
            price_range TEXT NOT NULL,
            price_min DOUBLE PRECISION NOT NULL,
            price_max DOUBLE PRECISION NOT NULL,
            quality TEXT NOT NULL,
            lift_distance TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );
        """
    )


def _expand_legacy_catalog_tables(
    connection: psycopg.Connection[Any],
) -> None:
    connection.execute(
        """
        ALTER TABLE stay_bases
        ADD COLUMN IF NOT EXISTS stay_destination_id TEXT,
        ADD COLUMN IF NOT EXISTS elevation_m INTEGER,
        ADD COLUMN IF NOT EXISTS base_character_json TEXT NOT NULL DEFAULT
            '{"development_style":"unknown","local_pace":"unknown"}',
        ADD COLUMN IF NOT EXISTS local_apres_profile_json TEXT NOT NULL DEFAULT
            '{"availability":"unknown","intensity":null,"season_label":null}',
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

        ALTER TABLE ski_areas
        ADD COLUMN IF NOT EXISTS supported_skill_levels_json
            TEXT NOT NULL DEFAULT '[]',
        ADD COLUMN IF NOT EXISTS snowmaking_json TEXT NOT NULL DEFAULT
            '{"availability":"unknown","coverage_pct":null,"coverage_basis":"unknown","season_label":null}',
        ADD COLUMN IF NOT EXISTS glacier_terrain_json TEXT NOT NULL DEFAULT
            '{"availability":"unknown"}',
        ADD COLUMN IF NOT EXISTS snow_park_json TEXT NOT NULL DEFAULT
            '{"availability":"unknown","park_count":null,"season_label":null}',
        ADD COLUMN IF NOT EXISTS night_skiing_json TEXT NOT NULL DEFAULT
            '{"availability":"unknown","season_label":null}',
        ADD COLUMN IF NOT EXISTS marked_freeride_routes_json TEXT NOT NULL DEFAULT
            '{"availability":"unknown","route_count":null,"season_label":null}',
        ADD COLUMN IF NOT EXISTS official_trail_map_json TEXT,
        ADD COLUMN IF NOT EXISTS ski_day_apres_profile_json TEXT NOT NULL DEFAULT
            '{"availability":"unknown","intensity":null,"season_label":null}';

        ALTER TABLE terrain_domains
        ADD COLUMN IF NOT EXISTS official_trail_map_json TEXT,
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

        ALTER TABLE lift_pass_products
        ADD COLUMN IF NOT EXISTS validity_windows_json TEXT NOT NULL DEFAULT '[]';

        ALTER TABLE stay_destinations
        DROP COLUMN IF EXISTS atmosphere_tags_json;

        ALTER TABLE stay_bases
        DROP COLUMN IF EXISTS atmosphere_tags_json;
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS stay_bases_stay_base_id_key
        ON stay_bases (stay_base_id)
        """
    )
    _ensure_foreign_key(
        connection,
        table_name="stay_bases",
        column_name="stay_destination_id",
        constraint_name="stay_bases_stay_destination_id_fkey",
        target_table="stay_destinations",
        target_column="stay_destination_id",
        on_delete="RESTRICT",
    )


def _create_normalized_catalog_relationship_tables(
    connection: psycopg.Connection[Any],
) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ski_area_access (
            ski_area_access_id TEXT PRIMARY KEY,
            stay_base_id TEXT NOT NULL REFERENCES stay_bases(stay_base_id)
                ON DELETE RESTRICT,
            ski_area_id TEXT NOT NULL REFERENCES ski_areas(ski_area_id)
                ON DELETE RESTRICT,
            access_mode TEXT NOT NULL,
            lift_distance TEXT NOT NULL,
            nearest_lift_name TEXT,
            distance_m INTEGER,
            duration_minutes INTEGER,
            is_direct BOOLEAN NOT NULL,
            regional_data_ids_json TEXT NOT NULL DEFAULT '{}',
            source_urls_json TEXT NOT NULL DEFAULT '[]',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            UNIQUE (stay_base_id, ski_area_id)
        );

        CREATE TABLE IF NOT EXISTS terrain_domain_ski_areas (
            terrain_domain_id TEXT NOT NULL
                REFERENCES terrain_domains(terrain_domain_id)
                ON DELETE RESTRICT,
            ski_area_id TEXT NOT NULL REFERENCES ski_areas(ski_area_id)
                ON DELETE RESTRICT,
            ordinal INTEGER NOT NULL,
            PRIMARY KEY (terrain_domain_id, ski_area_id),
            UNIQUE (terrain_domain_id, ordinal)
        );

        CREATE TABLE IF NOT EXISTS lift_pass_ski_areas (
            lift_pass_product_id TEXT NOT NULL
                REFERENCES lift_pass_products(lift_pass_product_id)
                ON DELETE RESTRICT,
            ski_area_id TEXT NOT NULL REFERENCES ski_areas(ski_area_id)
                ON DELETE RESTRICT,
            ordinal INTEGER NOT NULL,
            PRIMARY KEY (lift_pass_product_id, ski_area_id),
            UNIQUE (lift_pass_product_id, ordinal)
        );

        CREATE TABLE IF NOT EXISTS lift_pass_terrain_domains (
            lift_pass_product_id TEXT NOT NULL
                REFERENCES lift_pass_products(lift_pass_product_id)
                ON DELETE RESTRICT,
            terrain_domain_id TEXT NOT NULL
                REFERENCES terrain_domains(terrain_domain_id)
                ON DELETE RESTRICT,
            ordinal INTEGER NOT NULL,
            PRIMARY KEY (lift_pass_product_id, terrain_domain_id),
            UNIQUE (lift_pass_product_id, ordinal)
        );

        CREATE TABLE IF NOT EXISTS lift_pass_stay_destinations (
            lift_pass_product_id TEXT NOT NULL
                REFERENCES lift_pass_products(lift_pass_product_id)
                ON DELETE RESTRICT,
            stay_destination_id TEXT NOT NULL
                REFERENCES stay_destinations(stay_destination_id)
                ON DELETE RESTRICT,
            ordinal INTEGER NOT NULL,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            default_ordinal INTEGER,
            PRIMARY KEY (lift_pass_product_id, stay_destination_id),
            UNIQUE (lift_pass_product_id, ordinal)
        );
        """
    )
    connection.execute(
        """
        ALTER TABLE lift_pass_stay_destinations
        ADD COLUMN IF NOT EXISTS default_ordinal INTEGER;

        CREATE UNIQUE INDEX IF NOT EXISTS
            lift_pass_stay_destinations_default_ordinal_key
        ON lift_pass_stay_destinations (
            lift_pass_product_id,
            default_ordinal
        )
        WHERE default_ordinal IS NOT NULL;
        """
    )
    _ensure_foreign_key(
        connection,
        table_name="rental_display_facts",
        column_name="stay_base_id",
        constraint_name="rental_display_facts_stay_base_id_fkey",
        target_table="stay_bases",
        target_column="stay_base_id",
        on_delete="RESTRICT",
    )


def _rename_ski_area_evidence_keys(
    connection: psycopg.Connection[Any],
) -> None:
    for table_name in ("raw_weather_history", "resort_condition_history"):
        connection.execute(
            sql.SQL(
                """
                DO $$
                BEGIN
                  IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = {table_name_literal}
                      AND column_name = 'resort_id'
                  ) AND NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = {table_name_literal}
                      AND column_name = 'ski_area_id'
                  ) THEN
                    ALTER TABLE {table_name}
                    RENAME COLUMN resort_id TO ski_area_id;
                  END IF;
                END $$;
                """
            ).format(
                table_name=sql.Identifier(table_name),
                table_name_literal=sql.Literal(table_name),
            )
        )


def _recreate_ski_area_evidence_keys_and_indexes(
    connection: psycopg.Connection[Any],
) -> None:
    connection.execute(
        """
        ALTER TABLE raw_weather_history
        DROP CONSTRAINT IF EXISTS raw_weather_history_resort_id_observed_on_source_key;
        ALTER TABLE raw_weather_history
        DROP CONSTRAINT IF EXISTS raw_weather_history_resort_band_observed_source_key;

        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'raw_weather_history_ski_area_band_observed_source_key'
              AND conrelid = 'raw_weather_history'::regclass
          ) THEN
            ALTER TABLE raw_weather_history
            ADD CONSTRAINT raw_weather_history_ski_area_band_observed_source_key
            UNIQUE (ski_area_id, elevation_band, observed_on, source);
          END IF;
        END $$;

        ALTER TABLE resort_condition_history
        DROP CONSTRAINT IF EXISTS resort_condition_history_resort_id_observed_at_key;

        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'resort_condition_history_ski_area_observed_at_key'
              AND conrelid = 'resort_condition_history'::regclass
          ) THEN
            ALTER TABLE resort_condition_history
            ADD CONSTRAINT resort_condition_history_ski_area_observed_at_key
            UNIQUE (ski_area_id, observed_at);
          END IF;
        END $$;

        DROP INDEX IF EXISTS raw_weather_history_search_window_idx;
        CREATE INDEX raw_weather_history_search_window_idx
        ON raw_weather_history (
            ski_area_id,
            elevation_band,
            record_type,
            observed_on
        );

        CREATE INDEX IF NOT EXISTS resort_condition_history_search_idx
        ON resort_condition_history (ski_area_id, observed_at);
        """
    )


def _protect_ski_area_evidence_foreign_keys(
    connection: psycopg.Connection[Any],
) -> None:
    for table_name in (
        "raw_weather_history",
        "ski_area_snow_climatology_daily",
        "resort_conditions",
        "resort_condition_history",
    ):
        _ensure_foreign_key(
            connection,
            table_name=table_name,
            column_name="ski_area_id",
            constraint_name=f"{table_name}_ski_area_id_fkey",
            target_table="ski_areas",
            target_column="ski_area_id",
            on_delete="RESTRICT",
        )


def _ensure_foreign_key(
    connection: psycopg.Connection[Any],
    *,
    table_name: str,
    column_name: str,
    constraint_name: str,
    target_table: str,
    target_column: str,
    on_delete: str,
) -> None:
    constraints = connection.execute(
        """
        SELECT constraint_row.conname,
               target.relname AS target_table,
               target_attribute.attname AS target_column,
               constraint_row.confdeltype
        FROM pg_constraint constraint_row
        JOIN pg_class source ON source.oid = constraint_row.conrelid
        JOIN pg_namespace source_namespace
          ON source_namespace.oid = source.relnamespace
        JOIN pg_class target ON target.oid = constraint_row.confrelid
        JOIN pg_attribute source_attribute
          ON source_attribute.attrelid = source.oid
         AND source_attribute.attnum = constraint_row.conkey[1]
        JOIN pg_attribute target_attribute
          ON target_attribute.attrelid = target.oid
         AND target_attribute.attnum = constraint_row.confkey[1]
        WHERE constraint_row.contype = 'f'
          AND source_namespace.nspname = current_schema()
          AND source.relname = %s
          AND array_length(constraint_row.conkey, 1) = 1
          AND source_attribute.attname = %s
        """,
        (table_name, column_name),
    ).fetchall()
    expected_delete_type = {"RESTRICT": "r", "CASCADE": "c"}[on_delete]
    canonical_exists = False
    for constraint in constraints:
        is_canonical = (
            constraint["conname"] == constraint_name
            and constraint["target_table"] == target_table
            and constraint["target_column"] == target_column
            and constraint["confdeltype"] == expected_delete_type
        )
        if is_canonical:
            canonical_exists = True
            continue
        connection.execute(
            sql.SQL("ALTER TABLE {} DROP CONSTRAINT {}").format(
                sql.Identifier(table_name),
                sql.Identifier(constraint["conname"]),
            )
        )

    if canonical_exists:
        return
    connection.execute(
        sql.SQL(
            "ALTER TABLE {} ADD CONSTRAINT {} FOREIGN KEY ({}) "
            "REFERENCES {} ({}) ON DELETE {}"
        ).format(
            sql.Identifier(table_name),
            sql.Identifier(constraint_name),
            sql.Identifier(column_name),
            sql.Identifier(target_table),
            sql.Identifier(target_column),
            sql.SQL(on_delete),
        )
    )
