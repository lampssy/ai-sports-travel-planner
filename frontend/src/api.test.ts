import {
  clearCurrentTrip,
  fetchSearchRefinements,
  fetchSearchWeatherEvidence,
  getCurrentTrip,
  getCurrentTripEvents,
  getCurrentTripSummary,
  markCurrentTripChecked,
  parseTripBrief,
  saveCurrentTrip,
  searchIntentRequestPayload,
  searchResorts,
} from "./api";
import {
  ApiError,
  apiErrorMessage,
  publicApiErrorFromResponse,
  type ApiOperation,
} from "./apiErrors";
import type { SearchIntent } from "./types";

const responseShapedIntent = {
  constraints: {
    location: { country: "France" },
    travel_window: {
      month: 3,
      mode: "month",
      ski_day_count: null,
    },
    lodging_budget: {
      mode: "lodging_nightly",
      maximum: 320,
      currency: "EUR",
      budget_flex: 0,
      effective_flex: 0.1,
      effective_maximum: 352,
    },
  },
  party: { skill_levels: ["intermediate"] },
  travel_context: {},
  objectives: [],
  group_priorities: [],
  factor_preferences: [],
  assumptions: [],
} as unknown as SearchIntent;

describe("Search API request projection", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({}), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  });

  afterEach(() => vi.unstubAllGlobals());

  it("strips response-only computed fields without mutating the source", () => {
    const projected = searchIntentRequestPayload(responseShapedIntent);

    expect(projected.constraints.travel_window).toEqual({ month: 3 });
    expect(projected.constraints.lodging_budget).toEqual({
      mode: "lodging_nightly",
      maximum: 320,
      currency: "EUR",
      budget_flex: 0,
    });
    expect(responseShapedIntent.constraints.travel_window).toHaveProperty("mode");
    expect(responseShapedIntent.constraints.lodging_budget).toHaveProperty(
      "effective_maximum",
    );
  });

  it.each([
    ["ranking", () => searchResorts({ intent: responseShapedIntent })],
    [
      "refinement",
      () =>
        fetchSearchRefinements({
          intent: responseShapedIntent,
          brief: "March in France",
          baseline_fingerprint: "a".repeat(64),
          already_answered_question_ids: [],
          resolved_topic_ids: [],
        }),
    ],
    [
      "weather evidence",
      () =>
        fetchSearchWeatherEvidence({
          intent: responseShapedIntent,
          ski_area_id: "tignes-ski-area",
        }),
    ],
  ])("sends a request-shaped intent for %s", async (_label, request) => {
    await request();

    const init = vi.mocked(fetch).mock.calls[0][1];
    const body = JSON.parse(String(init?.body));
    expect(body.intent.constraints.travel_window).toEqual({ month: 3 });
    expect(body.intent.constraints.lodging_budget).not.toHaveProperty(
      "effective_maximum",
    );
  });

  it("aborts refinement transport after the client deadline", async () => {
    vi.useFakeTimers();
    const signalCapture: { current: AbortSignal | null } = { current: null };
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) => {
        signalCapture.current = init?.signal ?? null;
        return new Promise<Response>((_resolve, reject) => {
          signalCapture.current?.addEventListener("abort", () => {
            reject(new DOMException("The operation was aborted.", "AbortError"));
          });
        });
      }),
    );

    const request = fetchSearchRefinements({
      intent: responseShapedIntent,
      brief: "March in France",
      baseline_fingerprint: "a".repeat(64),
      already_answered_question_ids: [],
      resolved_topic_ids: [],
    });
    const rejection = expect(request).rejects.toMatchObject({
      name: "ApiError",
      failureKind: "aborted",
    });

    await vi.advanceTimersByTimeAsync(7_000);

    await rejection;
    expect(signalCapture.current?.aborted).toBe(true);
    vi.useRealTimers();
  });

  it.each([
    [
      "resort results",
      () => searchResorts({ intent: responseShapedIntent }),
      "Trip options could not be loaded. Check your connection and try again.",
    ],
    [
      "a refinement",
      () =>
        fetchSearchRefinements({
          intent: responseShapedIntent,
          brief: "March in France",
          baseline_fingerprint: "a".repeat(64),
          already_answered_question_ids: [],
          resolved_topic_ids: [],
        }),
      "Snowcast could not check for another useful question. Your results are unchanged.",
    ],
    [
      "snow evidence",
      () =>
        fetchSearchWeatherEvidence({
          intent: responseShapedIntent,
          ski_area_id: "tignes-ski-area",
        }),
      "Snow and weather could not be loaded. Try again.",
    ],
    [
      "trip brief",
      () => parseTripBrief("March in France"),
      "Your trip brief could not be read. Check your connection and try again.",
    ],
    [
      "current trip",
      () =>
        saveCurrentTrip({
          ski_region_id: "tignes",
          ski_region_name: "Tignes",
          stay_destination_id: "tignes",
          stay_destination_name: "Tignes",
          stay_base_id: "tignes-le-lac",
          stay_base_name: "Tignes le Lac",
          focus_ski_area_id: "tignes-ski-area",
          focus_ski_area_name: "Tignes",
          lift_pass_product_id: "tignes-pass",
          lift_pass_product_name: "Tignes Pass",
          travel_month: 3,
          booking_status: "not_booked_yet",
        }),
      "Your trip could not be saved. Try again.",
    ],
    [
      "saved current trip",
      () => getCurrentTrip(),
      "Your current trip could not be loaded. Try again.",
    ],
    [
      "current trip activity",
      () => getCurrentTripEvents(),
      "Current trip activity could not be loaded. Try again.",
    ],
    [
      "current trip removal",
      () => clearCurrentTrip(),
      "Your current trip could not be removed. Try again.",
    ],
    [
      "current trip summary",
      () => getCurrentTripSummary(),
      "Current conditions could not be updated. Try again.",
    ],
    [
      "current trip check",
      () => markCurrentTripChecked(),
      "Your current trip could not be updated. Try again.",
    ],
  ])("uses an action-scoped fetch failure for %s", async (_action, request, message) => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(request()).rejects.toThrow(message);
  });

  it("exposes a positive integer Retry-After delay for refinement admission limits", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: "refinement_rate_limited" } }), {
          status: 429,
          headers: { "Retry-After": "10" },
        }),
      ),
    );

    await expect(
      fetchSearchRefinements({
        intent: responseShapedIntent,
        brief: "March in France",
        baseline_fingerprint: "a".repeat(64),
        already_answered_question_ids: [],
        resolved_topic_ids: [],
      }),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 429,
      retryAfterSeconds: 10,
    });
  });

  it.each([undefined, "0", "-1", "1.5", "soon"])(
    "rejects invalid Retry-After metadata (%s)",
    async (retryAfter) => {
      const headers = new Headers();
      if (retryAfter !== undefined) headers.set("Retry-After", retryAfter);
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(
          new Response(JSON.stringify({ error: { code: "refinement_rate_limited" } }), {
            status: 429,
            headers,
          }),
        ),
      );

      await expect(
        fetchSearchRefinements({
          intent: responseShapedIntent,
          brief: "March in France",
          baseline_fingerprint: "a".repeat(64),
          already_answered_question_ids: [],
          resolved_topic_ids: [],
        }),
      ).rejects.toMatchObject({ retryAfterSeconds: null });
    },
  );
});

