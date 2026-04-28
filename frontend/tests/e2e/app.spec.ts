import { expect, type Page, test } from "@playwright/test";

const mockSearchResult = {
  resort_id: "alpine-horizon",
  resort_name: "Alpine Horizon",
  region: "Savoie, France",
  selected_ski_area_id: "alpine-horizon-main-bowl",
  selected_ski_area_name: "Alpine Horizon Main Bowl",
  selected_stay_base_name: "Pine Chalet Zone",
  selected_stay_base_lift_distance: "near",
  stay_base_price_range: "EUR 150-280",
  selected_area_name: "Pine Chalet Zone",
  selected_area_lift_distance: "near",
  area_price_range: "EUR 150-280",
  rental_name: "Alpine Rentals",
  rental_price_range: "EUR 30-45/day",
  rating_estimate: 4.4,
  link: "/resorts/alpine-horizon",
  score: 0.88,
  budget_penalty: 0,
  conditions_summary: "Good fit for the requested travel window.",
  snow_confidence_score: 0.86,
  snow_confidence_label: "good",
  availability_status: "open",
  conditions_score: 0.84,
  conditions_provenance: {
    source_name: "open-meteo",
    source_type: "forecast",
    updated_at: "2026-04-12T09:00:00+00:00",
    freshness_status: "fresh",
    basis_summary: "Using current forecast and stored weather history.",
  },
  explanation: {
    highlights: [
      { label: "Pine Chalet Zone supports intermediate skiers." },
      { label: "Stay base keeps you close to the lift." },
    ],
    risks: [],
    confidence_contributors: [
      { label: "Good snow confidence.", direction: "positive" },
    ],
  },
  recommendation_narrative:
    "Alpine Horizon is a strong fit for an intermediate trip with near-lift access.",
  recommendation_confidence: 0.82,
  planning_summary: "Good fit for the requested travel window.",
  planning_provenance: {
    source_name: "archive_weather+forecast",
    source_type: "estimated",
    updated_at: "2026-04-12T09:00:00+00:00",
    freshness_status: "historical",
    basis_summary: "Using historical weather records and current forecast.",
  },
  planning_evidence_count: 6,
  best_travel_months: [1, 2, 3],
};

async function mockApi(page: Page) {
  await page.route("**/api/current-trip", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Authentication required" }),
    });
  });

  await page.route("**/api/parse-query", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        filters: {
          location: "Austria",
          skill_level: "intermediate",
          lift_distance: "near",
          travel_month: 4,
        },
        confidence: 1,
        unknown_parts: [],
      }),
    });
  });

  await page.route("**/api/search?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ results: [mockSearchResult] }),
    });
  });
}

test("brief-first search interprets filters and returns results", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/");

  await page
    .getByLabel("What are you looking for?")
    .fill("Cheap April ski trip in Austria for intermediates, close to the lift");
  await page.getByRole("button", { name: "Find resorts" }).click();

  await expect(page.getByText("What we understood")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /remove austria/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /remove intermediate/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /remove near lifts/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /remove april/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recommended resorts" }),
  ).toBeVisible();
  await expect(page.getByTestId("result-details")).toBeVisible();
});

test("manual month travel window shows planning details and booking CTA", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/");

  await page.getByRole("button", { name: "Show" }).click();
  await page.getByRole("button", { name: "Month" }).click();
  await page.getByLabel("Travel month").selectOption("2");
  await page.getByRole("button", { name: "Find resorts" }).click();

  await expect(page.getByText("Best matches for February")).toBeVisible();
  await expect(page.getByText("Planning for February")).toBeVisible();

  const bookingLink = page.getByRole("link", { name: "Book accommodation" });
  await expect(bookingLink).toBeVisible();
  await expect(bookingLink).toHaveAttribute(
    "href",
    /\/api\/outbound\/accommodation\//,
  );
});

test("manual exact-date travel window is visible in search results", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/");

  await page.getByRole("button", { name: "Show" }).click();
  await page.getByRole("button", { name: "Exact dates" }).click();
  await page.getByLabel("Trip start date").fill("2026-04-09");
  await page.getByLabel("Trip end date").fill("2026-04-16");
  await page.getByRole("button", { name: "Find resorts" }).click();

  await expect(
    page.getByText(/Best matches for Apr 9, 2026 to Apr 16, 2026/),
  ).toBeVisible();
  await expect(
    page.getByText(/Planning for Apr 9, 2026 to Apr 16, 2026/),
  ).toBeVisible();
  await expect(page.getByTestId("result-details")).toBeVisible();
});

test("anonymous current-trip view stays mobile-first", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");

  await page.getByRole("button", { name: "Current trip" }).click();

  await expect(
    page.getByRole("heading", { name: "Save a resort first" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Go to search" })).toBeVisible();
});
