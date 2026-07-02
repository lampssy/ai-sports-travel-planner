from __future__ import annotations

from app.domain.catalog import CatalogSnapshot
from app.domain.models import ResortConditions, SearchFilters
from app.domain.search_evidence import load_planning_contexts
from tests.test_catalog_models import minimal_catalog_payload


class CountingConditionsProvider:
    def __init__(self) -> None:
        self.area_ids: list[str] = []

    def get_conditions_for_ski_area(
        self,
        ski_area_id: str,
    ) -> ResortConditions:
        self.area_ids.append(ski_area_id)
        return ResortConditions(
            resort_name="Example Area",
            snow_confidence_score=0.8,
            availability_status="open",
            weather_summary="Good conditions.",
            conditions_score=0.75,
            updated_at="2026-07-01T10:00:00+00:00",
            source="test",
        )


class UnexpectedRepository:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"repository should not be used: {name}")


def test_load_planning_contexts_builds_each_ski_area_once() -> None:
    area = CatalogSnapshot.model_validate(minimal_catalog_payload()).ski_areas[0]
    provider = CountingConditionsProvider()

    contexts = load_planning_contexts(
        ski_areas=(area, area),
        filters=SearchFilters(
            location="France",
            min_price=100,
            max_price=300,
            stars=1,
            skill_level="intermediate",
        ),
        conditions_provider=provider,
        condition_history_repository=UnexpectedRepository(),
        raw_weather_history_repository=UnexpectedRepository(),
        snow_climatology_repository=UnexpectedRepository(),
    )

    assert list(contexts) == ["example-area"]
    assert provider.area_ids == ["example-area"]
    assert contexts["example-area"].conditions.weather_summary == "Good conditions."
