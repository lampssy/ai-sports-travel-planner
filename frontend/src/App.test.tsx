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
  vi.stubGlobal("scrollTo", vi.fn());
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

async function openFilters(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Adjust filters" }));
  return screen.getByRole("dialog", { name: "Adjust filters" });
}

test("renders the accepted homepage command stage", () => {
  render(<App />);

  expect(
    screen.getByRole("heading", {
      name: /conditions-aware ski trips, planned around your window/i,
    }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Describe your ski trip")).toBeInTheDocument();
  expect(screen.getAllByText("Example recommendation")).toHaveLength(1);
  expect(screen.queryByText(/^Describe$/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/^Review$/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/^Compare$/i)).not.toBeInTheDocument();
});

test("parses and submits the brief, preserves it, and focuses results", async () => {
  const user = userEvent.setup();
  render(<App />);

  const brief = "A snow-reliable intermediate trip in France for March";
  await user.type(screen.getByLabelText("Describe your ski trip"), brief);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  const resultsHeading = await screen.findByRole("heading", {
    name: /recommended ski trips/i,
  });
  expect(resultsHeading).toHaveFocus();
  expect(screen.getByLabelText("Trip brief")).toHaveValue(brief);
  expect(requests.filter((item) => item.url === "/api/parse-query")).toHaveLength(1);
  expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(1);
});

test("names loading work and disables duplicate homepage submission", async () => {
  let resolveSearch: ((response: Response) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/current-trip") {
        return Promise.resolve(
          new Response(JSON.stringify({ trip: null }), { status: 200 }),
        );
      }
      if (url === "/api/parse-query") {
        return Promise.resolve(
          new Response(
            JSON.stringify({ filters: {}, confidence: 1, unknown_parts: [] }),
            { status: 200 },
          ),
        );
      }
      if (url === "/api/search") {
        return new Promise<Response>((resolve) => {
          resolveSearch = resolve;
        });
      }
      return Promise.resolve(new Response(null, { status: 404 }));
    }),
  );
  const user = userEvent.setup();
  render(<App />);

  await user.type(screen.getByLabelText("Describe your ski trip"), "March in France");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  const loadingButton = await screen.findByRole("button", {
    name: /finding resorts for your trip/i,
  });
  expect(loadingButton).toBeDisabled();
  await user.click(loadingButton);
  expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(1);

  resolveSearch?.(new Response(JSON.stringify(response()), { status: 200 }));
  await screen.findByRole("heading", { name: /recommended ski trips/i });
});

