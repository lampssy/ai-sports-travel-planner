import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import type { SearchV4Configuration } from "../types";
import { AccommodationHandoff } from "./AccommodationHandoff";

function configuration(
  trustStatus: NonNullable<SearchV4Configuration["lodging_estimate"]>["trust_status"] = "estimated",
): SearchV4Configuration {
  return {
    candidate_id: "candidate-1",
    ski_region_id: "tignes-val-disere",
    ski_region_name: "Tignes - Val d'Isere",
    stay_destination_id: "tignes",
    stay_destination_name: "Tignes",
    stay_base_id: "tignes-le-lac",
    stay_base_name: "Le Lac",
    ski_area_id: "tignes-ski-area",
    ski_area_name: "Tignes",
    access: {
      ski_area_access_id: "access-1",
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: "Toviere",
      distance_m: 250,
      duration_minutes: 4,
      is_direct: true,
    },
    selected_pass: {
      lift_pass_product_id: "pass-1",
      name: "Tignes pass",
      validity_scope: "single_ski_area",
      covered_ski_area_ids: ["tignes-ski-area"],
      accessible_piste_km: 150,
      price: null,
    },
    lodging_estimate: {
      mode: "lodging_nightly",
      minimum: 180,
      maximum: 255,
      currency: "EUR",
      trust_status: trustStatus,
      provenance: "Catalog stay-base estimate.",
    },
    ranking_status: "ranked",
    fit_score: 82,
    groups: [],
    factors: [],
    constraint_warnings: [],
  };
}

test("renders an honest stay-base estimate and selected-base handoff URL", () => {
  render(<AccommodationHandoff configuration={configuration()} />);

  expect(screen.getByText("Stay-base estimate, not live hotel inventory")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Find a stay in Le Lac" })).toBeVisible();
  expect(screen.getByText("EUR 180-255/night")).toBeVisible();
  expect(screen.getByText("Estimated")).toBeVisible();
  expect(screen.getByText(/toviere.*250 m walk/i)).toBeVisible();
  const link = screen.getByRole("link", { name: "Open accommodation search" });
  expect(link).toHaveAttribute(
    "href",
    "/api/outbound/accommodation/tignes?stay_base_id=tignes-le-lac&focus_ski_area_id=tignes-ski-area&source_surface=recommendation_dossier",
  );
  expect(document.body.textContent).not.toMatch(/hotel name|available rooms|booking\.com/i);
});

test.each([
  ["verified", "Verified"],
  ["verified_with_adjustment", "Verified with adjustment"],
  ["estimated", "Estimated"],
] as const)("preserves %s trust wording", (status, label) => {
  render(<AccommodationHandoff configuration={configuration(status)} />);
  expect(screen.getByText(label)).toBeVisible();
});

test("does not render a numeric lodging estimate when sourcing is required", () => {
  render(<AccommodationHandoff configuration={configuration("needs_source")} />);

  expect(screen.getByText("Needs source")).toBeVisible();
  expect(screen.getByText(/no supported lodging estimate is available/i)).toBeVisible();
  expect(screen.queryByText(/180|255/)).toBeNull();
});
