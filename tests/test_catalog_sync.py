import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import psycopg
import pytest
from pydantic import ValidationError

from app.data import catalog_sync
from app.data.catalog_sync import sync_catalog_snapshot
from app.data.database import bootstrap_database, connect
from app.domain.catalog import CatalogSnapshot
from tests.test_catalog_models import minimal_catalog_payload

CATALOG_TABLE_ORDER = {
    "ski_regions": "ski_region_id",
    "stay_destinations": "stay_destination_id",
    "stay_bases": "id",
    "ski_areas": "id",
    "ski_area_access": "ski_area_access_id",
    "terrain_domains": "terrain_domain_id",
    "lift_pass_products": "lift_pass_product_id",
    "rental_display_facts": "rental_display_fact_id",
    "terrain_domain_ski_areas": "terrain_domain_id, ordinal",
    "lift_pass_ski_areas": "lift_pass_product_id, ordinal",
    "lift_pass_terrain_domains": "lift_pass_product_id, ordinal",
    "lift_pass_stay_destinations": "lift_pass_product_id, ordinal",
}


def complete_catalog_payload() -> dict[str, Any]:
    payload = deepcopy(minimal_catalog_payload())
    payload["ski_areas"].append(
        {
            **payload["ski_areas"][0],
            "ski_area_id": "other-area",
            "name": "Other Area",
        }
    )
    payload["ski_area_access"].append(
        {
            **payload["ski_area_access"][0],
            "ski_area_access_id": "example-village--other-area",
            "ski_area_id": "other-area",
        }
    )
    payload["terrain_domains"] = [
        {
            "terrain_domain_id": "example-domain",
            "name": "Example Domain",
            "ski_area_ids": ["example-area", "other-area"],
            "source_urls": ["https://www.example.com/domain"],
        }
    ]
    payload["lift_pass_products"][0].update(
        {
            "validity_scope": "local_multi_area",
            "valid_ski_area_ids": ["example-area", "other-area"],
            "terrain_domain_ids": ["example-domain"],
        }
    )
    payload["rental_display_facts"] = [
        {
            "rental_display_fact_id": "example-rental",
            "stay_destination_id": "example",
            "stay_base_id": "example-village",
            "name": "Example Rental",
            "price_range": "EUR 30-50",
            "price_min": 30,
            "price_max": 50,
            "quality": "standard",
            "lift_distance": "near",
        }
    ]
    return payload


def slim_catalog_payload() -> dict[str, Any]:
    payload = complete_catalog_payload()
    payload["ski_areas"] = payload["ski_areas"][:1]
    payload["ski_area_access"] = payload["ski_area_access"][:1]
    payload["terrain_domains"] = []
    payload["lift_pass_products"][0].update(
        {
            "validity_scope": "single_ski_area",
            "valid_ski_area_ids": ["example-area"],
            "terrain_domain_ids": [],
        }
    )
    return payload


def catalog_table_state() -> dict[str, list[dict[str, Any]]]:
    with connect() as connection:
        return {
            table_name: connection.execute(
                f"SELECT * FROM {table_name} ORDER BY {order_by}"
            ).fetchall()
            for table_name, order_by in CATALOG_TABLE_ORDER.items()
        }


def test_sync_catalog_writes_every_entity_type_and_relationship() -> None:
    snapshot = CatalogSnapshot.model_validate(complete_catalog_payload())

    result = sync_catalog_snapshot(snapshot)

    expected_active_counts = {
        "ski_regions": 1,
        "stay_destinations": 1,
        "stay_bases": 1,
        "ski_areas": 2,
        "ski_area_access": 2,
        "terrain_domains": 1,
        "lift_pass_products": 1,
        "rental_display_facts": 1,
    }
    expected_relationship_counts = {
        "terrain_domain_ski_areas": 2,
        "lift_pass_ski_areas": 2,
        "lift_pass_terrain_domains": 1,
        "lift_pass_stay_destinations": 1,
    }
    with connect() as connection:
        actual_active_counts = {
            table_name: connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name} WHERE is_active"
            ).fetchone()["count"]
            for table_name in expected_active_counts
        }
        actual_relationship_counts = {
            table_name: connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name}"
            ).fetchone()["count"]
            for table_name in expected_relationship_counts
        }
        normalized_stay_base_count = connection.execute(
            "SELECT COUNT(*) AS count FROM stay_bases "
            "WHERE stay_destination_id IS NOT NULL AND is_active"
        ).fetchone()["count"]

    assert actual_active_counts == expected_active_counts
    assert actual_relationship_counts == expected_relationship_counts
    assert normalized_stay_base_count == 1
    assert result.ski_areas == 2
    assert result.relationships == 6


