import type {
  FactorPreferencePatch,
  GroupPriorityPatch,
  ParsedQueryResponse,
  SearchFilters,
  SearchIntent,
  SearchObjective,
  SearchResponse,
  SearchV4Configuration,
  SearchV4RecommendationGroup,
} from "../types";

export interface SearchSession {
  brief: string;
  intent: SearchIntent;
  response: SearchResponse;
  expandedGroupIds: Set<string>;
  selectedCandidateIdByGroup: Record<string, string>;
  resultsScrollY: number;
}

export const defaultSearchFilters: SearchFilters = {
  location: "France",
  maxPrice: "320",
  stars: "2",
  skillLevel: "intermediate",
  budgetFlex: "0.10",
  travelWindowMode: "month",
  travelMonth: 3,
  tripStartDate: "",
  tripEndDate: "",
  originText: "",
  maxDriveHours: "",
  valueObjective: "pass_terrain_value",
};

export function buildSearchIntent(
  filters: SearchFilters,
  assumptions: string[],
  preferences: FactorPreferencePatch[],
  groupPriorities: GroupPriorityPatch[],
  objectives: SearchObjective[],
): SearchIntent {
  const constraints: SearchIntent["constraints"] = {};
  if (filters.location.trim()) {
    constraints.location = { country: filters.location.trim() };
  }
  if (filters.travelWindowMode === "month" && filters.travelMonth) {
    constraints.travel_window = { month: filters.travelMonth };
  } else if (
    filters.travelWindowMode === "dates" &&
    filters.tripStartDate &&
    filters.tripEndDate
  ) {
    constraints.travel_window = {
      start_date: filters.tripStartDate,
      end_date: filters.tripEndDate,
    };
  }
  const maximum = Number(filters.maxPrice);
  if (Number.isFinite(maximum) && maximum > 0) {
    constraints.lodging_budget = {
      mode: "lodging_nightly",
      maximum,
      currency: "EUR",
      budget_flex: Number(filters.budgetFlex) || 0,
    };
  }
  if (filters.stars) {
    constraints.minimum_stay_quality = {
      minimum_score: (Number(filters.stars) / 3) * 10,
    };
  }
  const maximumDrive = Number(filters.maxDriveHours);
  if (
    filters.originText.trim() &&
    Number.isFinite(maximumDrive) &&
    maximumDrive > 0
  ) {
    constraints.travel_limit = {
      maximum_duration_hours: maximumDrive,
      mode: "car",
    };
  }
  return {
    constraints,
    party: {
      skill_levels: filters.skillLevel ? [filters.skillLevel] : [],
    },
    travel_context: filters.originText.trim()
      ? { origin_text: filters.originText.trim(), mode: "car" }
      : {},
    objectives,
    group_priorities: groupPriorities,
    factor_preferences: preferences,
    assumptions,
  };
}

export function mergeParsedFilters(
  current: SearchFilters,
  parsed: ParsedQueryResponse,
): SearchFilters {
  const next = { ...current };
  if (parsed.filters.location) next.location = parsed.filters.location;
  if (parsed.filters.max_price != null) {
    next.maxPrice = String(parsed.filters.max_price);
  }
  if (parsed.filters.stars != null && parsed.filters.stars >= 1) {
    next.stars = String(
      Math.min(3, parsed.filters.stars),
    ) as SearchFilters["stars"];
  }
  if (parsed.filters.skill_level) next.skillLevel = parsed.filters.skill_level;
  if (parsed.filters.trip_start_date && parsed.filters.trip_end_date) {
    next.travelWindowMode = "dates";
    next.tripStartDate = parsed.filters.trip_start_date;
    next.tripEndDate = parsed.filters.trip_end_date;
  } else if (parsed.filters.travel_month) {
    next.travelWindowMode = "month";
    next.travelMonth = parsed.filters.travel_month;
  }
  if (parsed.trip_context?.origin_text) {
    next.originText = parsed.trip_context.origin_text;
  }
  return next;
}

