import type {
  RefinementPreview,
  SearchIntent,
  SearchV4Configuration,
  SearchV4PassSummary,
  SearchV4RecommendationGroup,
} from "../types";
import type { EvidenceQualityMode } from "../ui/snowcastCopy";

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
    const label = factorLabels[item.factor_id];
    if (!label) continue;
    chips.push({
      id: `objective-${item.factor_id}`,
      label: `Optimize ${label}`,
      action: { kind: "objective", id: item.factor_id },
    });
  }
  for (const item of intent.group_priorities) {
    const label = groupLabels[item.group_id];
    if (!label) continue;
    chips.push({
      id: `group-${item.group_id}`,
      label: `${label}: ${item.importance}`,
      action: { kind: "group", id: item.group_id },
    });
  }
  for (const item of intent.factor_preferences) {
    const label = factorLabels[item.factor_id];
    if (!label) continue;
    chips.push({
      id: `factor-${item.factor_id}`,
      label: `${titleCase(item.mode)} ${label}${
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
  if (!estimate || estimate.trust_status === "needs_source") {
    return "Lodging estimate unavailable";
  }
  const unit = estimate.mode === "lodging_nightly" ? "/night" : " total trip";
  return `${estimate.currency} ${estimate.minimum}-${estimate.maximum}${unit} (${lodgingTrustLabel(estimate.trust_status)})`;
}

export function lodgingTrustLabel(
  trustStatus: NonNullable<SearchV4Configuration["lodging_estimate"]>["trust_status"],
): string {
  switch (trustStatus) {
    case "verified":
      return "Verified";
    case "verified_with_adjustment":
      return "Verified with adjustment";
    case "estimated":
      return "Estimated";
    case "needs_source":
      return "Needs source";
  }
}

export function formatAccommodationEstimate(
  configuration: SearchV4Configuration,
): string | null {
  const estimate = configuration.lodging_estimate;
  if (!estimate || estimate.trust_status === "needs_source") return null;
  const unit = estimate.mode === "lodging_nightly" ? "/night" : " total trip";
  return `${estimate.currency} ${formatNumber(estimate.minimum)}-${formatNumber(
    estimate.maximum,
  )}${unit}`;
}

export type TripEssentialCategory =
  | "terrain"
  | "passValue"
  | "liftAccess"
  | "lodging"
  | "travelEffort";

export interface TripEssential {
  category: TripEssentialCategory;
  label: string;
  value: string;
}

export interface TerrainPresentation {
  essentialValue: string;
  evidenceLabel: string;
}

export function terrainPresentation(
  selectedPass: SearchV4PassSummary,
): TerrainPresentation | null {
  const kilometres = selectedPass.accessible_piste_km;
  const evidence = selectedPass.accessible_piste_km_evidence;
  if (kilometres == null || !evidence) return null;

  const prefix =
    evidence.trust_status === "estimated"
      ? "Estimated "
      : evidence.trust_status === "verified_with_adjustment"
        ? "Adjusted "
        : "";
  const needsSource = evidence.trust_status === "needs_source";
  const unresolvedSuffix = needsSource ? " (needs source)" : "";

  if (evidence.scope === "ski_area") {
    return {
      essentialValue: `${prefix}${kilometres} km (ski area only${
        needsSource ? "; needs source" : ""
      })`,
      evidenceLabel: `${prefix}${kilometres} km in selected ski area${
        needsSource ? " (needs source)" : ""
      }; pass-wide coverage ${needsSource ? "unresolved" : "needs source"}`,
    };
  }
  if (evidence.scope === "terrain_domain") {
    return {
      essentialValue: `${prefix}${kilometres} km (covered domain${
        needsSource ? "; needs source" : ""
      })`,
      evidenceLabel: `${prefix}${kilometres} km in covered terrain domain${unresolvedSuffix}`,
    };
  }
  return {
    essentialValue: `${prefix}${kilometres} km${unresolvedSuffix}`,
    evidenceLabel: `${prefix}${kilometres} km pass-accessible terrain${unresolvedSuffix}`,
  };
}

export function factorLabelForConfiguration(
  configuration: SearchV4Configuration,
  factorId: string,
): string | undefined {
  if (factorId !== "accessible_terrain_scale") return factorLabels[factorId];
  const scope = configuration.selected_pass.accessible_piste_km_evidence?.scope;
  if (scope === "ski_area") return "Selected ski-area terrain";
  if (scope === "terrain_domain") return "Covered terrain-domain scale";
  if (scope === "pass") return factorLabels[factorId];
  return "Terrain scale";
}

const tripEssentialOrder: TripEssentialCategory[] = [
  "terrain",
  "passValue",
  "liftAccess",
  "lodging",
  "travelEffort",
];

const factorEssentialCategories: Record<string, TripEssentialCategory> = {
  accessible_terrain_scale: "terrain",
  terrain_potential_scale: "terrain",
  lift_network_scale: "terrain",
  pass_price_per_day: "passValue",
  pass_terrain_value: "passValue",
  stay_base_access: "liftAccess",
  travel_effort: "travelEffort",
};

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

const accessModeLabels: Record<string, string | null> = {
  walk: "walk",
  ski_bus: "ski bus",
  drive: "drive",
  ski_in_ski_out: "ski-in/out",
  mixed: "mixed access",
  unknown: null,
};

const liftDistanceLabels: Record<string, string> = {
  near: "Near",
  medium: "Moderate",
  far: "Far",
};

function passValue(configuration: SearchV4Configuration): string | null {
  const price = configuration.selected_pass.price;
  if (!price || price.duration_days <= 0) return null;
  if (price.amount != null) {
    return `${price.currency} ${formatNumber(price.amount / price.duration_days)}/day`;
  }
  if (price.amount_min != null && price.amount_max != null) {
    return `${price.currency} ${formatNumber(
      price.amount_min / price.duration_days,
    )}-${formatNumber(price.amount_max / price.duration_days)}/day`;
  }
  return null;
}

function accessValue(configuration: SearchV4Configuration): string | null {
  const { access } = configuration;
  const mode = accessModeLabels[access.access_mode];
  if (!mode) return null;
  if (access.distance_m != null) return `${access.distance_m} m ${mode}`;
  if (access.duration_minutes != null) {
    return `${access.duration_minutes} min ${mode}`;
  }
  if (access.is_direct || access.access_mode === "ski_in_ski_out") {
    return "Ski-in/out";
  }
  const distance = liftDistanceLabels[access.lift_distance];
  return distance ? `${distance} ${mode}` : titleCase(mode);
}

function lodgingValue(configuration: SearchV4Configuration): string | null {
  const estimate = configuration.lodging_estimate;
  if (!estimate || estimate.trust_status === "needs_source") return null;
  const prefix =
    estimate.trust_status === "estimated"
      ? "Estimated "
      : estimate.trust_status === "verified_with_adjustment"
        ? "Adjusted "
        : "";
  return `${prefix}${estimate.currency} ${estimate.minimum}-${estimate.maximum}/night`;
}

export function formatTripEssential(
  category: TripEssentialCategory,
  configuration: SearchV4Configuration,
): TripEssential | null {
  switch (category) {
    case "terrain":
      const terrain = terrainPresentation(configuration.selected_pass);
      return terrain
        ? {
            category,
            label: "Terrain",
            value: terrain.essentialValue,
          }
        : null;
    case "passValue": {
      const value = passValue(configuration);
      return value ? { category, label: "Pass value", value } : null;
    }
    case "liftAccess": {
      const value = accessValue(configuration);
      return value ? { category, label: "Lift access", value } : null;
    }
    case "lodging": {
      const value = lodgingValue(configuration);
      return value ? { category, label: "Stay", value } : null;
    }
    case "travelEffort":
      return null;
  }
}

function activeEssentialCategories(intent: SearchIntent): TripEssentialCategory[] {
  const categories: TripEssentialCategory[] = [];
  const addFactor = (factorId: string) => {
    const category = factorEssentialCategories[factorId];
    if (category && !categories.includes(category)) categories.push(category);
  };
  intent.objectives.forEach((item) => addFactor(item.factor_id));
  intent.factor_preferences.forEach((item) => addFactor(item.factor_id));
  if (intent.constraints.lodging_budget || intent.constraints.minimum_stay_quality) {
    categories.push("lodging");
  }
  if (intent.constraints.travel_limit || intent.travel_context.origin_text) {
    categories.push("travelEffort");
  }
  return [...new Set(categories)];
}

export function selectTripEssentialCategories(
  intent: SearchIntent,
  groups: SearchV4RecommendationGroup[],
): TripEssentialCategory[] {
  const visibleConfigurations = groups
    .slice(0, 3)
    .map((group) => group.top_configuration);
  if (!visibleConfigurations.length) return [];

  const comparable = (category: TripEssentialCategory) =>
    visibleConfigurations.every(
      (configuration) => formatTripEssential(category, configuration) !== null,
    );
  const selected: TripEssentialCategory[] = [];
  for (const category of [
    ...activeEssentialCategories(intent),
    ...tripEssentialOrder,
  ]) {
    if (!selected.includes(category) && comparable(category)) selected.push(category);
    if (selected.length === 3) break;
  }
  return selected;
}

const strengthCopy: Record<string, string> = {
  accessible_terrain_scale: "Terrain scale contributes positively to this comparison.",
  party_skill_coverage: "The selected terrain supports your party's skill mix.",
  terrain_potential_scale: "The selected pass supports a broad terrain choice.",
  lift_network_scale: "The lift network supports varied ski-day plans.",
  glacier_terrain: "Glacier terrain adds resilience for the selected window.",
  snowmaking_availability: "Snowmaking adds resilience for the selected window.",
  stay_base_access: "The selected stay base keeps lift access practical.",
  pass_price_per_day: "The selected pass offers competitive daily value.",
  pass_terrain_value: "The selected pass balances terrain access and price.",
  travel_effort: "The route keeps travel effort within the requested plan.",
  trip_window_snow_fit: "The available evidence supports the selected snow window.",
};

const watchoutCopy: Record<string, string> = {
  accessible_terrain_scale: "Terrain-scale evidence is limited for this pass.",
  party_skill_coverage: "Party skill coverage needs a closer terrain review.",
  terrain_potential_scale: "Connected terrain evidence is limited.",
  lift_network_scale: "Lift-network evidence is limited.",
  glacier_terrain: "Glacier access can still be disrupted by weather.",
  snowmaking_availability: "Snowmaking does not remove weather variability.",
  stay_base_access: "Lift access may require extra local travel.",
  pass_price_per_day: "Comparable pass-price evidence is limited.",
  pass_terrain_value: "Pass value depends on the terrain you plan to use.",
  travel_effort: "Travel time remains approximate for this route.",
  trip_window_snow_fit: "Snow evidence is limited for the requested travel window.",
};

export interface CandidateNarrative {
  verdict: string;
  strength?: string;
  watchout?: string;
}

export function buildCandidateNarrative(
  configuration: SearchV4Configuration,
): CandidateNarrative {
  const supported = configuration.factors
    .filter(
      (factor) =>
        strengthCopy[factor.factor_id] &&
        factor.effective_evidence_cap > 0 &&
        factor.effective_utility > factor.neutral_utility,
    )
    .sort((left, right) => right.effective_utility - left.effective_utility)[0];
  const caution = configuration.factors.find(
    (factor) =>
      watchoutCopy[factor.factor_id] &&
      (factor.effective_evidence_cap === 0 || factor.warnings.length > 0),
  );
  const supportedLabel = supported
    ? factorLabelForConfiguration(configuration, supported.factor_id)
    : undefined;
  const supportedTerrain =
    supported?.factor_id === "accessible_terrain_scale"
      ? terrainPresentation(configuration.selected_pass)
      : null;
  const verdict = supported
    ? supported.factor_id === "stay_base_access"
      ? "A practical lift-access match for this trip."
      : `A strong ${supportedLabel?.toLowerCase() ?? "trip"} match.`
    : "A complete trip configuration for comparison.";
  return {
    verdict,
    ...(supported
      ? {
          strength: supportedTerrain
            ? `${supportedTerrain.evidenceLabel}.`
            : strengthCopy[supported.factor_id],
        }
      : {}),
    ...(caution ? { watchout: watchoutCopy[caution.factor_id] } : {}),
  };
}

export function snowWindowLabel(configuration: SearchV4Configuration): string {
  const factor = configuration.factors.find(
    (item) => item.factor_id === "trip_window_snow_fit",
  );
  if (!factor || factor.effective_evidence_cap === 0) return "Unknown";
  if (factor.effective_utility >= 0.75) return "Strong";
  if (factor.effective_utility >= 0.55) return "Good";
  return "Mixed";
}

export function evidenceQualityMode(
  configuration: SearchV4Configuration,
): EvidenceQualityMode | null {
  const snowFactor = configuration.factors.find(
    (item) => item.factor_id === "trip_window_snow_fit",
  );
  if (!snowFactor || snowFactor.effective_evidence_cap === 0) {
    return "fallbackHeavy";
  }
  return null;
}

export function refinementPreviewCopy(
  preview?: RefinementPreview | null,
): string {
  if (!preview) return "This answer can materially reorder your results";
  const changes = preview.top_rank_changes;
  if (changes.length === 1) {
    const change = changes[0];
    if (change.previous_rank == null && change.preview_rank != null) {
      return "One result would enter your top three.";
    }
    if (change.previous_rank != null && change.preview_rank == null) {
      return "One result would leave your top three.";
    }
    if (
      change.previous_rank != null &&
      change.preview_rank != null &&
      change.previous_rank !== change.preview_rank
    ) {
      return `One result would move from #${change.previous_rank} to #${change.preview_rank}.`;
    }
  }
  if (changes.length > 0) {
    return `This choice would change ${changes.length} result positions.`;
  }
  if (preview.eligible_candidate_count_delta !== 0) {
    return `This choice may change eligibility for ${Math.abs(
      preview.eligible_candidate_count_delta,
    )} trip configurations.`;
  }
  return "This answer can materially reorder your results";
}
