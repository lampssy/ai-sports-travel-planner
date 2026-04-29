import { FormEvent, ReactNode, useEffect, useState } from "react";

import {
  buildAccommodationBookingRedirectUrl,
  clearCurrentTrip,
  getCurrentTripEvents,
  getCurrentTrip,
  getCurrentTripSummary,
  markCurrentTripChecked,
  parseTripBrief,
  saveCurrentTrip,
  searchResorts,
} from "./api";
import type {
  BookingStatus,
  CompanionEvent,
  CurrentTrip,
  CurrentTripSummary,
  ParsedQueryResponse,
  ProvenanceInfo,
  SearchFilters,
  SearchResult,
  TravelMonth,
  TravelWindowMode,
} from "./types";

const monthOptions = [
  { value: 1, label: "January" },
  { value: 2, label: "February" },
  { value: 3, label: "March" },
  { value: 4, label: "April" },
  { value: 5, label: "May" },
  { value: 6, label: "June" },
  { value: 7, label: "July" },
  { value: 8, label: "August" },
  { value: 9, label: "September" },
  { value: 10, label: "October" },
  { value: 11, label: "November" },
  { value: 12, label: "December" },
] as const;

const defaultFilters: SearchFilters = {
  location: "France",
  minPrice: "150",
  maxPrice: "320",
  stars: "2",
  skillLevel: "intermediate",
  liftDistance: "",
  budgetFlex: "",
  travelWindowMode: "any",
  travelMonth: "",
  tripStartDate: "",
  tripEndDate: "",
};

const storageKey = "sports-trip-planner-refine-open";
const searchStateStorageKey = "sports-trip-planner-search-state";
type AppRoute =
  | { name: "search" }
  | { name: "resort"; resortId: string }
  | { name: "current_trip" };
type AppliedFilterKey =
  | "location"
  | "skill_level"
  | "budget"
  | "stars"
  | "lift_distance"
  | "budget_flex"
  | "travel_window";

interface StoredSearchState {
  tripBrief: string;
  lastParsedTripBrief: string;
  parsedQuery: ParsedQueryResponse | null;
  filters: SearchFilters;
  results: SearchResult[];
  selectedResultId: string | null;
  hasSearched: boolean;
}

const emptyStoredSearchState: StoredSearchState = {
  tripBrief: "",
  lastParsedTripBrief: "",
  parsedQuery: null,
  filters: defaultFilters,
  results: [],
  selectedResultId: null,
  hasSearched: false,
};

function readCurrentRoute(): AppRoute {
  if (typeof window === "undefined") {
    return { name: "search" };
  }

  const pathname = window.location.pathname.replace(/\/+$/, "") || "/";
  if (pathname === "/current-trip") {
    return { name: "current_trip" };
  }

  const resortMatch = pathname.match(/^\/resorts\/([^/]+)$/);
  if (resortMatch) {
    return {
      name: "resort",
      resortId: decodeURIComponent(resortMatch[1]),
    };
  }

  return { name: "search" };
}

function routeToPath(route: AppRoute): string {
  if (route.name === "current_trip") {
    return "/current-trip";
  }
  if (route.name === "resort") {
    return `/resorts/${encodeURIComponent(route.resortId)}`;
  }

  return "/";
}

function readStoredSearchState(): StoredSearchState {
  if (typeof window === "undefined") {
    return emptyStoredSearchState;
  }

  try {
    const raw = window.sessionStorage.getItem(searchStateStorageKey);
    if (!raw) {
      return emptyStoredSearchState;
    }

    const parsed = JSON.parse(raw) as Partial<StoredSearchState>;
    return {
      tripBrief:
        typeof parsed.tripBrief === "string" ? parsed.tripBrief : "",
      lastParsedTripBrief:
        typeof parsed.lastParsedTripBrief === "string"
          ? parsed.lastParsedTripBrief
          : "",
      parsedQuery: parsed.parsedQuery ?? null,
      filters: {
        ...defaultFilters,
        ...(parsed.filters ?? {}),
      },
      results: Array.isArray(parsed.results) ? parsed.results : [],
      selectedResultId:
        typeof parsed.selectedResultId === "string"
          ? parsed.selectedResultId
          : null,
      hasSearched: parsed.hasSearched === true,
    };
  } catch {
    return emptyStoredSearchState;
  }
}

function writeStoredSearchState(state: StoredSearchState) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.sessionStorage.setItem(searchStateStorageKey, JSON.stringify(state));
  } catch {
    // Losing cached UI state should not break search or routing.
  }
}

