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

  await page.route("**/api/search", async (route) => {
    searchRequests.push(route.request().postDataJSON() as SearchV4Request);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(response),
    });
  });
}

test("submits a typed Search V4 request and renders grouped results", async ({
  page,
}) => {
  const searchRequests: SearchV4Request[] = [];
  await mockSearchV4Api(page, monthSearchResponse, searchRequests);
  await page.goto("/");
  await page.getByRole("button", { name: /search and rank/i }).click();
  await expect(page.getByText("Tignes - Val d'Isere")).toBeVisible();
  expect(searchRequests[0].intent.constraints.location).toEqual({
    country: "France",
  });
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
