from typing import Literal

from pydantic import BaseModel


Sport = Literal["ski", "windsurf"]
ActivityType = Literal["resort", "spot"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
PriceLevel = Literal["low", "medium", "high"]
Quality = Literal["budget", "standard", "premium"]


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
    quality: Quality
    distance_to_lift: str


class Rental(BaseModel):
    name: str
    price_range: str
    quality: Quality
    distance_to_lift: str


class Resort(BaseModel):
    name: str
    country: str
    price_level: PriceLevel
    areas: list[Area]
    rentals: list[Rental]


class SearchResult(BaseModel):
    resort_name: str
    selected_area_name: str
    area_price_range: str
    rental_name: str
    rental_price_range: str
    rating_estimate: int
    link: str
    score: float