function App() {
  const [initialSearchState] = useState(readStoredSearchState);
  const [route, setRoute] = useState<AppRoute>(() => readCurrentRoute());
  const [tripBrief, setTripBrief] = useState(initialSearchState.tripBrief);
  const [lastParsedTripBrief, setLastParsedTripBrief] = useState(
    initialSearchState.lastParsedTripBrief,
  );
  const [parsedQuery, setParsedQuery] = useState<ParsedQueryResponse | null>(
    initialSearchState.parsedQuery,
  );
  const [filters, setFilters] = useState<SearchFilters>(initialSearchState.filters);
  const [results, setResults] = useState<SearchResult[]>(
    initialSearchState.results,
  );
  const [selectedResultId, setSelectedResultId] = useState<string | null>(
    initialSearchState.selectedResultId,
  );
  const [hasSearched, setHasSearched] = useState(
    initialSearchState.hasSearched || initialSearchState.results.length > 0,
  );
  const [isAdvancedOpen, setIsAdvancedOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }

    return window.sessionStorage.getItem(storageKey) === "true";
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [isSavingTrip, setIsSavingTrip] = useState(false);
  const [isMarkingChecked, setIsMarkingChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [currentTrip, setCurrentTrip] = useState<CurrentTrip | null>(null);
  const [currentTripSummary, setCurrentTripSummary] =
    useState<CurrentTripSummary | null>(null);
  const [currentTripError, setCurrentTripError] = useState<string | null>(null);
  const [currentTripSummaryError, setCurrentTripSummaryError] = useState<
    string | null
  >(null);
  const [currentTripEvents, setCurrentTripEvents] = useState<CompanionEvent[]>([]);
  const [isCurrentTripLoading, setIsCurrentTripLoading] = useState(false);
  const [tripBookingStatus, setTripBookingStatus] =
    useState<BookingStatus>("not_booked_yet");

  useEffect(() => {
    window.sessionStorage.setItem(storageKey, String(isAdvancedOpen));
  }, [isAdvancedOpen]);

  useEffect(() => {
    function handlePopState() {
      setRoute(readCurrentRoute());
    }

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  useEffect(() => {
    writeStoredSearchState({
      tripBrief,
      lastParsedTripBrief,
      parsedQuery,
      filters,
      results,
      selectedResultId,
      hasSearched,
    });
  }, [
    tripBrief,
    lastParsedTripBrief,
    parsedQuery,
    filters,
    results,
    selectedResultId,
    hasSearched,
  ]);

  useEffect(() => {
    if (route.name === "resort") {
      setSelectedResultId(route.resortId);
    }
  }, [route]);

  useEffect(() => {
    let isCancelled = false;

    async function loadCurrentTrip() {
      try {
        const trip = await getCurrentTrip();
        if (!isCancelled) {
          setCurrentTrip(trip);
          setCurrentTripError(null);
        }
      } catch (caughtError) {
        if (!isCancelled) {
          setCurrentTripError(
            caughtError instanceof Error
              ? caughtError.message
              : "Unable to load current trip.",
          );
        }
      }
    }

    void loadCurrentTrip();

    return () => {
      isCancelled = true;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function loadCurrentTripSummaryState() {
      if (route.name !== "current_trip" || currentTrip === null) {
        if (!isCancelled && currentTrip === null) {
          setCurrentTripSummary(null);
          setCurrentTripSummaryError(null);
          setCurrentTripEvents([]);
        }
        return;
      }

      setIsCurrentTripLoading(true);

      try {
        const [summary, events] = await Promise.all([
          getCurrentTripSummary(),
          getCurrentTripEvents(),
        ]);
        if (!isCancelled) {
          setCurrentTripSummary(summary);
          setCurrentTripEvents(events);
          setCurrentTripSummaryError(null);
        }
      } catch (caughtError) {
        if (!isCancelled) {
          setCurrentTripSummary(null);
          setCurrentTripEvents([]);
          setCurrentTripSummaryError(
            caughtError instanceof Error
              ? caughtError.message
              : "Unable to load current trip summary.",
          );
        }
      } finally {
        if (!isCancelled) {
          setIsCurrentTripLoading(false);
        }
      }
    }

    void loadCurrentTripSummaryState();

    return () => {
      isCancelled = true;
    };
  }, [
    route.name,
    currentTrip?.resort_id,
    currentTrip?.selected_stay_base_name,
    currentTrip?.selected_ski_area_name,
    currentTrip?.travel_month,
    currentTrip?.trip_start_date,
    currentTrip?.trip_end_date,
    currentTrip?.booking_status,
    currentTrip?.last_checked_at,
  ]);

  const selectedResult =
    route.name === "resort"
      ? results.find((result) => result.resort_id === route.resortId) ?? null
      : results.find((result) => result.resort_id === selectedResultId) ??
        results[0] ??
        null;
  const showRecommendationsPanel =
    hasSearched || isLoading || Boolean(error) || results.length > 0;
  const searchRouteLayoutClass = showRecommendationsPanel
    ? "grid w-full flex-1 gap-8 xl:grid-cols-[0.82fr_1.18fr]"
    : "grid w-full flex-1";
  const searchPanelClass = showRecommendationsPanel
    ? "h-fit rounded-[2rem] border border-white/70 bg-white/88 p-5 shadow-panel backdrop-blur sm:p-6"
    : "rounded-[2.4rem] border border-white/70 bg-white/90 p-5 shadow-panel backdrop-blur sm:p-8 lg:p-10";

  useEffect(() => {
    if (
      currentTrip &&
      selectedResult &&
      currentTrip.resort_id === selectedResult.resort_id &&
      currentTrip.selected_stay_base_name === selectedResult.selected_stay_base_name &&
      currentTrip.selected_ski_area_name === selectedResult.selected_ski_area_name
    ) {
      setTripBookingStatus(currentTrip.booking_status);
      return;
    }

    setTripBookingStatus("not_booked_yet");
  }, [currentTrip, selectedResult]);

  function navigateTo(nextRoute: AppRoute, options?: { replace?: boolean }) {
    const nextPath = routeToPath(nextRoute);
    if (window.location.pathname !== nextPath) {
      if (options?.replace) {
        window.history.replaceState(null, "", nextPath);
      } else {
        window.history.pushState(null, "", nextPath);
      }
    }
    setRoute(nextRoute);
  }

  function handleSelectResult(resultId: string) {
    setSelectedResultId(resultId);
    navigateTo({ name: "resort", resortId: resultId });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setParseError(null);

    let nextFilters = filters;
    let attemptedParse = false;

    try {
      const trimmedBrief = tripBrief.trim();
      if (trimmedBrief && trimmedBrief !== lastParsedTripBrief) {
        attemptedParse = true;
        setIsParsing(true);
        const parsed = await parseTripBrief(trimmedBrief);
        setParsedQuery(parsed);
        setLastParsedTripBrief(trimmedBrief);
        nextFilters = mergeParsedFilters(filters, parsed);
        setFilters(nextFilters);
      }

      const validationError = validateSearchFilters(nextFilters);
      if (validationError) {
        setResults([]);
        setSelectedResultId(null);
        setHasSearched(true);
        setError(validationError);
        return;
      }

      setHasSearched(true);
      const response = await searchResorts(nextFilters);
      setResults(response.results);
      setSelectedResultId((current) => {
        const preserved = response.results.find(
          (result) => result.resort_id === current,
        );
        return preserved?.resort_id ?? response.results[0]?.resort_id ?? null;
      });
    } catch (caughtError) {
      setResults([]);
      setSelectedResultId(null);
      const message =
        caughtError instanceof Error
          ? caughtError.message
          : "Something went wrong while loading results.";
      if (attemptedParse) {
        setParseError(message);
      } else {
        setError(message);
      }
    } finally {
      setIsParsing(false);
      setIsLoading(false);
    }
  }

  function mergeParsedFilters(
    currentFilters: SearchFilters,
    parsed: ParsedQueryResponse,
  ): SearchFilters {
    const nextFilters = { ...currentFilters };
    const { filters: parsedFilters } = parsed;
    let shouldOpenAdvancedFilters = false;

    if (parsedFilters.location) {
      nextFilters.location = parsedFilters.location;
    }
    if (parsedFilters.min_price !== undefined) {
      nextFilters.minPrice = String(parsedFilters.min_price);
    }
    if (parsedFilters.max_price !== undefined) {
      nextFilters.maxPrice = String(parsedFilters.max_price);
    }
    if (parsedFilters.stars !== undefined) {
      nextFilters.stars = String(parsedFilters.stars) as SearchFilters["stars"];
    }
    if (parsedFilters.skill_level) {
      nextFilters.skillLevel = parsedFilters.skill_level;
    }
    if (parsedFilters.lift_distance) {
      nextFilters.liftDistance = parsedFilters.lift_distance;
      shouldOpenAdvancedFilters = true;
    }
    if (parsedFilters.budget_flex !== undefined) {
      nextFilters.budgetFlex = String(parsedFilters.budget_flex);
      shouldOpenAdvancedFilters = true;
    }
    if (parsedFilters.trip_start_date && parsedFilters.trip_end_date) {
      nextFilters.travelWindowMode = "dates";
      nextFilters.tripStartDate = parsedFilters.trip_start_date;
      nextFilters.tripEndDate = parsedFilters.trip_end_date;
      nextFilters.travelMonth = "";
    } else if (parsedFilters.travel_month !== undefined) {
      nextFilters.travelWindowMode = "month";
      nextFilters.travelMonth = parsedFilters.travel_month;
      nextFilters.tripStartDate = "";
      nextFilters.tripEndDate = "";
    }
    if (shouldOpenAdvancedFilters) {
      setIsAdvancedOpen(true);
    }

    return nextFilters;
  }

  function handleTravelWindowModeChange(mode: TravelWindowMode) {
    setFilters((current) => ({
      ...current,
      travelWindowMode: mode,
      travelMonth: mode === "month" ? current.travelMonth : "",
      tripStartDate: mode === "dates" ? current.tripStartDate : "",
      tripEndDate: mode === "dates" ? current.tripEndDate : "",
    }));
  }

  function handleRemoveAppliedFilter(key: AppliedFilterKey) {
    setIsAdvancedOpen(true);
    setFilters((current) => {
      if (key === "location") {
        return { ...current, location: "" };
      }
      if (key === "skill_level") {
        return { ...current, skillLevel: "" };
      }
      if (key === "budget") {
        return { ...current, minPrice: "", maxPrice: "" };
      }
      if (key === "stars") {
        return { ...current, stars: "" };
      }
      if (key === "lift_distance") {
        return { ...current, liftDistance: "" };
      }
      if (key === "budget_flex") {
        return { ...current, budgetFlex: "" };
      }

      return {
        ...current,
        travelWindowMode: "any",
        travelMonth: "",
        tripStartDate: "",
        tripEndDate: "",
      };
    });
  }

  async function handleSaveCurrentTrip() {
    if (!selectedResult) {
      return;
    }

    setIsSavingTrip(true);
    setCurrentTripError(null);

    try {
      const hasCompleteTripWindow =
        filters.travelWindowMode === "dates" &&
        Boolean(filters.tripStartDate) &&
        Boolean(filters.tripEndDate);
      const saved = await saveCurrentTrip({
        resort_id: selectedResult.resort_id,
        selected_ski_area_id: selectedResult.selected_ski_area_id,
        selected_ski_area_name: selectedResult.selected_ski_area_name,
        selected_stay_base_name: selectedResult.selected_stay_base_name,
        travel_month:
          filters.travelWindowMode === "month" && filters.travelMonth
            ? Number(filters.travelMonth)
            : null,
        trip_start_date: hasCompleteTripWindow ? filters.tripStartDate : null,
        trip_end_date: hasCompleteTripWindow ? filters.tripEndDate : null,
        booking_status: tripBookingStatus,
      });
      setCurrentTrip(saved);
      setCurrentTripSummaryError(null);
    } catch (caughtError) {
      setCurrentTripError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to save current trip.",
      );
    } finally {
      setIsSavingTrip(false);
    }
  }

  async function handleClearCurrentTrip() {
    setIsSavingTrip(true);
    setCurrentTripError(null);

    try {
      await clearCurrentTrip();
      setCurrentTrip(null);
      setCurrentTripSummary(null);
      setTripBookingStatus("not_booked_yet");
    } catch (caughtError) {
      setCurrentTripError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to clear current trip.",
      );
    } finally {
      setIsSavingTrip(false);
    }
  }

  async function handleMarkCurrentTripChecked() {
    setIsMarkingChecked(true);
    setCurrentTripSummaryError(null);

    try {
      const updatedTrip = await markCurrentTripChecked();
      setCurrentTrip(updatedTrip);
    } catch (caughtError) {
      setCurrentTripSummaryError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to mark current trip as checked.",
      );
    } finally {
      setIsMarkingChecked(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(214,103,63,0.16),_transparent_26%),radial-gradient(circle_at_85%_10%,_rgba(47,100,92,0.16),_transparent_24%),linear-gradient(180deg,_#f4efe7_0%,_#eef5f4_58%,_#f7faf9_100%)] text-ink">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-5 py-7 sm:px-8 lg:px-10">
        <header className="mb-8 grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="max-w-3xl">
            <p className="mb-3 text-sm font-semibold uppercase tracking-[0.28em] text-ember">
              AI-assisted snow-aware planning
            </p>
            <h1 className="font-display text-4xl font-semibold leading-[0.95] sm:text-6xl">
              Find the right ski window before you book.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-700 sm:text-lg">
              Describe the trip in plain language. Snowcast turns it into
              clear filters, ranks resorts by fit, and shows the evidence
              behind each recommendation.
            </p>
          </div>
          <div className="inline-flex h-fit w-fit rounded-full border border-white/70 bg-white/80 p-1 shadow-sm backdrop-blur">
            <button
              type="button"
              className={`rounded-full px-5 py-2.5 text-sm font-semibold transition ${
                route.name !== "current_trip"
                  ? "bg-ink text-white shadow-sm"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
              onClick={() => navigateTo({ name: "search" })}
            >
              Search
            </button>
            <button
              type="button"
              className={`rounded-full px-5 py-2.5 text-sm font-semibold transition ${
                route.name === "current_trip"
                  ? "bg-ink text-white shadow-sm"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
              onClick={() => navigateTo({ name: "current_trip" })}
            >
              Current trip
            </button>
          </div>
        </header>

        {route.name === "search" ? (
          <div className={searchRouteLayoutClass}>
            <section className={searchPanelClass}>
              <form className="space-y-5" onSubmit={handleSubmit}>
                <div className="rounded-[1.75rem] border border-white/80 bg-frost/80 p-4 shadow-sm">
                  <label className="space-y-3">
                    <span className="text-sm font-semibold text-slate-700">
                      What are you looking for?
                    </span>
                    <textarea
                      className="min-h-36 w-full rounded-[1.35rem] border border-slate-200 bg-white px-4 py-4 text-lg leading-7 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                      value={tripBrief}
                      onChange={(event) => setTripBrief(event.target.value)}
                      placeholder="Cheap March ski trip in France for intermediates, close to the lift."
                    />
                  </label>
                  <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
                    <div className="rounded-2xl bg-white/65 px-3 py-3">
                      <p className="font-semibold text-ink">1. Describe</p>
                      <p className="mt-1">Write timing, budget, level, and place.</p>
                    </div>
                    <div className="rounded-2xl bg-white/65 px-3 py-3">
                      <p className="font-semibold text-ink">2. Review</p>
                      <p className="mt-1">Remove any filter that feels wrong.</p>
                    </div>
                    <div className="rounded-2xl bg-white/65 px-3 py-3">
                      <p className="font-semibold text-ink">3. Compare</p>
                      <p className="mt-1">Open a resort to inspect the evidence.</p>
                    </div>
                  </div>

                  {parseError ? (
                    <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                      {parseError}
                    </div>
                  ) : null}

                  {parsedQuery ? (
                    <div className="mt-4 rounded-2xl border border-white/80 bg-white/85 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
                        What we understood
                      </p>
                      <p className="mt-2 text-sm text-slate-600">
                        Interpretation confidence:{" "}
                        {Math.round(parsedQuery.confidence * 100)}%
                        {parsedQuery.confidence < 0.6
                          ? " - review the filters below if this looks off."
                          : ""}
                      </p>

                      {parsedQuery.unknown_parts.length > 0 ? (
                        <p className="mt-4 text-sm text-slate-600">
                          Not sure how to use:{" "}
                          {parsedQuery.unknown_parts.join(", ")}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>

                <div className="rounded-[1.75rem] border border-slate-200 bg-white/80 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-alpine">
                        Your search filters
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        These are the constraints currently shaping the ranking.
                      </p>
                    </div>
                    <button
                      type="button"
                      className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-alpine hover:text-alpine"
                      onClick={() => setIsAdvancedOpen(true)}
                    >
                      Adjust filters
                    </button>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {buildAppliedFilterChips(filters).map((chip) => (
                      <button
                        key={chip.key}
                        type="button"
                        className="rounded-full border border-alpine/20 bg-frost px-3 py-2 text-sm font-semibold text-alpine transition hover:border-alpine hover:bg-white"
                        onClick={() => handleRemoveAppliedFilter(chip.key)}
                        aria-label={`Remove ${chip.label}`}
                      >
                        {chip.label} x
                      </button>
                    ))}
                  </div>
                </div>

                <div className="rounded-[1.75rem] bg-frost/80 p-4">
                <button
                  type="button"
                  className="flex w-full items-center justify-between text-left"
                  onClick={() => setIsAdvancedOpen((current) => !current)}
                  aria-expanded={isAdvancedOpen}
                >
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-alpine">
                      Adjust filters
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      Use these fields when you want exact control over budget,
                      timing, quality, or lift distance.
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-alpine">
                    {isAdvancedOpen ? "Hide" : "Show"}
                  </span>
                </button>

                {isAdvancedOpen ? (
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <label className="space-y-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Location
                      </span>
                      <input
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        value={filters.location}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            location: event.target.value,
                          }))
                        }
                        placeholder="France"
                      />
                    </label>

                    <label className="space-y-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Skill level
                      </span>
                      <select
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        value={filters.skillLevel}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            skillLevel:
                              event.target.value as SearchFilters["skillLevel"],
                          }))
                        }
                      >
                        <option value="">Choose skill level</option>
                        <option value="beginner">Beginner</option>
                        <option value="intermediate">Intermediate</option>
                        <option value="advanced">Advanced</option>
                      </select>
                    </label>

                    <label className="space-y-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Min price
                      </span>
                      <input
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        inputMode="decimal"
                        value={filters.minPrice}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            minPrice: event.target.value,
                          }))
                        }
                        placeholder="150"
                      />
                    </label>

                    <label className="space-y-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Max price
                      </span>
                      <input
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        inputMode="decimal"
                        value={filters.maxPrice}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            maxPrice: event.target.value,
                          }))
                        }
                        placeholder="320"
                      />
                    </label>

                    <div className="space-y-3 md:col-span-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Travel window
                      </span>
                      <div className="grid gap-3 sm:grid-cols-3">
                        {[
                          ["any", "Any time"],
                          ["month", "Month"],
                          ["dates", "Exact dates"],
                        ].map(([mode, label]) => {
                          const active = filters.travelWindowMode === mode;
                          return (
                            <button
                              key={mode}
                              type="button"
                              className={`rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
                                active
                                  ? "border-alpine bg-alpine text-white"
                                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                              }`}
                              onClick={() =>
                                handleTravelWindowModeChange(mode as TravelWindowMode)
                              }
                            >
                              {label}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {filters.travelWindowMode === "month" ? (
                      <label className="space-y-2 md:col-span-2">
                        <span className="text-sm font-semibold text-slate-700">
                          Travel month
                        </span>
                        <select
                          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                          value={filters.travelMonth}
                          onChange={(event) =>
                            setFilters((current) => ({
                              ...current,
                              travelMonth: event.target.value
                                ? (Number(event.target.value) as TravelMonth)
                                : "",
                              tripStartDate: "",
                              tripEndDate: "",
                            }))
                          }
                        >
                          <option value="">Choose month</option>
                          {monthOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : null}

                    {filters.travelWindowMode === "dates" ? (
                      <>
                        <label className="space-y-2">
                          <span className="text-sm font-semibold text-slate-700">
                            Trip start date
                          </span>
                          <input
                            type="date"
                            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                            value={filters.tripStartDate}
                            onChange={(event) =>
                              setFilters((current) => ({
                                ...current,
                                travelMonth: "",
                                tripStartDate: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="space-y-2">
                          <span className="text-sm font-semibold text-slate-700">
                            Trip end date
                          </span>
                          <input
                            type="date"
                            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                            value={filters.tripEndDate}
                            onChange={(event) =>
                              setFilters((current) => ({
                                ...current,
                                travelMonth: "",
                                tripEndDate: event.target.value,
                              }))
                            }
                          />
                        </label>
                      </>
                    ) : null}

                    <label className="space-y-2 md:col-span-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Minimum quality
                      </span>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          ["1", "1 star"],
                          ["2", "2 stars"],
                          ["3", "3 stars"],
                        ].map(([value, label]) => {
                          const active = filters.stars === value;
                          return (
                            <button
                              key={value}
                              type="button"
                              className={`rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
                                active
                                  ? "border-ember bg-ember text-white"
                                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                              }`}
                              onClick={() =>
                                setFilters((current) => ({
                                  ...current,
                                  stars: value as SearchFilters["stars"],
                                }))
                              }
                            >
                              {label}
                            </button>
                          );
                        })}
                      </div>
                    </label>

                    <label className="space-y-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Lift distance
                      </span>
                      <select
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        value={filters.liftDistance}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            liftDistance:
                              event.target.value as SearchFilters["liftDistance"],
                          }))
                        }
                      >
                        <option value="">No preference</option>
                        <option value="near">Near</option>
                        <option value="medium">Medium</option>
                        <option value="far">Far</option>
                      </select>
                    </label>

                    <label className="space-y-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Budget flex
                      </span>
                      <input
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        inputMode="decimal"
                        value={filters.budgetFlex}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            budgetFlex: event.target.value,
                          }))
                        }
                        placeholder="0.1"
                      />
                    </label>
                  </div>
                ) : null}
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  className="rounded-full bg-ink px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                  disabled={isLoading || isParsing}
                >
                  {isParsing
                    ? "Interpreting..."
                    : isLoading
                      ? "Searching..."
                      : "Find resorts"}
                </button>
                <p className="text-sm text-slate-600">
                  Results update from the filters above. Open any card for the
                  full recommendation evidence.
                </p>
              </div>
            </form>
            </section>

            {showRecommendationsPanel ? (
            <section className="rounded-[2rem] border border-white/70 bg-white/88 p-5 shadow-panel backdrop-blur sm:p-6">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-ember">
                    Ranked by fit and evidence
                  </p>
                  <h2 className="mt-2 font-display text-3xl font-semibold">
                    Recommended resorts
                  </h2>
                  <p className="text-sm text-slate-600">
                    {filters.travelWindowMode === "dates" &&
                    filters.tripStartDate &&
                    filters.tripEndDate
                      ? `Best matches for ${formatDate(filters.tripStartDate)} to ${formatDate(filters.tripEndDate)}. Your selected resort stays selected if it still appears.`
                      : filters.travelWindowMode === "month" && filters.travelMonth
                      ? `Best matches for ${formatMonth(Number(filters.travelMonth))}. Your selected resort stays selected if it still appears.`
                      : "Results are ranked by fit, snow confidence, and stay-base match."}
                  </p>
                </div>
                <span className="rounded-full bg-frost px-4 py-2 text-sm font-semibold text-alpine">
                  {results.length} result{results.length === 1 ? "" : "s"}
                </span>
              </div>

              {error ? (
                <div className="rounded-3xl border border-red-200 bg-red-50 px-4 py-5 text-sm text-red-700">
                  {error}
                </div>
              ) : null}

              {!error && isLoading && results.length === 0 ? (
                <div className="rounded-[1.75rem] border border-dashed border-slate-300 bg-frost/50 px-6 py-12 text-center text-sm text-slate-600">
                  <p className="font-display text-2xl font-semibold text-ink">
                    Comparing resorts...
                  </p>
                  <p className="mx-auto mt-3 max-w-md leading-6">
                    Snowcast is ranking resort fit, snow confidence, and
                    stay-base evidence for the current filters.
                  </p>
                </div>
              ) : null}

              {!error && !isLoading && hasSearched && results.length === 0 ? (
                <div className="rounded-[1.75rem] border border-dashed border-slate-300 bg-frost/50 px-6 py-12 text-center text-sm text-slate-600">
                  <p className="font-display text-2xl font-semibold text-ink">
                    No matching resorts yet.
                  </p>
                  <p className="mx-auto mt-3 max-w-md leading-6">
                    Try broadening the location, budget, quality, or travel
                    window. Snowcast will keep the filters visible so you can
                    adjust the search without starting over.
                  </p>
                </div>
              ) : null}

              <div className="grid gap-4">
                {results.map((result, index) => {
                  const selected = result.resort_id === selectedResult?.resort_id;
                  return (
                    <SearchResultCard
                      key={result.resort_id}
                      result={result}
                      rank={index + 1}
                      selected={selected}
                      onSelect={() => handleSelectResult(result.resort_id)}
                    />
                  );
                })}
              </div>
            </section>
            ) : null}
          </div>
        ) : route.name === "resort" ? (
          <SelectedResortPage
            result={selectedResult}
            filters={filters}
            tripBookingStatus={tripBookingStatus}
            onTripBookingStatusChange={setTripBookingStatus}
            onSaveCurrentTrip={handleSaveCurrentTrip}
            onClearCurrentTrip={handleClearCurrentTrip}
            currentTrip={currentTrip}
            currentTripError={currentTripError}
            isSavingTrip={isSavingTrip}
            onBackToSearch={() => navigateTo({ name: "search" })}
          />
        ) : (
          <CurrentTripView
            currentTrip={currentTrip}
            currentTripError={currentTripError}
            currentTripSummary={currentTripSummary}
            currentTripSummaryError={currentTripSummaryError}
            currentTripEvents={currentTripEvents}
            isCurrentTripLoading={isCurrentTripLoading}
            isMarkingChecked={isMarkingChecked}
            onMarkChecked={handleMarkCurrentTripChecked}
            onBackToSearch={() => navigateTo({ name: "search" })}
          />
        )}
      </div>
    </div>
  );
}

