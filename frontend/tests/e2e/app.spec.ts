import { expect, type Page, test } from "@playwright/test";

import type {
  SearchResponse,
  SearchWeatherEvidenceRequest,
  SearchWeatherEvidenceResponse,
  SearchV4Request,
  WeatherEvidencePoint,
} from "../../../src/types";
import { monthSearchResponse } from "./fixtures/searchV4";

type MockSearchResult = SearchResponse | { status: number; detail: string };
type MockWeatherResult =
  | SearchWeatherEvidenceResponse
  | { status: number; detail: string };
type WeatherResponder = (
  request: SearchWeatherEvidenceRequest,
  requestIndex: number,
) => MockWeatherResult;

const historicalProfile: WeatherEvidencePoint[] = [
  {
    date_or_month_day: "03-01",
    snow_depth_cm: null,
    snow_depth_cm_p25: 70,
    snow_depth_cm_p50: 110,
    snow_depth_cm_p75: 150,
    snowfall_cm: 3.8,
    temperature_min_c: -9,
    temperature_max_c: -3.4,
    rain_risk: null,
    thaw_risk: 0.08,
    wind_gust_kmh: null,
  },
  {
    date_or_month_day: "03-15",
    snow_depth_cm: null,
    snow_depth_cm_p25: 82,
    snow_depth_cm_p50: 128,
    snow_depth_cm_p75: 176,
    snowfall_cm: 4.2,
    temperature_min_c: -8,
    temperature_max_c: -2.1,
    rain_risk: null,
    thaw_risk: 0.18,
    wind_gust_kmh: null,
  },
  {
    date_or_month_day: "03-31",
    snow_depth_cm: null,
    snow_depth_cm_p25: 76,
    snow_depth_cm_p50: 119,
    snow_depth_cm_p75: 164,
    snowfall_cm: 3.1,
    temperature_min_c: -6,
    temperature_max_c: 0.4,
    rain_risk: null,
    thaw_risk: 0.32,
    wind_gust_kmh: null,
  },
];

function monthWeatherResponse(
  skiAreaId = "tignes-ski-area",
  limitations: string[] = [],
): Extract<SearchWeatherEvidenceResponse, { status: "available" }> {
  return {
    weather_evidence_version: "search-weather-evidence-v1",
    status: "available",
    ski_area_id: skiAreaId,
    evaluated_at: "2026-07-16T12:00:00Z",
    cache_valid_until: "2099-07-16T12:05:00Z",
    evidence: {
      mode: "climatology",
      window_label: "March",
      elevation_band: "mid_mountain",
      elevation_m: 2400,
      elevation_status: "exact",
      interpretation: "Historically reliable at mid-mountain in March.",
      limitations,
      historical: {
        source_label: "Open-Meteo archive climatology",
        source_model: "ERA5-Land",
        computed_at: "2026-07-15T02:00:00Z",
        baseline_start_year: 1995,
        baseline_end_year: 2024,
        evidence_seasons: 30,
        latest_archive_year: 2024,
        provenance_status: "homogeneous",
        sources: [
          {
            source_model: "ERA5-Land",
            computed_at: "2026-07-15T02:00:00Z",
            baseline_period: "normal_30y",
            baseline_start_year: 1995,
            baseline_end_year: 2024,
            evidence_seasons: 30,
            latest_archive_year: 2024,
            elevation_m: 2400,
            row_count: 3,
            profile_dates: ["03-01", "03-15", "03-31"],
          },
        ],
        snow_depth_cm_p25: 82,
        snow_depth_cm_p50: 128,
        snow_depth_cm_p75: 176,
        probability_snow_depth_ge_30cm: 0.87,
        average_daily_snowfall_cm: 4.2,
        average_max_temperature_c: -2.1,
        daily_profile: historicalProfile,
      },
      forecast: null,
    },
  };
}

function forecastWeatherResponse(
  head = "forecast-head-1",
  cacheValidUntil = "2099-07-16T13:00:00Z",
): Extract<SearchWeatherEvidenceResponse, { status: "available" }> {
  return {
    ...monthWeatherResponse(),
    cache_valid_until: cacheValidUntil,
    evidence: {
      ...monthWeatherResponse().evidence,
      mode: "forecast_assisted",
      window_label: "20-22 July 2026",
      interpretation: "Fresh forecast evidence supports the selected dates.",
      forecast: {
        source_label: "Open-Meteo forecast",
        source_model: "best_match",
        issued_at:
          head === "forecast-head-1"
            ? "2026-07-16T11:00:00Z"
            : "2026-07-16T12:30:00Z",
        provenance_status: "homogeneous",
        sources: [
          {
            forecast_run_id: head,
            forecast_source_key: "open-meteo",
            source_label: "Open-Meteo forecast",
            source_model: "best_match",
            issued_at: "2026-07-16T11:00:00Z",
            elevation_m: 2400,
            row_count: 2,
            profile_dates: ["2026-07-20", "2026-07-21"],
          },
        ],
        coverage_status: "partial",
        usable_date_count: 2,
        requested_date_count: 3,
        average_forecast_share: 0.8,
        daily_profile: [
          {
            date_or_month_day: "2026-07-20",
            snow_depth_cm: 112,
            snow_depth_cm_p25: null,
            snow_depth_cm_p50: null,
            snow_depth_cm_p75: null,
            snowfall_cm: 7.4,
            temperature_min_c: -7,
            temperature_max_c: -1,
            rain_risk: 0.1,
            thaw_risk: 0.2,
            wind_gust_kmh: 46,
          },
          {
            date_or_month_day: "2026-07-21",
            snow_depth_cm: 118,
            snow_depth_cm_p25: null,
            snow_depth_cm_p50: null,
            snow_depth_cm_p75: null,
            snowfall_cm: 5.1,
            temperature_min_c: -8,
            temperature_max_c: -2,
            rain_risk: 0,
            thaw_risk: 0,
            wind_gust_kmh: 10,
          },
        ],
      },
    },
  };
}

