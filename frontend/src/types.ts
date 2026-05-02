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

export interface SearchResult {
  resort_id: string;
  resort_name: string;
  region: string;
  selected_ski_area_id: string;
  selected_ski_area_name: string;
  selected_stay_base_name: string;
  selected_stay_base_lift_distance: LiftDistance;
  stay_base_price_range: string;
  selected_area_name: string;
  selected_area_lift_distance: LiftDistance;
  area_price_range: string;
  rental_name: string;
  rental_price_range: string;
  rating_estimate: number;
  link: string;
  score: number;
  budget_penalty: number;
  conditions_summary: string;
  snow_confidence_score: number;
  snow_confidence_label: SnowConfidenceLabel;
  availability_status: AvailabilityStatus;
  conditions_score: number;
  conditions_provenance: ProvenanceInfo;
  explanation: SearchExplanation;
  recommendation_narrative: string | null;
  recommendation_confidence: number;
  planning_summary: string | null;
  planning_provenance: ProvenanceInfo | null;
  planning_evidence_count: number | null;
  planning_weather_metrics: WeatherEvidenceMetrics | null;
  best_travel_months: number[];
}

export interface SearchResponse {
  results: SearchResult[];
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
}

export interface CurrentTrip {
  resort_id: string;
  resort_name: string;
  selected_ski_area_id: string;
  selected_ski_area_name: string;
  selected_stay_base_name: string;
  selected_area_name: string;
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
