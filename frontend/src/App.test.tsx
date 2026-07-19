import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import App from "./App";
import type {
  CurrentTrip,
  CurrentTripSummary,
  SearchIntent,
  RefinementProposal,
  SearchResponse,
  SearchV4RefinementRequest,
  SearchV4RefinementResponse,
  SearchV4Configuration,
  SearchWeatherEvidenceResponse,
} from "./types";

const intent: SearchIntent = {
  constraints: {
    location: { country: "France" },
    travel_window: { month: 3 },
    lodging_budget: {
      mode: "lodging_nightly",
      maximum: 320,
      currency: "EUR",
      budget_flex: 0.1,
    },
    minimum_stay_quality: { minimum_score: (2 / 3) * 10 },
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
  evidence_profile: "fallback_heavy",
  access: {
    ski_area_access_id: "tignes-access",
    access_mode: "walk",
    lift_distance: "near",
    nearest_lift_name: "Toviere",
    distance_m: 250,
    duration_minutes: 4,
    is_direct: true,
    relationship_trust_status: "verified",
    access_mode_distance_trust_status: "verified",
  },
  selected_pass: {
    lift_pass_product_id: "tignes-pass",
    name: "Tignes - Val d'Isere pass",
    validity_scope: "local_multi_area",
    covered_ski_area_ids: ["tignes-ski-area", "val-disere-ski-area"],
    accessible_piste_km: 300,
    accessible_piste_km_evidence: {
      trust_status: "verified",
      scope: "pass",
      source_entity_id: "tignes-pass",
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
    baseline_fingerprint: "baseline-1",
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

function refinementResponse(
  updates: Partial<SearchV4RefinementResponse> = {},
): SearchV4RefinementResponse {
  return {
    search_model_version: "search-v4",
    ranking_policy_version: "search-v4-policy-1",
    baseline_fingerprint: "baseline-1",
    baseline_status: "current",
    refinement_status: "not_needed",
    fallback_used: false,
    refinements: [],
    ...updates,
    refinement_presentation_policy_version:
      updates.refinement_presentation_policy_version ??
      "search-refinement-presentation-1",
  };
}

function refinement(questionId: string, question: string): RefinementProposal {
  return {
    topic_id: `${questionId}-topic`,
    target_factor_id: `${questionId}-factor`,
    question_id: questionId,
    question,
    reason: "One answer could reorder the top results.",
    options: [
      {
        label: "Prefer this",
        description: "Apply this preference.",
        intent_changed: true,
        group_priority_patches: [],
        factor_preference_patches: [],
        objective_patches: [],
      },
    ],
  };
}

let searchResponses: SearchResponse[];
let refinementResponses: SearchV4RefinementResponse[];
let requests: Array<{ url: string; init?: RequestInit }>;
let pendingLegacyRefinements: SearchResponse["refinements"];

function lastRequest(url: string) {
  const matching = requests.filter((item) => item.url === url);
  return matching[matching.length - 1];
}

const weatherResponse: SearchWeatherEvidenceResponse = {
  weather_evidence_version: "search-weather-evidence-v1",
  status: "unavailable",
  ski_area_id: "tignes-ski-area",
  evaluated_at: "2026-07-16T12:00:00Z",
  cache_valid_until: "2099-07-16T12:05:00Z",
  unavailable_reason: "historical_evidence_unavailable",
  limitations: ["No supported historical evidence covers this ski area."],
};

const savedTrip: CurrentTrip = {
  ski_region_id: "tignes-val-disere",
  ski_region_name: "Tignes - Val d'Isere",
  stay_destination_id: "tignes",
  stay_destination_name: "Tignes",
  stay_base_id: "tignes-le-lac",
  stay_base_name: "Le Lac",
  focus_ski_area_id: "tignes-ski-area",
  focus_ski_area_name: "Tignes",
  lift_pass_product_id: "tignes-pass",
  lift_pass_product_name: "Tignes - Val d'Isere pass",
  travel_month: 3,
  booking_status: "not_booked_yet",
  created_at: "2026-07-15T00:00:00Z",
  updated_at: "2026-07-15T00:00:00Z",
  last_checked_at: null,
};

const savedTripSummary: CurrentTripSummary = {
  trip: savedTrip,
  current_conditions: {
    resort_name: "Tignes",
    snow_confidence_score: 78,
    snow_confidence_label: "good",
    availability_status: "open",
    weather_summary: "Light snow is expected this week.",
    conditions_score: 76,
    updated_at: "2026-07-19T08:00:00Z",
    source: "Historical weather model",
  },
  current_conditions_provenance: {
    source_name: "Historical weather model",
    source_type: "estimated",
    updated_at: "2026-07-19T08:00:00Z",
    freshness_status: "fresh",
    basis_summary: "Weather evidence for the saved trip window.",
  },
  comparison_basis: {
    kind: "since_trip_saved",
    baseline_at: "2026-07-15T00:00:00Z",
    label: "Since this trip was saved",
  },
  delta: {
    status: "unchanged",
    summary: "No important change since this trip was saved.",
    changes: [],
  },
  companion_status: {
    trip_window_status: "upcoming",
    trip_window_label: "Upcoming trip",
    notification_eligible: true,
    eligibility_reason: "The trip is upcoming.",
    actionable_change_available: false,
  },
};

const previousTrip: CurrentTrip = {
  ...savedTrip,
  ski_region_id: "les-arcs",
  ski_region_name: "Les Arcs",
  stay_destination_id: "bourg-saint-maurice",
  stay_destination_name: "Bourg-Saint-Maurice",
  stay_base_id: "arc-1800",
  stay_base_name: "Arc 1800",
  focus_ski_area_id: "les-arcs-ski-area",
  focus_ski_area_name: "Les Arcs",
  lift_pass_product_id: "les-arcs-pass",
  lift_pass_product_name: "Les Arcs pass",
};

const previousTripSummary: CurrentTripSummary = {
  ...savedTripSummary,
  trip: previousTrip,
  current_conditions: {
    ...savedTripSummary.current_conditions,
    resort_name: "Les Arcs",
    weather_summary: "Trip A conditions must not appear for trip B.",
  },
};

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  vi.stubGlobal("scrollTo", vi.fn());
  searchResponses = [response()];
  refinementResponses = [];
  pendingLegacyRefinements = [];
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
        const nextResponse = searchResponses.shift() ?? response();
        pendingLegacyRefinements = nextResponse.refinements;
        return new Response(JSON.stringify(nextResponse), {
          status: 200,
        });
      }
      if (url === "/api/search/refinements") {
        const nextResponse =
          refinementResponses.shift() ??
          refinementResponse(
            pendingLegacyRefinements.length
              ? {
                  refinement_status: "questions_available",
                  refinements: pendingLegacyRefinements,
                }
              : {},
          );
        pendingLegacyRefinements = [];
        return new Response(JSON.stringify(nextResponse), { status: 200 });
      }
      if (url === "/api/search/weather-evidence") {
        return new Response(JSON.stringify(weatherResponse), { status: 200 });
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
  vi.useRealTimers();
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

test("keeps origin-based travel ranking visible after removing the hard drive limit", async () => {
  const originOnlyIntent: SearchIntent = {
    ...intent,
    travel_context: { origin_text: "Warsaw", mode: "car" },
  };
  const limitedIntent: SearchIntent = {
    ...originOnlyIntent,
    constraints: {
      ...originOnlyIntent.constraints,
      travel_limit: { maximum_duration_hours: 15, mode: "car" },
    },
  };
  searchResponses = [
    response({ applied_intent: limitedIntent }),
    response({ applied_intent: originOnlyIntent }),
    response(),
  ];
  const user = userEvent.setup();
  render(<App />);

  await openFilters(user);
  await user.type(screen.getByLabelText("Origin"), "Warsaw");
  await user.type(screen.getByLabelText("Hard drive limit"), "15");
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("button", { name: "Remove Prefer closer to Warsaw" }),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Adjust" }));
  await user.clear(screen.getByLabelText("Country"));
  await user.type(screen.getByLabelText("Country"), "Italy");
  await user.clear(screen.getByLabelText("Origin"));
  await user.type(screen.getByLabelText("Origin"), "Berlin");
  await user.selectOptions(screen.getByLabelText("Travel window"), "dates");
  await user.type(screen.getByLabelText("Trip start date"), "2027-01-16");
  await user.type(screen.getByLabelText("Trip end date"), "2027-01-20");
  await user.click(screen.getByRole("button", { name: /close filters/i }));

  await user.click(
    screen.getByRole("button", { name: "Remove Max 15 hours by car" }),
  );

  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(2);
  });
  const withoutLimit = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[1].init?.body),
  );
  expect(withoutLimit.intent.constraints.travel_limit).toBeUndefined();
  expect(withoutLimit.intent.constraints.location).toEqual({ country: "France" });
  expect(withoutLimit.intent.constraints.travel_window).toEqual({ month: 3 });
  expect(withoutLimit.intent.travel_context).toEqual({
    origin_text: "Warsaw",
    mode: "car",
  });
  expect(
    screen.getByRole("button", { name: "Remove Prefer closer to Warsaw" }),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Adjust" }));
  expect(screen.getByLabelText("Country")).toHaveValue("Italy");
  expect(screen.getByLabelText("Origin")).toHaveValue("Berlin");
  expect(screen.getByLabelText("Hard drive limit")).toHaveValue(null);
  expect(screen.getByLabelText("Travel window")).toHaveValue("dates");
  expect(screen.getByLabelText("Trip start date")).toHaveValue("2027-01-16");
  expect(screen.getByLabelText("Trip end date")).toHaveValue("2027-01-20");
  await user.click(screen.getByRole("button", { name: /close filters/i }));

  await user.click(
    screen.getByRole("button", { name: "Remove Prefer closer to Warsaw" }),
  );
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(3);
  });
  const withoutOrigin = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[2].init?.body),
  );
  expect(withoutOrigin.intent.travel_context).toEqual({});
  expect(withoutOrigin.intent.constraints.travel_limit).toBeUndefined();
});

