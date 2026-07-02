from app.data.catalog_schema import ensure_normalized_catalog_schema
from app.data.database import connect

NORMALIZED_TABLE_COLUMNS = {
    "ski_regions": {
        "ski_region_id",
        "name",
        "grouping_policy",
        "parent_ski_region_id",
        "source_urls_json",
        "is_active",
    },
    "stay_destinations": {
        "stay_destination_id",
        "name",
        "country",
        "region",
        "price_level",
        "latitude",
        "longitude",
        "trip_market_region_id",
        "atmosphere_tags_json",
        "regional_data_ids_json",
        "is_active",
    },
    "ski_area_access": {
        "ski_area_access_id",
        "stay_base_id",
        "ski_area_id",
        "access_mode",
        "lift_distance",
        "nearest_lift_name",
        "distance_m",
        "duration_minutes",
        "is_direct",
        "regional_data_ids_json",
        "source_urls_json",
        "is_active",
    },
    "terrain_domain_ski_areas": {
        "terrain_domain_id",
        "ski_area_id",
        "ordinal",
    },
    "lift_pass_products": {
        "lift_pass_product_id",
        "name",
        "validity_scope",
        "external_validity_summary",
        "pass_accessible_terrain_json",
        "prices_json",
        "is_active",
    },
    "lift_pass_ski_areas": {
        "lift_pass_product_id",
        "ski_area_id",
        "ordinal",
    },
    "lift_pass_terrain_domains": {
        "lift_pass_product_id",
        "terrain_domain_id",
        "ordinal",
    },
    "lift_pass_stay_destinations": {
        "lift_pass_product_id",
        "stay_destination_id",
        "ordinal",
        "is_default",
        "default_ordinal",
    },
    "rental_display_facts": {
        "rental_display_fact_id",
        "stay_destination_id",
        "stay_base_id",
        "name",
        "price_range",
        "price_min",
        "price_max",
        "quality",
        "lift_distance",
        "is_active",
    },
}


