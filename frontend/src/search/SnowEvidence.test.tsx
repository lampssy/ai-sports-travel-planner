import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import type {
  SearchIntent,
  SearchWeatherEvidenceResponse,
  WeatherEvidencePoint,
} from "../types";
import { SnowEvidence } from "./SnowEvidence";
import {
  clearWeatherEvidenceCache,
  readWeatherEvidenceCache,
  weatherEvidenceCacheKey,
} from "./weatherEvidenceCache";

const monthIntent: SearchIntent = {
  constraints: { travel_window: { month: 3 } },
  party: { skill_levels: ["intermediate"] },
  travel_context: {},
  objectives: [],
  group_priorities: [],
  factor_preferences: [],
  assumptions: [],
};

const datesIntent: SearchIntent = {
  ...monthIntent,
  constraints: {
    travel_window: { start_date: "2026-07-20", end_date: "2026-07-22" },
  },
};

const historicalPoint: WeatherEvidencePoint = {
  date_or_month_day: "03-15",
  snow_depth_cm: null,
  snow_depth_cm_p25: 82,
  snow_depth_cm_p50: 128,
  snow_depth_cm_p75: 176,
  snowfall_cm: 4.2,
  temperature_min_c: -8,
  temperature_max_c: -2.1,
  rain_risk: null,
  thaw_risk: 0.18,
  wind_gust_kmh: null,
};

function historicalResponse(
  updates: Partial<Extract<SearchWeatherEvidenceResponse, { status: "available" }>> = {},
): Extract<SearchWeatherEvidenceResponse, { status: "available" }> {
  return {
    weather_evidence_version: "search-weather-evidence-v1",
    status: "available",
    ski_area_id: "tignes-ski-area",
    evaluated_at: "2026-07-16T12:00:00Z",
    cache_valid_until: "2026-07-16T12:05:00Z",
    evidence: {
      mode: "climatology",
      window_label: "March",
      elevation_band: "mid_mountain",
      elevation_m: 2400,
      elevation_status: "exact",
      interpretation: "Historically reliable at mid-mountain in March.",
      limitations: [],
      historical: {
        source_label: "Open-Meteo archive climatology",
        source_model: "ERA5-Land",
        computed_at: "2026-07-15T02:00:00Z",
        baseline_start_year: 1995,
        baseline_end_year: 2024,
        evidence_seasons: 30,
        latest_archive_year: 2024,
        provenance_status: "homogeneous",
        sources: [],
        snow_depth_cm_p25: 82,
        snow_depth_cm_p50: 128,
        snow_depth_cm_p75: 176,
        probability_snow_depth_ge_30cm: 0.87,
        average_daily_snowfall_cm: 4.2,
        average_max_temperature_c: -2.1,
        daily_profile: [historicalPoint],
      },
      forecast: null,
    },
    ...updates,
  };
}

function forecastResponse(
  head = "forecast-head-1",
  pointUpdates: Partial<WeatherEvidencePoint> = {},
): Extract<SearchWeatherEvidenceResponse, { status: "available" }> {
  const forecastPoint: WeatherEvidencePoint = {
    date_or_month_day: "2026-07-20",
    snow_depth_cm: 112,
    snow_depth_cm_p25: null,
    snow_depth_cm_p50: null,
    snow_depth_cm_p75: null,
    snowfall_cm: 7.4,
    temperature_min_c: -7,
    temperature_max_c: -1,
    rain_risk: 0.1,
    thaw_risk: 0.2,
    wind_gust_kmh: 46,
    ...pointUpdates,
  };
  return {
    ...historicalResponse(),
    evaluated_at: "2026-07-16T12:02:00Z",
    cache_valid_until: "2026-07-16T13:00:00Z",
    evidence: {
      ...historicalResponse().evidence,
      mode: "forecast_assisted",
      window_label: "20-22 July 2026",
      interpretation: "Fresh forecast supports the requested dates.",
      forecast: {
        source_label: "Open-Meteo forecast",
        source_model: "best_match",
        issued_at: head === "forecast-head-1"
          ? "2026-07-16T11:00:00Z"
          : "2026-07-16T12:30:00Z",
        provenance_status: "homogeneous",
        sources: [
          {
            forecast_run_id: head,
            forecast_source_key: "open-meteo",
            source_label: "Open-Meteo forecast",
            source_model: "best_match",
            issued_at: "2026-07-16T11:00:00Z",
            elevation_m: 2400,
            row_count: 3,
            profile_dates: ["2026-07-20", "2026-07-21", "2026-07-22"],
          },
        ],
        coverage_status: "partial",
        usable_date_count: 2,
        requested_date_count: 3,
        average_forecast_share: 0.67,
        daily_profile: [forecastPoint],
      },
    },
  };
}

