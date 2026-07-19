import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  test.each([
    ["verified", "Based on source data."],
    [
      "verified_with_adjustment",
      "Estimated from source data for this trip option.",
    ],
    ["estimated", "Estimated from available catalog data."],
    ["needs_source", "Source confirmation is still needed."],
  ] as const)(
    "translates %s in the opened technical disclosure",
    async (trustStatus, expectedStatus) => {
      const user = userEvent.setup();
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
          provenance_summary: `Catalog field-group evidence: ${trustStatus}; 4 source reference(s).`,
          explanation_inputs: {},
        },
      ];

      render(<DecisionEvidenceLedger configuration={candidate} />);

      const details = screen
        .getByText("Show technical calculation details")
        .closest("details");
      expect(details).not.toHaveAttribute("open");

      await user.click(screen.getByText("Show technical calculation details"));

      expect(details).toHaveAttribute("open");
      const factorRow = within(details as HTMLElement)
        .getByRole("heading", { name: "Skiing level fit" })
        .closest("article");
      expect(factorRow).not.toBeNull();
      expect(within(factorRow as HTMLElement).getByText(new RegExp(expectedStatus))).toBeVisible();
      expect(
        within(factorRow as HTMLElement).getByText(
          /Catalog field-group evidence; 4 source reference/,
        ),
      ).toBeVisible();
      expect(
        within(factorRow as HTMLElement).queryByText(
          new RegExp(`\\b${trustStatus}\\b`),
        ),
      ).toBeNull();
    },
  );

  test.each([
    [
      "keeps the catalog place-to-stay relationship when distance needs verification",
      "estimated",
      "The catalog links Breuil-Cervinia to Cervinia.",
    ],
    [
      "identifies a place-to-stay relationship that needs verification",
      "needs_source",
      "The link between Breuil-Cervinia and Cervinia needs verification.",
    ],
  ] as const)(
    "%s in the opened access disclosure",
    async (_case, relationshipTrustStatus, relationshipBasis) => {
      const user = userEvent.setup();
      const candidate = configuration();
      candidate.access = {
        ...candidate.access,
        nearest_lift_name: "Plan Maison",
        distance_m: 250,
        relationship_trust_status: relationshipTrustStatus,
        access_mode_distance_trust_status: "needs_source",
      };

      render(<DecisionEvidenceLedger configuration={candidate} />);
      await user.click(screen.getByText("Show technical calculation details"));

      const accessRow = screen
        .getByRole("heading", { name: "Place to stay and lift access" })
        .closest("article");
      expect(accessRow).not.toBeNull();
      expect(
        within(accessRow as HTMLElement).getByText(
          "Source confirmation is still needed.",
          { exact: false },
        ),
      ).toBeVisible();
      expect(
        within(accessRow as HTMLElement).getByText(relationshipBasis, {
          exact: false,
        }),
      ).toBeVisible();
      expect(
        within(accessRow as HTMLElement).getByText(
          "The lift-access mode and distance need verification.",
          { exact: false },
        ),
      ).toBeVisible();
      expect(within(accessRow as HTMLElement).queryByText(/Plan Maison|250 m/i)).toBeNull();
    },
  );
});
