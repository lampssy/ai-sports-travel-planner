import json
import re
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
import pytest
from pydantic import ValidationError

from app.data import catalog_repository
from app.data.catalog_loader import load_catalog
from app.data.catalog_repository import CatalogRepository, CatalogRepositoryError
from app.data.catalog_sync import sync_catalog_snapshot
from app.data.database import connect
from app.data.repositories import clear_repository_caches, get_catalog_repository
from app.domain.catalog import CatalogSnapshot
from tests.test_catalog_models import (
    add_second_destination_base_with_access,
    minimal_catalog_payload,
)
from tests.test_catalog_sync import complete_catalog_payload


class _RecordingConnection:
    def __init__(
        self,
        connection: psycopg.Connection[Any],
        statements: list[str],
    ) -> None:
        self._connection = connection
        self._statements = statements

    def execute(self, query: str, params: object | None = None) -> Any:
        self._statements.append(" ".join(str(query).split()))
        return self._connection.execute(query, params)


def test_catalog_repository_returns_active_normalized_snapshot() -> None:
    snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())
    sync_catalog_snapshot(snapshot)

    repository = CatalogRepository()
    loaded = repository.get_snapshot()

    assert loaded == snapshot
    assert loaded.ski_area_access[0].stay_base_id == "example-village"
    assert repository.get_stay_destination("example") == snapshot.stay_destinations[0]
    assert repository.get_stay_destination("missing") is None
    assert repository.get_ski_area("example-area") == snapshot.ski_areas[0]
    assert repository.get_ski_area("missing") is None


def test_catalog_repository_uses_one_query_per_entity_or_join_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_catalog_snapshot(CatalogSnapshot.model_validate(complete_catalog_payload()))
    statements: list[str] = []

    @contextmanager
    def recording_connect(
        database_url: str | None = None,
    ) -> Iterator[_RecordingConnection]:
        with connect(database_url) as connection:
            yield _RecordingConnection(connection, statements)

    monkeypatch.setattr(catalog_repository, "connect", recording_connect)

    CatalogRepository().get_snapshot()

    primary_tables = [
        match.group(1)
        for statement in statements
        if (match := re.search(r"\bFROM\s+(\w+)", statement, re.IGNORECASE))
    ]
    assert Counter(primary_tables) == Counter(
        {
            "ski_regions": 1,
            "stay_destinations": 1,
            "stay_bases": 1,
            "ski_areas": 1,
            "ski_area_access": 1,
            "terrain_domains": 1,
            "lift_pass_products": 1,
            "rental_display_facts": 1,
            "terrain_domain_ski_areas": 1,
            "lift_pass_ski_areas": 1,
            "lift_pass_terrain_domains": 1,
            "lift_pass_stay_destinations": 1,
        }
    )


def test_catalog_repository_preserves_relationship_ordinals_and_shared_access() -> None:
    payload = complete_catalog_payload()
    add_second_destination_base_with_access(payload)
    payload["terrain_domains"][0]["ski_area_ids"] = [
        "other-area",
        "example-area",
    ]
    payload["lift_pass_products"][0].update(
        {
            "available_from_stay_destination_ids": [
                "other-destination",
                "example",
            ],
            "default_for_stay_destination_ids": [
                "example",
                "other-destination",
            ],
            "valid_ski_area_ids": ["other-area", "example-area"],
            "terrain_domain_ids": ["example-domain"],
        }
    )
    snapshot = CatalogSnapshot.model_validate(payload)
    sync_catalog_snapshot(snapshot)

    loaded = CatalogRepository().get_snapshot()

    assert loaded == snapshot
    assert loaded.terrain_domains[0].ski_area_ids == (
        "other-area",
        "example-area",
    )
    assert loaded.lift_pass_products[0].available_from_stay_destination_ids == (
        "other-destination",
        "example",
    )
    assert loaded.lift_pass_products[0].default_for_stay_destination_ids == (
        "example",
        "other-destination",
    )
    assert [
        access.stay_base_id
        for access in loaded.ski_area_access
        if access.ski_area_id == "example-area"
    ] == ["example-village", "other-village"]


def test_catalog_repository_excludes_inactive_stay_bases_and_their_access() -> None:
    payload = minimal_catalog_payload()
    add_second_destination_base_with_access(payload)
    sync_catalog_snapshot(CatalogSnapshot.model_validate(payload))
    with connect() as connection:
        connection.execute(
            "UPDATE stay_bases SET is_active = FALSE "
            "WHERE stay_base_id = 'other-village'"
        )

    loaded = CatalogRepository().get_snapshot()

    assert [stay_base.stay_base_id for stay_base in loaded.stay_bases] == [
        "example-village"
    ]
    assert [access.ski_area_access_id for access in loaded.ski_area_access] == [
        "example-village--example-area"
    ]