beforeEach(clearWeatherEvidenceCache);

test("renders month climatology provenance, supported metrics, and structured values", async () => {
  render(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockResolvedValue(historicalResponse())}
    />,
  );

  expect(await screen.findByText("Historical pattern")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Snow evidence for March" })).toBeVisible();
  expect(screen.getByText(/climatology rather than a live forecast/i)).toBeVisible();
  expect(screen.getByText(/mid-mountain.*2,400 m/i)).toBeVisible();
  expect(screen.getByText(/30 evidence seasons/i)).toBeVisible();
  expect(screen.getByText("Open-Meteo archive climatology")).toBeVisible();
  const metrics = document.querySelector(".snow-metrics") as HTMLElement;
  expect(
    within(metrics).getByText("128 cm"),
  ).toBeVisible();
  expect(within(metrics).getByText("82-176 cm")).toBeVisible();
  expect(within(metrics).getByText("4.2 cm/day")).toBeVisible();
  expect(within(metrics).getByText("87%")).toBeVisible();
  expect(within(metrics).getByText("-2.1 °C")).toBeVisible();
  expect(screen.queryByRole("tab", { name: "Forecast" })).toBeNull();
  expect(screen.getByText("Historically reliable at mid-mountain in March.")).toBeVisible();

  await userEvent.click(screen.getByText("View structured weather values"));
  const table = screen.getByRole("table", { name: "Historical weather values" });
  expect(within(table).getByText("03-15")).toBeVisible();
  expect(within(table).getByText("128 cm")).toBeVisible();
  expect(within(table).queryByText("0 cm")).toBeNull();
  expect(screen.getByText(/solid line: median/i)).toBeVisible();
  expect(screen.getByText(/shaded range: 25th to 75th percentile/i)).toBeVisible();
  expect(await screen.findByRole("status")).toHaveTextContent(/snow evidence loaded/i);
});

test("trusts forecast-assisted mode and supports keyboard tabs", async () => {
  const user = userEvent.setup();
  render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockResolvedValue(forecastResponse())}
    />,
  );

  expect(await screen.findByText("Forecast-assisted")).toBeVisible();
  expect(screen.getByText(/issued.*16 jul 2026/i)).toBeVisible();
  expect(screen.getByText(/fresh at evaluation time/i)).toBeVisible();
  expect(screen.getByText(/partial coverage.*2 of 3 dates/i)).toBeVisible();
  const forecastTab = screen.getByRole("tab", { name: "Forecast" });
  const historicalTab = screen.getByRole("tab", { name: "Historical context" });
  expect(forecastTab).toHaveAttribute("aria-selected", "true");
  forecastTab.focus();
  await user.keyboard("{ArrowRight}");
  expect(historicalTab).toHaveFocus();
  expect(historicalTab).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tabpanel", { name: "Historical context" })).toBeVisible();
  await user.keyboard("{ArrowRight}");
  expect(forecastTab).toHaveFocus();
  expect(forecastTab).toHaveAttribute("aria-selected", "true");
});

