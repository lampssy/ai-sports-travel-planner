export const PUBLIC_API_ERROR_CODES = [
  "invalid_request",
  "authentication_required",
  "session_expired",
  "sign_in_failed",
  "sign_in_unavailable",
  "search_request_invalid",
  "weather_area_not_found",
  "refinement_rate_limited",
  "trip_option_invalid",
  "current_trip_not_found",
  "trip_option_not_found",
  "not_found",
  "method_not_allowed",
  "request_failed",
] as const;

export type PublicApiErrorCode = (typeof PUBLIC_API_ERROR_CODES)[number];
export type ApiFailureKind = "response" | "transport" | "decode" | "aborted";
export type ApiOperation =
  | "search"
  | "searchUpdate"
  | "parseTripBrief"
  | "refinementDiscovery"
  | "refinementApply"
  | "weather"
  | "currentTripLoad"
  | "currentTripSave"
  | "currentTripEvents"
  | "currentTripSummary"
  | "currentTripClear"
  | "currentTripMarkChecked";

const publicErrorCodes = new Set<string>(PUBLIC_API_ERROR_CODES);

const FALLBACK_COPY: Record<ApiOperation, string> = {
  search: "Trip options could not be loaded. Try again.",
  searchUpdate:
    "Results could not be updated. Your current results are still available. Try again.",
  parseTripBrief: "Your trip brief could not be read. Try again.",
  refinementDiscovery:
    "Snowcast could not check for another useful question. Your results are unchanged.",
  refinementApply:
    "Results could not be updated. Your current results and answer are still available. Try again.",
  weather: "Snow and weather could not be loaded. Try again.",
  currentTripLoad: "Your current trip could not be loaded. Try again.",
  currentTripSave: "Your trip could not be saved. Try again.",
  currentTripEvents: "Trip updates could not be loaded. Try again.",
  currentTripSummary: "Current conditions could not be updated. Try again.",
  currentTripClear: "Your current trip could not be removed. Try again.",
  currentTripMarkChecked: "Your current trip could not be updated. Try again.",
};

const AUTH_REQUIRED_COPY =
  "Sign in to the Snowcast mobile app to use Current trip.";

const TRANSPORT_COPY: Partial<Record<ApiOperation, string>> = {
  search: "Trip options could not be loaded. Check your connection and try again.",
  parseTripBrief:
    "Your trip brief could not be read. Check your connection and try again.",
};

export class ApiError extends Error {
  readonly code: PublicApiErrorCode | null;
  readonly status: number | null;
  readonly retryAfterSeconds: number | null;
  readonly failureKind: ApiFailureKind;

  constructor({
    code = null,
    status = null,
    retryAfterSeconds = null,
    failureKind = "response",
    message = "Snowcast could not complete this request.",
  }: {
    code?: PublicApiErrorCode | null;
    status?: number | null;
    retryAfterSeconds?: number | null;
    failureKind?: ApiFailureKind;
    message?: string;
  }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
    this.failureKind = failureKind;
  }
}

function retryAfterSeconds(response: Response): number | null {
  const value = response.headers.get("Retry-After");
  if (!value || !/^[1-9]\d*$/.test(value)) return null;
  const seconds = Number(value);
  return Number.isSafeInteger(seconds) ? seconds : null;
}

function publicCode(payload: unknown): PublicApiErrorCode | null {
  if (!payload || typeof payload !== "object") return null;
  const error = (payload as { error?: unknown }).error;
  if (!error || typeof error !== "object") return null;
  const code = (error as { code?: unknown }).code;
  return typeof code === "string" && publicErrorCodes.has(code)
    ? (code as PublicApiErrorCode)
    : null;
}

export async function publicApiErrorFromResponse(
  response: Response,
): Promise<ApiError> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // Public copy never depends on an untrusted response body.
  }
  return new ApiError({
    code: publicCode(payload),
    status: response.status,
    retryAfterSeconds: retryAfterSeconds(response),
  });
}

export function apiErrorMessage(
  operation: ApiOperation,
  caught: unknown,
): string {
  const error = caught instanceof ApiError ? caught : null;
  const code = error?.code;

  if (code === "authentication_required" || code === "session_expired") {
    return AUTH_REQUIRED_COPY;
  }
  if (code === "trip_option_invalid") {
    return "Snowcast could not save this trip option. Return to the results and choose it again.";
  }
  if (code === "current_trip_not_found") {
    return "No current trip is saved.";
  }
  if (operation === "weather" && code === "weather_area_not_found") {
    return "Snow and weather are not available for this ski area.";
  }
  if (
    (operation === "search" || operation === "parseTripBrief") &&
    (code === "invalid_request" || code === "search_request_invalid")
  ) {
    return operation === "search"
      ? "Review your trip choices and try again."
      : "Your trip brief could not be read. Review it and try again.";
  }
  if (operation === "refinementDiscovery" && code === "refinement_rate_limited") {
    return "Snowcast needs a little more time before checking for another useful question.";
  }
  if (operation === "search" && code === "request_failed") {
    return "Snowcast is temporarily unavailable. Try again shortly.";
  }
  if (error?.failureKind === "transport" && TRANSPORT_COPY[operation]) {
    return TRANSPORT_COPY[operation];
  }

  return FALLBACK_COPY[operation];
}

export async function apiErrorForResponse(
  response: Response,
  operation: ApiOperation,
): Promise<ApiError> {
  const parsed = await publicApiErrorFromResponse(response);
  return new ApiError({
    code: parsed.code,
    status: parsed.status,
    retryAfterSeconds: parsed.retryAfterSeconds,
    failureKind: parsed.failureKind,
    message: apiErrorMessage(operation, parsed),
  });
}

export function apiErrorForCause(
  caught: unknown,
  operation: ApiOperation,
): ApiError {
  const aborted =
    typeof caught === "object" &&
    caught !== null &&
    "name" in caught &&
    caught.name === "AbortError";
  const failureKind = aborted ? "aborted" : "transport";
  return new ApiError({
    failureKind,
    message: apiErrorMessage(operation, new ApiError({ failureKind })),
  });
}

export async function decodeApiJson<T>(
  response: Response,
  operation: ApiOperation,
): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    const error = new ApiError({
      status: response.status,
      failureKind: "decode",
    });
    throw new ApiError({
      status: response.status,
      failureKind: "decode",
      message: apiErrorMessage(operation, error),
    });
  }
}
