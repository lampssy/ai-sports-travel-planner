import json

import pytest

from app.data.loader import load_resorts_from_path


def test_loader_deserializes_valid_resort_json(tmp_path) -> None:
    path = tmp_path / "resorts.json"
    path.write_text(
        json.dumps(
            [
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
                    "lift_pass_prices": [
                        {
                            "duration_days": 6,
                            "audience": "adult",
                            "amount": 390,
                            "currency": "EUR",
                            "price_kind": "fixed",
                            "season_label": "2025-2026",
                            "source_url": "https://example.com/prices",
                        }
                    ],
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
                            "total_piste_km": 130,
                            "total_lift_count": 42,
                            "piste_km_by_difficulty": {
                                "beginner": 50,
                                "intermediate": 60,
                                "advanced": 20,
                            },
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
        )
    )

    resorts = load_resorts_from_path(path)

    assert len(resorts) == 1
    assert resorts[0].stay_bases[0].price_min == 150
    assert resorts[0].stay_bases[0].price_max == 220
    assert resorts[0].ski_areas[0].name == "Test Resort"
    assert resorts[0].ski_areas[0].ski_area_id == "test-resort-ski-area"
    assert resorts[0].lift_pass_prices[0].duration_days == 6
    assert resorts[0].lift_pass_prices[0].amount == 390
    assert resorts[0].ski_areas[0].total_piste_km == 130
    assert resorts[0].ski_areas[0].total_lift_count == 42
    assert resorts[0].ski_areas[0].piste_km_by_difficulty is not None
    assert resorts[0].ski_areas[0].piste_km_by_difficulty.advanced == 20


def test_loader_rejects_invalid_enum_values(tmp_path) -> None:
    path = tmp_path / "resorts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "broken-resort",
                    "name": "Broken Resort",
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
                            "ski_area_id": "broken-resort-ski-area",
                            "name": "Broken Resort",
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
                            "quality": "luxury",
                            "lift_distance": "near",
                            "supported_skill_levels": ["beginner"],
                        }
                    ],
                    "rentals": [],
                }
            ]
        )
    )

    with pytest.raises(ValueError):
        load_resorts_from_path(path)


def test_loader_rejects_malformed_price_ranges(tmp_path) -> None:
    path = tmp_path / "resorts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "broken-resort",
                    "name": "Broken Resort",
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
                            "ski_area_id": "broken-resort-ski-area",
                            "name": "Broken Resort",
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
                            "price_range": "approx 200",
                            "quality": "standard",
                            "lift_distance": "near",
                            "supported_skill_levels": ["beginner"],
                        }
                    ],
                    "rentals": [],
                }
            ]
        )
    )

    with pytest.raises(ValueError):
        load_resorts_from_path(path)


def test_loader_rejects_missing_required_fields(tmp_path) -> None:
    path = tmp_path / "resorts.json"
    path.write_text(json.dumps([{"name": "Incomplete"}]))

    with pytest.raises(ValueError):
        load_resorts_from_path(path)


def test_loader_rejects_legacy_areas_without_explicit_stay_bases(tmp_path) -> None:
    path = tmp_path / "resorts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "legacy-resort",
                    "name": "Legacy Resort",
                    "country": "France",
                    "region": "Northern Alps",
                    "price_level": "medium",
                    "latitude": 45.9,
                    "longitude": 6.8,
                    "base_elevation_m": 1200,
                    "summit_elevation_m": 2800,
                    "season_start_month": 12,
                    "season_end_month": 4,
                    "areas": [],
                    "ski_areas": [],
                    "rentals": [],
                }
            ]
        )
    )

    with pytest.raises(ValueError, match="legacy 'areas'"):
        load_resorts_from_path(path)


def test_loader_requires_explicit_ski_areas(tmp_path) -> None:
    path = tmp_path / "resorts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "missing-ski-area",
                    "name": "Missing Ski Area",
                    "country": "France",
                    "region": "Northern Alps",
                    "price_level": "medium",
                    "latitude": 45.9,
                    "longitude": 6.8,
                    "base_elevation_m": 1200,
                    "summit_elevation_m": 2800,
                    "season_start_month": 12,
                    "season_end_month": 4,
                    "stay_bases": [],
                    "rentals": [],
                }
            ]
        )
    )

    with pytest.raises(ValueError, match="Missing required field: ski_areas"):
        load_resorts_from_path(path)
