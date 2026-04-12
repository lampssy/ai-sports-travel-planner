from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Sport = Literal["ski", "windsurf"]
ActivityType = Literal["resort", "spot"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
SkillLevel = Literal["beginner", "intermediate", "advanced"]
PriceLevel = Literal["low", "medium", "high"]
Quality = Literal["budget", "standard", "premium"]
LiftDistance = Literal["near", "medium", "far"]
SnowConfidenceLabel = Literal["poor", "fair", "good"]
AvailabilityStatus = Literal["open", "limited", "temporarily_closed", "out_of_season"]
ExplanationDirection = Literal["positive", "negative"]
SourceType = Literal["forecast", "reported", "estimated"]
FreshnessStatus = Literal["fresh", "stale", "historical", "unknown"]
BookingStatus = Literal[
    "not_booked_yet",
    "booked_through_app",
    "booked_elsewhere",
]
ComparisonBasisKind = Literal["since_last_check", "since_trip_saved"]
CurrentTripDeltaStatus = Literal["changed", "unchanged", "insufficient_history"]
ParserSource = Literal["llm", "llm_cache", "heuristic_fallback"]
ParserFallbackReason = Literal[
    "quota_error",
    "auth_error",
    "network_error",
    "provider_error",
    "invalid_output",
    "low_confidence",
    "empty_filters",
]
NarrativeSource = Literal["llm", "llm_cache", "skipped_non_top_result", "none"]
NarrativeError = Literal[
    "quota_error",
    "auth_error",
    "network_error",
    "provider_error",
    "invalid_output",
]


def snow_confidence_label_for_score(score: float) -> SnowConfidenceLabel:
    if score < 0.35:
        return "poor"
    if score < 0.7:
        return "fair"
    return "good"


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
    latitude: float = Field(description="Latitude used for weather lookups.")
    longitude: float = Field(description="Longitude used for weather lookups.")
    base_elevation_m: int = Field(
        description="Approximate village/base elevation in meters above sea level."
    )
    summit_elevation_m: int = Field(
        description="Approximate summit elevation in meters above sea level."
    )
    season_start_month: int = Field(
        ge=1,
        le=12,
        description="Typical start month of the ski season for seasonality heuristics.",
    )
    season_end_month: int = Field(
        ge=1,
        le=12,
        description="Typical end month of the ski season for seasonality heuristics.",
    )
    areas: list[Area]
    rentals: list[Rental]


class ResortConditions(BaseModel):
    resort_name: str = Field(
        description="Resort name that this conditions record maps to."
    )
    snow_confidence_score: float = Field(
        ge=0,
        le=1,
        description="Normalized snow-confidence signal for overall trip suitability.",
    )
    snow_confidence_label: SnowConfidenceLabel = Field(
        description=(
            "User-facing interpretation of the snow-confidence signal where "
            "poor/fair/good summarize trip suitability."
        )
    )
    availability_status: AvailabilityStatus = Field(
        description="Operational resort availability signal used in ranking."
    )
    weather_summary: str = Field(
        description="Short conditions summary shown in recommendation output."
    )
    conditions_score: float = Field(
        ge=0,
        le=1,
        description="Normalized conditions contribution used by ranking.",
    )
    updated_at: str | None = Field(
        default=None,
        description="Timestamp of the last successful conditions refresh.",
    )
    source: str | None = Field(
        default=None,
        description="Origin of the conditions record, for example open-meteo.",
    )

    @model_validator(mode="before")
    @classmethod
    def populate_snow_label(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        score = data.get("snow_confidence_score")
        if score is None:
            return data

        derived = snow_confidence_label_for_score(float(score))
        provided = data.get("snow_confidence_label")
        if provided is None:
            data["snow_confidence_label"] = derived
            return data

        if provided != derived:
            raise ValueError(
                "snow_confidence_label must match snow_confidence_score thresholds"
            )
        return data


class ResortConditionSnapshot(BaseModel):
    resort_id: str = Field(description="Stable resort identifier for the snapshot.")
    resort_name: str = Field(description="Resort name captured at snapshot time.")
    observed_month: int = Field(
        ge=1,
        le=12,
        description="Calendar month represented by this conditions snapshot.",
    )
    observed_at: str = Field(
        description="Timestamp at which the snapshot was recorded."
    )
    snow_confidence_score: float = Field(
        ge=0,
        le=1,
        description="Snow-confidence signal captured for this snapshot.",
    )
    snow_confidence_label: SnowConfidenceLabel = Field(
        description="Derived snow-confidence label captured for this snapshot."
    )
    availability_status: AvailabilityStatus = Field(
        description="Availability status captured for this snapshot."
    )
    weather_summary: str = Field(
        description="Weather summary captured for this snapshot."
    )
    conditions_score: float = Field(
        ge=0,
        le=1,
        description="Normalized conditions contribution captured for this snapshot.",
    )
    source: str | None = Field(
        default=None,
        description="Origin of the snapshot, for example open-meteo.",
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
    travel_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Optional travel month used for planning-oriented search.",
    )


class CurrentTrip(BaseModel):
    resort_id: str = Field(description="Stable resort identifier for the saved trip.")
    resort_name: str = Field(description="Display name of the saved resort.")
    selected_area_name: str = Field(
        description="Selected area carried into the saved trip context."
    )
    travel_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Optional saved travel month for the current trip.",
    )
    booking_status: BookingStatus = Field(
        description="Current booking state for the saved trip."
    )
    created_at: str = Field(description="Timestamp of the first save.")
    updated_at: str = Field(description="Timestamp of the latest trip update.")
    last_checked_at: str | None = Field(
        default=None,
        description="Timestamp of the last explicit companion check-in.",
    )


class UpsertCurrentTripRequest(BaseModel):
    resort_id: str = Field(description="Selected resort identifier for the trip.")
    selected_area_name: str = Field(
        description="Selected area name for the trip context."
    )
    travel_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Optional travel month for the trip context.",
    )
    booking_status: BookingStatus = Field(
        description="Booking status selected by the user for the trip."
    )


