import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { SearchV4Configuration } from "../types";
import { DecisionEvidenceLedger } from "./DecisionEvidenceLedger";

function configuration(): SearchV4Configuration {
  return {
    candidate_id: "cervinia",
    ski_region_id: "cervinia",
    ski_region_name: "Cervinia",
    stay_destination_id: "cervinia",
    stay_destination_name: "Cervinia",
    stay_base_id: "breuil-cervinia",
    stay_base_name: "Breuil-Cervinia",
    ski_area_id: "cervinia-ski-area",
    ski_area_name: "Cervinia",
    evidence_profile: "archive_backed",
    access: {
      ski_area_access_id: "cervinia-access",
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: null,
      distance_m: 100,
      duration_minutes: null,
      is_direct: true,
      relationship_trust_status: "verified",
      access_mode_distance_trust_status: "verified",
    },
    selected_pass: {
      lift_pass_product_id: "cervinia-pass",
      name: "Cervinia Pass",
      validity_scope: "local",
      covered_ski_area_ids: ["cervinia-ski-area"],
      accessible_piste_km: 150,
      accessible_piste_km_evidence: {
        trust_status: "verified",
        scope: "pass",
        source_entity_id: "cervinia-pass",
        field_group: "terrain_metrics",
      },
      price: null,
    },
    lodging_estimate: null,
    ranking_status: "ranked",
    fit_score: 80,
    groups: [],
    factors: [],
    constraint_warnings: [],
  };
}

describe("DecisionEvidenceLedger", () => {
  test("introduces the decision evidence in direct, plain language", () => {
    render(<DecisionEvidenceLedger configuration={configuration()} />);

    expect(screen.getByRole("heading", { name: "Why this trip" })).toBeVisible();
    expect(
      screen.getByText(
        "Why Snowcast recommends this trip, including important limits.",
      ),
    ).toBeVisible();
  });

  test("keeps technical provenance and controls outside the plain-language ledger", () => {
    const candidate = configuration();
    candidate.factors = [
      {
        factor_id: "party_skill_coverage",
        group_id: "ski_experience",
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
        provenance_summary: "Catalog field-group evidence: verified; 4 source reference(s).",
        explanation_inputs: {},
      },
    ];

    render(<DecisionEvidenceLedger configuration={candidate} />);

    expect(screen.queryByText("Show technical calculation details")).toBeNull();
    expect(screen.queryByText(/Catalog field-group evidence/i)).toBeNull();
  });
});
