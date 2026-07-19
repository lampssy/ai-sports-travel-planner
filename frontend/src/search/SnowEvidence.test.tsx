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
  buildWeatherChartData,
  formatWeatherChartTickLabel,
  selectWeatherChartTickLabels,
  weatherMetricDefinition,
} from "./SnowEvidenceChart";
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
        sources: [
          {
            source_model: "ERA5-Land",
            computed_at: "2026-07-15T02:00:00Z",
            baseline_period: "normal_30y",
            baseline_start_year: 1995,
            baseline_end_year: 2024,
            evidence_seasons: 30,
            latest_archive_year: 2024,
            elevation_m: 2400,
            row_count: 3,
            profile_dates: ["03-01", "03-15", "03-31"],
          },
        ],
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

async function openVisibleSources(user: ReturnType<typeof userEvent.setup>) {
  const summaries = await screen.findAllByText("Sources and daily values");
  const visibleSummary = summaries.find((summary) => !summary.closest("[hidden]"));
  expect(visibleSummary).toBeDefined();
  await user.click(visibleSummary!);
}

test("maps historical ranges and preserves missing observations as null chart gaps", () => {
  const missing: WeatherEvidencePoint = {
    date_or_month_day: "03-16",
    snow_depth_cm: null,
    snow_depth_cm_p25: null,
    snow_depth_cm_p50: null,
    snow_depth_cm_p75: null,
    snowfall_cm: null,
    temperature_min_c: null,
    temperature_max_c: null,
    rain_risk: null,
    thaw_risk: null,
    wind_gust_kmh: null,
  };

  expect(buildWeatherChartData("historical", "depth", [historicalPoint, missing])).toEqual([
    {
      label: "03-15",
      depthRange: [82, 176],
      medianDepth: 128,
      depth: null,
      freshSnow: 4.2,
      minimumTemperature: -8,
      maximumTemperature: -2.1,
    },
    {
      label: "03-16",
      depthRange: null,
      medianDepth: null,
      depth: null,
      freshSnow: null,
      minimumTemperature: null,
      maximumTemperature: null,
    },
  ]);
});

test("bounds dense chart labels while preserving the first, middle, and last dates", () => {
  const points = Array.from({ length: 31 }, (_, index) => ({
    ...historicalPoint,
    date_or_month_day: `2026-07-${String(index + 1).padStart(2, "0")}`,
  }));
  const data = buildWeatherChartData("forecast", "depth", points);

  expect(selectWeatherChartTickLabels(data)).toEqual([
    "2026-07-01",
    "2026-07-16",
    "2026-07-31",
  ]);
  expect(formatWeatherChartTickLabel("2026-07-31")).toBe("07-31");
  expect(formatWeatherChartTickLabel("03-31")).toBe("03-31");
});

test("does not load the chart controls until weather evidence resolves", async () => {
  let resolveEvidence:
    | ((response: SearchWeatherEvidenceResponse) => void)
    | undefined;
  const pending = new Promise<SearchWeatherEvidenceResponse>((resolve) => {
    resolveEvidence = resolve;
  });
  render(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockReturnValue(pending)}
    />,
  );

  expect(screen.queryByRole("tab", { name: "Snow depth" })).toBeNull();
  resolveEvidence?.(historicalResponse());
  expect(await screen.findByRole("tab", { name: "Snow depth" })).toBeVisible();
});

test("retains forecast API values and scopes the 30 cm reference to snow depth", () => {
  const point = forecastResponse().evidence.forecast?.daily_profile[0];
  expect(point).toBeDefined();
  expect(buildWeatherChartData("forecast", "temperature", [point!])).toEqual([
    expect.objectContaining({
      label: "2026-07-20",
      depth: 112,
      freshSnow: 7.4,
      minimumTemperature: -7,
      maximumTemperature: -1,
    }),
  ]);
  expect(weatherMetricDefinition.depth.referenceValue).toBe(30);
  expect(weatherMetricDefinition.depth.unit).toBe("cm");
  expect(weatherMetricDefinition.freshSnow.referenceValue).toBeNull();
  expect(weatherMetricDefinition.temperature.unit).toBe("°C");
});