function validateSearchFilters(filters: SearchFilters): string | null {
  if (!filters.location.trim()) {
    return "Add a location in Adjust filters before searching.";
  }
  if (!filters.skillLevel) {
    return "Choose a skill level in Adjust filters before searching.";
  }
  if (!filters.stars) {
    return "Choose a minimum quality in Adjust filters before searching.";
  }
  if (!filters.minPrice || !filters.maxPrice) {
    return "Add a budget range in Adjust filters before searching.";
  }

  const minPrice = Number(filters.minPrice);
  const maxPrice = Number(filters.maxPrice);
  if (Number.isNaN(minPrice) || Number.isNaN(maxPrice)) {
    return "Budget range must use numeric values.";
  }
  if (maxPrice < minPrice) {
    return "Max price must be greater than or equal to min price.";
  }

  if (filters.travelWindowMode === "month" && !filters.travelMonth) {
    return "Choose a month or switch Travel window back to Any time.";
  }
  if (filters.travelWindowMode === "dates") {
    if (!filters.tripStartDate || !filters.tripEndDate) {
      return "Choose both trip start and end dates, or switch Travel window back to Any time.";
    }
    if (filters.tripEndDate < filters.tripStartDate) {
      return "Trip end date must be on or after the start date.";
    }
  }

  return null;
}

