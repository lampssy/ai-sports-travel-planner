from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.catalog import CatalogSnapshot


def minimal_catalog_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ski_regions": [
            {
                "ski_region_id": "example",
                "name": "Example Valley",
                "grouping_policy": "trip_market",
            }
        ],
        "stay_destinations": [
            {
                "stay_destination_id": "example",
                "name": "Example",
                "country": "France",
                "region": "Savoie",
                "price_level": "medium",
                "latitude": 45.0,
                "longitude": 6.0,
                "trip_market_region_id": "example",
            }
        ],
        "stay_bases": [
            {
                "stay_base_id": "example-village",
                "stay_destination_id": "example",
                "name": "Example Village",
                "price_range": "EUR 150-220",
                "price_min": 150,
                "price_max": 220,
                "quality": "standard",
            }
        ],
        "ski_areas": [
            {
                "ski_area_id": "example-area",
                "name": "Example Area",
                "latitude": 45.01,
                "longitude": 6.01,
                "base_elevation_m": 1200,
                "summit_elevation_m": 2400,
                "season_start_month": 12,
                "season_end_month": 4,
                "supported_skill_levels": ["intermediate"],
            }
        ],
        "ski_area_access": [
            {
                "ski_area_access_id": "example-village--example-area",
                "stay_base_id": "example-village",
                "ski_area_id": "example-area",
                "access_mode": "walk",
                "lift_distance": "near",
                "nearest_lift_name": "Example Gondola",
                "distance_m": 300,
                "is_direct": True,
                "source_urls": ["https://www.openstreetmap.org/way/1"],
            }
        ],
        "terrain_domains": [],
        "lift_pass_products": [
            {
                "lift_pass_product_id": "example-local-pass",
                "name": "Example Local Pass",
                "validity_scope": "single_ski_area",
                "available_from_stay_destination_ids": ["example"],
                "default_for_stay_destination_ids": ["example"],
                "valid_ski_area_ids": ["example-area"],
                "terrain_domain_ids": [],
                "prices": [],
            }
        ],
        "rental_display_facts": [],
    }


def add_second_destination(payload: dict[str, Any]) -> None:
    destination = deepcopy(payload["stay_destinations"][0])
    destination["stay_destination_id"] = "other-destination"
    destination["name"] = "Other Destination"
    payload["stay_destinations"].append(destination)


def add_second_destination_base_with_access(payload: dict[str, Any]) -> None:
    add_second_destination(payload)
    payload["stay_bases"].append(
        {
            "stay_base_id": "other-village",
            "stay_destination_id": "other-destination",
            "name": "Other Village",
            "price_range": "EUR 120-180",
            "price_min": 120,
            "price_max": 180,
            "quality": "standard",
        }
    )
    access = deepcopy(payload["ski_area_access"][0])
    access["ski_area_access_id"] = "other-village--example-area"
    access["stay_base_id"] = "other-village"
    payload["ski_area_access"].append(access)


def add_second_ski_area_with_access(payload: dict[str, Any]) -> None:
    ski_area = deepcopy(payload["ski_areas"][0])
    ski_area["ski_area_id"] = "other-area"
    ski_area["name"] = "Other Area"
    payload["ski_areas"].append(ski_area)

    access = deepcopy(payload["ski_area_access"][0])
    access["ski_area_access_id"] = "example-village--other-area"
    access["ski_area_id"] = "other-area"
    payload["ski_area_access"].append(access)


def add_terrain_domain(payload: dict[str, Any]) -> None:
    add_second_ski_area_with_access(payload)
    payload["terrain_domains"].append(
        {
            "terrain_domain_id": "example-domain",
            "name": "Example Domain",
            "ski_area_ids": ["example-area", "other-area"],
            "source_urls": ["https://www.example.com/domain"],
        }
    )


def example_rental() -> dict[str, Any]:
    return {
        "rental_display_fact_id": "example-rental",
        "stay_destination_id": "example",
        "name": "Example Rental",
        "price_range": "EUR 30-50",
        "price_min": 30,
        "price_max": 50,
        "quality": "standard",
        "lift_distance": "near",
    }


