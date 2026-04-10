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

export interface SearchFilters {
  location: string;
  minPrice: string;
  maxPrice: string;
  stars: "1" | "2" | "3";
  skillLevel: SkillLevel;
  liftDistance: "" | LiftDistance;
  budgetFlex: string;
  travelMonth: "" | TravelMonth;
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

export interface SearchResult {
  resort_id: string;
  resort_name: string;
  region: string;
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
  explanation: SearchExplanation;
  recommendation_narrative: string | null;
  recommendation_confidence: number;
  planning_summary: string | null;
  planning_evidence_count: number | null;
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
  }>;
  confidence: number;
  unknown_parts: string[];
}
