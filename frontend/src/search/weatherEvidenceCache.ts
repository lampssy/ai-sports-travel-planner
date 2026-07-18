import type { SearchIntent, SearchWeatherEvidenceResponse } from "../types";

type TravelWindow = SearchIntent["constraints"]["travel_window"];

const sessionCache = new Map<string, SearchWeatherEvidenceResponse>();

export function weatherEvidenceCacheKey(
  skiAreaId: string,
  travelWindow: TravelWindow,
): string {
  if (!travelWindow) return `${skiAreaId}|window:none`;
  if (typeof travelWindow.month === "number") {
    return `${skiAreaId}|month:${travelWindow.month}`;
  }
  if (travelWindow.start_date && travelWindow.end_date) {
    return `${skiAreaId}|dates:${travelWindow.start_date}:${travelWindow.end_date}`;
  }
  return `${skiAreaId}|window:none`;
}

export function readWeatherEvidenceCache(
  key: string,
  now = Date.now(),
): SearchWeatherEvidenceResponse | null {
  const response = sessionCache.get(key);
  if (!response) return null;
  if (now >= Date.parse(response.cache_valid_until)) {
    sessionCache.delete(key);
    return null;
  }
  return response;
}

export function writeWeatherEvidenceCache(
  key: string,
  response: SearchWeatherEvidenceResponse,
): void {
  sessionCache.set(key, response);
}

export function deleteWeatherEvidenceCache(key: string): void {
  sessionCache.delete(key);
}

export function clearWeatherEvidenceCache(): void {
  sessionCache.clear();
}
