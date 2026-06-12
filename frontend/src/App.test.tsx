import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";
import type { SearchExplanation, TripOption } from "./types";

const alpineExplanation: SearchExplanation = {
  highlights: [{ label: "Pine Chalet Zone supports intermediate skiers." }],
  risks: [],
  confidence_contributors: [
    { label: "Snow outlook is strong for the trip window.", direction: "positive" },
  ],
};

const montBlancExplanation: SearchExplanation = {
  highlights: [{ label: "River Lane supports intermediate skiers." }],
  risks: [{ label: "Weather signal suggests some disruption risk right now." }],
  confidence_contributors: [
    {
      label: "Weather disruption risk reduces recommendation certainty.",
      direction: "negative",
    },
  ],
};

function makeTripOption(option: TripOption): TripOption {
  return option;
}

const firstResponse = {
  results: [
    {
      resort_id: "alpine-horizon",
      resort_name: "Alpine Horizon",
      region: "Northern Alps",
      selected_ski_area_id: "alpine-horizon-main-bowl",
      selected_ski_area_name: "Alpine Horizon Main Bowl",
      selected_stay_base_name: "Pine Chalet Zone",
      selected_stay_base_lift_distance: "near",
      stay_base_price_range: "EUR 150-190",
      selected_area_name: "Pine Chalet Zone",
      selected_area_lift_distance: "near",
      area_price_range: "EUR 150-190",
      rental_name: "Budget Ski Stop",
      rental_price_range: "EUR 30-45",
      rating_estimate: 2,
      link: "https://example.com/search?q=Alpine%20Horizon%20France",
      score: 1.7,
      budget_penalty: 0,
      conditions_summary: "Fresh snowfall and strong visibility.",
      snow_confidence_score: 0.89,
      snow_confidence_label: "good",
      availability_status: "open",
      conditions_score: 0.87,
      conditions_provenance: {
        source_name: "open-meteo",
        source_type: "forecast",
        updated_at: "2026-04-12T09:00:00+00:00",
        freshness_status: "fresh",
        basis_summary:
          "Using a current forecast-based conditions signal from the latest weather refresh.",
      },
      explanation: alpineExplanation,
      recommendation_narrative:
        "Alpine Horizon is a strong fit for an intermediate trip thanks to near-lift access and strong conditions.",
      recommendation_confidence: 0.86,
      planning_summary: null,
      planning_provenance: null,
      planning_evidence_count: null,
      planning_weather_metrics: null,
      best_travel_months: [],
      top_option: makeTripOption({
        option_id: "alpine-horizon-main-bowl|Pine Chalet Zone|Budget Ski Stop",
        ski_area_id: "alpine-horizon-main-bowl",
        ski_area_name: "Alpine Horizon Main Bowl",
        stay_base_name: "Pine Chalet Zone",
        stay_base_lift_distance: "near",
        stay_base_price_range: "EUR 150-190",
        rental_name: "Budget Ski Stop",
        rental_price_range: "EUR 30-45",
        rating_estimate: 2,
        score: 1.7,
        recommendation_confidence: 0.86,
        budget_penalty: 0,
        travel_effort: null,
        explanation: alpineExplanation,
        tradeoff_summary:
          "Pine Chalet Zone: near lift access, EUR 150-190 stay estimate.",
      }),
      alternative_options: [
        makeTripOption({
          option_id: "alpine-horizon-main-bowl|Lake Quarter|Alpine Demo Rental",
          ski_area_id: "alpine-horizon-main-bowl",
          ski_area_name: "Alpine Horizon Main Bowl",
          stay_base_name: "Lake Quarter",
          stay_base_lift_distance: "medium",
          stay_base_price_range: "EUR 120-160",
          rental_name: "Alpine Demo Rental",
          rental_price_range: "EUR 42-60",
          rating_estimate: 2,
          score: 1.55,
          recommendation_confidence: 0.8,
          budget_penalty: 0,
          travel_effort: null,
          explanation: alpineExplanation,
          tradeoff_summary:
            "Lake Quarter: medium lift access, EUR 120-160 stay estimate.",
        }),
      ],
    },
    {
      resort_id: "mont-blanc-escape",
      resort_name: "Mont Blanc Escape",
      region: "Northern Alps",
      selected_ski_area_id: "mont-blanc-escape-ridge",
      selected_ski_area_name: "Mont Blanc Escape Ridge",
      selected_stay_base_name: "River Lane",
      selected_stay_base_lift_distance: "medium",
      stay_base_price_range: "EUR 160-210",
      selected_area_name: "River Lane",
      selected_area_lift_distance: "medium",
      area_price_range: "EUR 160-210",
      rental_name: "Escape Ski Lab",
      rental_price_range: "EUR 50-70",
      rating_estimate: 2,
      link: "https://example.com/search?q=Mont%20Blanc%20Escape%20France",
      score: 1.4,
      budget_penalty: 0,
      conditions_summary: "Solid snow conditions with light cloud cover.",
      snow_confidence_score: 0.75,
      snow_confidence_label: "good",
      availability_status: "limited",
      conditions_score: 0.68,
      conditions_provenance: {
        source_name: "open-meteo",
        source_type: "forecast",
        updated_at: "2026-04-10T09:00:00+00:00",
        freshness_status: "stale",
        basis_summary:
          "Using a current forecast-based conditions signal from the latest weather refresh.",
      },
      explanation: montBlancExplanation,
      recommendation_narrative: null,
      recommendation_confidence: 0.74,
      planning_summary: null,
      planning_provenance: null,
      planning_evidence_count: null,
      planning_weather_metrics: null,
      best_travel_months: [],
      top_option: makeTripOption({
        option_id: "mont-blanc-escape-ridge|River Lane|Escape Ski Lab",
        ski_area_id: "mont-blanc-escape-ridge",
        ski_area_name: "Mont Blanc Escape Ridge",
        stay_base_name: "River Lane",
        stay_base_lift_distance: "medium",
        stay_base_price_range: "EUR 160-210",
        rental_name: "Escape Ski Lab",
        rental_price_range: "EUR 50-70",
        rating_estimate: 2,
        score: 1.4,
        recommendation_confidence: 0.74,
        budget_penalty: 0,
        travel_effort: null,
        explanation: montBlancExplanation,
        tradeoff_summary:
          "River Lane: medium lift access, EUR 160-210 stay estimate.",
      }),
      alternative_options: [],
    },
  ],
};

