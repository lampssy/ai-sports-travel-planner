import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "./App";
import type {
  SearchIntent,
  SearchResponse,
  SearchV4Configuration,
} from "./types";

const intent: SearchIntent = {
  constraints: {
    location: { country: "France" },
    travel_window: { month: 3 },
  },
  party: { skill_levels: ["intermediate"] },
  travel_context: {},
  objectives: [{ factor_id: "pass_terrain_value", importance: "normal" }],
  group_priorities: [],
  factor_preferences: [],
  assumptions: [],
};

const tignesConfiguration: SearchV4Configuration = {
  candidate_id: "tignes-access--tignes-pass",
  ski_region_id: "tignes-val-disere",
  ski_region_name: "Tignes - Val d'Isere",
  stay_destination_id: "tignes",
  stay_destination_name: "Tignes",
  stay_base_id: "tignes-le-lac",
  stay_base_name: "Le Lac",
  ski_area_id: "tignes-ski-area",
  ski_area_name: "Tignes",
  access: {
    ski_area_access_id: "tignes-access",
    access_mode: "walk",
    lift_distance: "near",
    nearest_lift_name: "Toviere",
    distance_m: 250,
    duration_minutes: 4,
    is_direct: true,
  },
  selected_pass: {
    lift_pass_product_id: "tignes-pass",
    name: "Tignes - Val d'Isere pass",
    validity_scope: "local_multi_area",
    covered_ski_area_ids: ["tignes-ski-area", "val-disere-ski-area"],
    accessible_piste_km: 300,
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
    provenance: "Catalog lodging range; estimate-aware constraint only.",
  },
  ranking_status: "ranked",
  fit_score: 82.4,
  groups: [
    {
      group_id: "ski_experience",
      normalized_share: 0.3,
      group_utility: 0.9,
      contribution_points: 27,
    },
  ],
  factors: [
    {
      factor_id: "party_skill_coverage",
      group_id: "ski_experience",
      direction: "prefer",
      raw_value: { basis: "piste_km_by_difficulty" },
      raw_utility: 0.9,
      neutral_utility: 0.5,
      effective_evidence_cap: 1,
      effective_utility: 0.9,
      effective_weight: 2,
      contribution_points: 12,
      evidence_cap_components: { catalog_source_strength: 1 },
      warnings: [],
      provenance_summary: "Source-backed piste difficulty inventory.",
      explanation_inputs: {},
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
      contribution_points: 15,
      evidence_cap_components: {},
      warnings: ["forecast unavailable for requested dates"],
      provenance_summary: "No applicable weather evidence.",
      explanation_inputs: {},
    },
  ],
  constraint_warnings: [],
};

function response(
  updates: Partial<SearchResponse> = {},
): SearchResponse {
  return {
    search_model_version: "search-v4",
    ranking_policy_version: "search-v4-policy-1",
    ranking_status: "ranked",
    unscored_reason: null,
    applied_intent: intent,
    eligible_candidate_count: 7,
    excluded_candidate_count: 3,
    results: [
      {
        ski_region_id: tignesConfiguration.ski_region_id,
        ski_region_name: tignesConfiguration.ski_region_name,
        rank: 1,
        fit_score: tignesConfiguration.fit_score,
        top_configuration: tignesConfiguration,
        alternative_configurations: [],
      },
    ],
    refinements: [],
    ...updates,
  };
}

