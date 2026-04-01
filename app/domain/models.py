from typing import Literal

from pydantic import BaseModel, Field

Sport = Literal["ski", "windsurf"]
ActivityType = Literal["resort", "spot"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
SkillLevel = Literal["beginner", "intermediate", "advanced"]
PriceLevel = Literal["low", "medium", "high"]
Quality = Literal["budget", "standard", "premium"]
LiftDistance = Literal["near", "medium", "far"]


class Activity(BaseModel):
    name: str
    destination: str
    region: str
    sport: Sport
    type: ActivityType
    difficulty: Difficulty
    description: str
    price_per_day: float
    currency: str


class Area(BaseModel):
    name: str
    price_range: str
    price_min: float
    price_max: float
    quality: Quality
    lift_distance: LiftDistance
    supported_skill_levels: list[SkillLevel]


class Rental(BaseModel):
    name: str
    price_range: str
    price_min: float
    price_max: float
    quality: Quality
    lift_distance: LiftDistance


class Resort(BaseModel):
    name: str
    country: str
    price_level: PriceLevel
    areas: list[Area]
    rentals: list[Rental]


class SearchFilters(BaseModel):
    location: str
    min_price: float
    max_price: float
    stars: int = Field(ge=1, le=3)
    skill_level: SkillLevel
    lift_distance: LiftDistance | None = None
    budget_flex: float | None = Field(default=None, ge=0, le=0.5)


class SearchResult(BaseModel):
    resort_name: str
    selected_area_name: str
    selected_area_lift_distance: LiftDistance
    area_price_range: str
    rental_name: str
    rental_price_range: str
    rating_estimate: int
    link: str
    score: float
    budget_penalty: float


class ParseQueryRequest(BaseModel):
    query: str


class ParsedQueryResponse(BaseModel):
    filters: dict[str, str | int | float]
    confidence: float = Field(ge=0, le=1)
    unknown_parts: list[str] = Field(default_factory=list)