const twoAlternativeResponse = {
  results: [
    {
      ...firstResponse.results[0],
      alternative_options: [
        ...firstResponse.results[0].alternative_options,
        makeTripOption({
          option_id: "alpine-horizon-main-bowl|Summit Village|Summit Rental Co",
          ski_area_id: "alpine-horizon-main-bowl",
          ski_area_name: "Alpine Horizon Main Bowl",
          stay_base_name: "Summit Village",
          stay_base_lift_distance: "far",
          stay_base_price_range: "EUR 105-145",
          rental_name: "Summit Rental Co",
          rental_price_range: "EUR 38-55",
          rating_estimate: 2,
          score: 1.47,
          recommendation_confidence: 0.76,
          budget_penalty: 0,
          travel_effort: null,
          explanation: alpineExplanation,
          tradeoff_summary:
            "Summit Village: far lift access, EUR 105-145 stay estimate.",
        }),
      ],
    },
  ],
};

const secondResponse = {
  results: [
    {
      ...firstResponse.results[1],
      conditions_summary: "Visibility is mixed but the selected area remains viable.",
      score: 1.39,
    },
    {
      ...firstResponse.results[0],
      conditions_summary: "Fresh snowfall continues through tomorrow.",
      score: 1.74,
    },
  ],
};

const emptyResponse = {
  results: [],
};

const planningResponse = {
  results: [
    {
      ...firstResponse.results[0],
      planning_summary:
        "Good fit for February, backed by 2 historical weather records.",
      planning_provenance: {
        source_name: "snapshot_history+seasonality",
        source_type: "estimated",
        updated_at: "2026-02-15T00:00:00+00:00",
        freshness_status: "historical",
        basis_summary:
          "Using historical weather records for this month together with seasonal patterns.",
      },
      planning_evidence_count: 2,
      planning_weather_metrics: {
        average_snow_depth_cm: 128,
        average_daily_snowfall_cm: 6.5,
        average_max_temperature_c: -2.4,
        average_wind_gust_kmh: 24,
        evidence_years: 2,
        latest_observed_on: "2025-02-28",
        elevation_band: "mid",
        elevation_m: 2500,
      },
      best_travel_months: [1, 2, 3],
      conditions_summary:
        "Good fit for February, backed by 2 historical weather records.",
    },
  ],
};

const weakMayResponse = {
  results: [
    {
      ...firstResponse.results[0],
      snow_confidence_score: 0.32,
      snow_confidence_label: "poor",
      availability_status: "limited",
      recommendation_confidence: 0.52,
      conditions_summary: "Poor snow outlook for May.",
      planning_summary: "Poor fit for May, backed by 1 archive weather window.",
      planning_provenance: {
        source_name: "snapshot_history+seasonality",
        source_type: "estimated",
        updated_at: "2026-05-06T14:00:00+00:00",
        freshness_status: "historical",
        basis_summary:
          "Using stored archive weather history together with seasonal patterns.",
      },
      planning_evidence_count: 1,
      planning_weather_metrics: {
        average_snow_depth_cm: 5,
        average_daily_snowfall_cm: 3.8,
        average_max_temperature_c: 0.2,
        average_wind_gust_kmh: 34,
        evidence_years: 1,
        latest_observed_on: "2026-05-06",
        elevation_band: "mid",
        elevation_m: 2100,
      },
      best_travel_months: [1, 2, 3],
      top_option: {
        ...firstResponse.results[0].top_option,
        recommendation_confidence: 0.52,
      },
    },
  ],
};

const travelEffortResponse = {
  results: [
    {
      ...firstResponse.results[0],
      travel_effort: {
        origin_label: "Munich",
        destination_label: "Pine Chalet Zone",
        mode: "car",
        distance_km: 185,
        duration_minutes: 150,
        effort_label: "easy",
        score: 0.86,
        summary: "Approx. 2h 30m drive from Munich.",
        provenance: "estimated_fallback",
        provider: "approximate_haversine_v2",
        cache_hit: false,
        caveat: "Drive times are approximate and can vary with winter traffic.",
        exceeds_max_drive: false,
      },
    },
  ],
};

const parseResponse = {
  filters: {
    location: "Austria",
    skill_level: "intermediate",
    lift_distance: "near",
    travel_month: 3,
  },
  confidence: 0.9,
  unknown_parts: ["fairly affordable"],
};

const originParseResponse = {
  ...parseResponse,
  trip_context: {
    budget_mode: null,
    budget_min: null,
    budget_max: null,
    party_size: null,
    trip_duration_nights: null,
    origin_text: "Munich",
  },
};

const dateParseResponse = {
  filters: {
    location: "France",
    skill_level: "intermediate",
    travel_month: 4,
    trip_start_date: "2026-04-09",
    trip_end_date: "2026-04-16",
  },
  confidence: 0.92,
  unknown_parts: [],
};

