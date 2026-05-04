import json
from pathlib import Path

import pytest

from app.data.validate_resort_catalog import CatalogValidationError, validate_catalog


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
        "stay_bases",
        "stay_base_quality_tier",
        "stay_base_lift_distance",
        "supported_skill_levels",
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
