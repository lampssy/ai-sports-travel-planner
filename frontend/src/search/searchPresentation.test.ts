import { describe, expect, test } from "vitest";

import type {
  RefinementPreview,
  SearchIntent,
  SearchWeatherEvidenceResponse,
  SearchV4Configuration,
  SearchV4RecommendationGroup,
} from "../types";
import {
  buildParsedChips,
  buildCandidateNarrative,
  decisionEvidencePresentation,
  evidenceQualityMode,
  factorLabelForConfiguration,
  formatAccess,
  formatTripEssential,
  refinementPreviewCopy,
  selectTripEssentialCategories,
  snowFitPresentation,
  snowFitLabel,
  technicalEvidenceDetails,
  terrainPresentation,
  weatherEvidencePresentation,
} from "./searchPresentation";

const baseIntent: SearchIntent = {
  constraints: {},
  party: { skill_levels: ["intermediate"] },
  travel_context: {},
  objectives: [],
  group_priorities: [],
  factor_preferences: [],
  assumptions: [],
};

function configuration(
  candidateId: string,
  updates: Partial<SearchV4Configuration> = {},
): SearchV4Configuration {
  return {
    candidate_id: candidateId,
    ski_region_id: `region-${candidateId}`,
    ski_region_name: `Region ${candidateId}`,
    stay_destination_id: `destination-${candidateId}`,
    stay_destination_name: `Destination ${candidateId}`,
    stay_base_id: `base-${candidateId}`,
    stay_base_name: `Base ${candidateId}`,
    ski_area_id: `area-${candidateId}`,
    ski_area_name: `Area ${candidateId}`,
    evidence_profile: "archive_backed",
    access: {
      ski_area_access_id: `access-${candidateId}`,
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: "Main lift",
      distance_m: 250,
      duration_minutes: 4,
      is_direct: true,
      relationship_trust_status: "verified",
      access_mode_distance_trust_status: "verified",
    },
    selected_pass: {
      lift_pass_product_id: `pass-${candidateId}`,
      name: `Pass ${candidateId}`,
      validity_scope: "regional",
      covered_ski_area_ids: [`area-${candidateId}`],
      accessible_piste_km: 300,
      accessible_piste_km_evidence: {
        trust_status: "verified",
        scope: "pass",
        source_entity_id: `pass-${candidateId}`,
        field_group: "pass_accessible_terrain",
      },
      price: {
        duration_days: 6,
        audience: "adult",
        amount: 426,
        amount_min: null,
        amount_max: null,
        currency: "EUR",
        price_kind: "fixed",
        season_label: "2026-2027",
      },
    },
    lodging_estimate: {
      mode: "lodging_nightly",
      minimum: 180,
      maximum: 255,
      currency: "EUR",
      trust_status: "estimated",
      provenance: "Catalog estimate.",
    },
    ranking_status: "ranked",
    fit_score: 82.4,
    groups: [],
    factors: [],
    constraint_warnings: [],
    ...updates,
  };
}

function group(candidate: SearchV4Configuration): SearchV4RecommendationGroup {
  return {
    ski_region_id: candidate.ski_region_id,
    ski_region_name: candidate.ski_region_name,
    rank: 1,
    fit_score: candidate.fit_score,
    top_configuration: candidate,
    alternative_configurations: [],
  };
}