const clarificationParseResponse = {
  filters: {
    location: "France",
    skill_level: "intermediate",
  },
  confidence: 0.88,
  unknown_parts: [],
  trip_context: {
    budget_mode: null,
    budget_min: 1500,
    budget_max: 1500,
    party_size: null,
    trip_duration_nights: null,
    origin_text: null,
  },
  clarifications: [
    {
      id: "budget-mode",
      question: "Is this budget for nightly lodging or the whole trip?",
      reason: "Budget amount was detected without clear budget mode.",
      priority: 10,
      options: [
        {
          id: "lodging-nightly",
          label: "Nightly lodging",
          description: "Use the amount as the stay-base nightly budget.",
          context_patch: { budget_mode: "lodging_nightly" },
          filter_patch: { min_price: 1500, max_price: 1500 },
        },
        {
          id: "total-trip",
          label: "Total trip",
          description: "Treat the amount as the approximate full trip budget.",
          context_patch: { budget_mode: "total_trip" },
          filter_patch: null,
        },
      ],
    },
  ],
  assumptions: [],
};

const originClarificationParseResponse = {
  filters: {
    location: "France",
    skill_level: "intermediate",
  },
  confidence: 0.88,
  unknown_parts: [],
  trip_context: {
    budget_mode: null,
    budget_min: null,
    budget_max: null,
    party_size: null,
    trip_duration_nights: null,
    origin_text: null,
  },
  clarifications: [
    {
      id: "travel-origin",
      question: "Where are you driving from?",
      reason: "Origin is needed to estimate car travel effort.",
      priority: 20,
      options: [
        {
          id: "add-origin",
          label: "Add origin",
          description: "Open travel filters so you can enter a starting point.",
          context_patch: {},
          filter_patch: null,
        },
      ],
    },
  ],
  assumptions: [],
};

const currentTripResponse = {
  trip: null,
};

const currentTripSummaryResponse = {
  trip: {
    resort_id: "alpine-horizon",
    resort_name: "Alpine Horizon",
    selected_ski_area_id: "alpine-horizon-main-bowl",
    selected_ski_area_name: "Alpine Horizon Main Bowl",
    selected_stay_base_name: "Pine Chalet Zone",
    selected_area_name: "Pine Chalet Zone",
    travel_month: 2,
    booking_status: "booked_elsewhere",
    created_at: "2026-04-12T10:00:00+00:00",
    updated_at: "2026-04-12T10:00:00+00:00",
    last_checked_at: null,
  },
  current_conditions: {
    resort_name: "Alpine Horizon",
    snow_confidence_score: 0.89,
    snow_confidence_label: "good",
    availability_status: "open",
    weather_summary: "Fresh snowfall and strong visibility.",
    conditions_score: 0.87,
    updated_at: "2026-04-12T09:00:00+00:00",
    source: "open-meteo",
  },
  current_conditions_provenance: firstResponse.results[0].conditions_provenance,
  comparison_basis: {
    kind: "since_trip_saved",
    baseline_at: "2026-04-12T10:00:00+00:00",
    label: "Since trip was saved",
  },
  delta: {
    status: "insufficient_history",
    summary:
      "Conditions were refreshed after the comparison baseline, but there is not enough earlier history to compare yet.",
    changes: [],
  },
  companion_status: {
    trip_window_status: "unscheduled",
    trip_window_label: "No exact trip dates saved yet",
    notification_eligible: false,
    eligibility_reason: "Add exact trip dates to enable companion alerts for this trip.",
    actionable_change_available: false,
  },
};

const currentTripEventsResponse = {
  events: [],
};

function jsonResponse(payload: unknown) {
  return {
    ok: true,
    json: async () => payload,
  };
}

function errorResponse(payload: unknown, status = 500) {
  return {
    ok: false,
    status,
    json: async () => payload,
  };
}

function mockFetchRoutes(options?: {
  searchResponses?: unknown[];
  parseResponse?: unknown;
  parseErrorResponse?: unknown;
  searchErrorResponse?: unknown;
  currentTripResponse?: unknown;
  currentTripSummaryResponse?: unknown;
  currentTripEventsResponse?: unknown;
  saveCurrentTripResponse?: unknown;
  deleteCurrentTripResponse?: unknown;
  markCheckedResponse?: unknown;
}) {
  const {
    searchResponses = [],
    parseResponse: parsePayload,
    parseErrorResponse,
    searchErrorResponse,
    currentTripResponse: currentTripPayload = currentTripResponse,
    currentTripSummaryResponse: currentTripSummaryPayload = currentTripSummaryResponse,
    currentTripEventsResponse: currentTripEventsPayload = currentTripEventsResponse,
    saveCurrentTripResponse,
    deleteCurrentTripResponse = null,
    markCheckedResponse,
  } = options ?? {};

  const queuedSearchResponses = [...searchResponses];

  return vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";

    if (url.includes("/api/current-trip/summary") && method === "GET") {
      return Promise.resolve(jsonResponse(currentTripSummaryPayload));
    }
    if (url.includes("/api/current-trip/events") && method === "GET") {
      return Promise.resolve(jsonResponse(currentTripEventsPayload));
    }
    if (url.includes("/api/current-trip/mark-checked") && method === "POST") {
      return Promise.resolve(
        jsonResponse(
          markCheckedResponse ??
            (currentTripSummaryPayload as { trip: unknown }).trip,
        ),
      );
    }
    if (url.includes("/api/current-trip") && method === "GET") {
      return Promise.resolve(jsonResponse(currentTripPayload));
    }
    if (url.includes("/api/current-trip") && method === "PUT") {
      return Promise.resolve(
        jsonResponse(saveCurrentTripResponse ?? currentTripPayload),
      );
    }
    if (url.includes("/api/current-trip") && method === "DELETE") {
      return Promise.resolve(jsonResponse(deleteCurrentTripResponse));
    }
    if (url.includes("/api/parse-query")) {
      if (parseErrorResponse !== undefined) {
        return Promise.resolve(errorResponse(parseErrorResponse));
      }
      return Promise.resolve(jsonResponse(parsePayload ?? parseResponse));
    }
    if (url.includes("/api/search")) {
      if (searchErrorResponse !== undefined) {
        return Promise.resolve(errorResponse(searchErrorResponse));
      }
      return Promise.resolve(
        jsonResponse(queuedSearchResponses.shift() ?? emptyResponse),
      );
    }

    return Promise.reject(new Error(`Unhandled fetch URL in test: ${url}`));
  });
}

