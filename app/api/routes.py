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
from app.data.database import connect, resolve_database_url
from app.data.repositories import (
    AppSessionRepository,
    AppUserRepository,
    CompanionEventRepository,
    CurrentTripRepository,
    DeviceRegistrationRepository,
    OutboundBookingClickRepository,
    ResortRepository,
)
from app.domain.models import (
    AuthenticatedUser,
    AuthSessionResponse,
    CompanionEventsResponse,
    CurrentTrip,
    CurrentTripResponse,
    CurrentTripSummary,
    DebugParsedQueryResponse,
    DebugSearchResponse,
    DeviceRegistrationRequest,
    GoogleSignInRequest,
    LiftDistance,
    ParsedQueryResponse,
    ParseQueryRequest,
    RegisteredDevice,
    SearchFilters,
    SearchResult,
    SkillLevel,
    UpsertCurrentTripRequest,
)
from app.domain.search_service import build_accommodation_link
from app.domain.services import (
    search_resorts,
    search_resorts_with_debug,
)
from app.domain.trip_companion import (
    build_current_trip_summary,
    mark_current_trip_checked,
    maybe_record_companion_event,
)

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


class SearchResponse(BaseModel):
    results: list[SearchResult]


class HealthResponse(BaseModel):
    status: str


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
    debug: bool = Query(default=False),
) -> SearchResponse | DebugSearchResponse:
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
    )
    if debug:
        results, debug_info = search_resorts_with_debug(filters)
        return DebugSearchResponse(results=results, debug=debug_info)

    results = search_resorts(filters)
    return SearchResponse(results=results)


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    with connect(resolve_database_url()) as connection:
        connection.execute("SELECT 1").fetchone()
    return HealthResponse(status="ok")


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
    resort = ResortRepository().get_resort_by_id(payload.resort_id)
    if resort is None:
        raise HTTPException(status_code=404, detail="Unknown resort_id")

    selected_stay_base_name = (
        payload.selected_stay_base_name or payload.selected_area_name
    )
    if selected_stay_base_name not in {
        stay_base.name for stay_base in resort.stay_bases
    }:
        raise HTTPException(status_code=422, detail="Unknown selected_stay_base_name")

    selected_ski_area = next(
        (
            ski_area
            for ski_area in resort.ski_areas
            if ski_area.name == payload.selected_ski_area_name
        ),
        None,
    )
    if selected_ski_area is None:
        raise HTTPException(status_code=422, detail="Unknown selected_ski_area_name")

    repository = CurrentTripRepository()
    existing = repository.get_current_trip(user_id=current_user.user_id)
    now = datetime.now(UTC).isoformat()
    trip = CurrentTrip(
        resort_id=resort.resort_id,
        resort_name=resort.name,
        selected_ski_area_id=selected_ski_area.ski_area_id,
        selected_ski_area_name=selected_ski_area.name,
        selected_stay_base_name=selected_stay_base_name,
        selected_area_name=selected_stay_base_name,
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
    "/outbound/accommodation/{resort_id}",
    response_class=RedirectResponse,
    response_model=None,
)  # pragma: no cover - response model intentionally omitted for redirects
def outbound_accommodation_redirect(
    resort_id: str,
    request: Request,
    selected_stay_base_name: str | None = None,
    selected_area_name: str | None = None,
    selected_ski_area_name: str | None = None,
    source_surface: str = Query(min_length=1),
) -> RedirectResponse:
    resort = ResortRepository().get_resort_by_id(resort_id)
    if resort is None:
        raise HTTPException(status_code=404, detail="Unknown resort_id")

    effective_stay_base = selected_stay_base_name or selected_area_name
    if effective_stay_base is None:
        raise HTTPException(
            status_code=422,
            detail="selected_stay_base_name or selected_area_name is required",
        )
    if effective_stay_base not in {stay_base.name for stay_base in resort.stay_bases}:
        raise HTTPException(status_code=422, detail="Unknown selected_stay_base_name")
    if selected_ski_area_name is not None and selected_ski_area_name not in {
        ski_area.name for ski_area in resort.ski_areas
    }:
        raise HTTPException(status_code=422, detail="Unknown selected_ski_area_name")

    target_url = build_accommodation_link(
        resort_name=resort.name,
        country=resort.country,
    )

    repository = OutboundBookingClickRepository()
    repository.record_click(
        created_at=datetime.now(UTC).isoformat(),
        resort_id=resort_id,
        selected_area_name=effective_stay_base,
        selected_ski_area_name=selected_ski_area_name,
        target_url=target_url,
        source_surface=source_surface,
        request_id=request.headers.get("x-request-id"),
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse(url=target_url, status_code=307)
