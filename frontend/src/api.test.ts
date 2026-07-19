import { fetchSearchRefinements, fetchSearchWeatherEvidence, searchIntentRequestPayload, searchResorts } from "./api";
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
    });
    const rejection = expect(request).rejects.toMatchObject({
      name: "AbortError",
    });

    await vi.advanceTimersByTimeAsync(7_000);

    await rejection;
    expect(signalCapture.current?.aborted).toBe(true);
    vi.useRealTimers();
  });

  it("uses a clear action-focused message when results cannot be updated", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(searchResorts({ intent: responseShapedIntent })).rejects.toThrow(
      "Snowcast could not update these results. Check your connection and try again.",
    );
  });

  it("exposes a positive integer Retry-After delay for refinement admission limits", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Too many refinement requests." }), {
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
          new Response(JSON.stringify({ detail: "Too many requests." }), {
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
        }),
      ).rejects.toMatchObject({ retryAfterSeconds: null });
    },
  );
});
