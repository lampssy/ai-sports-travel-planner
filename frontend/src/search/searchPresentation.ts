import type {
  CatalogTrustStatus,
  FactorPreferencePatch,
  GroupPriorityPatch,
  RefinementPreview,
  SearchIntent,
  SearchWeatherEvidenceResponse,
  SearchV4Configuration,
  SearchV4PassSummary,
  SearchV4RecommendationGroup,
  TravelWindow,
} from "../types";
import {
  catalogTrustStatusCopy,
  type EvidenceQualityMode,
} from "../ui/snowcastCopy";

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
  ["snowmaking_availability", "Snowmaking"],
  ["terrain_potential_scale", "Largest connected terrain"],
  ["lift_network_scale", "Large lift network"],
] as const;

export const factorLabels: Record<string, string> = {
  accessible_terrain_scale: "Terrain covered by your pass",
  party_skill_coverage: "Skiing level fit",
  terrain_potential_scale: "Connected ski area",
  lift_network_scale: "Lift access",
  marked_freeride_routes: "Marked freeride routes",
  snow_park: "Snow park",
  night_skiing: "Night skiing",
  glacier_terrain: "Glacier terrain",
  snowmaking_availability: "Snowmaking",
  stay_base_access: "Place to stay and lift access",
  pass_price_per_day: "Lift-pass price per day",
  pass_terrain_value: "Terrain for lift-pass price",
  ski_day_apres: "After-ski atmosphere",
  local_apres: "Evening atmosphere",
  local_pace: "Local pace",
  development_style: "Place style",
  base_type: "Place type",
  travel_effort: "Drive time and ease",
  trip_window_snow_fit: "Snow fit for your dates",
};

export const groupLabels: Record<string, string> = {
  trip_viability: "Trip timing",
  ski_experience: "Ski experience",
  stay_practicality: "Where you stay",
  value: "Value",
  character: "Character",
  travel_effort: "Drive time and ease",
};

const importanceLabels: Record<string, string> = {
  ignore: "Not a priority",
  secondary: "Lower priority",
  normal: "Balanced",
  important: "Important",
  primary: "Top priority",
  very_high: "Highest priority",
};

export function groupPriorityLabel(priority: GroupPriorityPatch): string | null {
  const groupLabel = groupLabels[priority.group_id];
  const importanceLabel = importanceLabels[priority.importance];
  return groupLabel && importanceLabel
    ? `${groupLabel}: ${importanceLabel}`
    : null;
}

const preferenceValueLabels: Record<string, string> = {
  "ski_day_apres:low_key": "Quiet",
  "ski_day_apres:moderate": "Some atmosphere",
  "ski_day_apres:lively": "Lively",
  "ski_day_apres:destination_defining": "A major après destination",
  "local_apres:low_key": "Quiet",
  "local_apres:moderate": "Some atmosphere",
  "local_apres:lively": "Lively",
  "local_apres:destination_defining": "A major après destination",
  "local_pace:quiet": "Quiet and relaxed",
  "local_pace:balanced": "Balanced",
  "local_pace:lively": "Lively",
  "development_style:traditional": "Traditional mountain village",
  "development_style:mixed": "A mix of old and new",
  "development_style:planned_resort": "Purpose-built ski resort",
  "base_type:town": "Ski town",
  "base_type:village|hamlet": "Village or hamlet",
  "base_type:resort_station": "Purpose-built resort base",
  "base_type:neighbourhood|resort_sector": "Resort neighborhood or area",
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

export interface ParsedChipPartitions {
  mustHaves: ParsedChip[];
  preferences: ParsedChip[];
}

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll("_", " ");
}