function searchUrls(fetchMock: ReturnType<typeof vi.fn>): string[] {
  return fetchMock.mock.calls
    .map((call) => String(call[0]))
    .filter((url) => url.includes("/api/search?"));
}

beforeEach(() => {
  sessionStorage.clear();
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});

test("renders the structured search form", () => {
  vi.stubGlobal("fetch", mockFetchRoutes());

  render(<App />);

  expect(screen.getByText("SNOWCAST")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", {
      name: /book the mountain,\s*not the guesswork/i,
    }),
  ).toBeInTheDocument();
  expect(screen.getByText(/snow-aware trip planning/i)).toBeInTheDocument();
  expect(screen.getByText(/april is risky below 1,800m/i)).toBeInTheDocument();
  expect(
    screen.getByText(/use archive snow evidence before you commit/i),
  ).toBeInTheDocument();
  expect(screen.getByLabelText(/what are you looking for/i)).toBeInTheDocument();
  expect(screen.getByText(/example recommendation/i)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /cervinia/i })).toBeInTheDocument();
  expect(screen.getByText(/stay in breuil-cervinia/i)).toBeInTheDocument();
  expect(screen.getByText(/archive-backed/i)).toBeInTheDocument();
  expect(screen.getByText(/strong late-season snow reliability/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /remove france/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /remove intermediate/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /remove march/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /adjust filters/i })).toBeInTheDocument();
  expect(screen.queryByText(/^1\. describe$/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/^2\. review$/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/^3\. compare$/i)).not.toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: /recommended ski trips/i }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText(/search surface/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/uses the live backend/i)).not.toBeInTheDocument();
});

test("direct resort detail route without cached search state shows a fallback", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes());
  window.history.replaceState(null, "", "/resorts/alpine-horizon");

  const user = userEvent.setup();
  render(<App />);

  expect(screen.getByTestId("detail-route-fallback")).toHaveTextContent(
    "Run a search first",
  );
  await user.click(screen.getByRole("button", { name: /go to search/i }));

  expect(window.location.pathname).toBe("/");
  expect(screen.getByRole("button", { name: /find resorts/i })).toBeInTheDocument();
});

test("renders ranked results and curated details after search", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", {
      name: /alpine horizon/i,
      level: 3,
    }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /alpine horizon/i }));

  expect(window.location.pathname).toBe("/resorts/alpine-horizon");
  const details = screen.getByTestId("result-details");
  expect(
    screen.getByRole("heading", { name: /why this trip fits/i }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /recommended ski trip/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /highlights/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /risks/i })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /current conditions/i }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: /watchouts/i })).not.toBeInTheDocument();
  expect(details).toHaveTextContent("Forecast");
  expect(details).toHaveTextContent("open-meteo");
  expect(details).toHaveTextContent("Alpine Horizon is a strong fit");
  expect(details).toHaveTextContent("Recommendation dossier");
  expect(details).toHaveTextContent("Alpine Horizon Main Bowl");
  expect(details).toHaveTextContent("Pine Chalet Zone");
  expect(details).toHaveTextContent("Trip fit combines snow outlook");
  expect(details).toHaveTextContent("Stay-base estimate, not live hotel inventory");
  expect(
    screen.getByRole("link", { name: /book accommodation/i }),
  ).toHaveAttribute(
    "href",
    "/api/outbound/accommodation/alpine-horizon?selected_ski_area_name=Alpine+Horizon+Main+Bowl&selected_stay_base_name=Pine+Chalet+Zone&source_surface=selected_result_details",
  );
});

test("post-search workspace uses compact command and refine drawer", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", { name: /recommended ski trips/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/why alpine horizon leads/i)).toBeInTheDocument();
  expect(screen.queryByLabelText(/what are you looking for/i)).not.toBeInTheDocument();
  expect(screen.getByLabelText(/trip brief/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /refine search/i })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /refine search/i }));

  const drawer = screen.getByRole("dialog", { name: /refine search filters/i });
  expect(within(drawer).getByLabelText(/location/i)).toHaveValue("France");
  expect(within(drawer).getByLabelText(/skill level/i)).toHaveValue("intermediate");
});

test("weather disruption states use warning semantics instead of success", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  const disruptionPill = await screen.findByText("Weather disruption possible");
  expect(disruptionPill).toHaveClass("bg-amber/10");
  expect(disruptionPill).not.toHaveClass("bg-pine");
});

