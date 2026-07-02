export type SkillLevel = "beginner" | "intermediate" | "advanced";
export type LiftDistance = "near" | "medium" | "far";
export type SnowConfidenceLabel = "poor" | "fair" | "good";
export type AvailabilityStatus =
  | "open"
  | "limited"
  | "temporarily_closed"
  | "out_of_season";
export type ExplanationDirection = "positive" | "negative";
export type TravelMonth = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12;
export type SourceType = "forecast" | "reported" | "estimated";
export type FreshnessStatus = "fresh" | "stale" | "historical" | "unknown";
export type WeatherElevationBand = "base" | "mid" | "upper";
export type BookingStatus =
  | "not_booked_yet"
  | "booked_through_app"
  | "booked_elsewhere";
export type ComparisonBasisKind = "since_last_check" | "since_trip_saved";
export type CurrentTripDeltaStatus =
  | "changed"
  | "unchanged"
  | "insufficient_history";
export type TripWindowStatus = "unscheduled" | "upcoming" | "active" | "past";
export type TravelWindowMode = "any" | "month" | "dates";
export type BudgetMode = "lodging_nightly" | "total_trip";
export type TravelTolerance = "" | "short" | "medium" | "flexible";
export type PlanningEvidenceProfile =
  | "forecast_assisted"
  | "archive_backed"
  | "snapshot_fallback"
  | "fallback_heavy";
export type SkiAreaAccessMode =
  | "walk"
  | "ski_bus"
  | "drive"
  | "ski_in_ski_out"
  | "mixed"
  | "unknown";
export type LiftPassValidityScope =
  | "single_ski_area"
  | "multi_ski_area"
  | "regional_network";

export interface SearchFilters {
  location: string;
  minPrice: string;
  maxPrice: string;
  stars: "" | "1" | "2" | "3";
  skillLevel: "" | SkillLevel;
  liftDistance: "" | LiftDistance;
  budgetFlex: string;
  travelWindowMode: TravelWindowMode;
  travelMonth: "" | TravelMonth;
  tripStartDate: string;
  tripEndDate: string;
  originText: string;
  maxDriveHours: string;
  travelTolerance: TravelTolerance;
}

export interface TripContext {
  budget_mode: BudgetMode | null;
  budget_min: number | null;
  budget_max: number | null;
  party_size: number | null;
  trip_duration_nights: number | null;
  origin_text: string | null;
}

export interface TripContextPatch {
  budget_mode?: BudgetMode | null;
  budget_min?: number | null;
  budget_max?: number | null;
  party_size?: number | null;
  trip_duration_nights?: number | null;
  origin_text?: string | null;
}

export interface SearchFilterPatch {
  min_price?: number | null;
  max_price?: number | null;
}

export interface TripClarificationOption {
  id: string;
  label: string;
  description: string;
  context_patch: TripContextPatch;
  filter_patch: SearchFilterPatch | null;
}

export interface TripClarification {
  id: string;
  question: string;
  reason: string;
  priority: number;
  options: TripClarificationOption[];
}

export interface ExplanationItem {
  label: string;
}

export interface ConfidenceContributor {
  label: string;
  direction: ExplanationDirection;
}

export interface SearchExplanation {
  highlights: ExplanationItem[];
  risks: ExplanationItem[];
  confidence_contributors: ConfidenceContributor[];
}

export interface ProvenanceInfo {
  source_name: string | null;
  source_type: SourceType;
  updated_at: string | null;
  freshness_status: FreshnessStatus;
  basis_summary: string;
}

export interface WeatherEvidenceMetrics {
  average_snow_depth_cm: number | null;
  average_daily_snowfall_cm: number;
  average_max_temperature_c: number;
  average_wind_gust_kmh: number;
  evidence_years: number;
  latest_observed_on: string;
  elevation_band: WeatherElevationBand;
  elevation_m: number | null;
}

export interface TravelEffort {
  origin_label: string;
  destination_label: string;
  mode: "car";
  distance_km: number;
  duration_minutes: number;
  effort_label: "easy" | "moderate" | "long" | "very_long";
  score: number;
  summary: string;
  provenance: "provider_backed" | "estimated_fallback";
  provider: string;
  cache_hit: boolean;
  caveat: string | null;
  exceeds_max_drive: boolean;
}

export interface AccessSummary {
  ski_area_access_id: string;
  mode: SkiAreaAccessMode;
  lift_distance: LiftDistance;
  nearest_lift_name: string | null;
  distance_m: number | null;
  duration_minutes: number | null;
  is_direct: boolean;
}

