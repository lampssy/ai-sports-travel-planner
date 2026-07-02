from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.ai.parser import QueryParser, get_query_parser
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
    ResortConditionsRepository,
)
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
    LiftDistance,
    ParsedQueryResponse,
    ParseQueryRequest,
    RegisteredDevice,
    SearchDebugInfo,
    SearchFilters,
    SkillLevel,
    TravelTolerance,
    UpsertCurrentTripRequest,
)
from app.domain.search_models import (
    InvalidSearchModelError,
    SearchModelSelection,
    resolve_search_model_selection,
)
from app.domain.search_v3_models import RecommendationGroup
from app.domain.search_v3_service import search_trip_markets
from app.domain.trip_companion import (
    build_current_trip_summary,
    mark_current_trip_checked,
    maybe_record_companion_event,
)

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


class SearchResponse(BaseModel):
    results: list[RecommendationGroup]


class DebugSearchV3Response(SearchResponse):
    debug: SearchDebugInfo


class HealthResponse(BaseModel):
    status: str


class SearchReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str | int]


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


def _resolve_search_model_for_request(
    *,
    requested_search_model: str | None,
    debug: bool,
) -> SearchModelSelection:
    if requested_search_model is not None and not debug:
        raise HTTPException(
            status_code=403,
            detail="search_model override requires debug=true",
        )
    try:
        selection = resolve_search_model_selection(
            requested_model=requested_search_model,
        )
    except InvalidSearchModelError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if requested_search_model is not None and not selection.override_allowed:
        raise HTTPException(
            status_code=403,
            detail="search_model override is disabled",
        )
    return selection


@router.get("/search", response_model=None)
def search(
    location: str,
    min_price: float,
    max_price: float,
    stars: Annotated[int, Query(ge=1, le=3)],
    skill_level: SkillLevel,
    lift_distance: LiftDistance | None = None,
    budget_flex: Annotated[float | None, Query(ge=0, le=0.5)] = None,
    travel_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    trip_start_date: date | None = None,
    trip_end_date: date | None = None,
    origin_text: str | None = None,
    max_drive_minutes: Annotated[int | None, Query(ge=1)] = None,
    travel_tolerance: TravelTolerance | None = None,
    debug: bool = Query(default=False),
    search_model: str | None = None,
) -> SearchResponse | DebugSearchV3Response:
    if min_price > max_price:
        raise HTTPException(
            status_code=422,
            detail="min_price must be less than or equal to max_price",
        )
    if (trip_start_date is None) != (trip_end_date is None):
        raise HTTPException(
            status_code=422,
            detail="trip_start_date and trip_end_date must be provided together",
        )
    if (
        trip_start_date is not None
        and trip_end_date is not None
        and trip_end_date < trip_start_date
    ):
        raise HTTPException(
            status_code=422,
            detail="trip_end_date must be on or after trip_start_date",
        )

    filters = SearchFilters(
        location=location,
        min_price=min_price,
        max_price=max_price,
        stars=stars,
        skill_level=skill_level,
        lift_distance=lift_distance,
        budget_flex=budget_flex,
        travel_month=travel_month,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
        origin_text=origin_text,
        max_drive_minutes=max_drive_minutes,
        travel_tolerance=travel_tolerance,
    )
    search_model_selection = _resolve_search_model_for_request(
        requested_search_model=search_model,
        debug=debug,
    )
    results = search_trip_markets(filters)
    if debug:
        return DebugSearchV3Response(
            results=results,
            debug=SearchDebugInfo(
                narrative_source="none",
                narrative_cache_hit=False,
                narrative_error=None,
                narrative_model=None,
                top_result_resort_id=None,
                configured_search_model=search_model_selection.configured_search_model,
                requested_search_model=search_model_selection.requested_search_model,
                effective_search_model=search_model_selection.effective_search_model,
                search_model_override_applied=search_model_selection.override_applied,
            ),
        )
    return SearchResponse(results=results)


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

        conditions = ResortConditionsRepository().list_conditions()
        checks["conditions_count"] = len(conditions)
        if not conditions:
            checks["conditions"] = "empty"
            return SearchReadinessResponse(status="degraded", checks=checks)
        checks["conditions"] = "ok"
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