test("does not mark a non-null wind gust as a forecast risk", async () => {
  render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockResolvedValue(forecastResponse("forecast-head-1", {
        rain_risk: 0,
        thaw_risk: 0,
        wind_gust_kmh: 10,
      }))}
    />,
  );

  await screen.findByText("Forecast-assisted");
  expect(document.querySelectorAll(".snow-chart__risk")).toHaveLength(0);
  expect(screen.getByText(/diamond: rain or thaw risk/i)).toBeVisible();
  expect(screen.getByText(/diamond markers identify days with rain or thaw risk/i)).toBeVisible();
});

test("marks a positive rain or thaw signal as a forecast risk", async () => {
  render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockResolvedValue(forecastResponse("forecast-head-1", {
        rain_risk: 0,
        thaw_risk: 0.2,
        wind_gust_kmh: 10,
      }))}
    />,
  );

  await screen.findByText("Forecast-assisted");
  expect(document.querySelectorAll(".snow-chart__risk")).toHaveLength(1);
});

test("renders server fallback limitations and typed unavailability without generic factor inference", async () => {
  const fallback = historicalResponse({
    evidence: {
      ...historicalResponse().evidence,
      window_label: "20-22 July 2026",
      limitations: ["The selected forecast run was stale at evaluation time."],
    },
  });
  const { rerender } = render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockResolvedValue(fallback)}
    />,
  );
  expect(await screen.findByText("Historical pattern")).toBeVisible();
  expect(screen.getByText(/selected forecast run was stale/i)).toBeVisible();
  expect(screen.queryByRole("tab", { name: "Forecast" })).toBeNull();

  clearWeatherEvidenceCache();
  rerender(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="les-arcs-ski-area"
      skiAreaName="Les Arcs"
      loadEvidence={vi.fn().mockResolvedValue({
        weather_evidence_version: "search-weather-evidence-v1",
        status: "unavailable",
        ski_area_id: "les-arcs-ski-area",
        evaluated_at: "2026-07-16T12:00:00Z",
        cache_valid_until: "2026-07-16T12:05:00Z",
        unavailable_reason: "historical_evidence_unavailable",
        limitations: ["No supported historical evidence covers this ski area."],
      })}
    />,
  );
  expect(await screen.findByRole("heading", { name: "Snow evidence unavailable" })).toBeVisible();
  expect(screen.getByText(/no supported historical evidence/i)).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent(/unavailable for les arcs/i);
  expect(document.body.textContent).not.toContain("trip_window_snow_fit");
});

test("preserves the section during retryable failure and announces a successful retry", async () => {
  const user = userEvent.setup();
  const loadEvidence = vi
    .fn()
    .mockRejectedValueOnce(new Error("Stored weather evidence is temporarily unavailable."))
    .mockResolvedValueOnce(historicalResponse());
  render(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );

  expect(await screen.findByRole("heading", { name: "Snow evidence could not be loaded" })).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent(/could not be loaded/i);
  const retry = screen.getByRole("button", { name: "Retry snow evidence" });
  await user.click(retry);
  expect(await screen.findByText("Historical pattern")).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent(/snow evidence loaded/i);
  expect(screen.getByRole("button", { name: "Reload snow evidence" })).toHaveFocus();
  expect(loadEvidence).toHaveBeenCalledTimes(2);
});

test("changes the cache context when the applied travel window changes", async () => {
  const loadEvidence = vi.fn().mockResolvedValue(historicalResponse());
  const { rerender } = render(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );
  expect(await screen.findByText("Historical pattern")).toBeVisible();

  rerender(
    <SnowEvidence
      intent={{
        ...monthIntent,
        constraints: { travel_window: { month: 4 } },
      }}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );
  await waitFor(() => expect(loadEvidence).toHaveBeenCalledTimes(2));
  expect(loadEvidence.mock.calls[1][0].intent.constraints.travel_window).toEqual({
    month: 4,
  });
});