def _table_columns() -> dict[str, set[str]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            """
        ).fetchall()

    columns: dict[str, set[str]] = {}
    for row in rows:
        columns.setdefault(row["table_name"], set()).add(row["column_name"])
    return columns


def test_normalized_catalog_schema_has_expected_tables_and_keys() -> None:
    ensure_normalized_catalog_schema()
    columns = _table_columns()

    for table_name, expected_columns in NORMALIZED_TABLE_COLUMNS.items():
        assert expected_columns <= columns[table_name]

    assert "stay_destination_id" in columns["stay_bases"]
    assert "is_active" in columns["stay_bases"]
    assert "supported_skill_levels_json" in columns["ski_areas"]
    assert "is_active" in columns["terrain_domains"]

    with connect() as connection:
        ski_area_keys = connection.execute(
            """
            SELECT a.attname, i.indisprimary, i.indisunique
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = 'ski_areas'::regclass
              AND (i.indisprimary OR i.indisunique)
            """
        ).fetchall()
        stay_base_key = connection.execute(
            """
            SELECT 1
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = 'stay_bases'::regclass
              AND i.indisunique
              AND a.attname = 'stay_base_id'
            """
        ).fetchone()

    assert any(row["attname"] == "id" and row["indisprimary"] for row in ski_area_keys)
    assert any(
        row["attname"] == "ski_area_id" and row["indisunique"] for row in ski_area_keys
    )
    assert stay_base_key is not None


def test_normalized_schema_retains_legacy_catalog_owner_columns() -> None:
    ensure_normalized_catalog_schema()
    columns = _table_columns()

    assert "resorts" in columns
    assert "resort_id" in columns["ski_areas"]
    assert "resort_id" in columns["stay_bases"]
    assert "ski_area_refs_json" in columns["terrain_domains"]


def test_schema_upgrade_renames_evidence_keys_in_place_and_is_idempotent() -> None:
    with connect() as connection:
        connection.execute(
            "ALTER TABLE raw_weather_history RENAME COLUMN ski_area_id TO resort_id"
        )
        connection.execute(
            "ALTER TABLE resort_condition_history "
            "RENAME COLUMN ski_area_id TO resort_id"
        )
        connection.execute(
            """
            INSERT INTO raw_weather_history (
                resort_id, resort_name, elevation_band, elevation_m,
                observed_on, observed_at, snowfall_cm, snow_depth_m,
                temperature_2m_max_c, temperature_2m_min_c,
                wind_speed_10m_max_kmh, wind_gusts_10m_max_kmh,
                weather_code, record_type, source
            ) VALUES (
                'tignes-ski-area', 'Tignes', 'mid', 2500,
                '2024-03-05', '2024-03-05T12:00:00+00:00', 8, 1.3,
                -3, -9, 18, 24, 3, 'archive', 'open-meteo'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO resort_condition_history (
                resort_id, resort_name, observed_month, observed_at,
                snow_confidence_score, snow_confidence_label,
                availability_status, weather_summary, conditions_score, source
            ) VALUES (
                'tignes-ski-area', 'Tignes', 3, '2024-03-05T12:00:00+00:00',
                0.82, 'good', 'open', 'Fresh snow.', 0.76, 'open-meteo'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO resort_conditions (
                ski_area_id, resort_name, snow_confidence_score,
                snow_confidence_label, availability_status, weather_summary,
                conditions_score, updated_at, source
            ) VALUES (
                'tignes-ski-area', 'Tignes', 0.82, 'good', 'open',
                'Fresh snow.', 0.76, '2024-03-05T12:00:00+00:00', 'open-meteo'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO ski_area_snow_climatology_daily (
                ski_area_id, resort_name, elevation_band, elevation_m,
                month, day, baseline_period, baseline_start_year,
                baseline_end_year, evidence_seasons, latest_archive_year,
                snow_depth_cm_p25, snow_depth_cm_p50, snow_depth_cm_p75,
                prob_snow_depth_ge_30cm, prob_snow_depth_ge_50cm,
                avg_daily_snowfall_cm, prob_rain_risk, prob_freeze_thaw,
                avg_max_temperature_c, avg_wind_gust_kmh,
                avg_snow_confidence_score, avg_conditions_score,
                source_model, computed_at
            ) VALUES (
                'tignes-ski-area', 'Tignes', 'mid', 2500,
                3, 5, 'normal_30y', 1995, 2024, 30, 2024,
                80, 120, 160, 0.93, 0.87, 6.5, 0.07, 0.12,
                -2.4, 28, 0.82, 0.78, 'snowcast_empirical_v1',
                '2026-06-15T00:00:00+00:00'
            )
            """
        )
        before_rows = {
            table_name: connection.execute(
                f"SELECT id, resort_id AS ski_area_id FROM {table_name} ORDER BY id"
            ).fetchall()
            for table_name in (
                "raw_weather_history",
                "resort_condition_history",
            )
        }
        evidence_tables = (
            "raw_weather_history",
            "ski_area_snow_climatology_daily",
            "resort_conditions",
            "resort_condition_history",
        )
        before_counts = {
            table_name: connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name}"
            ).fetchone()["count"]
            for table_name in evidence_tables
        }

    ensure_normalized_catalog_schema()
    ensure_normalized_catalog_schema()

    columns = _table_columns()
    with connect() as connection:
        after_rows = {
            table_name: connection.execute(
                f"SELECT id, ski_area_id FROM {table_name} ORDER BY id"
            ).fetchall()
            for table_name in before_rows
        }
        after_counts = {
            table_name: connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name}"
            ).fetchone()["count"]
            for table_name in evidence_tables
        }

    assert "ski_area_id" in columns["raw_weather_history"]
    assert "resort_id" not in columns["raw_weather_history"]
    assert "ski_area_id" in columns["resort_condition_history"]
    assert "resort_id" not in columns["resort_condition_history"]
    assert after_rows == before_rows
    assert (
        after_counts
        == before_counts
        == {
            "raw_weather_history": 1,
            "ski_area_snow_climatology_daily": 1,
            "resort_conditions": 1,
            "resort_condition_history": 1,
        }
    )


def test_ski_area_evidence_foreign_keys_do_not_cascade_delete() -> None:
    ensure_normalized_catalog_schema()

    with connect() as connection:
        constraints = connection.execute(
            """
            SELECT source.relname AS table_name,
                   source_attribute.attname AS source_column,
                   target.relname AS target_table,
                   target_attribute.attname AS target_column,
                   constraint_row.confdeltype
            FROM pg_constraint constraint_row
            JOIN pg_class source ON source.oid = constraint_row.conrelid
            JOIN pg_class target ON target.oid = constraint_row.confrelid
            JOIN pg_attribute source_attribute
              ON source_attribute.attrelid = source.oid
             AND source_attribute.attnum = constraint_row.conkey[1]
            JOIN pg_attribute target_attribute
              ON target_attribute.attrelid = target.oid
             AND target_attribute.attnum = constraint_row.confkey[1]
            WHERE constraint_row.contype = 'f'
              AND source.relname IN (
                'raw_weather_history',
                'ski_area_snow_climatology_daily',
                'resort_conditions',
                'resort_condition_history'
              )
            ORDER BY source.relname
            """
        ).fetchall()

    assert {
        (
            row["table_name"],
            row["source_column"],
            row["target_table"],
            row["target_column"],
            row["confdeltype"],
        )
        for row in constraints
    } == {
        (
            "raw_weather_history",
            "ski_area_id",
            "ski_areas",
            "ski_area_id",
            "r",
        ),
        (
            "ski_area_snow_climatology_daily",
            "ski_area_id",
            "ski_areas",
            "ski_area_id",
            "r",
        ),
        (
            "resort_conditions",
            "ski_area_id",
            "ski_areas",
            "ski_area_id",
            "r",
        ),
        (
            "resort_condition_history",
            "ski_area_id",
            "ski_areas",
            "ski_area_id",
            "r",
        ),
    }