async function mockWeatherEvidenceApi(
  page: Page,
  responder: WeatherResponder = (request) =>
    monthWeatherResponse(request.ski_area_id),
  weatherRequests: SearchWeatherEvidenceRequest[] = [],
  responseGates: Array<Promise<void> | undefined> = [],
) {
  await page.route("**/api/search/weather-evidence", async (route) => {
    const request = route.request().postDataJSON() as SearchWeatherEvidenceRequest;
    const requestIndex = weatherRequests.length;
    weatherRequests.push(request);
    const next = responder(request, requestIndex);
    await responseGates[requestIndex];
    if ("status" in next && typeof next.status === "number") {
      await route.fulfill({
        status: next.status,
        contentType: "application/json",
        body: JSON.stringify({ detail: next.detail }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(next),
    });
  });
}

async function mockSearchV4Api(
  page: Page,
  response: SearchResponse | MockSearchResult[],
  searchRequests: SearchV4Request[],
  responseGates: Array<Promise<void> | undefined> = [],
  weatherResponder?: WeatherResponder,
  weatherRequests: SearchWeatherEvidenceRequest[] = [],
  weatherResponseGates: Array<Promise<void> | undefined> = [],
) {
  const responses = Array.isArray(response) ? response : [response];
  let responseIndex = 0;
  await mockWeatherEvidenceApi(
    page,
    weatherResponder,
    weatherRequests,
    weatherResponseGates,
  );
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
          location: "France",
          travel_month: 3,
          skill_level: "intermediate",
        },
        confidence: 1,
        unknown_parts: [],
        assumptions: [],
      }),
    });
  });

  await page.route("**/api/search", async (route) => {
    searchRequests.push(route.request().postDataJSON() as SearchV4Request);
    const currentResponseIndex = responseIndex;
    const next = responses[Math.min(currentResponseIndex, responses.length - 1)];
    responseIndex += 1;
    await responseGates[currentResponseIndex];
    if ("status" in next) {
      await route.fulfill({
        status: next.status,
        contentType: "application/json",
        body: JSON.stringify({ detail: next.detail }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(next),
    });
  });
}

function refinementResponse(): SearchResponse {
  const response = structuredClone(monthSearchResponse);
  response.refinements = [
    {
      question_id: "snow-priority",
      question: "What should break the tie?",
      reason: "One answer could reorder your top results.",
      options: [
        {
          label: "Snow reliability",
          description: "Favor high-altitude options.",
          intent_changed: true,
          group_priority_patches: [],
          factor_preference_patches: [],
          objective_patches: [
            { factor_id: "trip_window_snow_fit", importance: "high" },
          ],
          preview: {
            top_rank_changes: [
              {
                ski_region_id: "paradiski",
                previous_rank: 2,
                preview_rank: 1,
              },
            ],
            eligible_candidate_count_delta: 0,
          },
        },
        {
          label: "Shorter journey",
          description: "Minimize travel effort.",
          intent_changed: false,
          group_priority_patches: [],
          factor_preference_patches: [],
          objective_patches: [],
        },
      ],
    },
    {
      question_id: "stay-style",
      question: "Which stay style fits?",
      reason: "Your stay preference can change the leading base.",
      options: [
        {
          label: "Quiet base",
          description: "Prefer a quieter local pace.",
          intent_changed: true,
          group_priority_patches: [],
          factor_preference_patches: [],
          objective_patches: [],
        },
      ],
    },
  ];
  return response;
}

function rerankedResponse(): SearchResponse {
  const response = structuredClone(monthSearchResponse);
  response.results = [response.results[1], response.results[0]];
  response.results[0].rank = 1;
  response.results[1].rank = 2;
  response.refinements = [
    {
      question_id: "replacement",
      question: "Replacement refinement?",
      reason: "The reranked result has one remaining decision.",
      options: [
        {
          label: "Keep balanced",
          description: "Keep the current balance.",
          intent_changed: false,
          group_priority_patches: [],
          factor_preference_patches: [],
          objective_patches: [],
        },
      ],
    },
  ];
  return response;
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport);
}

async function scrollYAfterLayout(page: Page) {
  return page.evaluate(
    () =>
      new Promise<number>((resolve) => {
        window.requestAnimationFrame(() => {
          window.requestAnimationFrame(() => resolve(window.scrollY));
        });
      }),
  );
}

async function submitHomepageBrief(page: Page, brief: string) {
  await page.getByLabel("Describe your ski trip").fill(brief);
  await page.getByRole("button", { name: "Find resorts" }).click();
  const heading = page.getByRole("heading", { name: "Recommended ski trips" });
  await expect(heading).toBeVisible();
  await expect(heading).toBeFocused();
  await expect(page.getByLabel("Trip brief")).toHaveValue(brief);
}

test("desktop homepage submits once, preserves the brief, and focuses results", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");

  const brief = "A snow-reliable intermediate trip in France for March";
  await submitHomepageBrief(page, brief);

  expect(searchRequests).toHaveLength(1);
  expect(searchRequests[0].intent.constraints.location).toEqual({
    country: "France",
  });
  await expectNoHorizontalOverflow(page);
});

test("filter drawer preserves edited-control focus, traps focus, and restores the trigger", async ({ page }) => {
  await mockSearchV4Api(page, monthSearchResponse, []);
  await page.goto("/");

  const trigger = page.getByRole("button", { name: "Adjust filters" });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Adjust filters" });
  await expect(dialog).toBeVisible();
  const close = dialog.getByRole("button", { name: "Close filters" });
  const lastControl = dialog.getByRole("button", { name: "Large lift network" });
  await expect(close).toBeFocused();
  await expect(page.getByRole("button", { name: "Dismiss filters" })).toHaveCount(0);
  expect(
    await page.locator(".app-shell > :not(.drawer-layer)").evaluateAll((elements) =>
      elements.every((element) => (element as HTMLElement).inert),
    ),
  ).toBe(true);

  const country = dialog.getByLabel("Country");
  await country.fill("");
  await country.focus();
  await page.keyboard.type("Austria");
  await expect(country).toHaveValue("Austria");
  await expect(country).toBeFocused();

  const skill = dialog.getByLabel("Skill");
  await skill.focus();
  await skill.selectOption("advanced");
  await expect(skill).toHaveValue("advanced");
  await expect(skill).toBeFocused();

  await lastControl.click();
  await expect(lastControl).toHaveAttribute("aria-pressed", "true");
  await expect(lastControl).toBeFocused();
  expect(
    await page.locator(".app-shell > :not(.drawer-layer)").evaluateAll((elements) =>
      elements.every((element) => (element as HTMLElement).inert),
    ),
  ).toBe(true);

  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(lastControl).toBeFocused();
  await page.keyboard.press("Escape");

  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
  expect(
    await page.locator(".app-shell > :not(.drawer-layer)").evaluateAll((elements) =>
      elements.every((element) => !(element as HTMLElement).inert),
    ),
  ).toBe(true);
  await expectNoHorizontalOverflow(page);
});

test("mobile homepage transition has no horizontal overflow", async ({ page }) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  const brief = "March in France with reliable snow and easy lift access";
  await submitHomepageBrief(page, brief);

  expect(searchRequests).toHaveLength(1);
  await expectNoHorizontalOverflow(page);
});

