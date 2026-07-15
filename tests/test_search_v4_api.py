from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.search_intent_policy import SearchIntentPolicyError
from app.domain.search_v4_service import SearchV4Response
from app.main import app

pytestmark = pytest.mark.db_free


def _request_payload() -> dict[str, object]:
    return {
        "intent": {
            "constraints": {
                "location": {"country": "France"},
                "travel_window": {
                    "start_date": "2027-01-16",
                    "end_date": "2027-01-20",
                },
            },
            "party": {"skill_levels": ["intermediate"]},
            "objectives": [{"factor_id": "pass_terrain_value", "importance": "normal"}],
        },
        "brief": "A good-value intermediate trip in France.",
        "generate_refinements": False,
    }


def test_post_search_accepts_typed_v4_contract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_search(**kwargs: object) -> SearchV4Response:
        captured.update(kwargs)
        intent = kwargs["intent"]
        return SearchV4Response(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            ranking_status="ranked",
            applied_intent=intent,
            eligible_candidate_count=0,
            excluded_candidate_count=10,
            results=(),
        )

    monkeypatch.setattr("app.api.routes.search_trip_configurations", fake_search)
    response = TestClient(app).post("/api/search", json=_request_payload())

    assert response.status_code == 200
    assert response.json()["search_model_version"] == "search-v4"
    assert captured["include_refinements"] is False
    assert captured["llm_client"] is None
    assert captured["brief"] == "A good-value intermediate trip in France."


def test_search_get_contract_is_removed() -> None:
    search_routes = [
        route for route in app.routes if getattr(route, "path", None) == "/api/search"
    ]

    assert len(search_routes) == 1
    assert search_routes[0].methods == {"POST"}


def test_post_search_rejects_untyped_raw_weights() -> None:
    payload = _request_payload()
    intent = payload["intent"]
    assert isinstance(intent, dict)
    intent["raw_weights"] = {"party_skill_coverage": 99}

    response = TestClient(app).post("/api/search", json=payload)

    assert response.status_code == 422


def test_post_search_maps_unregistered_intent_to_validation_error(monkeypatch) -> None:
    def reject_search(**_kwargs: object) -> SearchV4Response:
        raise SearchIntentPolicyError("unknown factor ID: invented")

    monkeypatch.setattr("app.api.routes.search_trip_configurations", reject_search)

    response = TestClient(app).post("/api/search", json=_request_payload())

    assert response.status_code == 422
    assert response.json()["detail"] == "unknown factor ID: invented"
