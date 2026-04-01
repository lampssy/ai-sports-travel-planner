from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.ai.parser import QueryParser, get_query_parser
from app.domain.models import (
    Activity,
    LiftDistance,
    ParsedQueryResponse,
    ParseQueryRequest,
    SearchFilters,
    SearchResult,
    SkillLevel,
)
from app.domain.services import recommend_activities, search_resorts

router = APIRouter()

Sport = Literal["ski", "windsurf"]
Difficulty = Literal["beginner", "intermediate", "advanced"]


class RecommendActivitiesResponse(BaseModel):
    activities: list[Activity]


class SearchResponse(BaseModel):
    results: list[SearchResult]


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


@router.get("/search", response_model=SearchResponse)
def search(
    location: str,
    min_price: float,
    max_price: float,
    stars: Annotated[int, Query(ge=1, le=3)],
    skill_level: SkillLevel,
    lift_distance: LiftDistance | None = None,
    budget_flex: Annotated[float | None, Query(ge=0, le=0.5)] = None,
) -> SearchResponse:
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
    )
    results = search_resorts(filters)
    return SearchResponse(results=results)


@router.post("/parse-query", response_model=ParsedQueryResponse)
def parse_query(
    payload: ParseQueryRequest,
    parser: QueryParser = Depends(get_query_parser),
) -> ParsedQueryResponse:
    parsed = parser.parse(payload.query)
    return ParsedQueryResponse.model_validate(parsed)
