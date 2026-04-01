from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.domain.models import Activity, SearchResult
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
) -> SearchResponse:
    if min_price > max_price:
        raise HTTPException(
            status_code=422,
            detail="min_price must be less than or equal to max_price",
        )

    results = search_resorts(
        location=location,
        min_price=min_price,
        max_price=max_price,
        stars=stars,
    )
    return SearchResponse(results=results)