test("weak travel windows show planning guidance instead of only ranking results", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [weakMayResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /adjust filters/i }));
  await user.click(screen.getByRole("button", { name: /^month$/i }));
  await user.selectOptions(screen.getByLabelText(/travel month/i), "5");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText(/may looks weak/i)).toBeInTheDocument();
  expect(screen.getByText(/try january, february, march/i)).toBeInTheDocument();
  expect(screen.getByText(/weak may match/i)).toBeInTheDocument();
});

test("result cards show alternative stay-base counts when alternatives exist", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("1 alternative base")).toBeInTheDocument();
});

test("result cards pluralize alternative stay-base counts", async () => {
  vi.stubGlobal(
    "fetch",
    mockFetchRoutes({ searchResponses: [twoAlternativeResponse] }),
  );

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText("2 alternative bases")).toBeInTheDocument();
});

test("results without alternatives hide the badge and stay-base selector", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  const montBlancCard = await screen.findByRole("button", {
    name: /mont blanc escape/i,
  });
  expect(within(montBlancCard).queryByText(/alternative base/i)).not.toBeInTheDocument();

  await user.click(montBlancCard);

  const details = screen.getByTestId("result-details");
  expect(
    screen.queryByRole("heading", { name: /stay-base alternatives/i }),
  ).not.toBeInTheDocument();
  expect(details).toHaveTextContent("Mont Blanc Escape Ridge");
  expect(details).toHaveTextContent("River Lane");
  expect(details).toHaveTextContent("EUR 160-210");
});

test("details open with the top stay base and stay-base alternatives", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("button", { name: /alpine horizon/i }),
  );

  const details = screen.getByTestId("result-details");
  expect(
    screen.getByRole("heading", { name: /stay-base alternatives/i }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /recommended stay base/i }),
  ).toBeInTheDocument();
  expect(details).toHaveTextContent("Alpine Horizon Main Bowl");
  expect(details).toHaveTextContent("Pine Chalet Zone");
  expect(details).toHaveTextContent("Continue from the recommended stay base in Pine Chalet Zone");
  expect(details).toHaveTextContent("EUR 150-190");
  expect(details).toHaveTextContent("Near");
  expect(
    screen.getByRole("button", { name: /pine chalet zone/i }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("clicking an alternative stay base updates option-specific details", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("button", { name: /alpine horizon/i }),
  );

  await user.click(screen.getByRole("button", { name: /lake quarter/i }));

  const details = screen.getByTestId("result-details");
  expect(
    screen.getByRole("button", { name: /lake quarter/i }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(details).toHaveTextContent("Alpine Horizon Main Bowl");
  expect(details).toHaveTextContent("Lake Quarter");
  expect(details).toHaveTextContent("Continue from the recommended stay base in Lake Quarter");
  expect(details).toHaveTextContent("EUR 120-160");
  expect(details).toHaveTextContent("Medium");
  expect(details).toHaveTextContent("Alpine Demo Rental");
  expect(details).toHaveTextContent("EUR 42-60");
  expect(details).toHaveTextContent("Alpine Horizon is a strong fit");
  expect(details).toHaveTextContent("open-meteo");
  expect(
    screen.getByRole("link", { name: /book accommodation/i }),
  ).toHaveAttribute(
    "href",
    "/api/outbound/accommodation/alpine-horizon?selected_ski_area_name=Alpine+Horizon+Main+Bowl&selected_stay_base_name=Lake+Quarter&source_surface=selected_result_details",
  );
});

test("switching results after selecting an alternative resets details to the new top option", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("button", { name: /alpine horizon/i }),
  );
  await user.click(screen.getByRole("button", { name: /lake quarter/i }));

  let details = screen.getByTestId("result-details");
  expect(details).toHaveTextContent("Alpine Horizon Main Bowl");
  expect(details).toHaveTextContent("Lake Quarter");
  expect(details).toHaveTextContent("EUR 120-160");

  await user.click(screen.getByRole("button", { name: /back to search results/i }));
  await user.click(
    await screen.findByRole("button", { name: /mont blanc escape/i }),
  );

  details = screen.getByTestId("result-details");
  expect(details).toHaveTextContent("Mont Blanc Escape Ridge");
  expect(details).toHaveTextContent("River Lane");
  expect(details).toHaveTextContent("EUR 160-210");
  expect(details).toHaveTextContent("Escape Ski Lab");
  expect(details).not.toHaveTextContent("Lake Quarter");
  expect(details).not.toHaveTextContent("EUR 120-160");
});

test("saving after selecting an alternative uses that stay base and ski area", async () => {
  const savedTrip = {
    resort_id: "alpine-horizon",
    resort_name: "Alpine Horizon",
    selected_ski_area_id: "alpine-horizon-main-bowl",
    selected_ski_area_name: "Alpine Horizon Main Bowl",
    selected_stay_base_name: "Lake Quarter",
    selected_area_name: "Lake Quarter",
    travel_month: null,
    booking_status: "not_booked_yet",
    created_at: "2026-04-12T10:00:00+00:00",
    updated_at: "2026-04-12T10:00:00+00:00",
    last_checked_at: null,
  };
  const fetchMock = mockFetchRoutes({
    searchResponses: [firstResponse],
    saveCurrentTripResponse: savedTrip,
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("button", { name: /alpine horizon/i }),
  );
  await user.click(screen.getByRole("button", { name: /lake quarter/i }));
  await user.click(screen.getByRole("button", { name: /save as current trip/i }));

  expect(await screen.findByText(/saved/i)).toBeInTheDocument();

  const saveCall = fetchMock.mock.calls.find(([input, init]) => {
    return String(input).includes("/api/current-trip") && init?.method === "PUT";
  });
  expect(saveCall).toBeDefined();
  expect(JSON.parse(String(saveCall?.[1]?.body))).toMatchObject({
    resort_id: "alpine-horizon",
    selected_ski_area_id: "alpine-horizon-main-bowl",
    selected_ski_area_name: "Alpine Horizon Main Bowl",
    selected_stay_base_name: "Lake Quarter",
  });
});

test("falls back to a deterministic narrative when the top-result LLM summary is missing", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [secondResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", {
      name: /mont blanc escape/i,
      level: 3,
    }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /mont blanc escape/i }));

  expect(screen.getByTestId("result-details")).toHaveTextContent(
    "Good snow confidence, but weather disruption possible.",
  );
  expect(screen.getByTestId("result-details")).not.toHaveTextContent(
    "Mont Blanc Escape pairs River Lane with Mont Blanc Escape Ridge",
  );
});

