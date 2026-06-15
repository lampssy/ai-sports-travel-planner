import {
  type Dispatch,
  FormEvent,
  ReactNode,
  type SetStateAction,
  useEffect,
  useState,
} from "react";

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
import { EvidenceQualityBadge } from "./ui/EvidenceQualityBadge";
import { SnowcastLogo } from "./ui/SnowcastLogo";
import { TripEntityStack } from "./ui/TripEntityStack";
import {
  evidenceQualityCopy,
  initialHeroCopy,
  snowRiskSignal,
  type EvidenceQualityMode,
} from "./ui/snowcastCopy";
import type {
  BookingStatus,
  CompanionEvent,
  CurrentTrip,
  CurrentTripSummary,
  ParsedQueryResponse,
  ProvenanceInfo,
  SearchFilters,
  SearchResult,
  TripClarification,
  TripClarificationOption,
  TripContext,
  TravelEffort,
  TripOption,
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
  travelWindowMode: "month",
  travelMonth: 3,
  tripStartDate: "",
  tripEndDate: "",
  originText: "",
  maxDriveHours: "",
  travelTolerance: "",
};

const emptyTripContext: TripContext = {
  budget_mode: null,
  budget_min: null,
  budget_max: null,
  party_size: null,
  trip_duration_nights: null,
  origin_text: null,
};

const storageKey = "snowcast-refine-open";
const searchStateStorageKey = "snowcast-search-state";
const tripFitExplanation =
  "Trip fit combines snow outlook, stay-base match, travel effort, budget fit, and evidence quality.";
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
  | "travel_window"
  | "origin"
  | "max_drive"
  | "travel_tolerance";

interface StoredSearchState {
  tripBrief: string;
  lastParsedTripBrief: string;
  parsedQuery: ParsedQueryResponse | null;
  tripContext: TripContext;
  clarifications: TripClarification[];
  assumptions: string[];
  filters: SearchFilters;
  results: SearchResult[];
  selectedResultId: string | null;
  hasSearched: boolean;
}

