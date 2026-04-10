import { FormEvent, ReactNode, useEffect, useState } from "react";

import {
  buildAccommodationBookingRedirectUrl,
  parseTripBrief,
  searchResorts,
} from "./api";
import type {
  ParsedQueryResponse,
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
  const [error, setError] = useState<string | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    window.sessionStorage.setItem(storageKey, String(isAdvancedOpen));
  }, [isAdvancedOpen]);

  const selectedResult =
    results.find((result) => result.resort_id === selectedResultId) ??
    results[0] ??
    null;

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

    setFilters(nextFilters);
    if (shouldOpenAdvancedFilters) {
      setIsAdvancedOpen(true);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(214,103,63,0.18),_transparent_28%),linear-gradient(180deg,_#f4efe7_0%,_#eef5f4_100%)] text-ink">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-8 lg:px-10">
        <header className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="mb-2 text-sm font-semibold uppercase tracking-[0.24em] text-ember">
              Sprint 7 Demo
            </p>
            <h1 className="font-display text-4xl font-semibold leading-tight sm:text-5xl">
              Ski trip search with explanation-first recommendations
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-700">
              Structured search for ski resorts with condition signals, grouped
              explanation output, and a focused result-inspection panel.
            </p>
          </div>
          <div className="rounded-3xl border border-white/60 bg-white/80 px-5 py-4 shadow-panel backdrop-blur">
            <p className="text-sm font-medium text-slate-500">Search surface</p>
            <p className="mt-1 text-lg font-semibold text-ink">
              AI-assisted, backend-driven
            </p>
          </div>
        </header>

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

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <button
                  type="submit"
                  className="rounded-full bg-ink px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                  disabled={isLoading}
                >
                  {isLoading ? "Searching..." : "Search ski trips"}
                </button>
                <p className="text-sm text-slate-600">
                  Uses the live backend `/api/search` contract through a local Vite proxy.
                </p>
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
                            label="Area"
                            value={result.selected_area_name}
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
              <ResultDetails result={selectedResult} travelMonth={filters.travelMonth} />
            ) : (
              <div className="flex h-full min-h-[420px] items-center justify-center rounded-[1.5rem] border border-white/10 bg-white/5 p-8 text-center text-sm text-slate-200">
                Select a ranked result to inspect why it fits, what to watch out
                for, and how conditions affect the recommendation.
              </div>
            )}
          </section>
        </div>
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
  };
  return `${labelMap[key] ?? key}: ${String(value)}`;
}

function ResultDetails({
  result,
  travelMonth,
}: {
  result: SearchResult;
  travelMonth: SearchFilters["travelMonth"];
}) {
  const bookingHref = buildAccommodationBookingRedirectUrl(
    result,
    "selected_result_details",
  );

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
          {result.selected_area_name} with {result.rental_name}. Conditions are{" "}
          {result.snow_confidence_label} and the current availability is{" "}
          {formatAvailability(result.availability_status).toLowerCase()}.
        </p>
        {result.recommendation_narrative ? (
          <p className="mt-4 rounded-2xl bg-white/10 px-4 py-3 text-sm leading-6 text-slate-100">
            {result.recommendation_narrative}
          </p>
        ) : null}
        {travelMonth && result.planning_summary ? (
          <div className="mt-4 rounded-2xl bg-amber-50/10 px-4 py-3 text-sm leading-6 text-amber-50">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-100">
              Planning for {formatMonth(Number(travelMonth))}
            </p>
            <p className="mt-2">{result.planning_summary}</p>
            <p className="mt-2 text-xs text-amber-100/90">
              {result.planning_evidence_count && result.planning_evidence_count > 0
                ? `Based on ${result.planning_evidence_count} stored snapshot${result.planning_evidence_count === 1 ? "" : "s"} plus resort seasonality.`
                : "Using resort seasonality and elevation while history is still sparse."}
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
            Continue with the selected stay option in {result.selected_area_name}.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Panel title="Why it fits">
          {result.explanation.highlights.map((item) => (
            <ListItem key={item.label} label={item.label} tone="positive" />
          ))}
        </Panel>

        <Panel title="Watchouts">
          {result.explanation.risks.length > 0 ? (
            result.explanation.risks.map((item) => (
              <ListItem key={item.label} label={item.label} tone="negative" />
            ))
          ) : (
            <p className="text-sm text-slate-300">
              No major watchouts surfaced for this result.
            </p>
          )}
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Panel title="Conditions">
          <div className="space-y-3 text-sm text-slate-200">
            <DetailRow label="Summary" value={result.conditions_summary} />
            <DetailRow
              label="Snow confidence"
              value={`${capitalize(result.snow_confidence_label)} (${Math.round(
                result.snow_confidence_score * 100,
              )}%)`}
            />
            <DetailRow
              label="Availability"
              value={formatAvailability(result.availability_status)}
            />
          </div>
        </Panel>

        <Panel title="Confidence">
          <div className="mb-4 rounded-2xl bg-white/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
              Overall recommendation confidence
            </p>
            <p className="mt-2 text-3xl font-semibold">
              {Math.round(result.recommendation_confidence * 100)}%
            </p>
          </div>

          <div className="space-y-3">
            {result.explanation.confidence_contributors.map((item) => (
              <ListItem
                key={`${item.direction}-${item.label}`}
                label={item.label}
                tone={item.direction}
              />
            ))}
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Panel title="Stay + Rental">
          <div className="space-y-3 text-sm text-slate-200">
            <DetailRow label="Area" value={result.selected_area_name} />
            <DetailRow label="Area price" value={result.area_price_range} />
            <DetailRow
              label="Lift distance"
              value={capitalize(result.selected_area_lift_distance)}
            />
            <DetailRow label="Rental" value={result.rental_name} />
            <DetailRow label="Rental price" value={result.rental_price_range} />
          </div>
        </Panel>

        {travelMonth ? (
          <Panel title="Travel window">
            <div className="space-y-3 text-sm text-slate-200">
              <DetailRow label="Month" value={formatMonth(Number(travelMonth))} />
              <DetailRow
                label="Best months"
                value={
                  result.best_travel_months.length > 0
                    ? result.best_travel_months.map(formatMonth).join(", ")
                    : "Not enough data yet"
                }
              />
              <DetailRow
                label="Planning score"
                value={`${Math.round(result.conditions_score * 100)}%`}
              />
            </div>
          </Panel>
        ) : (
          <Panel title="Signals">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <SignalCard label="Conditions score" value={result.conditions_score} />
              <SignalCard label="Ranking score" value={result.score} />
              <SignalCard
                label="Budget penalty"
                value={result.budget_penalty}
                formatter={(value) => value.toFixed(2)}
              />
              <SignalCard
                label="Rating estimate"
                value={result.rating_estimate}
                formatter={(value) => `${value.toFixed(0)} / 3`}
              />
            </div>
          </Panel>
        )}
      </div>
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

function SignalCard({
  label,
  value,
  formatter,
}: {
  label: string;
  value: number;
  formatter?: (value: number) => string;
}) {
  return (
    <div className="rounded-2xl bg-white/5 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold">
        {formatter ? formatter(value) : value.toFixed(2)}
      </p>
    </div>
  );
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatAvailability(value: SearchResult["availability_status"]) {
  return value.replace(/_/g, " ");
}

export default App;