export function factorPreferenceLabel(
  preference: FactorPreferencePatch,
): string | null {
  const factorLabel = factorLabels[preference.factor_id];
  if (!factorLabel) return null;
  const valuesLabel = preferenceValueLabels[
    `${preference.factor_id}:${preference.values.join("|")}`
  ];
  if (valuesLabel) {
    const modePrefix =
      preference.mode === "prefer" ? "" : `${titleCase(preference.mode)} `;
    return `${modePrefix}${factorLabel}: ${valuesLabel}`;
  }
  return `${titleCase(preference.mode)} ${factorLabel}`;
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
    const tier =
      score >= 10 ? "Higher comfort" : score >= 6 ? "Standard comfort" : "Basic comfort";
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
      label: `Prefer ${label}`,
      action: { kind: "objective", id: item.factor_id },
    });
  }
  for (const item of intent.group_priorities) {
    const label = groupPriorityLabel(item);
    if (!label) continue;
    chips.push({
      id: `group-${item.group_id}`,
      label,
      action: { kind: "group", id: item.group_id },
    });
  }
  for (const item of intent.factor_preferences) {
    const label = factorPreferenceLabel(item);
    if (!label) continue;
    chips.push({
      id: `factor-${item.factor_id}`,
      label,
      action: { kind: "preference", id: item.factor_id },
    });
  }
  return chips;
}

export function partitionParsedChips(intent: SearchIntent): ParsedChipPartitions {
  const chips = buildParsedChips(intent);
  const requiredFactorIds = new Set(
    intent.factor_preferences
      .filter((preference) => preference.mode === "require")
      .map((preference) => preference.factor_id),
  );
  const mustHaves = chips.filter(
    (chip) =>
      [
        "location",
        "travelWindow",
        "lodgingBudget",
        "stayQuality",
        "travelLimit",
        "skill",
      ].includes(chip.action.kind) ||
      (chip.action.kind === "preference" && requiredFactorIds.has(chip.action.id)),
  );
  return {
    mustHaves,
    preferences: chips.filter((chip) => !mustHaves.includes(chip)),
  };
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
  if (trust === "estimated" || trust === "verified_with_adjustment") {
    return "About ";
  }
  return "";
}

function accessDescription(
  configuration: SearchV4Configuration,
): string | null {
  const { access } = configuration;
  const mode = accessModeLabels[access.access_mode];
  if (!mode) return null;
  const prefix = accessTrustPrefix(configuration);

  if (access.distance_m != null) {
    if (mode === "walk") return `${prefix}${access.distance_m} m walk to the lifts`;
    if (mode === "ski bus") return `${prefix}${access.distance_m} m to the ski bus`;
    return `${prefix}${access.distance_m} m ${mode} to the lifts`;
  }
  if (access.duration_minutes != null) {
    if (mode === "ski bus") return `${prefix}${access.duration_minutes} min by ski bus`;
    if (mode === "walk") return `${prefix}${access.duration_minutes} min walk to the lifts`;
    return `${prefix}${access.duration_minutes} min by ${mode}`;
  }
  if (access.is_direct || access.access_mode === "ski_in_ski_out") {
    return "Ski-in/ski-out access";
  }
  const distance = liftDistanceLabels[access.lift_distance];
  return distance ? `${distance} ${mode} to the lifts` : `${titleCase(mode)} to the lifts`;
}

export function formatAccess(configuration: SearchV4Configuration): string {
  if (accessTrustState(configuration) === "needs_source") {
    return "Lift access needs source confirmation";
  }
  return accessDescription(configuration) ?? "Lift access details are unavailable";
}

export function formatAccommodationAccessContext(
  configuration: SearchV4Configuration,
): string | null {
  if (accessTrustState(configuration) === "needs_source") return null;
  const { access } = configuration;
  const detail = accessDescription(configuration);
  if (!detail) return access.nearest_lift_name;
  return access.nearest_lift_name
    ? `${access.nearest_lift_name} - ${detail}`
    : detail;
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
  return catalogTrustStatusCopy[trustStatus].primary;
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

  const prefix = approximatePrefix(evidence.trust_status);
  const needsSource = evidence.trust_status === "needs_source";
  const sourceQualifier = needsSource
    ? "; source confirmation is still needed"
    : "";

  if (evidence.scope === "ski_area") {
    const value = `${prefix}${kilometres} km in the selected ski area${sourceQualifier}`;
    return {
      essentialValue: value,
      evidenceLabel: value,
    };
  }
  if (evidence.scope === "terrain_domain") {
    const value = `${prefix}${kilometres} km in the connected area covered by this pass${sourceQualifier}`;
    return {
      essentialValue: value,
      evidenceLabel: value,
    };
  }
  const value = `${prefix}${kilometres} km covered by this pass${sourceQualifier}`;
  return {
    essentialValue: value,
    evidenceLabel: value,
  };
}

