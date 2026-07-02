from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.ai.parser import HeuristicQueryParser, get_query_parser
from app.auth.google import GoogleIdentity, GoogleIdentityTokenError
from app.data.catalog_loader import load_catalog
from app.data.catalog_sync import sync_catalog_snapshot
from app.data.repositories import (
    CurrentTripRepository,
    OutboundBookingClickRepository,
    RawWeatherHistoryRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    ResortRepository,
)
from app.domain.models import (
    CurrentTrip,
    RawWeatherObservation,
    ResortConditions,
    ResortConditionSnapshot,
    snow_confidence_label_for_score,
)
from app.main import app, create_app

client = TestClient(app)
LEGACY_SEARCH_TESTS = {
    "test_month_aware_search_and_booking_redirect_work_together",
    "test_search_populates_narrative_only_for_top_result",
    "test_search_debug_includes_narrative_metadata",
    "test_search_debug_includes_search_model_metadata",
}


@pytest.fixture(autouse=True)
def sync_normalized_catalog_for_search_tests(
    request: pytest.FixtureRequest,
    reset_postgres_database: None,
) -> None:
    if request.node.name in LEGACY_SEARCH_TESTS:
        return
    needs_normalized_catalog = (
        request.node.name.startswith("test_search")
        or request.node.name.startswith("test_month_aware_search")
        or request.node.name.startswith("test_current_trip")
        or request.node.name.startswith("test_mark_checked")
    )
    if needs_normalized_catalog:
        sync_catalog_snapshot(load_catalog())


def _top_configuration(payload: dict) -> dict:
    return payload["results"][0]["top_configuration"]


def _tignes_trip_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ski_region_id": "tignes-val-disere",
        "ski_region_name": "Tignes - Val d'Isere",
        "stay_destination_id": "tignes",
        "stay_destination_name": "Tignes",
        "stay_base_id": "tignes-le-lac",
        "stay_base_name": "Le Lac",
        "focus_ski_area_id": "tignes-ski-area",
        "focus_ski_area_name": "Tignes",
        "lift_pass_product_id": "tignes-val-disere-ski-pass",
        "lift_pass_product_name": "Tignes - Val d'Isere ski pass",
        "travel_month": 3,
        "booking_status": "booked_elsewhere",
    }
    payload.update(updates)
    return payload


def _cervinia_trip_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ski_region_id": "cervinia",
        "ski_region_name": "Cervinia",
        "stay_destination_id": "cervinia",
        "stay_destination_name": "Cervinia",
        "stay_base_id": "cervinia-breuil-cervinia",
        "stay_base_name": "Breuil-Cervinia",
        "focus_ski_area_id": "cervinia-ski-area",
        "focus_ski_area_name": "Cervinia",
        "lift_pass_product_id": "cervinia-valtournenche-skipass",
        "lift_pass_product_name": "Breuil-Cervinia Valtournenche Ski Pass",
        "travel_month": 2,
        "booking_status": "not_booked_yet",
    }
    payload.update(updates)
    return payload


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


def _raw_weather_observation(
    *,
    ski_area_id: str,
    resort_name: str,
    observed_on: str,
    snowfall_cm: float,
    snow_depth_m: float,
    max_temp_c: float,
    gust_kmh: float,
    elevation_band: str = "mid",
    elevation_m: int = 2500,
) -> RawWeatherObservation:
    return RawWeatherObservation(
        ski_area_id=ski_area_id,
        resort_name=resort_name,
        elevation_band=elevation_band,
        elevation_m=elevation_m,
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
        snowfall_cm=snowfall_cm,
        snow_depth_m=snow_depth_m,
        temperature_2m_max_c=max_temp_c,
        temperature_2m_min_c=max_temp_c - 6,
        wind_speed_10m_max_kmh=max(gust_kmh - 8, 0),
        wind_gusts_10m_max_kmh=gust_kmh,
        weather_code=3,
        record_type="archive",
        source="open-meteo",
        source_model="best_match",
    )


