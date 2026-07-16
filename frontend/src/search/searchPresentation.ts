import type {
  SearchIntent,
  SearchV4Configuration,
} from "../types";

export const monthOptions = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
] as const;

export const featureOptions = [
  ["marked_freeride_routes", "Marked freeride routes"],
  ["snow_park", "Snow park"],
  ["night_skiing", "Night skiing"],
  ["glacier_terrain", "Glacier terrain"],
  ["snowmaking_availability", "Snowmaking resilience"],
  ["terrain_potential_scale", "Largest connected terrain"],
  ["lift_network_scale", "Large lift network"],
] as const;

export const factorLabels: Record<string, string> = {
  accessible_terrain_scale: "Pass-accessible terrain",
  party_skill_coverage: "Party skill fit",
  terrain_potential_scale: "Connected terrain",
  lift_network_scale: "Lift network",
  marked_freeride_routes: "Marked freeride routes",
  snow_park: "Snow park",
  night_skiing: "Night skiing",
  glacier_terrain: "Glacier terrain",
  snowmaking_availability: "Snowmaking resilience",
  stay_base_access: "Stay-base access",
  pass_price_per_day: "Lowest pass price per day",
  pass_terrain_value: "Terrain per pass price",
  ski_day_apres: "On-mountain après",
  local_apres: "Stay-base après",
  local_pace: "Local pace",
  development_style: "Development style",
  base_type: "Base type",
  travel_effort: "Travel effort",
  trip_window_snow_fit: "Trip-window snow fit",
};

export const groupLabels: Record<string, string> = {
  trip_viability: "Trip viability",
  ski_experience: "Ski experience",
  stay_practicality: "Stay practicality",
  value: "Value",
  character: "Character",
  travel_effort: "Travel effort",
};

export type ParsedChipAction =
  | { kind: "location" }
  | { kind: "travelWindow" }
  | { kind: "lodgingBudget" }
  | { kind: "stayQuality" }
  | { kind: "travelLimit" }
  | { kind: "skill" }
  | { kind: "objective"; id: string }
  | { kind: "group"; id: string }
  | { kind: "preference"; id: string };

export interface ParsedChip {
  id: string;
  label: string;
  action: ParsedChipAction;
}

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll("_", " ");
}

function monthName(month: number): string {
  return monthOptions[month - 1] ?? `Month ${month}`;
}

export function buildParsedChips(intent: SearchIntent): ParsedChip[] {
  const chips: ParsedChip[] = [];
  const { constraints } = intent;
  if (constraints.location?.country) {
    chips.push({
      id: "location",
      label: constraints.location.country,
      action: { kind: "location" },
    });
  }
  if (constraints.travel_window) {
    const label =
      "month" in constraints.travel_window
        ? `${monthName(constraints.travel_window.month)} window`
        : `${constraints.travel_window.start_date} to ${constraints.travel_window.end_date}`;
    chips.push({ id: "travel-window", label, action: { kind: "travelWindow" } });
  }
  if (constraints.lodging_budget) {
    chips.push({
      id: "lodging-budget",
      label: `Max ${constraints.lodging_budget.currency} ${constraints.lodging_budget.maximum}/night`,
      action: { kind: "lodgingBudget" },
    });
  }
  if (constraints.minimum_stay_quality) {
    const score = constraints.minimum_stay_quality.minimum_score;
    const tier = score >= 10 ? "Premium" : score >= 6 ? "Standard+" : "Budget+";
    chips.push({
      id: "stay-quality",
      label: `${tier} stay`,
      action: { kind: "stayQuality" },
    });
  }
  if (constraints.travel_limit) {
    chips.push({
      id: "travel-limit",
      label: `Max ${constraints.travel_limit.maximum_duration_hours} hours by car`,
      action: { kind: "travelLimit" },
    });
  }
  for (const skill of intent.party.skill_levels) {
    chips.push({
      id: `skill-${skill}`,
      label: titleCase(skill),
      action: { kind: "skill" },
    });
  }
  for (const item of intent.objectives) {
    chips.push({
      id: `objective-${item.factor_id}`,
      label: `Optimize ${factorLabels[item.factor_id] ?? item.factor_id}`,
      action: { kind: "objective", id: item.factor_id },
    });
  }
  for (const item of intent.group_priorities) {
    chips.push({
      id: `group-${item.group_id}`,
      label: `${groupLabels[item.group_id] ?? item.group_id}: ${item.importance}`,
      action: { kind: "group", id: item.group_id },
    });
  }
  for (const item of intent.factor_preferences) {
    chips.push({
      id: `factor-${item.factor_id}`,
      label: `${titleCase(item.mode)} ${factorLabels[item.factor_id] ?? item.factor_id}${
        item.values.length ? `: ${item.values.join(", ")}` : ""
      }`,
      action: { kind: "preference", id: item.factor_id },
    });
  }
  return chips;
}

export function formatAccess(configuration: SearchV4Configuration): string {
  return titleCase(configuration.access.access_mode);
}

export function formatPassPrice(configuration: SearchV4Configuration): string {
  const price = configuration.selected_pass.price;
  if (!price) return "Comparable pass price unavailable";
  if (price.amount != null) {
    return `${price.currency} ${price.amount} / ${price.duration_days} days`;
  }
  if (price.amount_max != null) {
    return `${price.currency} ${price.amount_min}-${price.amount_max} / ${price.duration_days} days`;
  }
  return "Pass price unresolved";
}

export function formatLodging(configuration: SearchV4Configuration): string {
  const estimate = configuration.lodging_estimate;
  if (!estimate) return "Lodging estimate unavailable";
  return `${estimate.currency} ${estimate.minimum}-${estimate.maximum} nightly (${estimate.trust_status})`;
}
