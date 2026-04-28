from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from app.ai.parser import HeuristicQueryParser, get_query_parser
from app.auth.google import GoogleIdentity, GoogleIdentityTokenError
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


def _install_google_verifier(
    monkeypatch,
    *,
    identities_by_token: dict[str, GoogleIdentity],
) -> None:
    def _verify(identity_token: str) -> GoogleIdentity:
        if identity_token not in identities_by_token:
            raise GoogleIdentityTokenError("google identity token is invalid")
        return identities_by_token[identity_token]

    monkeypatch.setattr("app.api.routes.verify_google_identity_token", _verify)


def _sign_in(
    *,
    identity_token: str,
) -> tuple[dict[str, str], dict]:
    response = client.post(
        "/api/auth/google/sign-in",
        json={"identity_token": identity_token},
    )
    assert response.status_code == 200
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload


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
    assert result["planning_provenance"]["evidence_profile"] in {
        "archive_backed",
        "fallback_heavy",
    }


def test_search_accepts_exact_date_range_and_returns_planning_fields() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "trip_start_date": "2026-03-08",
            "trip_end_date": "2026-03-12",
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert "planning_summary" in result
    assert result["planning_provenance"]["evidence_profile"] in {
        "forecast_assisted",
        "archive_backed",
        "fallback_heavy",
    }


def test_search_exact_date_range_takes_precedence_over_travel_month() -> None:
    date_range_response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "trip_start_date": "2026-03-08",
            "trip_end_date": "2026-03-12",
        },
    )
    conflicting_response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "travel_month": 1,
            "trip_start_date": "2026-03-08",
            "trip_end_date": "2026-03-12",
        },
    )

    assert date_range_response.status_code == 200
    assert conflicting_response.status_code == 200
    assert (
        date_range_response.json()["results"][0]["planning_summary"]
        == conflicting_response.json()["results"][0]["planning_summary"]
    )


def test_search_rejects_partial_exact_date_window() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "trip_start_date": "2026-03-08",
        },
    )

    assert response.status_code == 422


def test_search_rejects_invalid_exact_date_window() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "trip_start_date": "2026-03-12",
            "trip_end_date": "2026-03-08",
        },
    )

    assert response.status_code == 422


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


