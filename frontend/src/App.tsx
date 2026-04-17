import { FormEvent, ReactNode, useEffect, useState } from "react";

import {
  buildAccommodationBookingRedirectUrl,
  clearCurrentTrip,
  getCurrentTrip,
  getCurrentTripSummary,
  markCurrentTripChecked,
  parseTripBrief,
  saveCurrentTrip,
  searchResorts,
} from "./api";
import type {
  BookingStatus,
  CurrentTrip,
  CurrentTripSummary,
  ParsedQueryResponse,
  ProvenanceInfo,
  SearchFilters,
  SearchResult,
  TravelMonth,
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
  travelMonth: "",
};

const storageKey = "sports-trip-planner-advanced-open";
type ViewMode = "search" | "current_trip";

function App() {
  const [tripBrief, setTripBrief] = useState("");
  const [parsedQuery, setParsedQuery] = useState<ParsedQueryResponse | null>(null);
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
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
  const [isCurrentTripLoading, setIsCurrentTripLoading] = useState(false);
  const [tripBookingStatus, setTripBookingStatus] =
    useState<BookingStatus>("not_booked_yet");
  const [viewMode, setViewMode] = useState<ViewMode>("search");

  useEffect(() => {
    window.sessionStorage.setItem(storageKey, String(isAdvancedOpen));
  }, [isAdvancedOpen]);

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
      if (viewMode !== "current_trip" || currentTrip === null) {
        if (!isCancelled && currentTrip === null) {
          setCurrentTripSummary(null);
          setCurrentTripSummaryError(null);
        }
        return;
      }

      setIsCurrentTripLoading(true);

      try {
        const summary = await getCurrentTripSummary();
        if (!isCancelled) {
          setCurrentTripSummary(summary);
          setCurrentTripSummaryError(null);
        }
      } catch (caughtError) {
        if (!isCancelled) {
          setCurrentTripSummary(null);
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
    viewMode,
    currentTrip?.resort_id,
    currentTrip?.selected_stay_base_name,
    currentTrip?.selected_ski_area_name,
    currentTrip?.travel_month,
    currentTrip?.booking_status,
    currentTrip?.last_checked_at,
  ]);

  const selectedResult =
    results.find((result) => result.resort_id === selectedResultId) ??
    results[0] ??
    null;

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await searchResorts(filters);
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
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Something went wrong while loading results.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleInterpretTripBrief() {
    if (!tripBrief.trim()) {
      setParseError("Enter a trip brief before interpreting it.");
      setParsedQuery(null);
      return;
    }

    setIsParsing(true);
    setParseError(null);

    try {
      const response = await parseTripBrief(tripBrief);
      setParsedQuery(response);
    } catch (caughtError) {
      setParsedQuery(null);
      setParseError(
        caughtError instanceof Error
          ? caughtError.message
          : "Something went wrong while interpreting the trip brief.",
      );
    } finally {
      setIsParsing(false);
    }
  }

  function handleApplyParsedFilters() {
    if (!parsedQuery) {
      return;
    }

    const nextFilters = { ...filters };
    const { filters: parsedFilters } = parsedQuery;
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
    if (parsedFilters.travel_month !== undefined) {
      nextFilters.travelMonth = parsedFilters.travel_month;
    }

    setFilters(nextFilters);
    if (shouldOpenAdvancedFilters) {
      setIsAdvancedOpen(true);
    }
  }

  async function handleSaveCurrentTrip() {
    if (!selectedResult) {
      return;
    }

    setIsSavingTrip(true);
    setCurrentTripError(null);

    try {
      const saved = await saveCurrentTrip({
        resort_id: selectedResult.resort_id,
        selected_ski_area_id: selectedResult.selected_ski_area_id,
        selected_ski_area_name: selectedResult.selected_ski_area_name,
        selected_stay_base_name: selectedResult.selected_stay_base_name,
        travel_month: filters.travelMonth ? Number(filters.travelMonth) : null,
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
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(214,103,63,0.18),_transparent_28%),linear-gradient(180deg,_#f4efe7_0%,_#eef5f4_100%)] text-ink">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-8 lg:px-10">
        <header className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-ember">
              Snow-aware ski planning
            </p>
            <h1 className="font-display text-4xl font-semibold leading-tight sm:text-5xl">
              Plan ski trips with clearer snow confidence
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-700">
              Choose where and when to ski with more confidence.
            </p>
            <div className="mt-5 inline-flex rounded-full border border-white/70 bg-white/70 p-1 shadow-sm">
              {[
                ["search", "Search"],
                ["current_trip", "Current trip"],
              ].map(([value, label]) => {
                const active = viewMode === value;
                return (
                  <button
                    key={value}
                    type="button"
                    className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                      active
                        ? "bg-ink text-white"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                    onClick={() => setViewMode(value as ViewMode)}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        {viewMode === "search" ? (
        <div className="grid flex-1 gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="rounded-[2rem] border border-white/70 bg-white/85 p-6 shadow-panel backdrop-blur">
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="rounded-3xl bg-frost/80 p-4">
                <label className="space-y-2">
                  <span className="text-sm font-semibold text-slate-700">
                    Trip brief
                  </span>
                  <textarea
                    className="min-h-28 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-alpine focus:ring-2 focus:ring-alpine/20"
                    value={tripBrief}
                    onChange={(event) => setTripBrief(event.target.value)}
                    placeholder="Looking for a fairly affordable ski trip in Austria, intermediate level, not too far from the lifts."
                  />
                </label>
                <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
                  <button
                    type="button"
                    className="rounded-full border border-alpine px-5 py-3 text-sm font-semibold text-alpine transition hover:bg-alpine hover:text-white disabled:cursor-not-allowed disabled:border-slate-300 disabled:text-slate-400"
                    onClick={handleInterpretTripBrief}
                    disabled={isParsing}
                  >
                    {isParsing ? "Interpreting..." : "Interpret trip brief"}
                  </button>
                  <p className="text-sm text-slate-600">
                    AI-assisted parsing fills the structured filters, but you stay in control before searching.
                  </p>
                </div>

                {parseError ? (
                  <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {parseError}
                  </div>
                ) : null}

                {parsedQuery ? (
                  <div className="mt-4 rounded-2xl border border-white/60 bg-white/80 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
                          Interpreted trip brief
                        </p>
                        <p className="mt-2 text-sm text-slate-600">
                          Confidence: {Math.round(parsedQuery.confidence * 100)}%
                          {parsedQuery.confidence < 0.6
                            ? " • Some parts may need review before searching."
                            : ""}
                        </p>
                      </div>
                      <button
                        type="button"
                        className="rounded-full bg-ember px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700"
                        onClick={handleApplyParsedFilters}
                      >
                        Apply filters
                      </button>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      {Object.entries(parsedQuery.filters).length > 0 ? (
                        Object.entries(parsedQuery.filters).map(([key, value]) => (
                          <span
                            key={key}
                            className="rounded-full bg-frost px-3 py-1 text-sm font-medium text-alpine"
                          >
                            {formatParsedFilter(key, value)}
                          </span>
                        ))
                      ) : (
                        <p className="text-sm text-slate-500">
                          No structured filters were confidently extracted.
                        </p>
                      )}
                    </div>

                    {parsedQuery.unknown_parts.length > 0 ? (
                      <p className="mt-4 text-sm text-slate-600">
                        Could not confidently map:{" "}
                        {parsedQuery.unknown_parts.join(", ")}
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
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
                        skillLevel: event.target.value as SearchFilters["skillLevel"],
                      }))
                    }
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </label>

                <label className="space-y-2">
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
                      }))
                    }
                  >
                    <option value="">Any month</option>
                    {monthOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
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
              </div>

              <div className="rounded-3xl bg-frost/80 p-4">
                <button
                  type="button"
                  className="flex w-full items-center justify-between text-left"
                  onClick={() => setIsAdvancedOpen((current) => !current)}
                  aria-expanded={isAdvancedOpen}
                >
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-alpine">
                      Advanced filters
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      Lift distance and budget flexibility for softer ranking control.
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

              <div>
                <button
                  type="submit"
                  className="rounded-full bg-ink px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                  disabled={isLoading}
                >
                  {isLoading ? "Searching..." : "Search ski trips"}
                </button>
              </div>
            </form>

            <div className="mt-8">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="font-display text-2xl font-semibold">Ranked results</h2>
                  <p className="text-sm text-slate-600">
                    {filters.travelMonth
                      ? `Best resorts for ${formatMonth(Number(filters.travelMonth))}; highest-ranked result auto-selects unless your previous pick still exists.`
                      : "Highest-ranked resort auto-selects unless your previous pick still exists."}
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

              {!error && !isLoading && results.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-slate-300 bg-white/70 px-4 py-8 text-center text-sm text-slate-500">
                  Run a search to see ranked ski trip options.
                </div>
              ) : null}

              <div className="space-y-4">
                {results.map((result, index) => {
                  const selected = result.resort_id === selectedResult?.resort_id;
                  return (
                    <button
                      key={result.resort_id}
                      type="button"
                      className={`w-full rounded-[1.6rem] border p-5 text-left transition ${
                        selected
                          ? "border-ink bg-ink text-white shadow-panel"
                          : "border-white/70 bg-white/80 hover:border-slate-300 hover:bg-white"
                      }`}
                      onClick={() => setSelectedResultId(result.resort_id)}
                    >
                      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="flex items-center gap-3">
                            <span
                              className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${
                                selected
                                  ? "bg-white/15 text-white"
                                  : "bg-frost text-alpine"
                              }`}
                            >
                              #{index + 1}
                            </span>
                            <span className="text-sm font-medium">
                              {result.region}
                            </span>
                          </div>
                          <h3 className="mt-3 font-display text-2xl font-semibold">
                            {result.resort_name}
                          </h3>
                          <p className="mt-2 text-sm leading-6 opacity-80">
                            {result.conditions_summary}
                          </p>
                          <p
                            className={`mt-2 text-xs font-medium ${
                              selected ? "text-slate-200" : "text-slate-500"
                            }`}
                          >
                            {formatTrustCue(result.conditions_provenance)}
                          </p>
                        </div>

                        <dl className="grid min-w-[220px] grid-cols-2 gap-3 text-sm">
                          <MetricCard
                            selected={selected}
                            label="Confidence"
                            value={`${Math.round(result.recommendation_confidence * 100)}%`}
                          />
                          <MetricCard
                            selected={selected}
                            label="Snow"
                            value={capitalize(result.snow_confidence_label)}
                          />
                          <MetricCard
                            selected={selected}
                            label="Stay base"
                            value={result.selected_stay_base_name}
                          />
                          <MetricCard
                            selected={selected}
                            label="Availability"
                            value={formatAvailability(result.availability_status)}
                          />
                        </dl>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </section>

          <section className="rounded-[2rem] border border-ink/10 bg-ink p-6 text-white shadow-panel">
            {selectedResult ? (
              <ResultDetails
                result={selectedResult}
                travelMonth={filters.travelMonth}
                tripBookingStatus={tripBookingStatus}
                onTripBookingStatusChange={setTripBookingStatus}
                onSaveCurrentTrip={handleSaveCurrentTrip}
                onClearCurrentTrip={handleClearCurrentTrip}
                currentTrip={currentTrip}
                currentTripError={currentTripError}
                isSavingTrip={isSavingTrip}
              />
            ) : (
              <div className="flex h-full min-h-[420px] items-center justify-center rounded-[1.5rem] border border-white/10 bg-white/5 p-8 text-center text-sm text-slate-200">
                Select a ranked result to inspect why it fits, what to watch out
                for, and how conditions affect the recommendation.
              </div>
            )}
          </section>
        </div>
        ) : (
          <CurrentTripView
            currentTrip={currentTrip}
            currentTripError={currentTripError}
            currentTripSummary={currentTripSummary}
            currentTripSummaryError={currentTripSummaryError}
            isCurrentTripLoading={isCurrentTripLoading}
            isMarkingChecked={isMarkingChecked}
            onMarkChecked={handleMarkCurrentTripChecked}
            onBackToSearch={() => setViewMode("search")}
          />
        )}
      </div>
    </div>
  );
}

function formatParsedFilter(key: string, value: string | number) {
  const labelMap: Record<string, string> = {
    location: "Location",
    min_price: "Min price",
    max_price: "Max price",
    stars: "Stars",
    skill_level: "Skill",
    lift_distance: "Lift distance",
    budget_flex: "Budget flex",
    travel_month: "Travel month",
  };
  const formattedValue =
    key === "travel_month" && typeof value === "number"
      ? formatMonth(value)
      : String(value);
  return `${labelMap[key] ?? key}: ${formattedValue}`;
}

function ResultDetails({
  result,
  travelMonth,
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

  return (
    <div data-testid="result-details" className="flex h-full flex-col">
      <div className="rounded-[1.5rem] bg-white/5 p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-100">
            Selected resort
          </span>
          <span className="rounded-full bg-ember/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-100">
            {result.region}
          </span>
        </div>
        <h2 className="mt-4 font-display text-3xl font-semibold">
          {result.resort_name}
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-200">
          Ski {result.selected_ski_area_name}, stay in {result.selected_stay_base_name},
          and rent from {result.rental_name}. Conditions are{" "}
          {result.snow_confidence_label} and the current availability is{" "}
          {formatAvailability(result.availability_status).toLowerCase()}.
        </p>
        {displayedNarrative ? (
          <p className="mt-4 rounded-2xl bg-white/10 px-4 py-3 text-sm leading-6 text-slate-100">
            {displayedNarrative}
          </p>
        ) : null}
        {travelMonth && result.planning_summary ? (
          <div className="mt-4 rounded-2xl bg-amber-50/10 px-4 py-3 text-sm leading-6 text-amber-50">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-100">
              Planning for {formatMonth(Number(travelMonth))}
            </p>
            <p className="mt-2">{result.planning_summary}</p>
            <p className="mt-2 text-xs text-amber-100/90">
              {result.planning_provenance?.basis_summary ??
                (result.planning_evidence_count &&
                result.planning_evidence_count > 0
                  ? `Using ${result.planning_evidence_count} historical weather record${result.planning_evidence_count === 1 ? "" : "s"} for this month together with seasonal patterns.`
                  : "Using seasonal patterns and elevation because historical weather data is limited.")}
            </p>
          </div>
        ) : null}
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
          <a
            href={bookingHref}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white transition hover:bg-orange-700"
          >
            Book accommodation
          </a>
          <p className="text-sm text-slate-300">
            Continue with the selected stay option in{" "}
            {result.selected_stay_base_name}.
          </p>
        </div>
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
                Current trip
              </p>
              <p className="mt-2 text-sm text-slate-200">
                Save this selected result as your current trip context for the
                next companion step.
              </p>
            </div>
            {isCurrentTripForSelection ? (
              <span className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-200">
                Saved
              </span>
            ) : null}
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
                Booking status
              </span>
              <select
                className="w-full rounded-2xl border border-white/10 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-amber-200 focus:ring-2 focus:ring-amber-100/40"
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
            <button
              type="button"
              className="rounded-full bg-white px-4 py-3 text-sm font-semibold text-ink transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:bg-slate-300"
              onClick={() => void onSaveCurrentTrip()}
              disabled={isSavingTrip}
            >
              {isSavingTrip ? "Saving..." : "Save as current trip"}
            </button>
            <button
              type="button"
              className="rounded-full border border-white/20 px-4 py-3 text-sm font-semibold text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:text-slate-500"
              onClick={() => void onClearCurrentTrip()}
              disabled={isSavingTrip || currentTrip === null}
            >
              Clear trip
            </button>
          </div>
          {currentTripError ? (
            <p className="mt-3 text-sm text-amber-200">{currentTripError}</p>
          ) : null}
          {currentTrip ? (
            <div className="mt-4 rounded-2xl bg-white/5 px-4 py-3 text-sm text-slate-200">
              <p className="font-semibold text-white">{currentTrip.resort_name}</p>
              <p className="mt-1">
                {currentTrip.selected_ski_area_name} •{" "}
                {currentTrip.selected_stay_base_name}
                {currentTrip.travel_month
                  ? ` • ${formatMonth(currentTrip.travel_month)}`
                  : ""}
              </p>
              <p className="mt-1 text-slate-300">
                {formatBookingStatus(currentTrip.booking_status)}
              </p>
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-6">
        <Panel title="Why this result">
          {result.explanation.highlights.map((item) => (
            <ListItem key={item.label} label={item.label} tone="positive" />
          ))}
          {result.explanation.risks.length > 0 ? (
            <div className="mt-5 border-t border-white/10 pt-5">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
                Caveats
              </p>
              <div className="mt-3 space-y-3">
                {result.explanation.risks.map((item) => (
                  <ListItem key={item.label} label={item.label} tone="negative" />
                ))}
              </div>
            </div>
          ) : null}
        </Panel>
      </div>

      <div className="mt-4">
        <Panel title="Confidence">
          <div className="rounded-2xl bg-white/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
              Overall recommendation confidence
            </p>
            <p className="mt-2 text-3xl font-semibold">
              {Math.round(result.recommendation_confidence * 100)}%
            </p>
          </div>
        </Panel>
      </div>

      <div className={`mt-4 grid gap-4 ${travelMonth ? "sm:grid-cols-2" : ""}`}>
        <div
          data-testid="current-conditions-section"
          className={!travelMonth ? "sm:col-span-2" : ""}
        >
          <Panel title="Current conditions">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-slate-200">
              <p className="text-sm text-slate-100">
                {formatTrustCue(result.conditions_provenance)}
              </p>
              <div className="mt-3 space-y-3">
                <DetailRow
                  label="Source"
                  value={
                    result.conditions_provenance.source_name ?? "Estimated fallback"
                  }
                />
                <DetailRow
                  label="Freshness"
                  value={formatFreshnessStatus(
                    result.conditions_provenance.freshness_status,
                  )}
                />
                <DetailRow
                  label="Updated"
                  value={formatTimestamp(result.conditions_provenance.updated_at)}
                />
                <DetailRow
                  label="Status"
                  value={`${capitalize(result.snow_confidence_label)} snow • ${formatAvailability(
                    result.availability_status,
                  )}`}
                />
              </div>
            </div>
          </Panel>
        </div>

        {travelMonth ? (
          <Panel title="Travel window">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-slate-200">
              <div className="space-y-3">
                <DetailRow label="Month" value={formatMonth(Number(travelMonth))} />
                <DetailRow
                  label="Evidence type"
                  value={
                    result.planning_provenance?.freshness_status === "historical"
                      ? "Historical weather records"
                      : "Seasonal estimate"
                  }
                />
                <DetailRow
                  label="Latest weather record"
                  value={formatTimestamp(result.planning_provenance?.updated_at ?? null)}
                />
                <DetailRow
                  label="Best months"
                  value={
                    result.best_travel_months.length > 0
                      ? result.best_travel_months.map(formatMonth).join(", ")
                      : "Not enough data yet"
                  }
                />
              </div>
            </div>
          </Panel>
        ) : null}
      </div>

      <div className="mt-4">
        <Panel title="Stay + Rental">
          <div className="grid gap-3 text-sm text-slate-200 sm:grid-cols-2">
            <DetailRow label="Ski area" value={result.selected_ski_area_name} />
            <DetailRow label="Stay base" value={result.selected_stay_base_name} />
            <DetailRow label="Stay-base price" value={result.stay_base_price_range} />
            <DetailRow
              label="Lift distance"
              value={capitalize(result.selected_stay_base_lift_distance)}
            />
            <DetailRow label="Rental" value={result.rental_name} />
            <DetailRow label="Rental price" value={result.rental_price_range} />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function CurrentTripView({
  currentTrip,
  currentTripError,
  currentTripSummary,
  currentTripSummaryError,
  isCurrentTripLoading,
  isMarkingChecked,
  onMarkChecked,
  onBackToSearch,
}: {
  currentTrip: CurrentTrip | null;
  currentTripError: string | null;
  currentTripSummary: CurrentTripSummary | null;
  currentTripSummaryError: string | null;
  isCurrentTripLoading: boolean;
  isMarkingChecked: boolean;
  onMarkChecked: () => Promise<void>;
  onBackToSearch: () => void;
}) {
  if (currentTrip === null) {
    return (
      <section className="rounded-[2rem] border border-white/70 bg-white/85 p-8 shadow-panel backdrop-blur">
        <div className="mx-auto max-w-2xl rounded-[1.6rem] border border-dashed border-slate-300 bg-frost/60 p-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-alpine">
            Current trip
          </p>
          <h2 className="mt-4 font-display text-3xl font-semibold text-ink">
            Save a resort first
          </h2>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Your companion view appears after you save a selected result as the current trip from the search surface.
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
