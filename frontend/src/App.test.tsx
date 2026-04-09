import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";

const firstResponse = {
  results: [
    {
      resort_id: "alpine-horizon",
      resort_name: "Alpine Horizon",
      region: "Northern Alps",
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
    },
    {
      resort_id: "mont-blanc-escape",
      resort_name: "Mont Blanc Escape",
      region: "Northern Alps",
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
      explanation: {
        highlights: [{ label: "River Lane supports intermediate skiers." }],
        risks: [{ label: "Resort operations are limited at the moment." }],
        confidence_contributors: [
          { label: "Operational limits reduce certainty.", direction: "negative" },
        ],
      },
      recommendation_narrative: null,
      recommendation_confidence: 0.74,
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

beforeEach(() => {
  sessionStorage.clear();
  vi.restoreAllMocks();
});

test("renders the structured search form", () => {
  vi.stubGlobal("fetch", vi.fn());

  render(<App />);

  expect(screen.getByText(/ski trip search/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/skill level/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /show/i })).toBeInTheDocument();
});

test("renders ranked results and curated details after search", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => firstResponse,
    }),
  );

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /search ski trips/i }));

  expect(
    await screen.findByRole("heading", { name: "Alpine Horizon", level: 2 }),
  ).toBeInTheDocument();
  const details = screen.getByTestId("result-details");
  expect(screen.getByRole("heading", { name: /why it fits/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /^conditions$/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /^confidence$/i })).toBeInTheDocument();
  expect(details).toHaveTextContent("Fresh snowfall and strong visibility.");
  expect(details).toHaveTextContent("Alpine Horizon is a strong fit");
});

test("preserves the selected result when it still exists after a new search", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => firstResponse,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => secondResponse,
      }),
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
  expect(screen.getByTestId("result-details")).toHaveTextContent(
    "Visibility is mixed but the selected area remains viable.",
  );
});

test("renders an empty state when the backend returns no results", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => emptyResponse,
    }),
  );

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /search ski trips/i }));

  expect(
    await screen.findByText(/run a search to see ranked ski trip options/i),
  ).toBeInTheDocument();
});
