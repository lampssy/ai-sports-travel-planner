import { expect, type Page, test } from "@playwright/test";

const mockSearchResult = {
  ski_region_id: "alpine-horizon",
  ski_region_name: "Alpine Horizon",
  rank: 1,
  score: 0.82,
  top_configuration: {
    configuration_id: "alpine-horizon|pine-chalet|main-bowl",
    ski_region_id: "alpine-horizon",
    stay_destination_id: "alpine-horizon-village",
    stay_destination_name: "Alpine Horizon Village",
    stay_base_id: "pine-chalet-zone",
    stay_base_name: "Pine Chalet Zone",
    focus_ski_area_id: "alpine-horizon-main-bowl",
    focus_ski_area_name: "Alpine Horizon Main Bowl",
    access: {
      ski_area_access_id: "pine-chalet-main-bowl",
      mode: "walk",
      lift_distance: "near",
      nearest_lift_name: "Main Bowl Gondola",
      distance_m: 250,
      duration_minutes: 4,
      is_direct: true,
    },
    selected_pass: {
      lift_pass_product_id: "alpine-horizon-local-pass",
      name: "Alpine Horizon Local Pass",
      validity_scope: "single_ski_area",
      accessible_ski_area_ids: ["alpine-horizon-main-bowl"],
      accessible_terrain_label: "Alpine Horizon Main Bowl",
      accessible_piste_km: 92,
      price_example: null,
      pass_fit_score: 0.9,
      tradeoff_summary: "Local terrain coverage at the lower pass price.",
    },
    alternative_passes: [],
    resilience: {
      alternative_area_count: 0,
      evidenced_alternative_count: 0,
      areas: [],
      summary: "No fallback ski area is modeled for this configuration.",
      ranking_component: 0,
    },
    score: 0.82,
    score_components: {
      legacy_base: 0.8, terrain: 0.8, skill_fit: 0.9, stay_base_access: 0.9,
      snow_evidence: 0.86, conditions: 0.84, budget: 0.8, travel_effort: 0.7,
    },
    budget_penalty: 0,
    travel_effort: null,
    conditions_summary: "Good fit for the requested travel window.",
    snow_confidence_score: 0.86,
    conditions_score: 0.84,
    planning_summary: "Good fit for the requested travel window.",
    planning_provenance: {
      source_name: "open-meteo-archive",
      source_type: "estimated",
      updated_at: "2026-04-12T09:00:00+00:00",
      freshness_status: "historical",
      basis_summary: "Using historical weather records and current forecast.",
    },
    planning_evidence_count: 6,
    planning_weather_metrics: null,
    evidence_quality: {
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
  },
  alternative_configurations: [],
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

  await expect(
    page.getByRole("heading", { name: "Search understood" }),
  ).toBeVisible();
  await expect(page.getByText("Trip context")).toBeVisible();
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
    page.getByRole("heading", { name: "Recommended ski trips" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /alpine horizon/i }).click();
  await expect(page).toHaveURL(/\/recommendations\/alpine-horizon$/);
  await expect(page.getByTestId("result-details")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Why this trip fits" }),
  ).toBeVisible();

  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByRole("heading", { name: "Recommended ski trips" }),
  ).toBeVisible();
});

test("manual month travel window shows planning details and booking CTA", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/");

  await page.getByRole("button", { name: "Adjust filters" }).click();
  await page.getByRole("button", { name: "Month" }).click();
  await page.getByLabel("Travel month").selectOption("2");
  await page.getByRole("button", { name: "Find resorts" }).click();

  await expect(page.getByText("Best ski trips for February")).toBeVisible();
  await page.getByRole("button", { name: /alpine horizon/i }).click();

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

  await page.getByRole("button", { name: "Adjust filters" }).click();
  await page.getByRole("button", { name: "Exact dates" }).click();
  await page.getByLabel("Trip start date").fill("2026-04-09");
  await page.getByLabel("Trip end date").fill("2026-04-16");
  await page.getByRole("button", { name: "Find resorts" }).click();

  await expect(
    page.getByText(/Best ski trips for Apr 9, 2026 to Apr 16, 2026/),
  ).toBeVisible();
  await page.getByRole("button", { name: /alpine horizon/i }).click();

  await expect(
    page.getByText(/Planning for Apr 9, 2026 to Apr 16, 2026/),
  ).toBeVisible();
  await expect(page.getByTestId("result-details")).toBeVisible();
});

test("anonymous current-trip view stays mobile-first", async ({ page }) => {
  await mockApi(page);
  await page.goto("/current-trip");

  await expect(
    page.getByRole("heading", { name: "Save a resort first" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Go to search" })).toBeVisible();
});

test("direct recommendation detail route without cached search state is graceful", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/recommendations/alpine-horizon");

  await expect(
    page.getByRole("heading", { name: "Run a search first" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Go to search" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: "Find resorts" })).toBeVisible();
});