def _seed_france_archive_weather() -> None:
    raw_repository = RawWeatherHistoryRepository()
    for resort in ResortRepository().list_resorts():
        if resort.country != "France" or not resort.ski_areas:
            continue
        ski_area = resort.ski_areas[0]
        raw_repository.upsert_observation(
            _raw_weather_observation(
                ski_area_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
                observed_on="2024-03-05",
                snowfall_cm=9,
                snow_depth_m=1.4,
                max_temp_c=-4,
                gust_kmh=24,
            )
        )
        raw_repository.upsert_observation(
            _raw_weather_observation(
                ski_area_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
                observed_on="2025-03-08",
                snowfall_cm=7,
                snow_depth_m=1.2,
                max_temp_c=-2,
                gust_kmh=28,
            )
        )


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
    group = payload["results"][0]
    result = group["top_configuration"]
    assert group["score"] == result["score"]
    assert group["ski_region_id"]
    assert result["focus_ski_area_id"]
    assert result["stay_destination_id"]
    assert result["stay_base_id"]
    assert result["access"]["lift_distance"] in {"near", "medium"}
    assert result["budget_penalty"] >= 0
    assert result["conditions_summary"]
    assert 0 <= result["snow_confidence_score"] <= 1
    assert result["explanation"]["highlights"]
    assert result["selected_pass"]["lift_pass_product_id"]
    assert result["resilience"]["ranking_component"] == 0
    assert result["evidence_quality"]["source_type"] in {
        "forecast",
        "estimated",
    }
    assert result["evidence_quality"]["freshness_status"] in {
        "fresh",
        "stale",
        "unknown",
    }


def test_search_response_includes_grouped_trip_option_fields() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 120,
            "max_price": 340,
            "stars": 1,
            "skill_level": "intermediate",
        },
    )

    assert response.status_code == 200
    group = response.json()["results"][0]
    assert group["top_configuration"]["ski_region_id"] == group["ski_region_id"]
    assert group["top_configuration"]["score"] == group["score"]
    assert isinstance(group["alternative_configurations"], list)
    assert isinstance(group["top_configuration"]["alternative_passes"], list)


def test_search_serializes_stable_normalized_identifiers() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "Italy",
            "min_price": 0,
            "max_price": 1_000,
            "stars": 1,
            "skill_level": "intermediate",
        },
    )

    assert response.status_code == 200
    result = _top_configuration(response.json())
    assert result["stay_destination_id"]
    assert result["stay_base_id"]
    assert result["focus_ski_area_id"]
    assert result["configuration_id"] == result["access"]["ski_area_access_id"]


def test_search_accepts_origin_and_returns_travel_effort() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "origin_text": "Munich",
            "travel_tolerance": "medium",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    travel_effort = _top_configuration(payload)["travel_effort"]
    assert travel_effort is not None
    assert travel_effort["origin_label"] == "Munich"
    assert travel_effort["mode"] == "car"
    assert travel_effort["duration_minutes"] > 0
    assert travel_effort["provider"] == "approximate_haversine_v2"


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
    result = _top_configuration(response.json())
    assert "planning_summary" in result
    assert "planning_provenance" in result
    assert "planning_evidence_count" in result
    assert result["planning_provenance"]["source_type"] == "estimated"
    assert result["planning_provenance"]["evidence_profile"] in {
        "archive_backed",
        "fallback_heavy",
    }


def test_search_includes_planning_weather_metrics_when_archive_rows_exist() -> None:
    _seed_france_archive_weather()

    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "travel_month": 3,
        },
    )

    assert response.status_code == 200
    result = _top_configuration(response.json())
    assert result["planning_weather_metrics"]["average_snow_depth_cm"] == 130.0
    assert result["planning_weather_metrics"]["average_daily_snowfall_cm"] == 8.0
    assert result["planning_weather_metrics"]["evidence_years"] == 2
    assert result["planning_weather_metrics"]["elevation_band"] == "mid"
    assert result["planning_weather_metrics"]["elevation_m"] == 2500