test("reuses an unexpired cache entry and refetches an expired entry with a new head", async () => {
  vi.setSystemTime("2026-07-16T12:00:00Z");
  const loadEvidence = vi
    .fn()
    .mockResolvedValueOnce(forecastResponse("forecast-head-1"))
    .mockResolvedValueOnce(forecastResponse("forecast-head-2"));
  const first = render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );
  expect(await screen.findByText(/selected run forecast-head-1/i)).toBeVisible();
  first.unmount();

  const cached = render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );
  expect(await screen.findByText(/selected run forecast-head-1/i)).toBeVisible();
  expect(loadEvidence).toHaveBeenCalledTimes(1);
  cached.unmount();

  vi.setSystemTime("2026-07-16T13:00:00Z");
  render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );
  expect(await screen.findByText(/selected run forecast-head-2/i)).toBeVisible();
  expect(screen.queryByText(/selected run forecast-head-1/i)).toBeNull();
  vi.useRealTimers();
});

test("ignores an older in-flight response after the ski area changes", async () => {
  let resolveFirst: ((response: SearchWeatherEvidenceResponse) => void) | undefined;
  const first = new Promise<SearchWeatherEvidenceResponse>((resolve) => {
    resolveFirst = resolve;
  });
  const lesArcs = historicalResponse({
    ski_area_id: "les-arcs-ski-area",
    evidence: { ...historicalResponse().evidence, window_label: "Les Arcs March" },
  });
  const loadEvidence = vi.fn().mockReturnValueOnce(first).mockResolvedValueOnce(lesArcs);
  const { rerender } = render(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );
  expect(
    screen.getByRole("heading", { name: /loading snow evidence for tignes/i }),
  ).toBeVisible();

  rerender(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="les-arcs-ski-area"
      skiAreaName="Les Arcs"
      loadEvidence={loadEvidence}
    />,
  );
  expect(screen.queryByRole("heading", { name: "Snow evidence for March" })).toBeNull();
  expect(
    screen.getByRole("heading", { name: "Loading snow evidence for Les Arcs" }),
  ).toBeVisible();
  expect(await screen.findByRole("heading", { name: "Snow evidence for Les Arcs March" })).toBeVisible();
  resolveFirst?.(historicalResponse());
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Snow evidence for Les Arcs March" })).toBeVisible();
  });
  expect(screen.queryByRole("heading", { name: "Snow evidence for March" })).toBeNull();
});

test("ignores an older in-flight response after the applied window changes for the same ski area", async () => {
  vi.setSystemTime("2026-07-16T11:00:00Z");
  let resolveFirst: ((response: SearchWeatherEvidenceResponse) => void) | undefined;
  let resolveSecond: ((response: SearchWeatherEvidenceResponse) => void) | undefined;
  const first = new Promise<SearchWeatherEvidenceResponse>((resolve) => {
    resolveFirst = resolve;
  });
  const second = new Promise<SearchWeatherEvidenceResponse>((resolve) => {
    resolveSecond = resolve;
  });
  const aprilIntent: SearchIntent = {
    ...monthIntent,
    constraints: { travel_window: { month: 4 } },
  };
  const aprilResponse = historicalResponse({
    evidence: { ...historicalResponse().evidence, window_label: "April" },
  });
  const loadEvidence = vi.fn().mockReturnValueOnce(first).mockReturnValueOnce(second);
  const { rerender } = render(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );

  rerender(
    <SnowEvidence
      intent={aprilIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );
  await waitFor(() => expect(loadEvidence).toHaveBeenCalledTimes(2));

  resolveSecond?.(aprilResponse);
  expect(await screen.findByRole("heading", { name: "Snow evidence for April" })).toBeVisible();

  resolveFirst?.(historicalResponse());
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Snow evidence for April" })).toBeVisible();
  });
  expect(screen.queryByRole("heading", { name: "Snow evidence for March" })).toBeNull();
  expect(
    readWeatherEvidenceCache(weatherEvidenceCacheKey("tignes-ski-area", { month: 3 })),
  ).toBeNull();
  expect(
    readWeatherEvidenceCache(weatherEvidenceCacheKey("tignes-ski-area", { month: 4 })),
  ).toBe(aprilResponse);
  vi.useRealTimers();
});