for (const [name, viewport] of [
  ["tablet", { width: 1024, height: 768 }],
  ["mobile", { width: 390, height: 844 }],
] as const) {
  test(`${name} results and dossier keep Current trip reachable`, async ({ page }) => {
    await mockSearchV4Api(page, monthSearchResponse, []);
    await page.setViewportSize(viewport);
    await page.goto("/");
    await submitHomepageBrief(page, "March in France with reliable snow");

    const currentTrip = page.getByRole("button", {
      name: "Current trip",
      exact: true,
    });
    await expect(currentTrip).toBeVisible();
    await currentTrip.click();
    await expect(page).toHaveURL(/\/current-trip$/);
    await page.getByRole("button", { name: /back to search/i }).click();

    await page
      .locator("article.recommendation-card")
      .first()
      .getByRole("link", { name: "View dossier" })
      .click();
    await expect(currentTrip).toBeVisible();
    await currentTrip.click();
    await expect(page).toHaveURL(/\/current-trip$/);
  });
}

test("anonymous current-trip route remains available", async ({ page }) => {
  await mockSearchV4Api(page, monthSearchResponse, []);
  await page.goto("/current-trip");
  await expect(
    page.locator("main").getByText("Trip companion", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/save a ranked configuration/i)).toBeVisible();
  await page.getByRole("button", { name: /back to search/i }).click();
  await expect(page).toHaveURL(/\/$/);
});

