import { beforeEach, expect, test } from "vitest";

import type { SearchWeatherEvidenceResponse } from "../types";
import {
  clearWeatherEvidenceCache,
  readWeatherEvidenceCache,
  weatherEvidenceCacheKey,
  writeWeatherEvidenceCache,
} from "./weatherEvidenceCache";

const available: SearchWeatherEvidenceResponse = {
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
    interpretation: "Historically reliable at mid-mountain.",
    limitations: [],
    historical: {
      source_label: "Open-Meteo archive",
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
      daily_profile: [],
    },
    forecast: null,
  },
};

beforeEach(clearWeatherEvidenceCache);

test("builds a canonical key from only ski area and applied travel window", () => {
  expect(weatherEvidenceCacheKey("tignes-ski-area", { month: 3 })).toBe(
    "tignes-ski-area|month:3",
  );
  expect(
    weatherEvidenceCacheKey("tignes-ski-area", {
      start_date: "2027-01-16",
      end_date: "2027-01-20",
    }),
  ).toBe("tignes-ski-area|dates:2027-01-16:2027-01-20");
  expect(weatherEvidenceCacheKey("tignes-ski-area", undefined)).toBe(
    "tignes-ski-area|window:none",
  );
});

test("reuses available and unavailable responses only before server expiry", () => {
  const key = weatherEvidenceCacheKey("tignes-ski-area", { month: 3 });
  writeWeatherEvidenceCache(key, available);

  expect(readWeatherEvidenceCache(key, Date.parse("2026-07-16T12:04:59Z"))).toBe(
    available,
  );
  expect(readWeatherEvidenceCache(key, Date.parse("2026-07-16T12:05:00Z"))).toBeNull();

  const unavailable: SearchWeatherEvidenceResponse = {
    weather_evidence_version: "search-weather-evidence-v1",
    status: "unavailable",
    ski_area_id: "tignes-ski-area",
    evaluated_at: "2026-07-16T12:05:00Z",
    cache_valid_until: "2026-07-16T12:10:00Z",
    unavailable_reason: "historical_evidence_unavailable",
    limitations: ["No historical profile covers this window."],
  };
  writeWeatherEvidenceCache(key, unavailable);
  expect(readWeatherEvidenceCache(key, Date.parse("2026-07-16T12:09:59Z"))).toBe(
    unavailable,
  );
});

test("keeps ski areas and changed applied windows in separate entries", () => {
  const march = weatherEvidenceCacheKey("tignes-ski-area", { month: 3 });
  writeWeatherEvidenceCache(march, available);

  expect(
    readWeatherEvidenceCache(
      weatherEvidenceCacheKey("les-arcs-ski-area", { month: 3 }),
      Date.parse("2026-07-16T12:01:00Z"),
    ),
  ).toBeNull();
  expect(
    readWeatherEvidenceCache(
      weatherEvidenceCacheKey("tignes-ski-area", { month: 4 }),
      Date.parse("2026-07-16T12:01:00Z"),
    ),
  ).toBeNull();
});