describe("trip essentials", () => {
  test("prioritizes active intent categories and shares at most three across the top three", () => {
    const intent: SearchIntent = {
      ...baseIntent,
      constraints: {
        lodging_budget: {
          mode: "lodging_nightly",
          maximum: 320,
          currency: "EUR",
          budget_flex: 0.1,
        },
      },
      objectives: [{ factor_id: "pass_terrain_value", importance: "normal" }],
      factor_preferences: [
        {
          factor_id: "stay_base_access",
          mode: "prefer",
          values: ["near"],
          importance: "normal",
        },
      ],
    };
    const groups = ["a", "b", "c", "ignored"].map((id) =>
      group(configuration(id)),
    );

    expect(selectTripEssentialCategories(intent, groups)).toEqual([
      "passValue",
      "liftAccess",
      "lodging",
    ]);
  });

  test("uses the comparable default order and omits categories missing from a visible group", () => {
    const groups = [
      group(configuration("a")),
      group(
        configuration("b", {
          selected_pass: {
            ...configuration("b").selected_pass,
            price: null,
          },
        }),
      ),
      group(configuration("c")),
    ];

    expect(selectTripEssentialCategories(baseIntent, groups)).toEqual([
      "terrain",
      "liftAccess",
      "lodging",
    ]);
  });

  test("formats exact per-day price only with amount and duration and keeps ranges", () => {
    const exact = configuration("exact");
    expect(formatTripEssential("passValue", exact)?.value).toBe("EUR 71/day");

    const range = configuration("range", {
      selected_pass: {
        ...exact.selected_pass,
        price: {
          ...exact.selected_pass.price!,
          amount: null,
          amount_min: 360,
          amount_max: 480,
        },
      },
    });
    expect(formatTripEssential("passValue", range)?.value).toBe(
      "EUR 60-80/day",
    );

    const missingDuration = configuration("missing-duration", {
      selected_pass: {
        ...exact.selected_pass,
        price: { ...exact.selected_pass.price!, duration_days: 0 },
      },
    });
    expect(formatTripEssential("passValue", missingDuration)).toBeNull();
  });

  test("keeps estimate labels explicit and omits needs-source lodging", () => {
    expect(formatTripEssential("lodging", configuration("estimated"))?.value).toBe(
      "Estimated EUR 180-255/night",
    );
    expect(
      formatTripEssential(
        "lodging",
        configuration("needs-source", {
          lodging_estimate: {
            ...configuration("needs-source").lodging_estimate!,
            trust_status: "needs_source",
          },
        }),
      ),
    ).toBeNull();
  });

  test("keeps ski-area terrain fallback useful without claiming pass-wide coverage", () => {
    const estimatedTerrain = configuration("estimated-terrain", {
      selected_pass: {
        ...configuration("estimated-terrain").selected_pass,
        accessible_piste_km: 31,
        accessible_piste_km_evidence: {
          trust_status: "estimated",
          scope: "ski_area",
          source_entity_id: "pinzolo-ski-area",
          field_group: "terrain_metrics",
        },
      } as SearchV4Configuration["selected_pass"],
    });

    expect(formatTripEssential("terrain", estimatedTerrain)?.value).toBe(
      "About 31 km in the selected ski area",
    );
  });

  test("labels needs-source ski-area terrain at the field level", () => {
    const selectedPass = {
      ...configuration("needs-source-terrain").selected_pass,
      accessible_piste_km: 31,
      accessible_piste_km_evidence: {
        trust_status: "needs_source" as const,
        scope: "ski_area" as const,
        source_entity_id: "pinzolo-ski-area",
        field_group: "terrain_metrics" as const,
      },
    };

    expect(terrainPresentation(selectedPass)?.evidenceLabel).toBe(
      "31 km in the selected ski area; source confirmation is still needed",
    );
  });

  test("does not expose an unknown access-mode identifier", () => {
    const unknownAccess = configuration("unknown-access", {
      access: {
        ...configuration("unknown-access").access,
        access_mode: "future_internal_mode",
        distance_m: null,
        duration_minutes: null,
        is_direct: false,
        relationship_trust_status: "verified",
        access_mode_distance_trust_status: "estimated",
      },
    });

    expect(formatTripEssential("liftAccess", unknownAccess)).toBeNull();
  });
});

describe("snow fit label", () => {
  test.each([
    [undefined, "Not enough evidence"],
    [
      {
        factor_id: "trip_window_snow_fit",
        group_id: "trip_viability",
        direction: "prefer",
        raw_value: null,
        raw_utility: 0.9,
        neutral_utility: 0.5,
        effective_evidence_cap: 1,
        effective_utility: 0.75,
        effective_weight: 1,
        contribution_points: 10,
        evidence_cap_components: {},
        warnings: [],
        provenance_summary: "Historical evidence.",
        explanation_inputs: {},
      },
      "Strong fit",
    ],
    [
      {
        factor_id: "trip_window_snow_fit",
        group_id: "trip_viability",
        direction: "prefer",
        raw_value: null,
        raw_utility: 0.4,
        neutral_utility: 0.5,
        effective_evidence_cap: 1,
        effective_utility: 0.4,
        effective_weight: 1,
        contribution_points: -4,
        evidence_cap_components: {},
        warnings: [],
        provenance_summary: "Historical evidence.",
        explanation_inputs: {},
      },
      "Some concerns",
    ],
    [
      {
        factor_id: "trip_window_snow_fit",
        group_id: "trip_viability",
        direction: "prefer",
        raw_value: null,
        raw_utility: 0.8,
        neutral_utility: 0.5,
        effective_evidence_cap: 0,
        effective_utility: 0.8,
        effective_weight: 1,
        contribution_points: 0,
        evidence_cap_components: {},
        warnings: ["No archive data"],
        provenance_summary: "No evidence.",
        explanation_inputs: {},
      },
      "Not enough evidence",
    ],
  ] as const)("uses %s for the canonical public snow state", (factor, expected) => {
    const factors = factor
      ? [
          {
            ...factor,
            evidence_cap_components: { ...factor.evidence_cap_components },
            warnings: [...factor.warnings],
            explanation_inputs: { ...factor.explanation_inputs },
          },
        ]
      : [];
    expect(snowFitLabel(configuration("snow", { factors }))).toBe(expected);
  });
});