test("restores the previous month when Month mode is selected again", async () => {
  const { travel_window: _travelWindow, ...constraintsWithoutWindow } =
    intent.constraints;
  const anytimeIntent: SearchIntent = {
    ...intent,
    constraints: constraintsWithoutWindow,
  };
  searchResponses = [
    response(),
    response({ applied_intent: anytimeIntent }),
    response(),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("button", { name: "Remove March window" }),
  );
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(2);
  });

  await user.click(screen.getByRole("button", { name: "Adjust" }));
  await user.selectOptions(screen.getByLabelText("Travel window"), "month");
  expect(screen.getByLabelText("Travel month")).toHaveValue("3");
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /update results/i }));

  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(3);
  });
  const restoredMonth = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[2].init?.body),
  );
  expect(restoredMonth.intent.constraints.travel_window).toEqual({ month: 3 });
});

test("posts one typed Search V4 request and renders fit and evidence", async () => {
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeInTheDocument();
  expect(screen.getByText("82.4")).toBeInTheDocument();
  expect(screen.getAllByText("300 km covered by this pass")).toHaveLength(2);
  expect(screen.getByText(/estimated EUR 180-255\/night/i)).toBeInTheDocument();
  const searchRequest = requests.find((item) => item.url === "/api/search");
  expect(searchRequest?.init?.method).toBe("POST");
  const body = JSON.parse(String(searchRequest?.init?.body));
  expect(body).toEqual({ intent });

  expect(
    screen.getByRole("button", { name: /collapse tignes - val d'isere/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/show scoring details/i)).toBeInTheDocument();
  expect(screen.getByText("Unknown")).toBeInTheDocument();
});

test("renders ranking before a separate refinement request resolves", async () => {
  let resolveRefinement: ((response: Response) => void) | undefined;
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
      if (url === "/api/search") {
        return Promise.resolve(
          new Response(JSON.stringify(response()), { status: 200 }),
        );
      }
      if (url === "/api/search/refinements") {
        return new Promise<Response>((resolve) => {
          resolveRefinement = resolve;
        });
      }
      return Promise.resolve(new Response(null, { status: 404 }));
    }),
  );
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();
  expect(
    screen.getByText("Checking whether one answer could improve this ranking.", {
      selector: ".contextual-refinement > p",
    }),
  ).toBeVisible();
  const searchRequest = requests.find((item) => item.url === "/api/search");
  expect(JSON.parse(String(searchRequest?.init?.body))).toEqual({ intent });
  const refinementRequest = requests.find(
    (item) => item.url === "/api/search/refinements",
  );
  expect(JSON.parse(String(refinementRequest?.init?.body))).toEqual({
    intent,
    brief: null,
    baseline_fingerprint: "baseline-1",
    already_answered_question_ids: [],
    resolved_topic_ids: [],
  });

  resolveRefinement?.(
    new Response(
      JSON.stringify(
        refinementResponse({
          refinement_status: "questions_available",
          refinements: [refinement("focus-safe", "What matters most?")],
        }),
      ),
      { status: 200 },
    ),
  );
  await waitFor(() => {
    expect(
      screen.queryByText("Checking whether one answer could improve this ranking."),
    ).not.toBeInTheDocument();
  });
  expect(
    screen.getByRole("heading", { level: 2, name: "What matters most?" }),
  ).toBeVisible();
  expect(
    screen.getByRole("heading", { name: "Recommended ski trips" }),
  ).toHaveFocus();
});

test("skips refinement discovery when no result is eligible", async () => {
  searchResponses = [
    response({ eligible_candidate_count: 0, results: [] }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", {
      name: /no trip matches every hard constraint/i,
    }),
  ).toBeVisible();
  expect(
    requests.some((item) => item.url === "/api/search/refinements"),
  ).toBe(false);
  expect(screen.queryByText(/no follow-up/i)).toBeNull();
});

test("keeps ranked results when refinement discovery is rate limited", async () => {
  refinementResponses = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(JSON.stringify(response()), { status: 200 });
      }
      if (url === "/api/search/refinements") {
        return new Response(
          JSON.stringify({ detail: "Too many refinement requests." }),
          { status: 429 },
        );
      }
      return new Response(null, { status: 404 });
    }),
  );
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();
  expect(await screen.findByRole("status")).toHaveTextContent(
    "No additional refinement is available right now. Your results are unchanged.",
  );
  expect(document.querySelector(".contextual-refinement")).toBeNull();
  expect(
    screen.queryByText(/snowcast is temporarily unavailable/i),
  ).not.toBeInTheDocument();
});

test("retries one admitted refinement request after Retry-After without replacing results", async () => {
  vi.useFakeTimers();
  let refinementCount = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(JSON.stringify(response()), { status: 200 });
      }
      if (url === "/api/search/refinements") {
        refinementCount += 1;
        if (refinementCount === 1) {
          return new Response(JSON.stringify({ detail: "Admission limited." }), {
            status: 429,
            headers: { "Retry-After": "10" },
          });
        }
        return new Response(
          JSON.stringify(
            refinementResponse({
              refinement_status: "questions_available",
              refinements: [refinement("retry-question", "Which trade-off matters?")],
            }),
          ),
          { status: 200 },
        );
      }
      return new Response(null, { status: 404 });
    }),
  );
  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /find resorts/i }));
  await act(() => vi.advanceTimersByTimeAsync(0));

  expect(screen.getByText("Tignes - Val d'Isere")).toBeVisible();
  expect(
    screen.getByText(
      "Snowcast is waiting a moment before checking for another useful question.",
      { selector: ".contextual-refinement > p" },
    ),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Adjust" })).toBeEnabled();
  expect(refinementCount).toBe(1);

  await act(() => vi.advanceTimersByTimeAsync(9_999));
  expect(refinementCount).toBe(1);
  await act(() => vi.advanceTimersByTimeAsync(1));

  expect(screen.getByRole("heading", { name: "Which trade-off matters?" })).toBeVisible();
  expect(refinementCount).toBe(2);
  const bodies = requests
    .filter((item) => item.url === "/api/search/refinements")
    .map((item) => JSON.parse(String(item.init?.body)));
  expect(bodies).toHaveLength(2);
  expect(bodies[1]).toEqual(bodies[0]);
});