describe("public API error boundary", () => {
  it("parses a known stable code and ignores every other response field", async () => {
    const error = await publicApiErrorFromResponse(
      new Response(
        JSON.stringify({
          error: { code: "search_request_invalid" },
          detail: "internal validation path",
          token: "secret",
        }),
        { status: 422 },
      ),
    );

    expect(error).toMatchObject({
      name: "ApiError",
      code: "search_request_invalid",
      status: 422,
    });
    expect(error.message).not.toMatch(/internal|validation|secret/i);
  });

  it.each([
    [JSON.stringify({ error: { code: "future_code" } }), "unknown code"],
    [JSON.stringify({ error: {} }), "missing code"],
    [JSON.stringify({ detail: "backend detail" }), "legacy detail"],
    ["not json", "non-JSON body"],
  ])("uses a bounded fallback for a %s envelope", async (body) => {
    const error = await publicApiErrorFromResponse(
      new Response(body, { status: 500 }),
    );

    expect(error).toMatchObject({ code: null, status: 500 });
    expect(apiErrorMessage("searchUpdate", error)).toBe(
      "Results could not be updated. Your current results are still available. Try again.",
    );
    expect(error.message).not.toContain("backend detail");
  });

  it.each([
    ["12", 12],
    [null, null],
    ["0", null],
    ["-1", null],
    ["1.5", null],
    ["soon", null],
  ])("accepts only a positive integer Retry-After value (%s)", async (value, expected) => {
    const headers = new Headers();
    if (value !== null) headers.set("Retry-After", value);
    const error = await publicApiErrorFromResponse(
      new Response(
        JSON.stringify({ error: { code: "refinement_rate_limited" } }),
        { status: 429, headers },
      ),
    );

    expect(error.retryAfterSeconds).toBe(expected);
  });

  it.each<[ApiOperation, string]>([
    ["search", "Trip options could not be loaded. Check your connection and try again."],
    ["searchUpdate", "Results could not be updated. Your current results are still available. Try again."],
    ["refinementDiscovery", "Snowcast could not check for another useful question. Your results are unchanged."],
    ["refinementApply", "Results could not be updated. Your current results and answer are still available. Try again."],
    ["weather", "Snow and weather could not be loaded. Try again."],
    ["currentTripLoad", "Your current trip could not be loaded. Try again."],
    ["currentTripSave", "Your trip could not be saved. Try again."],
    ["currentTripSummary", "Current conditions could not be updated. Try again."],
    ["currentTripClear", "Your current trip could not be removed. Try again."],
  ])("owns safe fallback copy for %s", (operation, expected) => {
    expect(apiErrorMessage(operation, new Error("raw transport failure"))).toBe(
      expected,
    );
  });

  it("maps operation-specific stable codes without displaying backend text", async () => {
    const invalidSearch = new ApiError({
      code: "search_request_invalid",
      status: 422,
    });
    const missingWeather = new ApiError({
      code: "weather_area_not_found",
      status: 422,
    });
    const invalidTrip = new ApiError({
      code: "trip_option_invalid",
      status: 422,
    });

    expect(apiErrorMessage("search", invalidSearch)).toBe(
      "Review your trip choices and try again.",
    );
    expect(apiErrorMessage("weather", missingWeather)).toBe(
      "Snow and weather are not available for this ski area.",
    );
    expect(apiErrorMessage("currentTripSave", invalidTrip)).toBe(
      "This trip option is no longer available. Return to the results and choose it again.",
    );
  });

  it("recognizes the complete public code registry", async () => {
    const knownCodes = [
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

    for (const code of knownCodes) {
      const error = await publicApiErrorFromResponse(
        new Response(JSON.stringify({ error: { code } }), { status: 500 }),
      );
      expect(error.code).toBe(code);
    }
  });

  it.each<[
    ApiOperation,
    ConstructorParameters<typeof ApiError>[0]["code"],
    string,
  ]>([
    ["search", "invalid_request", "Review your trip choices and try again."],
    ["search", "search_request_invalid", "Review your trip choices and try again."],
    ["search", "request_failed", "Snowcast is temporarily unavailable. Try again shortly."],
    ["refinementDiscovery", "refinement_rate_limited", "Snowcast needs a little more time before checking for another useful question."],
    ["weather", "weather_area_not_found", "Snow and weather are not available for this ski area."],
    ["currentTripLoad", "authentication_required", "Current trip is available in the authenticated mobile app."],
    ["currentTripLoad", "session_expired", "Current trip is available in the authenticated mobile app."],
    ["currentTripSave", "trip_option_invalid", "This trip option is no longer available. Return to the results and choose it again."],
    ["currentTripSummary", "current_trip_not_found", "No current trip is saved."],
  ])("maps %s / %s to client-owned copy", (operation, code, expected) => {
    expect(apiErrorMessage(operation, new ApiError({ code }))).toBe(expected);
  });

  it("turns malformed success JSON into a safe decode failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not json", { status: 200 })),
    );

    await expect(searchResorts({ intent: responseShapedIntent })).rejects.toMatchObject({
      name: "ApiError",
      code: null,
      status: 200,
      failureKind: "decode",
    });
  });

  it("never renders a legacy backend detail through an API operation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "private backend detail" }), {
          status: 422,
        }),
      ),
    );

    const request = searchResorts({ intent: responseShapedIntent });
    await expect(request).rejects.toThrow(
      "Trip options could not be loaded. Check your connection and try again.",
    );
  });
});
