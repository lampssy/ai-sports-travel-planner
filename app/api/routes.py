import ipaddress
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextvars import copy_context
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.ai.gemini_client import GeminiClient
from app.ai.parser import QueryParser, get_query_parser
from app.api.refinement_admission import RefinementAdmissionGuard
from app.auth.google import (
    GoogleAuthConfigurationError,
    GoogleIdentityTokenError,
    verify_google_identity_token,
)
from app.data.catalog_repository import CatalogRepository
from app.data.database import connect, resolve_database_url
from app.data.repositories import (
    AppSessionRepository,
    AppUserRepository,
    CompanionEventRepository,
    CurrentTripRepository,
    DeviceRegistrationRepository,
    OutboundBookingClickRepository,
)
from app.data.weather_forecast_repository import WeatherForecastRepository
from app.domain.booking import build_accommodation_link
from app.domain.catalog_graph import CatalogGraph
from app.domain.models import (
    AuthenticatedUser,
    AuthSessionResponse,
    CompanionEventsResponse,
    CurrentTrip,
    CurrentTripResponse,
    CurrentTripSummary,
    DebugParsedQueryResponse,
    DeviceRegistrationRequest,
    GoogleSignInRequest,
    ParsedQueryResponse,
    ParseQueryRequest,
    RegisteredDevice,
    UpsertCurrentTripRequest,
)
from app.domain.search_factors import build_factor_registry
from app.domain.search_intent_policy import SearchIntentPolicyError
from app.domain.search_policy import load_search_policy
from app.domain.search_refinement_presentation import (
    load_refinement_presentation_policy,
)
from app.domain.search_v4_service import (
    SEARCH_REFINEMENT_REQUEST_BUDGET_SECONDS,
    SearchV4RefinementRequest,
    SearchV4RefinementResponse,
    SearchV4Request,
    SearchV4Response,
    UnknownSearchWeatherAreaError,
    forecast_run_is_fresh,
    get_search_refinements,
    get_search_weather_evidence,
    search_trip_configurations,
)
from app.domain.search_weather_evidence import (
    SearchWeatherEvidenceRequest,
    SearchWeatherEvidenceResponse,
)
from app.domain.trip_companion import (
    build_current_trip_summary,
    mark_current_trip_checked,
    maybe_record_companion_event,
)
from app.observability.search import record_search_refinement_route_outcome

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)
refinement_admission_guard = RefinementAdmissionGuard()
refinement_executor = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="search-refinement",
)


class HealthResponse(BaseModel):
    status: str


class SearchReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str | int]


class ApiErrorResponse(BaseModel):
    detail: str


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")

    user = AppSessionRepository().get_user_for_access_token(
        access_token=credentials.credentials
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


@router.post("/search", response_model=SearchV4Response)
def search(payload: SearchV4Request) -> SearchV4Response:
    try:
        return search_trip_configurations(intent=payload.intent)
    except SearchIntentPolicyError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/search/refinements",
    response_model=SearchV4RefinementResponse,
    responses={
        429: {
            "model": ApiErrorResponse,
            "description": "Refinement admission limit reached",
            "headers": {
                "Retry-After": {
                    "description": "Seconds before another refinement request",
                    "schema": {"type": "integer", "minimum": 1},
                }
            },
        }
    },
)
def search_refinements(
    payload: SearchV4RefinementRequest,
    request: Request,
) -> SearchV4RefinementResponse:
    request_started_at = time.monotonic()
    admission = refinement_admission_guard.acquire(_refinement_client_key(request))
    if not admission.accepted:
        record_search_refinement_route_outcome("admission_rejected")
        headers = (
            {"Retry-After": str(admission.retry_after_seconds)}
            if admission.retry_after_seconds is not None
            else None
        )
        raise HTTPException(
            status_code=429,
            detail="Refinement is temporarily unavailable.",
            headers=headers,
        )
    worker_context = copy_context()
    try:
        future = refinement_executor.submit(
            worker_context.run,
            get_search_refinements,
            intent=payload.intent,
            brief=payload.brief,
            baseline_fingerprint=payload.baseline_fingerprint,
            already_answered_question_ids=frozenset(
                payload.already_answered_question_ids
            ),
            llm_client_factory=lambda timeout_seconds: GeminiClient(
                timeout_seconds=timeout_seconds
            ),
            request_started_at=request_started_at,
        )
    except Exception as error:
        admission.release()
        record_search_refinement_route_outcome("executor_rejected")
        raise HTTPException(
            status_code=500,
            detail="Unable to load refinements.",
        ) from error
    future.add_done_callback(lambda _future: admission.release())
    remaining_seconds = max(
        0.0,
        SEARCH_REFINEMENT_REQUEST_BUDGET_SECONDS
        - (time.monotonic() - request_started_at),
    )
    try:
        response = future.result(timeout=remaining_seconds)
        record_search_refinement_route_outcome("completed")
        return response
    except FutureTimeoutError:
        record_search_refinement_route_outcome("deadline_exceeded")
        policy = load_search_policy()
        presentation = load_refinement_presentation_policy()
        return SearchV4RefinementResponse(
            search_model_version=policy.search_model_version,
            ranking_policy_version=policy.ranking_policy_version,
            refinement_presentation_policy_version=(
                presentation.presentation_policy_version
            ),
            baseline_fingerprint=payload.baseline_fingerprint,
            baseline_status="unverified",
            refinement_status="temporarily_unavailable",
        )
    except SearchIntentPolicyError as error:
        record_search_refinement_route_outcome("invalid_intent")
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        record_search_refinement_route_outcome("route_error")
        raise HTTPException(
            status_code=500,
            detail="Unable to load refinements.",
        ) from error


