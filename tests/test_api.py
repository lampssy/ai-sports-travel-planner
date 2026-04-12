from pathlib import Path

from fastapi.testclient import TestClient

from app.data.repositories import OutboundBookingClickRepository
from app.main import app, create_app

client = TestClient(app)


def test_recommend_activities_rejects_invalid_sport() -> None:
    response = client.get(
        "/api/recommend-activities",
        params={
            "sport": "cycling",
            "region": "Alps",
            "difficulty": "beginner",
        },
    )

    assert response.status_code == 422


def test_search_returns_ranked_results_with_new_filters() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "lift_distance": "medium",
            "budget_flex": 0.1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert payload["results"][0]["selected_area_lift_distance"] in {"near", "medium"}
    assert payload["results"][0]["budget_penalty"] >= 0
    assert payload["results"][0]["conditions_summary"]
    assert 0 <= payload["results"][0]["snow_confidence_score"] <= 1
    assert payload["results"][0]["snow_confidence_label"] in {"poor", "fair", "good"}
    assert payload["results"][0]["availability_status"] in {
        "open",
        "limited",
        "temporarily_closed",
        "out_of_season",
    }
    assert payload["results"][0]["explanation"]["highlights"]
    assert payload["results"][0]["recommendation_confidence"] >= 0
    assert "recommendation_narrative" in payload["results"][0]
    assert payload["results"][0]["resort_id"]
    assert payload["results"][0]["region"]
    assert payload["results"][0]["conditions_provenance"]["source_type"] in {
        "forecast",
        "estimated",
    }
    assert payload["results"][0]["conditions_provenance"]["freshness_status"] in {
        "fresh",
        "stale",
        "unknown",
    }


def test_search_accepts_optional_travel_month_and_returns_planning_fields() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "travel_month": 2,
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert "planning_summary" in result
    assert "planning_provenance" in result
    assert "planning_evidence_count" in result
    assert "best_travel_months" in result
    assert result["planning_provenance"]["source_type"] == "estimated"
    assert (
        result["planning_provenance"]["source_name"] == "snapshot_history+seasonality"
    )


def test_search_rejects_invalid_skill_level() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "Austria",
            "min_price": 150,
            "max_price": 220,
            "stars": 2,
            "skill_level": "expert",
        },
    )

    assert response.status_code == 422


def test_search_rejects_invalid_lift_distance() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "Austria",
            "min_price": 150,
            "max_price": 220,
            "stars": 2,
            "skill_level": "intermediate",
            "lift_distance": "walkable",
        },
    )

    assert response.status_code == 422


def test_search_rejects_invalid_budget_flex() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "Austria",
            "min_price": 150,
            "max_price": 220,
            "stars": 2,
            "skill_level": "intermediate",
            "budget_flex": 0.6,
        },
    )

    assert response.status_code == 422


def test_search_rejects_invalid_price_interval() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "Austria",
            "min_price": 250,
            "max_price": 200,
            "stars": 2,
            "skill_level": "intermediate",
        },
    )

    assert response.status_code == 422