test("renders month climatology metrics, segmented charts, and collapsed source values", async () => {
  const user = userEvent.setup();
  render(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockResolvedValue(historicalResponse())}
    />,
  );

  expect(await screen.findByText("Historical pattern")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Snow & weather for March" })).toBeVisible();
  expect(screen.getByText(/climatology rather than a live forecast/i)).toBeVisible();
  expect(screen.getByText(/mid-mountain.*2,400 m/i)).toBeVisible();
  expect(screen.getByText(/30 evidence seasons/i)).toBeVisible();
  const metrics = document.querySelector(".snow-metrics") as HTMLElement;
  expect(
    within(metrics).getByText("128 cm"),
  ).toBeVisible();
  expect(within(metrics).getByText("82-176 cm")).toBeVisible();
  expect(within(metrics).getByText("4.2 cm/day")).toBeVisible();
  expect(within(metrics).getByText(/87% average historical likelihood/i)).toBeVisible();
  expect(within(metrics).getByText("-2.1 °C")).toBeVisible();
  expect(screen.queryByRole("tab", { name: "Forecast" })).toBeNull();
  expect(
    screen.getAllByText("Historically reliable at mid-mountain in March."),
  ).toHaveLength(2);
  expect(screen.getByRole("tab", { name: "Snow depth" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(screen.getByRole("tab", { name: "Fresh snow" })).toBeVisible();
  expect(screen.getByRole("tab", { name: "Temperature" })).toBeVisible();
  expect(
    screen.getByRole("img", { name: /historical snow depth chart in cm/i }),
  ).toBeVisible();
  await user.click(screen.getByRole("tab", { name: "Fresh snow" }));
  expect(
    screen.getByRole("img", { name: /historical fresh snow chart in cm/i }),
  ).toBeVisible();
  expect(
    screen.queryByRole("img", { name: /historical snow depth chart in cm/i }),
  ).toBeNull();
  await user.click(screen.getByRole("tab", { name: "Temperature" }));
  expect(
    screen.getByRole("img", { name: /historical temperature chart in °c/i }),
  ).toBeVisible();
  expect(screen.getByRole("table", { name: "Historical weather values", hidden: true })).not.toBeVisible();
  expect(screen.getByText("Open-Meteo archive climatology")).not.toBeVisible();

  await user.click(screen.getByText("Sources and daily values"));
  const table = screen.getByRole("table", { name: "Historical weather values" });
  expect(screen.getByText("Open-Meteo archive climatology")).toBeVisible();
  expect(within(table).getByText("03-15")).toBeVisible();
  expect(within(table).getByText("128 cm")).toBeVisible();
  expect(within(table).queryByText("0 cm")).toBeNull();
  expect(within(table).getAllByText("Not available").length).toBeGreaterThan(0);
  expect(screen.queryByText(/typed weather evidence/i)).toBeNull();
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
  expect(screen.getByText("16 Jul 2026, 11:00 UTC")).toBeVisible();
  expect(screen.getByText(/fresh at 16 jul 2026, 12:02 utc/i)).toBeVisible();
  expect(screen.getByText("2 of 3 covered")).toBeVisible();
  expect(screen.getByText("67%")).toBeVisible();
  expect(screen.getByText("Forecast coverage in this assessment")).toBeVisible();
  const forecastTab = screen.getByRole("tab", { name: "Forecast" });
  const historicalTab = screen.getByRole("tab", { name: "Historical context" });
  expect(screen.getByText("Average daily median depth")).not.toBeVisible();
  expect(forecastTab).toHaveAttribute("aria-selected", "true");
  forecastTab.focus();
  await user.keyboard("{ArrowRight}");
  expect(historicalTab).toHaveFocus();
  expect(historicalTab).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tabpanel", { name: "Historical context" })).toBeVisible();
  expect(screen.getByText("Average daily median depth")).toBeVisible();
  await user.keyboard("{ArrowRight}");
  expect(forecastTab).toHaveFocus();
  expect(forecastTab).toHaveAttribute("aria-selected", "true");
});

test("keeps selected forecast freshness separate from excluded stale rows", async () => {
  const response = forecastResponse();
  response.evidence = {
    ...response.evidence,
    limitations: ["Stale forecast rows were excluded before selection."],
  };
  render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockResolvedValue(response)}
    />,
  );

  expect(await screen.findByText(/fresh at 16 jul 2026, 12:02 utc/i)).toBeVisible();
  expect(screen.queryByText("Stale at evaluation")).toBeNull();
  expect(screen.getByText(/stale forecast rows were excluded/i)).toBeVisible();
});

test("distinguishes mixed source elevations from unavailable elevation", async () => {
  const mixed = forecastResponse();
  mixed.evidence = {
    ...mixed.evidence,
    elevation_m: null,
    elevation_status: "mixed",
    historical: {
      ...mixed.evidence.historical,
      provenance_status: "mixed",
      sources: [
        {
          source_model: "ERA5-Land",
          computed_at: "2026-07-15T02:00:00Z",
          baseline_period: "normal_30y",
          baseline_start_year: 1995,
          baseline_end_year: 2024,
          evidence_seasons: 30,
          latest_archive_year: 2024,
          elevation_m: 2200,
          row_count: 1,
          profile_dates: ["03-15"],
        },
        {
          source_model: "ERA5-Land",
          computed_at: "2026-07-15T02:00:00Z",
          baseline_period: "recent_15y",
          baseline_start_year: 2010,
          baseline_end_year: 2024,
          evidence_seasons: 15,
          latest_archive_year: 2024,
          elevation_m: 2400,
          row_count: 1,
          profile_dates: ["03-15"],
        },
      ],
    },
    forecast: mixed.evidence.forecast
      ? {
          ...mixed.evidence.forecast,
          provenance_status: "mixed",
        }
      : null,
  };

  render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={vi.fn().mockResolvedValue(mixed)}
    />,
  );

  expect(
    await screen.findByText("Mixed source elevations across this assessment"),
  ).toBeVisible();
  expect(screen.queryByText(/elevation unavailable/i)).toBeNull();
});