export function factorLabelForConfiguration(
  configuration: SearchV4Configuration,
  factorId: string,
  travelWindow?: TravelWindow,
): string | undefined {
  if (factorId === "trip_window_snow_fit") {
    return snowFitPresentation(configuration, travelWindow).label;
  }
  if (factorId !== "accessible_terrain_scale") return factorLabels[factorId];
  const scope = configuration.selected_pass.accessible_piste_km_evidence?.scope;
  if (scope === "ski_area") return "Terrain in the selected ski area";
  if (scope === "terrain_domain") return "Connected terrain covered by this pass";
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
      return "Based on source data";
    case "verified_with_adjustment":
      return "Estimated from source data";
    case "estimated":
      return "Estimated from catalog data";
    case "needs_source":
      return "Source confirmation needed";
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

function approximatePrefix(
  trust: "verified" | "verified_with_adjustment" | "estimated" | "needs_source",
): string {
  return trust === "estimated" || trust === "verified_with_adjustment"
    ? "About "
    : "";
}

function trustProvenance(
  trust: CatalogTrustStatus,
): string {
  return catalogTrustStatusCopy[trust].technical;
}

const catalogTrustStatuses = [
  "verified",
  "verified_with_adjustment",
  "estimated",
  "needs_source",
] as const satisfies readonly CatalogTrustStatus[];

function trustStatusFromProvenance(provenance: string): CatalogTrustStatus | null {
  return (
    catalogTrustStatuses.find((status) =>
      new RegExp(`\\b${status}\\b`, "i").test(provenance),
    ) ?? null
  );
}

function technicalProvenance(provenance: string): string {
  const trust = trustStatusFromProvenance(provenance);
  if (!trust) return provenance;

  const detail = provenance
    .replace(new RegExp(`\\b${trust}\\b`, "i"), "")
    .replace(/:\s*;/g, ";")
    .replace(/[:;,]\s*\./g, ".")
    .replace(/\s{2,}/g, " ")
    .trim();

  return detail ? `${trustProvenance(trust)} ${detail}` : trustProvenance(trust);
}

function accessProvenance(configuration: SearchV4Configuration): string {
  const { access } = configuration;
  const details = [trustProvenance(accessTrustState(configuration))];

  details.push(
    access.relationship_trust_status === "needs_source"
      ? `The link between ${configuration.stay_base_name} and ${configuration.ski_area_name} needs verification.`
      : `The catalog links ${configuration.stay_base_name} to ${configuration.ski_area_name}.`,
  );

  if (access.access_mode_distance_trust_status === "needs_source") {
    details.push("The lift-access mode and distance need verification.");
  } else if (
    access.relationship_trust_status !== "needs_source" &&
    access.nearest_lift_name
  ) {
    details.push(`Nearest lift: ${access.nearest_lift_name}.`);
  }

  return details.join(" ");
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
  if (accessTrustState(configuration) === "needs_source") return null;
  return accessDescription(configuration);
}

function lodgingValue(configuration: SearchV4Configuration): string | null {
  const estimate = configuration.lodging_estimate;
  if (!estimate || estimate.trust_status === "needs_source") return null;
  const prefix =
    estimate.trust_status === "estimated" ||
    estimate.trust_status === "verified_with_adjustment"
      ? "Estimated "
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
  accessible_terrain_scale: "Terrain scale compares well with the other matches.",
  party_skill_coverage: "The selected terrain supports your party's skill mix.",
  terrain_potential_scale: "The ski region offers wider terrain.",
  lift_network_scale: "The lift network supports varied ski-day plans.",
  glacier_terrain: "Glacier terrain is available for this trip option.",
  snowmaking_availability: "Snowmaking is available for this trip option.",
  stay_base_access: "The recommended place to stay keeps lift access practical.",
  pass_price_per_day: "The selected pass offers competitive daily value.",
  pass_terrain_value: "The selected pass balances terrain access and price.",
  travel_effort: "The route keeps travel effort within the requested plan.",
  trip_window_snow_fit: "Available snow evidence supports your requested travel dates.",
};

const watchoutCopy: Record<string, string> = {
  accessible_terrain_scale: "Terrain-scale evidence is limited for this pass.",
  party_skill_coverage: "Some terrain may not suit every skier in your group.",
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

function supportedVerdict(
  configuration: SearchV4Configuration,
  factorId: string,
  travelWindow?: TravelWindow,
): string {
  if (factorId === "trip_window_snow_fit") {
    const label = snowFitPresentation(configuration, travelWindow).label.replace(
      /^Snow/,
      "snow",
    );
    return `Strong ${label}.`;
  }
  if (factorId === "accessible_terrain_scale") {
    switch (configuration.selected_pass.accessible_piste_km_evidence?.scope) {
      case "ski_area":
        return "Matches terrain in the selected ski area.";
      case "terrain_domain":
        return "Matches connected terrain covered by this pass.";
      case "pass":
        return "Matches terrain covered by this pass.";
      default:
        return "Terrain compares well with the other matches.";
    }
  }
  const verdicts: Record<string, string> = {
    party_skill_coverage: "Matches your group's skiing level.",
    terrain_potential_scale: "The ski region offers wider terrain.",
    lift_network_scale: "The lift network supports varied ski-day plans.",
    glacier_terrain: "Glacier terrain is available for this trip option.",
    snowmaking_availability: "Snowmaking is available for this trip option.",
    pass_price_per_day: "The lift-pass price compares well with the other matches.",
    pass_terrain_value: "Terrain and lift-pass value compare well with the other matches.",
    travel_effort: "The route fits a shorter or easier journey.",
  };
  return verdicts[factorId] ?? "This trip compares well with the other matches.";
}

function supportedStrength(
  configuration: SearchV4Configuration,
  factorId: string,
): string {
  if (factorId === "terrain_potential_scale") {
    return `${configuration.ski_region_name} offers wider terrain; a different or additional pass may be needed.`;
  }
  return strengthCopy[factorId];
}

export interface CandidateNarrative {
  verdict: string;
  strength?: string;
  watchout?: string;
  watchoutEvidenceId?: DecisionEvidenceId;
}

export type DecisionEvidenceId =
  | "snow-window"
  | "skill-match"
  | "terrain"
  | "lift-access"
  | "pass-price"
  | "lodging"
  | "constraints";

export interface DecisionEvidencePresentation {
  supports: Array<{ id: DecisionEvidenceId; title: string; detail: string }>;
  uncertainties: Array<{ id: DecisionEvidenceId; detail: string }>;
}

export interface TechnicalEvidenceDetail {
  id: string;
  label: string;
  provenance: string;
  evidenceLabel: string;
}

export interface WeatherEvidencePresentation {
  sourceType: string;
  sourceCurrency: string;
  coverage: string;
  expectedConditions: string;
  mainLimitation: string;
}

const weatherDateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "UTC",
});

