from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.ai.parser import HeuristicQueryParser, get_query_parser
from app.auth.google import (
    GoogleAuthConfigurationError,
    GoogleIdentity,
    GoogleIdentityTokenError,
)
from app.data.catalog_loader import load_catalog
from app.data.catalog_repository import CatalogRepository
from app.data.catalog_sync import sync_catalog_snapshot
from app.data.repositories import (
    CurrentTripRepository,
    OutboundBookingClickRepository,
    RawWeatherHistoryRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
)
from app.domain.models import (
    CurrentTrip,
    RawWeatherObservation,
    ResortConditions,
    ResortConditionSnapshot,
    snow_confidence_label_for_score,
)
from app.domain.search_intent_policy import SearchIntentPolicyError
from app.domain.search_v4_models import GroupPriorityPatch, SearchIntent
from app.domain.search_v4_service import (
    SearchV4AccessSummary,
    SearchV4Configuration,
    SearchV4PassSummary,
    SearchV4RecommendationGroup,
    SearchV4RefinementOption,
    SearchV4RefinementPreview,
    SearchV4RefinementProposal,
    SearchV4RefinementRankChange,
    SearchV4RefinementResponse,
    SearchV4Response,
    UnknownSearchWeatherAreaError,
)
from app.domain.search_weather_evidence import (
    ForecastWeatherEvidence,
    ForecastWeatherSource,
    HistoricalWeatherEvidence,
    HistoricalWeatherSource,
    SearchWeatherEvidence,
    SearchWeatherEvidenceAvailableResponse,
    SearchWeatherEvidenceUnavailableResponse,
    WeatherEvidencePoint,
)
from app.main import app, create_app
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def sync_normalized_catalog_for_search_tests(
    request: pytest.FixtureRequest,
    reset_postgres_database: None,
) -> None:
    needs_normalized_catalog = (
        request.node.name.startswith("test_search")
        or request.node.name.startswith("test_month_aware_search")
        or request.node.name.startswith("test_current_trip")
        or request.node.name.startswith("test_mark_checked")
        or request.node.name.startswith("test_outbound")
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


def test_search_refinements_serializes_previews_and_preserves_patch_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refinement = SearchV4RefinementProposal(
        topic_id="accessible_terrain_scale",
        target_factor_id="accessible_terrain_scale",
        question_id="terrain-vs-access",
        question="Which tradeoff should lead the ranking?",
        reason="The leading regions trade terrain scale against base access.",
        options=(
            SearchV4RefinementOption(
                label="Terrain",
                description="Prioritize ski-area scale.",
                intent_changed=True,
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="ski_experience",
                        importance="very_high",
                    ),
                ),
                preview=SearchV4RefinementPreview(
                    top_rank_changes=(
                        SearchV4RefinementRankChange(
                            ski_region_id="region-c",
                            previous_rank=3,
                            preview_rank=2,
                        ),
                    ),
                    eligible_candidate_count_delta=-1,
                ),
            ),
            SearchV4RefinementOption(
                label="Access",
                description="Prioritize stay-base access.",
                intent_changed=True,
                group_priority_patches=(
                    GroupPriorityPatch(
                        group_id="stay_practicality",
                        importance="very_high",
                    ),
                ),
                preview=None,
            ),
        ),
    )
    monkeypatch.setattr(
        "app.api.routes.get_search_refinements",
        lambda **_kwargs: SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version=("search-refinement-presentation-1"),
            refinement_status="questions_available",
            refinements=(refinement,),
        ),
    )

    response = client.post(
        "/api/search/refinements",
        json={
            "intent": {},
            "baseline_fingerprint": "a" * 64,
        },
    )

    assert response.status_code == 200
    options = response.json()["refinements"][0]["options"]
    assert options[0]["preview"] == {
        "top_rank_changes": [
            {
                "ski_region_id": "region-c",
                "previous_rank": 3,
                "preview_rank": 2,
            }
        ],
        "eligible_candidate_count_delta": -1,
    }
    assert options[1]["preview"] is None
    assert options[0]["intent_changed"] is True
    assert options[1]["intent_changed"] is True
    assert options[0]["group_priority_patches"] == [
        {"group_id": "ski_experience", "importance": "very_high"}
    ]


