from app.data.repositories import get_conditions_repository
from app.domain.models import ResortConditions


class ResortConditionsProvider:
    def __init__(self, conditions: dict[str, ResortConditions]) -> None:
        self._conditions = conditions

    def get_conditions_for_ski_area(self, ski_area_id: str) -> ResortConditions | None:
        return self._conditions.get(ski_area_id)

    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions | None:
        return next(
            (
                conditions
                for conditions in self._conditions.values()
                if conditions.resort_name == resort_name
            ),
            None,
        )


def get_conditions_provider() -> ResortConditionsProvider:
    return ResortConditionsProvider(get_conditions_repository().list_conditions())