function formatWeatherDateTime(value: string): string {
  return weatherDateTimeFormatter.format(new Date(value));
}

function historicalArchiveCurrency(
  historical: Extract<
    SearchWeatherEvidenceResponse,
    { status: "available" }
  >["evidence"]["historical"],
): string {
  const parts: string[] = [];
  if (historical.latest_archive_year != null) {
    parts.push(`archive through ${historical.latest_archive_year}`);
  } else {
    const archiveYears = [...new Set(
      historical.sources
        .map((source) => source.latest_archive_year)
        .filter((year): year is number => year != null),
    )].sort((left, right) => left - right);
    if (archiveYears.length === 1) {
      parts.push(`archive through ${archiveYears[0]}`);
    } else if (archiveYears.length > 1) {
      parts.push(
        `archives through ${archiveYears[0]}-${archiveYears[archiveYears.length - 1]}`,
      );
    }
  }
  if (
    historical.baseline_start_year != null &&
    historical.baseline_end_year != null
  ) {
    parts.push(
      `${historical.baseline_start_year}-${historical.baseline_end_year} baseline`,
    );
  } else {
    const baselineYears = new Set(
      historical.sources.map(
        (source) => `${source.baseline_start_year}-${source.baseline_end_year}`,
      ),
    );
    if (baselineYears.size === 1) {
      parts.push(`${[...baselineYears][0]} baseline`);
    } else if (baselineYears.size > 1) {
      parts.push("baseline years vary across sources");
    }
  }
  return parts.length ? parts.join("; ") : "archive year and baseline unavailable";
}

