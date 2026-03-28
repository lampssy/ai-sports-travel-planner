from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.models import Activity
from app.domain.services import recommend_activities


router = APIRouter()

Sport = Literal["ski", "windsurf"]
Difficulty = Literal["beginner", "intermediate", "advanced"]


class RecommendActivitiesResponse(BaseModel):
    activities: list[Activity]


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