function buildAppliedFilterChips(
  filters: SearchFilters,
): { key: AppliedFilterKey; label: string }[] {
  const chips: { key: AppliedFilterKey; label: string }[] = [];

  if (filters.location.trim()) {
    chips.push({ key: "location", label: filters.location.trim() });
  }
  if (filters.skillLevel) {
    chips.push({
      key: "skill_level",
      label: capitalize(filters.skillLevel),
    });
  }
  if (filters.minPrice || filters.maxPrice) {
    chips.push({
      key: "budget",
      label: `EUR ${filters.minPrice || "?"}-${filters.maxPrice || "?"}`,
    });
  }
  if (filters.stars) {
    chips.push({ key: "stars", label: `${filters.stars}+ stars` });
  }
  if (filters.liftDistance) {
    chips.push({
      key: "lift_distance",
      label: `${capitalize(filters.liftDistance)} lifts`,
    });
  }
  if (filters.budgetFlex) {
    chips.push({
      key: "budget_flex",
      label: `Budget flex ${filters.budgetFlex}`,
    });
  }
  if (filters.travelWindowMode === "month" && filters.travelMonth) {
    chips.push({
      key: "travel_window",
      label: formatMonth(Number(filters.travelMonth)),
    });
  }
  if (
    filters.travelWindowMode === "dates" &&
    filters.tripStartDate &&
    filters.tripEndDate
  ) {
    chips.push({
      key: "travel_window",
      label: `${formatDate(filters.tripStartDate)} to ${formatDate(
        filters.tripEndDate,
      )}`,
    });
  }

  return chips;
}