function historicalSeasonCoverage(
  historical: Extract<
    SearchWeatherEvidenceResponse,
    { status: "available" }
  >["evidence"]["historical"],
): string {
  if (historical.evidence_seasons != null) {
    return `${historical.evidence_seasons} historical seasons`;
  }
  const seasons = [...new Set(historical.sources.map((source) => source.evidence_seasons))]
    .sort((left, right) => left - right);
  if (seasons.length === 1) return `${seasons[0]} historical seasons`;
  return `${seasons[0]}-${seasons[seasons.length - 1]} historical seasons across sources`;
}

function formatWeatherMetric(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function forecastConditions(
  response: Extract<SearchWeatherEvidenceResponse, { status: "available" }>,
): string {
  const forecast = response.evidence.forecast;
  if (!forecast) return "Forecast conditions are unavailable.";
  const snowfall = forecast.daily_profile
    .map((point) => point.snowfall_cm)
    .filter((value): value is number => value != null);
  const minimums = forecast.daily_profile
    .map((point) => point.temperature_min_c)
    .filter((value): value is number => value != null);
  const maximums = forecast.daily_profile
    .map((point) => point.temperature_max_c)
    .filter((value): value is number => value != null);
  const parts: string[] = [];
  if (snowfall.length) {
    parts.push(
      `Forecast fresh snow ${formatWeatherMetric(
        snowfall.reduce((total, value) => total + value, 0),
      )} cm`,
    );
  }
  if (minimums.length || maximums.length) {
    const lower = minimums.length ? Math.min(...minimums) : Math.min(...maximums);
    const upper = maximums.length ? Math.max(...maximums) : Math.max(...minimums);
    parts.push(
      `forecast temperature range ${formatWeatherMetric(lower)} to ${formatWeatherMetric(upper)} °C`,
    );
  }
  if (response.evidence.historical.snow_depth_cm_p50 != null) {
    parts.push(
      `typical historical snow depth ${formatWeatherMetric(
        response.evidence.historical.snow_depth_cm_p50,
      )} cm`,
    );
  }
  return parts.length
    ? parts.join("; ")
    : "No forecast condition values are available for the requested dates.";
}

function mainWeatherLimitation(
  response: Extract<SearchWeatherEvidenceResponse, { status: "available" }>,
): string {
  const { evidence } = response;
  const { historical, forecast } = evidence;
  const hasMixedProvenance =
    historical.provenance_status === "mixed" ||
    forecast?.provenance_status === "mixed";
  if (evidence.elevation_status === "mixed" && hasMixedProvenance) {
    return "This assessment combines weather data from different sources and elevations.";
  }
  if (evidence.elevation_status === "mixed") {
    return "This assessment combines weather data from different elevations.";
  }
  if (hasMixedProvenance) {
    return "This assessment combines weather data from different sources.";
  }
  if (evidence.limitations[0]) return evidence.limitations[0];

  if (evidence.mode === "forecast_assisted" && forecast) {
    const missingDates = Math.max(
      0,
      forecast.requested_date_count - forecast.usable_date_count,
    );
    return missingDates > 0
      ? `Forecast values are unavailable for ${missingDates} of ${forecast.requested_date_count} requested dates.`
      : "Forecast conditions can still change before travel.";
  }

  return "Historical patterns do not predict exact trip conditions.";
}

export function weatherEvidencePresentation(
  response: SearchWeatherEvidenceResponse,
): WeatherEvidencePresentation {
  if (response.status === "unavailable") {
    if (response.unavailable_reason === "travel_window_missing") {
      return {
        sourceType: "Travel dates needed",
        sourceCurrency: "Add travel dates to assess weather conditions.",
        coverage: "Weather coverage will be assessed after travel dates are added.",
        expectedConditions: "Choose travel dates to see weather conditions.",
        mainLimitation:
          response.limitations[0] ?? "Add travel dates to assess weather conditions.",
      };
    }
    return {
      sourceType: "Historical weather evidence unavailable",
      sourceCurrency: "Not available for this assessment.",
      coverage:
        "No historical profile met Snowcast's evidence requirements for this trip window.",
      expectedConditions: "Unavailable from the current evidence.",
      mainLimitation:
        response.limitations[0] ??
        "No complete historical profile is available for this trip window.",
    };
  }

  const { historical, forecast } = response.evidence;
  const archive = historicalArchiveCurrency(historical);
  const seasonCoverage = historicalSeasonCoverage(historical);
  if (response.evidence.mode === "forecast_assisted" && forecast) {
    return {
      sourceType: "Forecast and historical pattern",
      sourceCurrency: [
        forecast.issued_at
          ? `Forecast issued ${formatWeatherDateTime(forecast.issued_at)} UTC`
          : "Forecast issue time unavailable",
        archive,
      ].join("; "),
      coverage: `${forecast.usable_date_count} of ${forecast.requested_date_count} requested dates have forecast values; ${seasonCoverage}`,
      expectedConditions: forecastConditions(response),
      mainLimitation: mainWeatherLimitation(response),
    };
  }

  const historicalConditions = [
    historical.snow_depth_cm_p50 == null
      ? null
      : `Typical historical snow depth ${formatWeatherMetric(
          historical.snow_depth_cm_p50,
        )} cm`,
    historical.average_daily_snowfall_cm == null
      ? null
      : `typical fresh snow ${formatWeatherMetric(
          historical.average_daily_snowfall_cm,
        )} cm/day`,
    historical.average_max_temperature_c == null
      ? null
      : `average high ${formatWeatherMetric(
          historical.average_max_temperature_c,
        )} °C`,
  ].filter((value): value is string => value != null);
  const profileDateCount = historical.daily_profile.length;
  return {
    sourceType: "Historical pattern",
    sourceCurrency: archive.charAt(0).toUpperCase() + archive.slice(1),
    coverage: `${seasonCoverage}; ${profileDateCount} profile ${profileDateCount === 1 ? "date" : "dates"}`,
    expectedConditions: historicalConditions.length
      ? historicalConditions.join("; ")
      : "No historical condition values are available for this trip window.",
    mainLimitation: mainWeatherLimitation(response),
  };
}

function hasAppliedTravelWindow(travelWindow?: TravelWindow): boolean {
  return Boolean(
    (travelWindow?.start_date && travelWindow.end_date) ||
      typeof travelWindow?.month === "number",
  );
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
  travelWindow?: TravelWindow,
): DecisionEvidencePresentation {
  const supports: DecisionEvidencePresentation["supports"] = [];
  const uncertainties: DecisionEvidencePresentation["uncertainties"] = [];
  const addSupport = (id: DecisionEvidenceId, title: string, detail: string) => {
    supports.push({ id, title, detail });
  };
  const addUncertainty = (id: DecisionEvidenceId, detail: string) => {
    if (!uncertainties.some((item) => item.detail === detail)) {
      uncertainties.push({ id, detail });
    }
  };

  const snowFactor = configuration.factors.find(
    (item) => item.factor_id === "trip_window_snow_fit",
  );
  if (hasAppliedTravelWindow(travelWindow) && supportedFactor(configuration, "trip_window_snow_fit")) {
    addSupport(
      "snow-window",
      snowFitPresentation(configuration, travelWindow).label,
      "Available snow evidence supports the requested travel window.",
    );
  } else if (
    hasAppliedTravelWindow(travelWindow) &&
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
      terrain.essentialValue,
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
      `${configuration.stay_base_name}: ${access}`,
    );
  } else if (accessNeedsSource) {
    addUncertainty(
      "lift-access",
      "Lift access from this place to stay still needs source verification.",
    );
  } else {
    addUncertainty(
      "lift-access",
      "Lift access may require additional local travel from the recommended place to stay.",
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
      "A comparable pass price is not available for this trip option.",
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
      "No stay-price estimate is available for this trip option.",
    );
  }

  if (configuration.constraint_warnings.length > 0) {
    addUncertainty(
      "constraints",
      "One or more trip constraints rely on limited supporting data.",
    );
  }

  return {
    supports: supports.slice(0, 4),
    uncertainties,
  };
}