test("a new ranking aborts a pending refinement retry before its search resolves", async () => {
  vi.useFakeTimers();
  let searchCount = 0;
  let resolveSecondSearch: ((response: Response) => void) | undefined;
  const refinementBodies: SearchV4RefinementRequest[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        searchCount += 1;
        const requestIntent = JSON.parse(String(init?.body)).intent as SearchIntent;
        const searchResponse = new Response(
          JSON.stringify(
            response({
              baseline_fingerprint: `baseline-${searchCount}`,
              applied_intent: requestIntent,
            }),
          ),
          { status: 200 },
        );
        if (searchCount === 2) {
          return new Promise<Response>((resolve) => {
            resolveSecondSearch = resolve;
          });
        }
        return searchResponse;
      }
      if (url === "/api/search/refinements") {
        const body = JSON.parse(String(init?.body)) as SearchV4RefinementRequest;
        refinementBodies.push(body);
        if (body.baseline_fingerprint === "baseline-1") {
          if (
            refinementBodies.filter(
              (candidate) => candidate.baseline_fingerprint === "baseline-1",
            ).length === 1
          ) {
            return new Response(JSON.stringify({ detail: "Admission limited." }), {
              status: 429,
              headers: { "Retry-After": "10" },
            });
          }
          return new Response(
            JSON.stringify(
              refinementResponse({
                refinement_status: "questions_available",
                refinements: [refinement("old-question", "Outdated question?")],
              }),
            ),
            { status: 200 },
          );
        }
        return new Response(
          JSON.stringify(
            refinementResponse({
              baseline_fingerprint: "baseline-2",
              refinement_status: "not_needed",
            }),
          ),
          { status: 200 },
        );
      }
      return new Response(null, { status: 404 });
    }),
  );
  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /find resorts/i }));
  await act(() => vi.advanceTimersByTimeAsync(0));
  screen.getByText(
    "Snowcast is waiting a moment before checking for another useful question.",
    { selector: ".contextual-refinement > p" },
  );
  fireEvent.click(
    screen.getByRole("button", { name: /remove optimize terrain per pass price/i }),
  );
  await act(() => vi.advanceTimersByTimeAsync(0));
  expect(searchCount).toBe(2);
  await act(() => vi.advanceTimersByTimeAsync(10_000));

  expect(
    refinementBodies.filter((body) => body.baseline_fingerprint === "baseline-1"),
  ).toHaveLength(1);
  expect(screen.queryByText("Outdated question?")).not.toBeInTheDocument();

  resolveSecondSearch?.(
    new Response(
      JSON.stringify(
        response({
          baseline_fingerprint: "baseline-2",
          applied_intent: {
            ...intent,
            objectives: [],
          },
        }),
      ),
      { status: 200 },
    ),
  );
  await act(() => vi.advanceTimersByTimeAsync(0));
  expect(
    refinementBodies.filter((body) => body.baseline_fingerprint === "baseline-2"),
  ).toHaveLength(1);
});

test("unmount aborts a pending refinement retry", async () => {
  vi.useFakeTimers();
  let refinementCount = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(JSON.stringify(response()), { status: 200 });
      }
      if (url === "/api/search/refinements") {
        refinementCount += 1;
        return new Response(JSON.stringify({ detail: "Admission limited." }), {
          status: 429,
          headers: { "Retry-After": "10" },
        });
      }
      return new Response(null, { status: 404 });
    }),
  );
  const view = render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /find resorts/i }));
  await act(() => vi.advanceTimersByTimeAsync(0));
  screen.getByText(
    "Snowcast is waiting a moment before checking for another useful question.",
    { selector: ".contextual-refinement > p" },
  );
  view.unmount();
  await act(() => vi.advanceTimersByTimeAsync(10_000));

  expect(refinementCount).toBe(1);
});

test("a second admission limit terminates the single retry cycle", async () => {
  vi.useFakeTimers();
  let refinementCount = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(JSON.stringify(response()), { status: 200 });
      }
      if (url === "/api/search/refinements") {
        refinementCount += 1;
        return new Response(JSON.stringify({ detail: "Admission limited." }), {
          status: 429,
          headers: { "Retry-After": "1" },
        });
      }
      return new Response(null, { status: 404 });
    }),
  );
  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: /find resorts/i }));
  await act(() => vi.advanceTimersByTimeAsync(0));
  screen.getByText(
    "Snowcast is waiting a moment before checking for another useful question.",
    { selector: ".contextual-refinement > p" },
  );
  await act(() => vi.advanceTimersByTimeAsync(1_000));

  expect(screen.getByRole("status")).toHaveTextContent(
    "No additional refinement is available right now. Your results are unchanged.",
  );
  expect(refinementCount).toBe(2);
  await act(() => vi.advanceTimersByTimeAsync(20_000));
  expect(refinementCount).toBe(2);
  expect(document.querySelector(".contextual-refinement")).toBeNull();
});

test.each(["long Retry-After", "network failure"] as const)(
  "does not retry a terminal %s",
  async (failure) => {
    let refinementCount = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/current-trip") {
          return new Response(JSON.stringify({ trip: null }), { status: 200 });
        }
        if (url === "/api/search") {
          return new Response(JSON.stringify(response()), { status: 200 });
        }
        if (url === "/api/search/refinements") {
          refinementCount += 1;
          if (failure === "network failure") throw new TypeError("offline");
          return new Response(JSON.stringify({ detail: "Admission limited." }), {
            status: 429,
            headers: { "Retry-After": "16" },
          });
        }
        return new Response(null, { status: 404 });
      }),
    );
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /find resorts/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "No additional refinement is available right now. Your results are unchanged.",
    );
    expect(refinementCount).toBe(1);
    expect(document.querySelector(".contextual-refinement")).toBeNull();
  },
);

test("keeps refinement validation details out of the traveller-facing UI", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(JSON.stringify(response()), { status: 200 });
      }
      if (url === "/api/search/refinements") {
        return new Response(
          JSON.stringify({
            detail: [
              {
                loc: ["body", "intent", "constraints", "travel_window", "mode"],
                msg: "Extra inputs are not permitted",
              },
            ],
          }),
          { status: 422 },
        );
      }
      return new Response(null, { status: 404 });
    }),
  );
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();
  expect(await screen.findByRole("status")).toHaveTextContent(
    "No additional refinement is available right now. Your results are unchanged.",
  );
  expect(document.querySelector(".contextual-refinement")).toBeNull();
  expect(screen.queryByText(/extra inputs are not permitted/i)).not.toBeInTheDocument();
});

test("shows the slow refinement message without blocking the ranking", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  let resolveRefinement: ((response: Response) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/current-trip") {
        return Promise.resolve(
          new Response(JSON.stringify({ trip: null }), { status: 200 }),
        );
      }
      if (url === "/api/search") {
        return Promise.resolve(
          new Response(JSON.stringify(response()), { status: 200 }),
        );
      }
      if (url === "/api/search/refinements") {
        return new Promise<Response>((resolve) => {
          resolveRefinement = resolve;
        });
      }
      return Promise.resolve(new Response(null, { status: 404 }));
    }),
  );
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();

  await act(() => vi.advanceTimersByTimeAsync(2_500));

  expect(
    screen.getByText(
      "Your ranking is ready. Snowcast is checking whether one answer could improve it.",
      { selector: ".contextual-refinement > p" },
    ),
  ).toBeVisible();
  resolveRefinement?.(
    new Response(JSON.stringify(refinementResponse()), { status: 200 }),
  );
  await act(() => vi.runAllTimersAsync());
});

test("suppresses questions for a stale baseline or ranking policy", async () => {
  refinementResponses = [
    refinementResponse({
      ranking_policy_version: "search-v4-policy-newer",
      baseline_fingerprint: "baseline-stale",
      baseline_status: "stale",
      refinement_status: "questions_available",
      refinements: [refinement("stale-question", "Should not appear?")],
    }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();
  expect(
    await screen.findByText("A newer ranking replaced this refinement check.", {
      selector: ".contextual-refinement > p",
    }),
  ).toBeVisible();
  expect(screen.queryByText("Should not appear?")).not.toBeInTheDocument();
});

test("keeps ranking usable when a timed-out refinement baseline is unverified", async () => {
  refinementResponses = [
    refinementResponse({
      baseline_status: "unverified",
      refinement_status: "temporarily_unavailable",
      refinements: [],
    }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();
  expect(await screen.findByRole("status")).toHaveTextContent(
    "No additional refinement is available right now. Your results are unchanged.",
  );
  expect(document.querySelector(".contextual-refinement")).toBeNull();
  expect(
    screen.queryByText("A newer ranking replaced this refinement check."),
  ).not.toBeInTheDocument();
});

test("does not retry a current-baseline provider temporarily unavailable response", async () => {
  let refinementCount = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(JSON.stringify(response()), { status: 200 });
      }
      if (url === "/api/search/refinements") {
        refinementCount += 1;
        return new Response(
          JSON.stringify(
            refinementResponse({
              baseline_status: "current",
              refinement_status: "temporarily_unavailable",
              refinements: [],
            }),
          ),
          { status: 200 },
        );
      }
      return new Response(null, { status: 404 });
    }),
  );
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();
  expect(await screen.findByRole("status")).toHaveTextContent(
    "No additional refinement is available right now. Your results are unchanged.",
  );
  expect(refinementCount).toBe(1);
  expect(document.querySelector(".contextual-refinement")).toBeNull();
});