export interface PassPriceExample {
  duration_days: number;
  audience: string;
  amount: number | null;
  amount_min: number | null;
  amount_max: number | null;
  currency: string;
  match_kind: "exact_duration" | "representative" | "unavailable";
}

export interface PassOption {
  lift_pass_product_id: string;
  name: string;
  validity_scope: LiftPassValidityScope;
  accessible_ski_area_ids: string[];
  accessible_terrain_label: string;
  accessible_piste_km: number | null;
  price_example: PassPriceExample | null;
  pass_fit_score: number;
  tradeoff_summary: string;
}

export interface AreaResilienceItem {
  ski_area_id: string;
  ski_area_name: string;
  evidence_profile: PlanningEvidenceProfile | null;
  evidence_seasons: number | null;
  conditions_summary: string | null;
}

export interface ResilienceSummary {
  alternative_area_count: number;
  evidenced_alternative_count: number;
  areas: AreaResilienceItem[];
  summary: string;
  ranking_component: 0;
}

export interface TripConfiguration {
  configuration_id: string;
  ski_region_id: string;
  stay_destination_id: string;
  stay_destination_name: string;
  stay_base_id: string;
  stay_base_name: string;
  focus_ski_area_id: string;
  focus_ski_area_name: string;
  access: AccessSummary;
  selected_pass: PassOption;
  alternative_passes: PassOption[];
  resilience: ResilienceSummary;
  score: number;
  score_components: Record<string, number>;
  budget_penalty: number;
  travel_effort: TravelEffort | null;
  conditions_summary: string;
  snow_confidence_score: number;
  conditions_score: number;
  planning_summary: string | null;
  planning_provenance: ProvenanceInfo | null;
  planning_evidence_count: number | null;
  planning_weather_metrics: WeatherEvidenceMetrics | null;
  evidence_quality: ProvenanceInfo;
  explanation: SearchExplanation;
}

export interface RecommendationGroup {
  ski_region_id: string;
  ski_region_name: string;
  rank: number;
  score: number;
  top_configuration: TripConfiguration;
  alternative_configurations: TripConfiguration[];
}

export interface SearchResponse {
  results: RecommendationGroup[];
}

export interface ParsedQueryResponse {
  filters: Partial<{
    location: string;
    min_price: number;
    max_price: number;
    stars: number;
    skill_level: SkillLevel;
    lift_distance: LiftDistance;
    budget_flex: number;
    travel_month: TravelMonth;
    trip_start_date: string;
    trip_end_date: string;
  }>;
  confidence: number;
  unknown_parts: string[];
  trip_context?: TripContext;
  clarifications?: TripClarification[];
  assumptions?: string[];
}

export interface CurrentTrip {
  ski_region_id: string;
  ski_region_name: string;
  stay_destination_id: string;
  stay_destination_name: string;
  stay_base_id: string;
  stay_base_name: string;
  focus_ski_area_id: string;
  focus_ski_area_name: string;
  lift_pass_product_id: string;
  lift_pass_product_name: string;
  travel_month: TravelMonth | null;
  trip_start_date?: string | null;
  trip_end_date?: string | null;
  booking_status: BookingStatus;
  created_at: string;
  updated_at: string;
  last_checked_at: string | null;
}

export interface CurrentTripResponse {
  trip: CurrentTrip | null;
}

export interface CurrentTripComparisonBasis {
  kind: ComparisonBasisKind;
  baseline_at: string;
  label: string;
}

export interface CurrentTripDelta {
  status: CurrentTripDeltaStatus;
  summary: string;
  changes: string[];
}

export interface CompanionStatus {
  trip_window_status: TripWindowStatus;
  trip_window_label: string;
  notification_eligible: boolean;
  eligibility_reason: string;
  actionable_change_available: boolean;
}

export interface CompanionEvent {
  event_id: string;
  event_type: "conditions_change";
  recorded_at: string;
  actionable: boolean;
  summary: string;
  changes: string[];
  trip_window_status: TripWindowStatus;
  conditions_updated_at: string | null;
}

export interface CurrentTripSummary {
  trip: CurrentTrip;
  current_conditions: {
    resort_name: string;
    snow_confidence_score: number;
    snow_confidence_label: SnowConfidenceLabel;
    availability_status: AvailabilityStatus;
    weather_summary: string;
    conditions_score: number;
    updated_at: string | null;
    source: string | null;
  };
  current_conditions_provenance: ProvenanceInfo;
  comparison_basis: CurrentTripComparisonBasis;
  delta: CurrentTripDelta;
  companion_status: CompanionStatus;
}