export function technicalEvidenceDetails(
  configuration: SearchV4Configuration,
  travelWindow?: TravelWindow,
): TechnicalEvidenceDetail[] {
  const terrain = terrainPresentation(configuration.selected_pass);
  const technicalDetails: TechnicalEvidenceDetail[] =
    configuration.factors
      .filter((factor) => factorLabels[factor.factor_id] && factor.provenance_summary)
      .map((factor) => ({
        id: `factor-${factor.factor_id}`,
        label:
          factorLabelForConfiguration(configuration, factor.factor_id, travelWindow) ??
          "Ranking factor",
        provenance: technicalProvenance(factor.provenance_summary),
        evidenceLabel:
          factor.effective_evidence_cap > 0 ? "Supported" : "Limited evidence",
      }));

  const accessTrust = accessTrustState(configuration);
  technicalDetails.push(
    accessTrust === "needs_source"
      ? {
          id: "catalog-access",
          label: "Place to stay and lift access",
          provenance: accessProvenance(configuration),
          evidenceLabel: "Source confirmation needed",
        }
      : {
          id: "catalog-access",
          label: "Place to stay and lift access",
          provenance: accessProvenance(configuration),
          evidenceLabel:
            configuration.access.distance_m != null
              ? `${accessTrustPrefix(configuration)}${configuration.access.distance_m} m`
              : trustProvenance(accessTrust).replace(/\.$/, ""),
        },
  );
  const terrainTrust = configuration.selected_pass.accessible_piste_km_evidence?.trust_status;
  technicalDetails.push({
    id: "selected-pass",
    label: "Selected pass",
    provenance: terrainTrust
      ? `${trustProvenance(terrainTrust)} ${configuration.selected_pass.name} is the pass used for this trip.`
      : `${configuration.selected_pass.name} is the pass used for this trip.`,
    evidenceLabel: terrain?.evidenceLabel ?? "Coverage unresolved",
  });
  if (configuration.lodging_estimate?.provenance) {
      technicalDetails.push({
        id: "lodging-estimate",
        label: "Lodging estimate",
        provenance: technicalProvenance(configuration.lodging_estimate.provenance),
        evidenceLabel: "Place to stay estimate",
      });
  }

  return technicalDetails;
}

