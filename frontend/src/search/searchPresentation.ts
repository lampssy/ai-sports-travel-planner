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
  | { kind: "travelOrigin" }
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
    const { month, start_date: startDate, end_date: endDate } =
      constraints.travel_window;
    const label =
      startDate && endDate
        ? `${startDate} to ${endDate}`
        : typeof month === "number"
          ? `${monthName(month)} window`
          : null;
    if (label) {
      chips.push({ id: "travel-window", label, action: { kind: "travelWindow" } });
    }
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
  const originText = intent.travel_context.origin_text?.trim();
  if (originText) {
    chips.push({
      id: "travel-origin",
      label: `Prefer closer to ${originText}`,
      action: { kind: "travelOrigin" },
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

function accessTrustState(
  configuration: SearchV4Configuration,
): "verified" | "verified_with_adjustment" | "estimated" | "needs_source" {
  const statuses = [
    configuration.access.relationship_trust_status,
    configuration.access.access_mode_distance_trust_status,
  ];
  if (statuses.includes("needs_source")) return "needs_source";
  if (statuses.includes("estimated")) return "estimated";
  if (statuses.includes("verified_with_adjustment")) {
    return "verified_with_adjustment";
  }
  return "verified";
}

function accessTrustPrefix(configuration: SearchV4Configuration): string {
  const trust = accessTrustState(configuration);
  if (trust === "estimated") return "Estimated ";
  if (trust === "verified_with_adjustment") return "Adjusted ";
  return "";
}

export function formatAccess(configuration: SearchV4Configuration): string {
  if (accessTrustState(configuration) === "needs_source") {
    return "Access details need source verification";
  }
  const mode = accessModeLabels[configuration.access.access_mode];
  if (!mode) return "Access mode unavailable";
  return `${accessTrustPrefix(configuration)}${titleCase(mode)}`;
}

export function formatAccommodationAccessContext(
  configuration: SearchV4Configuration,
): string | null {
  if (accessTrustState(configuration) === "needs_source") return null;
  const { access } = configuration;
  const mode = accessModeLabels[access.access_mode];
  if (!mode) return null;
  const detail =
    access.distance_m != null
      ? `${access.distance_m} m ${mode}`
      : access.duration_minutes != null
        ? `${access.duration_minutes} min ${mode}`
        : access.is_direct
          ? "direct access"
          : null;
  const context = detail
    ? access.nearest_lift_name
      ? `${access.nearest_lift_name} - ${detail}`
      : detail
    : access.nearest_lift_name;
  return context ? `${accessTrustPrefix(configuration)}${context}` : null;
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

const selectedPassTerrainFactorIds = new Set([
  "accessible_terrain_scale",
  "pass_terrain_value",
]);

export function factorTrustLabelForConfiguration(
  configuration: SearchV4Configuration,
  factorId: string,
): string | null {
  if (!selectedPassTerrainFactorIds.has(factorId)) return null;
  const status = configuration.selected_pass.accessible_piste_km_evidence?.trust_status;
  switch (status) {
    case "verified":
      return "Verified";
    case "verified_with_adjustment":
      return "Verified with adjustment";
    case "estimated":
      return "Estimated";
    case "needs_source":
      return "Needs source";
    default:
      return null;
  }
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
  if (accessTrustState(configuration) === "needs_source") return null;
  const mode = accessModeLabels[access.access_mode];
  if (!mode) return null;
  const prefix = accessTrustPrefix(configuration);
  if (access.distance_m != null) return `${prefix}${access.distance_m} m ${mode}`;
  if (access.duration_minutes != null) {
    return `${prefix}${access.duration_minutes} min ${mode}`;
  }
  if (access.is_direct || access.access_mode === "ski_in_ski_out") {
    return `${prefix}Ski-in/out`;
  }
  const distance = liftDistanceLabels[access.lift_distance];
  return distance ? `${prefix}${distance} ${mode}` : `${prefix}${titleCase(mode)}`;
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

export interface DecisionEvidencePresentation {
  supports: Array<{ id: string; title: string; detail: string }>;
  uncertainties: Array<{ id: string; detail: string }>;
  technicalDetails: Array<{
    id: string;
    label: string;
    provenance: string;
    evidenceLabel: string;
  }>;
}

function supportedFactor(
  configuration: SearchV4Configuration,
  factorId: string,
): boolean {
  const factor = configuration.factors.find((item) => item.factor_id === factorId);
  return Boolean(
    factor &&
      factor.effective_evidence_cap > 0 &&
      factor.effective_utility > factor.neutral_utility,
  );
}

export function decisionEvidencePresentation(
  configuration: SearchV4Configuration,
): DecisionEvidencePresentation {
  const supports: DecisionEvidencePresentation["supports"] = [];
  const uncertainties: DecisionEvidencePresentation["uncertainties"] = [];
  const addSupport = (id: string, title: string, detail: string) => {
    supports.push({ id, title, detail });
  };
  const addUncertainty = (id: string, detail: string) => {
    if (!uncertainties.some((item) => item.detail === detail)) {
      uncertainties.push({ id, detail });
    }
  };

  const snowFactor = configuration.factors.find(
    (item) => item.factor_id === "trip_window_snow_fit",
  );
  if (supportedFactor(configuration, "trip_window_snow_fit")) {
    addSupport(
      "snow-window",
      "Snow window",
      "Available snow evidence supports the requested travel window.",
    );
  } else if (
    snowFactor &&
    (snowFactor.effective_evidence_cap === 0 || snowFactor.warnings.length > 0)
  ) {
    addUncertainty(
      "snow-window",
      "Snow evidence is limited for the requested travel window.",
    );
  }

  if (supportedFactor(configuration, "party_skill_coverage")) {
    addSupport(
      "skill-match",
      "Skill match",
      "The selected ski area supports the requested skill level.",
    );
  }

  const terrain = terrainPresentation(configuration.selected_pass);
  if (
    terrain &&
    configuration.selected_pass.accessible_piste_km_evidence?.trust_status !==
      "needs_source"
  ) {
    addSupport(
      "terrain",
      "Terrain choice",
      `${terrain.essentialValue} is covered by the selected pass context.`,
    );
  } else {
    addUncertainty(
      "terrain",
      "Comparable pass-wide terrain coverage is not available yet.",
    );
  }

  const access = accessValue(configuration);
  const accessNeedsSource = accessTrustState(configuration) === "needs_source";
  if (access && configuration.access.lift_distance !== "far" && !accessNeedsSource) {
    addSupport(
      "lift-access",
      "Lift access",
      `${configuration.stay_base_name} offers ${access.toLowerCase()} for this configuration.`,
    );
  } else if (accessNeedsSource) {
    addUncertainty(
      "lift-access",
      "Lift access from this stay base still needs source verification.",
    );
  } else {
    addUncertainty(
      "lift-access",
      "Lift access may require additional local travel from the selected stay base.",
    );
  }

  const price = passValue(configuration);
  if (price) {
    addSupport(
      "pass-price",
      "Pass value",
      `The selected pass is currently compared at ${price}.`,
    );
  } else {
    addUncertainty(
      "pass-price",
      "A comparable pass price is not available for this configuration.",
    );
  }

  const lodging = formatAccommodationEstimate(configuration);
  if (lodging) {
    addSupport(
      "lodging",
      "Stay estimate",
      `${configuration.stay_base_name} is estimated at ${lodging}.`,
    );
  } else {
    addUncertainty(
      "lodging",
      "No stay-price estimate is available for this configuration.",
    );
  }

  if (configuration.constraint_warnings.length > 0) {
    addUncertainty(
      "constraints",
      "One or more trip constraints rely on limited supporting data.",
    );
  }

  const technicalDetails: DecisionEvidencePresentation["technicalDetails"] =
    configuration.factors
      .filter((factor) => factorLabels[factor.factor_id] && factor.provenance_summary)
      .map((factor) => ({
        id: `factor-${factor.factor_id}`,
        label:
          factorLabelForConfiguration(configuration, factor.factor_id) ??
          "Ranking factor",
        provenance: factor.provenance_summary,
        evidenceLabel:
          factor.effective_evidence_cap > 0 ? "Supported" : "Limited evidence",
      }));

  const accessTrust = accessTrustState(configuration);
  const accessProvenanceLabel =
    accessTrust === "estimated"
      ? "Estimated access"
      : accessTrust === "verified_with_adjustment"
        ? "Adjusted access"
        : "Selected access";
  const accessEvidencePrefix =
    accessTrust === "estimated"
      ? "Estimated "
      : accessTrust === "verified_with_adjustment"
        ? "Adjusted "
        : "";
  technicalDetails.push(
    accessTrust === "needs_source"
      ? {
          id: "catalog-access",
          label: "Stay base and lift access",
          provenance:
            "Lift-access relationship and distance need source verification.",
          evidenceLabel: "Needs source",
        }
      : {
          id: "catalog-access",
          label: "Stay base and lift access",
          provenance: configuration.access.nearest_lift_name
            ? `${accessProvenanceLabel} is anchored to ${configuration.access.nearest_lift_name}.`
            : `${accessProvenanceLabel} uses the catalog stay-base relationship.`,
          evidenceLabel:
            configuration.access.distance_m != null
              ? `${accessEvidencePrefix}${configuration.access.distance_m} m`
              : `${accessEvidencePrefix}Catalog context`,
        },
  );
  technicalDetails.push({
    id: "selected-pass",
    label: "Selected pass",
    provenance: `${configuration.selected_pass.name} is selected for this configuration.`,
    evidenceLabel: terrain?.evidenceLabel ?? "Coverage unresolved",
  });
  if (configuration.lodging_estimate?.provenance) {
    technicalDetails.push({
      id: "lodging-estimate",
      label: "Lodging estimate",
      provenance: configuration.lodging_estimate.provenance,
      evidenceLabel: "Stay-base estimate",
    });
  }

  return {
    supports: supports.slice(0, 4),
    uncertainties,
    technicalDetails,
  };
}

export function buildCandidateNarrative(
  configuration: SearchV4Configuration,
): CandidateNarrative {
  const accessTrust = accessTrustState(configuration);
  const supported = configuration.factors
    .filter(
      (factor) =>
        strengthCopy[factor.factor_id] &&
        factor.effective_evidence_cap > 0 &&
        factor.effective_utility > factor.neutral_utility &&
        !(
          factor.factor_id === "stay_base_access" &&
          accessTrust === "needs_source"
        ),
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
  const watchout = caution
    ? caution.factor_id === "stay_base_access" && accessTrust === "needs_source"
      ? "Lift-access details need source verification."
      : watchoutCopy[caution.factor_id]
    : undefined;
  const verdict = supported
    ? supported.factor_id === "stay_base_access"
      ? accessTrust === "estimated"
        ? "An estimated practical lift-access match for this trip."
        : accessTrust === "verified_with_adjustment"
          ? "An adjusted practical lift-access match for this trip."
          : "A practical lift-access match for this trip."
      : `A strong ${supportedLabel?.toLowerCase() ?? "trip"} match.`
    : "A complete trip configuration for comparison.";
  return {
    verdict,
    ...(supported
      ? {
          strength: supportedTerrain
            ? `${supportedTerrain.evidenceLabel}.`
            : supported.factor_id === "stay_base_access"
              ? accessTrust === "estimated"
                ? "Catalog estimates suggest the stay base keeps access practical."
                : accessTrust === "verified_with_adjustment"
                  ? "Adjusted access evidence supports the stay base as a practical choice."
                  : strengthCopy[supported.factor_id]
              : strengthCopy[supported.factor_id],
        }
      : {}),
    ...(watchout ? { watchout } : {}),
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
): EvidenceQualityMode {
  if (configuration.evidence_profile === "archive_backed") {
    return "archiveBacked";
  }
  if (configuration.evidence_profile === "forecast_assisted") {
    return "forecastAssisted";
  }
  return "fallbackHeavy";
}

export function refinementPreviewCopy(
  preview?: RefinementPreview | null,
  intentChanged = true,
): string {
  if (!intentChanged) return "Keeps your current trip decisions and ranking.";
  if (!preview) return "This changes how your current matches are evaluated.";
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
  return "This changes how your current matches are evaluated.";
}