export function validateSearchFilters(filters: SearchFilters): string | null {
  if (!filters.location.trim()) return "Choose a country.";
  if (
    filters.travelWindowMode === "dates" &&
    (!filters.tripStartDate || !filters.tripEndDate)
  ) {
    return "Provide both trip dates.";
  }
  if (
    filters.travelWindowMode === "dates" &&
    filters.tripEndDate < filters.tripStartDate
  ) {
    return "The end date must be on or after the start date.";
  }
  const maximumText = filters.maxPrice.trim();
  const maximum = Number(maximumText);
  if (maximumText && (!Number.isFinite(maximum) || maximum <= 0)) {
    return "Maximum nightly price must be greater than 0.";
  }
  const maximumDriveText = filters.maxDriveHours.trim();
  const maximumDrive = Number(maximumDriveText);
  if (
    maximumDriveText &&
    (!Number.isFinite(maximumDrive) || maximumDrive <= 0)
  ) {
    return "Hard drive limit must be greater than 0 hours.";
  }
  if (maximumDriveText && !filters.originText.trim()) {
    return "Provide an origin to use a hard drive limit.";
  }
  const flex = Number(filters.budgetFlex);
  if (filters.budgetFlex && (!Number.isFinite(flex) || flex < 0 || flex > 0.5)) {
    return "Budget flexibility must be between 0 and 0.5.";
  }
  return null;
}

export function upsertBy<T>(
  current: T[],
  patches: T[],
  key: (item: T) => string,
): T[] {
  const patchKeys = new Set(patches.map(key));
  return [...current.filter((item) => !patchKeys.has(key(item))), ...patches];
}

function candidateIdsByGroup(
  response: SearchResponse,
): Record<string, Set<string>> {
  return Object.fromEntries(
    response.results.map((result) => [
      result.ski_region_id,
      new Set([
        result.top_configuration.candidate_id,
        ...result.alternative_configurations.map((item) => item.candidate_id),
      ]),
    ]),
  );
}

function defaultSelections(response: SearchResponse): Record<string, string> {
  return Object.fromEntries(
    response.results.map((result) => [
      result.ski_region_id,
      result.top_configuration.candidate_id,
    ]),
  );
}

export function createSearchSession(
  brief: string,
  intent: SearchIntent,
  response: SearchResponse,
): SearchSession {
  const winner = response.results[0]?.ski_region_id;
  return {
    brief,
    intent,
    response,
    expandedGroupIds: new Set(winner ? [winner] : []),
    selectedCandidateIdByGroup: defaultSelections(response),
    resultsScrollY: 0,
  };
}

export function reconcileSearchSession(
  current: SearchSession,
  intent: SearchIntent,
  response: SearchResponse,
): SearchSession {
  const availableCandidateIds = candidateIdsByGroup(response);
  const selectedCandidateIdByGroup = defaultSelections(response);
  for (const [groupId, candidateId] of Object.entries(
    current.selectedCandidateIdByGroup,
  )) {
    if (availableCandidateIds[groupId]?.has(candidateId)) {
      selectedCandidateIdByGroup[groupId] = candidateId;
    }
  }

  const currentGroupIds = new Set(response.results.map((item) => item.ski_region_id));
  const expandedGroupIds = new Set(
    [...current.expandedGroupIds].filter((groupId) => currentGroupIds.has(groupId)),
  );
  const winner = response.results[0]?.ski_region_id;
  if (winner) expandedGroupIds.add(winner);

  return {
    ...current,
    intent,
    response,
    expandedGroupIds,
    selectedCandidateIdByGroup,
  };
}

export function findSelectedCandidate(
  result: SearchV4RecommendationGroup,
  candidateId: string | undefined,
): SearchV4Configuration {
  return (
    [result.top_configuration, ...result.alternative_configurations].find(
      (item) => item.candidate_id === candidateId,
    ) ?? result.top_configuration
  );
}
