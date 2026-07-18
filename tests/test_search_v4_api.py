from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from app.api.refinement_admission import RefinementAdmissionGuard
from app.api.refinement_workers import RefinementWorkerUnavailableError
from app.data.catalog_loader import CATALOG_PATH, load_catalog_from_path
from app.domain import search_v4_service
from app.domain.search_intent_policy import SearchIntentPolicyError
from app.domain.search_policy import load_search_policy
from app.domain.search_refinement_snapshot import (
    RefinementBaselineSnapshot,
    SearchRefinementSnapshotStore,
    canonical_search_intent_digest,
)
from app.domain.search_v4_models import SearchIntent
from app.domain.search_v4_service import (
    SearchV4RefinementResponse,
    SearchV4Response,
)
from app.main import app
from app.observability.context import current_request_id

pytestmark = pytest.mark.db_free


@pytest.fixture(autouse=True)
def reset_refinement_admission_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.refinement_admission_guard",
        RefinementAdmissionGuard(),
    )


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
        "baseline_fingerprint": "a" * 64,
    }


def _ranking_request_payload() -> dict[str, object]:
    return {"intent": _request_payload()["intent"]}


def test_refinement_openapi_documents_admission_rejection() -> None:
    app.openapi_schema = None

    response = app.openapi()["paths"]["/api/search/refinements"]["post"]["responses"][
        "429"
    ]

    assert response["description"] == "Refinement admission limit reached"
    assert response["headers"]["Retry-After"]["schema"] == {
        "type": "integer",
        "minimum": 1,
    }
    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ApiErrorResponse"
    }


def test_post_search_is_ranking_only_and_never_constructs_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setattr(
        "app.api.routes.GeminiClient",
        lambda **_kwargs: pytest.fail("ranking endpoint must not construct Gemini"),
    )
    payload = _ranking_request_payload()
    intent_payload = payload["intent"]
    assert isinstance(intent_payload, dict)
    constraints = intent_payload["constraints"]
    assert isinstance(constraints, dict)
    constraints["lodging_budget"] = {
        "mode": "lodging_nightly",
        "maximum": 320,
        "currency": "EUR",
        "budget_flex": 0,
    }

    response = TestClient(app).post("/api/search", json=payload)

    assert response.status_code == 200
    assert response.json()["search_model_version"] == "search-v4"
    assert captured == {"intent": captured["intent"]}
    assert response.json()["refinements"] == []
    assert response.json()["baseline_fingerprint"] == "0" * 64
    applied_constraints = response.json()["applied_intent"]["constraints"]
    assert applied_constraints["travel_window"] == {
        "month": None,
        "start_date": "2027-01-16",
        "end_date": "2027-01-20",
    }
    assert applied_constraints["lodging_budget"] == {
        "mode": "lodging_nightly",
        "maximum": 320.0,
        "currency": "EUR",
        "budget_flex": 0.0,
    }


def test_search_openapi_matches_request_shaped_applied_intent() -> None:
    schemas = app.openapi()["components"]["schemas"]

    travel_window = schemas["TravelWindow"]
    lodging_budget = schemas["LodgingBudgetConstraint"]

    assert "mode" not in travel_window["properties"]
    assert "ski_day_count" not in travel_window["properties"]
    assert "effective_flex" not in lodging_budget["properties"]
    assert "effective_maximum" not in lodging_budget["properties"]


def test_post_search_accepts_legacy_refinement_fields_but_returns_empty_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.search_trip_configurations",
        lambda **kwargs: SearchV4Response(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            ranking_status="ranked",
            applied_intent=kwargs["intent"],
            eligible_candidate_count=0,
            excluded_candidate_count=0,
            results=(),
        ),
    )
    monkeypatch.setattr(
        "app.api.routes.GeminiClient",
        lambda **_kwargs: pytest.fail("legacy fields must not construct Gemini"),
    )

    response = TestClient(app).post(
        "/api/search",
        json={
            "intent": _request_payload()["intent"],
            "brief": "legacy mobile request",
            "generate_refinements": True,
            "already_answered_question_ids": ["previous-question"],
        },
    )

    assert response.status_code == 200
    assert response.json()["refinements"] == []


def test_post_search_refinements_uses_separate_typed_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_refinements(**kwargs: object) -> SearchV4RefinementResponse:
        captured.update(kwargs)
        return SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version="search-refinement-presentation-1",
            refinement_status="not_needed",
        )

    monkeypatch.setattr("app.api.routes.get_search_refinements", fake_refinements)
    payload = _request_payload()
    payload["already_answered_question_ids"] = ["fallback-group-ski_experience"]

    response = TestClient(app).post("/api/search/refinements", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "search_model_version": "search-v4",
        "ranking_policy_version": "search-v4-policy-1",
        "refinement_presentation_policy_version": "search-refinement-presentation-1",
        "baseline_fingerprint": "0" * 64,
        "baseline_status": "current",
        "refinement_status": "not_needed",
        "fallback_used": False,
        "refinements": [],
    }
    assert captured["brief"] == "A good-value intermediate trip in France."
    assert captured["already_answered_question_ids"] == frozenset(
        {"fallback-group-ski_experience"}
    )


