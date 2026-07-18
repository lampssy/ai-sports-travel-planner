export const APP_NAVIGATION_EVENT = "snowcast:navigate";

export type AppRoute =
  | { name: "search" }
  | { name: "currentTrip" }
  | { name: "dossier"; skiRegionId: string; candidateId: string | null };

export function parseAppRoute(location: Location): AppRoute {
  if (location.pathname === "/" || location.pathname === "") {
    return { name: "search" };
  }
  if (location.pathname === "/current-trip") {
    return { name: "currentTrip" };
  }

  const match = /^\/recommendations\/([^/]+)$/.exec(location.pathname);
  if (!match) {
    return { name: "search" };
  }

  try {
    const skiRegionId = decodeURIComponent(match[1]);
    if (!skiRegionId.trim()) {
      return { name: "search" };
    }
    const candidate = new URLSearchParams(location.search).get("candidate");
    return {
      name: "dossier",
      skiRegionId,
      candidateId: candidate?.trim() ? candidate : null,
    };
  } catch {
    return { name: "search" };
  }
}

export function buildDossierHref(
  regionId: string,
  candidateId: string,
): string {
  const query = new URLSearchParams({ candidate: candidateId });
  return `/recommendations/${encodeURIComponent(regionId)}?${query.toString()}`;
}

export function navigate(href: string): void {
  window.history.pushState(null, "", href);
  window.dispatchEvent(new Event(APP_NAVIGATION_EVENT));
}
