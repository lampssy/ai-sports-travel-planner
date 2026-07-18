import { afterEach, expect, test, vi } from "vitest";

import {
  APP_NAVIGATION_EVENT,
  buildDossierHref,
  navigate,
  parseAppRoute,
} from "./navigation";

function locationFor(href: string): Location {
  return new URL(href, "https://snowcast.test") as unknown as Location;
}

afterEach(() => {
  vi.restoreAllMocks();
});

test.each([
  ["/", { name: "search" }],
  ["/current-trip", { name: "currentTrip" }],
  [
    "/recommendations/region-a?candidate=candidate-a",
    { name: "dossier", skiRegionId: "region-a", candidateId: "candidate-a" },
  ],
  [
    "/recommendations/region-a",
    { name: "dossier", skiRegionId: "region-a", candidateId: null },
  ],
])("parses %s", (href, expected) => {
  expect(parseAppRoute(locationFor(href))).toEqual(expected);
});

test.each([
  "/recommendations/",
  "/recommendations/region-a/extra",
  "/recommendations/%E0%A4%A",
  "/not-a-route",
])("recovers invalid dossier route %s to search", (href) => {
  expect(parseAppRoute(locationFor(href))).toEqual({ name: "search" });
});

test("builds an encoded dossier href", () => {
  expect(buildDossierHref("region/a", "candidate a")).toBe(
    "/recommendations/region%2Fa?candidate=candidate+a",
  );
});

test("navigates through browser history and dispatches one local event", () => {
  const pushState = vi.spyOn(window.history, "pushState");
  const listener = vi.fn();
  window.addEventListener(APP_NAVIGATION_EVENT, listener);

  navigate("/current-trip");

  expect(pushState).toHaveBeenCalledOnce();
  expect(pushState).toHaveBeenCalledWith(null, "", "/current-trip");
  expect(listener).toHaveBeenCalledOnce();
  window.removeEventListener(APP_NAVIGATION_EVENT, listener);
});