def test_parse_query_returns_structured_filters_and_confidence() -> None:
    response = client.post(
        "/api/parse-query",
        json={"query": "cheap france ski trip close to lift in march for intermediate"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "filters" in payload
    assert "confidence" in payload
    assert "unknown_parts" in payload
    assert 0 <= payload["confidence"] <= 1
    if "travel_month" in payload["filters"]:
        assert payload["filters"]["travel_month"] == 3


def test_parse_query_debug_includes_parser_metadata() -> None:
    response = client.post(
        "/api/parse-query?debug=true",
        json={"query": "cheap france ski trip close to lift for intermediate"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "debug" in payload
    assert payload["debug"]["parser_source"] in {
        "llm",
        "llm_cache",
        "heuristic_fallback",
    }
    assert "fallback_reason" in payload["debug"]
    assert "raw_response_preview" in payload["debug"]


def test_search_contract_returns_required_semantic_fields() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert "recommendation_reasons" not in result
    assert "tradeoff_summary" not in result
    assert result["explanation"]["highlights"]
    assert isinstance(result["explanation"]["risks"], list)
    assert result["explanation"]["confidence_contributors"]
    assert {
        contributor["direction"]
        for contributor in result["explanation"]["confidence_contributors"]
    } <= {"positive", "negative"}
    assert 0 <= result["conditions_score"] <= 1
    assert 0 <= result["snow_confidence_score"] <= 1
    assert result["snow_confidence_label"] in {"poor", "fair", "good"}
    assert result["availability_status"] in {
        "open",
        "limited",
        "temporarily_closed",
        "out_of_season",
    }
    assert 0 <= result["recommendation_confidence"] <= 1
    assert result["budget_penalty"] >= 0
    assert "conditions_provenance" in result
    assert result["conditions_provenance"]["basis_summary"]
    assert result["recommendation_narrative"] is None or isinstance(
        result["recommendation_narrative"], str
    )


def test_outbound_accommodation_redirect_records_click(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()

    with TestClient(app_with_temp_db) as temp_client:
        response = temp_client.get(
            "/api/outbound/accommodation/tignes",
            params={
                "selected_area_name": "Le Lac",
                "source_surface": "selected_result_details",
            },
            headers={
                "user-agent": "pytest-agent",
                "x-request-id": "req-123",
            },
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/search?q=Tignes+France"

    repository = OutboundBookingClickRepository(db_path)
    clicks = repository.list_clicks()
    assert len(clicks) == 1
    assert clicks[0]["resort_id"] == "tignes"
    assert clicks[0]["selected_area_name"] == "Le Lac"
    assert clicks[0]["target_url"] == "https://example.com/search?q=Tignes+France"
    assert clicks[0]["source_surface"] == "selected_result_details"
    assert clicks[0]["request_id"] == "req-123"
    assert clicks[0]["user_agent"] == "pytest-agent"


def test_month_aware_search_and_booking_redirect_work_together(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()

    with TestClient(app_with_temp_db) as temp_client:
        search_response = temp_client.get(
            "/api/search",
            params={
                "location": "France",
                "min_price": 150,
                "max_price": 320,
                "stars": 1,
                "skill_level": "intermediate",
                "travel_month": 2,
            },
        )

        assert search_response.status_code == 200
        top_result = search_response.json()["results"][0]

        redirect_response = temp_client.get(
            f"/api/outbound/accommodation/{top_result['resort_id']}",
            params={
                "selected_area_name": top_result["selected_area_name"],
                "source_surface": "selected_result_details",
            },
            follow_redirects=False,
        )

    assert redirect_response.status_code == 307
    repository = OutboundBookingClickRepository(db_path)
    clicks = repository.list_clicks()
    assert len(clicks) == 1
    assert clicks[0]["resort_id"] == top_result["resort_id"]


def test_outbound_accommodation_redirect_rejects_unknown_resort_id() -> None:
    response = client.get(
        "/api/outbound/accommodation/unknown-resort",
        params={
            "selected_area_name": "Le Lac",
            "source_surface": "selected_result_details",
        },
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown resort_id"


def test_search_populates_narrative_only_for_top_result(monkeypatch) -> None:
    class StubNarrativeGenerator:
        def generate(self, result) -> str | None:
            return f"{result.resort_name} is the strongest overall recommendation."

    monkeypatch.setattr(
        "app.domain.services.get_narrative_generator",
        lambda: StubNarrativeGenerator(),
    )

    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
        },
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert isinstance(results[0]["recommendation_narrative"], str)
    assert all(result["recommendation_narrative"] is None for result in results[1:])


def test_search_debug_includes_narrative_metadata(monkeypatch) -> None:
    class StubNarrativeGenerator:
        def generate(self, result) -> str | None:
            return "unused"

        def generate_with_debug(self, result):
            return (
                f"{result.resort_name} is the strongest overall recommendation.",
                {
                    "narrative_source": "llm",
                    "narrative_cache_hit": False,
                    "narrative_error": None,
                    "narrative_model": "stub-model",
                    "top_result_resort_id": result.resort_id,
                },
            )

    monkeypatch.setattr(
        "app.domain.services.get_narrative_generator",
        lambda: StubNarrativeGenerator(),
    )

    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "debug": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "debug" in payload
    assert payload["debug"]["narrative_source"] == "llm"
    assert "results" in payload


def test_healthz_returns_ok() -> None:
    response = client.get("/api/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_ok() -> None:
    response = client.get("/api/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_serves_built_frontend_from_single_url(tmp_path, monkeypatch) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>frontend</html>", encoding="utf-8")
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "planner.db"))

    app_with_frontend = create_app(frontend_dist_dir=dist_dir)

    with TestClient(app_with_frontend) as frontend_client:
        response = frontend_client.get("/")

    assert response.status_code == 200
    assert "frontend" in response.text


def test_app_bootstraps_against_configurable_sqlite_path(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "runtime" / "planner.db"
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>frontend</html>", encoding="utf-8")
    monkeypatch.setenv("APP_DB_PATH", str(db_path))

    app_with_frontend = create_app(frontend_dist_dir=dist_dir)

    with TestClient(app_with_frontend) as frontend_client:
        response = frontend_client.get("/api/readyz")

    assert response.status_code == 200
    assert db_path.exists()