def _refinement_client_key(request: Request) -> str:
    fly_client_ip = request.headers.get("Fly-Client-IP")
    if fly_client_ip:
        try:
            return f"fly:{ipaddress.ip_address(fly_client_ip).compressed}"
        except ValueError:
            pass
    if request.client is None or not request.client.host:
        return "client:unknown"
    return f"client:{request.client.host}"


@router.post(
    "/search/weather-evidence",
    response_model=SearchWeatherEvidenceResponse,
)
def search_weather_evidence(
    payload: SearchWeatherEvidenceRequest,
) -> SearchWeatherEvidenceResponse:
    try:
        return get_search_weather_evidence(
            intent=payload.intent,
            ski_area_id=payload.ski_area_id,
        )
    except SearchIntentPolicyError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except UnknownSearchWeatherAreaError as error:
        raise HTTPException(status_code=422, detail="Unknown ski area ID.") from error


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    with connect(resolve_database_url()) as connection:
        connection.execute("SELECT 1").fetchone()
    return HealthResponse(status="ok")


@router.get("/search-readiness", response_model=SearchReadinessResponse)
def search_readiness() -> SearchReadinessResponse:
    checks: dict[str, str | int] = {}
    try:
        with connect(resolve_database_url()) as connection:
            connection.execute("SELECT 1").fetchone()
        checks["database"] = "ok"

        snapshot = CatalogRepository().get_snapshot()
        ski_area_count = len(snapshot.ski_areas)
        checks["resort_count"] = len(snapshot.stay_destinations)
        checks["ski_area_count"] = ski_area_count
        if not snapshot.stay_destinations or ski_area_count == 0:
            checks["catalog"] = "empty"
            raise HTTPException(status_code=503, detail=checks)
        checks["catalog"] = "ok"

        policy = load_search_policy()
        registry = build_factor_registry()
        registry.validate_policy(policy)
        presentation = load_refinement_presentation_policy()
        checks["search_model"] = policy.search_model_version
        checks["ranking_policy"] = policy.ranking_policy_version
        checks["refinement_presentation_policy"] = (
            presentation.presentation_policy_version
        )
        checks["factor_count"] = len(policy.factors)
        checks["factor_registry"] = "ok"

        heads = WeatherForecastRepository().list_heads()
        now = datetime.now(UTC)
        source_keys = {
            policy.weather.preferred_short_range_source,
            policy.weather.fallback_and_long_range_source,
        }
        expected_pairs = {
            (area.ski_area_id, source_key)
            for area in snapshot.ski_areas
            for source_key in source_keys
        }
        heads_by_pair = {
            (head.ski_area_id, head.forecast_source_key): head
            for head in heads
            if (head.ski_area_id, head.forecast_source_key) in expected_pairs
        }
        fresh_pairs = {
            pair
            for pair, head in heads_by_pair.items()
            if forecast_run_is_fresh(head.run, now)
        }
        checks["expected_forecast_head_count"] = len(expected_pairs)
        checks["forecast_head_count"] = len(heads_by_pair)
        checks["fresh_forecast_head_count"] = len(fresh_pairs)
        checks["missing_forecast_head_count"] = len(
            expected_pairs - heads_by_pair.keys()
        )
        checks["stale_forecast_head_count"] = len(heads_by_pair.keys() - fresh_pairs)
        if len(heads_by_pair) < len(expected_pairs):
            checks["forecast_heads"] = "missing_or_partial"
            return SearchReadinessResponse(status="degraded", checks=checks)
        if len(fresh_pairs) < len(expected_pairs):
            checks["forecast_heads"] = "stale_or_partial"
            return SearchReadinessResponse(status="degraded", checks=checks)
        checks["forecast_heads"] = "fresh"
        return SearchReadinessResponse(status="ok", checks=checks)
    except HTTPException:
        raise
    except Exception as error:
        checks["error"] = error.__class__.__name__
        raise HTTPException(status_code=503, detail=checks) from error