def test_post_search_refinements_propagates_request_context_to_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_request_ids: list[str | None] = []

    def fake_refinements(**_kwargs: object) -> SearchV4RefinementResponse:
        captured_request_ids.append(current_request_id())
        return SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version="search-refinement-presentation-1",
            refinement_status="not_needed",
        )

    monkeypatch.setattr("app.api.routes.get_search_refinements", fake_refinements)

    response = TestClient(app).post(
        "/api/search/refinements",
        json=_request_payload(),
        headers={"X-Request-ID": "req-refinement-context"},
    )

    assert response.status_code == 200
    assert captured_request_ids == ["req-refinement-context"]


def test_post_search_refinements_rejects_invalid_intent_with_safe_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_refinements(**_kwargs: object) -> SearchV4RefinementResponse:
        raise SearchIntentPolicyError("unknown factor ID: invented")

    monkeypatch.setattr("app.api.routes.get_search_refinements", reject_refinements)

    response = TestClient(app).post("/api/search/refinements", json=_request_payload())

    assert response.status_code == 422
    assert response.json()["detail"] == "unknown factor ID: invented"


def test_post_search_refinements_hides_provider_failure_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_refinements(**_kwargs: object) -> SearchV4RefinementResponse:
        raise RuntimeError("provider body prompt token traceback secret")

    monkeypatch.setattr("app.api.routes.get_search_refinements", fail_refinements)

    response = TestClient(app).post("/api/search/refinements", json=_request_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to load refinements."}


def test_post_search_refinements_fails_closed_when_snapshot_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        search_v4_service,
        "default_refinement_snapshot_store",
        SearchRefinementSnapshotStore(),
    )
    monkeypatch.setattr(
        "app.api.routes.GeminiClient",
        lambda **_kwargs: pytest.fail("snapshot miss must not construct Gemini"),
    )
    monkeypatch.setattr(
        search_v4_service,
        "_evaluate_search",
        lambda **_kwargs: pytest.fail("snapshot miss must not rerun search"),
    )

    response = TestClient(app).post("/api/search/refinements", json=_request_payload())

    assert response.status_code == 200
    assert response.json()["baseline_status"] == "unverified"
    assert response.json()["refinement_status"] == "temporarily_unavailable"
    assert response.json()["refinements"] == []


def test_post_search_snapshot_is_consumed_by_the_followup_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ClimatologyRepository:
        def list_daily_rows_for_ski_areas_window(
            self,
            ski_area_ids: tuple[str, ...],
            **_kwargs: object,
        ) -> dict[tuple[str, str, str], tuple[object, ...]]:
            return {
                (ski_area_id, "mid", baseline): ()
                for ski_area_id in ski_area_ids
                for baseline in ("normal_30y", "recent_15y")
            }

    class _ForecastRepository:
        def list_latest_daily_rows(self, **_kwargs: object) -> tuple[object, ...]:
            return ()

    snapshot_store = SearchRefinementSnapshotStore()
    monkeypatch.setattr(
        search_v4_service,
        "default_refinement_snapshot_store",
        snapshot_store,
    )
    monkeypatch.setattr(
        search_v4_service,
        "generate_refinement_proposals",
        lambda **_kwargs: search_v4_service.RefinementGenerationResult(
            outcome="no_proposals",
            proposals=(),
        ),
    )
    monkeypatch.setattr(
        search_v4_service.CatalogRepository,
        "get_snapshot",
        lambda _repository: load_catalog_from_path(CATALOG_PATH),
    )
    monkeypatch.setattr(
        search_v4_service,
        "get_snow_climatology_repository",
        _ClimatologyRepository,
    )
    monkeypatch.setattr(
        search_v4_service,
        "WeatherForecastRepository",
        _ForecastRepository,
    )
    monkeypatch.setattr("app.api.routes.GeminiClient", lambda **_kwargs: object())

    ranking = TestClient(app).post("/api/search", json=_ranking_request_payload())
    assert ranking.status_code == 200
    ranking_body = ranking.json()

    refinement = TestClient(app).post(
        "/api/search/refinements",
        json={
            "intent": ranking_body["applied_intent"],
            "brief": "A good-value intermediate trip in France.",
            "baseline_fingerprint": ranking_body["baseline_fingerprint"],
        },
    )

    assert refinement.status_code == 200
    assert refinement.json()["baseline_status"] == "current"
    assert refinement.json()["refinement_status"] in {
        "questions_available",
        "not_needed",
    }


