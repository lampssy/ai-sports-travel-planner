from __future__ import annotations

from copy import deepcopy
from datetime import date

from app.domain.catalog import CatalogSnapshot, LiftPassProduct
from app.domain.catalog_graph import CatalogGraph
from app.domain.pass_selection import select_pass
from tests.test_catalog_models import minimal_catalog_payload


def _pass_graph() -> CatalogGraph:
    payload = minimal_catalog_payload()
    payload["ski_areas"][0]["total_piste_km"] = 50
    second_area = deepcopy(payload["ski_areas"][0])
    second_area.update(
        {
            "ski_area_id": "other-area",
            "name": "Other Area",
            "total_piste_km": 40,
        }
    )
    payload["ski_areas"].append(second_area)
    second_access = deepcopy(payload["ski_area_access"][0])
    second_access.update(
        {
            "ski_area_access_id": "example-village--other-area",
            "ski_area_id": "other-area",
        }
    )
    payload["ski_area_access"].append(second_access)
    payload["terrain_domains"].append(
        {
            "terrain_domain_id": "example-domain",
            "name": "Example Connected Domain",
            "ski_area_ids": ["example-area", "other-area"],
            "total_piste_km": 100,
            "source_urls": ["https://example.com/domain"],
        }
    )
    payload["lift_pass_products"] = [
        {
            "lift_pass_product_id": "default-local",
            "name": "Local Pass",
            "validity_scope": "single_ski_area",
            "available_from_stay_destination_ids": ["example"],
            "default_for_stay_destination_ids": ["example"],
            "valid_ski_area_ids": ["example-area"],
            "terrain_domain_ids": [],
            "prices": [
                {
                    "duration_days": 6,
                    "audience": "adult",
                    "amount": 300,
                    "currency": "EUR",
                    "price_kind": "fixed",
                }
            ],
        },
        {
            "lift_pass_product_id": "broad-pass",
            "name": "Broad Pass",
            "validity_scope": "local_multi_area",
            "available_from_stay_destination_ids": ["example"],
            "default_for_stay_destination_ids": [],
            "valid_ski_area_ids": [],
            "terrain_domain_ids": ["example-domain"],
            "prices": [
                {
                    "duration_days": 6,
                    "audience": "adult",
                    "amount": 280,
                    "currency": "EUR",
                    "price_kind": "fixed",
                }
            ],
        },
    ]
    return CatalogGraph.from_snapshot(CatalogSnapshot.model_validate(payload))


def _products(graph: CatalogGraph) -> tuple[LiftPassProduct, ...]:
    return graph.passes_by_destination_area[("example", "example-area")]


def test_month_only_search_prefers_destination_default_pass() -> None:
    graph = _pass_graph()

    selection = select_pass(
        products=_products(graph),
        graph=graph,
        stay_destination_id="example",
        focus_ski_area_id="example-area",
        trip_start_date=None,
        trip_end_date=None,
    )

    assert selection.selected.lift_pass_product_id == "default-local"
    assert selection.selected.price_example is not None
    assert selection.selected.price_example.match_kind == "representative"
    assert [item.lift_pass_product_id for item in selection.alternatives] == [
        "broad-pass"
    ]


def test_exact_dates_compare_matching_adult_price_and_coverage() -> None:
    graph = _pass_graph()

    selection = select_pass(
        products=_products(graph),
        graph=graph,
        stay_destination_id="example",
        focus_ski_area_id="example-area",
        trip_start_date=date(2027, 2, 1),
        trip_end_date=date(2027, 2, 6),
    )

    assert selection.selected.lift_pass_product_id == "broad-pass"
    assert selection.selected.accessible_ski_area_ids == [
        "example-area",
        "other-area",
    ]
    assert selection.selected.accessible_piste_km == 100
    assert selection.selected.price_example is not None
    assert selection.selected.price_example.duration_days == 6
    assert selection.selected.price_example.match_kind == "exact_duration"


def test_exact_dates_do_not_imply_a_non_matching_tariff() -> None:
    graph = _pass_graph()

    selection = select_pass(
        products=_products(graph),
        graph=graph,
        stay_destination_id="example",
        focus_ski_area_id="example-area",
        trip_start_date=date(2027, 2, 1),
        trip_end_date=date(2027, 2, 4),
    )

    assert selection.selected.price_example is None
    assert all(item.price_example is None for item in selection.alternatives)


def test_pass_aggregate_is_display_only() -> None:
    graph = _pass_graph()
    payload = graph.snapshot.model_dump(mode="json")
    broad = next(
        item
        for item in payload["lift_pass_products"]
        if item["lift_pass_product_id"] == "broad-pass"
    )
    broad["lift_pass_product_id"] = "a-aggregate-pass"
    broad["terrain_domain_ids"] = []
    broad["valid_ski_area_ids"] = ["example-area", "other-area"]
    broad["pass_accessible_terrain"] = {
        "metric_scope": "pass_accessible",
        "total_piste_km": 150,
        "source_urls": ["https://example.com/pass-terrain"],
    }
    payload["lift_pass_products"] = [broad]
    aggregate_graph = CatalogGraph.from_snapshot(
        CatalogSnapshot.model_validate(payload)
    )

    selection = select_pass(
        products=_products(aggregate_graph),
        graph=aggregate_graph,
        stay_destination_id="example",
        focus_ski_area_id="example-area",
        trip_start_date=None,
        trip_end_date=None,
    )

    assert selection.selected.lift_pass_product_id == "a-aggregate-pass"
    assert selection.selected.accessible_piste_km == 150
    assert aggregate_graph.areas_by_id["example-area"].total_piste_km == 50


def test_stable_product_id_breaks_exact_ties() -> None:
    graph = _pass_graph()
    payload = graph.snapshot.model_dump(mode="json")
    local = next(
        item
        for item in payload["lift_pass_products"]
        if item["lift_pass_product_id"] == "default-local"
    )
    local["default_for_stay_destination_ids"] = []
    other = deepcopy(local)
    local["lift_pass_product_id"] = "z-local"
    other["lift_pass_product_id"] = "a-local"
    payload["lift_pass_products"] = [local, other]
    tied_graph = CatalogGraph.from_snapshot(CatalogSnapshot.model_validate(payload))

    selection = select_pass(
        products=_products(tied_graph),
        graph=tied_graph,
        stay_destination_id="example",
        focus_ski_area_id="example-area",
        trip_start_date=None,
        trip_end_date=None,
    )

    assert selection.selected.lift_pass_product_id == "a-local"
