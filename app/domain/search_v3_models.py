from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.catalog import SkiAreaAccessMode
from app.domain.models import (
    LiftDistance,
    LiftPassValidityScope,
    PlanningEvidenceProfile,
    ProvenanceInfo,
    SearchExplanation,
    TravelEffort,
    WeatherEvidenceMetrics,
)


class _SearchV3Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AccessSummary(_SearchV3Model):
    ski_area_access_id: str
    mode: SkiAreaAccessMode
    lift_distance: LiftDistance
    nearest_lift_name: str | None = None
    distance_m: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, ge=0)
    is_direct: bool


class PassPriceExample(_SearchV3Model):
    duration_days: int = Field(ge=1)
    audience: str
    amount: float | None = Field(default=None, ge=0)
    amount_min: float | None = Field(default=None, ge=0)
    amount_max: float | None = Field(default=None, ge=0)
    currency: str = Field(min_length=3, max_length=3)
    match_kind: Literal["exact_duration", "representative", "unavailable"]


class PassOption(_SearchV3Model):
    lift_pass_product_id: str
    name: str
    validity_scope: LiftPassValidityScope
    accessible_ski_area_ids: list[str]
    accessible_terrain_label: str
    accessible_piste_km: float | None = Field(default=None, ge=0)
    price_example: PassPriceExample | None = None
    pass_fit_score: float = Field(ge=0, le=1)
    tradeoff_summary: str


class AreaResilienceItem(_SearchV3Model):
    ski_area_id: str
    ski_area_name: str
    evidence_profile: PlanningEvidenceProfile | None = None
    evidence_seasons: int | None = Field(default=None, ge=0)
    conditions_summary: str | None = None


class ResilienceSummary(_SearchV3Model):
    alternative_area_count: int = Field(ge=0)
    evidenced_alternative_count: int = Field(ge=0)
    areas: list[AreaResilienceItem]
    summary: str
    ranking_component: Literal[0] = 0


class TripConfiguration(_SearchV3Model):
    configuration_id: str
    ski_region_id: str
    stay_destination_id: str
    stay_destination_name: str
    stay_base_id: str
    stay_base_name: str
    focus_ski_area_id: str
    focus_ski_area_name: str
    access: AccessSummary
    selected_pass: PassOption
    alternative_passes: list[PassOption]
    resilience: ResilienceSummary
    score: float
    score_components: dict[str, float]
    budget_penalty: float
    travel_effort: TravelEffort | None = None
    conditions_summary: str
    snow_confidence_score: float = Field(ge=0, le=1)
    conditions_score: float = Field(ge=0, le=1)
    planning_summary: str | None = None
    planning_provenance: ProvenanceInfo | None = None
    planning_evidence_count: int | None = Field(default=None, ge=0)
    planning_weather_metrics: WeatherEvidenceMetrics | None = None
    evidence_quality: ProvenanceInfo
    explanation: SearchExplanation


class RecommendationGroup(_SearchV3Model):
    ski_region_id: str
    ski_region_name: str
    rank: int = Field(ge=1)
    score: float
    top_configuration: TripConfiguration
    alternative_configurations: list[TripConfiguration]

    @model_validator(mode="after")
    def validate_group_invariants(self) -> "RecommendationGroup":
        if self.score != self.top_configuration.score:
            raise ValueError("group score must equal top configuration score")
        configurations = (
            self.top_configuration,
            *self.alternative_configurations,
        )
        if any(item.ski_region_id != self.ski_region_id for item in configurations):
            raise ValueError(
                f"all configurations must belong to ski region {self.ski_region_id}"
            )
        configuration_ids = [item.configuration_id for item in configurations]
        if len(configuration_ids) != len(set(configuration_ids)):
            raise ValueError("configuration IDs must be unique within a group")
        return self


class SearchV3Response(_SearchV3Model):
    results: list[RecommendationGroup]