export function buildCandidateNarrative(
  configuration: SearchV4Configuration,
  travelWindow?: TravelWindow,
): CandidateNarrative {
  const accessTrust = accessTrustState(configuration);
  const hasTravelWindow = hasAppliedTravelWindow(travelWindow);
  const snowPromptRequired =
    !hasTravelWindow &&
    configuration.factors.some((factor) => factor.factor_id === "trip_window_snow_fit");
  const supported = configuration.factors
    .filter(
      (factor) =>
        strengthCopy[factor.factor_id] &&
        factor.effective_evidence_cap > 0 &&
        factor.effective_utility > factor.neutral_utility &&
        !(
          factor.factor_id === "stay_base_access" &&
          accessTrust === "needs_source"
        ) &&
        (factor.factor_id !== "trip_window_snow_fit" || hasTravelWindow),
    )
    .sort((left, right) => right.effective_utility - left.effective_utility)[0];
  const caution = configuration.factors.find(
    (factor) =>
      watchoutCopy[factor.factor_id] &&
      (factor.factor_id !== "trip_window_snow_fit" || hasTravelWindow) &&
      (factor.effective_evidence_cap === 0 || factor.warnings.length > 0),
  );
  const supportedTerrain =
    supported?.factor_id === "accessible_terrain_scale"
      ? terrainPresentation(configuration.selected_pass)
      : null;
  const watchout = snowPromptRequired
    ? "Add travel dates to assess snow fit."
    : caution
    ? caution.factor_id === "stay_base_access" && accessTrust === "needs_source"
      ? "Lift-access details need source verification."
      : caution.factor_id === "trip_window_snow_fit"
        ? `${snowFitPresentation(configuration, travelWindow).label}: Snow evidence is limited for this travel window.`
      : watchoutCopy[caution.factor_id]
    : undefined;
  const verdict = supported
    ? supported.factor_id === "stay_base_access"
      ? accessTrust === "estimated"
        ? "An estimated practical lift-access match for this trip."
        : accessTrust === "verified_with_adjustment"
          ? "A practical lift-access match based on estimated data."
          : "A practical lift-access match for this trip."
      : supportedVerdict(configuration, supported.factor_id, travelWindow)
    : "A complete trip option for comparison.";
  return {
    verdict,
    ...(supported
      ? {
          strength: supportedTerrain
            ? `${supportedTerrain.evidenceLabel}.`
            : supported.factor_id === "stay_base_access"
              ? accessTrust === "estimated"
                ? `Available estimates suggest ${configuration.stay_base_name} offers practical lift access.`
                : accessTrust === "verified_with_adjustment"
                  ? `Available source data suggests ${configuration.stay_base_name} offers practical lift access.`
                  : strengthCopy[supported.factor_id]
              : supported.factor_id === "trip_window_snow_fit"
                ? `${snowFitPresentation(configuration, travelWindow).label}: Available snow evidence supports this travel window.`
              : supportedStrength(configuration, supported.factor_id),
        }
      : {}),
    ...(watchout ? { watchout } : {}),
    ...(caution?.factor_id === "trip_window_snow_fit"
      ? { watchoutEvidenceId: "snow-window" as const }
      : {}),
  };
}