let searchResponses: SearchResponse[];
let requests: Array<{ url: string; init?: RequestInit }>;

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  searchResponses = [response()];
  requests = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/current-trip" && (!init?.method || init.method === "GET")) {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(JSON.stringify(searchResponses.shift() ?? response()), {
          status: 200,
        });
      }
      if (url === "/api/parse-query") {
        return new Response(
          JSON.stringify({ filters: {}, confidence: 1, unknown_parts: [] }),
          { status: 200 },
        );
      }
      if (url === "/api/current-trip" && init?.method === "PUT") {
        const body = JSON.parse(String(init.body));
        return new Response(
          JSON.stringify({
            ...body,
            created_at: "2026-07-15T00:00:00Z",
            updated_at: "2026-07-15T00:00:00Z",
            last_checked_at: null,
          }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify({ detail: "Not found" }), { status: 404 });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("posts one typed Search V4 request and renders fit and evidence", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /search and rank/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeInTheDocument();
  expect(screen.getByText("82.4")).toBeInTheDocument();
  expect(screen.getByText(/300 km pass coverage/i)).toBeInTheDocument();
  expect(screen.getByText(/EUR 180-255 nightly \(estimated\)/i)).toBeInTheDocument();
  const searchRequest = requests.find((item) => item.url === "/api/search");
  expect(searchRequest?.init?.method).toBe("POST");
  const body = JSON.parse(String(searchRequest?.init?.body));
  expect(body.intent.constraints.location).toEqual({ country: "France" });
  expect(body.intent.party.skill_levels).toEqual(["intermediate"]);
  expect(body.intent.objectives[0].factor_id).toBe("pass_terrain_value");
  expect(body.generate_refinements).toBe(true);

  await user.click(screen.getByRole("button", { name: /why this fit/i }));
  expect(screen.getByText(/source-backed piste difficulty/i)).toBeInTheDocument();
  expect(screen.getByText("Unknown")).toBeInTheDocument();
});

test("exact dates take precedence in the POST intent", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.selectOptions(screen.getByLabelText("Travel window"), "dates");
  await user.type(screen.getByLabelText("Trip start date"), "2027-01-16");
  await user.type(screen.getByLabelText("Trip end date"), "2027-01-20");
  await user.click(screen.getByRole("button", { name: /search and rank/i }));

  await screen.findByText("Tignes - Val d'Isere");
  const searchRequest = requests.find((item) => item.url === "/api/search");
  const body = JSON.parse(String(searchRequest?.init?.body));
  expect(body.intent.constraints.travel_window).toEqual({
    start_date: "2027-01-16",
    end_date: "2027-01-20",
  });
  expect(body.intent.constraints.travel_window.month).toBeUndefined();
});

test("rejects invalid hard numeric filters instead of silently omitting them", async () => {
  render(<App />);

  const maxNightly = screen.getByLabelText("Max nightly");
  const maxDriveHours = screen.getByLabelText("Hard drive limit");
  const searchForm = screen
    .getByRole("button", { name: /search and rank/i })
    .closest("form");
  expect(searchForm).not.toBeNull();
  expect(maxNightly).toHaveAttribute("min", "0.01");
  expect(maxNightly).toHaveAttribute("step", "0.01");
  expect(maxDriveHours).toHaveAttribute("min", "0.1");
  expect(maxDriveHours).toHaveAttribute("step", "0.1");

  fireEvent.change(maxNightly, { target: { value: "0" } });
  fireEvent.submit(searchForm as HTMLFormElement);

  expect(
    await screen.findByText("Maximum nightly price must be greater than 0."),
  ).toBeInTheDocument();
  expect(requests.some((item) => item.url === "/api/search")).toBe(false);

  fireEvent.change(maxNightly, { target: { value: "250" } });
  fireEvent.change(maxDriveHours, { target: { value: "12.5" } });
  fireEvent.submit(searchForm as HTMLFormElement);

  expect(
    await screen.findByText("Provide an origin to use a hard drive limit."),
  ).toBeInTheDocument();
  expect(requests.some((item) => item.url === "/api/search")).toBe(false);

  fireEvent.change(screen.getByLabelText("Origin"), {
    target: { value: "Berlin" },
  });
  fireEvent.change(maxDriveHours, { target: { value: "-1" } });
  fireEvent.submit(searchForm as HTMLFormElement);

  expect(
    await screen.findByText("Hard drive limit must be greater than 0 hours."),
  ).toBeInTheDocument();
  expect(requests.some((item) => item.url === "/api/search")).toBe(false);

  fireEvent.change(maxDriveHours, { target: { value: "12.5" } });
  fireEvent.submit(searchForm as HTMLFormElement);

  await screen.findByText("Tignes - Val d'Isere");
  const searchRequest = requests.find((item) => item.url === "/api/search");
  const body = JSON.parse(String(searchRequest?.init?.body));
  expect(body.intent.constraints.lodging_budget.maximum).toBe(250);
  expect(body.intent.constraints.travel_limit.maximum_duration_hours).toBe(12.5);
});

