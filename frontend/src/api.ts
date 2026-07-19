import type {
  BookingStatus,
  CompanionEvent,
  CurrentTrip,
  CurrentTripSummary,
  CurrentTripResponse,
  ParsedQueryResponse,
  SearchResponse,
  SearchIntent,
  SearchWeatherEvidenceRequest,
  SearchWeatherEvidenceResponse,
  SearchV4RefinementRequest,
  SearchV4RefinementResponse,
  SearchV4Request,
} from "./types";
import {
  ApiError,
  apiErrorForCause,
  apiErrorForResponse,
  decodeApiJson,
  type ApiOperation,
} from "./apiErrors";

export { ApiError } from "./apiErrors";

const API_PREFIX = "/api";
const REFINEMENT_CLIENT_DEADLINE_MS = 6_500;

async function fetchForOperation(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  operation: ApiOperation,
): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (caught) {
    throw apiErrorForCause(caught, operation);
  }
}

async function checkedJson<T>(
  response: Response,
  operation: ApiOperation,
): Promise<T> {
  if (!response.ok) throw await apiErrorForResponse(response, operation);
  return decodeApiJson<T>(response, operation);
}

type ResponseTravelWindow = NonNullable<
  SearchIntent["constraints"]["travel_window"]
> & {
  mode?: unknown;
  ski_day_count?: unknown;
};

type ResponseLodgingBudget = NonNullable<
  SearchIntent["constraints"]["lodging_budget"]
> & {
  effective_flex?: unknown;
  effective_maximum?: unknown;
};

export function searchIntentRequestPayload(intent: SearchIntent): SearchIntent {
  const constraints = { ...intent.constraints };

  if (constraints.travel_window) {
    const { mode: _mode, ski_day_count: _skiDayCount, ...travelWindow } =
      constraints.travel_window as ResponseTravelWindow;
    constraints.travel_window = Object.fromEntries(
      Object.entries(travelWindow).filter(([, value]) => value != null),
    );
  }

  if (constraints.lodging_budget) {
    const {
      effective_flex: _effectiveFlex,
      effective_maximum: _effectiveMaximum,
      ...lodgingBudget
    } = constraints.lodging_budget as ResponseLodgingBudget;
    constraints.lodging_budget = lodgingBudget;
  }

  return { ...intent, constraints };
}

export async function searchResorts(
  request: SearchV4Request,
  operation: "search" | "searchUpdate" | "refinementApply" = "search",
): Promise<SearchResponse> {
  const response = await fetchForOperation(
    `${API_PREFIX}/search`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ intent: searchIntentRequestPayload(request.intent) }),
    },
    operation,
  );
  return checkedJson<SearchResponse>(response, operation);
}

export async function fetchSearchRefinements(
  request: SearchV4RefinementRequest,
  signal?: AbortSignal,
): Promise<SearchV4RefinementResponse> {
  const transportController = new AbortController();
  const abortFromCaller = () => transportController.abort();
  if (signal?.aborted) {
    transportController.abort();
  } else {
    signal?.addEventListener("abort", abortFromCaller, { once: true });
  }
  const deadlineTimer = globalThis.setTimeout(
    () => transportController.abort(),
    REFINEMENT_CLIENT_DEADLINE_MS,
  );
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}/search/refinements`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...request,
        intent: searchIntentRequestPayload(request.intent),
      }),
      signal: transportController.signal,
    });
  } catch (error) {
    throw apiErrorForCause(error, "refinementDiscovery");
  } finally {
    globalThis.clearTimeout(deadlineTimer);
    signal?.removeEventListener("abort", abortFromCaller);
  }

  if (!response.ok) {
    throw await apiErrorForResponse(response, "refinementDiscovery");
  }
  return decodeApiJson<SearchV4RefinementResponse>(
    response,
    "refinementDiscovery",
  );
}

export async function fetchSearchWeatherEvidence(
  request: SearchWeatherEvidenceRequest,
  signal?: AbortSignal,
): Promise<SearchWeatherEvidenceResponse> {
  const response = await fetchForOperation(
    `${API_PREFIX}/search/weather-evidence`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...request,
        intent: searchIntentRequestPayload(request.intent),
      }),
      signal,
    },
    "weather",
  );
  return checkedJson<SearchWeatherEvidenceResponse>(response, "weather");
}

export async function parseTripBrief(
  query: string,
): Promise<ParsedQueryResponse> {
  const response = await fetchForOperation(
    `${API_PREFIX}/parse-query`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    },
    "parseTripBrief",
  );
  return checkedJson<ParsedQueryResponse>(response, "parseTripBrief");
}

export async function getCurrentTrip(): Promise<CurrentTrip | null> {
  const response = await fetchForOperation(
    `${API_PREFIX}/current-trip`,
    undefined,
    "currentTripLoad",
  );
  const payload = await checkedJson<CurrentTripResponse>(
    response,
    "currentTripLoad",
  );
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
  const response = await fetchForOperation(
    `${API_PREFIX}/current-trip`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
    "currentTripSave",
  );
  return checkedJson<CurrentTrip>(response, "currentTripSave");
}

export async function getCurrentTripEvents(): Promise<CompanionEvent[]> {
  const response = await fetchForOperation(
    `${API_PREFIX}/current-trip/events`,
    undefined,
    "currentTripEvents",
  );
  const payload = await checkedJson<{ events: CompanionEvent[] }>(
    response,
    "currentTripEvents",
  );
  return payload.events;
}

export async function clearCurrentTrip(): Promise<void> {
  const response = await fetchForOperation(
    `${API_PREFIX}/current-trip`,
    {
      method: "DELETE",
    },
    "currentTripClear",
  );
  if (!response.ok) throw await apiErrorForResponse(response, "currentTripClear");
}

export async function getCurrentTripSummary(): Promise<CurrentTripSummary | null> {
  const response = await fetchForOperation(
    `${API_PREFIX}/current-trip/summary`,
    undefined,
    "currentTripSummary",
  );
  if (!response.ok) {
    const error = await apiErrorForResponse(response, "currentTripSummary");
    if (error.code === "current_trip_not_found") return null;
    throw error;
  }
  return decodeApiJson<CurrentTripSummary>(response, "currentTripSummary");
}

export async function markCurrentTripChecked(): Promise<CurrentTrip> {
  const response = await fetchForOperation(
    `${API_PREFIX}/current-trip/mark-checked`,
    {
      method: "POST",
    },
    "currentTripMarkChecked",
  );
  return checkedJson<CurrentTrip>(response, "currentTripMarkChecked");
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