def test_catalog_repository_normalizes_optional_json_nulls_to_typed_defaults() -> None:
    sync_catalog_snapshot(CatalogSnapshot.model_validate(minimal_catalog_payload()))
    with connect() as connection:
        connection.execute("UPDATE ski_regions SET source_urls_json = 'null'")
        connection.execute(
            "UPDATE stay_destinations SET atmosphere_tags_json = 'null', "
            "regional_data_ids_json = 'null'"
        )
        connection.execute(
            "UPDATE stay_bases SET atmosphere_tags_json = 'null', "
            "regional_data_ids_json = 'null'"
        )
        connection.execute(
            "UPDATE ski_areas SET season_windows_json = 'null', "
            "supported_skill_levels_json = 'null'"
        )
        connection.execute("UPDATE ski_area_access SET regional_data_ids_json = 'null'")
        connection.execute("UPDATE lift_pass_products SET prices_json = 'null'")

    loaded = CatalogRepository().get_snapshot()

    assert loaded.ski_regions[0].source_urls == ()
    assert loaded.stay_destinations[0].atmosphere_tags == ()
    assert dict(loaded.stay_destinations[0].regional_data_ids) == {}
    assert loaded.stay_bases[0].atmosphere_tags == ()
    assert dict(loaded.stay_bases[0].regional_data_ids) == {}
    assert loaded.ski_areas[0].season_windows == ()
    assert loaded.ski_areas[0].supported_skill_levels == ()
    assert dict(loaded.ski_area_access[0].regional_data_ids) == {}
    assert loaded.lift_pass_products[0].prices == ()
    assert loaded.lift_pass_products[0].pass_accessible_terrain is None


def test_catalog_repository_raises_explicit_error_for_malformed_json() -> None:
    sync_catalog_snapshot(CatalogSnapshot.model_validate(minimal_catalog_payload()))
    with connect() as connection:
        connection.execute("UPDATE stay_destinations SET atmosphere_tags_json = '{'")

    with pytest.raises(
        CatalogRepositoryError,
        match=r"stay_destinations\.atmosphere_tags_json",
    ) as error:
        CatalogRepository().get_snapshot()

    assert isinstance(error.value.__cause__, json.JSONDecodeError)


def test_catalog_repository_raises_explicit_error_for_invalid_rows() -> None:
    sync_catalog_snapshot(CatalogSnapshot.model_validate(minimal_catalog_payload()))
    with connect() as connection:
        connection.execute(
            "UPDATE stay_destinations SET price_level = 'not-a-price-level'"
        )

    with pytest.raises(
        CatalogRepositoryError,
        match="normalized catalog graph failed validation",
    ) as error:
        CatalogRepository().get_snapshot()

    assert isinstance(error.value.__cause__, ValidationError)


def test_catalog_repository_caches_per_instance_until_global_clear() -> None:
    sync_catalog_snapshot(CatalogSnapshot.model_validate(minimal_catalog_payload()))
    repository = get_catalog_repository()
    initial_snapshot = repository.get_snapshot()
    with connect() as connection:
        connection.execute(
            "UPDATE ski_areas SET name = 'Updated Area' "
            "WHERE ski_area_id = 'example-area'"
        )

    assert repository.get_snapshot() is initial_snapshot
    assert repository.get_ski_area("example-area").name == "Example Area"

    clear_repository_caches()
    assert repository.get_ski_area("example-area").name == "Updated Area"
    refreshed_repository = get_catalog_repository()

    assert refreshed_repository is not repository
    assert refreshed_repository.get_ski_area("example-area").name == "Updated Area"


def test_catalog_repository_rejects_an_invalid_active_graph() -> None:
    payload = minimal_catalog_payload()
    sync_catalog_snapshot(CatalogSnapshot.model_validate(payload))
    with connect() as connection:
        connection.execute("UPDATE stay_bases SET is_active = FALSE")

    with pytest.raises(CatalogRepositoryError) as error:
        CatalogRepository().get_snapshot()

    assert isinstance(error.value.__cause__, ValidationError)


def test_select_active_ski_areas_selects_an_exact_area() -> None:
    selected = catalog_repository.select_active_ski_areas(
        load_catalog(),
        ski_area_ids=("grands-montets",),
    )

    assert tuple(area.ski_area_id for area in selected) == ("grands-montets",)


def test_select_active_ski_areas_resolves_destination_access_without_duplicates() -> (
    None
):
    selected = catalog_repository.select_active_ski_areas(
        load_catalog(),
        stay_destination_ids=("chamonix-mont-blanc",),
    )

    assert tuple(area.ski_area_id for area in selected) == (
        "balme-le-tour-vallorcine",
        "brevent-flegere",
        "grands-montets",
        "les-houches-saint-gervais",
    )


def test_select_active_ski_areas_resolves_single_area_destination() -> None:
    selected = catalog_repository.select_active_ski_areas(
        load_catalog(),
        stay_destination_ids=("pinzolo",),
    )

    assert tuple(area.ski_area_id for area in selected) == ("pinzolo-ski-area",)


def test_select_active_ski_areas_without_targets_selects_every_area() -> None:
    snapshot = load_catalog()

    selected = catalog_repository.select_active_ski_areas(snapshot)

    assert tuple(area.ski_area_id for area in selected) == tuple(
        sorted(area.ski_area_id for area in snapshot.ski_areas)
    )


def test_select_active_ski_areas_rejects_unknown_targets() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"unknown catalog targets: areas=\['missing-area'\], "
            r"stay_destinations=\['missing-destination'\]"
        ),
    ):
        catalog_repository.select_active_ski_areas(
            load_catalog(),
            ski_area_ids=("missing-area",),
            stay_destination_ids=("missing-destination",),
        )
