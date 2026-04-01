import json

import pytest

from app.data.loader import load_resorts_from_path


def test_loader_deserializes_valid_resort_json(tmp_path) -> None:
    path = tmp_path / "resorts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "name": "Test Resort",
                    "country": "France",
                    "price_level": "medium",
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
    assert resorts[0].areas[0].price_min == 150
    assert resorts[0].areas[0].price_max == 220


def test_loader_rejects_invalid_enum_values(tmp_path) -> None:
    path = tmp_path / "resorts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "name": "Broken Resort",
                    "country": "France",
                    "price_level": "medium",
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
                    "name": "Broken Resort",
                    "country": "France",
                    "price_level": "medium",
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