describe("snow fit presentation", () => {
  test.each([
    [
      { start_date: "2027-01-16", end_date: "2027-01-20" },
      "Snow fit for your dates",
      "Not enough evidence",
    ],
    [{ month: 3 }, "Snow fit for March", "Not enough evidence"],
    [undefined, "Add travel dates to assess snow fit", "Not assessed"],
  ] as const)("uses the applied travel window %o", (travelWindow, label, value) => {
    expect(
      snowFitPresentation(configuration("snow"), travelWindow),
    ).toEqual({ label, value });
  });

  test.each([
    [0.8, "Strong fit"],
    [0.4, "Some concerns"],
  ])("does not present %s without an applied travel window", (utility) => {
    const candidate = configuration("snow-without-window", {
      factors: [
        {
          factor_id: "trip_window_snow_fit",
          group_id: "trip_viability",
          direction: "prefer",
          raw_value: null,
          raw_utility: utility,
          neutral_utility: 0.5,
          effective_evidence_cap: 1,
          effective_utility: utility,
          effective_weight: 1,
          contribution_points: 10,
          evidence_cap_components: {},
          warnings: [],
          provenance_summary: "Historical snow evidence.",
          explanation_inputs: {},
        },
      ],
    });

    expect(snowFitPresentation(candidate, undefined)).toEqual({
      label: "Add travel dates to assess snow fit",
      value: "Not assessed",
    });
  });
});

describe("applied travel-window presentation", () => {
  test("shows response-shaped exact dates instead of treating month null as a month", () => {
    const chips = buildParsedChips({
      ...baseIntent,
      constraints: {
        travel_window: {
          month: null,
          start_date: "2027-01-16",
          end_date: "2027-01-20",
        },
      },
    });

    expect(chips).toContainEqual({
      id: "travel-window",
      label: "2027-01-16 to 2027-01-20",
      action: { kind: "travelWindow" },
    });
  });

  test("gives complete exact dates precedence when a response also contains a month", () => {
    const chips = buildParsedChips({
      ...baseIntent,
      constraints: {
        travel_window: {
          month: 3,
          start_date: "2027-01-16",
          end_date: "2027-01-20",
        },
      },
    });

    expect(chips).toContainEqual({
      id: "travel-window",
      label: "2027-01-16 to 2027-01-20",
      action: { kind: "travelWindow" },
    });
    expect(chips).not.toContainEqual(
      expect.objectContaining({ label: "March window" }),
    );
  });
});

describe("applied travel-origin presentation", () => {
  test("shows origin-driven travel ranking separately from a hard drive limit", () => {
    const chips = buildParsedChips({
      ...baseIntent,
      constraints: {
        travel_limit: { maximum_duration_hours: 15, mode: "car" },
      },
      travel_context: { origin_text: "Warsaw", mode: "car" },
    });

    expect(chips).toContainEqual({
      id: "travel-origin",
      label: "Prefer closer to Warsaw",
      action: { kind: "travelOrigin" },
    });
    expect(chips).toContainEqual({
      id: "travel-limit",
      label: "Max 15 hours by car",
      action: { kind: "travelLimit" },
    });
  });
});

