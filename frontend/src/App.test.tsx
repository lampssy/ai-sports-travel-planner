import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";

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
      explanation: {
        highlights: [{ label: "Pine Chalet Zone supports intermediate skiers." }],
        risks: [],
        confidence_contributors: [
          { label: "Snow outlook is strong for the trip window.", direction: "positive" },
        ],
      },
      recommendation_narrative:
        "Alpine Horizon is a strong fit for an intermediate trip thanks to near-lift access and strong conditions.",
      recommendation_confidence: 0.86,
      planning_summary: null,
      planning_provenance: null,
      planning_evidence_count: null,
      best_travel_months: [],
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
      explanation: {
        highlights: [{ label: "River Lane supports intermediate skiers." }],
        risks: [{ label: "Resort operations are limited at the moment." }],
        confidence_contributors: [
          { label: "Operational limits reduce certainty.", direction: "negative" },
        ],
      },
      recommendation_narrative: null,
      recommendation_confidence: 0.74,
      planning_summary: null,
      planning_provenance: null,
      planning_evidence_count: null,
      best_travel_months: [],
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
      best_travel_months: [1, 2, 3],
      conditions_summary:
        "Good fit for February, backed by 2 historical weather records.",
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
};

function jsonResponse(payload: unknown) {
  return {
    ok: true,
    json: async () => payload,
  };
}

function mockFetchRoutes(options?: {
  searchResponses?: unknown[];
  parseResponse?: unknown;
  currentTripResponse?: unknown;
  currentTripSummaryResponse?: unknown;
  saveCurrentTripResponse?: unknown;
  deleteCurrentTripResponse?: unknown;
  markCheckedResponse?: unknown;
}) {
  const {
    searchResponses = [],
    parseResponse: parsePayload,
    currentTripResponse: currentTripPayload = currentTripResponse,
    currentTripSummaryResponse: currentTripSummaryPayload = currentTripSummaryResponse,
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
      return Promise.resolve(jsonResponse(parsePayload ?? parseResponse));
    }
    if (url.includes("/api/search")) {
      return Promise.resolve(
        jsonResponse(queuedSearchResponses.shift() ?? emptyResponse),
      );
    }

    return Promise.reject(new Error(`Unhandled fetch URL in test: ${url}`));
  });
}

beforeEach(() => {
  sessionStorage.clear();
  vi.restoreAllMocks();
});

test("renders the structured search form", () => {
  vi.stubGlobal("fetch", mockFetchRoutes());

  render(<App />);

  expect(screen.getByText(/plan ski trips with clearer snow confidence/i)).toBeInTheDocument();
  expect(screen.getByText(/choose where and when to ski with more confidence/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/skill level/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /show/i })).toBeInTheDocument();
  expect(screen.queryByText(/search surface/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/uses the live backend/i)).not.toBeInTheDocument();
});

test("renders ranked results and curated details after search", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [firstResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /search ski trips/i }));

  expect(
    await screen.findByRole("heading", { name: "Alpine Horizon", level: 2 }),
  ).toBeInTheDocument();
  const details = screen.getByTestId("result-details");
  expect(screen.getByRole("heading", { name: /why this result/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /^confidence$/i })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /current conditions/i }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: /watchouts/i })).not.toBeInTheDocument();
  expect(details).toHaveTextContent("Forecast");
  expect(details).toHaveTextContent("open-meteo");
  expect(details).toHaveTextContent("Alpine Horizon is a strong fit");
  expect(details).toHaveTextContent("Ski Alpine Horizon Main Bowl, stay in Pine Chalet Zone");
  expect(details).not.toHaveTextContent("Snow outlook is strong for the trip window.");
  expect(screen.getByTestId("current-conditions-section")).toHaveClass("sm:col-span-2");
  expect(
    screen.getByRole("link", { name: /book accommodation/i }),
  ).toHaveAttribute(
    "href",
    "/api/outbound/accommodation/alpine-horizon?selected_ski_area_name=Alpine+Horizon+Main+Bowl&selected_stay_base_name=Pine+Chalet+Zone&source_surface=selected_result_details",
  );
});

