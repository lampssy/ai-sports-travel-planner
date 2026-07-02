from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_graph import CatalogGraph
from app.domain.models import ProvenanceInfo, SearchExplanation
from app.domain.search_v3_models import (
    AccessSummary,
    PassOption,
    RecommendationGroup,
    ResilienceSummary,
    TripConfiguration,
)
from tests.test_catalog_models import minimal_catalog_payload


def _configuration(
    *,
    configuration_id: str = "example-village--example-area",
    ski_region_id: str = "example",
    score: float = 0.82,
) -> TripConfiguration:
    provenance = ProvenanceInfo(
        source_name="Open-Meteo",
        source_type="forecast",
        freshness_status="fresh",
        basis_summary="Current forecast.",
        evidence_profile="forecast_assisted",
    )
    return TripConfiguration(
        configuration_id=configuration_id,
        ski_region_id=ski_region_id,
        stay_destination_id="example",
        stay_destination_name="Example",
        stay_base_id="example-village",
        stay_base_name="Example Village",
        focus_ski_area_id="example-area",
        focus_ski_area_name="Example Area",
        access=AccessSummary(
            ski_area_access_id="example-village--example-area",
            mode="walk",
            lift_distance="near",
            nearest_lift_name="Example Gondola",
            distance_m=300,
            duration_minutes=None,
            is_direct=True,
        ),
        selected_pass=PassOption(
            lift_pass_product_id="example-local-pass",
            name="Example Local Pass",
            validity_scope="single_ski_area",
            accessible_ski_area_ids=["example-area"],
            accessible_terrain_label="Example Area",
            accessible_piste_km=50,
            price_example=None,
            pass_fit_score=1,
            tradeoff_summary="Local terrain access.",
        ),
        alternative_passes=[],
        resilience=ResilienceSummary(
            alternative_area_count=0,
            evidenced_alternative_count=0,
            areas=[],
            summary="No alternative ski areas on this pass.",
            ranking_component=0,
        ),
        score=score,
        score_components={"conditions": 0.2},
        budget_penalty=0,
        travel_effort=None,
        conditions_summary="Good conditions.",
        snow_confidence_score=0.8,
        conditions_score=0.75,
        planning_summary=None,
        planning_provenance=None,
        planning_evidence_count=None,
        planning_weather_metrics=None,
        evidence_quality=provenance,
        explanation=SearchExplanation(
            highlights=[], risks=[], confidence_contributors=[]
        ),
    )


def test_recommendation_group_score_must_match_winner() -> None:
    with pytest.raises(ValidationError, match="must equal top configuration"):
        RecommendationGroup(
            ski_region_id="example",
            ski_region_name="Example Valley",
            rank=1,
            score=0.75,
            top_configuration=_configuration(score=0.82),
            alternative_configurations=[],
        )


def test_recommendation_group_requires_same_region_and_unique_configurations() -> None:
    top = _configuration()
    with pytest.raises(ValidationError, match="must belong to ski region"):
        RecommendationGroup(
            ski_region_id="example",
            ski_region_name="Example Valley",
            rank=1,
            score=top.score,
            top_configuration=top,
            alternative_configurations=[
                _configuration(configuration_id="other", ski_region_id="other")
            ],
        )

    with pytest.raises(ValidationError, match="configuration IDs must be unique"):
        RecommendationGroup(
            ski_region_id="example",
            ski_region_name="Example Valley",
            rank=1,
            score=top.score,
            top_configuration=top,
            alternative_configurations=[top],
        )


def test_resilience_cannot_contribute_to_ranking() -> None:
    with pytest.raises(ValidationError):
        ResilienceSummary(
            alternative_area_count=1,
            evidenced_alternative_count=1,
            areas=[],
            summary="Alternative available.",
            ranking_component=0.1,
        )


def test_catalog_graph_indexes_domain_covered_passes_and_is_immutable() -> None:
    payload = minimal_catalog_payload()
    second_area = deepcopy(payload["ski_areas"][0])
    second_area["ski_area_id"] = "other-area"
    second_area["name"] = "Other Area"
    payload["ski_areas"].append(second_area)
    second_access = deepcopy(payload["ski_area_access"][0])
    second_access["ski_area_access_id"] = "example-village--other-area"
    second_access["ski_area_id"] = "other-area"
    payload["ski_area_access"].append(second_access)
    payload["terrain_domains"].append(
        {
            "terrain_domain_id": "example-domain",
            "name": "Example Domain",
            "ski_area_ids": ["example-area", "other-area"],
            "source_urls": ["https://example.com/domain"],
        }
    )
    payload["lift_pass_products"][0].update(
        {
            "validity_scope": "local_multi_area",
            "valid_ski_area_ids": [],
            "terrain_domain_ids": ["example-domain"],
        }
    )
    graph = CatalogGraph.from_snapshot(CatalogSnapshot.model_validate(payload))

    assert [
        product.lift_pass_product_id
        for product in graph.passes_by_destination_area[("example", "other-area")]
    ] == ["example-local-pass"]
    assert len(graph.accesses_by_base_id["example-village"]) == 2
    with pytest.raises(TypeError):
        graph.areas_by_id["new"] = graph.areas_by_id["example-area"]  # type: ignore[index]