def test_post_search_refinements_skips_gemini_when_questions_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _request_payload()
    intent = SearchIntent.model_validate(payload["intent"])
    base_policy = load_search_policy()
    policy = base_policy.model_copy(
        update={
            "refinement": base_policy.refinement.model_copy(update={"max_questions": 0})
        }
    )
    snapshot_store = SearchRefinementSnapshotStore()
    snapshot_store.put(
        RefinementBaselineSnapshot(
            fingerprint=payload["baseline_fingerprint"],
            intent_digest=canonical_search_intent_digest(intent),
            policy=policy,
            candidates=(),
        )
    )
    monkeypatch.setattr(
        search_v4_service,
        "default_refinement_snapshot_store",
        snapshot_store,
    )
    monkeypatch.setattr(
        "app.api.routes.GeminiClient",
        lambda **_kwargs: pytest.fail("disabled questions must not construct Gemini"),
    )
    monkeypatch.setattr(
        search_v4_service,
        "build_deterministic_refinement_fallback",
        lambda **_kwargs: pytest.fail("disabled questions must not build fallback"),
    )

    response = TestClient(app).post("/api/search/refinements", json=payload)

    assert response.status_code == 200
    assert response.json()["baseline_status"] == "current"
    assert response.json()["refinement_status"] == "not_needed"
    assert response.json()["refinements"] == []


def test_post_search_refinements_rejects_before_evaluation_when_admission_denies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_keys: list[str] = []

    class _DeniedAdmission:
        accepted = False
        retry_after_seconds = 7

        def release(self) -> None:
            pytest.fail("rejected admission must not be released")

    class _Guard:
        def acquire(self, client_key: str) -> _DeniedAdmission:
            captured_keys.append(client_key)
            return _DeniedAdmission()

    monkeypatch.setattr("app.api.routes.refinement_admission_guard", _Guard())
    monkeypatch.setattr(
        "app.api.routes.get_search_refinements",
        lambda **_kwargs: pytest.fail("admission rejection must skip evaluation"),
    )

    response = TestClient(app).post(
        "/api/search/refinements",
        json=_request_payload(),
        headers={"Fly-Client-IP": "203.0.113.7"},
    )

    assert response.status_code == 429
    assert response.json() == {"detail": "Refinement is temporarily unavailable."}
    assert response.headers["Retry-After"] == "7"
    assert captured_keys == ["fly:203.0.113.7"]


def test_post_search_refinements_releases_capacity_after_service_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    releases = 0

    class _Admission:
        accepted = True
        retry_after_seconds = None

        def release(self) -> None:
            nonlocal releases
            releases += 1

    class _Guard:
        def acquire(self, _client_key: str) -> _Admission:
            return _Admission()

    monkeypatch.setattr("app.api.routes.refinement_admission_guard", _Guard())
    monkeypatch.setattr(
        "app.api.routes.get_search_refinements",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("provider secret")),
    )

    response = TestClient(app).post("/api/search/refinements", json=_request_payload())

    assert response.status_code == 500
    assert releases == 1


