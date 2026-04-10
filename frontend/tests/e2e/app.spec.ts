import { expect, test } from "@playwright/test";

test("trip brief flow applies filters and returns results", async ({ page }) => {
  await page.goto("/");

  await page
    .getByLabel("Trip brief")
    .fill("cheap france ski trip close to lift for intermediate");
  await page.getByRole("button", { name: "Interpret trip brief" }).click();

  await expect(page.getByText("Interpreted trip brief")).toBeVisible();
  await page.getByRole("button", { name: "Apply filters" }).click();

  await expect(page.getByLabel("Location")).toHaveValue("France");
  await expect(page.getByLabel("Skill level")).toHaveValue("intermediate");

  await page.getByRole("button", { name: "Search ski trips" }).click();

  await expect(page.getByRole("heading", { name: "Ranked results" })).toBeVisible();
  await expect(page.getByTestId("result-details")).toBeVisible();
});

test("month-aware search shows planning output and booking CTA", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Travel month").selectOption("2");
  await page.getByRole("button", { name: "Search ski trips" }).click();

  await expect(page.getByText("Best resorts for February")).toBeVisible();
  await expect(page.getByText("Planning for February")).toBeVisible();

  const bookingLink = page.getByRole("link", { name: "Book accommodation" });
  await expect(bookingLink).toBeVisible();
  await expect(bookingLink).toHaveAttribute(
    "href",
    /\/api\/outbound\/accommodation\//,
  );
});