test("aborts and ignores a superseded refinement response", async () => {
  let firstRefinementResolve: ((response: Response) => void) | undefined;
  const refinementSignals: AbortSignal[] = [];
  let searchCount = 0;
  let refinementCount = 0;
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
      if (url === "/api/search") {
        searchCount += 1;
        const requestIntent = JSON.parse(String(init?.body)).intent as SearchIntent;
        return Promise.resolve(
          new Response(
            JSON.stringify(
              response({
                baseline_fingerprint: `baseline-${searchCount}`,
                applied_intent: requestIntent,
              }),
            ),
            { status: 200 },
          ),
        );
      }
      if (url === "/api/search/refinements") {
        refinementCount += 1;
        if (refinementCount === 1) {
          if (init?.signal) refinementSignals.push(init.signal);
          return new Promise<Response>((resolve) => {
            firstRefinementResolve = resolve;
          });
        }
        return Promise.resolve(
          new Response(
            JSON.stringify(
              refinementResponse({
                baseline_fingerprint: "baseline-2",
                refinement_status: "questions_available",
                refinements: [refinement("new-question", "Newest question?")],
              }),
            ),
            { status: 200 },
          ),
        );
      }
      return Promise.resolve(new Response(null, { status: 404 }));
    }),
  );
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();
  await user.click(
    screen.getByRole("button", {
      name: /remove optimize terrain per pass price/i,
    }),
  );

  expect(await screen.findByText("Newest question?")).toBeVisible();
  expect(refinementSignals[0]?.aborted).toBe(true);

  firstRefinementResolve?.(
    new Response(
      JSON.stringify(
        refinementResponse({
          refinement_status: "questions_available",
          refinements: [refinement("old-question", "Outdated question?")],
        }),
      ),
      { status: 200 },
    ),
  );
  await waitFor(() => {
    expect(screen.queryByText("Outdated question?")).not.toBeInTheDocument();
  });
});

test("renders readable FastAPI validation details for a failed search", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(
          JSON.stringify({
            detail: [
              {
                loc: ["body", "intent", "constraints", "travel_window"],
                msg: "Choose a valid travel window",
                type: "value_error",
              },
            ],
          }),
          { status: 422 },
        );
      }
      return new Response(null, { status: 404 });
    }),
  );
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("alert"),
  ).toHaveTextContent("Travel window: Choose a valid travel window");
});

test("bounds the separate refinement brief at 2000 characters", async () => {
  const user = userEvent.setup();
  render(<App />);
  fireEvent.change(screen.getByLabelText("Describe your ski trip"), {
    target: { value: "x".repeat(2_100) },
  });

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  await waitFor(() => {
    expect(
      requests.some((item) => item.url === "/api/search/refinements"),
    ).toBe(true);
  });
  const request = requests.find(
    (item) => item.url === "/api/search/refinements",
  );
  expect(JSON.parse(String(request?.init?.body)).brief).toHaveLength(2_000);
});

test("opens the selected candidate dossier without rerunning search and saves it", async () => {
  const alternative = {
    ...tignesConfiguration,
    candidate_id: "tignes-access--local-pass",
    selected_pass: {
      ...tignesConfiguration.selected_pass,
      lift_pass_product_id: "local-pass",
      name: "Tignes local pass",
    },
  };
  searchResponses = [
    response({
      results: [
        {
          ...response().results[0],
          alternative_configurations: [alternative],
        },
      ],
    }),
  ];
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    screen.getByRole("button", { name: /select le lac with tignes local pass/i }),
  );
  await user.click(screen.getByRole("link", { name: "View dossier" }));

  expect(window.location.pathname).toBe("/recommendations/tignes-val-disere");
  expect(window.location.search).toBe("?candidate=tignes-access--local-pass");
  expect(
    await screen.findByRole("heading", { name: "Tignes - Val d'Isere - Le Lac" }),
  ).toBeInTheDocument();
  expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(1);
  await screen.findByRole("heading", { name: "Snow evidence unavailable" });
  const weatherRequest = requests.find(
    (item) => item.url === "/api/search/weather-evidence",
  );
  expect(weatherRequest?.init?.method).toBe("POST");
  expect(JSON.parse(String(weatherRequest?.init?.body))).toEqual({
    intent,
    ski_area_id: "tignes-ski-area",
  });

  await user.click(screen.getByRole("button", { name: "Save as current trip" }));
  const saveRequest = requests.find(
    (item) => item.url === "/api/current-trip" && item.init?.method === "PUT",
  );
  expect(JSON.parse(String(saveRequest?.init?.body)).lift_pass_product_id).toBe(
    "local-pass",
  );
});

test("shows and retries a failed saved-trip load", async () => {
  window.history.replaceState(null, "", "/current-trip");
  let tripLoadAttempts = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/current-trip" && (!init?.method || init.method === "GET")) {
        tripLoadAttempts += 1;
        if (tripLoadAttempts === 1) throw new TypeError("Failed to fetch");
        return new Response(JSON.stringify({ trip: savedTrip }), { status: 200 });
      }
      if (url === "/api/current-trip/summary") {
        return new Response(null, { status: 404 });
      }
      return new Response(null, { status: 404 });
    }),
  );
  const user = userEvent.setup();

  render(<App />);

  const error = await screen.findByRole("alert");
  expect(error).toHaveTextContent("Saved trip could not be loaded");
  expect(error).toHaveTextContent("Check your connection and try again.");
  expect(error).not.toHaveTextContent(/failed to fetch|api|backend/i);

  await user.click(screen.getByRole("button", { name: "Retry saved trip" }));

  expect(
    await screen.findByRole("heading", { name: "Tignes - Val d'Isere" }),
  ).toBeVisible();
  expect(screen.queryByText("Saved trip could not be loaded")).toBeNull();
  expect(tripLoadAttempts).toBe(2);
});

test("keeps an absent saved trip as an empty state", async () => {
  window.history.replaceState(null, "", "/current-trip");
  render(<App />);

  expect(
    await screen.findByText(/save a ranked configuration.*to track it/i),
  ).toBeVisible();
  await waitFor(() =>
    expect(requests.filter((item) => item.url === "/api/current-trip")).toHaveLength(1),
  );
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.queryByRole("button", { name: "Retry saved trip" })).toBeNull();
});

test("keeps current conditions visible when refresh fails and retries them", async () => {
  window.history.replaceState(null, "", "/current-trip");
  let summaryLoadAttempts = 0;
  const refreshedSummary: CurrentTripSummary = {
    ...savedTripSummary,
    current_conditions: {
      ...savedTripSummary.current_conditions,
      weather_summary: "Fresh snow is now expected before the trip.",
    },
    delta: {
      status: "changed",
      summary: "Snow confidence has improved since this trip was saved.",
      changes: ["Snow confidence improved."],
    },
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/current-trip" && (!init?.method || init.method === "GET")) {
        return new Response(JSON.stringify({ trip: savedTrip }), { status: 200 });
      }
      if (url === "/api/current-trip/summary") {
        summaryLoadAttempts += 1;
        if (summaryLoadAttempts === 1) {
          return new Response(JSON.stringify(savedTripSummary), { status: 200 });
        }
        if (summaryLoadAttempts === 2) throw new TypeError("Failed to fetch");
        return new Response(JSON.stringify(refreshedSummary), { status: 200 });
      }
      return new Response(null, { status: 404 });
    }),
  );
  const user = userEvent.setup();

  render(<App />);
  expect(await screen.findByText("Light snow is expected this week.")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Back to search" }));
  await user.click(screen.getByRole("button", { name: "Current trip" }));

  const error = await screen.findByRole("alert");
  expect(error).toHaveTextContent("Current conditions could not be updated");
  expect(error).toHaveTextContent("Check your connection and try again.");
  expect(error).not.toHaveTextContent(/failed to fetch|api|backend/i);
  expect(screen.getByText("Light snow is expected this week.")).toBeVisible();

  await user.click(
    screen.getByRole("button", { name: "Retry current conditions" }),
  );

  expect(
    await screen.findByText("Fresh snow is now expected before the trip."),
  ).toBeVisible();
  expect(screen.queryByText("Current conditions could not be updated")).toBeNull();
  expect(summaryLoadAttempts).toBe(3);
});

