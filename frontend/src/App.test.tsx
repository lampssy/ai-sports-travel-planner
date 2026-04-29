import { render, screen } from "@testing-library/react";
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

function mockFetchRoutes(options?: {
  searchResponses?: unknown[];
  parseResponse?: unknown;
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

  expect(screen.getByText(/find the right ski window before you book/i)).toBeInTheDocument();
  expect(screen.getByText(/ai-assisted snow-aware planning/i)).toBeInTheDocument();
  expect(screen.getByText(/describe the trip in plain language/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/what are you looking for/i)).toBeInTheDocument();
  expect(screen.getByText(/your search filters/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /remove france/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /remove intermediate/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /show/i })).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: /recommended resorts/i }),
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
    await screen.findByRole("heading", { name: "Alpine Horizon", level: 3 }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /alpine horizon/i }));

  expect(window.location.pathname).toBe("/resorts/alpine-horizon");
  const details = screen.getByTestId("result-details");
  expect(screen.getByRole("heading", { name: /why this result/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /highlights/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /risks/i })).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /current conditions/i }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: /watchouts/i })).not.toBeInTheDocument();
  expect(details).toHaveTextContent("Forecast");
  expect(details).toHaveTextContent("open-meteo");
  expect(details).toHaveTextContent("Alpine Horizon is a strong fit");
  expect(details).toHaveTextContent("Ski Alpine Horizon Main Bowl, stay in Pine Chalet Zone");
  expect(details).toHaveTextContent("Combined from resort fit");
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

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", { name: "Mont Blanc Escape", level: 3 }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /mont blanc escape/i }));

  expect(screen.getByTestId("result-details")).toHaveTextContent(
    "Good snow confidence, but limited operations right now.",
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

  expect(
    await screen.findByText(/interpretation confidence:\s*90%/i),
  ).toBeInTheDocument();
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

  expect(screen.getByLabelText(/location/i)).toHaveValue("Austria");
  expect(screen.getByLabelText(/skill level/i)).toHaveValue("intermediate");
  expect(screen.getByLabelText(/travel month/i)).toHaveValue("3");
  expect(screen.getByLabelText(/lift distance/i)).toHaveValue("near");
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
    await screen.findByRole("heading", { name: "Alpine Horizon", level: 3 }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /remove apr 9, 2026 to apr 16, 2026/i }),
  ).toBeInTheDocument();
  const [searchUrl] = searchUrls(fetchMock);
  expect(searchUrl).toContain("trip_start_date=2026-04-09");
  expect(searchUrl).toContain("trip_end_date=2026-04-16");
  expect(searchUrl).not.toContain("travel_month");
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
  expect(screen.getByLabelText(/location/i)).toHaveValue("");
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
  expect(screen.getByText(/resort operations are limited at the moment/i)).toBeInTheDocument();
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

  await user.click(screen.getByRole("button", { name: /show/i }));
  await user.click(screen.getByRole("button", { name: /^month$/i }));
  await user.selectOptions(screen.getByLabelText(/travel month/i), "2");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText(/best matches for february/i)).toBeInTheDocument();
  const [searchUrl] = searchUrls(fetchMock);
  expect(searchUrl).toContain("travel_month=2");
  expect(searchUrl).not.toContain("trip_start_date");
  expect(searchUrl).not.toContain("trip_end_date");
  await user.click(screen.getByRole("button", { name: /alpine horizon/i }));

  expect(screen.getByText(/combined from resort fit/i)).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: /current conditions/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /travel window/i })).toBeInTheDocument();
  expect(screen.getByText(/planning for february/i)).toBeInTheDocument();
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

test("manual exact-date travel window sends only date fields", async () => {
  const fetchMock = mockFetchRoutes({ searchResponses: [firstResponse] });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /show/i }));
  await user.click(screen.getByRole("button", { name: /exact dates/i }));
  await user.type(screen.getByLabelText(/trip start date/i), "2026-04-09");
  await user.type(screen.getByLabelText(/trip end date/i), "2026-04-16");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", { name: "Alpine Horizon", level: 3 }),
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
    await screen.findByText(/no matching resorts yet/i),
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

  await user.click(screen.getByRole("button", { name: /show/i }));
  await user.click(screen.getByRole("button", { name: /^month$/i }));
  await user.selectOptions(screen.getByLabelText(/travel month/i), "2");
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  await screen.findByRole("heading", { name: "Alpine Horizon", level: 3 });
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

  expect(await screen.findByText(/what changed since last check/i)).toBeInTheDocument();
  expect(screen.getAllByText(/since trip was saved/i)).toHaveLength(2);
  await user.click(screen.getByRole("button", { name: /mark checked/i }));

  expect(await screen.findAllByText(/since last check/i)).toHaveLength(3);
  expect(screen.getByText(/no newer conditions refresh has landed/i)).toBeInTheDocument();
});
