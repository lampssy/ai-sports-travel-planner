import { createElement } from "react";
import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { SearchV4Configuration } from "../types";
import { evidenceQualityCopy, initialHeroCopy } from "../ui/snowcastCopy";
import { AccommodationHandoff } from "./AccommodationHandoff";
import {
  buildCandidateNarrative,
  decisionEvidencePresentation,
  formatTripEssential,
  lodgingTrustLabel,
  terrainPresentation,
} from "./searchPresentation";

const INTERNAL_PRIMARY_PHRASES = [
  "adjusted walk",
  "selected pass context",
  "covered terrain domain",
  "uncertainty kept explicit",
  "closer terrain review",
  "fallback-heavy",
  "backend api",
  "verified with adjustment",
  "needs source",
];

function configuration(): SearchV4Configuration {
  return {
    candidate_id: "ischgl",
    ski_region_id: "ischgl",
    ski_region_name: "Ischgl",
    stay_destination_id: "ischgl",
    stay_destination_name: "Ischgl",
    stay_base_id: "ischgl-centre",
    stay_base_name: "Ischgl",
    ski_area_id: "ischgl-ski-area",
    ski_area_name: "Ischgl",
    evidence_profile: "fallback_heavy",
    access: {
      ski_area_access_id: "ischgl-access",
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: "Silvrettabahn",
      distance_m: 324,
      duration_minutes: null,
      is_direct: false,
      relationship_trust_status: "verified_with_adjustment",
      access_mode_distance_trust_status: "verified_with_adjustment",
    },
    selected_pass: {
      lift_pass_product_id: "ischgl-pass",
      name: "Ischgl/Samnaun VIP Skipass",
      validity_scope: "regional",
      covered_ski_area_ids: ["ischgl-ski-area"],
      accessible_piste_km: 239,
      accessible_piste_km_evidence: {
        trust_status: "verified_with_adjustment",
        scope: "terrain_domain",
        source_entity_id: "ischgl-domain",
        field_group: "terrain_metrics",
      },
      price: {
        duration_days: 6,
        audience: "adult",
        amount: 385,
        amount_min: null,
        amount_max: null,
        currency: "EUR",
        price_kind: "fixed",
        season_label: "2026-2027",
      },
    },
    lodging_estimate: null,
    ranking_status: "ranked",
    fit_score: 62.9,
    groups: [],
    factors: [
      {
        factor_id: "party_skill_coverage",
        group_id: "ski_experience",
        direction: "prefer",
        raw_value: null,
        raw_utility: 0.5,
        neutral_utility: 0.5,
        effective_evidence_cap: 0,
        effective_utility: 0.5,
        effective_weight: 1,
        contribution_points: 0,
        evidence_cap_components: {},
        warnings: ["limited terrain detail"],
        provenance_summary: "Terrain coverage from the catalog.",
        explanation_inputs: {},
      },
    ],
    constraint_warnings: [],
  };
}

describe("content language contracts", () => {
  test("uses public trip-option language in the initial search copy", () => {
    expect(initialHeroCopy.body).toContain("Trip options");
    expect(initialHeroCopy.body).toContain("snow fit for your dates");
    expect(initialHeroCopy.body.toLowerCase()).not.toContain("ranks ski resorts");
  });

  test("keeps internal language out of primary recommendation copy", () => {
    const candidate = configuration();
    const terrain = terrainPresentation(candidate.selected_pass);
    const primaryCopy = [
      terrain?.essentialValue,
      terrain?.evidenceLabel,
      formatTripEssential("liftAccess", candidate)?.value,
      buildCandidateNarrative(candidate).watchout,
      ...decisionEvidencePresentation(candidate).supports.map((item) => item.detail),
      ...decisionEvidencePresentation(candidate).uncertainties.map((item) => item.detail),
      evidenceQualityCopy.fallbackHeavy.label,
      lodgingTrustLabel("verified_with_adjustment"),
      lodgingTrustLabel("needs_source"),
    ]
      .filter((value): value is string => Boolean(value))
      .join(" ")
      .toLowerCase();

    for (const phrase of INTERNAL_PRIMARY_PHRASES) {
      expect(primaryCopy).not.toContain(phrase);
    }
  });

  test("uses plain lodging evidence statuses", () => {
    expect([
      lodgingTrustLabel("verified"),
      lodgingTrustLabel("verified_with_adjustment"),
      lodgingTrustLabel("estimated"),
      lodgingTrustLabel("needs_source"),
    ]).toEqual([
      "Based on source data",
      "Estimated from source data for this trip",
      "Estimated from available data",
      "Source confirmation needed",
    ]);
  });

  test("keeps lodging provenance in technical details, not primary handoff copy", () => {
    const candidate: SearchV4Configuration = {
      ...configuration(),
      lodging_estimate: {
        mode: "lodging_nightly",
        minimum: 180,
        maximum: 255,
        currency: "EUR",
        trust_status: "estimated",
        provenance: "Catalog lodging range; estimate-aware constraint only.",
      },
    };
    const view = render(
      createElement(AccommodationHandoff, { configuration: candidate }),
    );

    expect(view.getByText("Estimated from available data")).toBeVisible();
    expect(view.container.textContent).not.toMatch(
      /catalog lodging range|estimate-aware constraint/i,
    );
    expect(
      decisionEvidencePresentation(candidate).technicalDetails,
    ).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "lodging-estimate",
          label: "Lodging estimate",
          provenance: "Catalog lodging range; estimate-aware constraint only.",
          evidenceLabel: "Place to stay estimate",
        }),
      ]),
    );
  });

  test("keeps estimates visible while giving terrain and lift access plain labels", () => {
    const candidate = configuration();

    expect(terrainPresentation(candidate.selected_pass)?.essentialValue).toBe(
      "About 239 km in the connected area covered by this pass",
    );
    expect(formatTripEssential("liftAccess", candidate)?.value).toBe(
      "About 324 m walk to the lifts",
    );
  });

  test("uses plain evidence labels and direct source details", () => {
    const candidate = configuration();
    const presentation = decisionEvidencePresentation(candidate);

    expect(evidenceQualityCopy.fallbackHeavy).toEqual({
      label: "Limited evidence",
      description: "Some parts of this recommendation rely on limited data.",
    });
    expect(buildCandidateNarrative(candidate).watchout).toBe(
      "Some terrain may not suit every skier in your group.",
    );
    expect(presentation.technicalDetails).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "catalog-access",
          provenance:
            "Estimated from source data for this trip configuration. The catalog links Ischgl to Ischgl. Nearest lift: Silvrettabahn.",
        }),
      ]),
    );
  });
});