@router.post("/parse-query", response_model=None)
def parse_query(
    payload: ParseQueryRequest,
    parser: QueryParser = Depends(get_query_parser),
    debug: bool = Query(default=False),
) -> ParsedQueryResponse | DebugParsedQueryResponse:
    if debug:
        parsed, debug_info = parser.parse_with_debug(payload.query)
        return DebugParsedQueryResponse(
            **ParsedQueryResponse.model_validate(parsed).model_dump(),
            debug=debug_info,
        )

    parsed = parser.parse(payload.query)
    return ParsedQueryResponse.model_validate(parsed)


@router.post("/auth/google/sign-in", response_model=AuthSessionResponse)
def google_sign_in(payload: GoogleSignInRequest) -> AuthSessionResponse:
    try:
        identity = verify_google_identity_token(payload.identity_token)
    except GoogleAuthConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except GoogleIdentityTokenError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    user = AppUserRepository().upsert_google_user(
        provider_subject=identity.subject,
        email=identity.email,
        display_name=identity.display_name,
    )
    return AppSessionRepository().create_session(user=user)


@router.get("/current-trip", response_model=CurrentTripResponse)
def get_current_trip(
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> CurrentTripResponse:
    trip = CurrentTripRepository().get_current_trip(user_id=current_user.user_id)
    return CurrentTripResponse(trip=trip)


@router.put("/current-trip", response_model=CurrentTrip)
def upsert_current_trip(
    payload: UpsertCurrentTripRequest,
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> CurrentTrip:
    graph = CatalogGraph.from_snapshot(CatalogRepository().get_snapshot())
    region = graph.regions_by_id.get(payload.ski_region_id)
    destination = graph.destinations_by_id.get(payload.stay_destination_id)
    base = graph.bases_by_id.get(payload.stay_base_id)
    area = graph.areas_by_id.get(payload.focus_ski_area_id)
    product = graph.passes_by_id.get(payload.lift_pass_product_id)
    if any(item is None for item in (region, destination, base, area, product)):
        raise HTTPException(status_code=422, detail="Unknown trip configuration ID")
    assert region is not None
    assert destination is not None
    assert base is not None
    assert area is not None
    assert product is not None
    access_exists = any(
        access.ski_area_id == area.ski_area_id
        for access in graph.accesses_by_base_id.get(base.stay_base_id, ())
    )
    covering_pass_ids = {
        item.lift_pass_product_id
        for item in graph.passes_by_destination_area.get(
            (destination.stay_destination_id, area.ski_area_id), ()
        )
    }
    if (
        destination.trip_market_region_id != region.ski_region_id
        or base.stay_destination_id != destination.stay_destination_id
        or not access_exists
        or product.lift_pass_product_id not in covering_pass_ids
    ):
        raise HTTPException(status_code=422, detail="Invalid trip configuration")
    if (
        payload.ski_region_name != region.name
        or payload.stay_destination_name != destination.name
        or payload.stay_base_name != base.name
        or payload.focus_ski_area_name != area.name
        or payload.lift_pass_product_name != product.name
    ):
        raise HTTPException(status_code=422, detail="Trip display names do not match")

    repository = CurrentTripRepository()
    existing = repository.get_current_trip(user_id=current_user.user_id)
    now = datetime.now(UTC).isoformat()
    trip = CurrentTrip(
        ski_region_id=region.ski_region_id,
        ski_region_name=region.name,
        stay_destination_id=destination.stay_destination_id,
        stay_destination_name=destination.name,
        stay_base_id=base.stay_base_id,
        stay_base_name=base.name,
        focus_ski_area_id=area.ski_area_id,
        focus_ski_area_name=area.name,
        lift_pass_product_id=product.lift_pass_product_id,
        lift_pass_product_name=product.name,
        travel_month=payload.travel_month,
        trip_start_date=payload.trip_start_date,
        trip_end_date=payload.trip_end_date,
        booking_status=payload.booking_status,
        created_at=existing.created_at if existing is not None else now,
        updated_at=now,
        last_checked_at=existing.last_checked_at if existing is not None else None,
    )
    return repository.upsert_current_trip(user_id=current_user.user_id, trip=trip)


@router.delete("/current-trip", status_code=204, response_model=None)
def delete_current_trip(
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    CurrentTripRepository().clear_current_trip(user_id=current_user.user_id)
    return None


@router.get("/current-trip/summary", response_model=CurrentTripSummary)
def get_current_trip_summary(
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> CurrentTripSummary:
    summary = build_current_trip_summary(user_id=current_user.user_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="No current trip saved")
    maybe_record_companion_event(user_id=current_user.user_id, summary=summary)
    return summary


@router.post("/current-trip/mark-checked", response_model=CurrentTrip)
def mark_current_trip_checked_endpoint(
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> CurrentTrip:
    trip = mark_current_trip_checked(user_id=current_user.user_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="No current trip saved")
    return trip


@router.post("/devices/register", response_model=RegisteredDevice)
def register_device(
    payload: DeviceRegistrationRequest,
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
):
    return DeviceRegistrationRepository().register_device(
        user_id=current_user.user_id,
        installation_id=payload.installation_id,
        platform=payload.platform,
        push_token=payload.push_token,
        push_enabled=payload.push_enabled,
    )


@router.get("/current-trip/events", response_model=CompanionEventsResponse)
def get_current_trip_events(
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> CompanionEventsResponse:
    summary = build_current_trip_summary(user_id=current_user.user_id)
    if summary is not None:
        maybe_record_companion_event(user_id=current_user.user_id, summary=summary)
    return CompanionEventsResponse(
        events=CompanionEventRepository().list_events_for_user(
            user_id=current_user.user_id
        )
    )


@router.get(
    "/outbound/accommodation/{stay_destination_id}",
    response_class=RedirectResponse,
    response_model=None,
)  # pragma: no cover - response model intentionally omitted for redirects
def outbound_accommodation_redirect(
    stay_destination_id: str,
    request: Request,
    stay_base_id: str,
    focus_ski_area_id: str,
    source_surface: str = Query(min_length=1),
) -> RedirectResponse:
    graph = CatalogGraph.from_snapshot(CatalogRepository().get_snapshot())
    destination = graph.destinations_by_id.get(stay_destination_id)
    base = graph.bases_by_id.get(stay_base_id)
    access_exists = any(
        access.ski_area_id == focus_ski_area_id
        for access in graph.accesses_by_base_id.get(stay_base_id, ())
    )
    if (
        destination is None
        or base is None
        or base.stay_destination_id != stay_destination_id
        or focus_ski_area_id not in graph.areas_by_id
        or not access_exists
    ):
        raise HTTPException(status_code=404, detail="Unknown trip configuration")

    target_url = build_accommodation_link(
        destination_name=destination.name,
        country=destination.country,
    )

    repository = OutboundBookingClickRepository()
    repository.record_click(
        created_at=datetime.now(UTC).isoformat(),
        stay_destination_id=stay_destination_id,
        stay_base_id=stay_base_id,
        focus_ski_area_id=focus_ski_area_id,
        target_url=target_url,
        source_surface=source_surface,
        request_id=request.headers.get("x-request-id"),
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse(url=target_url, status_code=307)