test("auto-interprets a changed trip brief before searching", async () => {
  const fetchMock = mockFetchRoutes({ parseResponse, searchResponses: [emptyResponse] });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "Looking for a fairly affordable ski trip in Austria, intermediate level, not too far from the lifts.",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  const parsedConfidence = await screen.findByText(/search confidence/i);
  expect(parsedConfidence).toHaveTextContent("90%");
  expect(screen.getByRole("button", { name: /remove austria/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /remove march/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /remove near lifts/i })).toBeInTheDocument();
  expect(
    screen.getByText(/not sure how to use: fairly affordable/i),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/parse-query",
    expect.objectContaining({ method: "POST" }),
  );
  expect(String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1][0])).toContain(
    "/api/search?",
  );

  await user.click(screen.getByRole("button", { name: /refine search/i }));
  const drawer = screen.getByRole("dialog", { name: /refine search filters/i });
  expect(within(drawer).getByLabelText(/location/i)).toHaveValue("Austria");
  expect(within(drawer).getByLabelText(/skill level/i)).toHaveValue("intermediate");
  expect(within(drawer).getByLabelText(/travel month/i)).toHaveValue("3");
  expect(within(drawer).getByLabelText(/lift distance/i)).toHaveValue("near");
});

test("parse proxy failure explains that the backend API is not reachable", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ parseErrorResponse: null }));

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "Ski trip france in march",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText(
      /backend api is not reachable\. the service may be starting or temporarily unavailable/i,
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(/unable to interpret trip brief/i),
  ).not.toBeInTheDocument();
});

test("parsed exact dates override month before search", async () => {
  const fetchMock = mockFetchRoutes({
    parseResponse: dateParseResponse,
    searchResponses: [firstResponse],
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "France intermediate ski trip 9 Apr to 16 Apr",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", {
      name: /alpine horizon/i,
      level: 3,
    }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /remove apr 9, 2026 to apr 16, 2026/i }),
  ).toBeInTheDocument();
  const [searchUrl] = searchUrls(fetchMock);
  expect(searchUrl).toContain("trip_start_date=2026-04-09");
  expect(searchUrl).toContain("trip_end_date=2026-04-16");
  expect(searchUrl).not.toContain("travel_month");
});

test("successful brief parse shows search failures in the results panel", async () => {
  const fetchMock = mockFetchRoutes({
    parseResponse: originParseResponse,
    searchErrorResponse: { detail: "Unable to load resort results." },
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "Ski in Italy from Berlin, 21-27.02.2027",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText(/unable to load resort results/i),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(/unable to interpret trip brief/i),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText(/no matching ski trips yet/i),
  ).not.toBeInTheDocument();
  expect(screen.getByText(/search confidence/i)).toBeInTheDocument();
});

test("travel effort parsed origin populates the origin filter and chip", async () => {
  const fetchMock = mockFetchRoutes({
    parseResponse: originParseResponse,
    searchResponses: [emptyResponse],
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "Intermediate March ski trip in Austria, driving from Munich.",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("button", { name: /remove origin munich/i }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /refine search/i }));
  expect(
    within(screen.getByRole("dialog", { name: /refine search filters/i })).getByLabelText(
      /travel origin/i,
    ),
  ).toHaveValue("Munich");
  expect(
    screen.getByRole("button", { name: /remove origin munich/i }),
  ).toBeInTheDocument();
});

test("travel effort search sends origin, tolerance, and max drive constraints", async () => {
  const fetchMock = mockFetchRoutes({ searchResponses: [emptyResponse] });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /adjust filters/i }));
  await user.type(screen.getByLabelText(/travel origin/i), " Munich ");
  await user.type(screen.getByLabelText(/max drive hours/i), "3.5");
  await user.selectOptions(screen.getByLabelText(/travel tolerance/i), "medium");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  const [searchUrl] = searchUrls(fetchMock);
  expect(searchUrl).toContain("origin_text=Munich");
  expect(searchUrl).toContain("max_drive_minutes=210");
  expect(searchUrl).toContain("travel_tolerance=medium");
});

test("travel effort invalid max drive hours blocks search", async () => {
  const fetchMock = mockFetchRoutes({ searchResponses: [emptyResponse] });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /adjust filters/i }));
  await user.type(screen.getByLabelText(/max drive hours/i), "-1");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText(/max drive hours must be a positive number/i),
  ).toBeInTheDocument();
  expect(searchUrls(fetchMock)).toHaveLength(0);
});

test("travel effort add-origin clarification opens the origin control", async () => {
  const fetchMock = mockFetchRoutes({
    parseResponse: originClarificationParseResponse,
    searchResponses: [emptyResponse],
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "France intermediate ski trip, driving distance matters.",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText(/where are you driving from/i)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /add origin/i }));

  expect(screen.getByLabelText(/travel origin/i)).toBeInTheDocument();
});