def test_catalog_snapshot_accepts_a_complete_graph() -> None:
    snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())

    assert snapshot.schema_version == 1
    assert snapshot.stay_destinations[0].trip_market_region_id == "example"


@pytest.mark.parametrize(
    ("collection_name", "id_field"),
    [
        ("ski_regions", "ski_region_id"),
        ("stay_destinations", "stay_destination_id"),
        ("stay_bases", "stay_base_id"),
        ("ski_areas", "ski_area_id"),
        ("ski_area_access", "ski_area_access_id"),
        ("lift_pass_products", "lift_pass_product_id"),
    ],
)
def test_catalog_rejects_duplicate_ids(collection_name: str, id_field: str) -> None:
    payload = minimal_catalog_payload()
    entity = deepcopy(payload[collection_name][0])
    payload[collection_name].append(entity)

    with pytest.raises(
        ValidationError,
        match=rf"duplicate {id_field}: {entity[id_field]}",
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_duplicate_terrain_domain_ids() -> None:
    payload = minimal_catalog_payload()
    domain = {
        "terrain_domain_id": "example-domain",
        "name": "Example Domain",
        "ski_area_ids": ["example-area", "other-area"],
        "source_urls": ["https://www.example.com/domain"],
    }
    payload["terrain_domains"] = [domain, deepcopy(domain)]

    with pytest.raises(
        ValidationError,
        match="duplicate terrain_domain_id: example-domain",
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_duplicate_rental_display_fact_ids() -> None:
    payload = minimal_catalog_payload()
    rental = {
        "rental_display_fact_id": "example-rental",
        "stay_destination_id": "example",
        "name": "Example Rental",
        "price_range": "EUR 30-50",
        "price_min": 30,
        "price_max": 50,
        "quality": "standard",
        "lift_distance": "near",
    }
    payload["rental_display_facts"] = [rental, deepcopy(rental)]

    with pytest.raises(
        ValidationError,
        match="duplicate rental_display_fact_id: example-rental",
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_unknown_region_parent() -> None:
    payload = minimal_catalog_payload()
    payload["ski_regions"][0]["parent_ski_region_id"] = "missing-region"

    with pytest.raises(
        ValidationError,
        match=(
            "unknown parent_ski_region_id: missing-region for ski_region_id: example"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_region_parent_cycle() -> None:
    payload = minimal_catalog_payload()
    payload["ski_regions"][0]["parent_ski_region_id"] = "regional-network"
    payload["ski_regions"].append(
        {
            "ski_region_id": "regional-network",
            "name": "Regional Network",
            "grouping_policy": "regional_network",
            "parent_ski_region_id": "example",
        }
    )

    with pytest.raises(
        ValidationError,
        match="ski region parent cycle: example -> regional-network -> example",
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_unknown_trip_market_region() -> None:
    payload = minimal_catalog_payload()
    payload["stay_destinations"][0]["trip_market_region_id"] = "missing-region"

    with pytest.raises(
        ValidationError,
        match=(
            "unknown trip_market_region_id: missing-region "
            "for stay_destination_id: example"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_destination_without_trip_market_region() -> None:
    payload = minimal_catalog_payload()
    payload["ski_regions"][0]["grouping_policy"] = "regional_network"

    with pytest.raises(
        ValidationError,
        match=(
            "stay_destination_id example must reference a trip_market ski region: "
            "example"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_unknown_base_destination() -> None:
    payload = minimal_catalog_payload()
    payload["stay_bases"][0]["stay_destination_id"] = "missing-destination"

    with pytest.raises(
        ValidationError,
        match=(
            "unknown stay_destination_id: missing-destination "
            "for stay_base_id: example-village"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_unknown_access_base() -> None:
    payload = minimal_catalog_payload()
    payload["ski_area_access"][0]["stay_base_id"] = "missing-base"

    with pytest.raises(
        ValidationError,
        match=(
            "unknown stay_base_id: missing-base for ski_area_access_id: "
            "example-village--example-area"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_unknown_access_ski_area() -> None:
    payload = minimal_catalog_payload()
    payload["ski_area_access"][0]["ski_area_id"] = "missing-area"

    with pytest.raises(
        ValidationError,
        match=(
            "unknown ski_area_id: missing-area for ski_area_access_id: "
            "example-village--example-area"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_duplicate_access_pair() -> None:
    payload = minimal_catalog_payload()
    duplicate_access = deepcopy(payload["ski_area_access"][0])
    duplicate_access["ski_area_access_id"] = "duplicate-access"
    payload["ski_area_access"].append(duplicate_access)

    with pytest.raises(
        ValidationError,
        match=(
            "duplicate ski area access pair: stay_base_id example-village, "
            "ski_area_id example-area"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_inaccessible_base() -> None:
    payload = minimal_catalog_payload()
    payload["stay_bases"].append(
        {
            "stay_base_id": "inaccessible-village",
            "stay_destination_id": "example",
            "name": "Inaccessible Village",
            "price_range": "EUR 100-150",
            "price_min": 100,
            "price_max": 150,
            "quality": "budget",
        }
    )

    with pytest.raises(
        ValidationError,
        match="stay_base_id has no ski area access: inaccessible-village",
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_inaccessible_ski_area() -> None:
    payload = minimal_catalog_payload()
    payload["ski_areas"].append(
        {
            "ski_area_id": "inaccessible-area",
            "name": "Inaccessible Area",
            "latitude": 45.02,
            "longitude": 6.02,
            "base_elevation_m": 1300,
            "summit_elevation_m": 2300,
            "season_start_month": 12,
            "season_end_month": 4,
            "supported_skill_levels": ["advanced"],
        }
    )

    with pytest.raises(
        ValidationError,
        match="ski_area_id has no stay-base access: inaccessible-area",
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_unknown_terrain_domain_ski_area() -> None:
    payload = minimal_catalog_payload()
    payload["terrain_domains"] = [
        {
            "terrain_domain_id": "example-domain",
            "name": "Example Domain",
            "ski_area_ids": ["example-area", "missing-area"],
            "source_urls": ["https://www.example.com/domain"],
        }
    ]

    with pytest.raises(
        ValidationError,
        match=(
            "unknown ski_area_id: missing-area for terrain_domain_id: example-domain"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "missing_id", "error_label"),
    [
        (
            "available_from_stay_destination_ids",
            "missing-destination",
            "available stay_destination_id",
        ),
        (
            "default_for_stay_destination_ids",
            "missing-destination",
            "default stay_destination_id",
        ),
        ("valid_ski_area_ids", "missing-area", "valid ski_area_id"),
        ("terrain_domain_ids", "missing-domain", "terrain_domain_id"),
    ],
)
def test_catalog_rejects_unknown_pass_references(
    field_name: str, missing_id: str, error_label: str
) -> None:
    payload = minimal_catalog_payload()
    payload["lift_pass_products"][0][field_name] = [missing_id]

    with pytest.raises(
        ValidationError,
        match=(
            rf"unknown {error_label}: {missing_id} for lift_pass_product_id: "
            "example-local-pass"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_accepts_pass_coverage_through_terrain_domain() -> None:
    payload = minimal_catalog_payload()
    add_terrain_domain(payload)
    lift_pass = payload["lift_pass_products"][0]
    lift_pass["validity_scope"] = "local_multi_area"
    lift_pass["valid_ski_area_ids"] = []
    lift_pass["terrain_domain_ids"] = ["example-domain"]

    snapshot = CatalogSnapshot.model_validate(payload)

    assert snapshot.lift_pass_products[0].terrain_domain_ids == ["example-domain"]


def test_catalog_rejects_pass_without_terrain_coverage() -> None:
    payload = minimal_catalog_payload()
    payload["lift_pass_products"][0]["valid_ski_area_ids"] = []

    with pytest.raises(
        ValidationError,
        match=(
            "lift_pass_product_id example-local-pass must cover at least one "
            "ski area or terrain domain"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_invalid_single_area_pass_shape() -> None:
    payload = minimal_catalog_payload()
    add_second_ski_area_with_access(payload)
    payload["lift_pass_products"][0]["valid_ski_area_ids"] = [
        "example-area",
        "other-area",
    ]

    with pytest.raises(
        ValidationError,
        match=(
            "single_ski_area lift_pass_product_id example-local-pass requires "
            "exactly one direct valid_ski_area_id and no terrain_domain_ids"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_single_area_pass_with_terrain_domain() -> None:
    payload = minimal_catalog_payload()
    add_terrain_domain(payload)
    payload["lift_pass_products"][0]["terrain_domain_ids"] = ["example-domain"]

    with pytest.raises(
        ValidationError,
        match=(
            "single_ski_area lift_pass_product_id example-local-pass requires "
            "exactly one direct valid_ski_area_id and no terrain_domain_ids"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_default_pass_where_product_is_not_available() -> None:
    payload = minimal_catalog_payload()
    add_second_destination(payload)
    payload["lift_pass_products"][0]["default_for_stay_destination_ids"] = [
        "other-destination"
    ]

    with pytest.raises(
        ValidationError,
        match=(
            "default stay_destination_id other-destination is not available for "
            "lift_pass_product_id example-local-pass"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_multiple_default_passes_for_destination() -> None:
    payload = minimal_catalog_payload()
    second_pass = deepcopy(payload["lift_pass_products"][0])
    second_pass["lift_pass_product_id"] = "example-second-pass"
    second_pass["name"] = "Example Second Pass"
    payload["lift_pass_products"].append(second_pass)

    with pytest.raises(
        ValidationError,
        match=(
            "stay_destination_id example has multiple default lift passes: "
            "example-local-pass, example-second-pass"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_unknown_rental_destination() -> None:
    payload = minimal_catalog_payload()
    rental = example_rental()
    rental["stay_destination_id"] = "missing-destination"
    payload["rental_display_facts"] = [rental]

    with pytest.raises(
        ValidationError,
        match=(
            "unknown stay_destination_id: missing-destination for "
            "rental_display_fact_id: example-rental"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_unknown_rental_base() -> None:
    payload = minimal_catalog_payload()
    rental = example_rental()
    rental["stay_base_id"] = "missing-base"
    payload["rental_display_facts"] = [rental]

    with pytest.raises(
        ValidationError,
        match=(
            "unknown stay_base_id: missing-base for rental_display_fact_id: "
            "example-rental"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_rental_base_owned_by_another_destination() -> None:
    payload = minimal_catalog_payload()
    add_second_destination_base_with_access(payload)
    rental = example_rental()
    rental["stay_base_id"] = "other-village"
    payload["rental_display_facts"] = [rental]

    with pytest.raises(
        ValidationError,
        match=(
            "rental_display_fact_id example-rental references stay_base_id "
            "other-village owned by stay_destination_id other-destination, not "
            "example"
        ),
    ):
        CatalogSnapshot.model_validate(payload)


@pytest.mark.parametrize(
    "source_owner",
    ["ski_region", "ski_area_access", "terrain_domain", "pass_metrics", "price"],
)
def test_catalog_rejects_invalid_or_non_direct_source_urls(
    source_owner: str,
) -> None:
    payload = minimal_catalog_payload()
    invalid_url = "https://localhost/catalog-source"

    if source_owner == "ski_region":
        payload["ski_regions"][0]["source_urls"] = [invalid_url]
    elif source_owner == "ski_area_access":
        payload["ski_area_access"][0]["source_urls"] = [invalid_url]
    elif source_owner == "terrain_domain":
        add_terrain_domain(payload)
        payload["terrain_domains"][0]["source_urls"] = [invalid_url]
    elif source_owner == "pass_metrics":
        payload["lift_pass_products"][0]["pass_accessible_terrain"] = {
            "source_urls": [invalid_url]
        }
    else:
        payload["lift_pass_products"][0]["prices"] = [
            {
                "duration_days": 1,
                "audience": "adult",
                "amount": 100,
                "currency": "EUR",
                "price_kind": "fixed",
                "source_url": invalid_url,
            }
        ]

    with pytest.raises(
        ValidationError,
        match=r"must be a direct external HTTP\(S\) URL",
    ):
        CatalogSnapshot.model_validate(payload)


def test_catalog_normalizes_direct_source_urls() -> None:
    payload = minimal_catalog_payload()
    payload["ski_area_access"][0]["source_urls"] = [
        "  https://www.example.com/access  "
    ]

    snapshot = CatalogSnapshot.model_validate(payload)

    assert snapshot.ski_area_access[0].source_urls == ["https://www.example.com/access"]
