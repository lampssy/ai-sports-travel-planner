from app.data.conditions_loader import (
    DEFAULT_CONDITIONS_PATH,
    load_conditions_from_path,
)
from app.data.repositories import get_conditions_repository
from app.domain.models import ResortConditions

CONDITIONS_PATH = DEFAULT_CONDITIONS_PATH


class ResortConditionsProvider:
    def __init__(self, conditions: dict[str, ResortConditions]) -> None:
        self._conditions = conditions

    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions | None:
        return self._conditions.get(resort_name)


def _load_conditions() -> dict[str, ResortConditions]:
    return load_conditions_from_path(CONDITIONS_PATH)


def get_conditions_provider() -> ResortConditionsProvider:
    return ResortConditionsProvider(get_conditions_repository().list_conditions())