test("shows API risk and wind values only in the complete daily-values table", async () => {
  const user = userEvent.setup();
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
  const summaries = screen.getAllByText("Sources and daily values");
  const visibleSummary = summaries.find((summary) => !summary.closest("[hidden]"));
  expect(visibleSummary).toBeDefined();
  await user.click(visibleSummary!);
  const table = screen.getByRole("table", { name: "Forecast weather values" });
  const row = within(table).getByRole("row", { name: /2026-07-20/ });
  expect(row).toHaveTextContent("0 %");
  expect(row).toHaveTextContent("10 km/h");
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
  expect(await screen.findByText("Snow evidence unavailable")).toBeVisible();
  expect(screen.getByText(/no supported historical evidence/i)).toBeVisible();
  expect(screen.getAllByRole("alert")).toHaveLength(1);
  expect(screen.queryByRole("status")).toBeNull();
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

  expect(await screen.findByText("Snow evidence could not be loaded")).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Snow and weather could not be loaded. Try again.",
  );
  expect(screen.getByRole("alert")).not.toHaveTextContent("Stored weather evidence");
  expect(screen.getAllByRole("alert")).toHaveLength(1);
  expect(screen.queryByRole("status")).toBeNull();
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
  const user = userEvent.setup();
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
  await openVisibleSources(user);
  expect(await screen.findByText(/run forecast-head-1/i)).toBeVisible();
  first.unmount();

  const cached = render(
    <SnowEvidence
      intent={datesIntent}
      skiAreaId="tignes-ski-area"
      skiAreaName="Tignes"
      loadEvidence={loadEvidence}
    />,
  );
  await openVisibleSources(user);
  expect(await screen.findByText(/run forecast-head-1/i)).toBeVisible();
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
  await openVisibleSources(user);
  expect(await screen.findByText(/run forecast-head-2/i)).toBeVisible();
  expect(screen.queryByText(/run forecast-head-1/i)).toBeNull();
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
  expect(screen.getAllByText(/loading snow evidence for tignes/i).length).toBeGreaterThan(0);

  rerender(
    <SnowEvidence
      intent={monthIntent}
      skiAreaId="les-arcs-ski-area"
      skiAreaName="Les Arcs"
      loadEvidence={loadEvidence}
    />,
  );
  expect(screen.queryByRole("heading", { name: "Snow & weather for March" })).toBeNull();
  expect(screen.getAllByText("Loading snow evidence for Les Arcs").length).toBeGreaterThan(0);
  expect(await screen.findByRole("heading", { name: "Snow & weather for Les Arcs March" })).toBeVisible();
  resolveFirst?.(historicalResponse());
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Snow & weather for Les Arcs March" })).toBeVisible();
  });
  expect(screen.queryByRole("heading", { name: "Snow & weather for March" })).toBeNull();
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
  expect(await screen.findByRole("heading", { name: "Snow & weather for April" })).toBeVisible();

  resolveFirst?.(historicalResponse());
  await waitFor(() => {
    expect(screen.getByRole("heading", { name: "Snow & weather for April" })).toBeVisible();
  });
  expect(screen.queryByRole("heading", { name: "Snow & weather for March" })).toBeNull();
  expect(
    readWeatherEvidenceCache(weatherEvidenceCacheKey("tignes-ski-area", { month: 3 })),
  ).toBeNull();
  expect(
    readWeatherEvidenceCache(weatherEvidenceCacheKey("tignes-ski-area", { month: 4 })),
  ).toBe(aprilResponse);
  vi.useRealTimers();
});
