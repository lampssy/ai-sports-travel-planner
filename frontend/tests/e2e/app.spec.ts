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

test("selected result can be saved as the current trip", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Travel month").selectOption("2");
  await page.getByRole("button", { name: "Search ski trips" }).click();

  await expect(page.getByTestId("result-details")).toBeVisible();
  await page.getByLabel("Booking status").selectOption("booked_elsewhere");
  await page.getByRole("button", { name: "Save as current trip" }).click();

  await expect(page.getByText("Saved")).toBeVisible();
  await expect(page.getByLabel("Booking status")).toHaveValue(
    "booked_elsewhere",
  );
});

test("current trip view shows the saved trip and supports mark checked", async ({
  page,
}) => {
  await page.goto("/");

  await page.getByLabel("Travel month").selectOption("2");
  await page.getByRole("button", { name: "Search ski trips" }).click();

  await expect(page.getByTestId("result-details")).toBeVisible();
  await page.getByRole("button", { name: "Save as current trip" }).click();
  await expect(page.getByText("Saved")).toBeVisible();

  await page.getByRole("button", { name: "Current trip" }).click();
  await expect(
    page.getByRole("heading", { name: "Current conditions" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "What changed since last check" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Mark checked" }).click();
  await expect(page.getByText(/since last check/i)).toBeVisible();
});