def test_post_search_refinements_releases_capacity_when_executor_rejects_submit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    releases = 0

    class _Admission:
        accepted = True
        retry_after_seconds = None

        def release(self) -> None:
            nonlocal releases
            releases += 1

    class _Guard:
        def acquire(self, _client_key: str) -> _Admission:
            return _Admission()

    class _RejectingWorkerPool:
        def submit(self, *_args: object, **_kwargs: object) -> object:
            raise RuntimeError("executor is shutting down")

    monkeypatch.setattr("app.api.routes.refinement_admission_guard", _Guard())
    monkeypatch.setattr(
        "app.api.routes.refinement_worker_pool",
        _RejectingWorkerPool(),
    )

    response = TestClient(app).post("/api/search/refinements", json=_request_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to load refinements."}
    assert releases == 1


def test_post_search_refinements_fails_fast_while_timed_out_worker_is_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    releases = 0

    class _Admission:
        accepted = True
        retry_after_seconds = None

        def release(self) -> None:
            nonlocal releases
            releases += 1

    class _Guard:
        def acquire(self, _client_key: str) -> _Admission:
            return _Admission()

    class _UnavailableWorkerPool:
        def submit(self, *_args: object, **_kwargs: object) -> object:
            raise RefinementWorkerUnavailableError("worker still running")

    monkeypatch.setattr("app.api.routes.refinement_admission_guard", _Guard())
    monkeypatch.setattr(
        "app.api.routes.refinement_worker_pool",
        _UnavailableWorkerPool(),
    )
    monkeypatch.setattr(
        "app.api.routes.get_search_refinements",
        lambda **_kwargs: pytest.fail("open worker circuit must skip evaluation"),
    )

    response = TestClient(app).post("/api/search/refinements", json=_request_payload())

    assert response.status_code == 200
    assert response.json()["baseline_status"] == "unverified"
    assert response.json()["refinement_status"] == "temporarily_unavailable"
    assert releases == 1


def test_post_search_refinements_ignores_arbitrary_forwarded_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_keys: list[str] = []

    class _DeniedAdmission:
        accepted = False
        retry_after_seconds = 1

        def release(self) -> None:
            pytest.fail("rejected admission must not be released")

    class _Guard:
        def acquire(self, client_key: str) -> _DeniedAdmission:
            captured_keys.append(client_key)
            return _DeniedAdmission()

    monkeypatch.setattr("app.api.routes.refinement_admission_guard", _Guard())

    response = TestClient(app).post(
        "/api/search/refinements",
        json=_request_payload(),
        headers={"X-Forwarded-For": "203.0.113.9"},
    )

    assert response.status_code == 429
    assert captured_keys == ["client:testclient"]


def test_refinement_deadline_releases_endpoint_capacity_before_worker_finishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    releases = 0
    worker_released = threading.Event()
    allow_worker_to_finish = threading.Event()

    class _Admission:
        accepted = True
        retry_after_seconds = None

        def release(self) -> None:
            nonlocal releases
            releases += 1

    class _Guard:
        def acquire(self, _client_key: str) -> _Admission:
            return _Admission()

    def slow_refinement(**_kwargs: object) -> SearchV4RefinementResponse:
        assert allow_worker_to_finish.wait(timeout=1)
        worker_released.set()
        return SearchV4RefinementResponse(
            search_model_version="search-v4",
            ranking_policy_version="search-v4-policy-1",
            refinement_presentation_policy_version="search-refinement-presentation-1",
            refinement_status="not_needed",
        )

    monkeypatch.setattr("app.api.routes.refinement_admission_guard", _Guard())
    monkeypatch.setattr("app.api.routes.get_search_refinements", slow_refinement)
    monkeypatch.setattr(
        "app.api.routes.SEARCH_REFINEMENT_REQUEST_BUDGET_SECONDS",
        0.02,
    )

    response = TestClient(app).post("/api/search/refinements", json=_request_payload())

    assert response.status_code == 200
    assert response.json()["refinement_status"] == "temporarily_unavailable"
    assert response.json()["baseline_status"] == "unverified"
    assert not worker_released.is_set()
    assert releases == 1

    allow_worker_to_finish.set()
    assert worker_released.wait(timeout=1)
    assert releases == 1


def test_post_search_preserves_pinzolo_terrain_trust_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        search_v4_service.CatalogRepository,
        "get_snapshot",
        lambda _repository: load_catalog_from_path(CATALOG_PATH),
    )
    payload = _request_payload()
    payload["intent"] = {
        "constraints": {
            "location": {"country": "Italy"},
            "pass_price_ceiling": {
                "maximum": 320,
                "currency": "EUR",
                "duration_days": 6,
                "audience": "adult",
                "season": "high season 2025/26",
            },
        },
        "party": {"skill_levels": ["intermediate"]},
        "objectives": [],
    }

    payload.pop("brief")
    payload.pop("baseline_fingerprint")
    response = TestClient(app).post("/api/search", json=payload)

    assert response.status_code == 200
    pinzolo = next(
        configuration
        for group in response.json()["results"]
        for configuration in (
            group["top_configuration"],
            *group["alternative_configurations"],
        )
        if configuration["selected_pass"]["lift_pass_product_id"]
        == "pinzolo-local-pass"
    )
    assert pinzolo["selected_pass"]["accessible_piste_km"] == 31
    assert pinzolo["selected_pass"]["accessible_piste_km_evidence"] == {
        "trust_status": "estimated",
        "scope": "ski_area",
        "source_entity_id": "pinzolo-ski-area",
        "field_group": "terrain_metrics",
    }


def test_search_get_contract_is_removed() -> None:
    search_routes = [
        route for route in app.routes if getattr(route, "path", None) == "/api/search"
    ]

    assert len(search_routes) == 1
    assert search_routes[0].methods == {"POST"}


def test_post_search_rejects_untyped_raw_weights() -> None:
    payload = _ranking_request_payload()
    intent = payload["intent"]
    assert isinstance(intent, dict)
    intent["raw_weights"] = {"party_skill_coverage": 99}

    response = TestClient(app).post("/api/search", json=payload)

    assert response.status_code == 422


def test_post_search_maps_unregistered_intent_to_validation_error(monkeypatch) -> None:
    def reject_search(**_kwargs: object) -> SearchV4Response:
        raise SearchIntentPolicyError("unknown factor ID: invented")

    monkeypatch.setattr("app.api.routes.search_trip_configurations", reject_search)

    response = TestClient(app).post("/api/search", json=_ranking_request_payload())

    assert response.status_code == 422
    assert response.json()["detail"] == "unknown factor ID: invented"
