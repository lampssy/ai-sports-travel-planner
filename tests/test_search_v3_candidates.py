from __future__ import annotations

from copy import deepcopy

from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_graph import CatalogGraph
from app.domain.models import SearchFilters
from app.domain.search_v3_candidates import generate_candidate_seeds
from tests.test_catalog_models import minimal_catalog_payload


def _filters(**updates: object) -> SearchFilters:
    payload: dict[str, object] = {
        "location": "France",
        "min_price": 140,
        "max_price": 240,
        "stars": 1,
        "skill_level": "intermediate",
    }
    payload.update(updates)
    return SearchFilters.model_validate(payload)


def _two_by_two_graph() -> CatalogGraph:
    payload = minimal_catalog_payload()
    payload["stay_bases"][0]["quality"] = "standard"
    second_base = deepcopy(payload["stay_bases"][0])
    second_base.update(
        {
            "stay_base_id": "other-village",
            "name": "Other Village",
            "price_min": 210,
            "price_max": 280,
            "quality": "premium",
        }
    )
    payload["stay_bases"].append(second_base)

    second_area = deepcopy(payload["ski_areas"][0])
    second_area.update(
        {
            "ski_area_id": "other-area",
            "name": "Other Area",
            "supported_skill_levels": ["intermediate", "advanced"],
        }
    )
    payload["ski_areas"].append(second_area)
    payload["ski_area_access"][0]["lift_distance"] = "near"
    second_access = deepcopy(payload["ski_area_access"][0])
    second_access.update(
        {
            "ski_area_access_id": "other-village--other-area",
            "stay_base_id": "other-village",
            "ski_area_id": "other-area",
            "lift_distance": "far",
        }
    )
    payload["ski_area_access"].append(second_access)
    payload["lift_pass_products"][0].update(
        {
            "validity_scope": "local_multi_area",
            "valid_ski_area_ids": ["example-area", "other-area"],
        }
    )
    return CatalogGraph.from_snapshot(CatalogSnapshot.model_validate(payload))


def test_candidate_generation_uses_only_explicit_access_edges() -> None:
    candidates = generate_candidate_seeds(
        _two_by_two_graph(),
        _filters(),
    )

    assert {
        (candidate.stay_base.stay_base_id, candidate.ski_area.ski_area_id)
        for candidate in candidates
    } == {
        ("example-village", "example-area"),
        ("other-village", "other-area"),
    }
    assert all(candidate.candidate_passes for candidate in candidates)


def test_candidate_filters_read_from_canonical_catalog_owners() -> None:
    graph = _two_by_two_graph()

    assert generate_candidate_seeds(graph, _filters(location="Italy")) == ()
    assert {
        seed.stay_base.stay_base_id
        for seed in generate_candidate_seeds(graph, _filters(stars=3))
    } == {"other-village"}
    assert generate_candidate_seeds(graph, _filters(min_price=20, max_price=40)) == ()
    assert {
        seed.ski_area.ski_area_id
        for seed in generate_candidate_seeds(graph, _filters(skill_level="advanced"))
    } == {"other-area"}
    assert (
        generate_candidate_seeds(
            graph,
            _filters(
                skill_level="advanced",
                budget_flex=0.5,
                lift_distance="medium",
            ),
        )
        == ()
    )


def test_candidate_generation_requires_a_covering_pass() -> None:
    payload = _two_by_two_graph().snapshot.model_dump(mode="json")
    payload["lift_pass_products"][0]["valid_ski_area_ids"] = ["example-area"]
    graph = CatalogGraph.from_snapshot(CatalogSnapshot.model_validate(payload))

    candidates = generate_candidate_seeds(graph, _filters())

    assert len(candidates) == 1
    assert candidates[0].ski_area.ski_area_id == "example-area"
    assert candidates[0].candidate_passes[0].lift_pass_product_id == (
        "example-local-pass"
    )
