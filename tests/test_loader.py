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
                    "areas": [
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
                    "areas": [
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
                    "areas": [
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
