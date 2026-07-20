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
    evidence_profile: "archive_backed",
    access: {
      ski_area_access_id: `access-${rank}`,
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: `Lift ${rank}`,
      distance_m: rank * 100,
      duration_minutes: rank * 2,
      is_direct: true,
      relationship_trust_status: "verified",
      access_mode_distance_trust_status: "verified",
    },
    selected_pass: {
      lift_pass_product_id: `pass-${candidateId}`,
      name: `Pass ${candidateId}`,
      validity_scope: "single_ski_area",
      covered_ski_area_ids: [`area-${rank}`],
      accessible_piste_km: 100 + rank,
      accessible_piste_km_evidence: {
        trust_status: "verified",
        scope: "pass",
        source_entity_id: `pass-${candidateId}`,
        field_group: "pass_accessible_terrain",
      },
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
    baseline_fingerprint: "baseline-dossier",
    ranking_status: "ranked",
    unscored_reason: null,
    applied_intent: intent,
    eligible_candidate_count: 4,
    excluded_candidate_count: 0,
    results: groups,
    refinements: [],
  };
  return createSearchSession("March in France", response);
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

test("does not present unscored options as ranked recommendations", () => {
  const unscoredSession = session();
  unscoredSession.response = {
    ...unscoredSession.response,
    ranking_status: "unscored",
    unscored_reason: "No comparable ranking factors are available.",
    results: unscoredSession.response.results.map((result) => ({
      ...result,
      fit_score: null,
      top_configuration: {
        ...result.top_configuration,
        ranking_status: "unscored",
        fit_score: null,
      },
      alternative_configurations: result.alternative_configurations.map(
        (candidate) => ({
          ...candidate,
          ranking_status: "unscored",
          fit_score: null,
        }),
      ),
    })),
  };

  render(
    <RecommendationDossier
      session={unscoredSession}
      skiRegionId="region-4"
      candidateId="region-4-alternative"
      onSwitch={vi.fn()}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={vi.fn()}
    />,
  );

  expect(screen.getAllByText("Fit comparison unavailable").length).toBeGreaterThan(0);
  expect(screen.queryByText("Unscored")).toBeNull();
  expect(screen.getByText("Why it fits")).toBeVisible();
  expect(screen.getByText("Main concern")).toBeVisible();
  expect(
    screen.queryByRole("heading", { name: "Technical calculation details" }),
  ).toBeNull();
  expect(screen.queryByText(/complete ranked trip configuration/i)).toBeNull();
  expect(screen.getByText("Alternative trip option")).toBeVisible();
  expect(screen.queryByText("#4")).toBeNull();
  const navigator = screen.getByRole("navigation", {
    name: "Trip option results",
  });
  const unavailableRow = within(navigator).getByRole("button", {
    name: /region 4.*fit comparison unavailable/i,
  });
  expect(unavailableRow).toHaveAccessibleName(/fit comparison unavailable/i);
  expect(unavailableRow).not.toHaveAccessibleName(/trip fit not scored/i);
});