test("ignores trip A summary when a pending save replaces it with trip B", async () => {
  window.history.replaceState(null, "", "/current-trip");
  const baseFetch = fetch;
  let summaryLoads = 0;
  let resolveSave: ((response: Response) => void) | undefined;
  let resolveTripASummary: ((response: Response) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/current-trip" && (!init?.method || init.method === "GET")) {
        return Promise.resolve(
          new Response(JSON.stringify({ trip: previousTrip }), { status: 200 }),
        );
      }
      if (url === "/api/current-trip/summary") {
        summaryLoads += 1;
        if (summaryLoads === 1) {
          return Promise.resolve(new Response(null, { status: 404 }));
        }
        if (summaryLoads === 2) {
          return new Promise<Response>((resolve) => {
            resolveTripASummary = resolve;
          });
        }
        return new Promise<Response>(() => undefined);
      }
      if (url === "/api/current-trip" && init?.method === "PUT") {
        return new Promise<Response>((resolve) => {
          resolveSave = resolve;
        });
      }
      return baseFetch(input, init);
    }),
  );
  const user = userEvent.setup();

  render(<App />);
  expect(await screen.findByRole("heading", { name: "Les Arcs" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Back to search" }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("button", { name: "Save as current trip" }),
  );
  await waitFor(() => expect(resolveSave).toBeDefined());
  await user.click(screen.getByRole("button", { name: "Current trip" }));
  expect(await screen.findByRole("heading", { name: "Les Arcs" })).toBeVisible();
  await waitFor(() => expect(resolveTripASummary).toBeDefined());

  await act(async () => {
    resolveSave?.(new Response(JSON.stringify(savedTrip), { status: 200 }));
    resolveTripASummary?.(
      new Response(JSON.stringify(previousTripSummary), { status: 200 }),
    );
    await Promise.resolve();
  });

  expect(
    await screen.findByRole("heading", { name: "Tignes - Val d'Isere" }),
  ).toBeVisible();
  expect(
    screen.queryByText("Trip A conditions must not appear for trip B."),
  ).toBeNull();
});

test("ignores trip A summary when clear completes before a pending trip B save", async () => {
  window.history.replaceState(null, "", "/current-trip");
  const baseFetch = fetch;
  let summaryLoads = 0;
  let resolveSave: ((response: Response) => void) | undefined;
  let resolveClear: ((response: Response) => void) | undefined;
  let resolveTripASummary: ((response: Response) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      if (url === "/api/current-trip" && (!init?.method || init.method === "GET")) {
        return Promise.resolve(
          new Response(JSON.stringify({ trip: previousTrip }), { status: 200 }),
        );
      }
      if (url === "/api/current-trip/summary") {
        summaryLoads += 1;
        if (summaryLoads === 1) {
          return Promise.resolve(new Response(null, { status: 404 }));
        }
        if (summaryLoads === 2) {
          return new Promise<Response>((resolve) => {
            resolveTripASummary = resolve;
          });
        }
        return new Promise<Response>(() => undefined);
      }
      if (url === "/api/current-trip" && init?.method === "PUT") {
        return new Promise<Response>((resolve) => {
          resolveSave = resolve;
        });
      }
      if (url === "/api/current-trip" && init?.method === "DELETE") {
        return new Promise<Response>((resolve) => {
          resolveClear = resolve;
        });
      }
      return baseFetch(input, init);
    }),
  );
  const user = userEvent.setup();

  render(<App />);
  expect(await screen.findByRole("heading", { name: "Les Arcs" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Back to search" }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("button", { name: "Save as current trip" }),
  );
  await waitFor(() => expect(resolveSave).toBeDefined());
  await user.click(screen.getByRole("button", { name: "Current trip" }));
  await waitFor(() => expect(resolveTripASummary).toBeDefined());
  await user.click(screen.getByRole("button", { name: "Clear current trip" }));
  await waitFor(() => expect(resolveClear).toBeDefined());

  await act(async () => {
    resolveClear?.(new Response(null, { status: 204 }));
    resolveSave?.(new Response(JSON.stringify(savedTrip), { status: 200 }));
    resolveTripASummary?.(
      new Response(JSON.stringify(previousTripSummary), { status: 200 }),
    );
    await Promise.resolve();
  });

  expect(
    await screen.findByRole("heading", { name: "Tignes - Val d'Isere" }),
  ).toBeVisible();
  expect(
    screen.queryByText("Trip A conditions must not appear for trip B."),
  ).toBeNull();
});

test("keeps the current trip and handles a failed clear action", async () => {
  window.history.replaceState(null, "", "/current-trip");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/current-trip" && (!init?.method || init.method === "GET")) {
        return new Response(JSON.stringify({ trip: savedTrip }), { status: 200 });
      }
      if (url === "/api/current-trip" && init?.method === "DELETE") {
        throw new TypeError("Failed to fetch");
      }
      return new Response(null, { status: 404 });
    }),
  );
  const unhandledRejection = vi.fn();
  window.addEventListener("unhandledrejection", unhandledRejection);
  const user = userEvent.setup();

  try {
    render(<App />);
    expect(
      await screen.findByRole("heading", { name: "Tignes - Val d'Isere" }),
    ).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Clear current trip" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to remove current trip. Check your connection and try again.",
    );
    expect(
      screen.getByRole("heading", { name: "Tignes - Val d'Isere" }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Clear current trip" }),
    ).toBeVisible();
    await act(async () => Promise.resolve());
    expect(unhandledRejection).not.toHaveBeenCalled();
  } finally {
    window.removeEventListener("unhandledrejection", unhandledRejection);
  }
});