test("applies a validated dynamic refinement and immediately reruns", async () => {
  searchResponses = [
    response({
      refinements: [
        {
          question_id: "evening-style",
          question: "Would you prefer lively après or a quieter base?",
          reason: "The answer changes the leading stay base.",
          options: [
            {
              label: "Lively après",
              description: "Prefer a lively local après profile.",
              group_priority_patches: [],
              factor_preference_patches: [
                {
                  factor_id: "local_apres",
                  mode: "prefer",
                  values: ["lively"],
                  importance: "normal",
                },
              ],
              objective_patches: [],
            },
            {
              label: "Quiet base",
              description: "Prefer a quiet local pace.",
              group_priority_patches: [],
              factor_preference_patches: [
                {
                  factor_id: "local_pace",
                  mode: "prefer",
                  values: ["quiet"],
                  importance: "normal",
                },
              ],
              objective_patches: [],
            },
          ],
        },
      ],
    }),
    response(),
  ];
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /search and rank/i }));
  expect(await screen.findByText(/would you prefer lively après/i)).toBeInTheDocument();

  let resolveRefinedSearch: ((value: Response) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/search") {
        return new Promise<Response>((resolve) => {
          resolveRefinedSearch = resolve;
        });
      }
      return Promise.resolve(
        new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
      );
    }),
  );
  const livelyOption = screen.getByRole("button", { name: "Lively après" });
  await user.click(livelyOption);
  expect(livelyOption).toBeDisabled();
  resolveRefinedSearch?.(
    new Response(JSON.stringify(response()), { status: 200 }),
  );

  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(2);
  });
  const body = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[1].init?.body),
  );
  expect(body.intent.factor_preferences).toEqual([
    {
      factor_id: "local_apres",
      mode: "prefer",
      values: ["lively"],
      importance: "normal",
    },
  ]);
  expect(body.already_answered_question_ids).toEqual(["evening-style"]);
  expect(screen.getByText(/prefer stay-base après: lively/i)).toBeInTheDocument();
});

test("lets users remove selected objectives and refinement group priorities", async () => {
  searchResponses = [
    response({
      refinements: [
        {
          question_id: "snow-priority",
          question: "How important is trip-window snow confidence?",
          reason: "The answer changes the result order.",
          options: [
            {
              label: "Very important",
              description: "Give trip viability very high importance.",
              group_priority_patches: [
                { group_id: "trip_viability", importance: "very_high" },
              ],
              factor_preference_patches: [],
              objective_patches: [],
            },
            {
              label: "Normal",
              description: "Keep the normal trip viability importance.",
              group_priority_patches: [
                { group_id: "trip_viability", importance: "normal" },
              ],
              factor_preference_patches: [],
              objective_patches: [],
            },
          ],
        },
      ],
    }),
    response(),
    response(),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(
    screen.getByRole("button", { name: /remove optimize terrain per pass price/i }),
  );
  expect(screen.queryByText(/optimize terrain per pass price/i)).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /search and rank/i }));
  const firstSearch = requests.find((item) => item.url === "/api/search");
  expect(JSON.parse(String(firstSearch?.init?.body)).intent.objectives).toEqual([]);

  await user.click(await screen.findByRole("button", { name: "Very important" }));
  expect(screen.getByText(/trip viability: very_high/i)).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: /remove trip viability: very_high/i }),
  );

  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(3);
  });
  const lastBody = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[2].init?.body),
  );
  expect(lastBody.intent.group_priorities).toEqual([]);
});

test("saving a V4 configuration preserves trip entity identities", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /search and rank/i }));
  const card = (await screen.findByText("Tignes - Val d'Isere")).closest("article");
  expect(card).not.toBeNull();
  await user.click(within(card as HTMLElement).getByRole("button", { name: /save trip/i }));

  await waitFor(() => {
    expect(
      requests.some((item) => item.url === "/api/current-trip" && item.init?.method === "PUT"),
    ).toBe(true);
  });
  const saveRequest = requests.find(
    (item) => item.url === "/api/current-trip" && item.init?.method === "PUT",
  );
  const body = JSON.parse(String(saveRequest?.init?.body));
  expect(body).toMatchObject({
    ski_region_id: "tignes-val-disere",
    stay_destination_id: "tignes",
    stay_base_id: "tignes-le-lac",
    focus_ski_area_id: "tignes-ski-area",
    lift_pass_product_id: "tignes-pass",
  });
});

test("does not present stable unscored order as recommendation strength", async () => {
  searchResponses = [
    response({
      ranking_status: "unscored",
      unscored_reason: "no_active_groups",
      results: [
        {
          ski_region_id: tignesConfiguration.ski_region_id,
          ski_region_name: tignesConfiguration.ski_region_name,
          rank: 1,
          fit_score: null,
          top_configuration: {
            ...tignesConfiguration,
            ranking_status: "unscored",
            fit_score: null,
            groups: [],
            factors: [],
          },
          alternative_configurations: [],
        },
      ],
    }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /search and rank/i }));

  expect(await screen.findByText("Unranked option")).toBeInTheDocument();
  expect(screen.queryByText("#1")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Show evidence" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /why this fit/i })).not.toBeInTheDocument();
});
