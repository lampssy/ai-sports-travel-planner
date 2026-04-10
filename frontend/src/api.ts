import type {
  ParsedQueryResponse,
  SearchFilters,
  SearchResponse,
} from "./types";

const API_PREFIX = "/api";

export async function searchResorts(
  filters: SearchFilters,
): Promise<SearchResponse> {
  const query = new URLSearchParams({
    location: filters.location,
    min_price: filters.minPrice,
    max_price: filters.maxPrice,
    stars: filters.stars,
    skill_level: filters.skillLevel,
  });

  if (filters.liftDistance) {
    query.set("lift_distance", filters.liftDistance);
  }

  if (filters.budgetFlex) {
    query.set("budget_flex", filters.budgetFlex);
  }

  if (filters.travelMonth) {
    query.set("travel_month", String(filters.travelMonth));
  }

  const response = await fetch(`${API_PREFIX}/search?${query.toString()}`);

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to load resort results.");
  }

  return (await response.json()) as SearchResponse;
}

export async function parseTripBrief(
  query: string,
): Promise<ParsedQueryResponse> {
  const response = await fetch(`${API_PREFIX}/parse-query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to interpret trip brief.");
  }

  return (await response.json()) as ParsedQueryResponse;
}

export function buildAccommodationBookingRedirectUrl(
  result: {
    resort_id: string;
    selected_area_name: string;
    link: string;
  },
  sourceSurface: string,
): string {
  const query = new URLSearchParams({
    selected_area_name: result.selected_area_name,
    source_surface: sourceSurface,
  });
  return `${API_PREFIX}/outbound/accommodation/${encodeURIComponent(
    result.resort_id,
  )}?${query.toString()}`;
}
