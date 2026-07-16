import { describe, expect, test } from "vitest";

import type {
  RefinementPreview,
  SearchIntent,
  SearchV4Configuration,
  SearchV4RecommendationGroup,
} from "../types";
import {
  buildParsedChips,
  buildCandidateNarrative,
  evidenceQualityMode,
  factorLabelForConfiguration,
  formatTripEssential,
  refinementPreviewCopy,
  selectTripEssentialCategories,
  terrainPresentation,
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
    access: {
      ski_area_access_id: `access-${candidateId}`,
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: "Main lift",
      distance_m: 250,
      duration_minutes: 4,
      is_direct: true,
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
      "Estimated 31 km (ski area only)",
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
      "31 km in selected ski area (needs source); pass-wide coverage unresolved",
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
      },
    });

    expect(formatTripEssential("liftAccess", unknownAccess)).toBeNull();
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
      verdict: "A strong selected ski-area terrain match.",
      strength:
        "Estimated 31 km in selected ski area; pass-wide coverage needs source.",
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
      verdict: "A strong terrain scale match.",
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
      strength: "The selected stay base keeps lift access practical.",
      watchout: "Snow evidence is limited for the requested travel window.",
    });
  });

  test("does not infer archive or forecast mode from factor warning state", () => {
    const candidate = configuration("supported-snow", {
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

    expect(evidenceQualityMode(candidate)).toBeNull();
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
      "This choice may change eligibility for 4 trip configurations.",
    ],
    [
      "absent",
      undefined,
      "This answer can materially reorder your results",
    ],
  ])("formats %s preview", (_name, preview, expected) => {
    expect(refinementPreviewCopy(preview)).toBe(expected);
  });
});