def test_sync_is_idempotent() -> None:
    snapshot = CatalogSnapshot.model_validate(complete_catalog_payload())

    sync_catalog_snapshot(snapshot)
    first_state = catalog_table_state()
    sync_catalog_snapshot(snapshot)

    assert catalog_table_state() == first_state


def test_sync_retires_absent_ski_area_without_deleting_evidence() -> None:
    sync_catalog_snapshot(CatalogSnapshot.model_validate(complete_catalog_payload()))
    with connect() as connection:
        ski_area_row = connection.execute(
            "SELECT id FROM ski_areas WHERE ski_area_id = 'other-area'"
        ).fetchone()
        assert ski_area_row is not None
        connection.execute(
            """
            INSERT INTO raw_weather_history (
                ski_area_id, resort_name, elevation_band, elevation_m,
                observed_on, observed_at, snowfall_cm, snow_depth_m,
                temperature_2m_max_c, temperature_2m_min_c,
                wind_speed_10m_max_kmh, wind_gusts_10m_max_kmh,
                weather_code, record_type, source
            ) VALUES (
                'other-area', 'Other Area', 'mid', 1800,
                '2026-01-02', '2026-01-02T12:00:00+00:00', 5, 0.8,
                -2, -8, 15, 22, 3, 'archive', 'test-source'
            )
            """
        )

    sync_catalog_snapshot(CatalogSnapshot.model_validate(slim_catalog_payload()))

    with connect() as connection:
        retired_row = connection.execute(
            "SELECT id, is_active FROM ski_areas WHERE ski_area_id = 'other-area'"
        ).fetchone()
        evidence_count = connection.execute(
            "SELECT COUNT(*) AS count FROM raw_weather_history "
            "WHERE ski_area_id = 'other-area'"
        ).fetchone()["count"]

    assert retired_row == {"id": ski_area_row["id"], "is_active": False}
    assert evidence_count == 1


def test_sync_retires_absent_stay_base() -> None:
    payload = complete_catalog_payload()
    payload["stay_bases"].append(
        {
            **payload["stay_bases"][0],
            "stay_base_id": "other-village",
            "name": "Other Village",
        }
    )
    payload["ski_area_access"].append(
        {
            **payload["ski_area_access"][0],
            "ski_area_access_id": "other-village--example-area",
            "stay_base_id": "other-village",
        }
    )
    sync_catalog_snapshot(CatalogSnapshot.model_validate(payload))

    sync_catalog_snapshot(CatalogSnapshot.model_validate(complete_catalog_payload()))

    with connect() as connection:
        retired = connection.execute(
            "SELECT is_active FROM stay_bases WHERE stay_base_id = 'other-village'"
        ).fetchone()

    assert retired == {"is_active": False}


def test_sync_updates_metadata_without_changing_stable_database_id() -> None:
    initial = CatalogSnapshot.model_validate(minimal_catalog_payload())
    sync_catalog_snapshot(initial)
    with connect() as connection:
        before = connection.execute(
            "SELECT id FROM ski_areas WHERE ski_area_id = 'example-area'"
        ).fetchone()

    changed_payload = minimal_catalog_payload()
    changed_payload["ski_areas"][0]["name"] = "Renamed Example Area"
    sync_catalog_snapshot(CatalogSnapshot.model_validate(changed_payload))

    with connect() as connection:
        after = connection.execute(
            "SELECT id, name FROM ski_areas WHERE ski_area_id = 'example-area'"
        ).fetchone()

    assert before is not None
    assert after == {"id": before["id"], "name": "Renamed Example Area"}