test("prompts for travel dates instead of narrating a snow fit without a window", () => {
  const noWindowSession = session();
  noWindowSession.response = {
    ...noWindowSession.response,
    applied_intent: {
      ...noWindowSession.response.applied_intent,
      constraints: { location: { country: "France" } },
    },
  };

  render(
    <RecommendationDossier
      session={noWindowSession}
      skiRegionId="region-4"
      candidateId="region-4-alternative"
      onSwitch={vi.fn()}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={vi.fn()}
    />,
  );

  expect(screen.getAllByText("Add travel dates to assess snow fit").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Not assessed").length).toBeGreaterThan(0);
  expect(screen.queryByText("Strong fit")).toBeNull();
  expect(screen.queryByText("Some concerns")).toBeNull();
  expect(screen.queryByText(/supports this travel window/i)).toBeNull();
  const navigator = screen.getByRole("navigation", {
    name: "Trip option results",
  });
  expect(
    within(navigator).getByRole("button", {
      name: /region 4.*add travel dates to assess snow fit: not assessed/i,
    }),
  ).toBeVisible();
});

test("de-duplicates the snow warning between the verdict and remaining uncertainty by evidence id", () => {
  const currentSession = session();
  const current = currentSession.response.results[0].top_configuration;
  current.factors[0] = {
    ...current.factors[0],
    effective_evidence_cap: 0,
    warnings: ["Historical evidence is limited."],
  };

  render(
    <RecommendationDossier
      session={currentSession}
      skiRegionId={current.ski_region_id}
      candidateId={current.candidate_id}
      onSwitch={vi.fn()}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={vi.fn()}
    />,
  );

  expect(screen.getByText("Main concern").parentElement).toHaveTextContent(
    "Snow fit for March: Snow evidence is limited for this travel window.",
  );
  expect(
    screen.queryByText("Snow evidence is limited for the requested travel window."),
  ).toBeNull();
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
    name: "Trip option results",
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
  expect(screen.getByText("Recommended place to stay: Base 4")).toBeVisible();
  expect(screen.getByText("Trip fit")).toBeVisible();
  expect(screen.getAllByText("Snow fit for March")[0]).toBeVisible();
  expect(screen.getByText("Evidence quality")).toBeVisible();
  expect(screen.getAllByText("Destination 4")[0]).toBeVisible();
  expect(screen.getAllByText("Area 4")[0]).toBeVisible();
  expect(screen.getAllByText("Pass region-4-alternative")[0]).toBeVisible();
  expect(
    screen.getByRole("heading", {
      name: "Alternative trip options in Region 4",
    }),
  ).toBeVisible();
  expect(document.body.textContent).not.toMatch(/configuration|dossier/i);
  for (const name of [
    "Snow & weather",
    "Trip details",
    "Alternative trip options",
    "Accommodation",
    "Why this trip",
    "Technical calculation details",
  ]) {
    expect(screen.getByRole("link", { name })).toBeVisible();
  }
  expect(
    screen.getAllByText("Technical calculation details", { selector: "summary" }),
  ).toHaveLength(1);
  expect(
    screen.getByRole("heading", { level: 2, name: "Advanced details" }),
  ).toBeVisible();
  expect(document.querySelectorAll("#scoring-details details")).toHaveLength(1);

  await user.click(screen.getByRole("button", { name: "Save as current trip" }));
  expect(onSave).toHaveBeenCalledWith(
    expect.objectContaining({ candidate_id: "region-4-alternative" }),
  );

  await user.click(
    screen.getByRole("button", { name: /select base 4 with pass region-4-top/i }),
  );
  expect(onSelectCandidate).toHaveBeenCalledWith("region-4", "region-4-top");
});

test("explains why the trip leads before exposing technical provenance", () => {
  const evidenceSession = session();
  const selected = evidenceSession.response.results[0].top_configuration;
  selected.factors = [
    {
      ...selected.factors[0],
      factor_id: "party_skill_coverage",
      effective_evidence_cap: 1,
      effective_utility: 0.9,
      neutral_utility: 0.5,
      provenance_summary:
        "Catalog field-group evidence: verified_with_adjustment; 4 source reference(s).",
    },
    {
      ...selected.factors[0],
      factor_id: "trip_window_snow_fit",
      effective_evidence_cap: 0,
      warnings: ["climatology unavailable"],
      provenance_summary: "Derived daily climatology; exact-date forecast unavailable.",
    },
  ];

  render(
    <RecommendationDossier
      session={evidenceSession}
      skiRegionId="region-1"
      candidateId="region-1-top"
      onSwitch={vi.fn()}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={vi.fn()}
    />,
  );

  const section = document.querySelector("#decision-evidence");
  expect(section).not.toBeNull();
  expect(within(section as HTMLElement).getByRole("heading", { name: "Why this trip" })).toBeVisible();
  expect(within(section as HTMLElement).getByRole("heading", { name: "What supports this choice" })).toBeVisible();
  expect(within(section as HTMLElement).queryByRole("heading", { name: "What remains uncertain" })).toBeNull();
  expect(screen.getByText("Main concern").parentElement).toHaveTextContent(
    "Snow fit for March: Snow evidence is limited for this travel window.",
  );
  expect(
    within(section as HTMLElement).queryByText("Technical calculation details"),
  ).toBeNull();
  expect(
    within(section as HTMLElement).queryByText(/Catalog field-group evidence/),
  ).toBeNull();
  const disclosures = screen
    .getAllByText("Technical calculation details")
    .filter((element) => element.tagName === "SUMMARY");
  expect(disclosures).toHaveLength(1);
  expect(disclosures[0].closest("details")).not.toHaveAttribute("open");
});

test("qualifies estimated terrain in dossier essentials, evidence, and scoring", async () => {
  const user = userEvent.setup();
  const estimatedSession = session();
  const selected = estimatedSession.response.results[0].top_configuration;
  selected.selected_pass = {
    ...selected.selected_pass,
    accessible_piste_km: 31,
    accessible_piste_km_evidence: {
      trust_status: "estimated",
      scope: "ski_area",
      source_entity_id: "pinzolo-ski-area",
      field_group: "terrain_metrics",
    },
  } as SearchV4Configuration["selected_pass"];
  selected.factors = [
    {
      ...selected.factors[0],
      factor_id: "accessible_terrain_scale",
      group_id: "ski_experience",
      raw_value: 31,
      provenance_summary: "Estimated ski-area terrain.",
    },
  ];

  render(
    <RecommendationDossier
      session={estimatedSession}
      skiRegionId="region-1"
      candidateId="region-1-top"
      onSwitch={vi.fn()}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={vi.fn()}
    />,
  );

  expect(
    screen.getAllByText("About 31 km in the selected ski area"),
  ).not.toHaveLength(0);
  expect(
    screen.getAllByText("About 31 km in the selected ski area"),
  ).not.toHaveLength(0);
  expect(screen.getAllByText("Terrain in the selected ski area")).toHaveLength(2);
  expect(screen.queryByText("Pass-accessible terrain")).toBeNull();
  expect(screen.queryByText("31 km accessible")).toBeNull();

  const scoringSection = document.querySelector("#scoring-details");
  expect(scoringSection).not.toBeNull();
  const scoring = within(scoringSection as HTMLElement)
    .getByText("Technical calculation details")
    .closest("details");
  expect(scoring).not.toHaveAttribute("open");
  await user.click(
    within(scoringSection as HTMLElement).getByText("Technical calculation details"),
  );
  expect(
    within(scoring as HTMLElement).getByText("Estimated from catalog data"),
  ).toBeVisible();
});

test("keeps domain terrain aligned across dossier evidence and scoring", async () => {
  const user = userEvent.setup();
  const domainSession = session();
  const selected = domainSession.response.results[0].top_configuration;
  selected.selected_pass = {
    ...selected.selected_pass,
    accessible_piste_km: 300,
    accessible_piste_km_evidence: {
      trust_status: "verified_with_adjustment",
      scope: "terrain_domain",
      source_entity_id: "tignes-val-disere",
      field_group: "aggregate_terrain",
    },
  } as SearchV4Configuration["selected_pass"];
  selected.factors = [
    {
      ...selected.factors[0],
      factor_id: "accessible_terrain_scale",
      group_id: "ski_experience",
      raw_value: 300,
      effective_evidence_cap: 1,
      provenance_summary: "Verified-with-adjustment terrain-domain aggregate.",
    },
  ];

  render(
    <RecommendationDossier
      session={domainSession}
      skiRegionId="region-1"
      candidateId="region-1-top"
      onSwitch={vi.fn()}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={vi.fn()}
    />,
  );

  expect(
    screen.getAllByText("About 300 km in the connected area covered by this pass"),
  ).not.toHaveLength(0);
  expect(
    screen.getAllByText("About 300 km in the connected area covered by this pass"),
  ).not.toHaveLength(0);
  expect(screen.getAllByText("Connected terrain covered by this pass")).toHaveLength(2);

  const scoringSection = document.querySelector("#scoring-details");
  expect(scoringSection).not.toBeNull();
  const scoring = within(scoringSection as HTMLElement)
    .getByText("Technical calculation details")
    .closest("details");
  await user.click(
    within(scoringSection as HTMLElement).getByText("Technical calculation details"),
  );
  expect(within(scoring as HTMLElement).getByText("Estimated from source data")).toBeVisible();
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
    name: "Collapse trip option navigator",
  });
  expect(collapse).toHaveAttribute("aria-expanded", "true");
  await user.click(collapse);
  expect(onToggleNavigator).toHaveBeenCalledOnce();

  const switcher = screen.getByRole("button", { name: /trip option 1 of 4/i });
  expect(switcher).toHaveAttribute("aria-expanded", "false");
  await user.click(switcher);
  expect(switcher).toHaveAttribute("aria-expanded", "true");
  await user.click(screen.getByRole("button", { name: /switch to region 2/i }));
  expect(onSwitch).toHaveBeenCalledWith("region-2", "region-2-top");
});