export function snowFitLabel(configuration: SearchV4Configuration): string {
  const factor = configuration.factors.find(
    (item) => item.factor_id === "trip_window_snow_fit",
  );
  if (!factor || factor.effective_evidence_cap === 0) return "Not enough evidence";
  if (factor.effective_utility >= 0.75) return "Strong fit";
  return "Some concerns";
}

export function snowFitPresentation(
  configuration: SearchV4Configuration,
  travelWindow: TravelWindow | undefined,
): { label: string; value: string } {
  const hasExactDates = Boolean(travelWindow?.start_date && travelWindow?.end_date);
  if (!hasAppliedTravelWindow(travelWindow)) {
    return {
      label: "Add travel dates to assess snow fit",
      value: "Not assessed",
    };
  }
  const label = hasExactDates
    ? "Snow fit for your dates"
    : typeof travelWindow?.month === "number"
      ? `Snow fit for ${monthName(travelWindow.month)}`
      : "Snow fit for your dates";
  return { label, value: snowFitLabel(configuration) };
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
  if (!intentChanged) return "Keeps your current trip decisions unchanged.";
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
    const count = Math.abs(preview.eligible_candidate_count_delta);
    return `This choice may change ${count} possible ${count === 1 ? "match" : "matches"}.`;
  }
  return "This changes how your current matches are evaluated.";
}

export function tripOptionCountCopy(count: number): string {
  return `${count} trip ${count === 1 ? "option matches" : "options match"} your must-haves`;
}
