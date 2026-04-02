import json
from functools import lru_cache
from pathlib import Path

from app.domain.models import ResortConditions

CONDITIONS_PATH = Path(__file__).with_name("conditions.json")


class ResortConditionsProvider:
    def __init__(self, conditions: dict[str, ResortConditions]) -> None:
        self._conditions = conditions

    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions | None:
        return self._conditions.get(resort_name)


def _load_conditions() -> dict[str, ResortConditions]:
    payload = json.loads(CONDITIONS_PATH.read_text())
    return {
        item["resort_name"]: ResortConditions.model_validate(item) for item in payload
    }


@lru_cache
def get_conditions_provider() -> ResortConditionsProvider:
    return ResortConditionsProvider(_load_conditions())
