from app.domain.models import ResortConditions
from app.integrations.conditions import get_conditions_provider


class FakeConditionsRepository:
    def __init__(self, conditions: dict[str, ResortConditions]) -> None:
        self._conditions = conditions

    def list_conditions(self) -> dict[str, ResortConditions]:
        return self._conditions


def test_conditions_provider_returns_resort_conditions(monkeypatch) -> None:
    repository = FakeConditionsRepository(
        {
            "brevent-flegere": ResortConditions(
                resort_name="Chamonix Mont-Blanc",
                snow_confidence_score=0.78,
                availability_status="open",
                weather_summary="Strong alpine outlook.",
                conditions_score=0.72,
                updated_at="2026-04-07T10:00:00+00:00",
                source="open-meteo",
            ),
        }
    )
    monkeypatch.setattr(
        "app.integrations.conditions.get_conditions_repository",
        lambda: repository,
    )

    provider = get_conditions_provider()

    conditions = provider.get_conditions_for_ski_area("brevent-flegere")

    assert conditions is not None
    assert conditions.snow_confidence_score == 0.78
    assert conditions.snow_confidence_label == "good"
    assert conditions.availability_status == "open"


def test_conditions_provider_returns_none_for_unknown_resort(
    monkeypatch,
) -> None:
    repository = FakeConditionsRepository({})
    monkeypatch.setattr(
        "app.integrations.conditions.get_conditions_repository",
        lambda: repository,
    )
    provider = get_conditions_provider()

    conditions = provider.get_conditions_for_ski_area("unknown-ski-area")

    assert conditions is None