test("restores result state and scroll after returning from a dossier", async () => {
  const user = userEvent.setup();
  Object.defineProperty(window, "scrollY", { configurable: true, value: 428 });
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(screen.getByRole("link", { name: "View dossier" }));
  await screen.findByRole("heading", { name: /tignes - val d'isere - le lac/i });
  await user.click(screen.getByRole("button", { name: "All results" }));

  expect(await screen.findByRole("heading", { name: /recommended ski trips/i })).toBeVisible();
  await waitFor(() => expect(window.scrollTo).toHaveBeenCalledWith(0, 428));
  expect(
    screen.getByRole("button", { name: /collapse tignes - val d'isere/i }),
  ).toHaveAttribute("aria-expanded", "true");
  expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(1);
});

test("recovers a direct dossier route without browser-session search state", async () => {
  window.history.replaceState(
    null,
    "",
    "/recommendations/tignes-val-disere?candidate=missing",
  );
  const user = userEvent.setup();
  render(<App />);

  expect(screen.getByRole("heading", { name: "Run a search first" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Return to search" }));
  expect(window.location.pathname).toBe("/");
  expect(screen.getByLabelText("Describe your ski trip")).toBeVisible();
  expect(requests.some((item) => item.url === "/api/search")).toBe(false);
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
          topic_id: "local_apres",
          target_factor_id: "local_apres",
          question_id: "evening-style",
          question: "Would you prefer lively après or a quieter base?",
          reason: "The answer changes the leading stay base.",
          options: [
            {
              label: "Lively après",
              description: "Prefer a lively local après profile.",
              intent_changed: true,
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
              intent_changed: true,
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
    response({
      applied_intent: {
        ...intent,
        factor_preferences: [
          {
            factor_id: "local_apres",
            mode: "prefer",
            values: ["lively"],
            importance: "normal",
          },
        ],
      },
    }),
    response(),
  ];
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  expect(
    await screen.findByRole("heading", {
      level: 2,
      name: /would you prefer lively après/i,
    }),
  ).toBeInTheDocument();

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
    screen.getByText("This changes how your current matches are evaluated."),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));
  expect(livelyOption).toBeDisabled();
  expect(screen.getByRole("heading", { name: /tignes - val d'isere/i })).toBeVisible();
  expect(
    screen.getByText(/reranking these recommendations/i),
  ).toBeInTheDocument();
  expect(
    requests.filter((item) => item.url === "/api/search/refinements"),
  ).toHaveLength(1);
  resolveRefinedSearch?.(
    new Response(
      JSON.stringify(
        response({
          applied_intent: {
            ...intent,
            factor_preferences: [
              {
                factor_id: "local_apres",
                mode: "prefer",
                values: ["lively"],
                importance: "normal",
              },
            ],
          },
        }),
      ),
      { status: 200 },
    ),
  );

  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(2);
    expect(
      requests.filter((item) => item.url === "/api/search/refinements"),
    ).toHaveLength(2);
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
  const latestRefinementRequest = lastRequest("/api/search/refinements");
  expect(
    JSON.parse(String(latestRefinementRequest?.init?.body))
      .already_answered_question_ids,
  ).toEqual(["evening-style"]);
  expect(
    JSON.parse(String(latestRefinementRequest?.init?.body)).resolved_topic_ids,
  ).toEqual(["local_apres"]);
  expect(screen.getByText(/prefer stay-base après: lively/i)).toBeInTheDocument();
});

test("applies a refinement to the displayed session instead of unsent drawer and brief edits", async () => {
  const appliedBrief = "Applied March trip from Warsaw";
  const appliedTravelIntent: SearchIntent = {
    ...intent,
    constraints: {
      ...intent.constraints,
      travel_limit: { maximum_duration_hours: 15, mode: "car" },
    },
    travel_context: { origin_text: "Warsaw", mode: "car" },
  };
  const pacePreference = {
    factor_id: "local_pace",
    mode: "prefer" as const,
    values: ["quiet"],
    importance: "normal" as const,
  };
  searchResponses = [
    response({
      applied_intent: appliedTravelIntent,
      refinements: [
        {
          topic_id: "local_pace",
          target_factor_id: "local_pace",
          question_id: "pace",
          question: "What pace should your accommodation base have?",
          reason: "This can change the leading stay base.",
          options: [
            {
              label: "Quiet and relaxed",
              description: "Prefer a calm base.",
              intent_changed: true,
              group_priority_patches: [],
              factor_preference_patches: [pacePreference],
              objective_patches: [],
            },
          ],
        },
      ],
    }),
    response({
      baseline_fingerprint: "baseline-2",
      applied_intent: {
        ...appliedTravelIntent,
        factor_preferences: [pacePreference],
      },
    }),
    response({
      baseline_fingerprint: "baseline-3",
      applied_intent: appliedTravelIntent,
    }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.type(screen.getByLabelText("Describe your ski trip"), appliedBrief);
  await openFilters(user);
  await user.type(screen.getByLabelText("Origin"), "Warsaw");
  await user.type(screen.getByLabelText("Hard drive limit"), "15");
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("radio", { name: /quiet and relaxed/i }),
  );

  const tripBrief = screen.getByLabelText("Trip brief");
  await user.clear(tripBrief);
  await user.type(tripBrief, "Unsent Italy trip from Berlin");
  await user.click(screen.getByRole("button", { name: "Adjust" }));
  await user.clear(screen.getByLabelText("Country"));
  await user.type(screen.getByLabelText("Country"), "Italy");
  await user.clear(screen.getByLabelText("Origin"));
  await user.type(screen.getByLabelText("Origin"), "Berlin");
  await user.clear(screen.getByLabelText("Hard drive limit"));
  await user.type(screen.getByLabelText("Hard drive limit"), "5");
  await user.click(screen.getByRole("button", { name: "Glacier terrain" }));
  await user.selectOptions(
    screen.getByLabelText("Value objective"),
    "pass_price_per_day",
  );
  await user.click(screen.getByRole("button", { name: /close filters/i }));

  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(2);
  });

  const rerankBody = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[1].init?.body),
  );
  expect(rerankBody.intent.constraints.location).toEqual({ country: "France" });
  expect(rerankBody.intent.constraints.travel_limit).toEqual({
    maximum_duration_hours: 15,
    mode: "car",
  });
  expect(rerankBody.intent.travel_context).toEqual({
    origin_text: "Warsaw",
    mode: "car",
  });
  expect(rerankBody.intent.factor_preferences).toEqual([pacePreference]);
  expect(rerankBody.intent.objectives).toEqual(intent.objectives);
  const latestRefinementRequest = JSON.parse(
    String(lastRequest("/api/search/refinements")?.init?.body),
  );
  expect(latestRefinementRequest.brief).toBe(appliedBrief);

  expect(screen.getByLabelText("Trip brief")).toHaveValue(
    "Unsent Italy trip from Berlin",
  );
  await user.click(screen.getByRole("button", { name: "Adjust" }));
  expect(screen.getByLabelText("Country")).toHaveValue("Italy");
  expect(screen.getByLabelText("Origin")).toHaveValue("Berlin");
  expect(screen.getByLabelText("Hard drive limit")).toHaveValue(5);
  expect(screen.getByLabelText("Value objective")).toHaveValue(
    "pass_price_per_day",
  );
  expect(screen.getByRole("button", { name: "Glacier terrain" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  expect(screen.getByText(/prefer local pace: quiet/i)).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Undo" }));
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(3);
  });
  const undoBody = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[2].init?.body),
  );
  expect(undoBody.intent).toEqual(appliedTravelIntent);
  const undoRefinementBody = JSON.parse(
    String(lastRequest("/api/search/refinements")?.init?.body),
  );
  expect(undoRefinementBody.already_answered_question_ids).toEqual([]);
  expect(undoRefinementBody.resolved_topic_ids).toEqual([]);
  expect(screen.getByLabelText("Trip brief")).toHaveValue(
    "Unsent Italy trip from Berlin",
  );
  await user.click(screen.getByRole("button", { name: "Adjust" }));
  expect(screen.getByLabelText("Country")).toHaveValue("Italy");
  expect(screen.getByLabelText("Origin")).toHaveValue("Berlin");
  expect(screen.getByLabelText("Hard drive limit")).toHaveValue(5);
  expect(screen.getByLabelText("Value objective")).toHaveValue(
    "pass_price_per_day",
  );
  expect(screen.getByRole("button", { name: "Glacier terrain" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(screen.queryByText(/prefer local pace: quiet/i)).not.toBeInTheDocument();
});

test("keeps pass-value objectives exclusive through refinement apply and undo", async () => {
  const terrainObjective = {
    factor_id: "pass_terrain_value",
    importance: "normal" as const,
  };
  const priceObjective = {
    factor_id: "pass_price_per_day",
    importance: "high" as const,
  };
  const unrelatedObjective = {
    factor_id: "terrain_scale",
    importance: "high" as const,
  };
  const appliedIntent = {
    ...intent,
    objectives: [terrainObjective, unrelatedObjective],
  };
  searchResponses = [
    response({
      applied_intent: appliedIntent,
      refinements: [
        {
          topic_id: "pass_value",
          target_factor_id: "pass_price_per_day",
          question_id: "pass-value",
          question: "How should pass value influence your search?",
          reason: "This can reorder the leading recommendations.",
          options: [
            {
              label: "Prefer the lowest daily pass price",
              description: "Prioritize price per ski day.",
              intent_changed: true,
              group_priority_patches: [],
              factor_preference_patches: [],
              objective_patches: [priceObjective],
            },
          ],
        },
      ],
    }),
    response({
      baseline_fingerprint: "baseline-2",
      applied_intent: {
        ...appliedIntent,
        objectives: [unrelatedObjective, priceObjective],
      },
    }),
    response({
      baseline_fingerprint: "baseline-3",
      applied_intent: appliedIntent,
    }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("radio", {
      name: /prefer the lowest daily pass price/i,
    }),
  );
  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(2);
  });

  const applyBody = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[1].init?.body),
  );
  expect(applyBody.intent.objectives).toEqual([unrelatedObjective, priceObjective]);
  await user.click(screen.getByRole("button", { name: "Adjust" }));
  expect(screen.getByLabelText("Value objective")).toHaveValue(
    "pass_price_per_day",
  );
  await user.click(screen.getByRole("button", { name: /close filters/i }));

  await user.click(screen.getByRole("button", { name: "Undo" }));
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(3);
  });
  const undoBody = JSON.parse(
    String(requests.filter((item) => item.url === "/api/search")[2].init?.body),
  );
  expect(undoBody.intent.objectives).toEqual([terrainObjective, unrelatedObjective]);
  await user.click(screen.getByRole("button", { name: "Adjust" }));
  expect(screen.getByLabelText("Value objective")).toHaveValue(
    "pass_terrain_value",
  );
});

test("an ordinary successful search clears refinement undo and rank feedback", async () => {
  const pacePreference = {
    factor_id: "local_pace",
    mode: "prefer" as const,
    values: ["quiet"],
    importance: "normal" as const,
  };
  searchResponses = [
    response({
      refinements: [
        {
          topic_id: "local_pace",
          target_factor_id: "local_pace",
          question_id: "pace",
          question: "Would you prefer a quieter base?",
          reason: "This can change the leading stay base.",
          options: [
            {
              label: "Quiet and relaxed",
              description: "Prefer a calm base.",
              intent_changed: true,
              group_priority_patches: [],
              factor_preference_patches: [pacePreference],
              objective_patches: [],
            },
          ],
        },
      ],
    }),
    response({
      baseline_fingerprint: "baseline-2",
      applied_intent: { ...intent, factor_preferences: [pacePreference] },
    }),
    response({
      baseline_fingerprint: "baseline-3",
      applied_intent: { ...intent, factor_preferences: [pacePreference] },
    }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("radio", { name: /quiet and relaxed/i }),
  );
  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));

  expect(await screen.findByRole("button", { name: "Undo" })).toBeVisible();
  expect(screen.getAllByText("Ranking unchanged.")[0]).toBeVisible();

  await user.click(screen.getByRole("button", { name: /update results/i }));
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(3);
  });
  expect(screen.queryByRole("button", { name: "Undo" })).not.toBeInTheDocument();
  expect(screen.queryByText("Ranking unchanged.")).not.toBeInTheDocument();
});