describe("deterministic recommendation copy", () => {
  test("qualifies an accessible-terrain narrative to its ski-area evidence scope", () => {
    const candidate = configuration("bounded-terrain", {
      selected_pass: {
        ...configuration("bounded-terrain").selected_pass,
        accessible_piste_km: 31,
        accessible_piste_km_evidence: {
          trust_status: "estimated",
          scope: "ski_area",
          source_entity_id: "pinzolo-ski-area",
          field_group: "terrain_metrics",
        },
      },
      factors: [
        {
          factor_id: "accessible_terrain_scale",
          group_id: "ski_experience",
          direction: "prefer",
          raw_value: 31,
          raw_utility: 0.8,
          neutral_utility: 0.5,
          effective_evidence_cap: 0.65,
          effective_utility: 0.7,
          effective_weight: 1,
          contribution_points: 8,
          evidence_cap_components: {},
          warnings: [],
          provenance_summary: "Estimated ski-area terrain.",
          explanation_inputs: {},
        },
      ],
    });

    expect(buildCandidateNarrative(candidate)).toEqual({
      verdict: "A strong match for terrain in the selected ski area.",
      strength: "About 31 km in the selected ski area.",
    });
  });

  test("does not infer pass-wide terrain wording when terrain provenance is absent", () => {
    const candidate = configuration("missing-terrain-provenance", {
      selected_pass: {
        ...configuration("missing-terrain-provenance").selected_pass,
        accessible_piste_km: 31,
        accessible_piste_km_evidence: null,
      },
      factors: [
        {
          factor_id: "accessible_terrain_scale",
          group_id: "ski_experience",
          direction: "prefer",
          raw_value: 31,
          raw_utility: 0.8,
          neutral_utility: 0.5,
          effective_evidence_cap: 0.65,
          effective_utility: 0.7,
          effective_weight: 1,
          contribution_points: 8,
          evidence_cap_components: {},
          warnings: [],
          provenance_summary: "Terrain provenance is missing.",
          explanation_inputs: {},
        },
      ],
    });

    expect(factorLabelForConfiguration(candidate, "accessible_terrain_scale")).toBe(
      "Terrain scale",
    );
    expect(buildCandidateNarrative(candidate)).toEqual({
      verdict: "A strong terrain match.",
      strength: "Terrain scale contributes positively to this comparison.",
    });
  });

  test("uses approved factor copy without reading arbitrary factor JSON", () => {
    const candidate = configuration("copy", {
      factors: [
        {
          factor_id: "stay_base_access",
          group_id: "stay_practicality",
          direction: "prefer",
          raw_value: { secret: "DO NOT RENDER" },
          raw_utility: 0.9,
          neutral_utility: 0.5,
          effective_evidence_cap: 1,
          effective_utility: 0.9,
          effective_weight: 1,
          contribution_points: 12,
          evidence_cap_components: { secret: "DO NOT RENDER" },
          warnings: [],
          provenance_summary: "UNAPPROVED SERVER COPY",
          explanation_inputs: { secret: "DO NOT RENDER" },
        },
        {
          factor_id: "trip_window_snow_fit",
          group_id: "trip_viability",
          direction: "prefer",
          raw_value: null,
          raw_utility: 0.5,
          neutral_utility: 0.5,
          effective_evidence_cap: 0,
          effective_utility: 0.5,
          effective_weight: 1,
          contribution_points: 0,
          evidence_cap_components: {},
          warnings: ["UNAPPROVED WARNING"],
          provenance_summary: "UNAPPROVED SERVER COPY",
          explanation_inputs: {},
        },
      ],
    });

    expect(buildCandidateNarrative(candidate)).toEqual({
      verdict: "A practical lift-access match for this trip.",
      strength: "The recommended place to stay keeps lift access practical.",
      watchout: "Add travel dates to assess snow fit.",
    });
  });

  test.each([
    [{ month: 3 }, "Snow fit for March", "Strong snow fit for March."],
    [
      { start_date: "2027-01-16", end_date: "2027-01-20" },
      "Snow fit for your dates",
      "Strong snow fit for your dates.",
    ],
  ] as const)(
    "uses %s in a snow-led narrative",
    (travelWindow, snowLabel, expectedVerdict) => {
      const candidate = configuration("supported-snow-narrative", {
        factors: [
          {
            factor_id: "trip_window_snow_fit",
            group_id: "trip_viability",
            direction: "prefer",
            raw_value: null,
            raw_utility: 0.8,
            neutral_utility: 0.5,
            effective_evidence_cap: 1,
            effective_utility: 0.8,
            effective_weight: 1,
            contribution_points: 10,
            evidence_cap_components: {},
            warnings: [],
            provenance_summary: "Historical snow evidence.",
            explanation_inputs: {},
          },
        ],
      });

      expect(buildCandidateNarrative(candidate, travelWindow)).toEqual({
        verdict: expectedVerdict,
        strength: `${snowLabel}: Available snow evidence supports this travel window.`,
      });
    },
  );

  test("prompts for dates instead of assessing snow fit without a travel window", () => {
    const candidate = configuration("supported-snow-without-window", {
      factors: [
        {
          factor_id: "trip_window_snow_fit",
          group_id: "trip_viability",
          direction: "prefer",
          raw_value: null,
          raw_utility: 0.8,
          neutral_utility: 0.5,
          effective_evidence_cap: 1,
          effective_utility: 0.8,
          effective_weight: 1,
          contribution_points: 10,
          evidence_cap_components: {},
          warnings: [],
          provenance_summary: "Historical snow evidence.",
          explanation_inputs: {},
        },
      ],
    });

    expect(buildCandidateNarrative(candidate)).toEqual({
      verdict: "A complete trip option for comparison.",
      watchout: "Add travel dates to assess snow fit.",
    });
  });

  test.each([
    ["glacier_terrain", "Glacier terrain is available for this trip option."],
    ["snowmaking_availability", "Snowmaking is available for this trip option."],
  ])("states %s availability without claiming resilience", (factorId, strength) => {
    const candidate = configuration(factorId, {
      factors: [
        {
          factor_id: factorId,
          group_id: "ski_experience",
          direction: "prefer",
          raw_value: true,
          raw_utility: 1,
          neutral_utility: 0.5,
          effective_evidence_cap: 1,
          effective_utility: 1,
          effective_weight: 1,
          contribution_points: 12,
          evidence_cap_components: {},
          warnings: [],
          provenance_summary: "Catalog availability evidence.",
          explanation_inputs: {},
        },
      ],
    });

    expect(buildCandidateNarrative(candidate).strength).toBe(strength);
    expect(buildCandidateNarrative(candidate).strength).not.toMatch(/resilien/i);
  });

  test("qualifies or suppresses access strengths from non-verified catalog evidence", () => {
    const accessFactor = {
      factor_id: "stay_base_access",
      group_id: "stay_practicality",
      direction: "prefer" as const,
      raw_value: null,
      raw_utility: 0.9,
      neutral_utility: 0.5,
      effective_evidence_cap: 1,
      effective_utility: 0.9,
      effective_weight: 1,
      contribution_points: 12,
      evidence_cap_components: {},
      warnings: [],
      provenance_summary: "Catalog access evidence.",
      explanation_inputs: {},
    };
    const estimated = configuration("estimated-access", {
      access: {
        ...configuration("estimated-access").access,
        relationship_trust_status: "estimated",
        access_mode_distance_trust_status: "estimated",
      },
      factors: [accessFactor],
    });
    const needsSource = configuration("unsourced-access", {
      access: {
        ...configuration("unsourced-access").access,
        relationship_trust_status: "needs_source",
        access_mode_distance_trust_status: "needs_source",
      },
      factors: [accessFactor],
    });
    const adjusted = configuration("adjusted-access", {
      access: {
        ...configuration("adjusted-access").access,
        relationship_trust_status: "verified_with_adjustment",
        access_mode_distance_trust_status: "verified_with_adjustment",
      },
      factors: [accessFactor],
    });
    const missingEvidence = configuration("missing-access-evidence", {
      access: {
        ...configuration("missing-access-evidence").access,
        relationship_trust_status: "needs_source",
        access_mode_distance_trust_status: "needs_source",
      },
      factors: [{ ...accessFactor, effective_evidence_cap: 0 }],
    });

    expect(buildCandidateNarrative(estimated)).toEqual({
      verdict: "An estimated practical lift-access match for this trip.",
      strength:
        "Available estimates suggest Base estimated-access offers practical lift access.",
    });
    expect(buildCandidateNarrative(needsSource)).toEqual({
      verdict: "A complete trip option for comparison.",
    });
    expect(buildCandidateNarrative(adjusted)).toEqual({
      verdict: "A practical lift-access match based on estimated data.",
      strength:
        "Available source data suggests Base adjusted-access offers practical lift access.",
    });
    expect(buildCandidateNarrative(missingEvidence)).toEqual({
      verdict: "A complete trip option for comparison.",
      watchout: "Lift-access details need source verification.",
    });
  });

  test("uses the backend-owned evidence profile instead of factor internals", () => {
    const candidate = configuration("supported-snow", {
      evidence_profile: "forecast_assisted",
      factors: [
        {
          factor_id: "trip_window_snow_fit",
          group_id: "trip_viability",
          direction: "prefer",
          raw_value: { mode: "not-a-client-contract" },
          raw_utility: 0.8,
          neutral_utility: 0.5,
          effective_evidence_cap: 1,
          effective_utility: 0.8,
          effective_weight: 1,
          contribution_points: 10,
          evidence_cap_components: {},
          warnings: [],
          provenance_summary: "Not approved client copy.",
          explanation_inputs: {},
        },
      ],
    });

    expect(evidenceQualityMode(candidate)).toBe("forecastAssisted");
    expect(
      evidenceQualityMode(
        configuration("fallback", { evidence_profile: "fallback_heavy" }),
      ),
    ).toBe("fallbackHeavy");
  });

  test("does not expose unknown factor or group identifiers as context labels", () => {
    const intent: SearchIntent = {
      ...baseIntent,
      objectives: [
        { factor_id: "future_internal_factor", importance: "normal" },
      ],
      group_priorities: [
        { group_id: "future_internal_group", importance: "normal" },
      ],
      factor_preferences: [
        {
          factor_id: "future_internal_preference",
          mode: "prefer",
          values: ["future_internal_value"],
          importance: "normal",
        },
      ],
    };

    expect(buildParsedChips(intent).map((chip) => chip.label)).toEqual([
      "Intermediate",
    ]);
  });

  test("uses approved public labels for controlled preference values", () => {
    const intent: SearchIntent = {
      ...baseIntent,
      factor_preferences: [
        {
          factor_id: "development_style",
          mode: "prefer",
          values: ["planned_resort"],
          importance: "normal",
        },
        {
          factor_id: "base_type",
          mode: "prefer",
          values: ["village", "hamlet"],
          importance: "normal",
        },
      ],
    };

    expect(buildParsedChips(intent).map((chip) => chip.label)).toEqual([
      "Intermediate",
      "Place style: Purpose-built ski resort",
      "Place type: Village or hamlet",
    ]);
  });

  test("uses public labels for group-priority values", () => {
    const intent: SearchIntent = {
      ...baseIntent,
      group_priorities: [
        { group_id: "trip_viability", importance: "very_high" },
      ],
    };

    expect(buildParsedChips(intent)).toContainEqual({
      id: "group-trip_viability",
      label: "Trip timing: Highest priority",
      action: { kind: "group", id: "trip_viability" },
    });
    expect(
      buildParsedChips(intent).some((chip) => chip.label.includes("very_high")),
    ).toBe(false);
  });
});