test("navigator and mobile switcher open the selected alternative they display", async () => {
  const user = userEvent.setup();
  const selectedSession = session();
  const secondGroup = selectedSession.response.results[1];
  const selectedAlternative = configuration(
    "region-2",
    2,
    "region-2-selected-alternative",
  );
  selectedAlternative.stay_base_name = "Selected Base 2";
  selectedAlternative.ski_area_id = "selected-area-2";
  secondGroup.alternative_configurations = [selectedAlternative];
  selectedSession.selectedCandidateIdByGroup[secondGroup.ski_region_id] =
    selectedAlternative.candidate_id;
  const onSwitch = vi.fn();

  render(
    <RecommendationDossier
      session={selectedSession}
      skiRegionId="region-1"
      candidateId="region-1-top"
      onSwitch={onSwitch}
      onReturn={vi.fn()}
      onSave={vi.fn()}
      onSelectCandidate={vi.fn()}
      onToggleNavigator={vi.fn()}
    />,
  );

  const navigator = screen.getByRole("navigation", {
    name: "Trip option results",
  });
  expect(within(navigator).getByText("Selected Base 2")).toBeVisible();
  expect(
    within(navigator).getByRole("button", {
      name: /region 2, rank 2, open option/i,
    }),
  ).toHaveAccessibleName(
    /selected base 2.*88 trip fit.*snow fit for march: strong fit/i,
  );
  await user.click(
    within(navigator).getByRole("button", {
      name: /region 2, rank 2, open option/i,
    }),
  );
  expect(onSwitch).toHaveBeenLastCalledWith(
    "region-2",
    "region-2-selected-alternative",
  );

  await user.click(screen.getByRole("button", { name: /trip option 1 of 4/i }));
  await user.click(screen.getByRole("button", { name: /switch to region 2/i }));
  expect(onSwitch).toHaveBeenLastCalledWith(
    "region-2",
    "region-2-selected-alternative",
  );
});