test("opens the labelled filter drawer and restores focus after Escape", async () => {
  const user = userEvent.setup();
  render(<App />);

  const trigger = screen.getByRole("button", { name: "Adjust filters" });
  await user.click(trigger);
  expect(screen.getByRole("dialog", { name: "Adjust filters" })).toBeInTheDocument();

  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog", { name: "Adjust filters" })).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});

test("renders removable parsed chips with user-language names", async () => {
  const user = userEvent.setup();
  render(<App />);

  const franceChip = screen.getByRole("button", { name: "Remove France" });
  await user.click(franceChip);

  expect(screen.queryByRole("button", { name: "Remove France" })).not.toBeInTheDocument();
});

test("posts one typed Search V4 request and renders fit and evidence", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeInTheDocument();
  expect(screen.getByText("82.4")).toBeInTheDocument();
  expect(screen.getByText(/300 km accessible terrain/i)).toBeInTheDocument();
  expect(screen.getByText(/estimated EUR 180-255\/night/i)).toBeInTheDocument();
  const searchRequest = requests.find((item) => item.url === "/api/search");
  expect(searchRequest?.init?.method).toBe("POST");
  const body = JSON.parse(String(searchRequest?.init?.body));
  expect(body.intent.constraints.location).toEqual({ country: "France" });
  expect(body.intent.party.skill_levels).toEqual(["intermediate"]);
  expect(body.intent.objectives[0].factor_id).toBe("pass_terrain_value");
  expect(body.generate_refinements).toBe(true);

  expect(
    screen.getByRole("button", { name: /collapse tignes - val d'isere/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/show scoring details/i)).toBeInTheDocument();
  expect(screen.getByText("Unknown")).toBeInTheDocument();
});

test("exact dates take precedence in the POST intent", async () => {
  const user = userEvent.setup();
  render(<App />);

  await openFilters(user);
  await user.selectOptions(screen.getByLabelText("Travel window"), "dates");
  await user.type(screen.getByLabelText("Trip start date"), "2027-01-16");
  await user.type(screen.getByLabelText("Trip end date"), "2027-01-20");
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

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
  const user = userEvent.setup();
  render(<App />);

  await openFilters(user);
  const maxNightly = screen.getByLabelText("Max nightly");
  const maxDriveHours = screen.getByLabelText("Hard drive limit");
  expect(maxNightly).toHaveAttribute("min", "0.01");
  expect(maxNightly).toHaveAttribute("step", "0.01");
  expect(maxDriveHours).toHaveAttribute("min", "0.1");
  expect(maxDriveHours).toHaveAttribute("step", "0.1");

  fireEvent.change(maxNightly, { target: { value: "0" } });
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText("Maximum nightly price must be greater than 0."),
  ).toBeInTheDocument();
  expect(requests.some((item) => item.url === "/api/search")).toBe(false);

  await openFilters(user);
  fireEvent.change(screen.getByLabelText("Max nightly"), {
    target: { value: "250" },
  });
  fireEvent.change(screen.getByLabelText("Hard drive limit"), {
    target: { value: "12.5" },
  });
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText("Provide an origin to use a hard drive limit."),
  ).toBeInTheDocument();
  expect(requests.some((item) => item.url === "/api/search")).toBe(false);

  await openFilters(user);
  fireEvent.change(screen.getByLabelText("Origin"), {
    target: { value: "Berlin" },
  });
  fireEvent.change(screen.getByLabelText("Hard drive limit"), {
    target: { value: "-1" },
  });
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText("Hard drive limit must be greater than 0 hours."),
  ).toBeInTheDocument();
  expect(requests.some((item) => item.url === "/api/search")).toBe(false);

  await openFilters(user);
  fireEvent.change(screen.getByLabelText("Hard drive limit"), {
    target: { value: "12.5" },
  });
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  await screen.findByText("Tignes - Val d'Isere");
  const searchRequest = requests.find((item) => item.url === "/api/search");
  const body = JSON.parse(String(searchRequest?.init?.body));
  expect(body.intent.constraints.lodging_budget.maximum).toBe(250);
  expect(body.intent.constraints.travel_limit.maximum_duration_hours).toBe(12.5);
});

test("previews a validated dynamic refinement before applying it", async () => {
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
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
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
  const livelyOption = screen.getByRole("radio", { name: /lively après/i });
  await user.click(livelyOption);
  expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(1);
  expect(
    screen.getByText("This answer can materially reorder your results"),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));
  expect(livelyOption).toBeDisabled();
  expect(screen.getByRole("heading", { name: /tignes - val d'isere/i })).toBeVisible();
  expect(
    screen.getByText(/reranking these recommendations/i),
  ).toBeInTheDocument();
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

test("guards open-drawer and chip mutations during a delayed rerank", async () => {
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
          ],
        },
      ],
    }),
  ];
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(await screen.findByRole("radio", { name: /very important/i }));
  await user.click(screen.getByRole("button", { name: "Adjust" }));

  let resolveRerank: ((value: Response) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/search") {
        return new Promise<Response>((resolve) => {
          resolveRerank = resolve;
        });
      }
      return Promise.resolve(
        new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
      );
    }),
  );

  fireEvent.click(screen.getByRole("button", { name: /apply and rerank/i }));
  expect(await screen.findByText(/reranking these recommendations/i)).toBeVisible();
  const country = screen.getByLabelText("Country");
  expect(country).toBeDisabled();
  fireEvent.change(country, { target: { value: "Austria" } });
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  expect(screen.getByRole("button", { name: "Remove France" })).toBeDisabled();

  resolveRerank?.(new Response(JSON.stringify(response()), { status: 200 }));
  await waitFor(() => {
    expect(screen.queryByText(/reranking these recommendations/i)).not.toBeInTheDocument();
  });
  await user.click(screen.getByRole("button", { name: "Adjust" }));
  expect(screen.getByLabelText("Country")).toHaveValue("France");
  expect(screen.getByRole("button", { name: "Remove France" })).toBeInTheDocument();
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

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  const firstSearch = requests.find((item) => item.url === "/api/search");
  expect(JSON.parse(String(firstSearch?.init?.body)).intent.objectives).toEqual([]);

  await user.click(await screen.findByRole("radio", { name: /very important/i }));
  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));
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
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  const card = (await screen.findByText("Tignes - Val d'Isere")).closest("article");
  expect(card).not.toBeNull();
  await user.click(
    within(card as HTMLElement).getByRole("button", {
      name: /save as current trip/i,
    }),
  );

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

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Unranked")).toBeInTheDocument();
  expect(screen.queryByText("#1")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /collapse tignes - val d'isere/i }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /expand tignes/i })).not.toBeInTheDocument();
});

