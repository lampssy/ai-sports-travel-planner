import { expect, type Page, test } from "@playwright/test";

import type {
  SearchResponse,
  SearchV4Request,
} from "../../../src/types";
import { monthSearchResponse } from "./fixtures/searchV4";

type MockSearchResult = SearchResponse | { status: number; detail: string };

async function mockSearchV4Api(
  page: Page,
  response: SearchResponse | MockSearchResult[],
  searchRequests: SearchV4Request[],
) {
  const responses = Array.isArray(response) ? response : [response];
  let responseIndex = 0;
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
    const next = responses[Math.min(responseIndex, responses.length - 1)];
    responseIndex += 1;
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

test("filter drawer closes with Escape and returns focus", async ({ page }) => {
  await mockSearchV4Api(page, monthSearchResponse, []);
  await page.goto("/");

  const trigger = page.getByRole("button", { name: "Adjust filters" });
  await trigger.click();
  await expect(page.getByRole("dialog", { name: "Adjust filters" })).toBeVisible();
  await page.keyboard.press("Escape");

  await expect(page.getByRole("dialog", { name: "Adjust filters" })).toBeHidden();
  await expect(trigger).toBeFocused();
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
  await expect(page.getByText("Replacement refinement?")).toBeVisible();
  await expect(page.getByText("Which stay style fits?")).toBeHidden();
  expect(await page.evaluate(() => window.scrollY)).toBe(scrollBeforeRerank);
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