def test_search_exact_dates_include_planning_weather_metrics_when_available() -> None:
    _seed_france_archive_weather()

    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "trip_start_date": "2026-03-04",
            "trip_end_date": "2026-03-09",
        },
    )

    assert response.status_code == 200
    result = _top_configuration(response.json())
    assert result["planning_weather_metrics"]["average_snow_depth_cm"] == 130.0
    assert result["planning_weather_metrics"]["latest_observed_on"] == "2025-03-08"
    assert result["planning_weather_metrics"]["elevation_band"] == "mid"


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
    result = _top_configuration(response.json())
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
        _top_configuration(date_range_response.json())["planning_summary"]
        == _top_configuration(conflicting_response.json())["planning_summary"]
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


def test_parse_query_returns_trip_context_and_clarifications() -> None:
    app.dependency_overrides[get_query_parser] = lambda: HeuristicQueryParser(
        reference_date=date(2026, 1, 1)
    )
    try:
        response = client.post(
            "/api/parse-query",
            json={"query": "France ski trip total budget EUR 1500 for two people"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["trip_context"]["budget_mode"] == "total_trip"
    assert payload["trip_context"]["party_size"] == 2
    assert "clarifications" in payload
    assert "assumptions" in payload


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
    result = _top_configuration(response.json())
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
    assert result["budget_penalty"] >= 0
    assert result["evidence_quality"]["basis_summary"]
    assert result["selected_pass"]["accessible_ski_area_ids"]
    assert result["resilience"]["ranking_component"] == 0


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


def test_month_aware_search_and_booking_redirect_work_together(monkeypatch) -> None:
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v1")
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
            json=_tignes_trip_payload(),
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
        json=_tignes_trip_payload(
            trip_start_date="2026-03-08",
            trip_end_date="2026-03-12",
        ),
        headers=headers,
    )

    assert save_response.status_code == 200
    payload = save_response.json()
    assert payload["ski_region_id"] == "tignes-val-disere"
    assert payload["stay_destination_id"] == "tignes"
    assert payload["stay_base_id"] == "tignes-le-lac"
    assert payload["focus_ski_area_id"] == "tignes-ski-area"
    assert payload["lift_pass_product_id"] == "tignes-val-disere-ski-pass"
    assert payload["travel_month"] == 3
    assert payload["trip_start_date"] == "2026-03-08"
    assert payload["trip_end_date"] == "2026-03-12"
    assert payload["booking_status"] == "booked_elsewhere"

    get_saved = client.get("/api/current-trip", headers=headers)
    assert get_saved.status_code == 200
    assert get_saved.json()["trip"]["stay_destination_id"] == "tignes"

    delete_response = client.delete("/api/current-trip", headers=headers)
    assert delete_response.status_code == 204

    get_cleared = client.get("/api/current-trip", headers=headers)
    assert get_cleared.status_code == 200
    assert get_cleared.json() == {"trip": None}

    assert (
        CurrentTripRepository().get_current_trip(user_id=session["user"]["user_id"])
        is None
    )


def test_current_trip_rejects_base_owned_by_another_destination(monkeypatch) -> None:
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
        json=_tignes_trip_payload(
            stay_base_id="val-disere-le-fornet",
            stay_base_name="Le Fornet",
        ),
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid trip configuration"


@pytest.mark.parametrize(
    ("updates", "expected_detail"),
    [
        (
            {
                "ski_region_id": "cervinia",
                "ski_region_name": "Cervinia",
            },
            "Invalid trip configuration",
        ),
        (
            {
                "focus_ski_area_id": "val-disere-ski-area",
                "focus_ski_area_name": "Val d'Isere",
            },
            "Invalid trip configuration",
        ),
        (
            {
                "lift_pass_product_id": "cervinia-valtournenche-skipass",
                "lift_pass_product_name": "Breuil-Cervinia Valtournenche Ski Pass",
            },
            "Invalid trip configuration",
        ),
        (
            {"stay_base_name": "Not Le Lac"},
            "Trip display names do not match",
        ),
    ],
)
def test_current_trip_rejects_inconsistent_configuration(
    monkeypatch,
    updates: dict[str, str],
    expected_detail: str,
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
    headers, _ = _sign_in(identity_token="google-token")

    response = client.put(
        "/api/current-trip",
        json=_tignes_trip_payload(**updates),
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail


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
        json=_tignes_trip_payload(trip_start_date="2026-03-08"),
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
        json=_tignes_trip_payload(
            trip_start_date="2026-03-12",
            trip_end_date="2026-03-08",
        ),
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
    trip_repository = CurrentTripRepository()
    trip_repository.upsert_current_trip(
        user_id=user_id,
        trip=CurrentTrip(
            ski_region_id="tignes-val-disere",
            ski_region_name="Tignes - Val d'Isere",
            stay_destination_id="tignes",
            stay_destination_name="Tignes",
            stay_base_id="tignes-le-lac",
            stay_base_name="Le Lac",
            focus_ski_area_id="tignes-ski-area",
            focus_ski_area_name="Tignes",
            lift_pass_product_id="tignes-val-disere-ski-pass",
            lift_pass_product_name="Tignes - Val d'Isere ski pass",
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
        resort_name="Tignes",
        snow_confidence_score=current_score,
        snow_confidence_label=snow_confidence_label_for_score(current_score),
        availability_status=current_status,
        weather_summary=current_summary,
        conditions_score=current_score,
        updated_at=current_updated_at.isoformat(),
        source="open-meteo",
    )
    ResortConditionsRepository().upsert_conditions(
        entity_id="tignes-ski-area",
        entity_name="Tignes",
        conditions=current_conditions,
    )

    if prior_snapshot_at is not None:
        prior_snapshot = ResortConditionSnapshot(
            ski_area_id="tignes-ski-area",
            resort_name="Tignes",
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
        json=_tignes_trip_payload(),
        headers=headers_a,
    )
    save_b = client.put(
        "/api/current-trip",
        json=_cervinia_trip_payload(),
        headers=headers_b,
    )

    assert save_a.status_code == 200
    assert save_b.status_code == 200
    assert (
        client.get("/api/current-trip", headers=headers_a).json()["trip"][
            "stay_destination_id"
        ]
        == "tignes"
    )
    assert (
        client.get("/api/current-trip", headers=headers_b).json()["trip"][
            "stay_destination_id"
        ]
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
    assert payload["trip"]["focus_ski_area_id"] == "tignes-ski-area"
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
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v1")

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
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v1")

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


def test_search_debug_includes_search_model_metadata(monkeypatch) -> None:
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v1")
    monkeypatch.setenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", "true")

    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "debug": "true",
            "search_model": "search_v2",
        },
    )

    assert response.status_code == 200
    debug = response.json()["debug"]
    assert debug["configured_search_model"] == "search_v1"
    assert debug["requested_search_model"] == "search_v2"
    assert debug["effective_search_model"] == "search_v2"
    assert debug["search_model_override_applied"] is True


def test_search_v3_debug_keeps_group_contract_and_model_metadata(monkeypatch) -> None:
    monkeypatch.delenv("SNOWCAST_SEARCH_MODEL", raising=False)
    monkeypatch.delenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", raising=False)

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
    assert payload["debug"]["effective_search_model"] == "search_v3"
    assert payload["debug"]["narrative_source"] == "none"
    assert payload["results"][0]["top_configuration"]


def test_search_model_override_requires_debug(monkeypatch) -> None:
    monkeypatch.setenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", "true")

    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "search_model": "search_v2",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "search_model override requires debug=true"


def test_search_model_override_requires_enablement(monkeypatch) -> None:
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v1")
    monkeypatch.delenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", raising=False)

    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "debug": "true",
            "search_model": "search_v2",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "search_model override is disabled"


def test_healthz_returns_ok() -> None:
    response = client.get("/api/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_ok() -> None:
    response = client.get("/api/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_readiness_checks_search_dependencies() -> None:
    response = client.get("/api/search-readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["catalog"] == "ok"
    assert payload["checks"]["resort_count"] > 0
    assert payload["checks"]["ski_area_count"] > 0
    assert "conditions_count" in payload["checks"]


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
