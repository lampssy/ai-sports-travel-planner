import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  clearCurrentTrip,
  getCurrentTrip,
  getCurrentTripSummary,
  parseTripBrief,
  saveCurrentTrip,
  searchResorts,
} from "./api";
import { SnowcastLogo } from "./ui/SnowcastLogo";
import type {
  CurrentTrip,
  CurrentTripSummary,
  FactorPreferencePatch,
  GroupPriorityPatch,
  ParsedQueryResponse,
  RefinementOption,
  SearchFilters,
  SearchIntent,
  SearchObjective,
  SearchResponse,
  SearchV4Configuration,
  SearchV4RecommendationGroup,
  TravelMonth,
} from "./types";

const monthOptions = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const featureOptions = [
  ["marked_freeride_routes", "Marked freeride routes"],
  ["snow_park", "Snow park"],
  ["night_skiing", "Night skiing"],
  ["glacier_terrain", "Glacier terrain"],
  ["snowmaking_availability", "Snowmaking resilience"],
  ["terrain_potential_scale", "Largest connected terrain"],
  ["lift_network_scale", "Large lift network"],
] as const;

const factorLabels: Record<string, string> = {
  accessible_terrain_scale: "Pass-accessible terrain",
  party_skill_coverage: "Party skill fit",
  terrain_potential_scale: "Connected terrain",
  lift_network_scale: "Lift network",
  marked_freeride_routes: "Marked freeride routes",
  snow_park: "Snow park",
  night_skiing: "Night skiing",
  glacier_terrain: "Glacier terrain",
  snowmaking_availability: "Snowmaking resilience",
  stay_base_access: "Stay-base access",
  pass_price_per_day: "Pass price per day",
  pass_terrain_value: "Terrain per pass price",
  ski_day_apres: "On-mountain après",
  local_apres: "Stay-base après",
  local_pace: "Local pace",
  development_style: "Development style",
  base_type: "Base type",
  travel_effort: "Travel effort",
  trip_window_snow_fit: "Trip-window snow fit",
};

const groupLabels: Record<string, string> = {
  trip_viability: "Trip viability",
  ski_experience: "Ski experience",
  stay_practicality: "Stay practicality",
  value: "Value",
  character: "Character",
  travel_effort: "Travel effort",
};

const defaultFilters: SearchFilters = {
  location: "France",
  maxPrice: "320",
  stars: "2",
  skillLevel: "intermediate",
  budgetFlex: "0.10",
  travelWindowMode: "month",
  travelMonth: 3,
  tripStartDate: "",
  tripEndDate: "",
  originText: "",
  maxDriveHours: "",
  valueObjective: "pass_terrain_value",
};

