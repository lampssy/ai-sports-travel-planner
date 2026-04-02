from app.integrations.conditions import get_conditions_provider


def test_conditions_provider_returns_resort_conditions() -> None:
    provider = get_conditions_provider()

    conditions = provider.get_conditions_for_resort("Alpine Horizon")

    assert conditions is not None
    assert conditions.snow_quality in {"poor", "fair", "good", "excellent"}
    assert 0 <= conditions.confidence <= 1


def test_conditions_provider_returns_none_for_unknown_resort() -> None:
    provider = get_conditions_provider()

    conditions = provider.get_conditions_for_resort("Unknown Resort")

    assert conditions is None