function SearchResultCard({
  result,
  rank,
  selected,
  onSelect,
}: {
  result: SearchResult;
  rank: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const confidencePercent = Math.round(result.recommendation_confidence * 100);
  const evidenceLabel =
    result.planning_evidence_count && result.planning_evidence_count > 0
      ? `${result.planning_evidence_count} weather window${
          result.planning_evidence_count === 1 ? "" : "s"
        }`
      : formatTrustCue(result.conditions_provenance);

  return (
    <button
      type="button"
      className={`group overflow-hidden rounded-[1.75rem] border text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-panel ${
        selected
          ? "border-alpine bg-white ring-2 ring-alpine/20"
          : "border-slate-200 bg-white/90 hover:border-alpine/40"
      }`}
      onClick={onSelect}
    >
      <div className="relative min-h-28 bg-[linear-gradient(135deg,_rgba(220,232,239,0.95),_rgba(244,239,231,0.92)_48%,_rgba(47,100,92,0.16))] p-4">
        <div className="absolute inset-x-0 bottom-0 h-16 bg-[radial-gradient(circle_at_35%_90%,_rgba(47,100,92,0.22),_transparent_34%)]" />
        <div className="relative flex items-start justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-ink px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-white">
              #{rank}
            </span>
            <span className="rounded-full bg-white/75 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-alpine">
              {result.region}
            </span>
          </div>
          <span className="rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-white">
            {formatAvailability(result.availability_status)}
          </span>
        </div>
      </div>

      <div className="p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="max-w-xl">
            <h3 className="font-display text-3xl font-semibold text-ink">
              {result.resort_name}
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {result.conditions_summary}
            </p>
            <p className="mt-3 text-sm font-semibold text-alpine">
              {evidenceLabel} backing this recommendation
            </p>
          </div>
          <dl className="grid min-w-[240px] grid-cols-2 gap-3 text-sm">
            <MetricCard
              selected={false}
              label="Confidence"
              value={`${confidencePercent}%`}
            />
            <MetricCard
              selected={false}
              label="Snow"
              value={capitalize(result.snow_confidence_label)}
            />
            <MetricCard
              selected={false}
              label="Stay base"
              value={result.selected_stay_base_name}
            />
            <MetricCard
              selected={false}
              label="Rental"
              value={result.rental_price_range}
            />
          </dl>
        </div>
        <div className="mt-5">
          <div className="h-2 overflow-hidden rounded-full bg-frost">
            <div
              className="h-full rounded-full bg-alpine transition-all"
              style={{ width: `${confidencePercent}%` }}
            />
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-slate-600">
              Stay in {result.selected_stay_base_name} -{" "}
              {capitalize(result.selected_stay_base_lift_distance)} lift access
            </span>
            <span className="font-semibold text-alpine transition group-hover:text-ink">
              View resort details
            </span>
          </div>
        </div>
      </div>
    </button>
  );
}

function SelectedResortPage({
  result,
  filters,
  tripBookingStatus,
  onTripBookingStatusChange,
  onSaveCurrentTrip,
  onClearCurrentTrip,
  currentTrip,
  currentTripError,
  isSavingTrip,
  onBackToSearch,
}: {
  result: SearchResult | null;
  filters: SearchFilters;
  tripBookingStatus: BookingStatus;
  onTripBookingStatusChange: (status: BookingStatus) => void;
  onSaveCurrentTrip: () => Promise<void>;
  onClearCurrentTrip: () => Promise<void>;
  currentTrip: CurrentTrip | null;
  currentTripError: string | null;
  isSavingTrip: boolean;
  onBackToSearch: () => void;
}) {
  if (!result) {
    return (
      <section className="mx-auto w-full max-w-3xl rounded-[2rem] border border-white/70 bg-white/85 p-8 shadow-panel backdrop-blur">
        <div
          data-testid="detail-route-fallback"
          className="rounded-[1.6rem] border border-dashed border-slate-300 bg-frost/60 p-8 text-center"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
            Resort detail
          </p>
          <h2 className="mt-4 font-display text-3xl font-semibold text-ink">
            Run a search first
          </h2>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            This detail page uses your latest search context: travel window,
            stay base, ranking evidence, and recommendation explanation.
          </p>
          <button
            type="button"
            className="mt-6 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
            onClick={onBackToSearch}
          >
            Go to search
          </button>
        </div>
      </section>
    );
  }

  return (
    <div
      data-testid="selected-resort-page"
      className="mx-auto grid w-full max-w-6xl gap-5"
    >
      <button
        type="button"
        className="w-fit rounded-full border border-slate-300 bg-white/70 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-alpine hover:text-alpine"
        onClick={onBackToSearch}
      >
        Back to search results
      </button>
      <section className="grid gap-5">
        <ResultDetails
          result={result}
          travelMonth={filters.travelWindowMode === "month" ? filters.travelMonth : ""}
          tripStartDate={
            filters.travelWindowMode === "dates" ? filters.tripStartDate : ""
          }
          tripEndDate={
            filters.travelWindowMode === "dates" ? filters.tripEndDate : ""
          }
          tripBookingStatus={tripBookingStatus}
          onTripBookingStatusChange={onTripBookingStatusChange}
          onSaveCurrentTrip={onSaveCurrentTrip}
          onClearCurrentTrip={onClearCurrentTrip}
          currentTrip={currentTrip}
          currentTripError={currentTripError}
          isSavingTrip={isSavingTrip}
        />
      </section>
    </div>
  );
}

function ResultDetails({
  result,
  travelMonth,
  tripStartDate,
  tripEndDate,
  tripBookingStatus,
  onTripBookingStatusChange,
  onSaveCurrentTrip,
  onClearCurrentTrip,
  currentTrip,
  currentTripError,
  isSavingTrip,
}: {
  result: SearchResult;
  travelMonth: SearchFilters["travelMonth"];
  tripStartDate: string;
  tripEndDate: string;
  tripBookingStatus: BookingStatus;
  onTripBookingStatusChange: (status: BookingStatus) => void;
  onSaveCurrentTrip: () => Promise<void>;
  onClearCurrentTrip: () => Promise<void>;
  currentTrip: CurrentTrip | null;
  currentTripError: string | null;
  isSavingTrip: boolean;
}) {
  const bookingHref = buildAccommodationBookingRedirectUrl(
    result,
    "selected_result_details",
  );
  const displayedNarrative =
    result.recommendation_narrative ??
    buildFallbackRecommendationNarrative(result);
  const isCurrentTripForSelection =
    currentTrip?.resort_id === result.resort_id &&
    currentTrip.selected_stay_base_name === result.selected_stay_base_name &&
    currentTrip.selected_ski_area_name === result.selected_ski_area_name;
  const hasTravelWindow = Boolean(
    travelMonth || (tripStartDate && tripEndDate),
  );
  const travelWindowLabel =
    tripStartDate && tripEndDate
      ? `${formatDate(tripStartDate)} to ${formatDate(tripEndDate)}`
      : travelMonth
        ? formatMonth(Number(travelMonth))
        : "Any time";

  return (
    <div data-testid="result-details" className="grid gap-5">
      <section className="overflow-hidden rounded-[2rem] border border-ink/10 bg-white shadow-panel">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr]">
          <div className="bg-[linear-gradient(135deg,_#18222f_0%,_#263548_54%,_#2f645c_100%)] p-6 text-white sm:p-8">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-white/12 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-100">
                Selected resort
              </span>
              <span className="rounded-full bg-ember/25 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-100">
                {result.region}
              </span>
              <span className="rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-white">
                {formatAvailability(result.availability_status)}
              </span>
            </div>
            <h2 className="mt-5 font-display text-5xl font-semibold leading-none">
              {result.resort_name}
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-200">
              Ski {result.selected_ski_area_name}, stay in{" "}
              {result.selected_stay_base_name}, and rent from{" "}
              {result.rental_name}. Conditions are{" "}
              {result.snow_confidence_label} and the current availability is{" "}
              {formatAvailability(result.availability_status).toLowerCase()}.
            </p>
            {displayedNarrative ? (
              <p className="mt-5 rounded-2xl bg-white/10 px-4 py-4 text-sm leading-6 text-slate-100">
                {displayedNarrative}
              </p>
            ) : null}
          </div>

          <div className="grid content-between gap-4 bg-frost/55 p-6 sm:p-8">
            <div className="grid gap-3 sm:grid-cols-2">
              <EvidenceStat
                label="Confidence"
                value={`${Math.round(result.recommendation_confidence * 100)}%`}
              />
              <EvidenceStat
                label="Snow signal"
                value={capitalize(result.snow_confidence_label)}
              />
              <EvidenceStat label="Travel window" value={travelWindowLabel} />
              <EvidenceStat
                label="Evidence"
                value={
                  result.planning_evidence_count
                    ? `${result.planning_evidence_count} windows`
                    : formatSourceType(result.conditions_provenance.source_type)
                }
              />
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white/85 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
                Primary action
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Continue with the selected stay option in{" "}
                {result.selected_stay_base_name}.
              </p>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                <a
                  href={bookingHref}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center justify-center rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white transition hover:bg-orange-700"
                >
                  Book accommodation
                </a>
                <button
                  type="button"
                  className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                  onClick={() => void onSaveCurrentTrip()}
                  disabled={isSavingTrip}
                >
                  {isSavingTrip ? "Saving..." : "Save trip"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {hasTravelWindow && result.planning_summary ? (
        <section className="rounded-[2rem] border border-alpine/15 bg-alpine p-6 text-white shadow-panel sm:p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">
            Planning for {travelWindowLabel}
          </p>
          <p className="mt-3 text-lg leading-8">{result.planning_summary}</p>
          <p className="mt-3 text-sm leading-6 text-emerald-50/90">
            {result.planning_provenance?.basis_summary ??
              (result.planning_evidence_count &&
              result.planning_evidence_count > 0
                ? `Using ${result.planning_evidence_count} historical weather record${result.planning_evidence_count === 1 ? "" : "s"} for this month together with seasonal patterns.`
                : "Using seasonal patterns and elevation because historical weather data is limited.")}
          </p>
        </section>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-2">
        <DetailPanel title="Current conditions" testId="current-conditions-section">
          <div className="rounded-2xl border border-slate-200 bg-frost/50 px-4 py-4 text-sm text-slate-700">
            <p className="font-semibold text-ink">
              {formatTrustCue(result.conditions_provenance)}
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <FactRow
                label="Source"
                value={
                  result.conditions_provenance.source_name ?? "Estimated fallback"
                }
              />
              <FactRow
                label="Freshness"
                value={formatFreshnessStatus(
                  result.conditions_provenance.freshness_status,
                )}
              />
              <FactRow
                label="Updated"
                value={formatTimestamp(result.conditions_provenance.updated_at)}
              />
              <FactRow
                label="Status"
                value={`${capitalize(result.snow_confidence_label)} snow - ${formatAvailability(
                  result.availability_status,
                )}`}
              />
            </div>
          </div>
        </DetailPanel>

        <DetailPanel title="Travel window">
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700">
            <div className="grid gap-3 sm:grid-cols-2">
              <FactRow label="Window" value={travelWindowLabel} />
              <FactRow
                label="Evidence type"
                value={
                  result.planning_provenance?.freshness_status === "historical"
                    ? "Historical weather records"
                    : "Seasonal estimate"
                }
              />
              <FactRow
                label="Latest weather record"
                value={formatTimestamp(result.planning_provenance?.updated_at ?? null)}
              />
              <FactRow
                label="Best months"
                value={
                  result.best_travel_months.length > 0
                    ? result.best_travel_months.map(formatMonth).join(", ")
                    : "Not enough data yet"
                }
              />
            </div>
          </div>
        </DetailPanel>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <DetailPanel title="Highlights">
          <div className="space-y-3">
            {result.explanation.highlights.map((item) => (
              <LightListItem key={item.label} label={item.label} tone="positive" />
            ))}
          </div>
        </DetailPanel>

        <DetailPanel title="Risks">
          {result.explanation.risks.length > 0 ? (
            <div className="space-y-3">
              {result.explanation.risks.map((item) => (
                <LightListItem key={item.label} label={item.label} tone="negative" />
              ))}
            </div>
          ) : (
            <p className="rounded-2xl bg-frost/60 px-4 py-4 text-sm text-slate-600">
              No major caveats were detected from the current ranking evidence.
            </p>
          )}
        </DetailPanel>
      </div>

      <DetailPanel title="Why this result">
        <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="rounded-2xl bg-frost/55 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
              Confidence
            </p>
            <p className="mt-2 text-4xl font-semibold text-ink">
              {Math.round(result.recommendation_confidence * 100)}%
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Combined from resort fit, snow signal, stay-base match, and
              current availability.
            </p>
          </div>
          <div className="space-y-3">
            {result.explanation.confidence_contributors.map((item) => (
              <LightListItem
                key={item.label}
                label={item.label}
                tone={item.direction === "positive" ? "positive" : "negative"}
              />
            ))}
          </div>
        </div>
      </DetailPanel>

      <div className="grid gap-5 lg:grid-cols-2">
        <DetailPanel title="Stay + Rental">
          <div className="grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
            <FactRow label="Ski area" value={result.selected_ski_area_name} />
            <FactRow label="Stay base" value={result.selected_stay_base_name} />
            <FactRow label="Stay-base price" value={result.stay_base_price_range} />
            <FactRow
              label="Lift distance"
              value={capitalize(result.selected_stay_base_lift_distance)}
            />
            <FactRow label="Rental" value={result.rental_name} />
            <FactRow label="Rental price" value={result.rental_price_range} />
          </div>
        </DetailPanel>

        <DetailPanel title="Current trip">
          <p className="text-sm leading-6 text-slate-600">
            Save this result as the trip context for companion status, event
            history, and later push-ready alerts.
          </p>
          <div className="mt-4 grid gap-3">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Booking status
              </span>
              <select
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                value={tripBookingStatus}
                onChange={(event) =>
                  onTripBookingStatusChange(event.target.value as BookingStatus)
                }
              >
                <option value="not_booked_yet">Not booked yet</option>
                <option value="booked_through_app">Booked through app</option>
                <option value="booked_elsewhere">Booked elsewhere</option>
              </select>
            </label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                className="rounded-full bg-ink px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                onClick={() => void onSaveCurrentTrip()}
                disabled={isSavingTrip}
              >
                {isSavingTrip ? "Saving..." : "Save as current trip"}
              </button>
              <button
                type="button"
                className="rounded-full border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:border-alpine hover:text-alpine disabled:cursor-not-allowed disabled:text-slate-400"
                onClick={() => void onClearCurrentTrip()}
                disabled={isSavingTrip || currentTrip === null}
              >
                Clear trip
              </button>
            </div>
          </div>
          {currentTripError ? (
            <p className="mt-3 text-sm text-amber-700">{currentTripError}</p>
          ) : null}
          {isCurrentTripForSelection ? (
            <span className="mt-4 inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
              Saved
            </span>
          ) : null}
          {currentTrip ? (
            <div className="mt-4 rounded-2xl bg-frost/60 px-4 py-3 text-sm text-slate-700">
              <p className="font-semibold text-ink">{currentTrip.resort_name}</p>
              <p className="mt-1">
                {currentTrip.selected_ski_area_name} -{" "}
                {currentTrip.selected_stay_base_name}
                {currentTrip.travel_month
                  ? ` - ${formatMonth(currentTrip.travel_month)}`
                  : ""}
              </p>
              <p className="mt-1 text-slate-600">
                {formatBookingStatus(currentTrip.booking_status)}
              </p>
            </div>
          ) : null}
        </DetailPanel>
      </div>
    </div>
  );
}

function CurrentTripView({
  currentTrip,
  currentTripError,
  currentTripSummary,
  currentTripSummaryError,
  currentTripEvents,
  isCurrentTripLoading,
  isMarkingChecked,
  onMarkChecked,
  onBackToSearch,
}: {
  currentTrip: CurrentTrip | null;
  currentTripError: string | null;
  currentTripSummary: CurrentTripSummary | null;
  currentTripSummaryError: string | null;
  currentTripEvents: CompanionEvent[];
  isCurrentTripLoading: boolean;
  isMarkingChecked: boolean;
  onMarkChecked: () => Promise<void>;
  onBackToSearch: () => void;
}) {
  if (currentTrip === null) {
    return (
      <section className="mx-auto w-full max-w-5xl rounded-[2rem] border border-white/70 bg-white/88 p-8 shadow-panel backdrop-blur">
        <div className="mx-auto max-w-2xl rounded-[1.8rem] border border-dashed border-slate-300 bg-[linear-gradient(180deg,_rgba(220,232,239,0.72),_rgba(255,255,255,0.78))] p-10 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-alpine/10 font-display text-2xl font-semibold text-alpine">
            S
          </div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
            Current trip
          </p>
          <h2 className="mt-4 font-display text-3xl font-semibold text-ink">
            Save a resort first
          </h2>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Your companion dashboard appears after you save a selected resort.
            It will track current conditions, trip-window relevance, and
            meaningful changes for that trip.
          </p>
          {currentTripError ? (
            <p className="mt-4 text-sm text-amber-700">{currentTripError}</p>
          ) : null}
          <button
            type="button"
            className="mt-6 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
            onClick={onBackToSearch}
          >
            Go to search
          </button>
        </div>
      </section>
    );
  }

  return (
    <div className="grid flex-1 gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <section className="rounded-[2rem] border border-white/70 bg-white/85 p-6 shadow-panel backdrop-blur">
        <div className="rounded-[1.6rem] bg-frost/75 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
            Current trip
          </p>
          <h2 className="mt-3 font-display text-3xl font-semibold text-ink">
            {currentTrip.resort_name}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {currentTrip.selected_ski_area_name} •{" "}
            {currentTrip.selected_stay_base_name}
            {currentTrip.travel_month
              ? ` • ${formatMonth(currentTrip.travel_month)}`
              : ""}
          </p>
          {currentTrip.trip_start_date && currentTrip.trip_end_date ? (
            <p className="mt-2 text-sm text-slate-600">
              {formatDate(currentTrip.trip_start_date)} to{" "}
              {formatDate(currentTrip.trip_end_date)}
            </p>
          ) : null}
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bg-white/85 px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Booking status
              </p>
              <p className="mt-2 text-lg font-semibold text-ink">
                {formatBookingStatus(currentTrip.booking_status)}
              </p>
            </div>
            <div className="rounded-2xl bg-white/85 px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Comparison basis
              </p>
              <p className="mt-2 text-lg font-semibold text-ink">
                {currentTripSummary?.comparison_basis.label ?? "Loading..."}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                {formatTimestamp(
                  currentTripSummary?.comparison_basis.baseline_at ??
                    currentTrip.last_checked_at ??
                    currentTrip.created_at,
                )}
              </p>
            </div>
            <div className="rounded-2xl bg-white/85 px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Trip relevance
              </p>
              <p className="mt-2 text-lg font-semibold text-ink">
                {currentTripSummary?.companion_status?.trip_window_label ??
                  "Loading..."}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                {currentTripSummary?.companion_status?.eligibility_reason ??
                  "Companion status will update when summary loads."}
              </p>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              onClick={() => void onMarkChecked()}
              disabled={isMarkingChecked}
            >
              {isMarkingChecked ? "Marking..." : "Mark checked"}
            </button>
            <p className="text-sm text-slate-600">
              Baseline advances only when you explicitly mark the trip as checked.
            </p>
          </div>
          {currentTripSummaryError ? (
            <p className="mt-4 text-sm text-amber-700">{currentTripSummaryError}</p>
          ) : null}
        </div>
      </section>

      <section className="rounded-[2rem] border border-ink/10 bg-ink p-6 text-white shadow-panel">
        {isCurrentTripLoading ? (
          <div className="flex min-h-[420px] items-center justify-center rounded-[1.5rem] border border-white/10 bg-white/5 p-8 text-sm text-slate-200">
            Loading current trip summary...
          </div>
        ) : currentTripSummary ? (
          <div className="space-y-4">
            <Panel title="Current conditions">
              <div className="space-y-4 text-sm text-slate-200">
                <p className="rounded-2xl bg-white/5 px-4 py-4 text-sm leading-6 text-slate-100">
                  {currentTripSummary.current_conditions.weather_summary}
                </p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <DetailRow
                    label="Signal"
                    value={formatTrustCue(
                      currentTripSummary.current_conditions_provenance,
                    )}
                  />
                  <DetailRow
                    label="Status"
                    value={`${capitalize(currentTripSummary.current_conditions.snow_confidence_label)} snow • ${formatAvailability(
                      currentTripSummary.current_conditions.availability_status,
                    )}`}
                  />
                  <DetailRow
                    label="Source"
                    value={
                      currentTripSummary.current_conditions_provenance.source_name ??
                      "Estimated fallback"
                    }
                  />
                  <DetailRow
                    label="Updated"
                    value={formatTimestamp(
                      currentTripSummary.current_conditions_provenance.updated_at,
                    )}
                  />
                </div>
              </div>
            </Panel>

            <Panel title="What changed since last check">
              <div className="space-y-4 text-sm text-slate-200">
                <div className="rounded-2xl bg-white/5 px-4 py-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
                    {currentTripSummary.comparison_basis.label}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-100">
                    {currentTripSummary.delta.summary}
                  </p>
                </div>
                {currentTripSummary.delta.changes.length > 0 ? (
                  <div className="space-y-3">
                    {currentTripSummary.delta.changes.map((change) => (
                      <ListItem key={change} label={change} tone="positive" />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-300">
                    {currentTripSummary.delta.status === "insufficient_history"
                      ? "Not enough earlier history to compare yet."
                      : "No material conditions changes surfaced yet."}
                  </p>
                )}
              </div>
            </Panel>
            <Panel title="Companion history">
              <div className="space-y-3 text-sm text-slate-200">
                {currentTripEvents.length > 0 ? (
                  currentTripEvents.map((event) => (
                    <div
                      key={event.event_id}
                      className="rounded-2xl bg-white/5 px-4 py-4"
                    >
                      <p className="font-semibold text-slate-100">
                        {event.summary}
                      </p>
                      <p className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-400">
                        {event.actionable ? "Actionable" : "Informational"} •{" "}
                        {formatTimestamp(event.recorded_at)}
                      </p>
                      {event.changes.length > 0 ? (
                        <div className="mt-3 space-y-2">
                          {event.changes.map((change) => (
                            <ListItem
                              key={`${event.event_id}-${change}`}
                              label={change}
                              tone={event.actionable ? "positive" : "negative"}
                            />
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-300">
                    No companion events have been recorded for this trip yet.
                  </p>
                )}
              </div>
            </Panel>
          </div>
        ) : (
          <div className="flex min-h-[420px] items-center justify-center rounded-[1.5rem] border border-white/10 bg-white/5 p-8 text-center text-sm text-slate-200">
            Companion details are not available yet.
          </div>
        )}
      </section>
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[1.5rem] bg-white/5 p-5">
      <h3 className="font-display text-xl font-semibold">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function DetailPanel({
  title,
  children,
  testId,
}: {
  title: string;
  children: ReactNode;
  testId?: string;
}) {
  return (
    <section
      data-testid={testId}
      className="rounded-[2rem] border border-slate-200 bg-white/90 p-5 shadow-sm sm:p-6"
    >
      <h3 className="font-display text-2xl font-semibold text-ink">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function EvidenceStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/85 px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold text-ink">{value}</p>
    </div>
  );
}

function FactRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </p>
      <p className="mt-1 font-semibold text-ink">{value}</p>
    </div>
  );
}

function LightListItem({
  label,
  tone,
}: {
  label: string;
  tone: "positive" | "negative";
}) {
  return (
    <div className="flex items-start gap-3 rounded-2xl bg-frost/60 px-4 py-3 text-sm text-slate-700">
      <span
        className={`mt-1 h-2.5 w-2.5 rounded-full ${
          tone === "positive" ? "bg-emerald-500" : "bg-amber-500"
        }`}
      />
      <span>{label}</span>
    </div>
  );
}

function MetricCard({
  label,
  value,
  selected,
}: {
  label: string;
  value: string;
  selected: boolean;
}) {
  return (
    <div
      className={`rounded-2xl px-3 py-3 ${
        selected ? "bg-white/10" : "bg-frost text-ink"
      }`}
    >
      <dt className={`text-xs font-semibold uppercase tracking-[0.14em] ${selected ? "text-slate-200" : "text-slate-500"}`}>
        {label}
      </dt>
      <dd className="mt-2 text-sm font-semibold">{value}</dd>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[110px_1fr]">
      <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
        {label}
      </span>
      <span>{value}</span>
    </div>
  );
}

function formatMonth(month: number): string {
  return (
    monthOptions.find((option) => option.value === month)?.label ?? `Month ${month}`
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatTrustCue(provenance: ProvenanceInfo): string {
  const updatedText =
    provenance.updated_at !== null
      ? `Updated ${formatRelativeTime(provenance.updated_at)}`
      : formatFreshnessStatus(provenance.freshness_status);
  return `${formatSourceType(provenance.source_type)} • ${updatedText}`;
}

function buildFallbackRecommendationNarrative(result: SearchResult): string {
  const snowText = `${capitalize(result.snow_confidence_label)} snow confidence`;
  const availabilityText =
    result.availability_status === "open"
      ? "open operations"
      : result.availability_status === "limited"
        ? "limited operations right now"
        : result.availability_status === "temporarily_closed"
          ? "temporary closure right now"
          : "out-of-season conditions";
  const stayBaseText =
    result.selected_stay_base_lift_distance === "near"
      ? "a near-lift stay base"
      : result.selected_stay_base_lift_distance === "medium"
        ? "a practical stay base"
        : "a stay base farther from the lift";

  if (result.availability_status === "open") {
    return `${snowText}, ${availabilityText}, and ${stayBaseText}.`;
  }

  return `${snowText}, but ${availabilityText}.`;
}

function ListItem({
  label,
  tone,
}: {
  label: string;
  tone: "positive" | "negative";
}) {
  return (
    <div className="flex items-start gap-3 rounded-2xl bg-white/5 px-4 py-3 text-sm text-slate-100">
      <span
        className={`mt-1 h-2.5 w-2.5 rounded-full ${
          tone === "positive" ? "bg-emerald-300" : "bg-amber-300"
        }`}
      />
      <span>{label}</span>
    </div>
  );
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatSourceType(value: ProvenanceInfo["source_type"]) {
  return capitalize(value);
}

function formatFreshnessStatus(value: ProvenanceInfo["freshness_status"]) {
  const labels: Record<ProvenanceInfo["freshness_status"], string> = {
    fresh: "Fresh",
    stale: "Stale",
    historical: "Historical",
    unknown: "Unknown",
  };
  return labels[value];
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatRelativeTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "unknown";
  }

  const diffMs = date.getTime() - Date.now();
  const diffHours = Math.round(diffMs / (1000 * 60 * 60));
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

  if (Math.abs(diffHours) < 24) {
    return formatter.format(diffHours, "hour");
  }

  const diffDays = Math.round(diffHours / 24);
  return formatter.format(diffDays, "day");
}

function formatAvailability(value: SearchResult["availability_status"]) {
  return value.replace(/_/g, " ");
}

function formatBookingStatus(value: BookingStatus) {
  return value.replace(/_/g, " ");
}

export default App;
