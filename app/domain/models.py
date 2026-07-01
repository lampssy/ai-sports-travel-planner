from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.source_urls import validate_direct_external_http_url

SkillLevel = Literal["beginner", "intermediate", "advanced"]
PriceLevel = Literal["low", "medium", "high"]
Quality = Literal["budget", "standard", "premium"]
LiftDistance = Literal["near", "medium", "far"]
StayBaseAccessMode = Literal["walk", "ski_bus", "car_recommended", "unknown"]
BudgetMode = Literal["lodging_nightly", "total_trip"]
PriceKind = Literal["fixed", "from", "range", "unknown"]
LiftPassValidityScope = Literal[
    "single_ski_area",
    "local_multi_area",
    "regional_network",
]
TerrainMetricScope = Literal["aggregate"]
SnowConfidenceLabel = Literal["poor", "fair", "good"]
AvailabilityStatus = Literal["open", "limited", "temporarily_closed", "out_of_season"]
ExplanationDirection = Literal["positive", "negative"]
SourceType = Literal["forecast", "reported", "estimated"]
FreshnessStatus = Literal["fresh", "stale", "historical", "unknown"]
WeatherRecordType = Literal["forecast", "archive"]
WeatherElevationBand = Literal["base", "mid", "upper"]
SnowClimatologyBaselinePeriod = Literal["normal_30y", "recent_15y"]
PlanningEvidenceProfile = Literal[
    "forecast_assisted",
    "archive_backed",
    "fallback_heavy",
]
BookingStatus = Literal[
    "not_booked_yet",
    "booked_through_app",
    "booked_elsewhere",
]
AuthProvider = Literal["google"]
ComparisonBasisKind = Literal["since_last_check", "since_trip_saved"]
CurrentTripDeltaStatus = Literal["changed", "unchanged", "insufficient_history"]
TripWindowStatus = Literal["unscheduled", "upcoming", "active", "past"]
NotificationPlatform = Literal["ios", "android"]
CompanionEventType = Literal["conditions_change"]
SeasonWindowStatus = Literal["planned", "estimated"]
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
TravelMode = Literal["car"]
TravelTolerance = Literal["short", "medium", "flexible"]
TravelEffortLabel = Literal["easy", "moderate", "long", "very_long"]
TravelRouteProvenance = Literal["provider_backed", "estimated_fallback"]
SearchModelVersion = Literal["search_v1", "search_v2"]


def snow_confidence_label_for_score(score: float) -> SnowConfidenceLabel:
    if score < 0.35:
        return "poor"
    if score < 0.7:
        return "fair"
    return "good"