describe("why this trip presentation", () => {
  test("builds bounded traveller-facing support without exposing internal provenance", () => {
    const candidate = configuration("why", {
      factors: [
        {
          factor_id: "trip_window_snow_fit",
          group_id: "trip_viability",
          direction: "prefer",
          raw_value: null,
          raw_utility: 0.82,
          neutral_utility: 0.5,
          effective_evidence_cap: 0.8,
          effective_utility: 0.76,
          effective_weight: 1,
          contribution_points: 10,
          evidence_cap_components: {},
          warnings: [],
          provenance_summary: "Catalog field-group evidence: verified_with_adjustment; 4 source reference(s).",
          explanation_inputs: {},
        },
        {
          factor_id: "party_skill_coverage",
          group_id: "ski_experience",
          direction: "prefer",
          raw_value: null,
          raw_utility: 0.9,
          neutral_utility: 0.5,
          effective_evidence_cap: 1,
          effective_utility: 0.9,
          effective_weight: 1,
          contribution_points: 12,
          evidence_cap_components: {},
          warnings: [],
          provenance_summary: "Catalog field-group evidence: verified_with_adjustment; 2 source reference(s).",
          explanation_inputs: {},
        },
      ],
    });

    const presentation = decisionEvidencePresentation(candidate, { month: 3 });
    const primaryCopy = JSON.stringify({
      supports: presentation.supports,
      uncertainties: presentation.uncertainties,
    });

    expect(presentation.supports).toHaveLength(4);
    expect(presentation.supports.map((item) => item.title)).toEqual([
      "Snow fit for March",
      "Skill match",
      "Terrain choice",
      "Lift access",
    ]);
    expect(primaryCopy).not.toMatch(/verified_with_adjustment|Catalog field-group|source reference|trip_window_snow_fit/);
    expect(presentation).not.toHaveProperty("technicalDetails");
  });

  test("states missing snow, pass coverage, and lodging evidence as uncertainties", () => {
    const candidate = configuration("uncertain", {
      selected_pass: {
        ...configuration("uncertain").selected_pass,
        accessible_piste_km: null,
        accessible_piste_km_evidence: null,
        price: null,
      },
      lodging_estimate: null,
      factors: [
        {
          factor_id: "trip_window_snow_fit",
          group_id: "trip_viability",
          direction: "prefer",
          raw_value: null,
          raw_utility: 0.5,
          neutral_utility: 0.5,
          effective_evidence_cap: 0,
          effective_utility: 0.5,
          effective_weight: 1,
          contribution_points: 0,
          evidence_cap_components: {},
          warnings: ["climatology unavailable"],
          provenance_summary: "No source references.",
          explanation_inputs: {},
        },
      ],
    });

    const presentation = decisionEvidencePresentation(candidate, { month: 3 });

    expect(presentation.uncertainties.map((item) => item.detail)).toEqual(
      expect.arrayContaining([
        "Snow evidence is limited for the requested travel window.",
        "Comparable pass-wide terrain coverage is not available yet.",
        "A comparable pass price is not available for this trip option.",
        "No stay-price estimate is available for this trip option.",
      ]),
    );
    expect(new Set(presentation.uncertainties.map((item) => item.detail)).size).toBe(
      presentation.uncertainties.length,
    );
  });

  test("does not present unverified lift access as positive evidence", () => {
    const candidate = configuration("unverified-access", {
      access: {
        ...configuration("unverified-access").access,
        relationship_trust_status: "estimated",
        access_mode_distance_trust_status: "needs_source",
      },
    });

    const presentation = decisionEvidencePresentation(candidate);

    expect(presentation.supports.map((item) => item.title)).not.toContain(
      "Lift access",
    );
    expect(presentation.uncertainties.map((item) => item.detail)).toContain(
      "Lift access from this place to stay still needs source verification.",
    );
    expect(formatTripEssential("liftAccess", candidate)).toBeNull();
    expect(formatAccess(candidate)).toBe(
      "Lift access needs source confirmation",
    );
    const technicalAccess = technicalEvidenceDetails(candidate).find(
      (item) => item.id === "catalog-access",
    );
    expect(technicalAccess).toMatchObject({
      evidenceLabel: "Source confirmation needed",
      provenance:
        "Source confirmation is still needed. The catalog links Base unverified-access to Area unverified-access. The lift-access mode and distance need verification.",
    });
    expect(JSON.stringify(technicalAccess)).not.toMatch(/Plan Maison|250 m/i);
  });
});