test("travel effort removing max drive and tolerance chips clears those search params", async () => {
  const fetchMock = mockFetchRoutes({
    searchResponses: [emptyResponse, emptyResponse],
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /adjust filters/i }));
  await user.type(screen.getByLabelText(/travel origin/i), "Munich");
  await user.type(screen.getByLabelText(/max drive hours/i), "3.5");
  await user.selectOptions(screen.getByLabelText(/travel tolerance/i), "medium");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(searchUrls(fetchMock)[0]).toContain("max_drive_minutes=210");
  expect(searchUrls(fetchMock)[0]).toContain("travel_tolerance=medium");

  await user.click(screen.getByRole("button", { name: /remove max drive 3.5h/i }));
  await user.click(screen.getByRole("button", { name: /remove medium travel/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  const secondSearchUrl = searchUrls(fetchMock)[1];
  expect(secondSearchUrl).toContain("origin_text=Munich");
  expect(secondSearchUrl).not.toContain("max_drive_minutes");
  expect(secondSearchUrl).not.toContain("travel_tolerance");
});

test("travel effort result shows approximate drive summary and detail evidence", async () => {
  vi.stubGlobal(
    "fetch",
    mockFetchRoutes({ searchResponses: [travelEffortResponse] }),
  );

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    (await screen.findAllByText(/approx\. 2h 30m drive from munich/i)).length,
  ).toBeGreaterThan(0);

  await user.click(screen.getByRole("button", { name: /alpine horizon/i }));

  const details = screen.getByTestId("result-details");
  expect(screen.getByRole("heading", { name: /travel effort/i })).toBeInTheDocument();
  expect(details).toHaveTextContent("Approx. 2h 30m drive from Munich.");
  expect(details).toHaveTextContent("Estimated fallback");
  expect(details).toHaveTextContent("Approximate road estimate");
  expect(details).toHaveTextContent(
    "Drive times are approximate and can vary with winter traffic.",
  );
});

test("changed parsed brief resets stale budget filters when budget is not mentioned", async () => {
  sessionStorage.setItem(
    "sports-trip-planner-search-state",
    JSON.stringify({
      tripBrief: "Cheap Italy ski trip",
      lastParsedTripBrief: "Cheap Italy ski trip",
      parsedQuery: null,
      tripContext: null,
      clarifications: [],
      assumptions: [],
      filters: {
        location: "Italy",
        minPrice: "150",
        maxPrice: "200",
        stars: "2",
        skillLevel: "intermediate",
        liftDistance: "",
        budgetFlex: "",
        travelWindowMode: "any",
        travelMonth: "",
        tripStartDate: "",
        tripEndDate: "",
      },
      results: [],
      selectedResultId: null,
      hasSearched: false,
    }),
  );
  const fetchMock = mockFetchRoutes({
    parseResponse: dateParseResponse,
    searchResponses: [emptyResponse],
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.clear(screen.getByLabelText(/what are you looking for/i));
  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "Ski in France, 9-16.04.2026",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("button", { name: /remove eur 150-320/i }),
  ).toBeInTheDocument();
  const [searchUrl] = searchUrls(fetchMock);
  expect(searchUrl).toContain("max_price=320");
  expect(searchUrl).not.toContain("max_price=200");
});

test("shows clarification cards and applies nightly budget choice", async () => {
  const fetchMock = mockFetchRoutes({
    parseResponse: clarificationParseResponse,
    searchResponses: [emptyResponse],
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "France ski trip with EUR 1500 budget",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText(/is this budget for nightly lodging or the whole trip/i),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /nightly lodging/i }));

  expect(screen.getByLabelText(/min price/i)).toHaveValue("1500");
  expect(screen.getByLabelText(/max price/i)).toHaveValue("1500");
  expect(screen.getByText(/Budget: nightly lodging/i)).toBeInTheDocument();
});

test("removing a required chip blocks search until the filter is restored", async () => {
  const fetchMock = mockFetchRoutes({ searchResponses: [firstResponse] });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /remove france/i }));
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText(/add a location/i),
  ).toBeInTheDocument();
  expect(searchUrls(fetchMock)).toHaveLength(0);
  expect(
    within(screen.getByRole("dialog", { name: /refine search filters/i })).getByLabelText(
      /location/i,
    ),
  ).toHaveValue("");
});

test("opens a result detail route and restores it from cached search state", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  const { unmount } = render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(
    await screen.findByRole("button", { name: /mont blanc escape/i }),
  );

  expect(window.location.pathname).toBe("/resorts/mont-blanc-escape");
  expect(await screen.findByTestId("selected-resort-page")).toHaveTextContent(
    "Mont Blanc Escape",
  );
  expect(
    screen.getByText(/weather signal suggests some disruption risk right now/i),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /risks/i })).toBeInTheDocument();

  unmount();
  render(<App />);

  expect(await screen.findByTestId("selected-resort-page")).toHaveTextContent(
    "Mont Blanc Escape",
  );
});