def _non_blank(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _validate_non_blank_values(values: list[str], field_name: str) -> list[str]:
    return [_non_blank(value, field_name) for value in values]


class StayBase(BaseModel):
    stay_base_id: str = Field(description="Stable stay-base identifier.")
    name: str = Field(
        description="Accommodation town or stay zone used in recommendation output."
    )
    price_range: str = Field(
        description="Human-readable accommodation price range for the stay base."
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
        description="Skill levels that the stay base meaningfully supports."
    )
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    nearest_lift_name: str | None = None
    nearest_lift_distance_m: int | None = Field(default=None, ge=0)
    access_mode: StayBaseAccessMode = "unknown"
    base_type: str | None = None
    atmosphere_tags: list[str] = Field(default_factory=list)
    regional_data_ids: dict[str, str] = Field(default_factory=dict)

    @field_validator("stay_base_id")
    @classmethod
    def validate_stay_base_id(cls, value: str) -> str:
        return _non_blank(value, "stay_base_id")


class SeasonWindow(BaseModel):
    season_label: str | None = Field(
        default=None,
        description="Human-readable season label, for example 2025-2026.",
    )
    start_date: date = Field(description="Exact planned or reported season start date.")
    end_date: date = Field(description="Exact planned or reported season end date.")
    status: SeasonWindowStatus = Field(
        default="planned",
        description="Whether this exact season window is planned or estimated.",
    )

    @model_validator(mode="after")
    def validate_date_order(self) -> "SeasonWindow":
        if self.end_date < self.start_date:
            raise ValueError("season window end_date must be on or after start_date")
        return self


class PisteKmByDifficulty(BaseModel):
    beginner: float = Field(
        ge=0,
        description="Kilometers of beginner-friendly pistes.",
    )
    intermediate: float = Field(
        ge=0,
        description="Kilometers of intermediate pistes.",
    )
    advanced: float = Field(
        ge=0,
        description="Kilometers of advanced pistes.",
    )


class LiftPassPrice(BaseModel):
    duration_days: int = Field(
        ge=1,
        description="Lift-pass duration in calendar days.",
    )
    audience: str = Field(
        min_length=1,
        description="Normalized audience label, for example adult.",
    )
    amount: float | None = Field(
        default=None,
        ge=0,
        description="Single price amount when the price is fixed or from.",
    )
    amount_min: float | None = Field(
        default=None,
        ge=0,
        description="Lower bound when the price is a range.",
    )
    amount_max: float | None = Field(
        default=None,
        ge=0,
        description="Upper bound when the price is a range.",
    )
    currency: str = Field(
        min_length=3,
        max_length=3,
        description="ISO currency code.",
    )
    price_kind: PriceKind = Field(
        description="Whether the price is exact, a from-price, a range, or unknown."
    )
    season_label: str | None = Field(
        default=None,
        description="Human-readable season label for this price.",
    )
    source_url: str | None = Field(
        default=None,
        description="Source URL used when the price was reviewed into the catalog.",
    )

    @model_validator(mode="after")
    def validate_amount_shape(self) -> "LiftPassPrice":
        if self.price_kind == "range":
            if self.amount is not None:
                raise ValueError("range prices cannot include amount")
            if self.amount_min is None or self.amount_max is None:
                raise ValueError("range prices require amount_min and amount_max")
            if self.amount_min > self.amount_max:
                raise ValueError("amount_min cannot exceed amount_max")
            return self

        if self.price_kind in {"fixed", "from"}:
            if self.amount is None:
                raise ValueError("fixed and from prices require amount")
            if self.amount_min is not None or self.amount_max is not None:
                raise ValueError("fixed and from prices cannot include range amounts")
            return self

        if (
            self.amount is not None
            or self.amount_min is not None
            or self.amount_max is not None
        ):
            raise ValueError("unknown prices cannot include amount values")
        return self


class LiftPassProduct(BaseModel):
    lift_pass_product_id: str = Field(description="Stable lift-pass product id.")
    name: str = Field(description="Display name of the pass product.")
    validity_scope: LiftPassValidityScope = Field(
        description=(
            "Whether the pass is valid for one modeled ski area, spans multiple "
            "modeled local ski areas, or belongs to a broader regional network."
        )
    )
    is_default: bool = Field(
        default=False,
        description=(
            "Whether this is the representative default adult/default product "
            "for planning and display when multiple pass products are available."
        ),
    )
    valid_ski_area_ids: list[str] = Field(
        default_factory=list,
        description="Modeled local ski areas covered by this pass product.",
    )
    terrain_domain_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Shared terrain-domain ids covered by this pass product when the "
            "pass spans ski areas modeled under multiple destinations."
        ),
    )
    external_validity_summary: str | None = Field(
        default=None,
        description=(
            "Human-readable summary of covered external regions when the pass "
            "extends beyond modeled local ski areas."
        ),
    )
    prices: list[LiftPassPrice] = Field(
        default_factory=list,
        description="Reviewed adult/default price examples for this pass product.",
    )

    @field_validator("lift_pass_product_id")
    @classmethod
    def validate_lift_pass_product_id(cls, value: str) -> str:
        return _non_blank(value, "lift_pass_product_id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _non_blank(value, "name")

    @field_validator("valid_ski_area_ids")
    @classmethod
    def validate_valid_ski_area_ids(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_values(values, "valid_ski_area_ids")

    @field_validator("terrain_domain_ids")
    @classmethod
    def validate_terrain_domain_ids(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_values(values, "terrain_domain_ids")

    @field_validator("external_validity_summary")
    @classmethod
    def validate_external_validity_summary(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _non_blank(value, "external_validity_summary")

    @model_validator(mode="after")
    def validate_scope_shape(self) -> "LiftPassProduct":
        if (
            self.validity_scope == "single_ski_area"
            and len(self.valid_ski_area_ids) != 1
        ):
            raise ValueError(
                "single_ski_area pass products require exactly one valid_ski_area_id"
            )
        if (
            self.validity_scope == "local_multi_area"
            and len(self.valid_ski_area_ids) < 2
        ):
            raise ValueError(
                "local_multi_area pass products require at least two valid_ski_area_ids"
            )
        if self.validity_scope == "regional_network" and not self.valid_ski_area_ids:
            raise ValueError(
                "regional_network pass products require valid_ski_area_ids"
            )
        if self.validity_scope == "regional_network" and not (
            self.external_validity_summary
        ):
            raise ValueError(
                "regional_network pass products require external_validity_summary"
            )
        return self


class SkiArea(BaseModel):
    ski_area_id: str = Field(
        description=(
            "Stable identifier for the smallest durable local terrain unit that "
            "owns weather and operations evidence; it may connect by lift or piste "
            "to other ski areas."
        )
    )
    name: str = Field(description="Display name of the ski-area weather entity.")
    latitude: float = Field(description="Latitude used for ski-area weather lookups.")
    longitude: float = Field(description="Longitude used for ski-area weather lookups.")
    base_elevation_m: int = Field(
        description="Approximate lowest skiable or lift-served elevation."
    )
    summit_elevation_m: int = Field(
        description="Approximate highest skiable or lift-served elevation."
    )
    season_start_month: int = Field(
        ge=1,
        le=12,
        description="Typical start month of the ski-area season.",
    )
    season_end_month: int = Field(
        ge=1,
        le=12,
        description="Typical end month of the ski-area season.",
    )
    season_windows: list[SeasonWindow] = Field(
        default_factory=list,
        description=(
            "Exact season-specific operating windows when known; month fields "
            "remain the fallback for years without exact windows."
        ),
    )
    total_piste_km: float | None = Field(
        default=None,
        ge=0,
        description="Total skiable piste kilometers for this ski area.",
    )
    total_lift_count: int | None = Field(
        default=None,
        ge=0,
        description="Total lift count for this ski area.",
    )
    piste_km_by_difficulty: PisteKmByDifficulty | None = Field(
        default=None,
        description="Piste kilometers split into beginner/intermediate/advanced.",
    )


class TerrainGroup(BaseModel):
    terrain_group_id: str = Field(
        description="Stable id for a destination-local aggregate terrain group."
    )
    name: str = Field(
        description="Display name of the destination-local aggregate terrain group."
    )
    ski_area_ids: list[str] = Field(
        min_length=1,
        description=(
            "Modeled ski areas under the same destination covered by this aggregate "
            "terrain fact."
        ),
    )
    metric_scope: TerrainMetricScope = Field(
        default="aggregate",
        description="Scope marker; aggregate facts must not be copied to child areas.",
    )
    total_piste_km: float | None = Field(
        default=None,
        ge=0,
        description="Aggregate piste kilometers for the linked ski areas.",
    )
    total_lift_count: int | None = Field(
        default=None,
        ge=0,
        description="Aggregate lift count for the linked ski areas.",
    )
    piste_km_by_difficulty: PisteKmByDifficulty | None = Field(
        default=None,
        description="Aggregate piste kilometers by difficulty.",
    )
    source_urls: list[str] = Field(
        default_factory=list,
        description="Reviewed source URLs supporting aggregate terrain-group facts.",
    )

    @field_validator("terrain_group_id")
    @classmethod
    def validate_terrain_group_id(cls, value: str) -> str:
        return _non_blank(value, "terrain_group_id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _non_blank(value, "name")

    @field_validator("ski_area_ids")
    @classmethod
    def validate_ski_area_ids(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_values(values, "ski_area_ids")

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(cls, values: list[str]) -> list[str]:
        return _validate_non_blank_values(values, "source_urls")


class TerrainDomainSkiAreaRef(BaseModel):
    resort_id: str = Field(
        description="Destination id that owns the referenced ski-area entity."
    )
    ski_area_id: str = Field(description="Referenced ski-area id.")

    @field_validator("resort_id")
    @classmethod
    def validate_resort_id(cls, value: str) -> str:
        return _non_blank(value, "resort_id")

    @field_validator("ski_area_id")
    @classmethod
    def validate_ski_area_id(cls, value: str) -> str:
        return _non_blank(value, "ski_area_id")


class TerrainDomain(BaseModel):
    """Ski-connected aggregate spanning at least two modeled destinations."""

    terrain_domain_id: str = Field(
        description=(
            "Stable id for a ski-connected cross-destination terrain aggregate; "
            "shared ticket validity alone is insufficient."
        )
    )
    name: str = Field(description="Display name of the shared terrain domain.")
    ski_area_refs: list[TerrainDomainSkiAreaRef] = Field(
        min_length=2,
        description=(
            "Ski-connected members with their owning destination ids; at least two "
            "distinct destinations are required."
        ),
    )
    metric_scope: TerrainMetricScope = Field(
        default="aggregate",
        description="Scope marker; aggregate facts must not be copied to children.",
    )
    total_piste_km: float | None = Field(
        default=None,
        ge=0,
        description="Aggregate piste kilometers for the shared domain.",
    )
    total_lift_count: int | None = Field(
        default=None,
        ge=0,
        description="Aggregate lift count for the shared domain.",
    )
    base_elevation_m: int | None = Field(
        default=None,
        ge=0,
        description="Lowest lift-served or skiable elevation for the shared domain.",
    )
    summit_elevation_m: int | None = Field(
        default=None,
        ge=0,
        description="Highest lift-served or skiable elevation for the shared domain.",
    )
    piste_km_by_difficulty: PisteKmByDifficulty | None = Field(
        default=None,
        description="Aggregate piste kilometers by difficulty for the shared domain.",
    )
    season_windows: list[SeasonWindow] = Field(
        default_factory=list,
        description="Exact operating windows when only shared-domain dates are known.",
    )
    source_urls: list[str] = Field(
        min_length=1,
        description=(
            "Direct HTTP(S) provenance supporting domain membership and every "
            "populated aggregate fact."
        ),
    )

    @field_validator("terrain_domain_id")
    @classmethod
    def validate_terrain_domain_id(cls, value: str) -> str:
        return _non_blank(value, "terrain_domain_id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _non_blank(value, "name")

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for index, source_url in enumerate(values):
            try:
                normalized.append(validate_direct_external_http_url(source_url))
            except ValueError as error:
                raise ValueError(f"source_urls[{index}] {error}") from error
        return normalized

    @model_validator(mode="after")
    def validate_domain_shape(self) -> "TerrainDomain":
        resort_ids = {ref.resort_id for ref in self.ski_area_refs}
        if len(resort_ids) < 2:
            raise ValueError(
                "terrain domains require ski areas from at least two distinct "
                "destinations"
            )
        if (self.base_elevation_m is None) != (self.summit_elevation_m is None):
            raise ValueError(
                "terrain domains require both base_elevation_m and "
                "summit_elevation_m when either is set"
            )
        if (
            self.base_elevation_m is not None
            and self.summit_elevation_m is not None
            and self.summit_elevation_m <= self.base_elevation_m
        ):
            raise ValueError("terrain domain summit elevation must be above base")
        return self


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


class Destination(BaseModel):
    resort_id: str = Field(
        description=(
            "Stable trip-planning destination identity used for recommendation, "
            "stay selection, frontend keys, and linking; transitionally kept as "
            "resort_id in public contracts."
        )
    )
    name: str = Field(description="Destination display name.")
    country: str = Field(description="Country used for destination filtering.")
    region: str = Field(description="Geographic region grouping for the destination.")
    price_level: PriceLevel
    latitude: float = Field(
        description=(
            "Destination center latitude for display and coarse geography; ski-area "
            "coordinates own weather lookups."
        )
    )
    longitude: float = Field(
        description=(
            "Destination center longitude for display and coarse geography; ski-area "
            "coordinates own weather lookups."
        )
    )
    base_elevation_m: int = Field(
        description=(
            "Approximate destination-level base elevation, kept for compatibility "
            "and coarse metadata display."
        )
    )
    summit_elevation_m: int = Field(
        description=(
            "Approximate destination-level summit elevation, kept for compatibility "
            "and coarse metadata display."
        )
    )
    season_start_month: int = Field(
        ge=1,
        le=12,
        description=(
            "Typical start month of the destination season, kept for compatibility."
        ),
    )
    season_end_month: int = Field(
        ge=1,
        le=12,
        description=(
            "Typical end month of the destination season, kept for compatibility."
        ),
    )
    season_windows: list[SeasonWindow] = Field(
        default_factory=list,
        description=(
            "Exact destination season windows when known; usually mirrored from "
            "the only ski area for single-area destinations."
        ),
    )
    lift_pass_products: list[LiftPassProduct] = Field(
        default_factory=list,
        description=(
            "Reviewed pass products with explicit local and regional validity scope."
        ),
    )
    stay_bases: list[StayBase]
    ski_areas: list[SkiArea]
    terrain_groups: list[TerrainGroup] = Field(
        default_factory=list,
        description=(
            "Destination-local aggregate terrain facts for multiple modeled ski "
            "areas; child ski-area fields remain single-area facts."
        ),
    )
    rentals: list[Rental]

    @model_validator(mode="after")
    def validate_scoped_references(self) -> "Destination":
        ski_area_ids = {ski_area.ski_area_id for ski_area in self.ski_areas}
        lift_pass_product_ids: set[str] = set()
        default_lift_pass_product_ids: list[str] = []
        for product in self.lift_pass_products:
            if product.lift_pass_product_id in lift_pass_product_ids:
                raise ValueError(
                    f"{self.resort_id}: duplicate lift-pass product id "
                    f"{product.lift_pass_product_id}"
                )
            lift_pass_product_ids.add(product.lift_pass_product_id)
            unknown_ids = sorted(set(product.valid_ski_area_ids) - ski_area_ids)
            if unknown_ids:
                joined = ", ".join(unknown_ids)
                raise ValueError(
                    f"{self.resort_id}/{product.lift_pass_product_id}: "
                    f"lift pass product references unknown ski_area_id: {joined}"
                )
            if product.is_default:
                default_lift_pass_product_ids.append(product.lift_pass_product_id)
        if len(default_lift_pass_product_ids) > 1:
            joined = ", ".join(default_lift_pass_product_ids)
            raise ValueError(
                f"{self.resort_id}: multiple default lift-pass products: {joined}"
            )
        terrain_group_ids: set[str] = set()
        for terrain_group in self.terrain_groups:
            if terrain_group.terrain_group_id in terrain_group_ids:
                raise ValueError(
                    f"{self.resort_id}: duplicate terrain group id "
                    f"{terrain_group.terrain_group_id}"
                )
            terrain_group_ids.add(terrain_group.terrain_group_id)
            unknown_ids = sorted(set(terrain_group.ski_area_ids) - ski_area_ids)
            if unknown_ids:
                joined = ", ".join(unknown_ids)
                raise ValueError(
                    f"{self.resort_id}/{terrain_group.terrain_group_id}: "
                    f"terrain group references unknown ski_area_id: {joined}"
                )
        return self


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
        description=(
            "Conditions/disruption signal used in ranking. The current provider "
            "derives this from weather and seasonality, not official lift status."
        )
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
    ski_area_id: str = Field(description="Stable ski-area identifier for the snapshot.")
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
        description="Conditions/disruption status captured for this snapshot."
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


class RawWeatherObservation(BaseModel):
    ski_area_id: str = Field(description="Stable ski-area identifier for this record.")
    resort_name: str = Field(description="Ski-area name captured for this record.")
    elevation_band: WeatherElevationBand = Field(
        default="mid",
        description=(
            "Weather sampling band. Default planning metrics use mid-mountain rows."
        ),
    )
    elevation_m: int | None = Field(
        default=None,
        description="Requested Open-Meteo elevation in meters for this observation.",
    )
    observed_on: str = Field(
        description="ISO date representing the daily historical weather record."
    )
    observed_at: str = Field(
        description="Timestamp associated with the underlying provider observation."
    )
    snowfall_cm: float = Field(
        ge=0,
        description="Daily snowfall amount in centimeters.",
    )
    snow_depth_m: float | None = Field(
        default=None,
        ge=0,
        description="Average snow depth on the ground in meters, when available.",
    )
    precipitation_sum_mm: float | None = Field(
        default=None,
        ge=0,
        description="Total daily precipitation water equivalent in millimeters.",
    )
    rain_sum_mm: float | None = Field(
        default=None,
        ge=0,
        description="Total daily liquid rain in millimeters.",
    )
    precipitation_hours: float | None = Field(
        default=None,
        ge=0,
        description="Daily hours with precipitation.",
    )
    snowfall_water_equivalent_sum_mm: float | None = Field(
        default=None,
        ge=0,
        description="Daily snowfall water equivalent in millimeters.",
    )
    temperature_2m_max_c: float = Field(
        description="Maximum daily air temperature at 2m in Celsius."
    )
    temperature_2m_min_c: float = Field(
        description="Minimum daily air temperature at 2m in Celsius."
    )
    apparent_temperature_2m_max_c: float | None = Field(
        default=None,
        description="Maximum daily apparent temperature at 2m in Celsius.",
    )
    apparent_temperature_2m_min_c: float | None = Field(
        default=None,
        description="Minimum daily apparent temperature at 2m in Celsius.",
    )
    cloud_cover_mean_pct: float | None = Field(
        default=None,
        ge=0,
        description="Mean daily cloud cover percentage.",
    )
    sunshine_duration_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Daily sunshine duration in seconds.",
    )
    visibility_min_m: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Minimum forecast visibility in meters for the observation date, when "
            "available."
        ),
    )
    wind_speed_10m_max_kmh: float = Field(
        ge=0,
        description="Maximum daily wind speed at 10m in km/h.",
    )
    wind_gusts_10m_max_kmh: float = Field(
        ge=0,
        description="Maximum daily wind gusts at 10m in km/h.",
    )
    weather_code: int = Field(
        description="Daily weather-code signal associated with the observation."
    )
    record_type: WeatherRecordType = Field(
        description=(
            "Whether the row came from live forecast refresh or archive backfill."
        )
    )
    source: str | None = Field(
        default=None,
        description="Origin of the record, for example open-meteo.",
    )
    source_model: str | None = Field(
        default=None,
        description="Underlying provider model label when available.",
    )


class SnowClimatologyDaily(BaseModel):
    ski_area_id: str = Field(description="Stable ski-area identifier.")
    resort_name: str = Field(description="Ski-area name captured for this row.")
    elevation_band: WeatherElevationBand = Field(
        description="Weather sampling band represented by this climatology row."
    )
    elevation_m: int | None = Field(
        default=None,
        description="Representative requested elevation in meters for the band.",
    )
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)
    baseline_period: SnowClimatologyBaselinePeriod
    baseline_start_year: int
    baseline_end_year: int
    evidence_seasons: int = Field(ge=0)
    latest_archive_year: int | None = None
    snow_depth_cm_p25: float | None = Field(default=None, ge=0)
    snow_depth_cm_p50: float | None = Field(default=None, ge=0)
    snow_depth_cm_p75: float | None = Field(default=None, ge=0)
    prob_snow_depth_ge_30cm: float = Field(ge=0, le=1)
    prob_snow_depth_ge_50cm: float = Field(ge=0, le=1)
    avg_daily_snowfall_cm: float = Field(ge=0)
    prob_rain_risk: float = Field(ge=0, le=1)
    prob_freeze_thaw: float = Field(ge=0, le=1)
    avg_max_temperature_c: float
    avg_wind_gust_kmh: float = Field(ge=0)
    avg_snow_confidence_score: float = Field(ge=0, le=1)
    avg_conditions_score: float = Field(ge=0, le=1)
    source_model: str = Field(
        default="snowcast_empirical_v1",
        description="Version label for the derived climatology algorithm.",
    )
    computed_at: str = Field(
        description="ISO timestamp when this climatology row was computed."
    )

    @model_validator(mode="after")
    def validate_baseline_years(self) -> "SnowClimatologyDaily":
        if self.baseline_end_year < self.baseline_start_year:
            raise ValueError("baseline_end_year must be >= baseline_start_year")
        return self


class WeatherEvidenceMetrics(BaseModel):
    average_snow_depth_cm: float | None = Field(
        default=None,
        ge=0,
        description="Average historical snow depth in centimeters when available.",
    )
    average_daily_snowfall_cm: float = Field(
        ge=0,
        description=(
            "Average daily snowfall in centimeters across matched archive rows."
        ),
    )
    average_max_temperature_c: float = Field(
        description="Average daily maximum temperature in Celsius."
    )
    average_wind_gust_kmh: float = Field(
        ge=0,
        description="Average daily maximum wind gust in km/h.",
    )
    evidence_years: int = Field(
        ge=1,
        description="Number of distinct archive years represented in the metrics.",
    )
    latest_observed_on: str = Field(
        description="Latest archive observation date included in the metrics."
    )
    elevation_band: WeatherElevationBand = Field(
        default="mid",
        description="Elevation band used to calculate the display metrics.",
    )
    elevation_m: int | None = Field(
        default=None,
        description="Representative requested elevation for the metric rows.",
    )


class SearchFilters(BaseModel):
    location: str = Field(description="Country filter used for resort search.")
    min_price: float = Field(
        description="Preferred minimum nightly stay-base budget estimate in EUR."
    )
    max_price: float = Field(
        description="Preferred maximum nightly stay-base budget estimate in EUR."
    )
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
    trip_start_date: date | None = Field(
        default=None,
        description="Optional exact trip start date used for date-aware planning.",
    )
    trip_end_date: date | None = Field(
        default=None,
        description="Optional exact trip end date used for date-aware planning.",
    )
    origin_text: str | None = Field(default=None)
    max_drive_minutes: int | None = Field(default=None, ge=1)
    travel_tolerance: TravelTolerance | None = Field(default=None)

    @model_validator(mode="after")
    def validate_trip_window(self) -> "SearchFilters":
        if (self.trip_start_date is None) != (self.trip_end_date is None):
            raise ValueError(
                "trip_start_date and trip_end_date must be provided together"
            )
        if (
            self.trip_start_date is not None
            and self.trip_end_date is not None
            and self.trip_end_date < self.trip_start_date
        ):
            raise ValueError("trip_end_date must be on or after trip_start_date")
        return self


class CurrentTrip(BaseModel):
    resort_id: str = Field(description="Stable resort identifier for the saved trip.")
    resort_name: str = Field(description="Display name of the saved resort.")
    selected_ski_area_id: str = Field(
        description="Stable ski-area identifier carried into the saved trip context."
    )
    selected_ski_area_name: str = Field(
        description="Selected ski area carried into the saved trip context."
    )
    selected_stay_base_name: str = Field(
        description="Selected stay base carried into the saved trip context."
    )
    selected_area_name: str = Field(
        description="Deprecated alias for selected_stay_base_name."
    )
    travel_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Optional saved travel month for the current trip.",
    )
    trip_start_date: date | None = Field(
        default=None,
        description="Optional exact saved trip start date for companion features.",
    )
    trip_end_date: date | None = Field(
        default=None,
        description="Optional exact saved trip end date for companion features.",
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

    @model_validator(mode="after")
    def validate_trip_window(self) -> "CurrentTrip":
        if (self.trip_start_date is None) != (self.trip_end_date is None):
            raise ValueError(
                "trip_start_date and trip_end_date must be provided together"
            )
        if (
            self.trip_start_date is not None
            and self.trip_end_date is not None
            and self.trip_end_date < self.trip_start_date
        ):
            raise ValueError("trip_end_date must be on or after trip_start_date")
        return self


class UpsertCurrentTripRequest(BaseModel):
    resort_id: str = Field(description="Selected resort identifier for the trip.")
    selected_ski_area_id: str | None = Field(
        default=None,
        description="Selected ski-area identifier for the trip context.",
    )
    selected_ski_area_name: str | None = Field(
        default=None,
        description="Selected ski-area name for the trip context.",
    )
    selected_stay_base_name: str | None = Field(
        default=None,
        description="Selected stay-base name for the trip context.",
    )
    selected_area_name: str | None = Field(
        default=None,
        description="Deprecated alias for selected_stay_base_name.",
    )
    travel_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Optional travel month for the trip context.",
    )
    trip_start_date: date | None = Field(
        default=None,
        description="Optional exact trip start date for the trip context.",
    )
    trip_end_date: date | None = Field(
        default=None,
        description="Optional exact trip end date for the trip context.",
    )
    booking_status: BookingStatus = Field(
        description="Booking status selected by the user for the trip."
    )

    @model_validator(mode="after")
    def validate_selection_fields(self) -> "UpsertCurrentTripRequest":
        if self.selected_stay_base_name is None and self.selected_area_name is None:
            raise ValueError(
                "selected_stay_base_name or selected_area_name must be provided"
            )
        if self.selected_ski_area_name is None:
            raise ValueError("selected_ski_area_name must be provided")
        if (self.trip_start_date is None) != (self.trip_end_date is None):
            raise ValueError(
                "trip_start_date and trip_end_date must be provided together"
            )
        if (
            self.trip_start_date is not None
            and self.trip_end_date is not None
            and self.trip_end_date < self.trip_start_date
        ):
            raise ValueError("trip_end_date must be on or after trip_start_date")
        return self


class AuthenticatedUser(BaseModel):
    user_id: str = Field(description="Stable backend-owned user identifier.")
    email: str = Field(description="Primary email address for the signed-in user.")
    display_name: str | None = Field(
        default=None,
        description="Display name from the identity provider when available.",
    )
    auth_provider: AuthProvider = Field(
        description="Identity provider currently linked to this user."
    )


class GoogleSignInRequest(BaseModel):
    identity_token: str = Field(
        min_length=1,
        description=(
            "Google-issued ID token returned by the mobile client sign-in flow."
        ),
    )


class AuthSessionResponse(BaseModel):
    access_token: str = Field(description="Backend-issued bearer token.")
    token_type: str = Field(
        default="bearer",
        description="Token type used by authenticated mobile requests.",
    )
    expires_at: str = Field(description="UTC timestamp at which the session expires.")
    user: AuthenticatedUser = Field(
        description="Authenticated backend user attached to this session."
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


class CompanionStatus(BaseModel):
    trip_window_status: TripWindowStatus = Field(
        description="Whether the saved trip is upcoming, active, past, or unscheduled."
    )
    trip_window_label: str = Field(
        description="Human-readable label for the current trip-window state."
    )
    notification_eligible: bool = Field(
        description="Whether this trip is currently eligible for companion alerts."
    )
    eligibility_reason: str = Field(
        description="Short explanation of why notifications are or are not eligible."
    )
    actionable_change_available: bool = Field(
        description="Whether the current summary contains a change worth surfacing."
    )


class RegisteredDevice(BaseModel):
    installation_id: str = Field(
        description="Stable client installation identifier for one signed-in device."
    )
    platform: NotificationPlatform = Field(
        description="Client platform used for later push delivery wiring."
    )
    push_token: str | None = Field(
        default=None,
        description="Optional future push token when real delivery is enabled.",
    )
    push_enabled: bool = Field(
        description="Whether this device should be treated as notification-capable."
    )
    created_at: str = Field(description="Timestamp of the first registration.")
    updated_at: str = Field(description="Timestamp of the latest registration update.")
    last_seen_at: str = Field(description="Timestamp of the latest registration ping.")


class DeviceRegistrationRequest(BaseModel):
    installation_id: str = Field(
        min_length=1,
        description="Stable installation identifier generated by the client.",
    )
    platform: NotificationPlatform = Field(
        description="Client platform registering for later companion delivery."
    )
    push_token: str | None = Field(
        default=None,
        description="Optional future push token for real push delivery.",
    )
    push_enabled: bool = Field(
        default=True,
        description="Whether this device should be treated as notification-capable.",
    )


class CompanionEvent(BaseModel):
    event_id: str = Field(
        description="Stable backend-owned companion event identifier."
    )
    event_type: CompanionEventType = Field(
        description="Type of companion event detected for the saved trip."
    )
    recorded_at: str = Field(description="When the backend recorded the event.")
    actionable: bool = Field(
        description="Whether the event is actionable for the current trip window."
    )
    summary: str = Field(description="Compact event summary shown in client history.")
    changes: list[str] = Field(
        default_factory=list,
        description="Specific condition changes attached to the event.",
    )
    trip_window_status: TripWindowStatus = Field(
        description="Trip-window state when the event was evaluated."
    )
    conditions_updated_at: str | None = Field(
        default=None,
        description="Timestamp of the conditions refresh that triggered the event.",
    )


class CompanionEventsResponse(BaseModel):
    events: list[CompanionEvent] = Field(
        default_factory=list,
        description="Recorded companion events for the current user.",
    )


class CurrentTripSummary(BaseModel):
    trip: CurrentTrip = Field(
        description="Persisted current-trip context for one user."
    )
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
    companion_status: CompanionStatus = Field(
        description="Trip-window and notification-eligibility state for the trip."
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
    evidence_profile: PlanningEvidenceProfile | None = Field(
        default=None,
        description=(
            "Optional planning-specific evidence profile showing whether the "
            "signal is forecast-assisted, archive-backed, or fallback-heavy."
        ),
    )


class TravelEffort(BaseModel):
    origin_label: str
    destination_label: str
    mode: TravelMode = "car"
    distance_km: float = Field(ge=0)
    duration_minutes: int = Field(ge=0)
    effort_label: TravelEffortLabel
    score: float = Field(ge=0, le=1)
    summary: str
    provenance: TravelRouteProvenance
    provider: str
    cache_hit: bool = False
    caveat: str | None = None
    exceeds_max_drive: bool = False


class TripOption(BaseModel):
    option_id: str
    ski_area_id: str
    ski_area_name: str
    stay_base_name: str
    stay_base_lift_distance: LiftDistance
    stay_base_price_range: str
    rental_name: str
    rental_price_range: str
    rating_estimate: int
    score: float
    recommendation_confidence: float = Field(ge=0, le=1)
    budget_penalty: float
    travel_effort: TravelEffort | None = None
    explanation: SearchExplanation
    tradeoff_summary: str


class SearchResult(BaseModel):
    resort_id: str = Field(
        description="Stable resort identifier for UI rendering and future deep links."
    )
    resort_name: str = Field(description="Resort display name.")
    region: str = Field(description="Geographic region of the recommended resort.")
    selected_ski_area_id: str = Field(
        description="Stable ski-area identifier selected for this destination."
    )
    selected_ski_area_name: str = Field(
        description="Best-matching ski area for this destination recommendation."
    )
    selected_stay_base_name: str = Field(
        description="Best-matching stay base for this destination recommendation."
    )
    selected_stay_base_lift_distance: LiftDistance
    stay_base_price_range: str
    selected_area_name: str = Field(
        description="Deprecated alias for selected_stay_base_name."
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
        description=(
            "Conditions/disruption status shown in recommendation output. This is "
            "not official operations status unless provenance is reported."
        )
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
    planning_weather_metrics: WeatherEvidenceMetrics | None = Field(
        default=None,
        description=(
            "Optional archive-weather metrics for the selected planning window."
        ),
    )
    best_travel_months: list[int] = Field(
        default_factory=list,
        description=(
            "Best-fit months for this resort based on deterministic planning logic."
        ),
    )
    travel_effort: TravelEffort | None = Field(default=None)
    top_option: TripOption | None = Field(default=None)
    alternative_options: list[TripOption] = Field(default_factory=list)


# Transitional aliases while the codebase migrates from the old naming.
Area = StayBase
Resort = Destination


class TripContext(BaseModel):
    budget_mode: BudgetMode | None = Field(
        default=None,
        description="Whether detected budget is nightly lodging or total trip budget.",
    )
    budget_min: float | None = Field(
        default=None,
        ge=0,
        description="Detected budget lower bound before search-filter projection.",
    )
    budget_max: float | None = Field(
        default=None,
        ge=0,
        description="Detected budget upper bound before search-filter projection.",
    )
    party_size: int | None = Field(
        default=None,
        ge=1,
        description="Detected number of travelers when present.",
    )
    trip_duration_nights: int | None = Field(
        default=None,
        ge=1,
        description="Detected or derived trip length in nights.",
    )
    origin_text: str | None = Field(
        default=None,
        description="User-provided origin text captured for Sprint 32 travel effort.",
    )


class TripContextPatch(BaseModel):
    budget_mode: BudgetMode | None = None
    party_size: int | None = Field(default=None, ge=1)
    trip_duration_nights: int | None = Field(default=None, ge=1)
    origin_text: str | None = None


class SearchFilterPatch(BaseModel):
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)


class TripClarificationOption(BaseModel):
    id: str
    label: str
    description: str
    context_patch: TripContextPatch = Field(default_factory=TripContextPatch)
    filter_patch: SearchFilterPatch | None = None


class TripClarification(BaseModel):
    id: str
    question: str
    reason: str
    priority: int
    options: list[TripClarificationOption]


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
    trip_context: TripContext = Field(default_factory=TripContext)
    clarifications: list[TripClarification] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class ParseQueryDebugInfo(BaseModel):
    parser_source: ParserSource
    fallback_reason: ParserFallbackReason | None = None
    llm_confidence: float | None = Field(default=None, ge=0, le=1)
    cache_hit: bool
    model: str | None = None
    raw_response_preview: str | None = None
    provider_http_status: int | None = None
    provider_status: str | None = None
    provider_message: str | None = None


class DebugParsedQueryResponse(ParsedQueryResponse):
    debug: ParseQueryDebugInfo


class SearchDebugInfo(BaseModel):
    narrative_source: NarrativeSource
    narrative_cache_hit: bool
    narrative_error: NarrativeError | None = None
    narrative_model: str | None = None
    top_result_resort_id: str | None = None
    configured_search_model: SearchModelVersion = "search_v1"
    requested_search_model: SearchModelVersion | None = None
    effective_search_model: SearchModelVersion = "search_v1"
    search_model_override_applied: bool = False


class DebugSearchResponse(BaseModel):
    results: list[SearchResult]
    debug: SearchDebugInfo