class CurrentTripResponse(BaseModel):
    trip: CurrentTrip | None = Field(
        default=None,
        description="The currently saved trip, if one exists.",
    )


class CurrentTripComparisonBasis(BaseModel):
    kind: ComparisonBasisKind = Field(
        description=(
            "Whether the comparison is since the last explicit check or since "
            "the trip was first saved."
        )
    )
    baseline_at: str = Field(
        description="Timestamp used as the current comparison baseline."
    )
    label: str = Field(
        description="Human-readable description of the comparison basis."
    )


class CurrentTripDelta(BaseModel):
    status: CurrentTripDeltaStatus = Field(
        description=(
            "Whether current conditions changed, stayed the same, or lack "
            "enough earlier history to compare."
        )
    )
    summary: str = Field(description="Compact user-facing summary of what changed.")
    changes: list[str] = Field(
        default_factory=list,
        description=(
            "Specific condition changes detected since the comparison baseline."
        ),
    )


class CurrentTripSummary(BaseModel):
    trip: CurrentTrip = Field(description="Persisted single current-trip context.")
    current_conditions: ResortConditions = Field(
        description="Latest current conditions available for the trip resort."
    )
    current_conditions_provenance: "ProvenanceInfo" = Field(
        description="Trust and freshness metadata for the current conditions signal."
    )
    comparison_basis: CurrentTripComparisonBasis = Field(
        description="Metadata describing the timestamp used for delta comparison."
    )
    delta: CurrentTripDelta = Field(
        description=(
            "Conditions-only delta summary since the chosen comparison baseline."
        )
    )


class ExplanationItem(BaseModel):
    label: str = Field(description="Short product-facing explanation label.")


class ConfidenceContributor(BaseModel):
    label: str = Field(description="Short reason influencing confidence.")
    direction: ExplanationDirection = Field(
        description=(
            "Whether the contributor raises or lowers recommendation confidence."
        )
    )


class SearchExplanation(BaseModel):
    highlights: list[ExplanationItem] = Field(
        description="Strong positive reasons this resort is attractive."
    )
    risks: list[ExplanationItem] = Field(
        description="Important downsides or penalties attached to this result."
    )
    confidence_contributors: list[ConfidenceContributor] = Field(
        description="Structured reasons behind the single recommendation confidence."
    )


class ProvenanceInfo(BaseModel):
    source_name: str | None = Field(
        default=None,
        description="Human-readable source or provenance basis name.",
    )
    source_type: SourceType = Field(
        description="Semantic evidence type shown in the trust UI."
    )
    updated_at: str | None = Field(
        default=None,
        description="Timestamp of the last relevant source update when available.",
    )
    freshness_status: FreshnessStatus = Field(
        description="Freshness classification used for trust presentation."
    )
    basis_summary: str = Field(
        description="Short summary of what evidence this signal is based on."
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
    link: str = Field(
        description=(
            "Outbound accommodation booking target for the selected area, suitable "
            "for tracked redirect flows."
        )
    )
    score: float
    budget_penalty: float = Field(
        description="Penalty applied when the result is allowed through budget flex."
    )
    conditions_summary: str = Field(
        description="Short weather and snow summary for the resort."
    )
    snow_confidence_score: float = Field(
        ge=0,
        le=1,
        description="Normalized snow-confidence signal used by ranking and debugging.",
    )
    snow_confidence_label: SnowConfidenceLabel = Field(
        description="User-facing snow-confidence interpretation for the trip window."
    )
    availability_status: AvailabilityStatus = Field(
        description="Operational resort availability shown in recommendation output."
    )
    conditions_score: float = Field(
        ge=0,
        le=1,
        description="Normalized conditions contribution used in ranking.",
    )
    conditions_provenance: ProvenanceInfo = Field(
        description="Provenance metadata for the conditions signal."
    )
    explanation: SearchExplanation = Field(
        description=(
            "Compact grouped explanation for why this resort ranked as recommended."
        )
    )
    recommendation_narrative: str | None = Field(
        default=None,
        description=(
            "Optional grounded narrative summary generated for the top-ranked result."
        ),
    )
    recommendation_confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Confidence in the recommendation based on fit and conditions inputs."
        ),
    )
    planning_summary: str | None = Field(
        default=None,
        description=(
            "Optional month-aware planning summary for the selected travel window."
        ),
    )
    planning_provenance: ProvenanceInfo | None = Field(
        default=None,
        description="Optional provenance metadata for the planning signal.",
    )
    planning_evidence_count: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Number of stored monthly snapshots supporting the planning signal."
        ),
    )
    best_travel_months: list[int] = Field(
        default_factory=list,
        description=(
            "Best-fit months for this resort based on deterministic planning logic."
        ),
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


class ParseQueryDebugInfo(BaseModel):
    parser_source: ParserSource
    fallback_reason: ParserFallbackReason | None = None
    llm_confidence: float | None = Field(default=None, ge=0, le=1)
    cache_hit: bool
    model: str | None = None
    raw_response_preview: str | None = None


class DebugParsedQueryResponse(ParsedQueryResponse):
    debug: ParseQueryDebugInfo


class SearchDebugInfo(BaseModel):
    narrative_source: NarrativeSource
    narrative_cache_hit: bool
    narrative_error: NarrativeError | None = None
    narrative_model: str | None = None
    top_result_resort_id: str | None = None


class DebugSearchResponse(BaseModel):
    results: list[SearchResult]
    debug: SearchDebugInfo