def test_sync_replaces_relationships_with_exact_latest_state() -> None:
    first_payload = complete_catalog_payload()
    sync_catalog_snapshot(CatalogSnapshot.model_validate(first_payload))

    latest_payload = complete_catalog_payload()
    latest_payload["terrain_domains"][0]["ski_area_ids"] = [
        "other-area",
        "example-area",
    ]
    latest_payload["lift_pass_products"][0]["valid_ski_area_ids"] = ["other-area"]
    sync_catalog_snapshot(CatalogSnapshot.model_validate(latest_payload))

    with connect() as connection:
        domain_areas = connection.execute(
            "SELECT ski_area_id, ordinal FROM terrain_domain_ski_areas ORDER BY ordinal"
        ).fetchall()
        pass_areas = connection.execute(
            "SELECT ski_area_id, ordinal FROM lift_pass_ski_areas ORDER BY ordinal"
        ).fetchall()
        pass_domains = connection.execute(
            "SELECT terrain_domain_id, ordinal FROM lift_pass_terrain_domains "
            "ORDER BY ordinal"
        ).fetchall()
        pass_destinations = connection.execute(
            "SELECT stay_destination_id, ordinal, is_default, default_ordinal "
            "FROM lift_pass_stay_destinations ORDER BY ordinal"
        ).fetchall()

    assert domain_areas == [
        {"ski_area_id": "other-area", "ordinal": 0},
        {"ski_area_id": "example-area", "ordinal": 1},
    ]
    assert pass_areas == [{"ski_area_id": "other-area", "ordinal": 0}]
    assert pass_domains == [{"terrain_domain_id": "example-domain", "ordinal": 0}]
    assert pass_destinations == [
        {
            "stay_destination_id": "example",
            "ordinal": 0,
            "is_default": True,
            "default_ordinal": 0,
        }
    ]


def test_invalid_snapshot_is_rejected_before_catalog_mutation() -> None:
    valid_snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())
    sync_catalog_snapshot(valid_snapshot)
    before = catalog_table_state()
    invalid_access = valid_snapshot.ski_area_access[0].model_copy(
        update={"ski_area_id": "missing-area"}
    )
    invalid_snapshot = valid_snapshot.model_copy(
        update={"ski_area_access": (invalid_access,)}
    )

    with pytest.raises(ValidationError, match="unknown ski_area_id"):
        sync_catalog_snapshot(invalid_snapshot)

    assert catalog_table_state() == before


def test_sql_failure_rolls_back_all_changes_and_keeps_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial_snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())
    sync_catalog_snapshot(initial_snapshot)
    before = catalog_table_state()
    original_replace_relationships = catalog_sync._replace_relationships
    cache_clear_calls: list[None] = []

    def replace_relationships_then_fail(
        connection: psycopg.Connection[Any], snapshot: CatalogSnapshot
    ) -> None:
        original_replace_relationships(connection, snapshot)
        connection.execute(
            """
            INSERT INTO lift_pass_ski_areas (
                lift_pass_product_id, ski_area_id, ordinal
            ) VALUES ('missing-pass', 'example-area', 99)
            """
        )

    monkeypatch.setattr(
        catalog_sync,
        "_replace_relationships",
        replace_relationships_then_fail,
    )
    monkeypatch.setattr(
        catalog_sync,
        "clear_repository_caches",
        lambda: cache_clear_calls.append(None),
    )
    changed_payload = minimal_catalog_payload()
    changed_payload["ski_areas"][0]["name"] = "Must Roll Back"

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        sync_catalog_snapshot(CatalogSnapshot.model_validate(changed_payload))

    assert catalog_table_state() == before
    assert cache_clear_calls == []


def test_repository_caches_clear_after_successful_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    committed_names_seen_by_cache_clear: list[str] = []

    def observe_committed_catalog() -> None:
        with connect() as connection:
            row = connection.execute(
                "SELECT name FROM ski_areas WHERE ski_area_id = 'example-area'"
            ).fetchone()
        assert row is not None
        committed_names_seen_by_cache_clear.append(row["name"])

    monkeypatch.setattr(
        catalog_sync,
        "clear_repository_caches",
        observe_committed_catalog,
    )

    sync_catalog_snapshot(CatalogSnapshot.model_validate(minimal_catalog_payload()))

    assert committed_names_seen_by_cache_clear == ["Example Area"]


def test_bootstrap_database_syncs_an_explicit_normalized_catalog(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(complete_catalog_payload()), encoding="utf-8")

    bootstrap_database(catalog_path=catalog_path)

    with connect() as connection:
        active_area_ids = connection.execute(
            "SELECT ski_area_id FROM ski_areas WHERE is_active ORDER BY ski_area_id"
        ).fetchall()

    assert active_area_ids == [
        {"ski_area_id": "example-area"},
        {"ski_area_id": "other-area"},
    ]


def test_bootstrap_database_defaults_to_the_canonical_catalog() -> None:
    bootstrap_database()

    with connect() as connection:
        active_area_count = connection.execute(
            "SELECT COUNT(*) AS count FROM ski_areas WHERE is_active"
        ).fetchone()["count"]
        legacy_table = connection.execute(
            "SELECT to_regclass('public.resorts') AS table_name"
        ).fetchone()["table_name"]

    assert active_area_count > 0
    assert legacy_table is None
