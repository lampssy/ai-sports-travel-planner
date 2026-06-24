import json
from pathlib import Path

import pytest

from app.data.loader import load_resorts_from_path, load_terrain_domains_from_path
from app.data.validate_resort_catalog import CatalogValidationError, validate_catalog
from app.domain.models import StayBase


def _valid_resort_payload() -> list[dict]:
    return [
        {
            "resort_id": "test-resort",
            "name": "Test Resort",
            "country": "France",
            "region": "Northern Alps",
            "price_level": "medium",
            "latitude": 45.9,
            "longitude": 6.8,
            "base_elevation_m": 1200,
            "summit_elevation_m": 2800,
            "season_start_month": 12,
            "season_end_month": 4,
            "ski_areas": [
                {
                    "ski_area_id": "test-resort-ski-area",
                    "name": "Test Resort",
                    "latitude": 45.9,
                    "longitude": 6.8,
                    "base_elevation_m": 1200,
                    "summit_elevation_m": 2800,
                    "season_start_month": 12,
                    "season_end_month": 4,
                }
            ],
            "stay_bases": [
                {
                    "name": "Village",
                    "price_range": "EUR 150-220",
                    "quality": "standard",
                    "lift_distance": "near",
                    "supported_skill_levels": ["beginner", "intermediate"],
                }
            ],
            "rentals": [
                {
                    "name": "Rental Shop",
                    "price_range": "EUR 40-60",
                    "quality": "standard",
                    "lift_distance": "near",
                }
            ],
        }
    ]


def _valid_manifest_payload() -> dict:
    groups = [
        "destination_identity",
        "country_region",
        "destination_coordinates",
        "destination_elevation",
        "season_window",
        "ski_areas",
        "terrain_groups",
        "stay_bases",
        "stay_base_quality_tier",
        "stay_base_lift_distance",
        "supported_skill_levels",
        "lift_pass_products",
        "rental_examples",
        "rental_quality_tier",
        "price_ranges",
    ]
    return {
        "version": "test",
        "field_groups": groups,
        "destinations": {
            "test-resort": {
                "display_name": "Test Resort",
                "field_statuses": {group: "estimated" for group in groups},
            }
        },
    }


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload))


def test_validate_catalog_accepts_explicit_catalog_and_manifest(tmp_path) -> None:
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, _valid_resort_payload())
    _write_json(manifest_path, _valid_manifest_payload())

    report = validate_catalog(
        resorts_path=resorts_path,
        trust_manifest_path=manifest_path,
    )

    assert report.destination_count == 1
    assert report.ski_area_count == 1
    assert report.stay_base_count == 1
    assert report.rental_count == 1


def test_catalog_loader_derives_stay_base_id_when_missing(tmp_path) -> None:
    resorts_path = tmp_path / "resorts.json"
    _write_json(resorts_path, _valid_resort_payload())

    resorts = load_resorts_from_path(resorts_path)

    assert resorts[0].stay_bases[0].stay_base_id == "test-resort-village"


