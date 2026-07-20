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
    evidence_profile: "archive_backed",
    access: {
      ski_area_access_id: "access-1",
      access_mode: "walk",
      lift_distance: "near",
      nearest_lift_name: "Toviere",
      distance_m: 250,
      duration_minutes: 4,
      is_direct: true,
      relationship_trust_status: "verified",
      access_mode_distance_trust_status: "verified",
    },
    selected_pass: {
      lift_pass_product_id: "pass-1",
      name: "Tignes pass",
      validity_scope: "single_ski_area",
      covered_ski_area_ids: ["tignes-ski-area"],
      accessible_piste_km: 150,
      accessible_piste_km_evidence: {
        trust_status: "verified",
        scope: "pass",
        source_entity_id: "pass-1",
        field_group: "pass_accessible_terrain",
      },
      price: null,
    },
    lodging_estimate: {
      mode: "lodging_nightly",
      minimum: 180,
      maximum: 255,
      currency: "EUR",
      trust_status: trustStatus,
      provenance: "Catalog lodging range; estimate-aware constraint only.",
    },
    ranking_status: "ranked",
    fit_score: 82,
    snow_assessment: {
      state: "not_assessed",
      reason: "not_assessed",
      forecast_status: "not_applicable",
    },
    groups: [],
    factors: [],
    constraint_warnings: [],
  };
}

test("keeps recommended stay-base guidance separate from destination-level search", () => {
  render(<AccommodationHandoff configuration={configuration()} />);

  expect(screen.getByText("Recommended place to stay")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Le Lac" })).toBeVisible();
  expect(
    screen.getByText(/Le Lac is planning guidance, not live hotel inventory/i),
  ).toBeVisible();
  expect(screen.getByText("EUR 180-255/night")).toBeVisible();
  expect(screen.getByText("Estimated from available data")).toBeVisible();
  expect(document.body.textContent).not.toMatch(
    /catalog lodging range|estimate-aware constraint/i,
  );
  expect(screen.getByText(/toviere.*250 m walk/i)).toBeVisible();
  const link = screen.getByRole("link", {
    name: "Search stays in Tignes on Booking.com",
  });
  expect(link).toHaveAttribute(
    "href",
    "/api/outbound/accommodation/tignes?stay_base_id=tignes-le-lac&focus_ski_area_id=tignes-ski-area&source_surface=recommendation_dossier",
  );
  expect(
    screen.getByText(
      "Booking.com searches Tignes, not the recommended place Le Lac.",
    ),
  ).toBeVisible();
  expect(document.body.textContent).not.toMatch(/hotel name|available rooms/i);
});

test.each([
  ["verified", "Based on source data"],
  ["verified_with_adjustment", "Estimated from source data for this trip"],
  ["estimated", "Estimated from available data"],
] as const)("presents %s lodging evidence in plain language", (status, label) => {
  render(<AccommodationHandoff configuration={configuration(status)} />);
  expect(screen.getByText(label)).toBeVisible();
  expect(document.body.textContent).not.toMatch(/verified with adjustment/i);
});

test("does not render a numeric lodging estimate when sourcing is required", () => {
  render(<AccommodationHandoff configuration={configuration("needs_source")} />);

  expect(screen.getByText("Source confirmation needed")).toBeVisible();
  expect(screen.getByText(/no supported lodging estimate is available/i)).toBeVisible();
  expect(screen.queryByText(/180|255/)).toBeNull();
  expect(document.body.textContent).not.toMatch(/needs source/i);
});

test("does not expose unverified lift-access details", () => {
  const candidate = configuration();
  render(
    <AccommodationHandoff
      configuration={{
        ...candidate,
        access: {
          ...candidate.access,
          relationship_trust_status: "verified",
          access_mode_distance_trust_status: "needs_source",
        },
      }}
    />,
  );

  expect(screen.queryByText(/toviere|250 m|walk/i)).toBeNull();
});
