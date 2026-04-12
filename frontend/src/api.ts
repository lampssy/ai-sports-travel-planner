import type {
  BookingStatus,
  CurrentTrip,
  CurrentTripSummary,
  CurrentTripResponse,
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

export async function getCurrentTrip(): Promise<CurrentTrip | null> {
  const response = await fetch(`${API_PREFIX}/current-trip`);

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to load current trip.");
  }

  const payload = (await response.json()) as CurrentTripResponse;
  return payload.trip;
}

export async function saveCurrentTrip(input: {
  resort_id: string;
  selected_area_name: string;
  travel_month: number | null;
  booking_status: BookingStatus;
}): Promise<CurrentTrip> {
  const response = await fetch(`${API_PREFIX}/current-trip`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to save current trip.");
  }

  return (await response.json()) as CurrentTrip;
}

export async function clearCurrentTrip(): Promise<void> {
  const response = await fetch(`${API_PREFIX}/current-trip`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to clear current trip.");
  }
}

export async function getCurrentTripSummary(): Promise<CurrentTripSummary | null> {
  const response = await fetch(`${API_PREFIX}/current-trip/summary`);

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to load current trip summary.");
  }

  return (await response.json()) as CurrentTripSummary;
}

export async function markCurrentTripChecked(): Promise<CurrentTrip> {
  const response = await fetch(`${API_PREFIX}/current-trip/mark-checked`, {
    method: "POST",
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to mark current trip as checked.");
  }

  return (await response.json()) as CurrentTrip;
}

export function buildAccommodationBookingRedirectUrl(
  result: {
    resort_id: string;
    selected_area_name: string;
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