const emptyStoredSearchState: StoredSearchState = {
  tripBrief: "",
  lastParsedTripBrief: "",
  parsedQuery: null,
  tripContext: emptyTripContext,
  clarifications: [],
  assumptions: [],
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
      tripContext:
        parsed.tripContext && typeof parsed.tripContext === "object"
          ? { ...emptyTripContext, ...parsed.tripContext }
          : emptyTripContext,
      clarifications: Array.isArray(parsed.clarifications)
        ? parsed.clarifications
        : [],
      assumptions: Array.isArray(parsed.assumptions)
        ? parsed.assumptions.filter(
            (assumption): assumption is string => typeof assumption === "string",
          )
        : [],
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
  const [tripContext, setTripContext] = useState<TripContext>(
    initialSearchState.tripContext,
  );
  const [clarifications, setClarifications] = useState<TripClarification[]>(
    initialSearchState.clarifications,
  );
  const [assumptions, setAssumptions] = useState<string[]>(
    initialSearchState.assumptions,
  );
  const [filters, setFilters] = useState<SearchFilters>(initialSearchState.filters);
  const [results, setResults] = useState<SearchResult[]>(
    initialSearchState.results,
  );
  const [selectedResultId, setSelectedResultId] = useState<string | null>(
    initialSearchState.selectedResultId,
  );
  const [activeTripOptionId, setActiveTripOptionId] = useState<string | null>(
    null,
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
  const [isRefineDrawerOpen, setIsRefineDrawerOpen] = useState(false);
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
      tripContext,
      clarifications,
      assumptions,
      filters,
      results,
      selectedResultId,
      hasSearched,
    });
  }, [
    tripBrief,
    lastParsedTripBrief,
    parsedQuery,
    tripContext,
    clarifications,
    assumptions,
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
  const activeTripOption = selectedResult
    ? findTripOption(selectedResult, activeTripOptionId)
    : null;
  const showRecommendationsPanel =
    hasSearched || isLoading || Boolean(error) || results.length > 0;
  const showEditorialEntry = route.name === "search" && !showRecommendationsPanel;
  const searchRouteLayoutClass = showRecommendationsPanel
    ? "grid w-full flex-1 gap-6 xl:grid-cols-[22rem_minmax(0,1fr)]"
    : "relative z-10 mx-auto -mt-36 grid w-full max-w-[78rem] flex-1 pb-8 sm:-mt-28 lg:-mt-32";
  const searchPanelClass = showRecommendationsPanel
    ? "h-fit rounded-[1.75rem] border border-line bg-white/92 p-5 shadow-panel backdrop-blur sm:p-6"
    : "rounded-[1.85rem] border border-white/85 bg-white p-5 shadow-premium sm:p-6 lg:p-7";
  const searchTravelWindowLabel = getTravelWindowLabelFromFilters(filters);
  const weakSearchGuidance = getSearchWeakGuidance(results, filters);

  useEffect(() => {
    if (!selectedResult) {
      setActiveTripOptionId(null);
      return;
    }

    setActiveTripOptionId(getTopTripOption(selectedResult).option_id);
  }, [selectedResult?.resort_id, selectedResult?.top_option?.option_id]);

  useEffect(() => {
    if (
      currentTrip &&
      selectedResult &&
      activeTripOption &&
      currentTrip.resort_id === selectedResult.resort_id &&
      currentTrip.selected_stay_base_name === activeTripOption.stay_base_name &&
      currentTrip.selected_ski_area_name === activeTripOption.ski_area_name
    ) {
      setTripBookingStatus(currentTrip.booking_status);
      return;
    }

    setTripBookingStatus("not_booked_yet");
  }, [currentTrip, selectedResult, activeTripOption]);

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

    try {
      const trimmedBrief = tripBrief.trim();
      if (trimmedBrief && trimmedBrief !== lastParsedTripBrief) {
        setIsParsing(true);
        try {
          const parsed = await parseTripBrief(trimmedBrief);
          setParsedQuery(parsed);
          setTripContext(parsed.trip_context ?? emptyTripContext);
          setClarifications(parsed.clarifications ?? []);
          setAssumptions(parsed.assumptions ?? []);
          setLastParsedTripBrief(trimmedBrief);
          nextFilters = mergeParsedFilters(defaultFilters, parsed);
          setFilters(nextFilters);
        } catch (caughtError) {
          setResults([]);
          setSelectedResultId(null);
          const message =
            caughtError instanceof Error
              ? caughtError.message
              : "Unable to interpret trip brief.";
          setParseError(message);
          return;
        }
      }

      const validationError = validateSearchFilters(nextFilters);
      if (validationError) {
        setResults([]);
        setSelectedResultId(null);
        setHasSearched(true);
        setError(validationError);
        setIsRefineDrawerOpen(true);
        return;
      }

      setHasSearched(true);
      try {
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
        setError(message);
      }
    } catch (caughtError) {
      setResults([]);
      setSelectedResultId(null);
      const message =
        caughtError instanceof Error
          ? caughtError.message
          : "Something went wrong while loading results.";
      setError(message);
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
    if (
      parsed.trip_context &&
      Object.prototype.hasOwnProperty.call(parsed.trip_context, "origin_text") &&
      parsed.trip_context.origin_text !== undefined
    ) {
      nextFilters.originText = parsed.trip_context.origin_text ?? "";
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

  function applyClarificationOption(
    clarificationId: string,
    option: TripClarificationOption,
  ) {
    setTripContext((current) => ({
      ...current,
      ...option.context_patch,
    }));
    if (clarificationId === "travel-origin" || option.id === "add-origin") {
      setIsAdvancedOpen(true);
      setIsRefineDrawerOpen(true);
    }
    if (
      Object.prototype.hasOwnProperty.call(option.context_patch, "origin_text") &&
      option.context_patch.origin_text !== undefined
    ) {
      setIsAdvancedOpen(true);
      setIsRefineDrawerOpen(true);
      setFilters((current) => ({
        ...current,
        originText: option.context_patch.origin_text ?? "",
      }));
    }
    setClarifications((current) =>
      current.filter((clarification) => clarification.id !== clarificationId),
    );

    if (!option.filter_patch) {
      return;
    }

    setIsAdvancedOpen(true);
    setIsRefineDrawerOpen(true);
    setFilters((current) => ({
      ...current,
      minPrice:
        option.filter_patch?.min_price !== undefined &&
        option.filter_patch.min_price !== null
          ? String(option.filter_patch.min_price)
          : current.minPrice,
      maxPrice:
        option.filter_patch?.max_price !== undefined &&
        option.filter_patch.max_price !== null
          ? String(option.filter_patch.max_price)
          : current.maxPrice,
    }));
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
    if (showRecommendationsPanel) {
      setIsRefineDrawerOpen(true);
    }
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
      if (key === "origin") {
        return { ...current, originText: "" };
      }
      if (key === "max_drive") {
        return { ...current, maxDriveHours: "" };
      }
      if (key === "travel_tolerance") {
        return { ...current, travelTolerance: "" };
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
    if (!selectedResult || !activeTripOption) {
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
        selected_ski_area_id: activeTripOption.ski_area_id,
        selected_ski_area_name: activeTripOption.ski_area_name,
        selected_stay_base_name: activeTripOption.stay_base_name,
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
    <div className="min-h-screen bg-[radial-gradient(circle_at_12%_0%,_rgba(255,95,143,0.16),_transparent_28%),radial-gradient(circle_at_90%_8%,_rgba(11,95,184,0.14),_transparent_26%),linear-gradient(180deg,_#f8fbff_0%,_#edf6fb_58%,_#f8fbff_100%)] text-ink">
      <div className="mx-auto flex min-h-screen max-w-[94rem] flex-col px-4 py-5 sm:px-7 lg:px-10">
        <header
          className={`overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_86%_10%,_rgba(255,95,143,0.14),_transparent_30%),linear-gradient(135deg,_#021a35_0%,_#062247_58%,_#111b3d_100%)] text-white shadow-premium ${
            showEditorialEntry
              ? "mb-0 p-5 pb-28 sm:p-7 sm:pb-36 lg:px-10 lg:pb-44 lg:pt-10"
              : "mb-7 p-3 sm:p-4"
          }`}
        >
          <div
            className={`grid gap-4 ${
              showEditorialEntry
                ? "lg:grid-cols-[1fr_auto] lg:items-start"
                : "lg:grid-cols-[auto_1fr_auto] lg:items-center"
            }`}
          >
            <SnowcastLogo compact={!showEditorialEntry} />
            {showEditorialEntry ? (
              <div className="inline-flex h-fit w-fit rounded-full border border-white/15 bg-white/8 p-1 backdrop-blur">
                <button
                  type="button"
                  className="rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-midnight shadow-sm transition"
                  onClick={() => navigateTo({ name: "search" })}
                >
                  Search
                </button>
                <button
                  type="button"
                  className="rounded-full px-5 py-2.5 text-sm font-semibold text-white/78 transition hover:bg-white/10"
                  onClick={() => navigateTo({ name: "current_trip" })}
                >
                  Current trip
                </button>
              </div>
            ) : (
              <>
                {route.name === "search" ? (
                  <form
                    className="grid min-w-0 gap-2 rounded-2xl border border-white/14 bg-white/8 p-2 backdrop-blur sm:grid-cols-[minmax(0,1fr)_auto]"
                    noValidate
                    onSubmit={handleSubmit}
                  >
                    <label className="min-w-0">
                      <span className="sr-only">Trip brief</span>
                      <input
                        className="w-full rounded-xl border border-white/15 bg-midnight/35 px-4 py-3 text-sm font-semibold text-white outline-none transition placeholder:text-white/45 focus:border-alpineBlue focus:ring-2 focus:ring-alpineBlue/35"
                        value={tripBrief}
                        onChange={(event) => setTripBrief(event.target.value)}
                        placeholder="Search by trip intent"
                      />
                      <span className="mt-1 block px-2 text-xs text-white/58">
                        Snow window, stay fit, travel effort, and evidence.
                      </span>
                    </label>
                    <button
                      type="submit"
                      className="rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-midnight shadow-sm transition hover:bg-snow disabled:cursor-not-allowed disabled:bg-white/45"
                      disabled={isLoading || isParsing}
                    >
                      {isParsing
                        ? "Interpreting..."
                        : isLoading
                          ? "Searching..."
                          : "Find resorts"}
                    </button>
                  </form>
                ) : (
                  <div className="min-w-0 rounded-2xl border border-white/14 bg-white/8 px-4 py-3 backdrop-blur">
                    <p className="truncate text-sm font-semibold text-white">
                      {tripBrief.trim() || "Search by trip intent"}
                    </p>
                    <p className="mt-1 text-xs text-white/58">
                      Snow window, stay fit, travel effort, and evidence.
                    </p>
                  </div>
                )}
                <div className="flex flex-wrap items-center justify-start gap-2 lg:justify-end">
                  <div className="rounded-2xl border border-amber/25 bg-amber/10 px-3 py-2 text-sm text-amber-100">
                    <p className="font-semibold">{snowRiskSignal.title}</p>
                    <p className="text-xs text-amber-50/78">
                      {snowRiskSignal.body}
                    </p>
                  </div>
                  <div className="inline-flex h-fit rounded-full border border-white/15 bg-white/8 p-1 backdrop-blur">
                    {route.name !== "search" ? (
                      <button
                        type="button"
                        className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                          route.name !== "current_trip"
                            ? "bg-white text-midnight shadow-sm"
                            : "text-white/78 hover:bg-white/10"
                        }`}
                        onClick={() => navigateTo({ name: "search" })}
                      >
                        Search
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                        route.name === "current_trip"
                          ? "bg-white text-midnight shadow-sm"
                          : "text-white/78 hover:bg-white/10"
                      }`}
                      onClick={() => navigateTo({ name: "current_trip" })}
                    >
                      Current trip
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {showEditorialEntry ? (
            <div className="mt-10 grid gap-6 sm:gap-8 lg:mt-16 lg:grid-cols-[minmax(0,1fr)_24rem] lg:items-center">
              <div className="max-w-4xl">
                <p className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-alpenglow">
                  Snow-aware trip planning
                </p>
                <h1 className="max-w-4xl font-display text-[2.85rem] font-semibold leading-[0.92] tracking-normal sm:text-6xl lg:text-7xl">
                  Book the mountain,
                  <br />
                  not the guesswork.
                </h1>
                <p className="mt-6 max-w-2xl text-base leading-7 text-slate-200 sm:text-lg">
                  {initialHeroCopy.body}
                </p>
              </div>
              <div className="rounded-[1.5rem] border border-white/24 bg-white/5 p-4 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur sm:p-6">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-100/70">
                  Planning signal
                </p>
                <div className="mt-4 flex gap-4 sm:mt-5">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-alpenglow/45 bg-alpenglow/10 text-alpenglow">
                    <SnowSignalIcon className="h-6 w-6" />
                  </span>
                  <p className="font-display text-xl font-semibold leading-tight sm:text-2xl">
                    {snowRiskSignal.title}
                  </p>
                </div>
                <div className="my-4 h-px bg-white/18 sm:my-5" />
                <p className="text-sm leading-6 text-white/76">
                  {snowRiskSignal.body}
                </p>
              </div>
            </div>
          ) : null}
        </header>

        {route.name === "search" ? (
          <div className={searchRouteLayoutClass}>
            {showRecommendationsPanel ? (
              <SearchDecisionRail
                filters={filters}
                parsedQuery={parsedQuery}
                tripContext={tripContext}
                clarifications={clarifications}
                assumptions={assumptions}
                selectedResult={selectedResult}
                resultsCount={results.length}
                onRefine={() => setIsRefineDrawerOpen(true)}
                onRemoveFilter={handleRemoveAppliedFilter}
                onApplyClarification={applyClarificationOption}
              />
            ) : (
              <section className={searchPanelClass}>
                <form className="space-y-5" noValidate onSubmit={handleSubmit}>
                  <div>
                    <label
                      htmlFor="trip-brief"
                      className="text-sm font-semibold text-slate-800"
                    >
                      What are you looking for?
                    </label>
                    <div className="mt-3 grid gap-3 rounded-[1.35rem] border border-slate-300 bg-white px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] transition focus-within:border-alpineBlue focus-within:ring-4 focus-within:ring-alpineBlue/10 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
                      <textarea
                        id="trip-brief"
                        className="min-h-20 w-full resize-y border-0 bg-transparent p-0 text-base leading-7 text-ink outline-none placeholder:text-slate-400 sm:min-h-20 sm:text-lg"
                        value={tripBrief}
                        onChange={(event) => setTripBrief(event.target.value)}
                        placeholder="Cheap March ski trip in France for intermediates, close to the lift."
                      />
                      <button
                        type="submit"
                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-midnight px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-midnightSoft disabled:cursor-not-allowed disabled:bg-slate-400 sm:min-w-40"
                        disabled={isLoading || isParsing}
                      >
                        <SearchIcon className="h-5 w-5" />
                        {isParsing
                          ? "Interpreting..."
                          : isLoading
                            ? "Searching..."
                            : "Find resorts"}
                      </button>
                    </div>
                  </div>

                  {parseError ? (
                    <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                      {parseError}
                    </div>
                  ) : null}

                  {parsedQuery ? (
                    <div className="rounded-2xl border border-slate-200 bg-ice/70 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpineBlue">
                        What we understood
                      </p>
                      <p className="mt-2 text-sm text-slate-600">
                        Search confidence:{" "}
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

                  {clarifications.length > 0 ? (
                    <div className="grid gap-3">
                      {clarifications.map((clarification) => (
                        <div
                          key={clarification.id}
                          className="rounded-2xl border border-ember/20 bg-white/90 p-4"
                        >
                          <p className="text-sm font-semibold text-ink">
                            {clarification.question}
                          </p>
                          <p className="mt-1 text-sm text-slate-600">
                            {clarification.reason}
                          </p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {clarification.options.map((option) => (
                              <button
                                key={option.id}
                                type="button"
                                className="rounded-full border border-alpine/30 bg-frost px-3 py-2 text-sm font-semibold text-alpine transition hover:border-alpine hover:bg-white"
                                onClick={() =>
                                  applyClarificationOption(
                                    clarification.id,
                                    option,
                                  )
                                }
                              >
                                {option.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  {assumptions.length > 0 ? (
                    <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                        Assumptions
                      </p>
                      <ul className="mt-2 space-y-1 text-sm text-slate-600">
                        {assumptions.map((assumption) => (
                          <li key={assumption}>{assumption}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <div className="flex flex-wrap items-center gap-3">
                    {buildAppliedFilterChips(filters).map((chip) => (
                      <button
                        key={chip.key}
                        type="button"
                        className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-ink shadow-sm transition hover:border-alpineBlue hover:text-alpineBlue"
                        onClick={() => handleRemoveAppliedFilter(chip.key)}
                        aria-label={`Remove ${chip.label}`}
                      >
                        <ChipIcon filterKey={chip.key} className="h-4 w-4" />
                        {chip.label}
                        <span className="text-slate-400" aria-hidden="true">
                          x
                        </span>
                      </button>
                    ))}
                    {tripContext.budget_mode ? (
                      <span className="inline-flex items-center gap-2 rounded-full border border-ember/20 bg-amber-50 px-4 py-2.5 text-sm font-semibold text-ember">
                        Budget: {formatBudgetMode(tripContext.budget_mode)}
                      </span>
                    ) : null}
                    <button
                      type="button"
                      className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-alpineBlue hover:text-alpineBlue"
                      onClick={() => setIsAdvancedOpen((current) => !current)}
                      aria-expanded={isAdvancedOpen}
                    >
                      <SlidersIcon className="h-4 w-4" />
                      Adjust filters
                    </button>
                  </div>

                  <InitialRecommendationPreview />

                  {isAdvancedOpen ? (
                    <div className="grid gap-4 rounded-[1.5rem] border border-slate-200 bg-ice/70 p-4 md:grid-cols-2">
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

                    <label className="space-y-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Travel origin
                      </span>
                      <input
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        value={filters.originText}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            originText: event.target.value,
                          }))
                        }
                        placeholder="Munich"
                      />
                    </label>

                    <label className="space-y-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Max drive hours
                      </span>
                      <input
                        type="number"
                        min="0.1"
                        step="0.5"
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        inputMode="decimal"
                        value={filters.maxDriveHours}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            maxDriveHours: event.target.value,
                          }))
                        }
                        placeholder="3.5"
                      />
                    </label>

                    <label className="space-y-2 md:col-span-2">
                      <span className="text-sm font-semibold text-slate-700">
                        Travel tolerance
                      </span>
                      <select
                        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                        value={filters.travelTolerance}
                        onChange={(event) =>
                          setFilters((current) => ({
                            ...current,
                            travelTolerance:
                              event.target.value as SearchFilters["travelTolerance"],
                          }))
                        }
                      >
                        <option value="">No preference</option>
                        <option value="short">Short drive</option>
                        <option value="medium">Medium drive</option>
                        <option value="flexible">Flexible drive</option>
                      </select>
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
                          ["1", "Budget+"],
                          ["2", "Standard+"],
                          ["3", "Premium"],
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
                </form>
              </section>
            )}

            {showRecommendationsPanel ? (
            <section className="rounded-[2rem] border border-white/70 bg-white/88 p-5 shadow-panel backdrop-blur sm:p-6">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.18em] text-warning">
                    Ranked by trip fit and evidence
                  </p>
                  <h2 className="mt-2 font-display text-3xl font-semibold">
                    Recommended ski trips
                  </h2>
                  <p className="text-sm text-slate-600">
                    {filters.travelWindowMode === "dates" &&
                    filters.tripStartDate &&
                    filters.tripEndDate
                      ? `Best ski trips for ${formatDate(filters.tripStartDate)} to ${formatDate(filters.tripEndDate)}. The selected stay base stays selected if it still fits.`
                      : filters.travelWindowMode === "month" && filters.travelMonth
                      ? `Best ski trips for ${formatMonth(Number(filters.travelMonth))}. The selected stay base stays selected if it still fits.`
                      : "Ski trips are ranked by trip fit, snow outlook, stay-base match, travel effort, and evidence quality."}
                  </p>
                </div>
                <span className="rounded-full bg-ice px-4 py-2 text-sm font-semibold text-pine">
                  {results.length} group{results.length === 1 ? "" : "s"}
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
                    Comparing ski trips...
                  </p>
                  <p className="mx-auto mt-3 max-w-md leading-6">
                    Snowcast is ranking destination, ski area, stay base, snow
                    outlook, travel effort, and evidence quality for the current
                    filters.
                  </p>
                </div>
              ) : null}

              {!error && !isLoading && hasSearched && results.length === 0 ? (
                <div className="rounded-[1.75rem] border border-dashed border-slate-300 bg-frost/50 px-6 py-12 text-center text-sm text-slate-600">
                  <p className="font-display text-2xl font-semibold text-ink">
                    No matching ski trips yet.
                  </p>
                  <p className="mx-auto mt-3 max-w-md leading-6">
                    Try broadening the location, budget, quality, or travel
                    window. Snowcast will keep the filters visible so you can
                    adjust the search without starting over.
                  </p>
                </div>
              ) : null}

              {weakSearchGuidance ? (
                <div className="mb-4 rounded-[1.5rem] border border-amber/30 bg-amber/10 px-5 py-4 text-sm text-slate-700">
                  <p className="font-semibold text-warning">
                    {weakSearchGuidance.title}
                  </p>
                  <p className="mt-1 leading-6">{weakSearchGuidance.body}</p>
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
                      travelWindowLabel={searchTravelWindowLabel}
                      onSelect={() => handleSelectResult(result.resort_id)}
                    />
                  );
                })}
              </div>
            </section>
            ) : null}

            {showRecommendationsPanel && isRefineDrawerOpen ? (
              <RefineDrawer
                filters={filters}
                isBusy={isLoading || isParsing}
                onClose={() => setIsRefineDrawerOpen(false)}
                onFiltersChange={setFilters}
                onSubmit={handleSubmit}
                onTravelWindowModeChange={handleTravelWindowModeChange}
              />
            ) : null}
          </div>
        ) : route.name === "resort" ? (
          <SelectedResortPage
            result={selectedResult}
            activeOption={activeTripOption}
            onActiveOptionChange={setActiveTripOptionId}
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

type IconProps = {
  className?: string;
};

function InitialRecommendationPreview() {
  return (
    <div className="rounded-[1.35rem] border border-slate-200 bg-white p-4 shadow-[0_1px_0_rgba(7,24,47,0.04)]">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-alpineBlue">
        Example recommendation
      </p>
      <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,1fr)_40rem] lg:items-start">
        <div className="flex items-start gap-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-50 font-display text-xl font-semibold text-alpineBlue">
            #1
          </span>
          <div>
            <h2 className="font-display text-3xl font-semibold tracking-normal text-ink">
              Cervinia
            </h2>
            <p className="mt-1 text-lg text-muted">Stay in Breuil-Cervinia</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <ExampleMetric
            icon={<SnowflakeIcon className="h-6 w-6" />}
            label="Snow outlook"
            value="Good"
            className="bg-emerald-50 text-pine"
          />
          <ExampleMetric
            icon={<ShieldCheckIcon className="h-6 w-6" />}
            label="Evidence"
            value="Archive-backed"
            className="bg-blue-50 text-alpineBlue"
          />
          <ExampleMetric
            icon={<TrendIcon className="h-6 w-6" />}
            label="Trip fit"
            value="92%"
            className="bg-violet-50 text-indigo-700"
          />
        </div>
      </div>

      <div className="mt-5 grid gap-3 text-sm sm:text-base">
        <p className="flex gap-3 text-slate-600">
          <CheckCircleIcon className="mt-0.5 h-5 w-5 shrink-0 text-pine" />
          <span>
            <span className="font-semibold text-pine">Why it leads:</span>{" "}
            Strong late-season snow reliability above 1,800m.
          </span>
        </p>
        <p className="flex gap-3 text-slate-600">
          <AlertTriangleIcon className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
          <span>
            <span className="font-semibold text-warning">Watchout:</span>{" "}
            April is weaker below mid-mountain elevations.
          </span>
        </p>
      </div>
    </div>
  );
}

function ExampleMetric({
  icon,
  label,
  value,
  className,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  className: string;
}) {
  return (
    <div
      className={`flex min-h-20 items-center gap-3 rounded-2xl px-4 py-3 ${className}`}
    >
      <span className="shrink-0" aria-hidden="true">
        {icon}
      </span>
      <div>
        <p className="text-sm leading-5">{label}</p>
        <p className="font-semibold leading-5 text-ink">{value}</p>
      </div>
    </div>
  );
}

function SearchIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m16.5 16.5 4 4" />
    </svg>
  );
}

function SlidersIcon({ className = "h-4 w-4" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 7h10" />
      <path d="M18 7h2" />
      <path d="M4 17h2" />
      <path d="M10 17h10" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="8" cy="17" r="2" />
    </svg>
  );
}

function SnowSignalIcon({ className = "h-6 w-6" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3 21 19H3L12 3Z" />
      <path d="M12 8v8" />
      <path d="m8.5 10 7 4" />
      <path d="m15.5 10-7 4" />
      <path d="m9.5 8.5 2.5 1.5 2.5-1.5" />
      <path d="m9.5 15.5 2.5-1.5 2.5 1.5" />
    </svg>
  );
}

function SnowflakeIcon({ className = "h-6 w-6" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3v18" />
      <path d="m5 7 14 10" />
      <path d="M19 7 5 17" />
      <path d="m9 4 3 3 3-3" />
      <path d="m9 20 3-3 3 3" />
    </svg>
  );
}

function ShieldCheckIcon({ className = "h-6 w-6" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3 19 6v5c0 5-3 8.5-7 10-4-1.5-7-5-7-10V6l7-3Z" />
      <path d="m8.5 12 2.2 2.2 4.8-5" />
    </svg>
  );
}

function TrendIcon({ className = "h-6 w-6" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <path d="M8 16v-4" />
      <path d="M12 16V9" />
      <path d="M16 16V7" />
      <path d="m16 7 3 3" />
      <path d="m16 7-3 3" />
    </svg>
  );
}

function CheckCircleIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="m8 12 2.5 2.5L16 9" />
    </svg>
  );
}

function AlertTriangleIcon({ className = "h-5 w-5" }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3 21 20H3L12 3Z" />
      <path d="M12 9v5" />
      <path d="M12 17h.01" />
    </svg>
  );
}

function ChipIcon({
  filterKey,
  className = "h-4 w-4",
}: IconProps & { filterKey: AppliedFilterKey }) {
  if (filterKey === "location") {
    return (
      <svg
        viewBox="0 0 24 24"
        className={className}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18" />
        <path d="M12 3a14 14 0 0 1 0 18" />
        <path d="M12 3a14 14 0 0 0 0 18" />
      </svg>
    );
  }

  if (filterKey === "skill_level") {
    return (
      <svg
        viewBox="0 0 24 24"
        className={className}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="8" r="4" />
        <path d="M5 21a7 7 0 0 1 14 0" />
      </svg>
    );
  }

  if (filterKey === "budget") {
    return (
      <svg
        viewBox="0 0 24 24"
        className={className}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="3" y="6" width="18" height="12" rx="3" />
        <path d="M7 10h5" />
        <path d="M17 14h.01" />
      </svg>
    );
  }

  if (filterKey === "stars") {
    return (
      <svg
        viewBox="0 0 24 24"
        className={className}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M12 3 21 12 12 21 3 12 12 3Z" />
        <path d="m8 12 2.5 2.5L16 9" />
      </svg>
    );
  }

  if (filterKey === "travel_window") {
    return (
      <svg
        viewBox="0 0 24 24"
        className={className}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="4" y="5" width="16" height="15" rx="3" />
        <path d="M8 3v4" />
        <path d="M16 3v4" />
        <path d="M4 10h16" />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" />
    </svg>
  );
}

function SearchDecisionRail({
  filters,
  parsedQuery,
  tripContext,
  clarifications,
  assumptions,
  selectedResult,
  resultsCount,
  onRefine,
  onRemoveFilter,
  onApplyClarification,
}: {
  filters: SearchFilters;
  parsedQuery: ParsedQueryResponse | null;
  tripContext: TripContext;
  clarifications: TripClarification[];
  assumptions: string[];
  selectedResult: SearchResult | null;
  resultsCount: number;
  onRefine: () => void;
  onRemoveFilter: (key: AppliedFilterKey) => void;
  onApplyClarification: (
    clarificationId: string,
    option: TripClarificationOption,
  ) => void;
}) {
  const chips = buildAppliedFilterChips(filters);
  const selectedTopOption = selectedResult ? getTopTripOption(selectedResult) : null;
  const travelEffort =
    selectedTopOption?.travel_effort ?? selectedResult?.travel_effort ?? null;
  const evidenceMode = selectedResult
    ? getEvidenceQualityMode(selectedResult)
    : null;
  const evidenceSeasonCount = selectedResult
    ? getEvidenceSeasonCount(selectedResult)
    : null;

  return (
    <aside className="grid h-fit gap-4">
      <section className="rounded-[1.75rem] border border-line bg-white/92 p-5 shadow-panel backdrop-blur">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
              Trip context
            </p>
            <h2 className="mt-2 font-display text-2xl font-semibold text-ink">
              Search understood
            </h2>
          </div>
          <button
            type="button"
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-alpineBlue hover:text-alpineBlue"
            onClick={onRefine}
          >
            Refine search
          </button>
        </div>

        {parsedQuery ? (
          <p className="mt-4 text-sm leading-6 text-muted">
            Search confidence:{" "}
            <span className="font-semibold text-ink">
              {Math.round(parsedQuery.confidence * 100)}%
            </span>
            {parsedQuery.unknown_parts.length > 0
              ? `. Not sure how to use: ${parsedQuery.unknown_parts.join(", ")}.`
              : ""}
          </p>
        ) : (
          <p className="mt-4 text-sm leading-6 text-muted">
            Structured filters are ready for ranking. Refine only the inputs that
            materially affect the trip.
          </p>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          {chips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              className="rounded-full border border-alpine/20 bg-frost px-3 py-2 text-sm font-semibold text-alpine transition hover:border-alpine hover:bg-white"
              onClick={() => onRemoveFilter(chip.key)}
              aria-label={`Remove ${chip.label}`}
            >
              {chip.label} x
            </button>
          ))}
          {tripContext.budget_mode ? (
            <span className="rounded-full border border-ember/20 bg-amber-50 px-3 py-2 text-sm font-semibold text-ember">
              Budget: {formatBudgetMode(tripContext.budget_mode)}
            </span>
          ) : null}
        </div>
      </section>

      {clarifications.length > 0 ? (
        <section className="rounded-[1.75rem] border border-amber/30 bg-amber-50 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-warning">
            Clarify ranking
          </p>
          <div className="mt-3 grid gap-3">
            {clarifications.map((clarification) => (
              <div key={clarification.id}>
                <p className="text-sm font-semibold text-ink">
                  {clarification.question}
                </p>
                <p className="mt-1 text-sm leading-6 text-slate-700">
                  {clarification.reason}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {clarification.options.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      className="rounded-full border border-warning/25 bg-white px-3 py-2 text-sm font-semibold text-warning transition hover:border-warning"
                      onClick={() => onApplyClarification(clarification.id, option)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {selectedResult ? (
        <section className="rounded-[1.75rem] border border-line bg-white/92 p-5 shadow-panel backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
            {isWeakTripMatch(selectedResult)
              ? `${selectedResult.resort_name} is a weak match`
              : `Why ${selectedResult.resort_name} leads`}
          </p>
          <div className="mt-4 grid gap-3">
            <div className="rounded-2xl border border-amber/20 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-ink">
                {resultsCount > 0
                  ? selectedResult && isWeakTripMatch(selectedResult)
                    ? "Best available match, but weak"
                    : "Best available match"
                  : "Ranking context"}
              </p>
              <p className="mt-2 text-sm leading-6 text-muted">
                {selectedResult.planning_summary ??
                  selectedResult.conditions_summary}
              </p>
            </div>
            {evidenceMode ? (
              <EvidenceQualityBadge
                mode={evidenceMode}
                seasons={evidenceSeasonCount}
              />
            ) : null}
            {travelEffort ? (
              <div className="rounded-2xl border border-warning/15 bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-warning">
                  Travel effort
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  {travelEffort.summary}
                </p>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {assumptions.length > 0 ? (
        <section className="rounded-[1.75rem] border border-line bg-white/86 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Assumptions
          </p>
          <ul className="mt-3 grid gap-2 text-sm leading-6 text-muted">
            {assumptions.map((assumption) => (
              <li key={assumption}>{assumption}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="rounded-[1.75rem] border border-line bg-ice/65 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
          How rankings work
        </p>
        <p className="mt-3 text-sm leading-6 text-muted">
          Snowcast ranks ski trips: destination, ski area, stay base,
          travel window, travel effort, budget fit, and evidence quality.
        </p>
      </section>
    </aside>
  );
}

function RefineDrawer({
  filters,
  isBusy,
  onClose,
  onFiltersChange,
  onSubmit,
  onTravelWindowModeChange,
}: {
  filters: SearchFilters;
  isBusy: boolean;
  onClose: () => void;
  onFiltersChange: Dispatch<SetStateAction<SearchFilters>>;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onTravelWindowModeChange: (mode: TravelWindowMode) => void;
}) {
  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 cursor-default bg-midnight/45"
        aria-label="Close refine filters"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="refine-drawer-title"
        className="absolute right-0 top-0 flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-white/60 bg-snow p-5 shadow-premium sm:p-7"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
              Adjust filters
            </p>
            <h2
              id="refine-drawer-title"
              className="mt-2 font-display text-3xl font-semibold text-ink"
            >
              Refine search filters
            </h2>
          </div>
          <button
            type="button"
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-alpineBlue hover:text-alpineBlue"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <form className="mt-6 grid gap-5" noValidate onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-700">Location</span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                value={filters.location}
                onChange={(event) =>
                  onFiltersChange((current) => ({
                    ...current,
                    location: event.target.value,
                  }))
                }
                placeholder="France"
              />
            </label>

            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-700">Skill level</span>
              <select
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                value={filters.skillLevel}
                onChange={(event) =>
                  onFiltersChange((current) => ({
                    ...current,
                    skillLevel: event.target.value as SearchFilters["skillLevel"],
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
              <span className="text-sm font-semibold text-slate-700">Min price</span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                inputMode="decimal"
                value={filters.minPrice}
                onChange={(event) =>
                  onFiltersChange((current) => ({
                    ...current,
                    minPrice: event.target.value,
                  }))
                }
                placeholder="150"
              />
            </label>

            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-700">Max price</span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                inputMode="decimal"
                value={filters.maxPrice}
                onChange={(event) =>
                  onFiltersChange((current) => ({
                    ...current,
                    maxPrice: event.target.value,
                  }))
                }
                placeholder="320"
              />
            </label>

            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-700">
                Travel origin
              </span>
              <input
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                value={filters.originText}
                onChange={(event) =>
                  onFiltersChange((current) => ({
                    ...current,
                    originText: event.target.value,
                  }))
                }
                placeholder="Munich"
              />
            </label>

            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-700">
                Max drive hours
              </span>
              <input
                type="number"
                min="0.1"
                step="0.5"
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                inputMode="decimal"
                value={filters.maxDriveHours}
                onChange={(event) =>
                  onFiltersChange((current) => ({
                    ...current,
                    maxDriveHours: event.target.value,
                  }))
                }
                placeholder="3.5"
              />
            </label>

            <label className="space-y-2 sm:col-span-2">
              <span className="text-sm font-semibold text-slate-700">
                Travel tolerance
              </span>
              <select
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                value={filters.travelTolerance}
                onChange={(event) =>
                  onFiltersChange((current) => ({
                    ...current,
                    travelTolerance:
                      event.target.value as SearchFilters["travelTolerance"],
                  }))
                }
              >
                <option value="">No preference</option>
                <option value="short">Short drive</option>
                <option value="medium">Medium drive</option>
                <option value="flexible">Flexible drive</option>
              </select>
            </label>
          </div>

          <div className="rounded-[1.5rem] border border-line bg-white p-4">
            <span className="text-sm font-semibold text-slate-700">
              Travel window
            </span>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
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
                      onTravelWindowModeChange(mode as TravelWindowMode)
                    }
                  >
                    {label}
                  </button>
                );
              })}
            </div>

            {filters.travelWindowMode === "month" ? (
              <label className="mt-4 block space-y-2">
                <span className="text-sm font-semibold text-slate-700">
                  Travel month
                </span>
                <select
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                  value={filters.travelMonth}
                  onChange={(event) =>
                    onFiltersChange((current) => ({
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
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-sm font-semibold text-slate-700">
                    Trip start date
                  </span>
                  <input
                    type="date"
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                    value={filters.tripStartDate}
                    onChange={(event) =>
                      onFiltersChange((current) => ({
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
                      onFiltersChange((current) => ({
                        ...current,
                        travelMonth: "",
                        tripEndDate: event.target.value,
                      }))
                    }
                  />
                </label>
              </div>
            ) : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-3 sm:col-span-2">
              <span className="text-sm font-semibold text-slate-700">
                Minimum quality
              </span>
              <div className="grid grid-cols-3 gap-3">
                {[
                  ["1", "Budget+"],
                  ["2", "Standard+"],
                  ["3", "Premium"],
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
                        onFiltersChange((current) => ({
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
            </div>

            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-700">
                Lift distance
              </span>
              <select
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                value={filters.liftDistance}
                onChange={(event) =>
                  onFiltersChange((current) => ({
                    ...current,
                    liftDistance: event.target.value as SearchFilters["liftDistance"],
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
                  onFiltersChange((current) => ({
                    ...current,
                    budgetFlex: event.target.value,
                  }))
                }
                placeholder="0.1"
              />
            </label>
          </div>

          <div className="sticky bottom-0 -mx-5 mt-2 flex flex-wrap items-center justify-end gap-3 border-t border-line bg-snow/95 px-5 py-4 backdrop-blur sm:-mx-7 sm:px-7">
            <button
              type="button"
              className="rounded-full border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-alpineBlue hover:text-alpineBlue"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-full bg-midnight px-6 py-3 text-sm font-semibold text-white transition hover:bg-midnightSoft disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={isBusy}
            >
              {isBusy ? "Updating..." : "Apply filters"}
            </button>
          </div>
        </form>
      </aside>
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

  if (filters.maxDriveHours.trim()) {
    const maxDriveHours = Number(filters.maxDriveHours);
    if (!Number.isFinite(maxDriveHours) || maxDriveHours <= 0) {
      return "Max drive hours must be a positive number.";
    }
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
    chips.push({
      key: "stars",
      label: `${formatQualityTier(Number(filters.stars))}+ quality`,
    });
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
  if (filters.originText.trim()) {
    chips.push({
      key: "origin",
      label: `Origin ${filters.originText.trim()}`,
    });
  }
  if (filters.maxDriveHours) {
    chips.push({
      key: "max_drive",
      label: `Max drive ${filters.maxDriveHours}h`,
    });
  }
  if (filters.travelTolerance) {
    chips.push({
      key: "travel_tolerance",
      label: `${formatTravelTolerance(filters.travelTolerance)} travel`,
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

function getTopTripOption(result: SearchResult): TripOption {
  return result.top_option ?? buildTripOptionFromSelectedResult(result);
}

function getTripOptions(result: SearchResult): TripOption[] {
  return [getTopTripOption(result), ...(result.alternative_options ?? [])];
}

function findTripOption(
  result: SearchResult,
  optionId: string | null,
): TripOption {
  const options = getTripOptions(result);
  return (
    options.find((option) => option.option_id === optionId) ?? getTopTripOption(result)
  );
}

function buildTripOptionFromSelectedResult(result: SearchResult): TripOption {
  return {
    option_id: `${result.selected_ski_area_id}|${result.selected_stay_base_name}|${result.rental_name}`,
    ski_area_id: result.selected_ski_area_id,
    ski_area_name: result.selected_ski_area_name,
    stay_base_name: result.selected_stay_base_name,
    stay_base_lift_distance: result.selected_stay_base_lift_distance,
    stay_base_price_range: result.stay_base_price_range,
    rental_name: result.rental_name,
    rental_price_range: result.rental_price_range,
    rating_estimate: result.rating_estimate,
    score: result.score,
    recommendation_confidence: result.recommendation_confidence,
    budget_penalty: result.budget_penalty,
    travel_effort: result.travel_effort ?? null,
    explanation: result.explanation,
    tradeoff_summary: `${result.selected_stay_base_name}: ${result.stay_base_price_range} stay estimate.`,
  };
}

function applyTripOptionToResult(
  result: SearchResult,
  option: TripOption,
): SearchResult {
  return {
    ...result,
    selected_ski_area_id: option.ski_area_id,
    selected_ski_area_name: option.ski_area_name,
    selected_stay_base_name: option.stay_base_name,
    selected_stay_base_lift_distance: option.stay_base_lift_distance,
    stay_base_price_range: option.stay_base_price_range,
    selected_area_name: option.stay_base_name,
    selected_area_lift_distance: option.stay_base_lift_distance,
    area_price_range: option.stay_base_price_range,
    rental_name: option.rental_name,
    rental_price_range: option.rental_price_range,
    rating_estimate: option.rating_estimate,
  };
}

function getEvidenceSeasonCount(result: SearchResult): number | null {
  if (result.planning_weather_metrics) {
    return result.planning_weather_metrics.evidence_years;
  }
  return result.planning_evidence_count ?? null;
}

function getEvidenceQualityMode(result: SearchResult): EvidenceQualityMode {
  const seasons = getEvidenceSeasonCount(result);
  if (seasons !== null && seasons >= 4) {
    return "archiveBacked";
  }
  if (
    result.conditions_provenance.source_type === "forecast" ||
    result.planning_provenance?.source_type === "forecast"
  ) {
    return "forecastAssisted";
  }
  if (seasons !== null && seasons > 0) {
    return "forecastAssisted";
  }
  return "fallbackHeavy";
}

function buildTripTitle(result: SearchResult) {
  return result.resort_name;
}

function buildTripSubtitle(option: TripOption) {
  return `Stay in ${option.stay_base_name}`;
}

function formatEvidenceQualitySummary(
  mode: EvidenceQualityMode,
  seasons: number | null,
) {
  const copy = evidenceQualityCopy[mode];
  const seasonSuffix =
    seasons !== null
      ? ` · ${seasons} season${seasons === 1 ? "" : "s"}`
      : "";
  return `${copy.trust} — ${copy.label}${seasonSuffix}`;
}

function getTravelWindowLabelFromFilters(filters: SearchFilters) {
  if (
    filters.travelWindowMode === "dates" &&
    filters.tripStartDate &&
    filters.tripEndDate
  ) {
    return `${formatDate(filters.tripStartDate)} to ${formatDate(filters.tripEndDate)}`;
  }
  if (filters.travelWindowMode === "month" && filters.travelMonth) {
    return formatMonth(Number(filters.travelMonth));
  }
  return "Any time";
}

function isWeakTripMatch(result: SearchResult) {
  const summary = `${result.planning_summary ?? ""} ${result.conditions_summary}`.toLowerCase();
  return (
    result.snow_confidence_label === "poor" ||
    result.recommendation_confidence < 0.62 ||
    summary.includes("poor fit")
  );
}

function getBestMonthText(result: SearchResult) {
  if (result.best_travel_months.length === 0) {
    return null;
  }
  return result.best_travel_months.map(formatMonth).join(", ");
}

function getSearchWeakGuidance(results: SearchResult[], filters: SearchFilters) {
  const weakResult = results.find(isWeakTripMatch);
  if (!weakResult) {
    return null;
  }

  const windowLabel = getTravelWindowLabelFromFilters(filters);
  const bestMonths = getBestMonthText(weakResult);
  return {
    title: `${windowLabel} looks weak for these matches.`,
    body: bestMonths
      ? `Try ${bestMonths}, higher-altitude resorts, or a wider search area if your dates are flexible.`
      : "Try a stronger snow window, higher-altitude resorts, or a wider search area if your dates are flexible.",
  };
}

function getAvailabilityToneClass(value: SearchResult["availability_status"]) {
  if (value === "open") {
    return "bg-pine text-white";
  }
  if (value === "limited") {
    return "border border-amber/25 bg-amber/10 text-warning";
  }
  if (value === "temporarily_closed") {
    return "bg-warning text-white";
  }
  return "border border-slate-300 bg-slate-100 text-slate-700";
}

function buildResultCardVerdict(
  result: SearchResult,
  rank: number,
  travelWindowLabel: string,
) {
  if (isWeakTripMatch(result)) {
    return `Weak ${travelWindowLabel} match`;
  }
  if (rank === 1) {
    return "Best available match for this search";
  }
  return "Alternative match for this search";
}

function buildDetailVerdict(result: SearchResult, travelWindowLabel: string) {
  if (isWeakTripMatch(result)) {
    return `${travelWindowLabel} is a weak match for this trip.`;
  }
  return `Best available ski trip for ${travelWindowLabel}.`;
}

function SearchResultCard({
  result,
  rank,
  selected,
  travelWindowLabel,
  onSelect,
}: {
  result: SearchResult;
  rank: number;
  selected: boolean;
  travelWindowLabel: string;
  onSelect: () => void;
}) {
  const topOption = getTopTripOption(result);
  const alternativeCount = result.alternative_options?.length ?? 0;
  const tripFitPercent = Math.round(result.recommendation_confidence * 100);
  const weatherMetrics = result.planning_weather_metrics;
  const evidenceMode = getEvidenceQualityMode(result);
  const evidenceSeasonCount = getEvidenceSeasonCount(result);
  const travelEffort = topOption.travel_effort ?? result.travel_effort ?? null;
  const evidenceSummary = formatEvidenceQualitySummary(
    evidenceMode,
    evidenceSeasonCount,
  );
  const cardVerdict = buildResultCardVerdict(result, rank, travelWindowLabel);

  return (
    <button
      type="button"
      className={`group overflow-hidden rounded-[1.5rem] border text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-panel ${
        selected
          ? "border-alpineBlue/45 bg-white ring-1 ring-alpineBlue/12"
          : "border-line bg-white/92 hover:border-alpineBlue/35"
      }`}
      onClick={onSelect}
    >
      <div className="grid md:grid-cols-[6.25rem_minmax(0,1fr)]">
        <div className="relative min-h-24 bg-[linear-gradient(180deg,_#021a35_0%,_#08284f_100%)] p-4 text-white">
          <div className="absolute inset-x-0 bottom-0 h-20 bg-[radial-gradient(circle_at_45%_88%,_rgba(255,255,255,0.16),_transparent_34%)]" />
          <div className="relative flex h-full flex-col justify-between gap-8">
            <span className="w-fit rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-midnight">
              #{rank}
            </span>
            <div>
              <p className="text-sm font-semibold leading-5">
                {rank === 1 ? "Best match" : "Alternative"}
              </p>
              <p className="mt-2 text-xs leading-5 text-white/68">
                {evidenceSummary}
              </p>
            </div>
          </div>
        </div>

        <div className="p-5">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0 max-w-2xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-alpenglowSoft px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-warning">
                  {selected ? "Selected" : result.region}
                </span>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${getAvailabilityToneClass(result.availability_status)}`}>
                  {formatAvailability(result.availability_status)}
                </span>
              </div>
              <h3 className="mt-3 font-display text-3xl font-semibold text-ink">
                {buildTripTitle(result)}
              </h3>
              <p className="mt-1 text-lg font-semibold text-ink/82">
                {buildTripSubtitle(topOption)}
              </p>
              <p className={`mt-2 text-sm font-semibold ${isWeakTripMatch(result) ? "text-warning" : "text-alpineBlue"}`}>
                {cardVerdict}
              </p>
              <p className="mt-2 text-sm leading-6 text-muted">
                {result.conditions_summary}
              </p>
              <div className="mt-4 rounded-2xl bg-ice px-4 py-3">
                <TripEntityStack
                  destination={result.resort_name}
                  skiArea={topOption.ski_area_name}
                  stayBase={topOption.stay_base_name}
                  compact
                />
              </div>
              {travelEffort?.summary ? (
                <p className="mt-3 inline-flex rounded-full bg-amber/10 px-3 py-1.5 text-sm font-semibold text-warning">
                  {travelEffort.summary}
                </p>
              ) : null}
              {weatherMetrics ? (
                <p className="mt-3 text-sm text-muted">
                  Snow reliability: {formatSnowDepth(weatherMetrics)} typical
                  mid-mountain depth · avg high{" "}
                  {weatherMetrics.average_max_temperature_c.toFixed(1)} C
                </p>
              ) : null}
            </div>

            <div className="grid min-w-[17rem] gap-3">
              <EvidenceQualityBadge
                mode={evidenceMode}
                seasons={evidenceSeasonCount}
                compact
              />
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <MetricCard
                  selected={false}
                  label="Trip fit"
                  value={`${tripFitPercent}%`}
                />
                <MetricCard
                  selected={false}
                  label={
                    result.conditions_provenance.source_type === "forecast"
                      ? "Snow outlook"
                      : "Snow reliability"
                  }
                  value={capitalize(result.snow_confidence_label)}
                />
              </dl>
            </div>
          </div>
          <div className="mt-5">
            <div className="h-2 overflow-hidden rounded-full bg-ice">
              <div
                className="h-full rounded-full bg-pine transition-all"
                style={{ width: `${tripFitPercent}%` }}
              />
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <span className="text-sm text-muted">
                Stay in {topOption.stay_base_name} -{" "}
                {capitalize(topOption.stay_base_lift_distance)} lift access
            </span>
              {alternativeCount > 0 ? (
                <span className="rounded-full bg-ice px-3 py-1 text-sm font-semibold text-alpineBlue">
                  {alternativeCount} alternative base
                  {alternativeCount === 1 ? "" : "s"}
                </span>
              ) : null}
              <span className="font-semibold text-alpineBlue transition group-hover:text-ink">
                View dossier
              </span>
            </div>
          </div>
        </div>
      </div>
    </button>
  );
}

function SelectedResortPage({
  result,
  activeOption,
  onActiveOptionChange,
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
  activeOption: TripOption | null;
  onActiveOptionChange: (optionId: string) => void;
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
          activeOption={activeOption ?? getTopTripOption(result)}
          onActiveOptionChange={onActiveOptionChange}
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
  activeOption,
  onActiveOptionChange,
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
  activeOption: TripOption;
  onActiveOptionChange: (optionId: string) => void;
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
  const options = getTripOptions(result);
  const selectedOptionResult = applyTripOptionToResult(result, activeOption);
  const bookingHref = buildAccommodationBookingRedirectUrl(
    selectedOptionResult,
    "selected_result_details",
  );
  const displayedNarrative =
    result.recommendation_narrative ??
    buildFallbackRecommendationNarrative(result);
  const isCurrentTripForSelection =
    currentTrip?.resort_id === result.resort_id &&
    currentTrip.selected_stay_base_name === activeOption.stay_base_name &&
    currentTrip.selected_ski_area_name === activeOption.ski_area_name;
  const hasTravelWindow = Boolean(
    travelMonth || (tripStartDate && tripEndDate),
  );
  const travelWindowLabel =
    tripStartDate && tripEndDate
      ? `${formatDate(tripStartDate)} to ${formatDate(tripEndDate)}`
      : travelMonth
        ? formatMonth(Number(travelMonth))
        : "Any time";
  const tripFitPercent = Math.round(result.recommendation_confidence * 100);
  const evidenceMode = getEvidenceQualityMode(result);
  const evidenceSeasonCount = getEvidenceSeasonCount(result);
  const travelEffort = activeOption.travel_effort ?? result.travel_effort ?? null;
  const evidenceSummary = formatEvidenceQualitySummary(
    evidenceMode,
    evidenceSeasonCount,
  );
  const tripTitle = buildTripTitle(result);
  const tripSubtitle = buildTripSubtitle(activeOption);
  const detailVerdict = buildDetailVerdict(result, travelWindowLabel);

  return (
    <div data-testid="result-details" className="grid gap-5">
      <section className="overflow-hidden rounded-[2rem] border border-ink/10 bg-white shadow-panel">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr]">
          <div className="bg-[radial-gradient(circle_at_88%_8%,_rgba(255,95,143,0.22),_transparent_25%),linear-gradient(135deg,_#021a35_0%,_#08284f_58%,_#07182f_100%)] p-6 text-white sm:p-8">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-white/12 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-100">
                Recommendation dossier
              </span>
              <span className="rounded-full bg-ember/25 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-100">
                {result.region}
              </span>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${getAvailabilityToneClass(result.availability_status)}`}>
                {formatAvailability(result.availability_status)}
              </span>
            </div>
            <h2 className="mt-5 font-display text-5xl font-semibold leading-none">
              {result.resort_name}
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-200">
              {detailVerdict} Snowcast is comparing the mountain, travel
              window, stay base, travel effort, and evidence quality before the
              booking handoff.
            </p>
            <div className="mt-5 rounded-2xl bg-white/[0.92] p-4">
              <TripEntityStack
                destination={result.resort_name}
                skiArea={activeOption.ski_area_name}
                stayBase={activeOption.stay_base_name}
              />
            </div>
            {displayedNarrative ? (
              <p className="mt-5 rounded-2xl bg-white/10 px-4 py-4 text-sm leading-6 text-slate-100">
                {displayedNarrative}
              </p>
            ) : null}
          </div>

          <div className="grid content-between gap-4 bg-frost/55 p-6 sm:p-8">
            <div className="grid gap-3 sm:grid-cols-2">
              <EvidenceStat
                label="Trip fit"
                value={`${tripFitPercent}%`}
              />
              <EvidenceStat
                label={
                  result.conditions_provenance.source_type === "forecast"
                    ? "Snow outlook"
                    : "Snow reliability"
                }
                value={capitalize(result.snow_confidence_label)}
              />
              <EvidenceStat label="Travel window" value={travelWindowLabel} />
              <EvidenceStat
                label="Travel effort"
                value={
                  travelEffort
                    ? formatEnumLabel(travelEffort.effort_label)
                    : "Not requested"
                }
              />
            </div>
            <EvidenceQualityBadge
              mode={evidenceMode}
              seasons={evidenceSeasonCount}
            />
            <div className="rounded-3xl border border-slate-200 bg-white/85 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
                Primary action
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Continue from the recommended stay base in{" "}
                {activeOption.stay_base_name}.
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

      <DetailPanel title="Recommended ski trip">
        <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
          <div className="rounded-2xl border border-line bg-ice/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-alpineBlue">
              Best available match for this search
            </p>
            <h3 className="mt-2 font-display text-2xl font-semibold text-ink">
              {tripTitle}
            </h3>
            <p className="mt-1 text-lg font-semibold text-ink/82">
              {tripSubtitle}
            </p>
            <p className="mt-2 text-sm leading-6 text-muted">
              Snowcast is ranking this destination, ski area, stay base, travel
              window, travel effort, and evidence quality as one ski trip, not
              as a generic hotel or resort listing.
            </p>
          </div>
          <div className="grid gap-3 text-sm sm:grid-cols-2">
            <FactRow label="Destination" value={result.resort_name} />
            <FactRow label="Ski area" value={activeOption.ski_area_name} />
            <FactRow label="Stay base" value={activeOption.stay_base_name} />
            <FactRow label="Travel window" value={travelWindowLabel} />
            <FactRow
              label="Travel effort"
              value={travelEffort?.summary ?? "Not requested"}
            />
            <FactRow label="Evidence" value={evidenceSummary} />
          </div>
        </div>
      </DetailPanel>

      <DetailPanel title="Why this trip fits">
        <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="rounded-2xl bg-frost/55 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
              Trip fit
            </p>
            <p className="mt-2 text-4xl font-semibold text-ink">
              {tripFitPercent}%
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              {tripFitExplanation}
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

      {(result.alternative_options?.length ?? 0) > 0 ? (
        <DetailPanel title="Stay-base alternatives">
          <div className="grid gap-3">
            {options.map((option) => {
              const selected = option.option_id === activeOption.option_id;
              return (
                <button
                  key={option.option_id}
                  type="button"
                  aria-pressed={selected}
                  className={`rounded-2xl border px-4 py-4 text-left transition ${
                    selected
                      ? "border-alpine bg-frost shadow-sm"
                      : "border-slate-200 bg-white hover:border-alpine/40"
                  }`}
                  onClick={() => onActiveOptionChange(option.option_id)}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink">
                        {option.stay_base_name}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        {capitalize(option.stay_base_lift_distance)} lift access
                      </p>
                    </div>
                    <div className="text-right text-sm">
                      <p className="font-semibold text-alpine">
                        {option.stay_base_price_range}
                      </p>
                      <p className="mt-1 text-slate-500">
                        Rental {option.rental_price_range}
                      </p>
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    {option.tradeoff_summary}
                  </p>
                </button>
              );
            })}
          </div>
        </DetailPanel>
      ) : null}

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

      {travelEffort ? (
        <DetailPanel title="Travel effort">
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700">
            <p className="font-semibold text-ink">{travelEffort.summary}</p>
            {travelEffort.caveat ? (
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {travelEffort.caveat}
              </p>
            ) : null}
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <FactRow label="Origin" value={travelEffort.origin_label} />
              <FactRow
                label="Destination"
                value={travelEffort.destination_label}
              />
              <FactRow label="Mode" value={capitalize(travelEffort.mode)} />
              <FactRow
                label="Effort"
                value={formatEnumLabel(travelEffort.effort_label)}
              />
              <FactRow
                label="Distance"
                value={`${Math.round(travelEffort.distance_km)} km`}
              />
              <FactRow
                label="Duration"
                value={formatDriveDuration(travelEffort.duration_minutes)}
              />
              <FactRow
                label="Source"
                value={formatTravelProvider(travelEffort.provider)}
              />
              <FactRow
                label="Evidence"
                value={formatTravelProvenance(travelEffort.provenance)}
              />
            </div>
          </div>
        </DetailPanel>
      ) : null}

      <DetailPanel title="Recommended stay base">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
          <div className="rounded-2xl border border-line bg-ice/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-alpineBlue">
              Stay-base estimate, not live hotel inventory
            </p>
            <h3 className="mt-2 font-display text-2xl font-semibold text-ink">
              Continue from {activeOption.stay_base_name}
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              Snowcast can hand off to accommodation search for this stay base.
              The current model supports stay-base price estimates and rental
              context; provider-backed hotel or apartment options are not
              attached to this result yet.
            </p>
            <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              <FactRow
                label="Nightly estimate"
                value={activeOption.stay_base_price_range}
              />
              <FactRow
                label="Lift access"
                value={capitalize(activeOption.stay_base_lift_distance)}
              />
              <FactRow
                label="Rental context"
                value={activeOption.rental_price_range}
              />
            </div>
          </div>
          <a
            href={bookingHref}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-full bg-midnight px-5 py-3 text-sm font-semibold text-white transition hover:bg-midnightSoft"
          >
            Open accommodation search
          </a>
        </div>
      </DetailPanel>

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
              {result.planning_weather_metrics ? (
                <>
                  <FactRow
                    label="Mid-mountain typical snow depth"
                    value={formatSnowDepth(result.planning_weather_metrics)}
                  />
                  <FactRow
                    label="Avg high"
                    value={`${result.planning_weather_metrics.average_max_temperature_c.toFixed(1)}°C`}
                  />
                  <FactRow
                    label="Daily snowfall"
                    value={`${result.planning_weather_metrics.average_daily_snowfall_cm.toFixed(1)} cm`}
                  />
                  <FactRow
                    label="Historical seasons"
                    value={`${result.planning_weather_metrics.evidence_years}`}
                  />
                </>
              ) : null}
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

      <div className="grid gap-5 lg:grid-cols-2">
        <DetailPanel title="Stay + Rental">
          <div className="grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
            <FactRow label="Ski area" value={activeOption.ski_area_name} />
            <FactRow label="Stay base" value={activeOption.stay_base_name} />
            <FactRow
              label="Stay-base price"
              value={activeOption.stay_base_price_range}
            />
            <FactRow
              label="Lift distance"
              value={capitalize(activeOption.stay_base_lift_distance)}
            />
            <FactRow label="Rental" value={activeOption.rental_name} />
            <FactRow label="Rental price" value={activeOption.rental_price_range} />
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

            <Panel title="Planning update">
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
      ? "low weather disruption risk"
      : result.availability_status === "limited"
        ? "weather disruption possible"
        : result.availability_status === "temporarily_closed"
          ? "high weather disruption risk"
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

function formatEnumLabel(value: string) {
  return value
    .split("_")
    .filter(Boolean)
    .map(capitalize)
    .join(" ");
}

function formatBudgetMode(value: TripContext["budget_mode"]) {
  if (value === "lodging_nightly") {
    return "nightly lodging";
  }
  if (value === "total_trip") {
    return "total trip";
  }

  return "unspecified";
}

function formatTravelTolerance(value: SearchFilters["travelTolerance"]) {
  const labels: Record<Exclude<SearchFilters["travelTolerance"], "">, string> = {
    short: "Short",
    medium: "Medium",
    flexible: "Flexible",
  };
  return value ? labels[value] : "Any";
}

function formatTravelProvider(value: string) {
  if (value.startsWith("approximate_haversine")) {
    return "Approximate road estimate";
  }
  return formatEnumLabel(value);
}

function formatTravelProvenance(value: NonNullable<TravelEffort["provenance"]>) {
  const labels: Record<TravelEffort["provenance"], string> = {
    provider_backed: "Provider-backed",
    estimated_fallback: "Estimated fallback",
  };
  return labels[value];
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

function formatSnowDepth(metrics: SearchResult["planning_weather_metrics"]) {
  if (!metrics || metrics.average_snow_depth_cm === null) {
    return "Not available";
  }
  return `${Math.round(metrics.average_snow_depth_cm)} cm`;
}

function formatDriveDuration(minutes: number) {
  const roundedMinutes = Math.round(minutes);
  const hours = Math.floor(roundedMinutes / 60);
  const remainingMinutes = roundedMinutes % 60;

  if (hours === 0) {
    return `${remainingMinutes}m`;
  }
  if (remainingMinutes === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${remainingMinutes}m`;
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
  const labels: Record<SearchResult["availability_status"], string> = {
    open: "Low disruption risk",
    limited: "Weather disruption possible",
    temporarily_closed: "High disruption risk",
    out_of_season: "Out of season",
  };
  return labels[value];
}

function formatQualityTier(value: number) {
  const labels: Record<number, string> = {
    1: "Budget",
    2: "Standard",
    3: "Premium",
  };
  return labels[value] ?? `Tier ${value}`;
}

function formatBookingStatus(value: BookingStatus) {
  return value.replace(/_/g, " ");
}

export default App;