describe("weather evidence presentation", () => {
  function archiveResponse(): Extract<
    SearchWeatherEvidenceResponse,
    { status: "available" }
  > {
    return {
      weather_evidence_version: "search-weather-evidence-v1",
      status: "available",
      ski_area_id: "area-weather",
      evaluated_at: "2026-07-16T12:02:00Z",
      cache_valid_until: "2026-07-16T13:00:00Z",
      evidence: {
        mode: "climatology",
        window_label: "March",
        elevation_band: "mid_mountain",
        elevation_m: 2400,
        elevation_status: "exact",
        interpretation: "Historically reliable at mid-mountain in March.",
        limitations: [],
        historical: {
          source_label: "Open-Meteo archive climatology",
          source_model: "ERA5-Land",
          computed_at: "2026-07-15T02:00:00Z",
          baseline_start_year: 1995,
          baseline_end_year: 2024,
          evidence_seasons: 30,
          latest_archive_year: 2024,
          provenance_status: "homogeneous",
          sources: [
            {
              source_model: "ERA5-Land",
              computed_at: "2026-07-15T02:00:00Z",
              baseline_period: "normal_30y",
              baseline_start_year: 1995,
              baseline_end_year: 2024,
              evidence_seasons: 30,
              latest_archive_year: 2024,
              elevation_m: 2400,
              row_count: 1,
              profile_dates: ["03-15"],
            },
          ],
          snow_depth_cm_p25: 82,
          snow_depth_cm_p50: 128,
          snow_depth_cm_p75: 176,
          probability_snow_depth_ge_30cm: 0.87,
          average_daily_snowfall_cm: 4.2,
          average_max_temperature_c: -2.1,
          daily_profile: [
            {
              date_or_month_day: "03-15",
              snow_depth_cm: null,
              snow_depth_cm_p25: 82,
              snow_depth_cm_p50: 128,
              snow_depth_cm_p75: 176,
              snowfall_cm: 4.2,
              temperature_min_c: -8,
              temperature_max_c: -2.1,
              rain_risk: null,
              thaw_risk: 0.18,
              wind_gust_kmh: null,
            },
          ],
        },
        forecast: null,
      },
    };
  }

  test("keeps archive source, currency, coverage, conditions, and limitations separate", () => {
    const response = archiveResponse();
    const presentation = weatherEvidencePresentation(response);

    expect(presentation).toMatchObject({
      sourceType: "Historical pattern",
      sourceCurrency: "Archive through 2024; 1995-2024 baseline",
      coverage: "30 historical seasons; 1 profile date",
      expectedConditions:
        "Typical historical snow depth 128 cm (daily medians averaged across the window); typical fresh snow 4.2 cm/day; average high -2.1 °C",
      mainLimitation: "Historical patterns do not predict exact trip conditions.",
    });
    expect(JSON.stringify(presentation)).not.toContain(response.evaluated_at);
    expect(JSON.stringify(presentation)).not.toContain(response.cache_valid_until);
  });

  test("derives mixed historical timing and coverage from source rows", () => {
    const response = archiveResponse();
    response.evidence = {
      ...response.evidence,
      historical: {
        ...response.evidence.historical,
        baseline_start_year: null,
        baseline_end_year: null,
        evidence_seasons: null,
        latest_archive_year: null,
        provenance_status: "mixed",
        sources: [
          {
            ...response.evidence.historical.sources[0],
            baseline_start_year: 1995,
            baseline_end_year: 2024,
            evidence_seasons: 30,
            latest_archive_year: 2024,
          },
          {
            ...response.evidence.historical.sources[0],
            baseline_period: "recent_15y",
            baseline_start_year: 2009,
            baseline_end_year: 2023,
            evidence_seasons: 15,
            latest_archive_year: 2023,
          },
        ],
      },
    };

    expect(weatherEvidencePresentation(response)).toMatchObject({
      sourceCurrency: "Archives through 2023-2024; baseline years vary across sources",
      coverage: "15-30 historical seasons across sources; 1 profile date",
    });
  });

  test("uses forecast issue time and archive year for partial forecast currency", () => {
    const response = archiveResponse();
    response.evidence = {
      ...response.evidence,
      mode: "forecast_assisted",
      forecast: {
        source_label: "Open-Meteo forecast",
        source_model: "best_match",
        issued_at: "2026-07-16T11:00:00Z",
        provenance_status: "homogeneous",
        sources: [],
        coverage_status: "partial",
        usable_date_count: 2,
        requested_date_count: 3,
        average_forecast_share: 0.67,
        daily_profile: [
          {
            date_or_month_day: "2026-07-20",
            snow_depth_cm: 112,
            snow_depth_cm_p25: null,
            snow_depth_cm_p50: null,
            snow_depth_cm_p75: null,
            snowfall_cm: 7.4,
            temperature_min_c: -7,
            temperature_max_c: -1,
            rain_risk: 0.1,
            thaw_risk: 0.2,
            wind_gust_kmh: 46,
          },
        ],
      },
    };

    const presentation = weatherEvidencePresentation(response);

    expect(presentation).toMatchObject({
      sourceType: "Forecast and historical pattern",
      sourceCurrency:
        "Forecast issued Jul 16, 2026, 11:00 UTC; archive through 2024; 1995-2024 baseline",
      coverage: "2 of 3 requested dates have forecast values; 30 historical seasons",
      expectedConditions:
        "Forecast fresh snow 7.4 cm; forecast temperature range -7 to -1 °C; typical historical snow depth 128 cm (daily medians averaged across the window)",
      mainLimitation: "Forecast values are unavailable for 1 of 3 requested dates.",
    });
    expect(JSON.stringify(presentation)).not.toContain(response.evaluated_at);
    expect(JSON.stringify(presentation)).not.toContain(response.cache_valid_until);
  });

  test("promotes mixed forecast provenance at one elevation to the main limitation", () => {
    const response = archiveResponse();
    response.evidence = {
      ...response.evidence,
      mode: "forecast_assisted",
      limitations: ["Forecast coverage is incomplete."],
      forecast: {
        source_label: "Open-Meteo forecast",
        source_model: "best_match",
        issued_at: "2026-07-16T11:00:00Z",
        provenance_status: "mixed",
        sources: [],
        coverage_status: "complete",
        usable_date_count: 3,
        requested_date_count: 3,
        average_forecast_share: 1,
        daily_profile: [],
      },
    };

    expect(weatherEvidencePresentation(response).mainLimitation).toBe(
      "This assessment combines weather data from different sources.",
    );
  });

  test("promotes mixed historical provenance to the main limitation", () => {
    const response = archiveResponse();
    response.evidence = {
      ...response.evidence,
      limitations: ["Historical coverage is incomplete."],
      historical: {
        ...response.evidence.historical,
        provenance_status: "mixed",
      },
    };

    expect(weatherEvidencePresentation(response).mainLimitation).toBe(
      "This assessment combines weather data from different sources.",
    );
  });

  test("names both mixed source provenance and elevations in the main limitation", () => {
    const response = archiveResponse();
    response.evidence = {
      ...response.evidence,
      elevation_m: null,
      elevation_status: "mixed",
      limitations: ["Historical coverage is incomplete."],
      historical: {
        ...response.evidence.historical,
        provenance_status: "mixed",
      },
    };

    expect(weatherEvidencePresentation(response).mainLimitation).toBe(
      "This assessment combines weather data from different sources and elevations.",
    );
  });

  test("presents unavailable evidence without claiming the archive is absent", () => {
    const presentation = weatherEvidencePresentation({
      weather_evidence_version: "search-weather-evidence-v1",
      status: "unavailable",
      ski_area_id: "area-weather",
      evaluated_at: "2026-07-16T12:02:00Z",
      cache_valid_until: "2026-07-16T13:00:00Z",
      unavailable_reason: "historical_evidence_unavailable",
      limitations: ["No complete archive profile is available."],
    });

    expect(presentation.sourceType).toBe("Historical weather evidence unavailable");
    expect(presentation.sourceCurrency).toBe("Not available for this assessment.");
    expect(presentation.coverage).toBe(
      "No historical profile met Snowcast's evidence requirements for this trip window.",
    );
    expect(presentation.expectedConditions).toBe("Unavailable from the current evidence.");
    expect(presentation.mainLimitation).toBe("No complete archive profile is available.");
    expect(`${presentation.sourceCurrency} ${presentation.coverage}`).not.toMatch(/archive/i);
  });

  test("presents missing travel dates as an informational not-assessed state", () => {
    const presentation = weatherEvidencePresentation({
      weather_evidence_version: "search-weather-evidence-v1",
      status: "unavailable",
      ski_area_id: "area-weather",
      evaluated_at: "2026-07-16T12:02:00Z",
      cache_valid_until: "2026-07-16T13:00:00Z",
      unavailable_reason: "travel_window_missing",
      limitations: ["A travel month or exact travel dates are required."],
    });

    expect(presentation).toEqual({
      sourceType: "Travel dates needed",
      sourceCurrency: "Add travel dates to assess weather conditions.",
      coverage: "Weather coverage will be assessed after travel dates are added.",
      expectedConditions: "Choose travel dates to see weather conditions.",
      mainLimitation: "A travel month or exact travel dates are required.",
    });
  });
});

