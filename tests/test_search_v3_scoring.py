from __future__ import annotations

import pytest

from app.domain.catalog import CatalogSnapshot
from app.domain.resort_fit import (
    ski_area_access_factor,
    terrain_scale_factor_for_catalog_area,
)
from app.domain.search_v3_scoring import (
    GLOBAL_SEARCH_V3_COMPONENTS,
    SearchV3ScoreInputs,
    score_search_v3_configuration,
)
from tests.test_catalog_models import minimal_catalog_payload


def _score_inputs() -> SearchV3ScoreInputs:
    return SearchV3ScoreInputs(
        lodging_quality=2,
        terrain_scale="large",
        terrain_trust_cap=1,
        skill_fit=("intermediate", "advanced"),
        skill_trust_cap=1,
        access_fit="walkable",
        access_trust_cap=1,
        snow_confidence_score=0.8,
        conditions_score=0.75,
        budget_penalty=0.1,
        travel_effort_score=0.7,
    )


def test_v3_scoring_uses_the_declared_global_components_and_values() -> None:
    inputs = _score_inputs()

    actual = score_search_v3_configuration(inputs)

    assert set(actual.components) == GLOBAL_SEARCH_V3_COMPONENTS
    assert dict(actual.components) == pytest.approx(
        {
            "legacy_base": 0.24,
            "terrain": 0.20,
            "skill_fit": 0.16,
            "stay_base_access": 0.18,
            "snow_evidence": 0.28,
            "conditions": 0.1875,
            "budget": -0.1,
            "travel_effort": -0.105,
        }
    )
    assert actual.total == sum(actual.components.values())
    assert "pass_fit" not in actual.components
    assert "resilience" not in actual.components


def test_v3_scoring_is_a_pure_function_of_explicit_inputs() -> None:
    inputs = _score_inputs()

    assert score_search_v3_configuration(inputs) == score_search_v3_configuration(
        inputs
    )


def test_canonical_terrain_prefers_larger_physically_connected_domain() -> None:
    payload = minimal_catalog_payload()
    payload["ski_areas"][0]["total_piste_km"] = 50
    second_area = dict(payload["ski_areas"][0])
    second_area["ski_area_id"] = "other-area"
    second_area["name"] = "Other Area"
    payload["ski_areas"].append(second_area)
    second_access = dict(payload["ski_area_access"][0])
    second_access["ski_area_access_id"] = "example-village--other-area"
    second_access["ski_area_id"] = "other-area"
    payload["ski_area_access"].append(second_access)
    payload["terrain_domains"] = [
        {
            "terrain_domain_id": "connected-domain",
            "name": "Connected Domain",
            "ski_area_ids": ["example-area", "other-area"],
            "total_piste_km": 180,
            "source_urls": ["https://example.com/domain"],
        }
    ]
    snapshot = CatalogSnapshot.model_validate(payload)

    factor = terrain_scale_factor_for_catalog_area(
        snapshot.ski_areas[0], snapshot.terrain_domains
    )

    assert factor.value == "large"
    assert factor.raw_inputs["terrain_source_scope"] == "terrain_domain"
    assert factor.raw_inputs["terrain_source_id"] == "connected-domain"


def test_canonical_access_uses_explicit_access_edge() -> None:
    snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())

    factor = ski_area_access_factor(snapshot.ski_area_access[0])

    assert factor.value == "walkable"
    assert factor.lifecycle_state == "active"
    assert factor.ranking_cap == 1
