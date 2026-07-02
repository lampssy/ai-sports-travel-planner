import type {
  BookingStatus,
  CompanionEvent,
  CurrentTrip,
  CurrentTripSummary,
  CurrentTripResponse,
  ParsedQueryResponse,
  SearchFilters,
  SearchResponse,
} from "./types";

const API_PREFIX = "/api";
const MOBILE_AUTH_REQUIRED_MESSAGE =
  "Current trip is available in the authenticated mobile app.";
const API_UNREACHABLE_MESSAGE =
  "Backend API is not reachable. The service may be starting or temporarily unavailable.";

async function errorMessageFromResponse(
  response: Response,
  fallback: string,
): Promise<string> {
  const payload = (await response.json().catch(() => null)) as
    | { detail?: string }
    | null;

  if (payload?.detail) {
    return payload.detail;
  }

  if (response.status >= 500) {
    return API_UNREACHABLE_MESSAGE;
  }

  return fallback;
}

function errorMessageFromFetchFailure(
  error: unknown,
  fallback: string,
): string {
  if (error instanceof TypeError) {
    return API_UNREACHABLE_MESSAGE;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

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
  if (filters.originText.trim()) {
    query.set("origin_text", filters.originText.trim());
  }
  const maxDriveHours = Number(filters.maxDriveHours);
  if (filters.maxDriveHours.trim() && Number.isFinite(maxDriveHours) && maxDriveHours > 0) {
    query.set(
      "max_drive_minutes",
      String(Math.round(maxDriveHours * 60)),
    );
  }
  if (filters.travelTolerance) {
    query.set("travel_tolerance", filters.travelTolerance);
  }

  if (filters.travelWindowMode === "month" && filters.travelMonth) {
    query.set("travel_month", String(filters.travelMonth));
  }
  if (
    filters.travelWindowMode === "dates" &&
    filters.tripStartDate &&
    filters.tripEndDate
  ) {
    query.set("trip_start_date", filters.tripStartDate);
    query.set("trip_end_date", filters.tripEndDate);
  }

  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}/search?${query.toString()}`);
  } catch (error) {
    throw new Error(
      errorMessageFromFetchFailure(error, "Unable to load resort results."),
    );
  }

  if (!response.ok) {
    throw new Error(
      await errorMessageFromResponse(response, "Unable to load resort results."),
    );
  }

  return (await response.json()) as SearchResponse;
}

export async function parseTripBrief(
  query: string,
): Promise<ParsedQueryResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}/parse-query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });
  } catch (error) {
    throw new Error(
      errorMessageFromFetchFailure(error, "Unable to interpret trip brief."),
    );
  }

  if (!response.ok) {
    throw new Error(
      await errorMessageFromResponse(response, "Unable to interpret trip brief."),
    );
  }

  return (await response.json()) as ParsedQueryResponse;
}

export async function getCurrentTrip(): Promise<CurrentTrip | null> {
  const response = await fetch(`${API_PREFIX}/current-trip`);

  if (response.status === 401) {
    return null;
  }

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
  ski_region_id: string;
  ski_region_name: string;
  stay_destination_id: string;
  stay_destination_name: string;
  stay_base_id: string;
  stay_base_name: string;
  focus_ski_area_id: string;
  focus_ski_area_name: string;
  lift_pass_product_id: string;
  lift_pass_product_name: string;
  travel_month: number | null;
  trip_start_date?: string | null;
  trip_end_date?: string | null;
  booking_status: BookingStatus;
}): Promise<CurrentTrip> {
  const response = await fetch(`${API_PREFIX}/current-trip`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (response.status === 401) {
    throw new Error(MOBILE_AUTH_REQUIRED_MESSAGE);
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to save current trip.");
  }

  return (await response.json()) as CurrentTrip;
}

export async function getCurrentTripEvents(): Promise<CompanionEvent[]> {
  const response = await fetch(`${API_PREFIX}/current-trip/events`);

  if (response.status === 401 || response.status === 404) {
    return [];
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to load current trip events.");
  }

  const payload = (await response.json()) as { events: CompanionEvent[] };
  return payload.events;
}

export async function clearCurrentTrip(): Promise<void> {
  const response = await fetch(`${API_PREFIX}/current-trip`, {
    method: "DELETE",
  });

  if (response.status === 401) {
    throw new Error(MOBILE_AUTH_REQUIRED_MESSAGE);
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? "Unable to clear current trip.");
  }
}

export async function getCurrentTripSummary(): Promise<CurrentTripSummary | null> {
  const response = await fetch(`${API_PREFIX}/current-trip/summary`);

  if (response.status === 401 || response.status === 404) {
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

  if (response.status === 401) {
    throw new Error(MOBILE_AUTH_REQUIRED_MESSAGE);
  }

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
    stay_destination_id: string;
    stay_base_id: string;
    focus_ski_area_id: string;
  },
  sourceSurface: string,
): string {
  const query = new URLSearchParams({
    stay_base_id: result.stay_base_id,
    focus_ski_area_id: result.focus_ski_area_id,
    source_surface: sourceSurface,
  });
  return `${API_PREFIX}/outbound/accommodation/${encodeURIComponent(
    result.stay_destination_id,
  )}?${query.toString()}`;
}
