from __future__ import annotations

from copy import deepcopy

from app.domain.catalog import CatalogSnapshot
from app.domain.models import ResortConditions, SearchFilters
from app.domain.search_v3_service import search_trip_markets
from tests.test_catalog_models import minimal_catalog_payload


class StaticCatalogRepository:
    def __init__(self, snapshot: CatalogSnapshot) -> None:
        self.snapshot = snapshot

    def get_snapshot(self) -> CatalogSnapshot:
        return self.snapshot


class StaticConditionsProvider:
    def __init__(self) -> None:
        self.area_ids: list[str] = []

    def get_conditions_for_ski_area(
        self,
        ski_area_id: str,
    ) -> ResortConditions:
        self.area_ids.append(ski_area_id)
        return ResortConditions(
            resort_name=ski_area_id,
            snow_confidence_score=0.8,
            availability_status="open",
            weather_summary="Good current conditions.",
            conditions_score=0.75,
            updated_at="2026-07-01T10:00:00+00:00",
            source="test",
        )


class UnexpectedRepository:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"repository should not be used: {name}")


def _shared_market_snapshot() -> CatalogSnapshot:
    payload = minimal_catalog_payload()
    payload["ski_regions"][0]["name"] = "Shared Valley"
    payload["stay_bases"][0]["quality"] = "standard"
    payload["ski_areas"][0].update(
        {
            "total_piste_km": 50,
            "piste_km_by_difficulty": {
                "beginner": 10,
                "intermediate": 30,
                "advanced": 10,
            },
        }
    )
    other_destination = deepcopy(payload["stay_destinations"][0])
    other_destination.update(
        {"stay_destination_id": "other", "name": "Other Destination"}
    )
    payload["stay_destinations"].append(other_destination)
    other_base = deepcopy(payload["stay_bases"][0])
    other_base.update(
        {
            "stay_base_id": "other-village",
            "stay_destination_id": "other",
            "name": "Other Village",
        }
    )
    payload["stay_bases"].append(other_base)
    other_area = deepcopy(payload["ski_areas"][0])
    other_area.update({"ski_area_id": "other-area", "name": "Other Area"})
    payload["ski_areas"].append(other_area)
    other_access = deepcopy(payload["ski_area_access"][0])
    other_access.update(
        {
            "ski_area_access_id": "other-village--other-area",
            "stay_base_id": "other-village",
            "ski_area_id": "other-area",
        }
    )
    payload["ski_area_access"].append(other_access)
    payload["terrain_domains"] = [
        {
            "terrain_domain_id": "shared-domain",
            "name": "Shared Connected Terrain",
            "ski_area_ids": ["example-area", "other-area"],
            "total_piste_km": 110,
            "source_urls": ["https://example.com/domain"],
        }
    ]
    payload["lift_pass_products"] = [
        {
            "lift_pass_product_id": "shared-pass",
            "name": "Shared Pass",
            "validity_scope": "local_multi_area",
            "available_from_stay_destination_ids": ["example", "other"],
            "default_for_stay_destination_ids": ["example", "other"],
            "valid_ski_area_ids": [],
            "terrain_domain_ids": ["shared-domain"],
            "prices": [],
        },
        {
            "lift_pass_product_id": "example-local-pass",
            "name": "Example Local Pass",
            "validity_scope": "single_ski_area",
            "available_from_stay_destination_ids": ["example"],
            "default_for_stay_destination_ids": [],
            "valid_ski_area_ids": ["example-area"],
            "terrain_domain_ids": [],
            "prices": [],
        },
    ]
    payload["rental_display_facts"] = [
        {
            "rental_display_fact_id": "rental-a",
            "stay_destination_id": "example",
            "name": "Rental A",
            "price_range": "EUR 30-40",
            "price_min": 30,
            "price_max": 40,
            "quality": "standard",
            "lift_distance": "near",
        },
        {
            "rental_display_fact_id": "rental-b",
            "stay_destination_id": "example",
            "name": "Rental B",
            "price_range": "EUR 35-45",
            "price_min": 35,
            "price_max": 45,
            "quality": "standard",
            "lift_distance": "near",
        },
    ]
    return CatalogSnapshot.model_validate(payload)


