import type { SearchFilters, SearchResponse } from "./types";

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

  const response = await fetch(`${API_PREFIX}/search?${query.toString()}`);

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to load resort results.");
  }

  return (await response.json()) as SearchResponse;
}
