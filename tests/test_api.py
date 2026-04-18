from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.data.repositories import (
    CurrentTripRepository,
    OutboundBookingClickRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    ResortRepository,
)
from app.domain.models import (
    CurrentTrip,
    ResortConditions,
    ResortConditionSnapshot,
    snow_confidence_label_for_score,
)
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
    assert payload["results"][0]["selected_ski_area_name"]
    assert payload["results"][0]["selected_stay_base_name"]
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
                "selected_stay_base_name": "Le Lac",
                "selected_ski_area_name": "Tignes",
                "source_surface": "selected_result_details",
            },
            headers={
                "user-agent": "pytest-agent",
                "x-request-id": "req-123",
            },
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert (
        response.headers["location"]
        == "https://www.booking.com/searchresults.html?ss=Tignes%2C+France&group_adults=2&no_rooms=1&group_children=0"
    )

    repository = OutboundBookingClickRepository(db_path)
    clicks = repository.list_clicks()
    assert len(clicks) == 1
    assert clicks[0]["resort_id"] == "tignes"
    assert clicks[0]["selected_area_name"] == "Le Lac"
    assert clicks[0]["selected_ski_area_name"] == "Tignes"
    assert (
        clicks[0]["target_url"]
        == "https://www.booking.com/searchresults.html?ss=Tignes%2C+France&group_adults=2&no_rooms=1&group_children=0"
    )
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
                "selected_stay_base_name": top_result["selected_stay_base_name"],
                "selected_ski_area_name": top_result["selected_ski_area_name"],
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
            "selected_stay_base_name": "Le Lac",
            "selected_ski_area_name": "Tignes",
            "source_surface": "selected_result_details",
        },
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown resort_id"