test("supports month-aware search and displays planning details", async () => {
  const fetchMock = mockFetchRoutes({ searchResponses: [planningResponse] });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /adjust filters/i }));
  await user.click(screen.getByRole("button", { name: /^month$/i }));
  await user.selectOptions(screen.getByLabelText(/travel month/i), "2");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText(/best ski trips for february/i),
  ).toBeInTheDocument();
  const [searchUrl] = searchUrls(fetchMock);
  expect(searchUrl).toContain("travel_month=2");
  expect(searchUrl).not.toContain("trip_start_date");
  expect(searchUrl).not.toContain("trip_end_date");
  await user.click(screen.getByRole("button", { name: /alpine horizon/i }));

  expect(screen.getByText(/trip fit combines snow outlook/i)).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /current conditions/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /travel window/i })).toBeInTheDocument();
  expect(screen.getByText(/planning for february/i)).toBeInTheDocument();
  expect(screen.getByText(/^Evidence type$/i)).toBeInTheDocument();
  expect(screen.getByText(/^Historical weather records$/i)).toBeInTheDocument();
  expect(screen.getAllByText(/typical snow/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/128 cm/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/avg high/i)).toBeInTheDocument();
  expect(screen.getByText(/-2.4°C/i)).toBeInTheDocument();
  expect(screen.getByText(/historical seasons/i)).toBeInTheDocument();
  expect(screen.getByText(/best months/i)).toBeInTheDocument();
  expect(
    screen.getByText(
      /using historical weather records for this month together with seasonal patterns/i,
    ),
  ).toBeInTheDocument();
  expect(screen.getByTestId("result-details")).toHaveTextContent(
    "January, February, March",
  );
});

test("manual exact-date travel window sends only date fields", async () => {
  const fetchMock = mockFetchRoutes({ searchResponses: [firstResponse] });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /adjust filters/i }));
  await user.click(screen.getByRole("button", { name: /exact dates/i }));
  await user.type(screen.getByLabelText(/trip start date/i), "2026-04-09");
  await user.type(screen.getByLabelText(/trip end date/i), "2026-04-16");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", {
      name: /alpine horizon/i,
      level: 3,
    }),
  ).toBeInTheDocument();
  const [searchUrl] = searchUrls(fetchMock);
  expect(searchUrl).toContain("trip_start_date=2026-04-09");
  expect(searchUrl).toContain("trip_end_date=2026-04-16");
  expect(searchUrl).not.toContain("travel_month");
});

test("renders an empty state when the backend returns no results", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [emptyResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText(/no matching ski trips yet/i),
  ).toBeInTheDocument();
});

test("saves the selected result as the current trip and shows the summary", async () => {
  const savedTrip = {
    resort_id: "alpine-horizon",
    resort_name: "Alpine Horizon",
    selected_ski_area_id: "alpine-horizon-main-bowl",
    selected_ski_area_name: "Alpine Horizon Main Bowl",
    selected_stay_base_name: "Pine Chalet Zone",
    selected_area_name: "Pine Chalet Zone",
    travel_month: 2,
    booking_status: "booked_elsewhere",
    created_at: "2026-04-12T10:00:00+00:00",
    updated_at: "2026-04-12T10:00:00+00:00",
    last_checked_at: null,
  };
  vi.stubGlobal(
    "fetch",
    mockFetchRoutes({
      searchResponses: [firstResponse],
      saveCurrentTripResponse: savedTrip,
    }),
  );

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /adjust filters/i }));
  await user.click(screen.getByRole("button", { name: /^month$/i }));
  await user.selectOptions(screen.getByLabelText(/travel month/i), "2");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  await screen.findByRole("heading", {
    name: /alpine horizon/i,
    level: 3,
  });
  await user.click(screen.getByRole("button", { name: /alpine horizon/i }));

  await user.selectOptions(screen.getByLabelText(/booking status/i), "booked_elsewhere");
  await user.click(screen.getByRole("button", { name: /save as current trip/i }));

  expect(await screen.findByText(/saved/i)).toBeInTheDocument();
  expect(
    screen.getByText("Alpine Horizon Main Bowl - Pine Chalet Zone - February"),
  ).toBeInTheDocument();
  expect(screen.getByLabelText(/booking status/i)).toHaveValue("booked_elsewhere");
});

test("current trip view renders an empty state when no trip is saved", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes());

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /current trip/i }));

  expect(await screen.findByText(/save a resort first/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /go to search/i })).toBeInTheDocument();
});

test("current trip view shows summary and supports mark checked", async () => {
  const currentTrip = currentTripSummaryResponse.trip;
  const markedTrip = {
    ...currentTrip,
    last_checked_at: "2026-04-12T11:00:00+00:00",
  };
  const updatedSummary = {
    ...currentTripSummaryResponse,
    trip: markedTrip,
    comparison_basis: {
      kind: "since_last_check",
      baseline_at: "2026-04-12T11:00:00+00:00",
      label: "Since last check",
    },
    delta: {
      status: "unchanged",
      summary: "No newer conditions refresh has landed since the comparison baseline.",
      changes: [],
    },
  };

  const fetchMock = vi
    .fn()
    .mockImplementationOnce(() => Promise.resolve(jsonResponse({ trip: currentTrip })))
    .mockImplementationOnce(() =>
      Promise.resolve(jsonResponse(currentTripSummaryResponse)),
    )
    .mockImplementationOnce(() => Promise.resolve(jsonResponse(currentTripEventsResponse)))
    .mockImplementationOnce(() => Promise.resolve(jsonResponse(markedTrip)))
    .mockImplementationOnce(() => Promise.resolve(jsonResponse(updatedSummary)))
    .mockImplementationOnce(() => Promise.resolve(jsonResponse(currentTripEventsResponse)));

  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /current trip/i }));

  expect(await screen.findByText(/planning update/i)).toBeInTheDocument();
  expect(screen.getAllByText(/since trip was saved/i)).toHaveLength(2);
  await user.click(screen.getByRole("button", { name: /mark checked/i }));

  expect(await screen.findAllByText(/since last check/i)).toHaveLength(2);
  expect(screen.getByText(/no newer conditions refresh has landed/i)).toBeInTheDocument();
});
