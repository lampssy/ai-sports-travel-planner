import { expect, type Page, test } from "@playwright/test";

import type {
  SearchResponse,
  SearchWeatherEvidenceRequest,
  SearchWeatherEvidenceResponse,
  WeatherEvidencePoint,
} from "../../../src/types";
import { monthSearchResponse } from "./fixtures/searchV4";

const fixedNow = new Date("2026-07-16T12:00:00Z");
const desktop = { width: 1440, height: 900 };
const tablet = { width: 1024, height: 768 };
const mobile = { width: 390, height: 844 };

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

function monthWeatherResponse(): SearchWeatherEvidenceResponse {
  return {
    weather_evidence_version: "search-weather-evidence-v1",
    status: "available",
    ski_area_id: "tignes-ski-area",
    evaluated_at: fixedNow.toISOString(),
    cache_valid_until: "2099-07-16T12:05:00Z",
    evidence: {
      mode: "climatology",
      window_label: "March",
      elevation_band: "mid_mountain",
      elevation_m: 2400,
      elevation_status: "exact",
      interpretation: "Historically reliable at mid-mountain in March.",
      limitations: [],
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

function forecastWeatherResponse(): SearchWeatherEvidenceResponse {
  return {
    ...monthWeatherResponse(),
    evidence: {
      ...monthWeatherResponse().evidence,
      mode: "forecast_assisted",
      window_label: "20-22 July 2026",
      interpretation: "Fresh forecast evidence supports the selected dates.",
      forecast: {
        source_label: "Open-Meteo forecast",
        source_model: "best_match",
        issued_at: "2026-07-16T11:00:00Z",
        provenance_status: "homogeneous",
        sources: [
          {
            forecast_run_id: "forecast-head-1",
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

function resultsResponse(): SearchResponse {
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
  ];
  return response;
}

function exactDateResponse(): SearchResponse {
  const response = structuredClone(monthSearchResponse);
  response.applied_intent.constraints.travel_window = {
    start_date: "2026-07-20",
    end_date: "2026-07-22",
  };
  return response;
}

async function mockApi(
  page: Page,
  response: SearchResponse,
  weatherResponse: SearchWeatherEvidenceResponse = monthWeatherResponse(),
) {
  await page.route("**/api/current-trip", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Authentication required" }),
    }),
  );
  await page.route("**/api/parse-query", (route) =>
    route.fulfill({
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
    }),
  );
  await page.route("**/api/search/weather-evidence", async (route) => {
    const request = route.request().postDataJSON() as SearchWeatherEvidenceRequest;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...weatherResponse, ski_area_id: request.ski_area_id }),
    });
  });
  await page.route("**/api/search", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(response),
    }),
  );
}

async function waitForStablePage(page: Page, heading: RegExp | string) {
  await expect(page.getByRole("heading", { name: heading }).first()).toBeVisible();
  await page.evaluate(async () => document.fonts.ready);
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        caret-color: transparent !important;
        scroll-behavior: auto !important;
        transition: none !important;
      }
    `,
  });
}

async function openResults(page: Page, response: SearchResponse) {
  await mockApi(page, response);
  await page.goto("/");
  await page
    .getByLabel("Describe your ski trip")
    .fill("A snow-reliable intermediate trip in France for March, close to the lifts");
  await page.getByRole("button", { name: "Find resorts" }).click();
  await waitForStablePage(page, "Recommended ski trips");
}

async function openDossier(
  page: Page,
  response: SearchResponse,
  weatherResponse: SearchWeatherEvidenceResponse,
) {
  await mockApi(page, response, weatherResponse);
  await page.goto("/");
  await page
    .getByLabel("Describe your ski trip")
    .fill("A snow-reliable intermediate trip in France for March, close to the lifts");
  await page.getByRole("button", { name: "Find resorts" }).click();
  await page
    .locator("article.recommendation-card")
    .first()
    .getByRole("link", { name: "View dossier" })
    .click();
  await waitForStablePage(page, "Tignes - Val d'Isere - Le Lac");
  await expect(page.getByRole("heading", { name: /Snow evidence for/ })).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(fixedNow);
});

for (const [name, viewport] of [
  ["desktop", desktop],
  ["tablet", tablet],
  ["mobile", mobile],
] as const) {
  test(`homepage ${name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockApi(page, monthSearchResponse);
    await page.goto("/");
    await page
      .getByLabel("Describe your ski trip")
      .fill("A snow-reliable intermediate trip in France for March, close to the lifts");
    await waitForStablePage(
      page,
      "Conditions-aware ski trips, planned around your window.",
    );

    await expect(page).toHaveScreenshot(`homepage-${name}.png`, {
      animations: "disabled",
      caret: "hide",
    });
  });

  test(`expanded results ${name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openResults(page, resultsResponse());
    await page
      .getByRole("button", { name: /expand les arcs - peisey vallandry/i })
      .click();
    await expect(
      page.getByRole("button", { name: /collapse les arcs - peisey vallandry/i }),
    ).toHaveAttribute("aria-expanded", "true");
    await page.evaluate(() => window.scrollTo(0, 0));

    await expect(page).toHaveScreenshot(`results-expanded-${name}.png`, {
      animations: "disabled",
      caret: "hide",
    });
  });
}

test("month dossier with expanded desktop navigator", async ({ page }) => {
  await page.setViewportSize(desktop);
  await openDossier(page, monthSearchResponse, monthWeatherResponse());

  await expect(page).toHaveScreenshot("dossier-month-expanded-desktop.png", {
    animations: "disabled",
    caret: "hide",
  });
  await expect(page).toHaveScreenshot("dossier-month-full-desktop.png", {
    animations: "disabled",
    caret: "hide",
    fullPage: true,
  });
});

test("exact-date dossier with collapsed desktop navigator", async ({ page }) => {
  await page.setViewportSize(desktop);
  await openDossier(page, exactDateResponse(), forecastWeatherResponse());
  await page
    .getByRole("button", { name: "Collapse recommendation navigator" })
    .click();
  await expect(page.getByRole("navigation", { name: "Recommendation results" })).toHaveAttribute(
    "data-collapsed",
    "true",
  );
  await page.evaluate(() => window.scrollTo(0, 0));

  await expect(page).toHaveScreenshot("dossier-dates-collapsed-desktop.png", {
    animations: "disabled",
    caret: "hide",
  });
});

test("mobile dossier switcher", async ({ page }) => {
  await page.setViewportSize(mobile);
  await openDossier(page, monthSearchResponse, monthWeatherResponse());
  await page.getByRole("button", { name: /recommendation 1 of 2/i }).click();
  await expect(page.getByRole("button", { name: /switch to les arcs/i })).toBeVisible();

  await expect(page).toHaveScreenshot("dossier-mobile-switcher.png", {
    animations: "disabled",
    caret: "hide",
  });
});

test("mobile dossier snow evidence", async ({ page }) => {
  await page.setViewportSize(mobile);
  await openDossier(page, monthSearchResponse, monthWeatherResponse());
  await page.getByRole("heading", { name: "Snow evidence for March" }).scrollIntoViewIfNeeded();

  await expect(page).toHaveScreenshot("dossier-mobile-snow-evidence.png", {
    animations: "disabled",
    caret: "hide",
  });
});