function App() {
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters);
  const [brief, setBrief] = useState("");
  const [lastParsedBrief, setLastParsedBrief] = useState("");
  const [assumptions, setAssumptions] = useState<string[]>([]);
  const [preferences, setPreferences] = useState<FactorPreferencePatch[]>([]);
  const [groupPriorities, setGroupPriorities] = useState<GroupPriorityPatch[]>([]);
  const [objectives, setObjectives] = useState<SearchObjective[]>([
    { factor_id: "pass_terrain_value", importance: "normal" },
  ]);
  const [answeredQuestionIds, setAnsweredQuestionIds] = useState<string[]>([]);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTrip, setCurrentTrip] = useState<CurrentTrip | null>(null);
  const [currentTripSummary, setCurrentTripSummary] =
    useState<CurrentTripSummary | null>(null);
  const [showCurrentTrip, setShowCurrentTrip] = useState(
    window.location.pathname === "/current-trip",
  );

  useEffect(() => {
    void getCurrentTrip()
      .then(setCurrentTrip)
      .catch(() => setCurrentTrip(null));
  }, []);

  useEffect(() => {
    if (!showCurrentTrip || !currentTrip) {
      setCurrentTripSummary(null);
      return;
    }
    void getCurrentTripSummary()
      .then(setCurrentTripSummary)
      .catch(() => setCurrentTripSummary(null));
  }, [showCurrentTrip, currentTrip]);

  const appliedIntent = useMemo(
    () => buildIntent(filters, assumptions, preferences, groupPriorities, objectives),
    [filters, assumptions, preferences, groupPriorities, objectives],
  );

  async function runSearch(
    nextFilters: SearchFilters,
    nextAssumptions: string[],
    nextPreferences: FactorPreferencePatch[],
    nextGroupPriorities: GroupPriorityPatch[],
    nextObjectives: SearchObjective[],
    nextAnsweredQuestionIds: string[],
  ) {
    const validationError = validateFilters(nextFilters);
    if (validationError) {
      setError(validationError);
      setResponse(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await searchResorts({
        intent: buildIntent(
          nextFilters,
          nextAssumptions,
          nextPreferences,
          nextGroupPriorities,
          nextObjectives,
        ),
        brief: brief.trim() || null,
        generate_refinements: true,
        already_answered_question_ids: nextAnsweredQuestionIds,
      });
      setResponse(result);
      setExpandedCandidateId(null);
    } catch (caught) {
      setResponse(null);
      setError(caught instanceof Error ? caught.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    let nextFilters = filters;
    let nextAssumptions = assumptions;
    const trimmedBrief = brief.trim();
    if (trimmedBrief && trimmedBrief !== lastParsedBrief) {
      try {
        const parsed = await parseTripBrief(trimmedBrief);
        nextFilters = mergeParsedFilters(filters, parsed);
        nextAssumptions = parsed.assumptions ?? [];
        setFilters(nextFilters);
        setAssumptions(nextAssumptions);
        setLastParsedBrief(trimmedBrief);
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : "Could not parse the brief.",
        );
        return;
      }
    }
    await runSearch(
      nextFilters,
      nextAssumptions,
      preferences,
      groupPriorities,
      objectives,
      answeredQuestionIds,
    );
  }

  async function applyRefinement(questionId: string, option: RefinementOption) {
    const nextPreferences = upsertBy(
      preferences.filter(
        (item) => !option.objective_patches.some((patch) => patch.factor_id === item.factor_id),
      ),
      option.factor_preference_patches,
      (item) => item.factor_id,
    );
    const nextObjectives = upsertBy(
      objectives.filter(
        (item) =>
          !option.factor_preference_patches.some(
            (patch) => patch.factor_id === item.factor_id,
          ),
      ),
      option.objective_patches,
      (item) => item.factor_id,
    );
    const nextGroups = upsertBy(
      groupPriorities,
      option.group_priority_patches,
      (item) => item.group_id,
    );
    const nextAnswered = [...new Set([...answeredQuestionIds, questionId])];
    setPreferences(nextPreferences);
    setObjectives(nextObjectives);
    setGroupPriorities(nextGroups);
    setAnsweredQuestionIds(nextAnswered);
    await runSearch(
      filters,
      assumptions,
      nextPreferences,
      nextGroups,
      nextObjectives,
      nextAnswered,
    );
  }

  async function removePreference(factorId: string) {
    const next = preferences.filter((item) => item.factor_id !== factorId);
    setPreferences(next);
    if (response) {
      await runSearch(
        filters,
        assumptions,
        next,
        groupPriorities,
        objectives,
        answeredQuestionIds,
      );
    }
  }

  async function removeObjective(factorId: string) {
    const nextObjectives = objectives.filter((item) => item.factor_id !== factorId);
    const nextFilters =
      filters.valueObjective === factorId
        ? { ...filters, valueObjective: "" as const }
        : filters;
    setObjectives(nextObjectives);
    setFilters(nextFilters);
    if (response) {
      await runSearch(
        nextFilters,
        assumptions,
        preferences,
        groupPriorities,
        nextObjectives,
        answeredQuestionIds,
      );
    }
  }

  async function removeGroupPriority(groupId: string) {
    const nextGroups = groupPriorities.filter((item) => item.group_id !== groupId);
    setGroupPriorities(nextGroups);
    if (response) {
      await runSearch(
        filters,
        assumptions,
        preferences,
        nextGroups,
        objectives,
        answeredQuestionIds,
      );
    }
  }

  async function saveConfiguration(configuration: SearchV4Configuration) {
    try {
      const saved = await saveCurrentTrip({
        ski_region_id: configuration.ski_region_id,
        ski_region_name: configuration.ski_region_name,
        stay_destination_id: configuration.stay_destination_id,
        stay_destination_name: configuration.stay_destination_name,
        stay_base_id: configuration.stay_base_id,
        stay_base_name: configuration.stay_base_name,
        focus_ski_area_id: configuration.ski_area_id,
        focus_ski_area_name: configuration.ski_area_name,
        lift_pass_product_id: configuration.selected_pass.lift_pass_product_id,
        lift_pass_product_name: configuration.selected_pass.name,
        travel_month:
          filters.travelWindowMode === "month" ? filters.travelMonth || null : null,
        trip_start_date:
          filters.travelWindowMode === "dates" ? filters.tripStartDate : null,
        trip_end_date:
          filters.travelWindowMode === "dates" ? filters.tripEndDate : null,
        booking_status: "not_booked_yet",
      });
      setCurrentTrip(saved);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save trip.");
    }
  }

  function navigateCurrentTrip(show: boolean) {
    window.history.pushState(null, "", show ? "/current-trip" : "/");
    setShowCurrentTrip(show);
  }

  if (showCurrentTrip) {
    return (
      <Shell currentTrip={currentTrip} onCurrentTrip={() => navigateCurrentTrip(false)}>
        <CurrentTripView
          trip={currentTrip}
          summary={currentTripSummary}
          onBack={() => navigateCurrentTrip(false)}
          onClear={async () => {
            await clearCurrentTrip();
            setCurrentTrip(null);
          }}
        />
      </Shell>
    );
  }

  return (
    <Shell currentTrip={currentTrip} onCurrentTrip={() => navigateCurrentTrip(true)}>
      <main className="mx-auto grid w-full max-w-[92rem] gap-6 px-4 py-8 lg:grid-cols-[24rem_minmax(0,1fr)] lg:px-8">
        <form
          onSubmit={handleSubmit}
          className="h-fit rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50"
        >
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-700">
            Search V4
          </p>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight">
            Find your best ski trip
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Start broad. Snowcast will ask only questions that can materially
            change the result.
          </p>

          <label className="mt-6 block text-sm font-semibold">
            What matters to you?
            <textarea
              value={brief}
              onChange={(event) => setBrief(event.target.value)}
              className="mt-2 min-h-24 w-full rounded-2xl border border-slate-300 p-3 font-normal"
              placeholder="A snow-reliable intermediate trip with lively après…"
            />
          </label>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <Field label="Country">
              <input
                value={filters.location}
                onChange={(event) =>
                  setFilters({ ...filters, location: event.target.value })
                }
                className="control"
              />
            </Field>
            <Field label="Skill">
              <select
                value={filters.skillLevel}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    skillLevel: event.target.value as SearchFilters["skillLevel"],
                  })
                }
                className="control"
              >
                <option value="">Not specified</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </Field>
            <Field label="Max nightly">
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={filters.maxPrice}
                onChange={(event) =>
                  setFilters({ ...filters, maxPrice: event.target.value })
                }
                className="control"
              />
            </Field>
            <Field label="Minimum stay tier">
              <select
                value={filters.stars}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    stars: event.target.value as SearchFilters["stars"],
                  })
                }
                className="control"
              >
                <option value="">Any</option>
                <option value="1">Budget+</option>
                <option value="2">Standard+</option>
                <option value="3">Premium</option>
              </select>
            </Field>
          </div>

          <Field label="Travel window" className="mt-4">
            <select
              value={filters.travelWindowMode}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  travelWindowMode: event.target
                    .value as SearchFilters["travelWindowMode"],
                })
              }
              className="control"
            >
              <option value="any">Any time</option>
              <option value="month">Month</option>
              <option value="dates">Exact dates</option>
            </select>
          </Field>
          {filters.travelWindowMode === "month" ? (
            <select
              aria-label="Travel month"
              value={filters.travelMonth}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  travelMonth: Number(event.target.value) as TravelMonth,
                })
              }
              className="control mt-2"
            >
              {monthOptions.map((month, index) => (
                <option key={month} value={index + 1}>
                  {month}
                </option>
              ))}
            </select>
          ) : null}
          {filters.travelWindowMode === "dates" ? (
            <div className="mt-2 grid grid-cols-2 gap-3">
              <input
                aria-label="Trip start date"
                type="date"
                value={filters.tripStartDate}
                onChange={(event) =>
                  setFilters({ ...filters, tripStartDate: event.target.value })
                }
                className="control"
              />
              <input
                aria-label="Trip end date"
                type="date"
                value={filters.tripEndDate}
                onChange={(event) =>
                  setFilters({ ...filters, tripEndDate: event.target.value })
                }
                className="control"
              />
            </div>
          ) : null}

          <div className="mt-4 grid grid-cols-2 gap-3">
            <Field label="Origin">
              <input
                value={filters.originText}
                onChange={(event) =>
                  setFilters({ ...filters, originText: event.target.value })
                }
                placeholder="Berlin"
                className="control"
              />
            </Field>
            <Field label="Hard drive limit">
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={filters.maxDriveHours}
                onChange={(event) =>
                  setFilters({ ...filters, maxDriveHours: event.target.value })
                }
                placeholder="hours"
                className="control"
              />
            </Field>
          </div>

          <Field label="Value objective" className="mt-4">
            <select
              value={filters.valueObjective}
              onChange={(event) => {
                const factorId = event.target
                  .value as SearchFilters["valueObjective"];
                setFilters({ ...filters, valueObjective: factorId });
                setObjectives(
                  factorId
                    ? [{ factor_id: factorId, importance: "normal" }]
                    : [],
                );
              }}
              className="control"
            >
              <option value="">No pass-value priority</option>
              <option value="pass_terrain_value">Most terrain for pass price</option>
              <option value="pass_price_per_day">Lowest pass price per day</option>
            </select>
          </Field>

          <fieldset className="mt-5">
            <legend className="text-sm font-semibold">Extra preferences</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {featureOptions.map(([factorId, label]) => {
                const active = preferences.some(
                  (item) => item.factor_id === factorId && item.mode === "prefer",
                );
                return (
                  <button
                    type="button"
                    key={factorId}
                    aria-pressed={active}
                    onClick={() => {
                      const next = active
                        ? preferences.filter((item) => item.factor_id !== factorId)
                        : upsertBy(
                            preferences,
                            [
                              {
                                factor_id: factorId,
                                mode: "prefer",
                                values: [],
                                importance: "normal",
                              },
                            ],
                            (item) => item.factor_id,
                          );
                      setPreferences(next);
                    }}
                    className={`rounded-full border px-3 py-2 text-xs font-semibold ${
                      active
                        ? "border-blue-700 bg-blue-700 text-white"
                        : "border-slate-300 bg-white text-slate-700"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <button
            type="submit"
            disabled={loading}
            className="mt-6 w-full rounded-2xl bg-blue-700 px-5 py-3 font-bold text-white shadow-lg shadow-blue-700/20 disabled:opacity-60"
          >
            {loading ? "Ranking trips…" : "Search and rank"}
          </button>
          {error ? (
            <p role="alert" className="mt-3 text-sm font-medium text-red-700">
              {error}
            </p>
          ) : null}
        </form>

        <section aria-live="polite">
          <AppliedIntent
            intent={appliedIntent}
            onRemovePreference={(factorId) => void removePreference(factorId)}
            onRemoveObjective={(factorId) => void removeObjective(factorId)}
            onRemoveGroupPriority={(groupId) => void removeGroupPriority(groupId)}
          />
          {response ? (
            <>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-600">
                    {response.eligible_candidate_count} eligible configurations ·{" "}
                    {response.excluded_candidate_count} filtered out
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {response.search_model_version} · {response.ranking_policy_version}
                  </p>
                </div>
                {response.ranking_status === "unscored" ? (
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-bold text-amber-900">
                    Unranked: {response.unscored_reason}
                  </span>
                ) : null}
              </div>
              <Refinements
                response={response}
                loading={loading}
                onApply={(questionId, option) =>
                  void applyRefinement(questionId, option)
                }
              />
              {response.results.length ? (
                <div className="space-y-4">
                  {response.results.map((result) => (
                    <ResultCard
                      key={result.ski_region_id}
                      result={result}
                      expandedCandidateId={expandedCandidateId}
                      onExpand={setExpandedCandidateId}
                      onSave={(configuration) => void saveConfiguration(configuration)}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState text="No configuration satisfies all hard constraints." />
              )}
            </>
          ) : loading ? (
            <EmptyState text="Evaluating catalog, pass, climate, and forecast evidence…" />
          ) : (
            <EmptyState text="Your ranked trip configurations will appear here." />
          )}
        </section>
      </main>
    </Shell>
  );
}

function Shell({
  children,
  currentTrip,
  onCurrentTrip,
}: {
  children: React.ReactNode;
  currentTrip: CurrentTrip | null;
  onCurrentTrip: () => void;
}) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="bg-gradient-to-r from-[#07182f] to-[#0b5fb8] px-4 py-4 lg:px-8">
        <div className="mx-auto flex max-w-[92rem] items-center justify-between">
          <SnowcastLogo compact />
          <button
            onClick={onCurrentTrip}
            className="rounded-full border border-white/30 px-4 py-2 text-sm font-semibold text-white"
          >
            {currentTrip ? "Current trip" : "Trip companion"}
          </button>
        </div>
      </header>
      {children}
    </div>
  );
}

function Field({
  label,
  className = "",
  children,
}: {
  label: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <label className={`block text-sm font-semibold ${className}`}>
      {label}
      <span className="mt-2 block font-normal">{children}</span>
    </label>
  );
}

function AppliedIntent({
  intent,
  onRemovePreference,
  onRemoveObjective,
  onRemoveGroupPriority,
}: {
  intent: SearchIntent;
  onRemovePreference: (factorId: string) => void;
  onRemoveObjective: (factorId: string) => void;
  onRemoveGroupPriority: (groupId: string) => void;
}) {
  const chips = [
    ...intent.objectives.map((item) => ({
      id: `objective-${item.factor_id}`,
      label: `Optimize ${factorLabels[item.factor_id] ?? item.factor_id}`,
      removalKind: "objective" as const,
      factorId: item.factor_id,
    })),
    ...intent.group_priorities.map((item) => ({
      id: `group-${item.group_id}`,
      label: `${groupLabels[item.group_id] ?? item.group_id}: ${item.importance}`,
      removalKind: "group" as const,
      factorId: item.group_id,
    })),
    ...intent.factor_preferences.map((item) => ({
      id: `factor-${item.factor_id}`,
      label: `${item.mode} ${factorLabels[item.factor_id] ?? item.factor_id}${
        item.values.length ? `: ${item.values.join(", ")}` : ""
      }`,
      removalKind: "preference" as const,
      factorId: item.factor_id,
    })),
  ];
  if (!chips.length) return null;
  return (
    <div className="mb-4 flex flex-wrap gap-2" aria-label="Applied search intent">
      {chips.map((chip) => (
        <span
          key={chip.id}
          className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold"
        >
          {chip.label}
          <button
            aria-label={`Remove ${chip.label}`}
            onClick={() => {
              if (chip.removalKind === "objective") {
                onRemoveObjective(chip.factorId);
              } else if (chip.removalKind === "group") {
                onRemoveGroupPriority(chip.factorId);
              } else {
                onRemovePreference(chip.factorId);
              }
            }}
            className="text-slate-500"
          >
            ×
          </button>
        </span>
      ))}
    </div>
  );
}

function Refinements({
  response,
  loading,
  onApply,
}: {
  response: SearchResponse;
  loading: boolean;
  onApply: (questionId: string, option: RefinementOption) => void;
}) {
  if (!response.refinements.length) return null;
  return (
    <div className="mb-5 grid gap-3 xl:grid-cols-2">
      {response.refinements.map((item) => (
        <article
          key={item.question_id}
          className="rounded-3xl border border-blue-200 bg-blue-50 p-5"
        >
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">
            This can reorder your results
          </p>
          <h2 className="mt-2 text-lg font-bold">{item.question}</h2>
          <p className="mt-1 text-sm text-slate-600">{item.reason}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {item.options.map((option) => (
              <button
                key={option.label}
                onClick={() => onApply(item.question_id, option)}
                disabled={loading}
                title={option.description}
                className="rounded-xl bg-white px-3 py-2 text-sm font-bold text-blue-800 shadow-sm disabled:cursor-wait disabled:opacity-60"
              >
                {option.label}
              </button>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function ResultCard({
  result,
  expandedCandidateId,
  onExpand,
  onSave,
}: {
  result: SearchV4RecommendationGroup;
  expandedCandidateId: string | null;
  onExpand: (candidateId: string | null) => void;
  onSave: (configuration: SearchV4Configuration) => void;
}) {
  const configuration = result.top_configuration;
  const expanded = expandedCandidateId === configuration.candidate_id;
  return (
    <article className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-lg shadow-slate-200/40">
      <div className="grid gap-5 p-6 md:grid-cols-[minmax(0,1fr)_9rem]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-900 px-2.5 py-1 text-xs font-bold text-white">
              {configuration.ranking_status === "ranked"
                ? `#${result.rank}`
                : "Unranked option"}
            </span>
            <span className="text-sm font-semibold text-slate-500">
              {configuration.stay_destination_name} · {configuration.stay_base_name}
            </span>
          </div>
          <h2 className="mt-3 font-display text-2xl font-semibold">
            {result.ski_region_name}
          </h2>
          <p className="mt-1 text-slate-600">
            Ski {configuration.ski_area_name} with {configuration.selected_pass.name}
          </p>
          <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold">
            <Pill>{formatAccess(configuration)}</Pill>
            <Pill>
              {configuration.selected_pass.accessible_piste_km != null
                ? `${configuration.selected_pass.accessible_piste_km} km pass coverage`
                : "Pass terrain unresolved"}
            </Pill>
            <Pill>{formatPassPrice(configuration)}</Pill>
            <Pill>{formatLodging(configuration)}</Pill>
          </div>
        </div>
        <div className="flex flex-col items-end justify-between">
          {configuration.fit_score != null ? (
            <div className="text-right">
              <p className="text-4xl font-bold text-blue-700">
                {configuration.fit_score.toFixed(1)}
              </p>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                fit / 100
              </p>
            </div>
          ) : (
            <p className="rounded-full bg-amber-100 px-3 py-1 text-sm font-bold">
              Unranked
            </p>
          )}
          <button
            onClick={() => onSave(configuration)}
            className="mt-4 rounded-xl bg-blue-700 px-4 py-2 text-sm font-bold text-white"
          >
            Save trip
          </button>
        </div>
      </div>
      <button
        onClick={() => onExpand(expanded ? null : configuration.candidate_id)}
        className="w-full border-t border-slate-200 px-6 py-3 text-left text-sm font-bold text-blue-800"
      >
        {expanded
          ? "Hide evidence"
          : configuration.ranking_status === "ranked"
            ? "Why this fit?"
            : "Show evidence"}
      </button>
      {expanded ? <RankingExplanation configuration={configuration} /> : null}
    </article>
  );
}

function RankingExplanation({
  configuration,
}: {
  configuration: SearchV4Configuration;
}) {
  return (
    <div className="border-t border-slate-200 bg-slate-50 p-6">
      <h3 className="font-bold">Group contributions</h3>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {configuration.groups.map((group) => (
          <div key={group.group_id} className="rounded-2xl bg-white p-3">
            <p className="text-sm font-bold">
              {groupLabels[group.group_id] ?? group.group_id}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {(group.normalized_share * 100).toFixed(0)}% budget ·{" "}
              {group.contribution_points.toFixed(1)} points
            </p>
          </div>
        ))}
      </div>
      <h3 className="mt-6 font-bold">Factor evidence</h3>
      <div className="mt-3 space-y-2">
        {configuration.factors.map((factor) => (
          <div
            key={factor.factor_id}
            className="grid gap-2 rounded-2xl bg-white p-3 sm:grid-cols-[12rem_1fr_8rem]"
          >
            <p className="text-sm font-bold">
              {factorLabels[factor.factor_id] ?? factor.factor_id}
            </p>
            <div>
              <p className="text-xs text-slate-600">{factor.provenance_summary}</p>
              {factor.warnings.length ? (
                <p className="mt-1 text-xs font-semibold text-amber-800">
                  {factor.warnings.join(" · ")}
                </p>
              ) : null}
            </div>
            <p className="text-right text-xs font-bold">
              {factor.effective_evidence_cap === 0
                ? "Unknown"
                : `${factor.contribution_points.toFixed(1)} points`}
            </p>
          </div>
        ))}
      </div>
      {configuration.constraint_warnings.length ? (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-bold">Constraint uncertainty</p>
          {configuration.constraint_warnings.map((warning) => (
            <p key={`${warning.constraint_id}-${warning.code}`} className="mt-1 text-sm">
              {warning.message}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5">
      {children}
    </span>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex min-h-72 items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white/70 p-8 text-center text-slate-500">
      {text}
    </div>
  );
}

function CurrentTripView({
  trip,
  summary,
  onBack,
  onClear,
}: {
  trip: CurrentTrip | null;
  summary: CurrentTripSummary | null;
  onBack: () => void;
  onClear: () => void;
}) {
  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <button onClick={onBack} className="text-sm font-bold text-blue-700">
        ← Back to search
      </button>
      <div className="mt-5 rounded-3xl border border-slate-200 bg-white p-7 shadow-xl">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">
          Trip companion
        </p>
        {trip ? (
          <>
            <h1 className="mt-2 text-3xl font-bold">{trip.ski_region_name}</h1>
            <p className="mt-2 text-slate-600">
              {trip.stay_base_name} · {trip.focus_ski_area_name} ·{" "}
              {trip.lift_pass_product_name}
            </p>
            {summary ? (
              <div className="mt-6 rounded-2xl bg-blue-50 p-5">
                <p className="font-bold">Current conditions</p>
                <p className="mt-2">{summary.current_conditions.weather_summary}</p>
                <p className="mt-2 text-sm text-slate-600">{summary.delta.summary}</p>
              </div>
            ) : null}
            <button
              onClick={onClear}
              className="mt-6 rounded-xl border border-red-200 px-4 py-2 text-sm font-bold text-red-700"
            >
              Clear current trip
            </button>
          </>
        ) : (
          <p className="mt-4 text-slate-600">
            Save a ranked configuration in the authenticated mobile app to track it.
          </p>
        )}
      </div>
    </main>
  );
}

function buildIntent(
  filters: SearchFilters,
  assumptions: string[],
  preferences: FactorPreferencePatch[],
  groupPriorities: GroupPriorityPatch[],
  objectives: SearchObjective[],
): SearchIntent {
  const constraints: SearchIntent["constraints"] = {};
  if (filters.location.trim()) {
    constraints.location = { country: filters.location.trim() };
  }
  if (filters.travelWindowMode === "month" && filters.travelMonth) {
    constraints.travel_window = { month: filters.travelMonth };
  } else if (
    filters.travelWindowMode === "dates" &&
    filters.tripStartDate &&
    filters.tripEndDate
  ) {
    constraints.travel_window = {
      start_date: filters.tripStartDate,
      end_date: filters.tripEndDate,
    };
  }
  const maximum = Number(filters.maxPrice);
  if (Number.isFinite(maximum) && maximum > 0) {
    constraints.lodging_budget = {
      mode: "lodging_nightly",
      maximum,
      currency: "EUR",
      budget_flex: Number(filters.budgetFlex) || 0,
    };
  }
  if (filters.stars) {
    constraints.minimum_stay_quality = {
      minimum_score: (Number(filters.stars) / 3) * 10,
    };
  }
  const maximumDrive = Number(filters.maxDriveHours);
  if (
    filters.originText.trim() &&
    Number.isFinite(maximumDrive) &&
    maximumDrive > 0
  ) {
    constraints.travel_limit = {
      maximum_duration_hours: maximumDrive,
      mode: "car",
    };
  }
  return {
    constraints,
    party: {
      skill_levels: filters.skillLevel ? [filters.skillLevel] : [],
    },
    travel_context: filters.originText.trim()
      ? { origin_text: filters.originText.trim(), mode: "car" }
      : {},
    objectives,
    group_priorities: groupPriorities,
    factor_preferences: preferences,
    assumptions,
  };
}

function mergeParsedFilters(
  current: SearchFilters,
  parsed: ParsedQueryResponse,
): SearchFilters {
  const next = { ...current };
  if (parsed.filters.location) next.location = parsed.filters.location;
  if (parsed.filters.max_price != null) {
    next.maxPrice = String(parsed.filters.max_price);
  }
  if (parsed.filters.stars != null && parsed.filters.stars >= 1) {
    next.stars = String(Math.min(3, parsed.filters.stars)) as SearchFilters["stars"];
  }
  if (parsed.filters.skill_level) next.skillLevel = parsed.filters.skill_level;
  if (parsed.filters.trip_start_date && parsed.filters.trip_end_date) {
    next.travelWindowMode = "dates";
    next.tripStartDate = parsed.filters.trip_start_date;
    next.tripEndDate = parsed.filters.trip_end_date;
  } else if (parsed.filters.travel_month) {
    next.travelWindowMode = "month";
    next.travelMonth = parsed.filters.travel_month;
  }
  if (parsed.trip_context?.origin_text) {
    next.originText = parsed.trip_context.origin_text;
  }
  return next;
}

function validateFilters(filters: SearchFilters): string | null {
  if (!filters.location.trim()) return "Choose a country.";
  if (
    filters.travelWindowMode === "dates" &&
    (!filters.tripStartDate || !filters.tripEndDate)
  ) {
    return "Provide both trip dates.";
  }
  if (
    filters.travelWindowMode === "dates" &&
    filters.tripEndDate < filters.tripStartDate
  ) {
    return "The end date must be on or after the start date.";
  }
  const maximumText = filters.maxPrice.trim();
  const maximum = Number(maximumText);
  if (maximumText && (!Number.isFinite(maximum) || maximum <= 0)) {
    return "Maximum nightly price must be greater than 0.";
  }
  const maximumDriveText = filters.maxDriveHours.trim();
  const maximumDrive = Number(maximumDriveText);
  if (
    maximumDriveText &&
    (!Number.isFinite(maximumDrive) || maximumDrive <= 0)
  ) {
    return "Hard drive limit must be greater than 0 hours.";
  }
  if (maximumDriveText && !filters.originText.trim()) {
    return "Provide an origin to use a hard drive limit.";
  }
  const flex = Number(filters.budgetFlex);
  if (filters.budgetFlex && (!Number.isFinite(flex) || flex < 0 || flex > 0.5)) {
    return "Budget flexibility must be between 0 and 0.5.";
  }
  return null;
}

function upsertBy<T>(
  current: T[],
  patches: T[],
  key: (item: T) => string,
): T[] {
  const patchKeys = new Set(patches.map(key));
  return [...current.filter((item) => !patchKeys.has(key(item))), ...patches];
}

function formatAccess(configuration: SearchV4Configuration): string {
  const value = configuration.access.access_mode.replaceAll("_", " ");
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatPassPrice(configuration: SearchV4Configuration): string {
  const price = configuration.selected_pass.price;
  if (!price) return "Comparable pass price unavailable";
  if (price.amount != null) {
    return `${price.currency} ${price.amount} / ${price.duration_days} days`;
  }
  if (price.amount_max != null) {
    return `${price.currency} ${price.amount_min}-${price.amount_max} / ${price.duration_days} days`;
  }
  return "Pass price unresolved";
}

function formatLodging(configuration: SearchV4Configuration): string {
  const estimate = configuration.lodging_estimate;
  if (!estimate) return "Lodging estimate unavailable";
  return `${estimate.currency} ${estimate.minimum}-${estimate.maximum} nightly (${estimate.trust_status})`;
}

export default App;
