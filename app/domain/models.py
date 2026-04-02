from typing import Literal

from pydantic import BaseModel, Field

Sport = Literal["ski", "windsurf"]
ActivityType = Literal["resort", "spot"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
SkillLevel = Literal["beginner", "intermediate", "advanced"]
PriceLevel = Literal["low", "medium", "high"]
Quality = Literal["budget", "standard", "premium"]
LiftDistance = Literal["near", "medium", "far"]
SnowQuality = Literal["poor", "fair", "good", "excellent"]


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
    name: str = Field(description="Area name used in the recommendation output.")
    price_range: str = Field(
        description="Human-readable accommodation price range for the area."
    )
    price_min: float
    price_max: float
    quality: Quality = Field(
        description="Normalized accommodation quality tier used by the ranking logic."
    )
    lift_distance: LiftDistance = Field(
        description="Normalized bucket describing proximity to the lift."
    )
    supported_skill_levels: list[SkillLevel] = Field(
        description="Skill levels that the area meaningfully supports."
    )


class Rental(BaseModel):
    name: str = Field(description="Rental provider name shown in search results.")
    price_range: str = Field(description="Human-readable equipment rental price range.")
    price_min: float
    price_max: float
    quality: Quality = Field(
        description="Normalized rental quality tier used by ranking."
    )
    lift_distance: LiftDistance = Field(
        description="Normalized bucket describing rental proximity to the lift."
    )


class Resort(BaseModel):
    resort_id: str = Field(
        description="Stable resort identifier for frontend keys and future linking."
    )
    name: str = Field(description="Resort display name.")
    country: str = Field(description="Country used for location filtering.")
    region: str = Field(description="Geographic region grouping for the resort.")
    price_level: PriceLevel
    areas: list[Area]
    rentals: list[Rental]


class ResortConditions(BaseModel):
    resort_name: str = Field(
        description="Resort name that this conditions record maps to."
    )
    snow_quality: SnowQuality
    weather_summary: str = Field(
        description="Short conditions summary shown in recommendation output."
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Confidence in the conditions signal itself, not recommendation confidence."
        ),
    )
    conditions_score: float = Field(
        ge=0,
        le=1,
        description="Normalized conditions contribution used by ranking.",
    )


class SearchFilters(BaseModel):
    location: str = Field(description="Country filter used for resort search.")
    min_price: float = Field(description="Preferred minimum package price range bound.")
    max_price: float = Field(description="Preferred maximum package price range bound.")
    stars: int = Field(
        ge=1,
        le=3,
        description="Minimum quality threshold where 1=budget, 2=standard, 3=premium.",
    )
    skill_level: SkillLevel = Field(
        description="Requested skier skill level used for suitability matching."
    )
    lift_distance: LiftDistance | None = Field(
        default=None,
        description="Optional minimum acceptable lift-distance bucket.",
    )
    budget_flex: float | None = Field(
        default=None,
        ge=0,
        le=0.5,
        description=(
            "Optional tolerance percentage used to admit slightly "
            "out-of-budget results."
        ),
        examples=[0.1],
    )


class SearchResult(BaseModel):
    resort_id: str = Field(
        description="Stable resort identifier for UI rendering and future deep links."
    )
    resort_name: str = Field(description="Resort display name.")
    region: str = Field(description="Geographic region of the recommended resort.")
    selected_area_name: str = Field(
        description="Single best-matching accommodation area for this recommendation."
    )
    selected_area_lift_distance: LiftDistance
    area_price_range: str
    rental_name: str
    rental_price_range: str
    rating_estimate: int
    link: str
    score: float
    budget_penalty: float = Field(
        description="Penalty applied when the result is allowed through budget flex."
    )
    conditions_summary: str = Field(
        description="Short weather and snow summary for the resort."
    )
    conditions_score: float = Field(
        ge=0,
        le=1,
        description="Normalized conditions contribution used in ranking.",
    )
    recommendation_reasons: list[str] = Field(
        description="Structured reasons explaining why this resort ranked highly."
    )
    recommendation_confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Confidence in the recommendation based on fit and conditions inputs."
        ),
    )
    tradeoff_summary: str = Field(
        description="Short summary of the main tradeoff behind the recommendation."
    )


class ParseQueryRequest(BaseModel):
    query: str = Field(description="Free-text ski trip request to parse into filters.")


class ParsedQueryResponse(BaseModel):
    filters: dict[str, str | int | float] = Field(
        description="Structured filters extracted from the free-text query."
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Confidence in the parser output, not in the recommendation engine."
        ),
    )
    unknown_parts: list[str] = Field(
        default_factory=list,
        description=(
            "Fragments of the query that were not confidently mapped to filters."
        ),
    )