def _weather_api_configuration(
    *,
    candidate_id: str,
) -> SearchV4Configuration:
    return SearchV4Configuration(
        candidate_id=candidate_id,
        ski_region_id="region",
        ski_region_name="Region",
        stay_destination_id="destination",
        stay_destination_name="Destination",
        stay_base_id="base",
        stay_base_name="Base",
        ski_area_id="area",
        ski_area_name="Area",
        evidence_profile="archive_backed",
        access=SearchV4AccessSummary(
            ski_area_access_id="access",
            access_mode="walk",
            lift_distance="nearby",
            nearest_lift_name="Main lift",
            distance_m=250,
            duration_minutes=4,
            is_direct=True,
            relationship_trust_status="verified",
            access_mode_distance_trust_status="verified",
        ),
        selected_pass=SearchV4PassSummary(
            lift_pass_product_id="pass",
            name="Ski pass",
            validity_scope="ski_area",
            covered_ski_area_ids=("area",),
            accessible_piste_km=180,
            accessible_piste_km_evidence={
                "trust_status": "verified",
                "scope": "pass",
                "source_entity_id": "pass",
                "field_group": "pass_accessible_terrain",
            },
            price=None,
        ),
        lodging_estimate=None,
        ranking_status="ranked",
        fit_score=88,
    )