test("falls back to a deterministic narrative when the top-result LLM summary is missing", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [secondResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /search ski trips/i }));

  expect(
    await screen.findByRole("heading", { name: "Mont Blanc Escape", level: 2 }),
  ).toBeInTheDocument();
  expect(screen.getByTestId("result-details")).toHaveTextContent(
    "Good snow confidence, but limited operations right now.",
  );
  expect(screen.getByTestId("result-details")).not.toHaveTextContent(
    "Mont Blanc Escape pairs River Lane with Mont Blanc Escape Ridge",
  );
});

test("interprets a trip brief and lets the user apply parsed filters", async () => {
  const fetchMock = mockFetchRoutes({ parseResponse });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/trip brief/i),
    "Looking for a fairly affordable ski trip in Austria, intermediate level, not too far from the lifts.",
  );
  await user.click(screen.getByRole("button", { name: /interpret trip brief/i }));

  expect(await screen.findByText(/confidence: 90%/i)).toBeInTheDocument();
  expect(screen.getByText(/Location: Austria/)).toBeInTheDocument();
  expect(
    screen.getByText(/Could not confidently map: fairly affordable/i),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /apply filters/i }));

  expect(screen.getByLabelText(/location/i)).toHaveValue("Austria");
  expect(screen.getByLabelText(/skill level/i)).toHaveValue("intermediate");
  expect(screen.getByLabelText(/travel month/i)).toHaveValue("3");
  expect(screen.getByLabelText(/lift distance/i)).toHaveValue("near");
  expect(screen.getByRole("button", { name: /hide/i })).toBeInTheDocument();
});

test("preserves the selected result when it still exists after a new search", async () => {
  vi.stubGlobal(
    "fetch",
    mockFetchRoutes({ searchResponses: [firstResponse, secondResponse] }),
  );

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /search ski trips/i }));
  await user.click(
    await screen.findByRole("button", { name: /mont blanc escape/i }),
  );

  await user.click(screen.getByRole("button", { name: /search ski trips/i }));

  await waitFor(() => {
    expect(screen.getByTestId("result-details")).toBeInTheDocument();
  });
  expect(screen.getByText(/resort operations are limited at the moment/i)).toBeInTheDocument();
  expect(screen.getByText(/caveats/i)).toBeInTheDocument();
});

test("supports month-aware search and displays planning details", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [planningResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.selectOptions(screen.getByLabelText(/travel month/i), "2");
  await user.click(screen.getByRole("button", { name: /search ski trips/i }));

  expect(await screen.findByText(/best resorts for february/i)).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /^confidence$/i })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /current conditions/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /travel window/i })).toBeInTheDocument();
  expect(screen.getByText(/planning for february/i)).toBeInTheDocument();
  expect(screen.getByTestId("current-conditions-section")).not.toHaveClass(
    "sm:col-span-2",
  );
  expect(screen.getByText(/^Evidence type$/i)).toBeInTheDocument();
  expect(screen.getByText(/^Historical weather records$/i)).toBeInTheDocument();
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

test("renders an empty state when the backend returns no results", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [emptyResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /search ski trips/i }));

  expect(
    await screen.findByText(/run a search to see ranked ski trip options/i),
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

  await user.selectOptions(screen.getByLabelText(/travel month/i), "2");
  await user.click(screen.getByRole("button", { name: /search ski trips/i }));

  await screen.findByRole("heading", { name: "Alpine Horizon", level: 2 });
  await user.selectOptions(screen.getByLabelText(/booking status/i), "booked_elsewhere");
  await user.click(screen.getByRole("button", { name: /save as current trip/i }));

  expect(await screen.findByText(/saved/i)).toBeInTheDocument();
  expect(
    screen.getByText("Alpine Horizon Main Bowl • Pine Chalet Zone • February"),
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
    .mockImplementationOnce(() => Promise.resolve(jsonResponse(markedTrip)))
    .mockImplementationOnce(() => Promise.resolve(jsonResponse(updatedSummary)));

  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /current trip/i }));

  expect(await screen.findByText(/what changed since last check/i)).toBeInTheDocument();
  expect(screen.getAllByText(/since trip was saved/i)).toHaveLength(2);
  await user.click(screen.getByRole("button", { name: /mark checked/i }));

  expect(await screen.findAllByText(/since last check/i)).toHaveLength(3);
  expect(screen.getByText(/no newer conditions refresh has landed/i)).toBeInTheDocument();
});