test("desktop board compares, selects alternatives, and reranks in place", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(
    page,
    [refinementResponse(), rerankedResponse(), monthSearchResponse],
    searchRequests,
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");

  const firstToggle = page.getByRole("button", {
    name: /collapse tignes - val d'isere/i,
  });
  const secondToggle = page.getByRole("button", {
    name: /expand les arcs - peisey vallandry/i,
  });
  const stableSecondToggle = page.locator(
    'button[aria-controls="recommendation-paradiski"]',
  );
  await expect(firstToggle).toHaveAttribute("aria-expanded", "true");

  await page.getByRole("button", { name: "Current trip", exact: true }).click();
  await expect(page.getByText("Trip companion", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /back to search/i }).click();
  await expect(
    page.getByRole("button", { name: /select le lac with espace killy pass/i }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(stableSecondToggle).toHaveAttribute("aria-expanded", "false");
  await secondToggle.focus();
  await page.keyboard.press("Enter");
  await expect(stableSecondToggle).toBeFocused();
  await expect(stableSecondToggle).toHaveAttribute("aria-expanded", "true");
  await expect(firstToggle).toHaveAttribute("aria-expanded", "true");

  const firstCard = page.locator("article.recommendation-card").first();
  await firstCard
    .getByRole("button", { name: /select le lac with tignes local pass/i })
    .click();
  await expect(firstCard.getByText("Tignes local pass", { exact: true }).first()).toBeVisible();
  await expect(firstCard.getByText("150 km", { exact: true })).toBeVisible();
  await expect(firstCard.getByRole("link", { name: "View dossier" })).toHaveAttribute(
    "href",
    "/recommendations/tignes-val-disere?candidate=tignes-access--tignes-local-pass",
  );
  await expect(firstToggle).toHaveAttribute("aria-expanded", "true");

  await page.getByRole("radio", { name: /snow reliability/i }).click();
  await expect(page.getByText("One result would move from #2 to #1.")).toBeVisible();
  await page.screenshot({
    path: "../.superpowers/sdd/task-5-results-desktop.png",
    fullPage: true,
  });
  await page.evaluate(() => window.scrollTo({ top: 260 }));
  const scrollBeforeRerank = await page.evaluate(() => window.scrollY);
  await page.getByRole("button", { name: "Apply and rerank" }).click();
  await expect(
    page.getByRole("heading", { name: /tignes - val d'isere/i }),
  ).toBeVisible();
  await expect(
    page.locator(".rerank-feedback").getByText(/2 recommendations changed position/i),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recommended ski trips" }),
  ).toBeFocused();
  await expect(page.getByText("Replacement refinement?")).toBeVisible();
  await expect(page.getByText("Which stay style fits?")).toBeHidden();
  await expect.poll(() => scrollYAfterLayout(page)).toBe(scrollBeforeRerank);
  await expect(page.getByRole("button", { name: "Undo" })).toBeVisible();
  expect(searchRequests).toHaveLength(2);
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.locator(".rerank-feedback")).toContainText(
    "Previous trip decisions restored.",
  );
  expect(searchRequests).toHaveLength(3);
  expect(searchRequests[2].intent.objectives).toEqual([
    { factor_id: "pass_terrain_value", importance: "normal" },
  ]);
  await expectNoHorizontalOverflow(page);
});

test("refinement objective survives pass-priority edits and reranks", async ({
  page,
}) => {
  const refined = structuredClone(monthSearchResponse);
  refined.applied_intent.objectives = [
    { factor_id: "pass_terrain_value", importance: "normal" },
    { factor_id: "trip_window_snow_fit", importance: "high" },
  ];
  const passPrice = structuredClone(monthSearchResponse);
  passPrice.applied_intent.objectives = [
    { factor_id: "trip_window_snow_fit", importance: "high" },
    { factor_id: "pass_price_per_day", importance: "normal" },
  ];
  const snowOnly = structuredClone(monthSearchResponse);
  snowOnly.applied_intent.objectives = [
    { factor_id: "trip_window_snow_fit", importance: "high" },
  ];
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(
    page,
    [refinementResponse(), refined, passPrice, snowOnly],
    searchRequests,
  );
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");

  await page.getByRole("radio", { name: /snow reliability/i }).click();
  await page.getByRole("button", { name: "Apply and rerank" }).click();
  await expect.poll(() => searchRequests.length).toBe(2);

  await page.getByRole("button", { name: "Adjust" }).click();
  await page.getByLabel("Value objective").selectOption("pass_price_per_day");
  await page.getByRole("button", { name: "Close filters" }).click();
  await page.getByRole("button", { name: "Update results" }).click();
  await expect.poll(() => searchRequests.length).toBe(3);

  await page.getByRole("button", { name: "Adjust" }).click();
  await page.getByLabel("Value objective").selectOption("");
  await page.getByRole("button", { name: "Close filters" }).click();
  await page.getByRole("button", { name: "Update results" }).click();
  await expect.poll(() => searchRequests.length).toBe(4);

  expect(searchRequests[1].intent.objectives).toEqual(refined.applied_intent.objectives);
  expect(searchRequests[2].intent.objectives).toEqual(passPrice.applied_intent.objectives);
  expect(searchRequests[3].intent.objectives).toEqual(snowOnly.applied_intent.objectives);
  expect(searchRequests[3].already_answered_question_ids).toEqual([
    "snow-priority",
  ]);
});

test("a no-op refinement focuses the next queued control without reranking", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, refinementResponse(), searchRequests);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");

  await page.evaluate(() => window.scrollTo(0, 260));
  const scrollBeforeApply = await scrollYAfterLayout(page);
  await page.getByRole("radio", { name: /shorter journey/i }).click();
  await page.getByRole("button", { name: "Keep current ranking" }).click();

  await expect(page.locator(".rerank-feedback")).toContainText(
    "Current ranking kept.",
  );
  await expect(page.getByRole("radio", { name: /quiet base/i })).toBeFocused();
  expect(searchRequests).toHaveLength(1);
  await expect.poll(() => scrollYAfterLayout(page)).toBe(scrollBeforeApply);
});

test("saving displayed results ignores unapplied drawer dates", async ({ page }) => {
  const saveRequests: Array<Record<string, unknown>> = [];
  page.on("request", (request) => {
    if (request.method() === "PUT" && request.url().endsWith("/api/current-trip")) {
      saveRequests.push(request.postDataJSON() as Record<string, unknown>);
    }
  });
  await mockSearchV4Api(page, monthSearchResponse, []);
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");

  await page.getByRole("button", { name: "Adjust" }).click();
  await page.getByLabel("Travel window").selectOption("dates");
  await page.getByLabel("Trip start date").fill("2027-04-10");
  await page.getByLabel("Trip end date").fill("2027-04-17");
  await page.getByRole("button", { name: "Close filters" }).click();
  await page
    .locator("article.recommendation-card")
    .first()
    .getByRole("button", { name: "Save as current trip" })
    .click();

  await expect.poll(() => saveRequests.length).toBe(1);
  expect(saveRequests[0]).toMatchObject({
    travel_month: 3,
    trip_start_date: null,
    trip_end_date: null,
  });
});

test("a delayed rerank cannot restore results scroll on Current trip", async ({
  page,
}) => {
  let releaseRerank: (() => void) | undefined;
  const rerankGate = new Promise<void>((resolve) => {
    releaseRerank = resolve;
  });
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(
    page,
    [refinementResponse(), rerankedResponse()],
    searchRequests,
    [undefined, rerankGate],
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");
  await page.getByRole("radio", { name: /snow reliability/i }).click();
  await page.evaluate(() => window.scrollTo(0, 260));
  await page.getByRole("button", { name: "Apply and rerank" }).click();
  await expect.poll(() => searchRequests.length).toBe(2);

  await page.getByRole("button", { name: "Current trip", exact: true }).click();
  await expect(page.getByText("Trip companion", { exact: true })).toBeVisible();
  await page.evaluate(() => {
    document.body.style.minHeight = "2000px";
    window.scrollTo(0, 40);
  });
  const rerankResponse = page.waitForResponse(
    (response) => response.url().includes("/api/search") && response.request().method() === "POST",
  );
  releaseRerank?.();
  await rerankResponse;
  await scrollYAfterLayout(page);
  await scrollYAfterLayout(page);

  expect(await page.evaluate(() => window.scrollY)).toBe(40);
});

test("a delayed rerank blocks chip edits and drawer entry", async ({ page }) => {
  let releaseRerank: (() => void) | undefined;
  const rerankGate = new Promise<void>((resolve) => {
    releaseRerank = resolve;
  });
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(
    page,
    [refinementResponse(), rerankedResponse()],
    searchRequests,
    [undefined, rerankGate],
  );
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");
  await page.getByRole("radio", { name: /snow reliability/i }).click();
  await page.getByRole("button", { name: "Apply and rerank" }).click();
  await expect.poll(() => searchRequests.length).toBe(2);

  await expect(page.getByRole("button", { name: "Adjust" })).toBeDisabled();
  const franceChip = page.getByRole("button", { name: "Remove France" });
  await expect(franceChip).toBeDisabled();
  await franceChip.dispatchEvent("click");
  releaseRerank?.();
  await expect(page.getByText("Replacement refinement?")).toBeVisible();

  expect(searchRequests[1].intent.constraints.location).toEqual({ country: "France" });
  await expect(page.getByRole("button", { name: "Remove France" })).toBeEnabled();
  await page.getByRole("button", { name: "Adjust" }).click();
  await expect(page.getByLabel("Country")).toHaveValue("France");
});

test("failed refinement apply preserves results and the selected option", async ({
  page,
}) => {
  await mockSearchV4Api(
    page,
    [
      refinementResponse(),
      { status: 503, detail: "Reranking is temporarily unavailable." },
    ],
    [],
  );
  await page.goto("/");
  await submitHomepageBrief(page, "March in France");
  const option = page.getByRole("radio", { name: /snow reliability/i });
  await option.click();
  await page.getByRole("button", { name: "Apply and rerank" }).click();

  await expect(
    page.getByRole("heading", { name: /tignes - val d'isere/i }),
  ).toBeVisible();
  await expect(option).toBeChecked();
  await expect(page.getByRole("alert")).toContainText(
    "Reranking is temporarily unavailable.",
  );
  await expect(page.getByRole("button", { name: /retry apply and rerank/i })).toBeEnabled();
});

test("mobile board advances refinements in document flow without overflow", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, refinementResponse(), searchRequests);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with easy lift access");

  await expect(page.getByText("What should break the tie?")).toBeVisible();
  await page.getByRole("button", { name: /skip for now/i }).click();
  await expect(page.getByText("Which stay style fits?")).toBeVisible();
  expect(searchRequests).toHaveLength(1);
  await page
    .getByRole("button", { name: /expand les arcs - peisey vallandry/i })
    .click();
  await expect(
    page.getByRole("button", { name: /collapse tignes - val d'isere/i }),
  ).toHaveAttribute("aria-expanded", "true");
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: "../.superpowers/sdd/task-5-results-mobile-390.png",
    fullPage: true,
  });
});

test("desktop dossier switches without search and collapses to the compact rail", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");

  await page.locator("article.recommendation-card").first().getByRole("link", {
    name: "View dossier",
  }).click();
  await expect(page).toHaveURL(
    /\/recommendations\/tignes-val-disere\?candidate=tignes-access--tignes-val-disere-pass$/,
  );
  const firstHeading = page.getByRole("heading", {
    name: "Tignes - Val d'Isere - Le Lac",
  });
  await expect(firstHeading).toBeFocused();
  expect(searchRequests).toHaveLength(1);

  const navigator = page.getByRole("navigation", {
    name: "Recommendation results",
  });
  await expect(navigator).toHaveCSS("width", "260px");
  await scrollYAfterLayout(page);
  await page.screenshot({
    path: "../.superpowers/sdd/task-6-dossier-desktop-expanded.png",
    fullPage: true,
  });
  await page.getByRole("button", {
    name: "Collapse recommendation navigator",
  }).click();
  await expect(navigator).toHaveCSS("width", "64px");
  await expect(firstHeading).toBeVisible();
  await scrollYAfterLayout(page);
  await page.screenshot({
    path: "../.superpowers/sdd/task-6-dossier-desktop-collapsed.png",
    fullPage: false,
  });

  await page.evaluate(() => window.scrollTo(0, 500));
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
  await page.getByRole("button", {
    name: /les arcs - peisey vallandry, rank 2/i,
  }).click();
  const secondHeading = page.getByRole("heading", {
    name: "Les Arcs - Peisey Vallandry - Arc 1800",
  });
  await expect(secondHeading).toBeFocused();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  await expect(page.getByText(/showing les arcs - peisey vallandry/i)).toBeAttached();
  expect(searchRequests).toHaveLength(1);
  await expectNoHorizontalOverflow(page);
});

for (const [name, viewport] of [
  ["desktop navigator", { width: 1440, height: 900 }],
  ["mobile switcher", { width: 390, height: 844 }],
] as const) {
  test(`${name} preserves the displayed selected alternative through route, weather, and save`, async ({ page }) => {
    const response = structuredClone(monthSearchResponse);
    const secondGroup = response.results[1];
    const alternative = structuredClone(secondGroup.top_configuration);
    alternative.candidate_id = "les-arcs-alt-access--les-arcs-local-pass";
    alternative.stay_base_id = "peisey-2000";
    alternative.stay_base_name = "Peisey 2000";
    alternative.ski_area_id = "peisey-ski-area";
    alternative.ski_area_name = "Peisey Vallandry";
    alternative.access.ski_area_access_id = "peisey-alt-access";
    alternative.selected_pass.lift_pass_product_id = "les-arcs-local-pass";
    alternative.selected_pass.name = "Les Arcs local pass";
    alternative.selected_pass.covered_ski_area_ids = ["peisey-ski-area"];
    alternative.selected_pass.accessible_piste_km_evidence!.source_entity_id =
      "les-arcs-local-pass";
    secondGroup.alternative_configurations = [alternative];
    const weatherRequests: SearchWeatherEvidenceRequest[] = [];
    const saveRequests: Array<Record<string, unknown>> = [];
    page.on("request", (request) => {
      if (request.method() === "PUT" && request.url().endsWith("/api/current-trip")) {
        saveRequests.push(request.postDataJSON() as Record<string, unknown>);
      }
    });
    await mockSearchV4Api(
      page,
      response,
      [],
      [],
      undefined,
      weatherRequests,
    );
    await page.setViewportSize(viewport);
    await page.goto("/");
    await submitHomepageBrief(page, "March in France with reliable snow");

    const secondCard = page.locator("article.recommendation-card").nth(1);
    await secondCard.getByRole("button", { name: /expand les arcs/i }).click();
    await secondCard
      .getByRole("button", { name: /select peisey 2000 with les arcs local pass/i })
      .click();
    await page
      .locator("article.recommendation-card")
      .first()
      .getByRole("link", { name: "View dossier" })
      .click();

    if (name === "desktop navigator") {
      const navigator = page.getByRole("navigation", {
        name: "Recommendation results",
      });
      await expect(navigator.getByText("Peisey 2000")).toBeVisible();
      await navigator
        .getByRole("button", { name: /les arcs - peisey vallandry, rank 2/i })
        .click();
    } else {
      await page.getByRole("button", { name: /recommendation 1 of 2/i }).click();
      const switchOption = page.getByRole("button", {
        name: "Switch to Les Arcs - Peisey Vallandry",
      });
      await expect(switchOption.getByText("Peisey 2000")).toBeVisible();
      await switchOption.click();
    }

    await expect(page).toHaveURL(
      /\/recommendations\/paradiski\?candidate=les-arcs-alt-access--les-arcs-local-pass$/,
    );
    await expect(
      page.getByRole("heading", {
        name: "Les Arcs - Peisey Vallandry - Peisey 2000",
      }),
    ).toBeFocused();
    await expect.poll(() => weatherRequests.at(-1)?.ski_area_id).toBe(
      "peisey-ski-area",
    );
    await page.getByRole("button", { name: "Save as current trip" }).click();
    await expect.poll(() => saveRequests.length).toBe(1);
    expect(saveRequests[0]).toMatchObject({
      stay_base_id: "peisey-2000",
      focus_ski_area_id: "peisey-ski-area",
      lift_pass_product_id: "les-arcs-local-pass",
    });
  });
}

test("month dossier loads one typed area, reuses cache, and renders the honest handoff", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  const weatherRequests: SearchWeatherEvidenceRequest[] = [];
  await mockSearchV4Api(
    page,
    monthSearchResponse,
    searchRequests,
    [],
    undefined,
    weatherRequests,
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");
  await page.locator("article.recommendation-card").first().getByRole("link", {
    name: "View dossier",
  }).click();

  await expect(page.getByText("Historical pattern")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Snow evidence for March" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "Historical snow-depth profile" }),
  ).toBeVisible();
  await page.getByText("View structured weather values").click();
  await expect(
    page.getByRole("table", { name: "Historical weather values" }),
  ).toBeVisible();
  await expect(page.getByText("Stay-base estimate, not live hotel inventory")).toBeVisible();
  const outbound = page.getByRole("link", { name: "Open accommodation search" });
  await expect(outbound).toHaveAttribute(
    "href",
    "/api/outbound/accommodation/tignes?stay_base_id=tignes-le-lac&focus_ski_area_id=tignes-ski-area&source_surface=recommendation_dossier",
  );
  expect(weatherRequests).toHaveLength(1);
  expect(weatherRequests[0]).toEqual({
    intent: monthSearchResponse.applied_intent,
    ski_area_id: "tignes-ski-area",
  });
  await expect(page.getByText(/booking\.com|available rooms|hotel rating/i)).toHaveCount(0);
  await expectNoHorizontalOverflow(page);
  await page.getByText("View structured weather values").click();
  await page.addStyleTag({
    content:
      ".search-command-header,.dossier-anchor-nav,.dossier-navigator{position:static!important}",
  });
  await scrollYAfterLayout(page);
  await page.screenshot({
    path: "../.superpowers/sdd/task-7-dossier-month-desktop.png",
    fullPage: true,
  });

  await page.getByRole("button", { name: "All results" }).click();
  await page.locator("article.recommendation-card").first().getByRole("link", {
    name: "View dossier",
  }).click();
  await expect(page.getByText("Historical pattern")).toBeVisible();
  expect(weatherRequests).toHaveLength(1);
});

test("forecast dossier exposes freshness, coverage, keyboard tabs, and chart alternatives", async ({
  page,
}) => {
  const searchResponse = structuredClone(monthSearchResponse);
  searchResponse.applied_intent.constraints.travel_window = {
    start_date: "2026-07-20",
    end_date: "2026-07-22",
  };
  const weatherRequests: SearchWeatherEvidenceRequest[] = [];
  await mockSearchV4Api(
    page,
    searchResponse,
    [],
    [],
    () => forecastWeatherResponse(),
    weatherRequests,
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await submitHomepageBrief(page, "Tignes from 20 to 22 July");
  await page.locator("article.recommendation-card").first().getByRole("link", {
    name: "View dossier",
  }).click();

  await expect(page.getByText("Forecast-assisted")).toBeVisible();
  await expect(page.getByText(/fresh at evaluation time/i)).toBeVisible();
  await expect(page.getByText(/partial coverage: 2 of 3 dates/i)).toBeVisible();
  const forecastTab = page.getByRole("tab", { name: "Forecast" });
  const historicalTab = page.getByRole("tab", { name: "Historical context" });
  await forecastTab.focus();
  await page.keyboard.press("ArrowRight");
  await expect(historicalTab).toBeFocused();
  await expect(historicalTab).toHaveAttribute("aria-selected", "true");
  await expect(
    page.getByRole("tabpanel", { name: "Historical context" }),
  ).toBeVisible();
  await page.keyboard.press("ArrowLeft");
  await expect(forecastTab).toBeFocused();
  await expect(
    page.getByRole("img", { name: "Forecast snow profile" }),
  ).toBeVisible();
  await expect(page.getByText(/dashed line: forecast depth/i)).toBeVisible();
  await expect(page.getByText(/diamond: rain or thaw risk/i)).toBeVisible();
  await expect(page.locator(".snow-chart__risk")).toHaveCount(1);
  expect(weatherRequests[0].intent.constraints.travel_window).toEqual({
    start_date: "2026-07-20",
    end_date: "2026-07-22",
  });
  await expectNoHorizontalOverflow(page);
  await page.addStyleTag({
    content:
      ".search-command-header,.dossier-anchor-nav,.dossier-navigator{position:static!important}",
  });
  await scrollYAfterLayout(page);
  await page.screenshot({
    path: "../.superpowers/sdd/task-7-dossier-forecast-desktop.png",
    fullPage: true,
  });
});

test("stale fallback and typed unavailable states keep dossier controls intact", async ({
  page,
}) => {
  let releaseEvidence: (() => void) | undefined;
  const evidenceGate = new Promise<void>((resolve) => {
    releaseEvidence = resolve;
  });
  const weatherRequests: SearchWeatherEvidenceRequest[] = [];
  await mockSearchV4Api(
    page,
    monthSearchResponse,
    [],
    [],
    (request) =>
      request.ski_area_id === "tignes-ski-area"
        ? monthWeatherResponse(request.ski_area_id, [
            "The selected forecast run was stale at evaluation time.",
          ])
        : {
            weather_evidence_version: "search-weather-evidence-v1",
            status: "unavailable",
            ski_area_id: request.ski_area_id,
            evaluated_at: "2026-07-16T12:00:00Z",
            cache_valid_until: "2099-07-16T12:05:00Z",
            unavailable_reason: "historical_evidence_unavailable",
            limitations: ["No supported historical evidence covers this ski area."],
          },
    weatherRequests,
    [evidenceGate],
  );
  await page.goto("/");
  await submitHomepageBrief(page, "March in France");
  await page.locator("article.recommendation-card").first().getByRole("link", {
    name: "View dossier",
  }).click();
  const snowAnchor = page.getByRole("link", { name: "Snow evidence" });
  await snowAnchor.focus();
  releaseEvidence?.();
  await expect(page.getByText(/selected forecast run was stale/i)).toBeVisible();
  await expect(snowAnchor).toBeFocused();
  await expect(page.getByRole("tab", { name: "Forecast" })).toHaveCount(0);

  await page.getByRole("button", {
    name: /les arcs - peisey vallandry, rank 2/i,
  }).click();
  await expect(
    page.getByRole("heading", { name: "Snow evidence unavailable" }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText(
    "Snow evidence is unavailable for Les Arcs.",
  );
  await expect(
    page.getByRole("heading", {
      name: "Les Arcs - Peisey Vallandry - Arc 1800",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Recommendation results" }),
  ).toBeVisible();
  expect(weatherRequests).toHaveLength(2);
});

test("transport failure is not cached and retry announces recovered evidence", async ({
  page,
}) => {
  const weatherRequests: SearchWeatherEvidenceRequest[] = [];
  await mockSearchV4Api(
    page,
    monthSearchResponse,
    [],
    [],
    (request, index) =>
      index === 0
        ? { status: 503, detail: "Stored weather evidence is temporarily unavailable." }
        : monthWeatherResponse(request.ski_area_id),
    weatherRequests,
  );
  await page.goto("/");
  await submitHomepageBrief(page, "March in France");
  await page.locator("article.recommendation-card").first().getByRole("link", {
    name: "View dossier",
  }).click();

  await expect(
    page.getByRole("heading", { name: "Snow evidence could not be loaded" }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText("could not be loaded");
  await expect(
    page.getByRole("heading", { name: "Tignes - Val d'Isere - Le Lac" }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Recommendation results" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retry snow evidence" }).click();
  await expect(page.getByText("Historical pattern")).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Snow evidence loaded");
  await expect(
    page.getByRole("button", { name: "Reload snow evidence" }),
  ).toBeFocused();
  expect(weatherRequests).toHaveLength(2);
});

test("expired forecast cache refetches and replaces the selected run head", async ({
  page,
}) => {
  const weatherRequests: SearchWeatherEvidenceRequest[] = [];
  const expiresSoon = new Date(Date.now() + 3000).toISOString();
  await mockSearchV4Api(
    page,
    monthSearchResponse,
    [],
    [],
    (_request, index) =>
      index === 0
        ? forecastWeatherResponse("forecast-head-1", expiresSoon)
        : forecastWeatherResponse("forecast-head-2"),
    weatherRequests,
  );
  await page.goto("/");
  await submitHomepageBrief(page, "March in France");
  const openDossier = () =>
    page.locator("article.recommendation-card").first().getByRole("link", {
      name: "View dossier",
    }).click();
  await openDossier();
  await expect(page.getByText(/selected run forecast-head-1/i)).toBeVisible();
  await page.getByRole("button", { name: "All results" }).click();
  await openDossier();
  await expect(page.getByText(/selected run forecast-head-1/i)).toBeVisible();
  expect(weatherRequests).toHaveLength(1);

  await page.getByRole("button", { name: "All results" }).click();
  await page.waitForTimeout(3100);
  await openDossier();
  await expect(page.getByText(/selected run forecast-head-2/i)).toBeVisible();
  await expect(page.getByText(/selected run forecast-head-1/i)).toHaveCount(0);
  expect(weatherRequests).toHaveLength(2);
});

test("late weather response cannot cross the selected ski-area context", async ({
  page,
}) => {
  let releaseFirst: (() => void) | undefined;
  const firstGate = new Promise<void>((resolve) => {
    releaseFirst = resolve;
  });
  await mockSearchV4Api(
    page,
    monthSearchResponse,
    [],
    [],
    (request) => {
      const response = monthWeatherResponse(request.ski_area_id);
      if (request.ski_area_id === "les-arcs-ski-area") {
        response.evidence = { ...response.evidence, window_label: "Les Arcs March" };
      }
      return response;
    },
    [],
    [firstGate],
  );
  await page.goto("/");
  await submitHomepageBrief(page, "March in France");
  await page.locator("article.recommendation-card").first().getByRole("link", {
    name: "View dossier",
  }).click();
  await expect(
    page.getByRole("heading", { name: "Loading snow evidence for Tignes" }),
  ).toBeVisible();
  await page.getByRole("button", {
    name: /les arcs - peisey vallandry, rank 2/i,
  }).click();
  await expect(
    page.getByRole("heading", { name: "Snow evidence for Les Arcs March" }),
  ).toBeVisible();
  releaseFirst?.();
  await page.waitForTimeout(100);
  await expect(
    page.getByRole("heading", { name: "Snow evidence for Les Arcs March" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Snow evidence for March" }),
  ).toHaveCount(0);
});

test("All results restores selected candidates, expansion state, and exact scroll", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.setViewportSize({ width: 1440, height: 650 });
  await page.goto("/");
  const brief = "March in France with reliable snow and lift access";
  await submitHomepageBrief(page, brief);

  const firstCard = page.locator("article.recommendation-card").first();
  await firstCard.getByRole("button", {
    name: /select le lac with tignes local pass/i,
  }).click();
  await page.getByRole("button", {
    name: /expand les arcs - peisey vallandry/i,
  }).click();
  await page.evaluate(() => window.scrollTo(0, 360));
  const expectedScroll = await page.evaluate(() => window.scrollY);
  expect(expectedScroll).toBeGreaterThan(0);
  await firstCard.getByRole("link", { name: "View dossier" }).dispatchEvent("click");
  await expect(page).toHaveURL(/candidate=tignes-access--tignes-local-pass$/);

  await page.getByRole("button", { name: "All results" }).click();
  await expect(page.getByLabel("Trip brief")).toHaveValue(brief);
  await expect(
    page.getByRole("button", { name: /select le lac with tignes local pass/i }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("button", { name: /collapse les arcs - peisey vallandry/i }),
  ).toHaveAttribute("aria-expanded", "true");
  await expect.poll(() => scrollYAfterLayout(page)).toBe(expectedScroll);
  await expect(firstCard.getByRole("link", { name: "View dossier" })).toBeFocused();
  expect(searchRequests).toHaveLength(1);
});

test("browser Back restores the exact results scroll without rerunning search", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.setViewportSize({ width: 1440, height: 650 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");
  const firstCard = page.locator("article.recommendation-card").first();
  await firstCard.getByRole("button", {
    name: /select le lac with tignes local pass/i,
  }).click();
  await page.getByRole("button", {
    name: /expand les arcs - peisey vallandry/i,
  }).click();
  await page.evaluate(() => window.scrollTo(0, 320));
  const expectedScroll = await page.evaluate(() => window.scrollY);
  await firstCard.getByRole("link", { name: "View dossier" }).dispatchEvent("click");

  await page.goBack();
  await expect(page.getByRole("heading", { name: "Recommended ski trips" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: /select le lac with tignes local pass/i }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("button", { name: /collapse les arcs - peisey vallandry/i }),
  ).toHaveAttribute("aria-expanded", "true");
  await expect.poll(() => scrollYAfterLayout(page)).toBe(expectedScroll);
  await expect(firstCard.getByRole("link", { name: "View dossier" })).toBeFocused();
  expect(searchRequests).toHaveLength(1);
});

test("dossier return focuses the results heading when the originating control no longer exists", async ({
  page,
}) => {
  await mockSearchV4Api(page, monthSearchResponse, []);
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");
  await page
    .locator("article.recommendation-card")
    .first()
    .getByRole("link", { name: "View dossier" })
    .click();
  await page
    .getByRole("button", { name: /select le lac with tignes local pass/i })
    .click();
  await page.getByRole("button", { name: "Back to results" }).click();

  await expect(
    page.getByRole("heading", { name: "Recommended ski trips" }),
  ).toBeFocused();
});

test("invalid dossier routes recover to a canonical top configuration", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.goto("/");
  await submitHomepageBrief(page, "March in France");

  await page.evaluate(() => {
    window.history.pushState(
      null,
      "",
      "/recommendations/not-a-region?candidate=not-a-candidate",
    );
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await expect(page).toHaveURL(
    /\/recommendations\/tignes-val-disere\?candidate=tignes-access--tignes-val-disere-pass$/,
  );
  await expect(
    page.getByRole("heading", { name: "Tignes - Val d'Isere - Le Lac" }),
  ).toBeVisible();

  await page.evaluate(() => {
    window.history.pushState(
      null,
      "",
      "/recommendations/paradiski?candidate=not-a-candidate",
    );
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await expect(page).toHaveURL(
    /\/recommendations\/paradiski\?candidate=les-arcs-access--paradiski-pass$/,
  );
  await expect(
    page.getByRole("heading", {
      name: "Les Arcs - Peisey Vallandry - Arc 1800",
    }),
  ).toBeVisible();
  expect(searchRequests).toHaveLength(1);
});

test("mobile dossier uses a keyboard-operable bounded switcher", async ({ page }) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with easy lift access");
  await page.locator("article.recommendation-card").first().getByRole("link", {
    name: "View dossier",
  }).click();

  await expect(
    page.getByRole("navigation", { name: "Recommendation results" }),
  ).toBeHidden();
  const switcher = page.getByRole("button", { name: /recommendation 1 of 2/i });
  await expect(switcher).toBeVisible();
  await switcher.focus();
  await page.keyboard.press("Enter");
  await expect(switcher).toHaveAttribute("aria-expanded", "true");
  const second = page.getByRole("button", {
    name: "Switch to Les Arcs - Peisey Vallandry",
  });
  await second.click();
  await expect(
    page.getByRole("heading", {
      name: "Les Arcs - Peisey Vallandry - Arc 1800",
    }),
  ).toBeFocused();
  await expect(page.getByText("Historical pattern")).toBeVisible();
  await expect(page.getByText("Stay-base estimate, not live hotel inventory")).toBeVisible();
  expect(searchRequests).toHaveLength(1);
  await expectNoHorizontalOverflow(page);
  await scrollYAfterLayout(page);
  await page.screenshot({
    path: "../.superpowers/sdd/task-7-dossier-mobile-390.png",
    fullPage: true,
  });
});

test("direct dossier load without search state offers recovery", async ({ page }) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.goto(
    "/recommendations/tignes-val-disere?candidate=tignes-access--tignes-val-disere-pass",
  );

  await expect(page.getByRole("heading", { name: "Run a search first" })).toBeVisible();
  await page.getByRole("button", { name: "Return to search" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByLabel("Describe your ski trip")).toBeVisible();
  expect(searchRequests).toHaveLength(0);
});

test("keyboard-only core flow keeps focus and route announcements logical", async ({
  page,
}) => {
  const response = structuredClone(monthSearchResponse);
  response.applied_intent.constraints.travel_window = {
    start_date: "2026-07-20",
    end_date: "2026-07-22",
  };
  await mockSearchV4Api(
    page,
    response,
    [],
    [],
    () => forecastWeatherResponse(),
  );
  await page.goto("/");

  const brief = page.getByLabel("Describe your ski trip");
  await brief.fill("Tignes from 20 to 22 July");
  await brief.press("Tab");
  await expect(page.getByRole("button", { name: "Find resorts" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Recommended ski trips" }),
  ).toBeFocused();

  const secondCardToggle = page.getByRole("button", {
    name: /expand les arcs - peisey vallandry/i,
  });
  const stableSecondCardToggle = page.locator(
    'button[aria-controls="recommendation-paradiski"]',
  );
  await secondCardToggle.focus();
  await page.keyboard.press("Enter");
  await expect(stableSecondCardToggle).toHaveAttribute("aria-expanded", "true");
  await expect(stableSecondCardToggle).toBeFocused();

  const scoring = page.locator("article.recommendation-card").first().locator("summary");
  await scoring.focus();
  await page.keyboard.press("Enter");
  await expect(scoring.locator("..")).toHaveAttribute("open", "");

  const dossier = page
    .locator("article.recommendation-card")
    .first()
    .getByRole("link", { name: "View dossier" });
  await dossier.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Tignes - Val d'Isere - Le Lac" }),
  ).toBeFocused();

  const historicalTab = page.getByRole("tab", { name: "Historical context" });
  await page.getByRole("tab", { name: "Forecast" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(historicalTab).toBeFocused();

  const secondRecommendation = page.getByRole("button", {
    name: /les arcs - peisey vallandry, rank 2/i,
  });
  await secondRecommendation.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", {
      name: "Les Arcs - Peisey Vallandry - Arc 1800",
    }),
  ).toBeFocused();
  await expect(
    page.locator('[aria-live="polite"]').filter({
      hasText: "Showing Les Arcs - Peisey Vallandry, stay in Arc 1800",
    }),
  ).toBeAttached();

  const back = page.getByRole("button", { name: "Back to results" });
  await back.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/$/);
  await expect(dossier).toBeFocused();
  await expectNoHorizontalOverflow(page);
});

test("failed initial search can be resubmitted without losing the brief", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(
    page,
    [
      { status: 503, detail: "Search is temporarily unavailable." },
      monthSearchResponse,
    ],
    searchRequests,
  );
  await page.goto("/");

  const brief = "March in France with reliable snow";
  await page.getByLabel("Describe your ski trip").fill(brief);
  await page.getByRole("button", { name: "Find resorts" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Search is temporarily unavailable.",
  );
  await expect(page.getByLabel("Describe your ski trip")).toHaveValue(brief);
  await expect(page.getByRole("button", { name: "Find resorts" })).toBeEnabled();

  await page.getByRole("button", { name: "Find resorts" }).click();
  await expect(
    page.getByRole("heading", { name: "Recommended ski trips" }),
  ).toBeFocused();
  expect(searchRequests).toHaveLength(2);
});

test("no results and missing metrics remain explicit and overflow-free", async ({
  page,
}) => {
  const noResults = structuredClone(monthSearchResponse);
  noResults.eligible_candidate_count = 0;
  noResults.results = [];

  const missingMetrics = structuredClone(monthSearchResponse);
  const configuration = missingMetrics.results[0].top_configuration;
  configuration.fit_score = null;
  configuration.lodging_estimate = null;
  configuration.selected_pass.price = null;
  configuration.selected_pass.accessible_piste_km = null;
  configuration.access.distance_m = null;
  configuration.access.duration_minutes = null;
  missingMetrics.results[0].fit_score = null;

  await mockSearchV4Api(page, [noResults, missingMetrics], []);
  await page.goto("/");
  await page.getByRole("button", { name: "Find resorts" }).click();
  await expect(
    page.getByRole("heading", { name: "No trip matches every hard constraint" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Adjust hard constraints" })).toBeVisible();

  await page.getByLabel("Trip brief").press("Enter");
  await expect(
    page.getByRole("heading", { name: "Recommended ski trips" }),
  ).toBeVisible();
  await expect(page.locator("article.recommendation-card").first()).toContainText("—");
  await expect(page.locator("body")).not.toContainText(/undefined|NaN|\[object Object\]/);
  await expectNoHorizontalOverflow(page);
});

test("results reflow at a 1440 viewport equivalent to 200 percent zoom", async ({
  page,
}) => {
  await mockSearchV4Api(page, refinementResponse(), []);
  await page.setViewportSize({ width: 720, height: 450 });
  await page.goto("/");
  await submitHomepageBrief(page, "March in France with reliable snow");

  await expect(page.getByText("Limited evidence — Fallback-heavy")).toBeVisible();
  await expect(page.getByText("Snow evidence is limited for the requested travel window.")).toBeVisible();
  await expectNoHorizontalOverflow(page);
  const motion = await page.locator(".recommendation-card__toggle").first().evaluate(
    (element) => getComputedStyle(element).transitionDuration,
  );
  expect(["0s", "0.01ms"]).toContain(motion);
});