def test_search_weather_evidence_endpoint_serializes_typed_available_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical_point = WeatherEvidencePoint(
        date_or_month_day="01-10",
        snow_depth_cm_p50=80,
        snowfall_cm=4,
        temperature_max_c=-1,
        rain_risk=0.1,
        thaw_risk=0.2,
        wind_gust_kmh=30,
    )
    forecast_point = WeatherEvidencePoint(
        date_or_month_day="2027-01-10",
        snow_depth_cm=60,
        snowfall_cm=10,
        temperature_min_c=-6,
        temperature_max_c=1,
        rain_risk=0.25,
        thaw_risk=0.1,
        wind_gust_kmh=50,
    )
    weather = SearchWeatherEvidence(
        mode="forecast_assisted",
        window_label="2027-01-10 to 2027-01-12",
        elevation_m=2000,
        elevation_status="exact",
        interpretation=(
            "Fresh forecast data adds to historical weather patterns for "
            "3 of 3 requested days."
        ),
        historical=HistoricalWeatherEvidence(
            source_label="30-year snow climatology",
            source_model="snowcast_empirical_v1",
            computed_at="2026-07-01T00:00:00+00:00",
            baseline_start_year=1991,
            baseline_end_year=2020,
            evidence_seasons=25,
            latest_archive_year=2025,
            provenance_status="homogeneous",
            sources=(
                HistoricalWeatherSource(
                    source_model="snowcast_empirical_v1",
                    computed_at="2026-07-01T00:00:00+00:00",
                    baseline_period="normal_30y",
                    baseline_start_year=1991,
                    baseline_end_year=2020,
                    evidence_seasons=25,
                    latest_archive_year=2025,
                    elevation_m=2000,
                    row_count=1,
                    profile_dates=("01-10",),
                ),
            ),
            snow_depth_cm_p25=60,
            snow_depth_cm_p50=80,
            snow_depth_cm_p75=100,
            probability_snow_depth_ge_30cm=0.8,
            average_daily_snowfall_cm=4,
            average_max_temperature_c=-1,
            daily_profile=(historical_point,),
        ),
        forecast=ForecastWeatherEvidence(
            source_label="ecmwf",
            source_model="ifs025",
            issued_at="2027-01-09T00:00:00+00:00",
            provenance_status="homogeneous",
            sources=(
                ForecastWeatherSource(
                    forecast_run_id="run-ecmwf",
                    forecast_source_key="ecmwf_ifs025_ensemble_mean",
                    source_label="ecmwf",
                    source_model="ifs025",
                    issued_at="2027-01-09T00:00:00+00:00",
                    elevation_m=2000,
                    row_count=3,
                    profile_dates=("2027-01-10",),
                ),
            ),
            coverage_status="complete",
            usable_date_count=3,
            requested_date_count=3,
            average_forecast_share=0.8,
            daily_profile=(forecast_point,),
        ),
    )
    monkeypatch.setattr(
        "app.api.routes.get_search_weather_evidence",
        lambda **_kwargs: SearchWeatherEvidenceAvailableResponse(
            weather_evidence_version="search-weather-evidence-v1",
            ski_area_id="area",
            evaluated_at="2027-01-09T12:00:00+00:00",
            cache_valid_until="2027-01-09T22:10:00+00:00",
            evidence=weather,
        ),
    )

    response = client.post(
        "/api/search/weather-evidence",
        json={
            "ski_area_id": "area",
            "intent": {
                "constraints": {
                    "travel_window": {
                        "start_date": "2027-01-10",
                        "end_date": "2027-01-12",
                    }
                }
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["evidence"]
    assert payload["mode"] == "forecast_assisted"
    assert payload["historical"]["daily_profile"][0]["snow_depth_cm_p50"] == 80
    assert payload["historical"]["provenance_status"] == "homogeneous"
    assert payload["historical"]["sources"][0]["baseline_period"] == "normal_30y"
    assert payload["forecast"]["usable_date_count"] == 3
    assert payload["forecast"]["sources"][0]["forecast_run_id"] == "run-ecmwf"
    assert response.json()["status"] == "available"


def test_search_weather_evidence_endpoint_serializes_typed_unavailable_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.get_search_weather_evidence",
        lambda **_kwargs: SearchWeatherEvidenceUnavailableResponse(
            weather_evidence_version="search-weather-evidence-v1",
            ski_area_id="area",
            evaluated_at="2027-01-09T12:00:00+00:00",
            cache_valid_until="2027-01-09T12:05:00+00:00",
            unavailable_reason="travel_window_missing",
            limitations=("A travel month or exact travel dates are required.",),
        ),
    )

    response = client.post(
        "/api/search/weather-evidence",
        json={"ski_area_id": "area", "intent": {}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["unavailable_reason"] == "travel_window_missing"


def test_search_grouped_response_omits_weather_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    top = _weather_api_configuration(candidate_id="candidate")
    monkeypatch.setattr(
        "app.api.routes.search_trip_configurations",
        lambda **_kwargs: SearchV4Response(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            ranking_status="ranked",
            applied_intent=SearchIntent(),
            eligible_candidate_count=1,
            excluded_candidate_count=0,
            results=(
                SearchV4RecommendationGroup(
                    ski_region_id="region",
                    ski_region_name="Region",
                    rank=1,
                    fit_score=88,
                    top_configuration=top,
                ),
            ),
        ),
    )

    response = client.post(
        "/api/search",
        json={"intent": {}},
    )

    assert response.status_code == 200
    assert "weather_evidence" not in _top_configuration(response.json())


def test_search_weather_evidence_endpoint_rejects_bounded_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unknown_area(**_kwargs):
        raise UnknownSearchWeatherAreaError("unknown-area")

    monkeypatch.setattr("app.api.routes.get_search_weather_evidence", unknown_area)
    unknown_response = client.post(
        "/api/search/weather-evidence",
        json={"ski_area_id": "unknown-area", "intent": {}},
    )

    assert unknown_response.status_code == 422
    assert unknown_response.json() == {"error": {"code": "weather_area_not_found"}}

    def invalid_intent(**_kwargs):
        raise SearchIntentPolicyError("unknown factor ID: invalid")

    monkeypatch.setattr("app.api.routes.get_search_weather_evidence", invalid_intent)
    invalid_response = client.post(
        "/api/search/weather-evidence",
        json={"ski_area_id": "area", "intent": {}},
    )

    assert invalid_response.status_code == 422
    assert invalid_response.json() == {"error": {"code": "search_request_invalid"}}


def test_search_weather_evidence_endpoint_records_bounded_http_route_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    monkeypatch.setattr(
        "app.api.routes.get_search_weather_evidence",
        lambda **_kwargs: SearchWeatherEvidenceUnavailableResponse(
            weather_evidence_version="search-weather-evidence-v1",
            ski_area_id="area",
            evaluated_at="2027-01-09T12:00:00+00:00",
            cache_valid_until="2027-01-09T12:05:00+00:00",
            unavailable_reason="travel_window_missing",
            limitations=("A travel month or exact travel dates are required.",),
        ),
    )
    try:
        response = client.post(
            "/api/search/weather-evidence",
            json={"ski_area_id": "area", "intent": {}},
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert response.status_code == 200
    assert any(
        name == "snowcast_http_request_duration_seconds"
        and labels
        == {
            "route": "/api/search/weather-evidence",
            "method": "POST",
            "status_class": "2xx",
        }
        for name, labels, _value in recorder.histograms
    )


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
    snapshot = CatalogRepository().get_snapshot()
    french_destination_ids = {
        destination.stay_destination_id
        for destination in snapshot.stay_destinations
        if destination.country == "France"
    }
    french_base_ids = {
        base.stay_base_id
        for base in snapshot.stay_bases
        if base.stay_destination_id in french_destination_ids
    }
    french_area_ids = {
        access.ski_area_id
        for access in snapshot.ski_area_access
        if access.stay_base_id in french_base_ids
    }
    for ski_area in snapshot.ski_areas:
        if ski_area.ski_area_id not in french_area_ids:
            continue
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


def test_outbound_accommodation_redirect_records_click() -> None:
    response = client.get(
        "/api/outbound/accommodation/tignes",
        params={
            "stay_base_id": "tignes-le-lac",
            "focus_ski_area_id": "tignes-ski-area",
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
    assert clicks[0]["stay_destination_id"] == "tignes"
    assert clicks[0]["stay_base_id"] == "tignes-le-lac"
    assert clicks[0]["focus_ski_area_id"] == "tignes-ski-area"
    assert (
        clicks[0]["target_url"]
        == "https://www.booking.com/searchresults.html?ss=Tignes%2C+France&group_adults=2&no_rooms=1&group_children=0"
    )
    assert clicks[0]["source_surface"] == "selected_result_details"
    assert clicks[0]["request_id"] == "req-123"
    assert clicks[0]["user_agent"] == "pytest-agent"


def test_outbound_accommodation_redirect_rejects_unknown_destination_id() -> None:
    response = client.get(
        "/api/outbound/accommodation/unknown-resort",
        params={
            "stay_base_id": "tignes-le-lac",
            "focus_ski_area_id": "tignes-ski-area",
            "source_surface": "selected_result_details",
        },
        headers={
            "referer": (
                "http://testserver/recommendations/tignes-val-disere"
                "?candidate=tignes-access--local-pass"
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "<title>Trip option unavailable | Snowcast</title>" in response.text
    assert "<main" in response.text
    assert "<h1>This trip option is no longer available</h1>" in response.text
    assert "Return to trip details" in response.text
    assert (
        'href="/recommendations/tignes-val-disere'
        '?candidate=tignes-access--local-pass"' in response.text
    )
    assert "Unknown trip configuration" not in response.text


def test_outbound_accommodation_redirect_rejects_invalid_access_pair() -> None:
    response = client.get(
        "/api/outbound/accommodation/tignes",
        params={
            "stay_base_id": "val-disere-le-fornet",
            "focus_ski_area_id": "val-disere-ski-area",
            "source_surface": "selected_result_details",
        },
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "Return to Snowcast" in response.text


@pytest.mark.parametrize(
    ("referer", "expected_label", "expected_href"),
    [
        (
            "https://attacker.example/recommendations/tignes",
            "Return to Snowcast",
            'href="/"',
        ),
        (
            "http://testserver/recommendations/tignes?candidate=%22%3E%3Cscript%3E",
            "Return to trip details",
            'href="/recommendations/tignes?candidate=%22%3E%3Cscript%3E"',
        ),
    ],
)
def test_outbound_accommodation_recovery_keeps_return_links_safe(
    referer: str,
    expected_label: str,
    expected_href: str,
) -> None:
    response = client.get(
        "/api/outbound/accommodation/unknown-resort",
        params={
            "stay_base_id": "tignes-le-lac",
            "focus_ski_area_id": "tignes-ski-area",
            "source_surface": "selected_result_details",
        },
        headers={"referer": referer},
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert expected_label in response.text
    assert expected_href in response.text
    assert "attacker.example" not in response.text
    assert "<script>" not in response.text


@pytest.mark.parametrize("frontend_built", [False, True])
@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize(
    "path",
    [
        "/api/outbound/accommodation",
        "/api/outbound/accommodation/tignes/extra",
    ],
)
def test_outbound_accommodation_routing_failures_return_branded_html(
    path: str,
    method: str,
    frontend_built: bool,
    tmp_path,
) -> None:
    dist_dir = tmp_path / "dist"
    if frontend_built:
        dist_dir.mkdir()
        (dist_dir / "index.html").write_text("<html>frontend</html>", encoding="utf-8")
    test_app = create_app(frontend_dist_dir=dist_dir)

    with TestClient(test_app) as test_client:
        response = test_client.request(method, path, follow_redirects=False)

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "<title>Trip option unavailable | Snowcast</title>" in response.text
    assert "<main" in response.text
    assert "Return to Snowcast" in response.text
    assert '"detail"' not in response.text


def test_outbound_accommodation_wrong_method_preserves_html_status_and_headers() -> (
    None
):
    response = client.post(
        "/api/outbound/accommodation/tignes",
        params={
            "stay_base_id": "tignes-le-lac",
            "focus_ski_area_id": "tignes-ski-area",
            "source_surface": "selected_result_details",
        },
        follow_redirects=False,
    )

    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"
    assert "text/html" in response.headers["content-type"]
    assert "<title>Trip option unavailable | Snowcast</title>" in response.text
    assert '"detail"' not in response.text


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
    assert response.json() == {"error": {"code": "sign_in_failed"}}


def test_google_sign_in_reports_provider_configuration_failure(monkeypatch) -> None:
    def _fail_verification(_identity_token: str) -> None:
        raise GoogleAuthConfigurationError("GOOGLE_OAUTH_CLIENT_IDS missing")

    monkeypatch.setattr(
        "app.api.routes.verify_google_identity_token",
        _fail_verification,
    )

    response = client.post(
        "/api/auth/google/sign-in",
        json={"identity_token": "google-token"},
    )

    assert response.status_code == 503
    assert response.json() == {"error": {"code": "sign_in_unavailable"}}


def test_current_trip_endpoints_require_authentication() -> None:
    responses = (
        client.get("/api/current-trip"),
        client.put(
            "/api/current-trip",
            json=_tignes_trip_payload(),
        ),
        client.get("/api/current-trip/summary"),
        client.post("/api/current-trip/mark-checked"),
        client.delete("/api/current-trip"),
    )

    for response in responses:
        assert response.status_code == 401
        assert response.json() == {"error": {"code": "authentication_required"}}


def test_current_trip_rejects_expired_session() -> None:
    response = client.get(
        "/api/current-trip",
        headers={"Authorization": "Bearer expired-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "session_expired"}}


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
    assert response.json() == {"error": {"code": "trip_option_invalid"}}


@pytest.mark.parametrize(
    "updates",
    [
        {
            "ski_region_id": "cervinia",
            "ski_region_name": "Cervinia",
        },
        {
            "focus_ski_area_id": "val-disere-ski-area",
            "focus_ski_area_name": "Val d'Isere",
        },
        {
            "lift_pass_product_id": "cervinia-valtournenche-skipass",
            "lift_pass_product_name": "Breuil-Cervinia Valtournenche Ski Pass",
        },
        {"stay_base_name": "Not Le Lac"},
    ],
)
def test_current_trip_rejects_inconsistent_configuration(
    monkeypatch,
    updates: dict[str, str],
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
    assert response.json() == {"error": {"code": "trip_option_invalid"}}


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
    assert response.json() == {"error": {"code": "current_trip_not_found"}}


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
    monkeypatch.setattr(
        "app.domain.trip_companion.is_condition_fresh",
        lambda _conditions: False,
    )

    response = client.get("/api/current-trip/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["trip"]["focus_ski_area_id"] == "tignes-ski-area"
    assert payload["comparison_basis"]["kind"] == "since_trip_saved"
    assert payload["current_conditions_provenance"]["source_type"] == "forecast"
    assert payload["delta"]["status"] == "changed"
    assert payload["delta"]["summary"] == (
        "Conditions have changed since you saved this trip."
    )
    assert payload["companion_status"]["trip_window_status"] == "unscheduled"
    assert payload["companion_status"]["notification_eligible"] is False
    assert payload["companion_status"]["eligibility_reason"] == (
        "Exact trip dates are not available."
    )
    assert payload["delta"]["changes"] == [
        "Snow outlook improved from fair to good.",
        "Weather disruption risk changed from some to low.",
        "The weather summary changed since you saved this trip.",
        "The latest forecast is out of date.",
    ]


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
    assert payload["delta"]["summary"] == (
        "Conditions have changed since your last check."
    )


@pytest.mark.parametrize(
    ("checked_at_offset", "comparison_kind", "expected_summary"),
    [
        (
            None,
            "since_trip_saved",
            "Conditions have not changed since you saved this trip.",
        ),
        (
            timedelta(days=1),
            "since_last_check",
            "Conditions have not changed since your last check.",
        ),
    ],
)
def test_current_trip_summary_uses_basis_aware_unchanged_copy(
    monkeypatch,
    checked_at_offset: timedelta | None,
    comparison_kind: str,
    expected_summary: str,
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
    trip_created_at = datetime(2026, 4, 10, 10, tzinfo=UTC)
    _seed_trip_conditions_state(
        user_id=session["user"]["user_id"],
        trip_created_at=trip_created_at,
        current_updated_at=trip_created_at,
        prior_snapshot_at=None,
    )
    if checked_at_offset is not None:
        CurrentTripRepository().mark_checked(
            user_id=session["user"]["user_id"],
            checked_at=(trip_created_at + checked_at_offset).isoformat(),
        )

    response = client.get("/api/current-trip/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparison_basis"]["kind"] == comparison_kind
    assert payload["delta"] == {
        "status": "unchanged",
        "summary": expected_summary,
        "changes": [],
    }


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
    assert payload["delta"]["summary"] == (
        "Conditions are newer since you saved this trip, but there is not enough "
        "earlier history to compare."
    )


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
    assert payload["companion_status"]["eligibility_reason"] == (
        "Trip dates are in the future."
    )


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
    assert payload["companion_status"]["eligibility_reason"] == "Trip dates have ended."


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
    assert payload["checks"]["search_model"] == "search-v4"
    assert payload["checks"]["ranking_policy"]
    assert payload["checks"]["factor_count"] > 0
    assert payload["checks"]["factor_registry"] == "ok"
    assert payload["checks"]["refinement_presentation_policy"] == (
        "search-refinement-presentation-2"
    )
    assert "Traditional mountain village" not in response.text
    assert payload["checks"]["expected_forecast_head_count"] > 0
    assert "forecast_head_count" in payload["checks"]
    assert "fresh_forecast_head_count" in payload["checks"]
    assert "missing_forecast_head_count" in payload["checks"]
    assert "stale_forecast_head_count" in payload["checks"]


def test_search_readiness_keeps_operational_diagnostics(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.CatalogRepository.get_snapshot",
        lambda _self: (_ for _ in ()).throw(RuntimeError("catalog unavailable")),
    )

    response = client.get("/api/search-readiness")

    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "ok"
    assert response.json()["detail"]["error"] == "RuntimeError"


def test_operational_wrong_method_keeps_framework_diagnostics() -> None:
    response = client.post("/api/healthz")

    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"
    assert response.json() == {"detail": "Method Not Allowed"}


@pytest.mark.parametrize("frontend_built", [False, True])
@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize("path", ["/api", "/api/not-a-snowcast-route"])
def test_unknown_customer_api_route_uses_bounded_public_error(
    tmp_path,
    frontend_built: bool,
    method: str,
    path: str,
) -> None:
    dist_dir = tmp_path / "dist"
    if frontend_built:
        dist_dir.mkdir()
        (dist_dir / "index.html").write_text("<html>frontend</html>", encoding="utf-8")
    test_app = create_app(frontend_dist_dir=dist_dir)

    with TestClient(test_app) as test_client:
        response = test_client.request(method, path)

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found"}}


@pytest.mark.parametrize("frontend_built", [False, True])
@pytest.mark.parametrize("method", ["get", "post"])
def test_customer_api_trailing_slash_redirect_is_deployment_independent(
    tmp_path,
    frontend_built: bool,
    method: str,
) -> None:
    dist_dir = tmp_path / "dist"
    if frontend_built:
        dist_dir.mkdir()
        (dist_dir / "index.html").write_text("<html>frontend</html>", encoding="utf-8")
    test_app = create_app(frontend_dist_dir=dist_dir)

    with TestClient(test_app) as test_client:
        response = test_client.request(
            method,
            "/api/search//",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert response.headers["location"] == "http://testserver/api/search"


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
