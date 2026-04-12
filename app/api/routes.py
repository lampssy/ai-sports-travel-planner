from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.ai.parser import QueryParser, get_query_parser
from app.data.database import connect, resolve_db_path
from app.data.repositories import (
    CurrentTripRepository,
    OutboundBookingClickRepository,
    ResortRepository,
)
from app.domain.models import (
    Activity,
    CurrentTrip,
    CurrentTripResponse,
    CurrentTripSummary,
    DebugParsedQueryResponse,
    DebugSearchResponse,
    LiftDistance,
    ParsedQueryResponse,
    ParseQueryRequest,
    SearchFilters,
    SearchResult,
    SkillLevel,
    UpsertCurrentTripRequest,
)
from app.domain.search_service import build_accommodation_link
from app.domain.services import (
    recommend_activities,
    search_resorts,
    search_resorts_with_debug,
)
from app.domain.trip_companion import (
    build_current_trip_summary,
    mark_current_trip_checked,
)

router = APIRouter()

Sport = Literal["ski", "windsurf"]
Difficulty = Literal["beginner", "intermediate", "advanced"]


class RecommendActivitiesResponse(BaseModel):
    activities: list[Activity]


class SearchResponse(BaseModel):
    results: list[SearchResult]


class HealthResponse(BaseModel):
    status: str


@router.get("/recommend-activities", response_model=RecommendActivitiesResponse)
def get_recommended_activities(
    sport: Sport,
    region: str,
    difficulty: Difficulty,
) -> RecommendActivitiesResponse:
    activities = recommend_activities(
        sport=sport,
        region=region,
        difficulty=difficulty,
    )
    return RecommendActivitiesResponse(activities=activities)


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
    debug: bool = Query(default=False),
) -> SearchResponse | DebugSearchResponse:
    if min_price > max_price:
        raise HTTPException(
            status_code=422,
            detail="min_price must be less than or equal to max_price",
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
    with connect(resolve_db_path()) as connection:
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


@router.get("/current-trip", response_model=CurrentTripResponse)
def get_current_trip() -> CurrentTripResponse:
    trip = CurrentTripRepository().get_current_trip()
    return CurrentTripResponse(trip=trip)


@router.put("/current-trip", response_model=CurrentTrip)
def upsert_current_trip(payload: UpsertCurrentTripRequest) -> CurrentTrip:
    resort = ResortRepository().get_resort_by_id(payload.resort_id)
    if resort is None:
        raise HTTPException(status_code=404, detail="Unknown resort_id")
    if payload.selected_area_name not in {area.name for area in resort.areas}:
        raise HTTPException(status_code=422, detail="Unknown selected_area_name")

    repository = CurrentTripRepository()
    existing = repository.get_current_trip()
    now = datetime.now(UTC).isoformat()
    trip = CurrentTrip(
        resort_id=resort.resort_id,
        resort_name=resort.name,
        selected_area_name=payload.selected_area_name,
        travel_month=payload.travel_month,
        booking_status=payload.booking_status,
        created_at=existing.created_at if existing is not None else now,
        updated_at=now,
        last_checked_at=existing.last_checked_at if existing is not None else None,
    )
    return repository.upsert_current_trip(trip)


@router.delete("/current-trip", status_code=204, response_model=None)
def delete_current_trip() -> None:
    CurrentTripRepository().clear_current_trip()
    return None


@router.get("/current-trip/summary", response_model=CurrentTripSummary)
def get_current_trip_summary() -> CurrentTripSummary:
    summary = build_current_trip_summary()
    if summary is None:
        raise HTTPException(status_code=404, detail="No current trip saved")
    return summary


@router.post("/current-trip/mark-checked", response_model=CurrentTrip)
def mark_current_trip_checked_endpoint() -> CurrentTrip:
    trip = mark_current_trip_checked()
    if trip is None:
        raise HTTPException(status_code=404, detail="No current trip saved")
    return trip


@router.get(
    "/outbound/accommodation/{resort_id}",
    response_class=RedirectResponse,
    response_model=None,
)  # pragma: no cover - response model intentionally omitted for redirects
def outbound_accommodation_redirect(
    resort_id: str,
    request: Request,
    selected_area_name: str,
    source_surface: str = Query(min_length=1),
) -> RedirectResponse:
    resort = ResortRepository().get_resort_by_id(resort_id)
    if resort is None:
        raise HTTPException(status_code=404, detail="Unknown resort_id")

    target_url = build_accommodation_link(
        resort_name=resort.name,
        country=resort.country,
    )

    repository = OutboundBookingClickRepository()
    repository.record_click(
        created_at=datetime.now(UTC).isoformat(),
        resort_id=resort_id,
        selected_area_name=selected_area_name,
        target_url=target_url,
        source_surface=source_surface,
        request_id=request.headers.get("x-request-id"),
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse(url=target_url, status_code=307)
