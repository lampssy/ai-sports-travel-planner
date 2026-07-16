import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import type {
  SearchIntent,
  SearchResponse,
  SearchV4Configuration,
  SearchV4RecommendationGroup,
} from "../types";
import { RecommendationDossier } from "./RecommendationDossier";
import { boundedNavigatorGroups } from "./RecommendationNavigator";
import { createSearchSession } from "./searchSession";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<Response>(() => undefined)),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const intent: SearchIntent = {
  constraints: {
    location: { country: "France" },
    travel_window: { month: 3 },
  },
  party: { skill_levels: ["intermediate"] },
  travel_context: {},
  objectives: [],
  group_priorities: [],
  factor_preferences: [],
  assumptions: [],
};

function configuration(
  regionId: string,
  rank: number,
  candidateId = `${regionId}-top`,
): SearchV4Configuration {
  return {
    candidate_id: candidateId,
    ski_region_id: regionId,
    ski_region_name: `Region ${rank}`,
    stay_destination_id: `destination-${rank}`,
    stay_destination_name: `Destination ${rank}`,
    stay_base_id: `base-${rank}`,
    stay_base_name: `Base ${rank}`,
    ski_area_id: `area-${rank}`,
    ski_area_name: `Area ${rank}`,
    access: {
      ski_area_access_id: `access-${rank}`,
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: `Lift ${rank}`,
      distance_m: rank * 100,
      duration_minutes: rank * 2,
      is_direct: true,
    },
    selected_pass: {
      lift_pass_product_id: `pass-${candidateId}`,
      name: `Pass ${candidateId}`,
      validity_scope: "single_ski_area",
      covered_ski_area_ids: [`area-${rank}`],
      accessible_piste_km: 100 + rank,
      price: {
        duration_days: 6,
        audience: "adult",
        amount: 300 + rank,
        amount_min: null,
        amount_max: null,
        currency: "EUR",
        price_kind: "fixed",
        season_label: "2026-2027",
      },
    },
    lodging_estimate: {
      mode: "lodging_nightly",
      minimum: 150,
      maximum: 220,
      currency: "EUR",
      trust_status: "estimated",
      provenance: "Catalog estimate.",
    },
    ranking_status: "ranked",
    fit_score: 90 - rank,
    groups: [],
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
        contribution_points: 12,
        evidence_cap_components: {},
        warnings: rank === 4 ? ["Lower slopes need monitoring."] : [],
        provenance_summary: "Historical snow evidence.",
        explanation_inputs: {},
      },
    ],
    constraint_warnings: [],
  };
}

function group(rank: number): SearchV4RecommendationGroup {
  const top = configuration(`region-${rank}`, rank);
  return {
    ski_region_id: top.ski_region_id,
    ski_region_name: top.ski_region_name,
    rank,
    fit_score: top.fit_score,
    top_configuration: top,
    alternative_configurations:
      rank === 4 ? [configuration("region-4", rank, "region-4-alternative")] : [],
  };
}

function session() {
  const groups = [1, 2, 3, 4].map(group);
  const response: SearchResponse = {
    search_model_version: "search-v4",
    ranking_policy_version: "test",
    ranking_status: "ranked",
    unscored_reason: null,
    applied_intent: intent,
    eligible_candidate_count: 4,
    excluded_candidate_count: 0,
    results: groups,
    refinements: [],
  };
  return createSearchSession("March in France", intent, response);
}

test("bounds the navigator to the top three or top two plus current", () => {
  const groups = session().response.results;

  expect(
    boundedNavigatorGroups(groups, "region-1").map((item) => item.ski_region_id),
  ).toEqual(["region-1", "region-2", "region-3"]);
  expect(
    boundedNavigatorGroups(groups, "region-4").map((item) => item.ski_region_id),
  ).toEqual(["region-1", "region-2", "region-4"]);
});

test("shows the top two plus an out-of-band current recommendation", () => {
  render(
    <RecommendationDossier
      session={session()}
      skiRegionId="region-4"
      candidateId="region-4-alternative"
      onSwitch={vi.fn()}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={vi.fn()}
    />,
  );

  const navigator = screen.getByRole("navigation", {
    name: "Recommendation results",
  });
  expect(within(navigator).getByRole("button", { name: /region 1/i })).toBeVisible();
  expect(within(navigator).getByRole("button", { name: /region 2/i })).toBeVisible();
  expect(within(navigator).queryByRole("button", { name: /region 3/i })).toBeNull();
  expect(within(navigator).getByRole("button", { name: /region 4/i })).toHaveAttribute(
    "aria-current",
    "page",
  );
});

test("renders the verdict hierarchy, progressive anchors, and selected save target", async () => {
  const user = userEvent.setup();
  const onSave = vi.fn();
  const onSelectCandidate = vi.fn();
  render(
    <RecommendationDossier
      session={session()}
      skiRegionId="region-4"
      candidateId="region-4-alternative"
      onSwitch={vi.fn()}
      onReturn={vi.fn()}
      onSave={onSave}
      onSelectCandidate={onSelectCandidate}
      onToggleNavigator={vi.fn()}
    />,
  );

  expect(screen.getByRole("heading", { name: "Region 4 - Base 4" })).toBeVisible();
  expect(screen.getByText("Trip fit")).toBeVisible();
  expect(screen.getByText("Snow window")).toBeVisible();
  expect(screen.getByText("Evidence quality")).toBeVisible();
  expect(screen.getAllByText("Destination 4")[0]).toBeVisible();
  expect(screen.getAllByText("Area 4")[0]).toBeVisible();
  expect(screen.getAllByText("Pass region-4-alternative")[0]).toBeVisible();
  for (const name of [
    "Snow evidence",
    "Trip configuration",
    "Alternatives",
    "Accommodation",
    "Scoring details",
  ]) {
    expect(screen.getByRole("link", { name })).toBeVisible();
  }

  await user.click(screen.getByRole("button", { name: "Save as current trip" }));
  expect(onSave).toHaveBeenCalledWith(
    expect.objectContaining({ candidate_id: "region-4-alternative" }),
  );

  await user.click(
    screen.getByRole("button", { name: /select base 4 with pass region-4-top/i }),
  );
  expect(onSelectCandidate).toHaveBeenCalledWith("region-4", "region-4-top");
});

test("exposes desktop collapse and the bounded mobile switcher", async () => {
  const user = userEvent.setup();
  const onToggleNavigator = vi.fn();
  const onSwitch = vi.fn();
  render(
    <RecommendationDossier
      session={session()}
      skiRegionId="region-1"
      candidateId="region-1-top"
      onSwitch={onSwitch}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={onToggleNavigator}
    />,
  );

  const collapse = screen.getByRole("button", {
    name: "Collapse recommendation navigator",
  });
  expect(collapse).toHaveAttribute("aria-expanded", "true");
  await user.click(collapse);
  expect(onToggleNavigator).toHaveBeenCalledOnce();

  const switcher = screen.getByRole("button", { name: /recommendation 1 of 4/i });
  expect(switcher).toHaveAttribute("aria-expanded", "false");
  await user.click(switcher);
  expect(switcher).toHaveAttribute("aria-expanded", "true");
  await user.click(screen.getByRole("button", { name: /switch to region 2/i }));
  expect(onSwitch).toHaveBeenCalledWith("region-2", "region-2-top");
});