test("renders grouped recommendations with independent expansion and no raw metadata", async () => {
  const secondConfiguration: SearchV4Configuration = {
    ...tignesConfiguration,
    candidate_id: "les-arcs--paradiski",
    ski_region_id: "paradiski",
    ski_region_name: "Les Arcs",
    stay_destination_id: "les-arcs",
    stay_destination_name: "Les Arcs",
    stay_base_id: "arc-1800",
    stay_base_name: "Arc 1800",
    ski_area_id: "les-arcs-area",
    ski_area_name: "Les Arcs",
    selected_pass: {
      ...tignesConfiguration.selected_pass,
      lift_pass_product_id: "paradiski-pass",
      name: "Paradiski pass",
    },
    fit_score: 78.2,
  };
  searchResponses = [
    response({
      results: [
        response().results[0],
        {
          ski_region_id: "paradiski",
          ski_region_name: "Les Arcs",
          rank: 2,
          fit_score: 78.2,
          top_configuration: secondConfiguration,
          alternative_configurations: [],
        },
      ],
    }),
  ];
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  const firstToggle = await screen.findByRole("button", {
    name: /collapse tignes - val d'isere/i,
  });
  const secondToggle = screen.getByRole("button", { name: /expand les arcs/i });
  expect(firstToggle).toHaveAttribute("aria-expanded", "true");
  expect(secondToggle).toHaveAttribute("aria-expanded", "false");

  await user.click(secondToggle);
  expect(firstToggle).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("button", { name: /collapse les arcs/i })).toHaveAttribute(
    "aria-expanded",
    "true",
  );
  expect(screen.queryByText("search-v4-policy-1")).not.toBeInTheDocument();
  expect(screen.queryByText(/filtered out/i)).not.toBeInTheDocument();
});

test("skipping advances the refinement queue without a request", async () => {
  searchResponses = [
    response({
      refinements: [
        {
          question_id: "first",
          question: "First refinement?",
          reason: "First reason.",
          options: [
            {
              label: "First option",
              description: "First tradeoff.",
              group_priority_patches: [],
              factor_preference_patches: [],
              objective_patches: [],
            },
          ],
        },
        {
          question_id: "second",
          question: "Second refinement?",
          reason: "Second reason.",
          options: [
            {
              label: "Second option",
              description: "Second tradeoff.",
              group_priority_patches: [],
              factor_preference_patches: [],
              objective_patches: [],
            },
          ],
        },
      ],
    }),
  ];
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  expect(await screen.findByText("First refinement?")).toBeInTheDocument();
  expect(screen.queryByText("Second refinement?")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /skip for now/i }));
  expect(screen.queryByText("First refinement?")).not.toBeInTheDocument();
  expect(screen.getByText("Second refinement?")).toBeInTheDocument();
  expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(1);
});