def test_parse_query_returns_exact_date_filters() -> None:
    app.dependency_overrides[get_query_parser] = lambda: HeuristicQueryParser(
        reference_date=date(2026, 1, 1)
    )
    try:
        response = client.post(
            "/api/parse-query",
            json={"query": "france ski trip 9 Apr to 16 Apr for intermediate"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["filters"]["trip_start_date"] == "2026-04-09"
    assert payload["filters"]["trip_end_date"] == "2026-04-16"
    assert "travel_month" not in payload["filters"]


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


def test_outbound_accommodation_redirect_records_click() -> None:
    response = client.get(
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

    repository = OutboundBookingClickRepository()
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


def test_month_aware_search_and_booking_redirect_work_together() -> None:
    search_response = client.get(
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

    redirect_response = client.get(
        f"/api/outbound/accommodation/{top_result['resort_id']}",
        params={
            "selected_stay_base_name": top_result["selected_stay_base_name"],
            "selected_ski_area_name": top_result["selected_ski_area_name"],
            "source_surface": "selected_result_details",
        },
        follow_redirects=False,
    )

    assert redirect_response.status_code == 307
    repository = OutboundBookingClickRepository()
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


def test_google_sign_in_creates_session_and_reuses_user(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token-a": GoogleIdentity(
                subject="google-sub-a",
                email="user@example.com",
                display_name="Example User",
                audience="mobile-client-id",
            ),
            "google-token-b": GoogleIdentity(
                subject="google-sub-a",
                email="user@example.com",
                display_name="Updated Name",
                audience="mobile-client-id",
            ),
        },
    )

    first_response = client.post(
        "/api/auth/google/sign-in",
        json={"identity_token": "google-token-a"},
    )
    second_response = client.post(
        "/api/auth/google/sign-in",
        json={"identity_token": "google-token-b"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_payload = first_response.json()
    second_payload = second_response.json()
    assert first_payload["user"]["email"] == "user@example.com"
    assert second_payload["user"]["display_name"] == "Updated Name"
    assert first_payload["user"]["user_id"] == second_payload["user"]["user_id"]
    assert first_payload["access_token"] != second_payload["access_token"]


def test_google_sign_in_rejects_invalid_token(monkeypatch) -> None:
    _install_google_verifier(monkeypatch, identities_by_token={})

    response = client.post(
        "/api/auth/google/sign-in",
        json={"identity_token": "bad-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "google identity token is invalid"


def test_current_trip_endpoints_require_authentication() -> None:
    assert client.get("/api/current-trip").status_code == 401
    assert (
        client.put(
            "/api/current-trip",
            json={
                "resort_id": "tignes",
                "selected_ski_area_name": "Tignes",
                "selected_stay_base_name": "Le Lac",
                "travel_month": 3,
                "booking_status": "booked_elsewhere",
            },
        ).status_code
        == 401
    )
    assert client.get("/api/current-trip/summary").status_code == 401
    assert client.post("/api/current-trip/mark-checked").status_code == 401
    assert client.delete("/api/current-trip").status_code == 401


def test_current_trip_endpoints_save_read_and_clear(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, session = _sign_in(identity_token="google-token")

    get_empty = client.get("/api/current-trip", headers=headers)
    assert get_empty.status_code == 200
    assert get_empty.json() == {"trip": None}

    save_response = client.put(
        "/api/current-trip",
        json={
            "resort_id": "tignes",
            "selected_ski_area_name": "Tignes",
            "selected_stay_base_name": "Le Lac",
            "travel_month": 3,
            "trip_start_date": "2026-03-08",
            "trip_end_date": "2026-03-12",
            "booking_status": "booked_elsewhere",
        },
        headers=headers,
    )

    assert save_response.status_code == 200
    payload = save_response.json()
    assert payload["resort_id"] == "tignes"
    assert payload["resort_name"] == "Tignes"
    assert payload["selected_ski_area_name"] == "Tignes"
    assert payload["selected_stay_base_name"] == "Le Lac"
    assert payload["selected_area_name"] == "Le Lac"
    assert payload["travel_month"] == 3
    assert payload["trip_start_date"] == "2026-03-08"
    assert payload["trip_end_date"] == "2026-03-12"
    assert payload["booking_status"] == "booked_elsewhere"

    get_saved = client.get("/api/current-trip", headers=headers)
    assert get_saved.status_code == 200
    assert get_saved.json()["trip"]["resort_id"] == "tignes"

    delete_response = client.delete("/api/current-trip", headers=headers)
    assert delete_response.status_code == 204

    get_cleared = client.get("/api/current-trip", headers=headers)
    assert get_cleared.status_code == 200
    assert get_cleared.json() == {"trip": None}

    assert (
        CurrentTripRepository().get_current_trip(user_id=session["user"]["user_id"])
        is None
    )


def test_current_trip_rejects_unknown_area(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, _ = _sign_in(identity_token="google-token")

    response = client.put(
        "/api/current-trip",
        json={
            "resort_id": "tignes",
            "selected_ski_area_name": "Tignes",
            "selected_stay_base_name": "Unknown Area",
            "travel_month": 3,
            "booking_status": "booked_elsewhere",
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown selected_stay_base_name"


def test_current_trip_rejects_partial_trip_window(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, _ = _sign_in(identity_token="google-token")

    response = client.put(
        "/api/current-trip",
        json={
            "resort_id": "tignes",
            "selected_ski_area_name": "Tignes",
            "selected_stay_base_name": "Le Lac",
            "trip_start_date": "2026-03-08",
            "booking_status": "booked_elsewhere",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_current_trip_rejects_invalid_trip_window(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, _ = _sign_in(identity_token="google-token")

    response = client.put(
        "/api/current-trip",
        json={
            "resort_id": "tignes",
            "selected_ski_area_name": "Tignes",
            "selected_stay_base_name": "Le Lac",
            "trip_start_date": "2026-03-12",
            "trip_end_date": "2026-03-08",
            "booking_status": "booked_elsewhere",
        },
        headers=headers,
    )

    assert response.status_code == 422


def _seed_trip_conditions_state(
    *,
    user_id: str,
    trip_created_at: datetime,
    current_updated_at: datetime,
    prior_snapshot_at: datetime | None,
    trip_start_date: date | None = None,
    trip_end_date: date | None = None,
    prior_score: float = 0.55,
    current_score: float = 0.84,
    prior_status: str = "limited",
    current_status: str = "open",
    current_summary: str = "Fresh snowfall and strong visibility.",
) -> None:
    resort = ResortRepository().get_resort_by_id("tignes")
    assert resort is not None

    trip_repository = CurrentTripRepository()
    trip_repository.upsert_current_trip(
        user_id=user_id,
        trip=CurrentTrip(
            resort_id=resort.resort_id,
            resort_name=resort.name,
            selected_ski_area_id=resort.ski_areas[0].ski_area_id,
            selected_ski_area_name=resort.ski_areas[0].name,
            selected_stay_base_name="Le Lac",
            selected_area_name="Le Lac",
            travel_month=3,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
            booking_status="booked_elsewhere",
            created_at=trip_created_at.isoformat(),
            updated_at=trip_created_at.isoformat(),
            last_checked_at=None,
        ),
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
    ResortConditionsRepository().upsert_conditions(
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
        ResortConditionHistoryRepository().append_snapshot(snapshot=prior_snapshot)


def test_current_trip_isolated_per_user(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token-a": GoogleIdentity(
                subject="google-sub-a",
                email="a@example.com",
                display_name="User A",
                audience="mobile-client-id",
            ),
            "google-token-b": GoogleIdentity(
                subject="google-sub-b",
                email="b@example.com",
                display_name="User B",
                audience="mobile-client-id",
            ),
        },
    )
    headers_a, _ = _sign_in(identity_token="google-token-a")
    headers_b, _ = _sign_in(identity_token="google-token-b")

    save_a = client.put(
        "/api/current-trip",
        json={
            "resort_id": "tignes",
            "selected_ski_area_name": "Tignes",
            "selected_stay_base_name": "Le Lac",
            "travel_month": 3,
            "booking_status": "booked_elsewhere",
        },
        headers=headers_a,
    )
    save_b = client.put(
        "/api/current-trip",
        json={
            "resort_id": "cervinia",
            "selected_ski_area_name": "Cervinia",
            "selected_stay_base_name": "Breuil-Cervinia",
            "travel_month": 2,
            "booking_status": "not_booked_yet",
        },
        headers=headers_b,
    )

    assert save_a.status_code == 200
    assert save_b.status_code == 200
    assert (
        client.get("/api/current-trip", headers=headers_a).json()["trip"]["resort_id"]
        == "tignes"
    )
    assert (
        client.get("/api/current-trip", headers=headers_b).json()["trip"]["resort_id"]
        == "cervinia"
    )


def test_current_trip_summary_returns_404_without_saved_trip(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, _ = _sign_in(identity_token="google-token")

    response = client.get("/api/current-trip/summary", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "No current trip saved"


def test_current_trip_summary_returns_conditions_and_delta(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, session = _sign_in(identity_token="google-token")
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        user_id=session["user"]["user_id"],
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at + timedelta(days=1),
        prior_snapshot_at=trip_created_at - timedelta(hours=6),
    )

    response = client.get("/api/current-trip/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["trip"]["resort_id"] == "tignes"
    assert payload["comparison_basis"]["kind"] == "since_trip_saved"
    assert payload["current_conditions_provenance"]["source_type"] == "forecast"
    assert payload["delta"]["status"] == "changed"
    assert payload["companion_status"]["trip_window_status"] == "unscheduled"
    assert payload["companion_status"]["notification_eligible"] is False
    assert any(
        "Snow confidence improved" in change for change in payload["delta"]["changes"]
    )
    assert any(
        "Availability changed" in change for change in payload["delta"]["changes"]
    )


def test_current_trip_summary_uses_last_checked_at_when_present(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, session = _sign_in(identity_token="google-token")
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        user_id=session["user"]["user_id"],
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at + timedelta(days=2),
        prior_snapshot_at=trip_created_at + timedelta(hours=12),
    )
    CurrentTripRepository().mark_checked(
        user_id=session["user"]["user_id"],
        checked_at=(trip_created_at + timedelta(days=1)).isoformat(),
    )

    response = client.get("/api/current-trip/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["trip"]["last_checked_at"]
        == (trip_created_at + timedelta(days=1)).isoformat()
    )
    assert payload["comparison_basis"]["kind"] == "since_last_check"


def test_current_trip_summary_handles_sparse_history_gracefully(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, session = _sign_in(identity_token="google-token")
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        user_id=session["user"]["user_id"],
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at + timedelta(days=1),
        prior_snapshot_at=None,
    )

    response = client.get("/api/current-trip/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["delta"]["status"] == "insufficient_history"
    assert "not enough earlier history" in payload["delta"]["summary"].lower()


def test_mark_checked_updates_only_last_checked_at(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, session = _sign_in(identity_token="google-token")
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        user_id=session["user"]["user_id"],
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at + timedelta(hours=6),
        prior_snapshot_at=None,
    )
    before = CurrentTripRepository().get_current_trip(
        user_id=session["user"]["user_id"]
    )
    assert before is not None

    response = client.post("/api/current-trip/mark-checked", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_checked_at"] is not None
    assert payload["created_at"] == before.created_at
    assert payload["updated_at"] == before.updated_at


def test_current_trip_summary_classifies_upcoming_trip_as_notification_eligible(
    monkeypatch,
) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, session = _sign_in(identity_token="google-token")
    trip_created_at = datetime.now(UTC) - timedelta(hours=2)
    trip_start = datetime.now(UTC).date() + timedelta(days=2)
    trip_end = trip_start + timedelta(days=4)
    _seed_trip_conditions_state(
        user_id=session["user"]["user_id"],
        trip_created_at=trip_created_at,
        current_updated_at=datetime.now(UTC),
        prior_snapshot_at=trip_created_at - timedelta(hours=4),
        trip_start_date=trip_start,
        trip_end_date=trip_end,
    )

    response = client.get("/api/current-trip/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["trip"]["trip_start_date"] == trip_start.isoformat()
    assert payload["trip"]["trip_end_date"] == trip_end.isoformat()
    assert payload["companion_status"]["trip_window_status"] == "upcoming"
    assert payload["companion_status"]["notification_eligible"] is True
    assert payload["companion_status"]["actionable_change_available"] is True


def test_current_trip_summary_suppresses_notifications_for_past_trip(
    monkeypatch,
) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, session = _sign_in(identity_token="google-token")
    trip_created_at = datetime.now(UTC) - timedelta(days=10)
    trip_end = datetime.now(UTC).date() - timedelta(days=1)
    trip_start = trip_end - timedelta(days=4)
    _seed_trip_conditions_state(
        user_id=session["user"]["user_id"],
        trip_created_at=trip_created_at,
        current_updated_at=datetime.now(UTC),
        prior_snapshot_at=trip_created_at - timedelta(hours=4),
        trip_start_date=trip_start,
        trip_end_date=trip_end,
    )

    response = client.get("/api/current-trip/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["companion_status"]["trip_window_status"] == "past"
    assert payload["companion_status"]["notification_eligible"] is False
    assert payload["companion_status"]["actionable_change_available"] is False


def test_current_trip_events_record_meaningful_change_once(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token": GoogleIdentity(
                subject="google-sub-1",
                email="trip-user@example.com",
                display_name="Trip User",
                audience="mobile-client-id",
            )
        },
    )
    headers, session = _sign_in(identity_token="google-token")
    trip_created_at = datetime.now(UTC) - timedelta(hours=2)
    trip_start = datetime.now(UTC).date()
    trip_end = trip_start + timedelta(days=3)
    _seed_trip_conditions_state(
        user_id=session["user"]["user_id"],
        trip_created_at=trip_created_at,
        current_updated_at=datetime.now(UTC),
        prior_snapshot_at=trip_created_at - timedelta(hours=4),
        trip_start_date=trip_start,
        trip_end_date=trip_end,
    )

    first = client.get("/api/current-trip/events", headers=headers)
    second = client.get("/api/current-trip/events", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()["events"]) == 1
    assert len(second.json()["events"]) == 1
    assert first.json()["events"][0]["actionable"] is True
    assert first.json()["events"][0]["event_type"] == "conditions_change"


def test_device_registration_is_authenticated_and_user_owned(monkeypatch) -> None:
    _install_google_verifier(
        monkeypatch,
        identities_by_token={
            "google-token-a": GoogleIdentity(
                subject="google-sub-a",
                email="a@example.com",
                display_name="User A",
                audience="mobile-client-id",
            ),
            "google-token-b": GoogleIdentity(
                subject="google-sub-b",
                email="b@example.com",
                display_name="User B",
                audience="mobile-client-id",
            ),
        },
    )

    unauthorized = client.post(
        "/api/devices/register",
        json={"installation_id": "ios-user-a", "platform": "ios"},
    )
    assert unauthorized.status_code == 401

    headers_a, _ = _sign_in(identity_token="google-token-a")
    headers_b, _ = _sign_in(identity_token="google-token-b")

    response_a = client.post(
        "/api/devices/register",
        json={
            "installation_id": "ios-user-a",
            "platform": "ios",
            "push_enabled": True,
        },
        headers=headers_a,
    )
    response_b = client.post(
        "/api/devices/register",
        json={
            "installation_id": "ios-user-a",
            "platform": "ios",
            "push_enabled": False,
        },
        headers=headers_b,
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.json()["installation_id"] == "ios-user-a"
    assert response_a.json()["push_enabled"] is True
    assert response_b.json()["installation_id"] == "ios-user-a"
    assert response_b.json()["push_enabled"] is False


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
