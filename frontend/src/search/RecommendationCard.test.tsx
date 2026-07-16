import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, test, vi } from "vitest";

import type {
  SearchV4Configuration,
  SearchV4RecommendationGroup,
} from "../types";
import { RecommendationCard } from "./RecommendationCard";
import { ScoringDetails } from "./ScoringDetails";

function candidate(
  id: string,
  stayBase: string,
  passName: string,
  terrainKm: number,
): SearchV4Configuration {
  return {
    candidate_id: id,
    ski_region_id: "region-a",
    ski_region_name: "Matterhorn Ski Paradise",
    stay_destination_id: "cervinia",
    stay_destination_name: "Cervinia",
    stay_base_id: `base-${id}`,
    stay_base_name: stayBase,
    ski_area_id: "cervinia-area",
    ski_area_name: "Cervinia",
    access: {
      ski_area_access_id: `access-${id}`,
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: "Plan Maison",
      distance_m: id === "primary" ? 250 : 400,
      duration_minutes: 4,
      is_direct: true,
    },
    selected_pass: {
      lift_pass_product_id: `pass-${id}`,
      name: passName,
      validity_scope: "regional",
      covered_ski_area_ids: ["cervinia-area"],
      accessible_piste_km: terrainKm,
      price: {
        duration_days: 6,
        audience: "adult",
        amount: id === "primary" ? 426 : 360,
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
      maximum: 250,
      currency: "EUR",
      trust_status: "estimated",
      provenance: "Catalog estimate.",
    },
    ranking_status: "ranked",
    fit_score: id === "primary" ? 94.8 : 91.2,
    groups: [
      {
        group_id: "ski_experience",
        normalized_share: 0.5,
        group_utility: 0.9,
        contribution_points: 45,
      },
    ],
    factors: [
      {
        factor_id: "stay_base_access",
        group_id: "stay_practicality",
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
        provenance_summary: "Typed access evidence.",
        explanation_inputs: {},
      },
    ],
    constraint_warnings: [],
  };
}

const primary = candidate("primary", "Breuil-Cervinia", "International pass", 360);
const alternative = candidate("alternative", "Valtournenche", "Local pass", 160);
const result: SearchV4RecommendationGroup = {
  ski_region_id: "region-a",
  ski_region_name: "Matterhorn Ski Paradise",
  rank: 1,
  fit_score: 94.8,
  top_configuration: primary,
  alternative_configurations: [alternative],
};

function StatefulCard({
  onSave = vi.fn(),
}: {
  onSave?: (configuration: SearchV4Configuration) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [selectedCandidateId, setSelectedCandidateId] = useState(
    primary.candidate_id,
  );
  return (
    <RecommendationCard
      result={result}
      expanded={expanded}
      selectedCandidateId={selectedCandidateId}
      essentialCategories={["terrain", "passValue", "liftAccess"]}
      changedRank={false}
      onToggle={() => setExpanded((value) => !value)}
      onSelectCandidate={setSelectedCandidateId}
      onSave={onSave}
    />
  );
}

describe("RecommendationCard", () => {
  test("exposes an independent expansion control", async () => {
    const user = userEvent.setup();
    render(<StatefulCard />);

    const toggle = screen.getByRole("button", {
      name: /collapse matterhorn ski paradise/i,
    });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveAttribute("aria-controls", "recommendation-region-a");

    await user.click(toggle);
    expect(screen.getByRole("button", { name: /expand matterhorn/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  test("keeps dossier, save, and alternative controls isolated from expansion", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<StatefulCard onSave={onSave} />);

    const card = screen.getByRole("article");
    const toggle = within(card).getByRole("button", { name: /collapse matterhorn/i });
    const dossierLink = within(card).getByRole("link", { name: /view dossier/i });
    dossierLink.addEventListener("click", (event) => event.preventDefault());
    await user.click(dossierLink);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.click(within(card).getByRole("button", { name: /save as current trip/i }));
    expect(onSave).toHaveBeenCalledWith(primary);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.click(within(card).getByRole("button", { name: /select valtournenche/i }));
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(within(card).getByRole("heading", { name: /stay in valtournenche/i })).toBeVisible();
    expect(within(card).getAllByText("Local pass")).toHaveLength(2);
    expect(within(card).getByText("160 km")).toBeVisible();
    expect(within(card).getByRole("link", { name: /view dossier/i })).toHaveAttribute(
      "href",
      "/recommendations/region-a?candidate=alternative",
    );

    await user.click(within(card).getByRole("button", { name: /save as current trip/i }));
    expect(onSave).toHaveBeenLastCalledWith(alternative);
    expect(within(card).getByText("#1")).toBeVisible();
  });

  test("shows only approved scoring labels", () => {
    const unknownScoring = candidate("unknown", "Unknown base", "Unknown pass", 100);
    unknownScoring.groups = [
      ...unknownScoring.groups,
      {
        group_id: "future_internal_group",
        normalized_share: 0.5,
        group_utility: 0.5,
        contribution_points: 10,
      },
    ];
    unknownScoring.factors = [
      ...unknownScoring.factors,
      {
        ...unknownScoring.factors[0],
        factor_id: "future_internal_factor",
      },
    ];

    render(<ScoringDetails configuration={unknownScoring} />);

    expect(screen.queryByText("future_internal_group")).not.toBeInTheDocument();
    expect(screen.queryByText("future_internal_factor")).not.toBeInTheDocument();
    expect(screen.getByText("Ski experience")).toBeInTheDocument();
    expect(screen.getByText("Stay-base access")).toBeInTheDocument();
  });
});
