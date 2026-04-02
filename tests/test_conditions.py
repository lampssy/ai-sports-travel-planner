import json

import pytest

from app.integrations.conditions import (
    get_conditions_provider,
    load_conditions_from_path,
)


def test_conditions_provider_returns_resort_conditions() -> None:
    provider = get_conditions_provider()

    conditions = provider.get_conditions_for_resort("Alpine Horizon")

    assert conditions is not None
    assert conditions.snow_confidence_score == 0.89
    assert conditions.snow_confidence_label == "good"
    assert conditions.availability_status == "open"


def test_conditions_provider_returns_none_for_unknown_resort() -> None:
    provider = get_conditions_provider()

    conditions = provider.get_conditions_for_resort("Unknown Resort")

    assert conditions is None


def test_conditions_loader_derives_label_from_score(tmp_path) -> None:
    path = tmp_path / "conditions.json"
    path.write_text(
        json.dumps(
            [
                {
                    "resort_name": "Test Resort",
                    "snow_confidence_score": 0.62,
                    "availability_status": "limited",
                    "weather_summary": "Changeable weather window.",
                    "conditions_score": 0.55,
                }
            ]
        )
    )

    conditions = load_conditions_from_path(path)

    assert conditions["Test Resort"].snow_confidence_label == "fair"


def test_conditions_loader_rejects_invalid_availability_status(tmp_path) -> None:
    path = tmp_path / "conditions.json"
    path.write_text(
        json.dumps(
            [
                {
                    "resort_name": "Broken Resort",
                    "snow_confidence_score": 0.75,
                    "availability_status": "unknown",
                    "weather_summary": "Stable snow window.",
                    "conditions_score": 0.7,
                }
            ]
        )
    )

    with pytest.raises(ValueError):
        load_conditions_from_path(path)


def test_conditions_loader_rejects_mismatched_label_and_score(tmp_path) -> None:
    path = tmp_path / "conditions.json"
    path.write_text(
        json.dumps(
            [
                {
                    "resort_name": "Broken Resort",
                    "snow_confidence_score": 0.2,
                    "snow_confidence_label": "good",
                    "availability_status": "open",
                    "weather_summary": "Stable snow window.",
                    "conditions_score": 0.7,
                }
            ]
        )
    )

    with pytest.raises(ValueError):
        load_conditions_from_path(path)