def test_catalog_loader_preserves_explicit_stay_base_id(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["stay_bases"][0]["stay_base_id"] = "village-core"
    resorts_path = tmp_path / "resorts.json"
    _write_json(resorts_path, payload)

    resorts = load_resorts_from_path(resorts_path)

    assert resorts[0].stay_bases[0].stay_base_id == "village-core"


def test_catalog_loader_accepts_scoped_lift_pass_products_and_terrain_groups(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    payload[0]["ski_areas"].append(
        {
            "ski_area_id": "test-resort-second-ski-area",
            "name": "Second Test Ski Area",
            "latitude": 45.91,
            "longitude": 6.81,
            "base_elevation_m": 1300,
            "summit_elevation_m": 2700,
            "season_start_month": 12,
            "season_end_month": 4,
        }
    )
    payload[0]["lift_pass_products"] = [
        {
            "lift_pass_product_id": "test-alpine-card",
            "name": "Test ALPIN Card",
            "validity_scope": "regional_network",
            "is_default": True,
            "valid_ski_area_ids": [
                "test-resort-ski-area",
                "test-resort-second-ski-area",
            ],
            "external_validity_summary": "Also valid in neighboring ski regions.",
            "prices": [
                {
                    "duration_days": 1,
                    "audience": "adult",
                    "amount": 82,
                    "currency": "EUR",
                    "price_kind": "fixed",
                    "season_label": "Winter 2026/27 main season",
                    "source_url": "https://example.com/tickets",
                }
            ],
        }
    ]
    payload[0]["terrain_groups"] = [
        {
            "terrain_group_id": "test-linked-terrain",
            "name": "Test Linked Terrain",
            "ski_area_ids": [
                "test-resort-ski-area",
                "test-resort-second-ski-area",
            ],
            "metric_scope": "aggregate",
            "total_piste_km": 62.5,
            "total_lift_count": 24,
            "piste_km_by_difficulty": {
                "beginner": 30.5,
                "intermediate": 23,
                "advanced": 9,
            },
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    _write_json(resorts_path, payload)

    resorts = load_resorts_from_path(resorts_path)

    assert resorts[0].lift_pass_products[0].name == "Test ALPIN Card"
    assert resorts[0].lift_pass_products[0].is_default is True
    assert resorts[0].lift_pass_products[0].valid_ski_area_ids == [
        "test-resort-ski-area",
        "test-resort-second-ski-area",
    ]
    assert resorts[0].terrain_groups[0].terrain_group_id == "test-linked-terrain"
    assert resorts[0].terrain_groups[0].piste_km_by_difficulty.beginner == 30.5


def test_catalog_accepts_shared_terrain_domains_across_destinations(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    linked_resort = json.loads(json.dumps(payload[0]))
    linked_resort["resort_id"] = "linked-resort"
    linked_resort["name"] = "Linked Resort"
    linked_resort["ski_areas"][0]["ski_area_id"] = "linked-resort-ski-area"
    linked_resort["ski_areas"][0]["name"] = "Linked Resort Ski Area"
    linked_resort["stay_bases"][0]["stay_base_id"] = "linked-resort-village"
    payload.append(linked_resort)
    payload[0]["lift_pass_products"] = [
        {
            "lift_pass_product_id": "shared-domain-card",
            "name": "Shared Domain Card",
            "validity_scope": "regional_network",
            "is_default": True,
            "valid_ski_area_ids": ["test-resort-ski-area"],
            "terrain_domain_ids": ["test-linked-domain"],
            "external_validity_summary": "Also valid in the linked destination.",
            "prices": [
                {
                    "duration_days": 1,
                    "audience": "adult",
                    "amount": 82,
                    "currency": "EUR",
                    "price_kind": "fixed",
                }
            ],
        }
    ]
    terrain_domains = [
        {
            "terrain_domain_id": "test-linked-domain",
            "name": "Test Linked Domain",
            "ski_area_refs": [
                {
                    "resort_id": "test-resort",
                    "ski_area_id": "test-resort-ski-area",
                },
                {
                    "resort_id": "linked-resort",
                    "ski_area_id": "linked-resort-ski-area",
                },
            ],
            "metric_scope": "aggregate",
            "total_piste_km": 300,
            "base_elevation_m": 1550,
            "summit_elevation_m": 3456,
            "source_urls": ["https://example.com/shared-domain"],
        }
    ]
    manifest = _valid_manifest_payload()
    manifest["destinations"]["linked-resort"] = {
        "display_name": "Linked Resort",
        "field_statuses": dict(
            manifest["destinations"]["test-resort"]["field_statuses"]
        ),
    }
    resorts_path = tmp_path / "resorts.json"
    terrain_domains_path = tmp_path / "terrain_domains.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(terrain_domains_path, terrain_domains)
    _write_json(manifest_path, manifest)

    domains = load_terrain_domains_from_path(terrain_domains_path)
    report = validate_catalog(
        resorts_path=resorts_path,
        terrain_domains_path=terrain_domains_path,
        trust_manifest_path=manifest_path,
    )

    assert domains[0].terrain_domain_id == "test-linked-domain"
    assert domains[0].ski_area_refs[1].resort_id == "linked-resort"
    assert report.terrain_domain_count == 1


def test_catalog_loader_accepts_single_ski_area_lift_pass_products(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    payload[0]["lift_pass_products"] = [
        {
            "lift_pass_product_id": "test-day-ticket",
            "name": "Test day ticket",
            "validity_scope": "single_ski_area",
            "is_default": True,
            "valid_ski_area_ids": ["test-resort-ski-area"],
            "prices": [
                {
                    "duration_days": 1,
                    "audience": "adult",
                    "amount": 65,
                    "currency": "EUR",
                    "price_kind": "fixed",
                }
            ],
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    _write_json(resorts_path, payload)

    resorts = load_resorts_from_path(resorts_path)

    product = resorts[0].lift_pass_products[0]
    assert product.validity_scope == "single_ski_area"
    assert product.valid_ski_area_ids == ["test-resort-ski-area"]
    assert product.is_default is True


def test_validate_catalog_rejects_unknown_lift_pass_product_ski_area_id(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    payload[0]["lift_pass_products"] = [
        {
            "lift_pass_product_id": "test-alpine-card",
            "name": "Test ALPIN Card",
            "validity_scope": "local_multi_area",
            "valid_ski_area_ids": ["test-resort-ski-area", "missing-ski-area"],
            "prices": [
                {
                    "duration_days": 1,
                    "audience": "adult",
                    "amount": 82,
                    "currency": "EUR",
                    "price_kind": "fixed",
                }
            ],
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "lift pass product references unknown ski_area_id" in issue
        for issue in error.value.issues
    )


def test_validate_catalog_rejects_unknown_lift_pass_product_terrain_domain_id(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    payload[0]["lift_pass_products"] = [
        {
            "lift_pass_product_id": "test-alpine-card",
            "name": "Test ALPIN Card",
            "validity_scope": "regional_network",
            "valid_ski_area_ids": ["test-resort-ski-area"],
            "terrain_domain_ids": ["missing-domain"],
            "external_validity_summary": "Also valid in neighboring ski regions.",
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    terrain_domains_path = tmp_path / "terrain_domains.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(terrain_domains_path, [])
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            terrain_domains_path=terrain_domains_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "lift pass product references unknown terrain_domain_id" in issue
        for issue in error.value.issues
    )


def test_validate_catalog_rejects_duplicate_lift_pass_product_ids(tmp_path) -> None:
    payload = _valid_resort_payload()
    product = {
        "lift_pass_product_id": "test-alpine-card",
        "name": "Test ALPIN Card",
        "validity_scope": "single_ski_area",
        "valid_ski_area_ids": ["test-resort-ski-area"],
        "prices": [
            {
                "duration_days": 1,
                "audience": "adult",
                "amount": 82,
                "currency": "EUR",
                "price_kind": "fixed",
            }
        ],
    }
    payload[0]["lift_pass_products"] = [product, {**product, "name": "Duplicate"}]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "duplicate lift-pass product id" in issue for issue in error.value.issues
    )


def test_validate_catalog_rejects_multiple_default_lift_pass_products(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    payload[0]["ski_areas"].append(
        {
            "ski_area_id": "test-resort-second-ski-area",
            "name": "Second Test Ski Area",
            "latitude": 45.91,
            "longitude": 6.81,
            "base_elevation_m": 1300,
            "summit_elevation_m": 2700,
            "season_start_month": 12,
            "season_end_month": 4,
        }
    )
    payload[0]["lift_pass_products"] = [
        {
            "lift_pass_product_id": "test-day-ticket",
            "name": "Test day ticket",
            "validity_scope": "single_ski_area",
            "is_default": True,
            "valid_ski_area_ids": ["test-resort-ski-area"],
        },
        {
            "lift_pass_product_id": "test-second-day-ticket",
            "name": "Second Test day ticket",
            "validity_scope": "single_ski_area",
            "is_default": True,
            "valid_ski_area_ids": ["test-resort-second-ski-area"],
        },
    ]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "multiple default lift-pass products" in issue for issue in error.value.issues
    )


def test_validate_catalog_rejects_mis_scoped_lift_pass_products(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["ski_areas"].append(
        {
            "ski_area_id": "test-resort-second-ski-area",
            "name": "Second Test Ski Area",
            "latitude": 45.91,
            "longitude": 6.81,
            "base_elevation_m": 1300,
            "summit_elevation_m": 2700,
            "season_start_month": 12,
            "season_end_month": 4,
        }
    )
    payload[0]["lift_pass_products"] = [
        {
            "lift_pass_product_id": "test-day-ticket",
            "name": "Test day ticket",
            "validity_scope": "single_ski_area",
            "valid_ski_area_ids": [
                "test-resort-ski-area",
                "test-resort-second-ski-area",
            ],
        },
        {
            "lift_pass_product_id": "test-local-pass",
            "name": "Test local pass",
            "validity_scope": "local_multi_area",
            "valid_ski_area_ids": ["test-resort-ski-area"],
        },
    ]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "single_ski_area pass products require exactly one valid_ski_area_id" in issue
        for issue in error.value.issues
    )
    assert any(
        "local_multi_area pass products require at least two valid_ski_area_ids"
        in issue
        for issue in error.value.issues
    )


def test_validate_catalog_rejects_legacy_lift_pass_prices_field(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["lift_pass_prices"] = [
        {
            "duration_days": 1,
            "audience": "adult",
            "amount": 82,
            "currency": "EUR",
            "price_kind": "fixed",
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "legacy lift_pass_prices field is not allowed" in issue
        for issue in error.value.issues
    )


def test_validate_catalog_rejects_unknown_terrain_group_ski_area_id(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    payload[0]["terrain_groups"] = [
        {
            "terrain_group_id": "test-linked-terrain",
            "name": "Test Linked Terrain",
            "ski_area_ids": ["test-resort-ski-area", "missing-ski-area"],
            "metric_scope": "aggregate",
            "total_piste_km": 62.5,
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "terrain group references unknown ski_area_id" in issue
        for issue in error.value.issues
    )


def test_validate_catalog_rejects_duplicate_terrain_group_ids(tmp_path) -> None:
    payload = _valid_resort_payload()
    group = {
        "terrain_group_id": "test-linked-terrain",
        "name": "Test Linked Terrain",
        "ski_area_ids": ["test-resort-ski-area"],
        "metric_scope": "aggregate",
        "total_piste_km": 62.5,
    }
    payload[0]["terrain_groups"] = [group, {**group, "name": "Duplicate"}]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("duplicate terrain group id" in issue for issue in error.value.issues)


def test_validate_catalog_rejects_mismatched_terrain_group_difficulty_totals(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    payload[0]["terrain_groups"] = [
        {
            "terrain_group_id": "test-linked-terrain",
            "name": "Test Linked Terrain",
            "ski_area_ids": ["test-resort-ski-area"],
            "metric_scope": "aggregate",
            "total_piste_km": 100,
            "piste_km_by_difficulty": {
                "beginner": 10,
                "intermediate": 20,
                "advanced": 30,
            },
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "terrain group difficulty piste total" in issue for issue in error.value.issues
    )


def test_validate_catalog_rejects_unknown_terrain_domain_ski_area_ref(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    terrain_domains = [
        {
            "terrain_domain_id": "test-linked-domain",
            "name": "Test Linked Domain",
            "ski_area_refs": [
                {
                    "resort_id": "test-resort",
                    "ski_area_id": "missing-ski-area",
                }
            ],
            "metric_scope": "aggregate",
            "total_piste_km": 300,
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    terrain_domains_path = tmp_path / "terrain_domains.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(terrain_domains_path, terrain_domains)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            terrain_domains_path=terrain_domains_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "terrain domain references unknown ski area" in issue
        for issue in error.value.issues
    )


@pytest.mark.parametrize("stay_base_id", ["", "   "])
def test_stay_base_rejects_blank_stay_base_id(stay_base_id) -> None:
    with pytest.raises(ValueError):
        StayBase(
            stay_base_id=stay_base_id,
            name="Village",
            price_range="EUR 150-220",
            price_min=150,
            price_max=220,
            quality="standard",
            lift_distance="near",
            supported_skill_levels=["beginner"],
        )


@pytest.mark.parametrize("stay_base_id", ["", "   "])
def test_catalog_loader_derives_stay_base_id_when_explicit_id_is_blank(
    tmp_path,
    stay_base_id,
) -> None:
    payload = _valid_resort_payload()
    payload[0]["stay_bases"][0]["stay_base_id"] = stay_base_id
    resorts_path = tmp_path / "resorts.json"
    _write_json(resorts_path, payload)

    resorts = load_resorts_from_path(resorts_path)

    assert resorts[0].stay_bases[0].stay_base_id == "test-resort-village"


def test_catalog_loader_rejects_invalid_stay_base_coordinates(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["stay_bases"][0]["latitude"] = 95.0
    payload[0]["stay_bases"][0]["longitude"] = 181.0
    resorts_path = tmp_path / "resorts.json"
    _write_json(resorts_path, payload)

    with pytest.raises(ValueError):
        load_resorts_from_path(resorts_path)


def test_validate_catalog_rejects_legacy_area_payloads(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["areas"] = payload[0].pop("stay_bases")
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("legacy 'areas'" in issue for issue in error.value.issues)


def test_validate_catalog_rejects_missing_trust_manifest_coverage(tmp_path) -> None:
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    manifest = _valid_manifest_payload()
    manifest["destinations"] = {}
    _write_json(resorts_path, _valid_resort_payload())
    _write_json(manifest_path, manifest)

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("missing trust manifest entry" in issue for issue in error.value.issues)


def test_validate_catalog_rejects_duplicate_ski_area_ids(tmp_path) -> None:
    payload = _valid_resort_payload()
    duplicate = json.loads(json.dumps(payload[0]))
    duplicate["resort_id"] = "second-resort"
    duplicate["name"] = "Second Resort"
    payload.append(duplicate)
    manifest = _valid_manifest_payload()
    manifest["destinations"]["second-resort"] = {
        "display_name": "Second Resort",
        "field_statuses": manifest["destinations"]["test-resort"]["field_statuses"],
    }
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, manifest)

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("duplicate ski-area id" in issue for issue in error.value.issues)


def test_validate_catalog_rejects_invalid_coordinates_and_elevation(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["latitude"] = 80
    payload[0]["summit_elevation_m"] = payload[0]["base_elevation_m"]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("coordinates are outside" in issue for issue in error.value.issues)
    assert any(
        "summit elevation must be above" in issue for issue in error.value.issues
    )


def test_validate_catalog_rejects_mismatched_piste_difficulty_totals(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["ski_areas"][0]["total_piste_km"] = 100
    payload[0]["ski_areas"][0]["piste_km_by_difficulty"] = {
        "beginner": 10,
        "intermediate": 20,
        "advanced": 30,
    }
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("difficulty piste total" in issue for issue in error.value.issues)


def test_validate_catalog_rejects_walk_access_with_far_nearest_lift(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["stay_bases"][0]["nearest_lift_name"] = "Distant lift"
    payload[0]["stay_bases"][0]["nearest_lift_distance_m"] = 2500
    payload[0]["stay_bases"][0]["access_mode"] = "walk"
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("walk access conflicts" in issue for issue in error.value.issues)


def test_validate_catalog_rejects_invalid_trust_status(tmp_path) -> None:
    manifest = _valid_manifest_payload()
    manifest["destinations"]["test-resort"]["field_statuses"]["price_ranges"] = (
        "unknown"
    )
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, _valid_resort_payload())
    _write_json(manifest_path, manifest)

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "price_ranges has invalid trust status" in issue for issue in error.value.issues
    )


def test_validate_catalog_rejects_verified_statuses_with_only_self_reference(
    tmp_path,
) -> None:
    manifest = _valid_manifest_payload()
    manifest["destinations"]["test-resort"]["field_statuses"][
        "destination_identity"
    ] = "verified"
    manifest["destinations"]["test-resort"]["source_refs"] = ["app/data/resorts.json"]
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, _valid_resort_payload())
    _write_json(manifest_path, manifest)

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "verified trust statuses require source_refs" in issue
        for issue in error.value.issues
    )


def test_validate_canonical_catalog_and_manifest() -> None:
    report = validate_catalog()

    assert report.destination_count == 26
    assert report.ski_area_count >= 26


def test_canonical_manifest_has_source_backed_factual_statuses() -> None:
    manifest = json.loads(Path("app/data/resort_trust_manifest.json").read_text())
    factual_groups = {
        "destination_identity",
        "country_region",
        "destination_coordinates",
        "destination_elevation",
        "season_window",
        "ski_areas",
        "stay_bases",
    }
    researched_destinations = {
        "hintertux",
        "stubai-glacier",
        "zell-am-see-kaprun",
        "tignes",
        "la-plagne",
        "zermatt",
    }

    for resort_id in researched_destinations:
        entry = manifest["destinations"][resort_id]
        assert entry["source_refs"] != ["app/data/resorts.json"]
        for group in factual_groups:
            assert entry["field_statuses"][group] in {
                "verified",
                "verified_with_adjustment",
            }