describe("refinement preview copy", () => {
  test.each<[string, RefinementPreview | null | undefined, string]>([
    [
      "movement",
      {
        top_rank_changes: [
          { ski_region_id: "region-a", previous_rank: 3, preview_rank: 2 },
        ],
        eligible_candidate_count_delta: 0,
      },
      "One result would move from #3 to #2.",
    ],
    [
      "entry",
      {
        top_rank_changes: [
          { ski_region_id: "region-a", previous_rank: null, preview_rank: 3 },
        ],
        eligible_candidate_count_delta: 0,
      },
      "One result would enter your top three.",
    ],
    [
      "exit",
      {
        top_rank_changes: [
          { ski_region_id: "region-a", previous_rank: 2, preview_rank: null },
        ],
        eligible_candidate_count_delta: 0,
      },
      "One result would leave your top three.",
    ],
    [
      "eligibility only",
      { top_rank_changes: [], eligible_candidate_count_delta: -4 },
      "This choice may change eligibility for 4 trip options.",
    ],
    [
      "absent",
      undefined,
      "This changes how your current matches are evaluated.",
    ],
  ])("formats %s preview", (_name, preview, expected) => {
    expect(refinementPreviewCopy(preview)).toBe(expected);
  });

  test("labels a baseline option without claiming a rerank", () => {
    expect(
      refinementPreviewCopy(
        { top_rank_changes: [], eligible_candidate_count_delta: 0 },
        false,
      ),
    ).toBe("Keeps your current trip decisions unchanged.");
  });
});