def _shared_market_with_competing_bases_snapshot() -> CatalogSnapshot:
    payload = _shared_market_snapshot().model_dump(mode="json")
    other_base = next(
        item
        for item in payload["stay_bases"]
        if item["stay_base_id"] == "other-village"
    )
    other_access = next(
        item
        for item in payload["ski_area_access"]
        if item["ski_area_access_id"] == "other-village--other-area"
    )
    for ordinal in range(2, 5):
        base = deepcopy(other_base)
        base.update(
            {
                "stay_base_id": f"other-village-{ordinal}",
                "name": f"Other Village {ordinal}",
            }
        )
        payload["stay_bases"].append(base)
        access = deepcopy(other_access)
        access.update(
            {
                "ski_area_access_id": f"other-village-{ordinal}--other-area",
                "stay_base_id": f"other-village-{ordinal}",
            }
        )
        payload["ski_area_access"].append(access)

    third_destination = deepcopy(payload["stay_destinations"][0])
    third_destination.update(
        {"stay_destination_id": "third", "name": "Third Destination"}
    )
    payload["stay_destinations"].append(third_destination)
    third_base = deepcopy(payload["stay_bases"][0])
    third_base.update(
        {
            "stay_base_id": "third-village",
            "stay_destination_id": "third",
            "name": "Third Village",
        }
    )
    payload["stay_bases"].append(third_base)
    third_area = deepcopy(payload["ski_areas"][0])
    third_area.update({"ski_area_id": "third-area", "name": "Third Area"})
    payload["ski_areas"].append(third_area)
    third_access = deepcopy(payload["ski_area_access"][0])
    third_access.update(
        {
            "ski_area_access_id": "third-village--third-area",
            "stay_base_id": "third-village",
            "ski_area_id": "third-area",
        }
    )
    payload["ski_area_access"].append(third_access)
    payload["terrain_domains"][0]["ski_area_ids"].append("third-area")
    shared_pass = payload["lift_pass_products"][0]
    shared_pass["available_from_stay_destination_ids"].append("third")
    shared_pass["default_for_stay_destination_ids"].append("third")
    return CatalogSnapshot.model_validate(payload)


def test_search_groups_concrete_configurations_by_trip_market() -> None:
    provider = StaticConditionsProvider()

    groups = search_trip_markets(
        SearchFilters(
            location="France",
            min_price=100,
            max_price=300,
            stars=1,
            skill_level="intermediate",
        ),
        catalog_repository=StaticCatalogRepository(_shared_market_snapshot()),
        conditions_provider=provider,
        condition_history_repository=UnexpectedRepository(),
        raw_weather_history_repository=UnexpectedRepository(),
        snow_climatology_repository=UnexpectedRepository(),
    )

    assert len(groups) == 1
    group = groups[0]
    configurations = [group.top_configuration, *group.alternative_configurations]
    assert group.ski_region_id == "example"
    assert group.score == group.top_configuration.score
    assert group.rank == 1
    assert {
        (item.stay_destination_id, item.stay_base_id, item.focus_ski_area_id)
        for item in configurations
    } == {
        ("example", "example-village", "example-area"),
        ("other", "other-village", "other-area"),
    }
    assert all(
        item.selected_pass.lift_pass_product_id == "shared-pass"
        for item in configurations
    )
    example = next(
        item for item in configurations if item.stay_destination_id == "example"
    )
    assert [item.lift_pass_product_id for item in example.alternative_passes] == [
        "example-local-pass"
    ]
    assert example.resilience.alternative_area_count == 1
    assert example.resilience.ranking_component == 0
    assert "resilience" not in example.score_components
    assert "pass_fit" not in example.score_components
    assert sorted(provider.area_ids) == ["example-area", "other-area"]


def test_group_alternatives_prioritize_distinct_stay_destinations() -> None:
    groups = search_trip_markets(
        SearchFilters(
            location="France",
            min_price=100,
            max_price=300,
            stars=1,
            skill_level="intermediate",
        ),
        catalog_repository=StaticCatalogRepository(
            _shared_market_with_competing_bases_snapshot()
        ),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=UnexpectedRepository(),
        raw_weather_history_repository=UnexpectedRepository(),
        snow_climatology_repository=UnexpectedRepository(),
    )

    group = groups[0]
    configurations = [group.top_configuration, *group.alternative_configurations]

    assert len(group.alternative_configurations) == 3
    assert {item.stay_destination_id for item in configurations} == {
        "example",
        "other",
        "third",
    }