def test_outbound_accommodation_redirect_rejects_unknown_stay_base() -> None:
    response = client.get(
        "/api/outbound/accommodation/tignes",
        params={
            "selected_stay_base_name": "Unknown Area",
            "selected_ski_area_name": "Tignes",
            "source_surface": "selected_result_details",
        },
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown selected_stay_base_name"


def test_current_trip_endpoints_save_read_and_clear(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()

    with TestClient(app_with_temp_db) as temp_client:
        get_empty = temp_client.get("/api/current-trip")
        assert get_empty.status_code == 200
        assert get_empty.json() == {"trip": None}

        save_response = temp_client.put(
            "/api/current-trip",
            json={
                "resort_id": "tignes",
                "selected_ski_area_name": "Tignes",
                "selected_stay_base_name": "Le Lac",
                "travel_month": 3,
                "booking_status": "booked_elsewhere",
            },
        )

        assert save_response.status_code == 200
        payload = save_response.json()
        assert payload["resort_id"] == "tignes"
        assert payload["resort_name"] == "Tignes"
        assert payload["selected_ski_area_name"] == "Tignes"
        assert payload["selected_stay_base_name"] == "Le Lac"
        assert payload["selected_area_name"] == "Le Lac"
        assert payload["travel_month"] == 3
        assert payload["booking_status"] == "booked_elsewhere"

        get_saved = temp_client.get("/api/current-trip")
        assert get_saved.status_code == 200
        assert get_saved.json()["trip"]["resort_id"] == "tignes"

        delete_response = temp_client.delete("/api/current-trip")
        assert delete_response.status_code == 204

        get_cleared = temp_client.get("/api/current-trip")
        assert get_cleared.status_code == 200
        assert get_cleared.json() == {"trip": None}

    assert CurrentTripRepository(db_path).get_current_trip() is None


def test_current_trip_rejects_unknown_area(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()

    with TestClient(app_with_temp_db) as temp_client:
        response = temp_client.put(
            "/api/current-trip",
            json={
                "resort_id": "tignes",
                "selected_ski_area_name": "Tignes",
                "selected_stay_base_name": "Unknown Area",
                "travel_month": 3,
                "booking_status": "booked_elsewhere",
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown selected_stay_base_name"


def _seed_trip_conditions_state(
    *,
    db_path: Path,
    trip_created_at: datetime,
    current_updated_at: datetime,
    prior_snapshot_at: datetime | None,
    prior_score: float = 0.55,
    current_score: float = 0.84,
    prior_status: str = "limited",
    current_status: str = "open",
    current_summary: str = "Fresh snowfall and strong visibility.",
) -> None:
    resort = ResortRepository(db_path).get_resort_by_id("tignes")
    assert resort is not None

    trip_repository = CurrentTripRepository(db_path)
    trip_repository.upsert_current_trip(
        CurrentTrip(
            resort_id=resort.resort_id,
            resort_name=resort.name,
            selected_ski_area_id=resort.ski_areas[0].ski_area_id,
            selected_ski_area_name=resort.ski_areas[0].name,
            selected_stay_base_name="Le Lac",
            selected_area_name="Le Lac",
            travel_month=3,
            booking_status="booked_elsewhere",
            created_at=trip_created_at.isoformat(),
            updated_at=trip_created_at.isoformat(),
            last_checked_at=None,
        )
    )

    current_conditions = ResortConditions(
        resort_name=resort.name,
        snow_confidence_score=current_score,
        snow_confidence_label=snow_confidence_label_for_score(current_score),
        availability_status=current_status,
        weather_summary=current_summary,
        conditions_score=current_score,
        updated_at=current_updated_at.isoformat(),
        source="open-meteo",
    )
    ResortConditionsRepository(db_path).upsert_conditions(
        entity_id=resort.ski_areas[0].ski_area_id,
        entity_name=resort.ski_areas[0].name,
        conditions=current_conditions,
    )

    if prior_snapshot_at is not None:
        prior_snapshot = ResortConditionSnapshot(
            resort_id=resort.ski_areas[0].ski_area_id,
            resort_name=resort.ski_areas[0].name,
            observed_month=prior_snapshot_at.month,
            observed_at=prior_snapshot_at.isoformat(),
            snow_confidence_score=prior_score,
            snow_confidence_label=snow_confidence_label_for_score(prior_score),
            availability_status=prior_status,
            weather_summary="Earlier conditions were mixed.",
            conditions_score=prior_score,
            source="open-meteo",
        )
        ResortConditionHistoryRepository(db_path).append_snapshot(
            snapshot=prior_snapshot
        )


def test_current_trip_summary_returns_404_without_saved_trip(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()

    with TestClient(app_with_temp_db) as temp_client:
        response = temp_client.get("/api/current-trip/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "No current trip saved"


def test_current_trip_summary_returns_conditions_and_delta(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        db_path=db_path,
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at + timedelta(days=1),
        prior_snapshot_at=trip_created_at - timedelta(hours=6),
    )

    with TestClient(app_with_temp_db) as temp_client:
        response = temp_client.get("/api/current-trip/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trip"]["resort_id"] == "tignes"
    assert payload["comparison_basis"]["kind"] == "since_trip_saved"
    assert payload["current_conditions_provenance"]["source_type"] == "forecast"
    assert payload["delta"]["status"] == "changed"
    assert any(
        "Snow confidence improved" in change for change in payload["delta"]["changes"]
    )
    assert any(
        "Availability changed" in change for change in payload["delta"]["changes"]
    )


def test_current_trip_summary_uses_last_checked_at_when_present(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        db_path=db_path,
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at + timedelta(days=2),
        prior_snapshot_at=trip_created_at + timedelta(hours=12),
    )
    CurrentTripRepository(db_path).mark_checked(
        checked_at=(trip_created_at + timedelta(days=1)).isoformat()
    )

    with TestClient(app_with_temp_db) as temp_client:
        response = temp_client.get("/api/current-trip/summary")

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["trip"]["last_checked_at"]
        == (trip_created_at + timedelta(days=1)).isoformat()
    )
    assert payload["comparison_basis"]["kind"] == "since_last_check"


def test_current_trip_summary_handles_sparse_history_gracefully(
    monkeypatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        db_path=db_path,
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at + timedelta(days=1),
        prior_snapshot_at=None,
    )

    with TestClient(app_with_temp_db) as temp_client:
        response = temp_client.get("/api/current-trip/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["delta"]["status"] == "insufficient_history"
    assert "not enough earlier history" in payload["delta"]["summary"].lower()


def test_mark_checked_updates_only_last_checked_at(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "planner.db"
    monkeypatch.setenv("APP_DB_PATH", str(db_path))
    app_with_temp_db = create_app()
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        db_path=db_path,
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at + timedelta(hours=6),
        prior_snapshot_at=None,
    )
    before = CurrentTripRepository(db_path).get_current_trip()
    assert before is not None

    with TestClient(app_with_temp_db) as temp_client:
        response = temp_client.post("/api/current-trip/mark-checked")

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_checked_at"] is not None
    assert payload["created_at"] == before.created_at
    assert payload["updated_at"] == before.updated_at


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

    app_with_frontend = create_app(frontend_dist_dir=dist_dir)

    with TestClient(app_with_frontend) as frontend_client:
        response = frontend_client.get("/")

    assert response.status_code == 200
    assert "frontend" in response.text


def test_app_starts_against_configurable_database_url(tmp_path, monkeypatch) -> None:
    database_url = (
        "postgresql://planner:planner@127.0.0.1:5432/ai_sports_travel_planner_test"
    )
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>frontend</html>", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", database_url)

    app_with_frontend = create_app(frontend_dist_dir=dist_dir)

    with TestClient(app_with_frontend) as frontend_client:
        response = frontend_client.get("/api/readyz")

    assert response.status_code == 200
