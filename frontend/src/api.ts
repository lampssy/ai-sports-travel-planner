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

const API_PREFIX = "/api";
const MOBILE_AUTH_REQUIRED_MESSAGE =
  "Current trip is available in the authenticated mobile app.";
const API_UNAVAILABLE_MESSAGE =
  "Snowcast is temporarily unavailable. Try again shortly.";
const REFINEMENT_CLIENT_DEADLINE_MS = 6_500;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly retryAfterSeconds: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function retryAfterSeconds(response: Response): number | null {
  const value = response.headers.get("Retry-After");
  if (!value || !/^[1-9]\d*$/.test(value)) return null;
  const seconds = Number(value);
  return Number.isSafeInteger(seconds) ? seconds : null;
}

interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
}

function validationIssueMessage(issue: ValidationIssue): string | null {
  if (!issue.msg) return null;
  const field = (issue.loc ?? [])
    .filter((part) => !["body", "intent", "constraints"].includes(String(part)))
    .map((part) => String(part).replaceAll("_", " "))
    .join(" ");
  if (!field) return issue.msg;
  return `${field.charAt(0).toUpperCase()}${field.slice(1)}: ${issue.msg}`;
}

async function errorMessageFromResponse(
  response: Response,
  fallback: string,
): Promise<string> {
  if (response.status >= 500) {
    return API_UNAVAILABLE_MESSAGE;
  }

  const payload = (await response.json().catch(() => null)) as
    | { detail?: string | ValidationIssue[] }
    | null;

  if (typeof payload?.detail === "string" && payload.detail) {
    return payload.detail;
  }
  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail
      .map(validationIssueMessage)
      .filter((message): message is string => Boolean(message));
    if (messages.length) return messages.join("; ");
  }

  return fallback;
}

function fetchFailureMessage(action: string): string {
  return `${action} Check your connection and try again.`;
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

export async function searchResorts(request: SearchV4Request): Promise<SearchResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ intent: searchIntentRequestPayload(request.intent) }),
    });
  } catch (error) {
    throw new Error(fetchFailureMessage("Unable to load resort results."));
  }

  if (!response.ok) {
    throw new ApiError(
      await errorMessageFromResponse(response, "Unable to load resort results."),
      response.status,
    );
  }

  return (await response.json()) as SearchResponse;
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
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      fetchFailureMessage("Unable to check for a refinement."),
      null,
    );
  } finally {
    globalThis.clearTimeout(deadlineTimer);
    signal?.removeEventListener("abort", abortFromCaller);
  }

  if (!response.ok) {
    throw new ApiError(
      await errorMessageFromResponse(
        response,
        "Unable to check for a refinement.",
      ),
      response.status,
      retryAfterSeconds(response),
    );
  }

  return (await response.json()) as SearchV4RefinementResponse;
}

export async function fetchSearchWeatherEvidence(
  request: SearchWeatherEvidenceRequest,
  signal?: AbortSignal,
): Promise<SearchWeatherEvidenceResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}/search/weather-evidence`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...request,
        intent: searchIntentRequestPayload(request.intent),
      }),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error(fetchFailureMessage("Unable to load snow evidence."));
  }

  if (!response.ok) {
    throw new Error(
      await errorMessageFromResponse(response, "Unable to load snow evidence."),
    );
  }

  return (await response.json()) as SearchWeatherEvidenceResponse;
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
    throw new Error(fetchFailureMessage("Unable to interpret trip brief."));
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
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}/current-trip`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    });
  } catch (error) {
    throw new Error(fetchFailureMessage("Unable to save current trip."));
  }

  if (response.status === 401) {
    throw new Error(MOBILE_AUTH_REQUIRED_MESSAGE);
  }

  if (!response.ok) {
    throw new Error(
      await errorMessageFromResponse(response, "Unable to save current trip."),
    );
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