test("preserves previous results and the refinement on a failed rerank", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/current-trip") {
        return new Response(JSON.stringify({ trip: null }), { status: 200 });
      }
      if (url === "/api/search") {
        return new Response(JSON.stringify(response()), { status: 200 });
      }
      if (url === "/api/search/refinements") {
        return new Response(
          JSON.stringify(
            refinementResponse({
              refinement_status: "questions_available",
              refinements: [
                refinement("rerank-question", "Change the ranking?"),
              ],
            }),
          ),
          { status: 200 },
        );
      }
      return new Response(null, { status: 404 });
    }),
  );
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await waitFor(() => {
    expect(
      requests.filter((item) => item.url === "/api/search/refinements"),
    ).toHaveLength(1);
  });
  await user.click(await screen.findByRole("radio", { name: /prefer this/i }));

  const refinementRequestsBefore = requests.filter(
    (item) => item.url === "/api/search/refinements",
  ).length;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/search") {
        return new Response(JSON.stringify({ detail: "internal stack trace" }), {
          status: 500,
        });
      }
      return new Response(null, { status: 404 });
    }),
  );

  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));

  expect(await screen.findByText("Tignes - Val d'Isere")).toBeVisible();
  expect(screen.getByText("Change the ranking?")).toBeVisible();
  expect(
    await screen.findByText(/snowcast is temporarily unavailable/i),
  ).toBeVisible();
  expect(
    requests.filter((item) => item.url === "/api/search/refinements"),
  ).toHaveLength(refinementRequestsBefore);

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/search") {
        return new Response(JSON.stringify(response()), { status: 200 });
      }
      if (url === "/api/search/refinements") {
        return new Response(
          JSON.stringify(refinementResponse({ refinement_status: "not_needed" })),
          { status: 200 },
        );
      }
      return new Response(null, { status: 404 });
    }),
  );

  await user.click(screen.getByRole("button", { name: /update results/i }));
  await waitFor(() => {
    expect(
      requests.filter((item) => item.url === "/api/search/refinements"),
    ).toHaveLength(refinementRequestsBefore + 1);
  });
  const latestRefinementRequest = requests
    .filter((item) => item.url === "/api/search/refinements")
    .at(-1);
  expect(
    JSON.parse(String(latestRefinementRequest?.init?.body)).resolved_topic_ids,
  ).toEqual([]);
});

test("shows save failures separately while keeping ranked results", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await screen.findByText("Tignes - Val d'Isere");

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/current-trip" && init?.method === "PUT") {
        return new Response(JSON.stringify({ detail: "internal stack trace" }), {
          status: 500,
        });
      }
      return new Response(null, { status: 404 });
    }),
  );
  const card = screen.getByText("Tignes - Val d'Isere").closest("article");
  await user.click(
    within(card as HTMLElement).getByRole("button", {
      name: /save as current trip/i,
    }),
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Snowcast is temporarily unavailable. Try again shortly.",
  );
  expect(screen.getByText("Tignes - Val d'Isere")).toBeVisible();
  expect(screen.queryByText(/unable to load resort results/i)).not.toBeInTheDocument();
});

test("preserves refinement objectives and answered state when pass priority changes", async () => {
  const refinedIntent: SearchIntent = {
    ...intent,
    objectives: [
      ...intent.objectives,
      { factor_id: "trip_window_snow_fit", importance: "high" },
    ],
  };
  const passPriceIntent: SearchIntent = {
    ...refinedIntent,
    objectives: [
      { factor_id: "trip_window_snow_fit", importance: "high" },
      { factor_id: "pass_price_per_day", importance: "normal" },
    ],
  };
  const snowOnlyIntent: SearchIntent = {
    ...refinedIntent,
    objectives: [{ factor_id: "trip_window_snow_fit", importance: "high" }],
  };
  searchResponses = [
    response({
      refinements: [
        {
          topic_id: "snow_priority",
          target_factor_id: "trip_window_snow_fit",
          question_id: "snow-priority",
          question: "How important is trip-window snow confidence?",
          reason: "The answer can change the result order.",
          options: [
            {
              label: "Very important",
              description: "Give snow evidence high importance.",
              intent_changed: true,
              group_priority_patches: [],
              factor_preference_patches: [],
              objective_patches: [
                { factor_id: "trip_window_snow_fit", importance: "high" },
              ],
            },
          ],
        },
      ],
    }),
    response({ applied_intent: refinedIntent }),
    response({ applied_intent: passPriceIntent }),
    response({ applied_intent: snowOnlyIntent }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(await screen.findByRole("radio", { name: /very important/i }));
  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));

  await user.click(screen.getByRole("button", { name: "Adjust" }));
  await user.selectOptions(
    screen.getByLabelText("Value objective"),
    "pass_price_per_day",
  );
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /update results/i }));

  await user.click(screen.getByRole("button", { name: "Adjust" }));
  await user.selectOptions(screen.getByLabelText("Value objective"), "");
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /update results/i }));

  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(4);
  });
  const searchBodies = requests
    .filter((item) => item.url === "/api/search")
    .map((item) => JSON.parse(String(item.init?.body)));
  expect(searchBodies[1].intent.objectives).toEqual(refinedIntent.objectives);
  expect(searchBodies[2].intent.objectives).toEqual(passPriceIntent.objectives);
  expect(searchBodies[3].intent.objectives).toEqual(snowOnlyIntent.objectives);
  const latestRefinementRequest = lastRequest("/api/search/refinements");
  expect(
    JSON.parse(String(latestRefinementRequest?.init?.body))
      .already_answered_question_ids,
  ).toEqual(["snow-priority"]);
  expect(
    JSON.parse(String(latestRefinementRequest?.init?.body)).resolved_topic_ids,
  ).toEqual(["snow_priority"]);
});

