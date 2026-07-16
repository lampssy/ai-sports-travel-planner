import { expect, type Page, test } from "@playwright/test";

import type { SearchV4Request } from "../../../src/types";
import { monthSearchResponse } from "./fixtures/searchV4";

async function mockSearchV4Api(
  page: Page,
  response: typeof monthSearchResponse,
  searchRequests: SearchV4Request[],
) {
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
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(response),
    });
  });
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
