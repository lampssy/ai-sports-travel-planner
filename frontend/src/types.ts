export type SkillLevel = "beginner" | "intermediate" | "advanced";
export type TravelMonth = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12;
export type TravelWindowMode = "any" | "month" | "dates";
export type BudgetMode = "lodging_nightly" | "total_trip";
export type BookingStatus =
  | "not_booked_yet"
  | "booked_through_app"
  | "booked_elsewhere";
export type GroupImportance =
  | "ignore"
  | "secondary"
  | "normal"
  | "important"
  | "primary"
  | "very_high";
export type FactorImportance = "low" | "normal" | "high";
export type PreferenceMode = "prefer" | "avoid" | "ignore" | "require";

export interface SearchFilters {
  location: string;
  maxPrice: string;
  stars: "" | "1" | "2" | "3";
  skillLevel: "" | SkillLevel;
  budgetFlex: string;
  travelWindowMode: TravelWindowMode;
  travelMonth: "" | TravelMonth;
  tripStartDate: string;
  tripEndDate: string;
  originText: string;
  maxDriveHours: string;
  valueObjective: "" | "pass_price_per_day" | "pass_terrain_value";
}

export interface GroupPriorityPatch {
  group_id: string;
  importance: GroupImportance;
}

export interface FactorPreferencePatch {
  factor_id: string;
  mode: PreferenceMode;
  values: string[];
  importance: FactorImportance;
}

export interface SearchObjective {
  factor_id: string;
  importance: FactorImportance;
}

export interface SearchIntent {
  constraints: {
    location?: { country: string };
    travel_window?:
      | { month: number }
      | { start_date: string; end_date: string };
    lodging_budget?: {
      mode: "lodging_nightly";
      maximum: number;
      currency: string;
      budget_flex: number;
    };
    travel_limit?: { maximum_duration_hours: number; mode: "car" };
    minimum_stay_quality?: { minimum_score: number };
  };
  party: { skill_levels: SkillLevel[] };
  travel_context: { origin_text?: string; mode?: "car" };
  objectives: SearchObjective[];
  group_priorities: GroupPriorityPatch[];
  factor_preferences: FactorPreferencePatch[];
  assumptions: string[];
}

export interface SearchV4Request {
  intent: SearchIntent;
  brief: string | null;
  generate_refinements: boolean;
  already_answered_question_ids: string[];
}

export interface FactorScoreBreakdown {
  factor_id: string;
  group_id: string;
  direction: "prefer" | "avoid";
  raw_value: unknown;
  raw_utility: number;
  neutral_utility: number;
  effective_evidence_cap: number;
  effective_utility: number;
  effective_weight: number;
  contribution_points: number;
  evidence_cap_components: Record<string, unknown>;
  warnings: string[];
  provenance_summary: string;
  explanation_inputs: Record<string, unknown>;
}

export interface GroupScoreBreakdown {
  group_id: string;
  normalized_share: number;
  group_utility: number;
  contribution_points: number;
}

export interface ConstraintIssue {
  constraint_id: string;
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface SearchV4AccessSummary {
  ski_area_access_id: string;
  access_mode: string;
  lift_distance: string;
  nearest_lift_name: string | null;
  distance_m: number | null;
  duration_minutes: number | null;
  is_direct: boolean;
}

export interface SearchV4PassPriceSummary {
  duration_days: number;
  audience: string;
  amount: number | null;
  amount_min: number | null;
  amount_max: number | null;
  currency: string;
  price_kind: string;
  season_label: string | null;
}

export interface SearchV4PassSummary {
  lift_pass_product_id: string;
  name: string;
  validity_scope: string;
  covered_ski_area_ids: string[];
  accessible_piste_km: number | null;
  price: SearchV4PassPriceSummary | null;
}

export interface SearchV4Configuration {
  candidate_id: string;
  ski_region_id: string;
  ski_region_name: string;
  stay_destination_id: string;
  stay_destination_name: string;
  stay_base_id: string;
  stay_base_name: string;
  ski_area_id: string;
  ski_area_name: string;
  access: SearchV4AccessSummary;
  selected_pass: SearchV4PassSummary;
  lodging_estimate: {
    mode: "lodging_nightly" | "total_trip";
    minimum: number;
    maximum: number;
    currency: string;
    trust_status:
      | "verified"
      | "verified_with_adjustment"
      | "estimated"
      | "needs_source";
    provenance: string;
  } | null;
  ranking_status: "ranked" | "unscored";
  fit_score: number | null;
  groups: GroupScoreBreakdown[];
  factors: FactorScoreBreakdown[];
  constraint_warnings: ConstraintIssue[];
}

export interface SearchV4RecommendationGroup {
  ski_region_id: string;
  ski_region_name: string;
  rank: number;
  fit_score: number | null;
  top_configuration: SearchV4Configuration;
  alternative_configurations: SearchV4Configuration[];
}

export interface RefinementOption {
  label: string;
  description: string;
  group_priority_patches: GroupPriorityPatch[];
  factor_preference_patches: FactorPreferencePatch[];
  objective_patches: SearchObjective[];
}

export interface RefinementProposal {
  question_id: string;
  question: string;
  reason: string;
  options: RefinementOption[];
}

export interface SearchResponse {
  search_model_version: "search-v4";
  ranking_policy_version: string;
  ranking_status: "ranked" | "unscored";
  unscored_reason: string | null;
  applied_intent: SearchIntent;
  eligible_candidate_count: number;
  excluded_candidate_count: number;
  results: SearchV4RecommendationGroup[];
  refinements: RefinementProposal[];
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

export interface TripClarificationOption {
  id: string;
  label: string;
  description: string;
  context_patch: TripContextPatch;
  filter_patch: { min_price?: number | null; max_price?: number | null } | null;
}

export interface TripClarification {
  id: string;
  question: string;
  reason: string;
  priority: number;
  options: TripClarificationOption[];
}

export interface ParsedQueryResponse {
  filters: Partial<{
    location: string;
    min_price: number;
    max_price: number;
    stars: number;
    skill_level: SkillLevel;
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

export type SnowConfidenceLabel = "poor" | "fair" | "good";
export type AvailabilityStatus =
  | "open"
  | "limited"
  | "temporarily_closed"
  | "out_of_season";
export type ComparisonBasisKind = "since_last_check" | "since_trip_saved";
export type CurrentTripDeltaStatus =
  | "changed"
  | "unchanged"
  | "insufficient_history";
export type TripWindowStatus = "unscheduled" | "upcoming" | "active" | "past";
export type SourceType = "forecast" | "reported" | "estimated";
export type FreshnessStatus = "fresh" | "stale" | "historical" | "unknown";

export interface ProvenanceInfo {
  source_name: string | null;
  source_type: SourceType;
  updated_at: string | null;
  freshness_status: FreshnessStatus;
  basis_summary: string;
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