test("changing a hard constraint starts a new refinement context", async () => {
  const quietPreference = {
    factor_id: "local_pace",
    mode: "prefer" as const,
    values: ["quiet"],
    importance: "normal" as const,
  };
  searchResponses = [
    response({
      refinements: [
        {
          ...refinement("pace", "Would you prefer a quieter base?"),
          topic_id: "local_pace",
          target_factor_id: "local_pace",
          options: [
            {
              label: "Quiet and relaxed",
              description: "Prefer a calm base.",
              intent_changed: true,
              group_priority_patches: [],
              factor_preference_patches: [quietPreference],
              objective_patches: [],
            },
          ],
        },
      ],
    }),
    response({
      baseline_fingerprint: "baseline-2",
      applied_intent: { ...intent, factor_preferences: [quietPreference] },
    }),
    response({
      baseline_fingerprint: "baseline-3",
      applied_intent: {
        ...intent,
        constraints: {
          ...intent.constraints,
          location: { country: "Italy" },
        },
        factor_preferences: [quietPreference],
      },
    }),
  ];
  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(await screen.findByRole("radio", { name: /quiet and relaxed/i }));
  await user.click(screen.getByRole("button", { name: /apply and rerank/i }));
  await screen.findByRole("button", { name: "Undo" });

  await user.click(screen.getByRole("button", { name: "Adjust" }));
  await user.clear(screen.getByLabelText("Country"));
  await user.type(screen.getByLabelText("Country"), "Italy");
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  await user.click(screen.getByRole("button", { name: /update results/i }));

  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(3);
  });
  const latestBody = JSON.parse(
    String(lastRequest("/api/search/refinements")?.init?.body),
  );
  expect(latestBody.already_answered_question_ids).toEqual([]);
  expect(latestBody.resolved_topic_ids).toEqual([]);
});

test("keeps a no-op refinement local and records it as answered", async () => {
  searchResponses = [
    response({
      refinements: [
        {
          topic_id: "pass_balance",
          target_factor_id: "pass_terrain_value",
          question_id: "pass-balance",
          question: "Keep the current pass-value balance?",
          reason: "The baseline remains a valid choice.",
          options: [
            {
              label: "Keep current balance",
              description: "Keep the current pass-value objective.",
              intent_changed: false,
              group_priority_patches: [],
              factor_preference_patches: [],
              objective_patches: [
                { factor_id: "pass_terrain_value", importance: "normal" },
              ],
              preview: {
                top_rank_changes: [],
                eligible_candidate_count_delta: 0,
              },
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
  await user.click(
    await screen.findByRole("radio", { name: /keep current balance/i }),
  );
  await user.click(screen.getByRole("button", { name: /keep current ranking/i }));

  expect(screen.getAllByText("Current ranking kept.")[0]).toBeVisible();
  expect(screen.queryByText(/keep the current pass-value balance/i)).toBeNull();
  expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(1);
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search/refinements")).toHaveLength(2);
  });
  const followUpBody = JSON.parse(
    String(lastRequest("/api/search/refinements")?.init?.body),
  );
  expect(followUpBody.already_answered_question_ids).toEqual(["pass-balance"]);
  expect(followUpBody.resolved_topic_ids).toEqual(["pass_balance"]);
  await waitFor(() => {
    expect(
      screen.getByRole("heading", { name: "Recommended ski trips" }),
    ).toHaveFocus();
  });

  await user.click(screen.getByRole("button", { name: /update results/i }));
  await waitFor(() => {
    expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(2);
  });
  const latestRefinementRequest = lastRequest("/api/search/refinements");
  expect(
    JSON.parse(String(latestRefinementRequest?.init?.body))
      .already_answered_question_ids,
  ).toEqual(["pass-balance"]);
});

test("guards drawer entry and chip mutations during a delayed rerank", async () => {
  searchResponses = [
    response({
      refinements: [
        {
          topic_id: "snow_priority",
          target_factor_id: "trip_window_snow_fit",
          question_id: "snow-priority",
          question: "How important is trip-window snow confidence?",
          reason: "The answer changes the result order.",
          options: [
            {
              label: "Very important",
              description: "Give trip viability very high importance.",
              intent_changed: true,
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
  expect(screen.getByRole("button", { name: "Adjust" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Remove France" })).toBeDisabled();

  resolveRerank?.(new Response(JSON.stringify(response()), { status: 200 }));
  await waitFor(() => {
    expect(screen.queryByText(/reranking these recommendations/i)).not.toBeInTheDocument();
  });
  await user.click(screen.getByRole("button", { name: "Adjust" }));
  expect(screen.getByLabelText("Country")).toHaveValue("France");
  await user.click(screen.getByRole("button", { name: /close filters/i }));
  expect(screen.getByRole("button", { name: "Remove France" })).toBeInTheDocument();
});

test("lets users remove selected objectives and refinement group priorities", async () => {
  searchResponses = [
    response({
      refinements: [
        {
          topic_id: "snow_priority",
          target_factor_id: "trip_window_snow_fit",
          question_id: "snow-priority",
          question: "How important is trip-window snow confidence?",
          reason: "The answer changes the result order.",
          options: [
            {
              label: "Very important",
              description: "Give trip viability very high importance.",
              intent_changed: true,
              group_priority_patches: [
                { group_id: "trip_viability", importance: "very_high" },
              ],
              factor_preference_patches: [],
              objective_patches: [],
            },
            {
              label: "Normal",
              description: "Keep the normal trip viability importance.",
              intent_changed: false,
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
    response({
      applied_intent: {
        ...intent,
        group_priorities: [
          { group_id: "trip_viability", importance: "very_high" },
        ],
      },
    }),
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

test("saving displayed results ignores unapplied draft travel dates", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  await user.click(screen.getByRole("button", { name: "Adjust" }));
  await user.selectOptions(screen.getByLabelText("Travel window"), "dates");
  await user.type(screen.getByLabelText("Trip start date"), "2027-04-10");
  await user.type(screen.getByLabelText("Trip end date"), "2027-04-17");
  await user.click(screen.getByRole("button", { name: /close filters/i }));

  const card = (await screen.findByText("Tignes - Val d'Isere")).closest("article");
  expect(card).not.toBeNull();
  await user.click(
    within(card as HTMLElement).getByRole("button", {
      name: /save as current trip/i,
    }),
  );

  await waitFor(() => {
    expect(
      requests.some(
        (item) => item.url === "/api/current-trip" && item.init?.method === "PUT",
      ),
    ).toBe(true);
  });
  const saveRequest = requests.find(
    (item) => item.url === "/api/current-trip" && item.init?.method === "PUT",
  );
  expect(JSON.parse(String(saveRequest?.init?.body))).toMatchObject({
    travel_month: 3,
    trip_start_date: null,
    trip_end_date: null,
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

test("skipping a topic requests the next question from the same baseline", async () => {
  searchResponses = [response()];
  refinementResponses = [
    refinementResponse({
      refinement_status: "questions_available",
      refinements: [refinement("first", "First refinement?")],
    }),
    refinementResponse({
      refinement_status: "questions_available",
      refinements: [refinement("second", "Second refinement?")],
    }),
  ];
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  expect(await screen.findByText("First refinement?")).toBeInTheDocument();
  expect(screen.queryByText("Second refinement?")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /skip this question/i }));
  expect(screen.queryByText("First refinement?")).not.toBeInTheDocument();
  expect(await screen.findByText("Second refinement?")).toBeInTheDocument();
  expect(requests.filter((item) => item.url === "/api/search")).toHaveLength(1);
  expect(requests.filter((item) => item.url === "/api/search/refinements")).toHaveLength(2);
  const latestRefinementRequest = lastRequest("/api/search/refinements");
  const latestBody = JSON.parse(String(latestRefinementRequest?.init?.body));
  expect(latestBody.baseline_fingerprint).toBe("baseline-1");
  expect(latestBody.already_answered_question_ids).toEqual(["first"]);
  expect(latestBody.resolved_topic_ids).toEqual(["first-topic"]);
});

test("skipping the final refinement returns focus to the results heading", async () => {
  searchResponses = [
    response({
      refinements: [
        {
          topic_id: "only-topic",
          target_factor_id: "only-factor",
          question_id: "only-question",
          question: "What should matter more?",
          reason: "This choice could change the order.",
          options: [
            {
              label: "Lift access",
              description: "Prefer closer lifts.",
              intent_changed: true,
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
  await screen.findByText("What should matter more?");

  await user.click(screen.getByRole("button", { name: /skip this question/i }));

  expect(screen.getByRole("status")).toHaveTextContent(
    /no follow-up would materially change these results/i,
  );
  await waitFor(() => {
    expect(
      screen.getByRole("heading", { name: "Recommended ski trips" }),
    ).toHaveFocus();
  });
});
