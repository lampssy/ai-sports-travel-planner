import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";

import {
  clearCurrentTrip,
  getCurrentTrip,
  getCurrentTripSummary,
  parseTripBrief,
  saveCurrentTrip,
  searchResorts,
} from "./api";
import {
  APP_NAVIGATION_EVENT,
  navigate,
  parseAppRoute,
  type AppRoute,
} from "./navigation";
import { Homepage } from "./search/Homepage";
import {
  SearchCommandHeader,
} from "./search/SearchCommandHeader";
import { RecommendationBoard } from "./search/RecommendationBoard";
import { SearchFiltersDrawer } from "./search/SearchFiltersDrawer";
import {
  buildParsedChips,
  type ParsedChip,
} from "./search/searchPresentation";
import {
  buildSearchIntent,
  createSearchSession,
  defaultSearchFilters,
  dismissRefinement,
  mergeParsedFilters,
  rankChangeSummary,
  reconcileSearchSession,
  upsertBy,
  validateSearchFilters,
  type SearchSession,
} from "./search/searchSession";
import type {
  CurrentTrip,
  CurrentTripSummary,
  FactorPreferencePatch,
  GroupPriorityPatch,
  RefinementOption,
  SearchFilters,
  SearchObjective,
  SearchV4Configuration,
} from "./types";
import { AppShell, CurrentTripView } from "./ui/AppShell";

interface PreviousSearchState {
  filters: SearchFilters;
  assumptions: string[];
  preferences: FactorPreferencePatch[];
  groupPriorities: GroupPriorityPatch[];
  objectives: SearchObjective[];
  answeredQuestionIds: string[];
}

function App() {
  const [route, setRoute] = useState<AppRoute>(() => parseAppRoute(window.location));
  const [filters, setFilters] = useState<SearchFilters>(defaultSearchFilters);
  const [brief, setBrief] = useState("");
  const [lastParsedBrief, setLastParsedBrief] = useState("");
  const [assumptions, setAssumptions] = useState<string[]>([]);
  const [preferences, setPreferences] = useState<FactorPreferencePatch[]>([]);
  const [groupPriorities, setGroupPriorities] = useState<GroupPriorityPatch[]>([]);
  const [objectives, setObjectives] = useState<SearchObjective[]>([
    { factor_id: "pass_terrain_value", importance: "normal" },
  ]);
  const [answeredQuestionIds, setAnsweredQuestionIds] = useState<string[]>([]);
  const [session, setSession] = useState<SearchSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refinementError, setRefinementError] = useState<string | null>(null);
  const [rankFeedback, setRankFeedback] = useState<string | null>(null);
  const [changedRankGroupIds, setChangedRankGroupIds] = useState<Set<string>>(
    new Set(),
  );
  const [undoState, setUndoState] = useState<PreviousSearchState | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [focusRequest, setFocusRequest] = useState(0);
  const [currentTrip, setCurrentTrip] = useState<CurrentTrip | null>(null);
  const [currentTripSummary, setCurrentTripSummary] =
    useState<CurrentTripSummary | null>(null);
  const adjustFiltersRef = useRef<HTMLButtonElement>(null);
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const syncRoute = () => {
      const nextRoute = parseAppRoute(window.location);
      if (nextRoute.name === "search" && window.location.pathname !== "/") {
        window.history.replaceState(null, "", "/");
      }
      setRoute(nextRoute);
    };
    window.addEventListener(APP_NAVIGATION_EVENT, syncRoute);
    window.addEventListener("popstate", syncRoute);
    syncRoute();
    return () => {
      window.removeEventListener(APP_NAVIGATION_EVENT, syncRoute);
      window.removeEventListener("popstate", syncRoute);
    };
  }, []);

  useEffect(() => {
    void getCurrentTrip()
      .then((trip) => {
        if (trip) setCurrentTrip(trip);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (route.name !== "currentTrip" || !currentTrip) {
      setCurrentTripSummary(null);
      return;
    }
    void getCurrentTripSummary()
      .then(setCurrentTripSummary)
      .catch(() => setCurrentTripSummary(null));
  }, [route.name, currentTrip]);

  useEffect(() => {
    if (focusRequest > 0 && session) {
      resultsHeadingRef.current?.focus();
    }
  }, [focusRequest]);

  const appliedIntent = useMemo(
    () =>
      buildSearchIntent(
        filters,
        assumptions,
        preferences,
        groupPriorities,
        objectives,
      ),
    [filters, assumptions, preferences, groupPriorities, objectives],
  );

  async function fetchSearch(
    nextFilters: SearchFilters,
    nextAssumptions: string[],
    nextPreferences: FactorPreferencePatch[],
    nextGroupPriorities: GroupPriorityPatch[],
    nextObjectives: SearchObjective[],
    nextAnsweredQuestionIds: string[],
    nextBrief: string,
    focusResults: boolean,
  ) {
    const validationError = validateSearchFilters(nextFilters);
    if (validationError) {
      setError(validationError);
      return null;
    }
    const intent = buildSearchIntent(
      nextFilters,
      nextAssumptions,
      nextPreferences,
      nextGroupPriorities,
      nextObjectives,
    );
    const response = await searchResorts({
      intent,
      brief: nextBrief.trim() || null,
      generate_refinements: true,
      already_answered_question_ids: nextAnsweredQuestionIds,
    });
    setSession((current) => {
      const next = current
        ? reconcileSearchSession(current, intent, response)
        : createSearchSession(nextBrief, intent, response);
      return { ...next, brief: nextBrief };
    });
    setError(null);
    if (focusResults) setFocusRequest((current) => current + 1);
    return response;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setError(null);
    let nextFilters = filters;
    let nextAssumptions = assumptions;
    const trimmedBrief = brief.trim();
    try {
      if (trimmedBrief && trimmedBrief !== lastParsedBrief) {
        const parsed = await parseTripBrief(trimmedBrief);
        nextFilters = mergeParsedFilters(filters, parsed);
        nextAssumptions = parsed.assumptions ?? [];
        setFilters(nextFilters);
        setAssumptions(nextAssumptions);
        setLastParsedBrief(trimmedBrief);
      }
      await fetchSearch(
        nextFilters,
        nextAssumptions,
        preferences,
        groupPriorities,
        objectives,
        answeredQuestionIds,
        brief,
        true,
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not complete the search.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function applyRefinement(questionId: string, option: RefinementOption) {
    if (loading) return;
    const nextPreferences = upsertBy(
      preferences.filter(
        (item) =>
          !option.objective_patches.some(
            (patch) => patch.factor_id === item.factor_id,
          ),
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
    const previousState: PreviousSearchState = {
      filters,
      assumptions,
      preferences,
      groupPriorities,
      objectives,
      answeredQuestionIds,
    };
    const previousResponse = session?.response;
    const scrollY = window.scrollY;
    setLoading(true);
    setRefinementError(null);
    try {
      const nextResponse = await fetchSearch(
        filters,
        assumptions,
        nextPreferences,
        nextGroups,
        nextObjectives,
        nextAnswered,
        brief,
        false,
      );
      if (!nextResponse) return;
      setPreferences(nextPreferences);
      setObjectives(nextObjectives);
      setGroupPriorities(nextGroups);
      setAnsweredQuestionIds(nextAnswered);
      setUndoState(previousState);
      if (previousResponse) {
        const summary = rankChangeSummary(previousResponse, nextResponse);
        setRankFeedback(summary.announcement);
        setChangedRankGroupIds(summary.changedGroupIds);
        window.setTimeout(() => setChangedRankGroupIds(new Set()), 2400);
      }
      if (window.scrollY !== scrollY) {
        window.requestAnimationFrame(() => window.scrollTo({ top: scrollY }));
      }
    } catch (caught) {
      setRefinementError(
        caught instanceof Error ? caught.message : "Could not rerank these results.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function undoRefinement() {
    if (!undoState || loading) return;
    setLoading(true);
    setRefinementError(null);
    try {
      await fetchSearch(
        undoState.filters,
        undoState.assumptions,
        undoState.preferences,
        undoState.groupPriorities,
        undoState.objectives,
        undoState.answeredQuestionIds,
        brief,
        false,
      );
      setFilters(undoState.filters);
      setAssumptions(undoState.assumptions);
      setPreferences(undoState.preferences);
      setGroupPriorities(undoState.groupPriorities);
      setObjectives(undoState.objectives);
      setAnsweredQuestionIds(undoState.answeredQuestionIds);
      setUndoState(null);
      setRankFeedback("Previous trip decisions restored.");
      setChangedRankGroupIds(new Set());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not restore results.");
    } finally {
      setLoading(false);
    }
  }

  async function removeChip(chip: ParsedChip) {
    let nextFilters = filters;
    let nextPreferences = preferences;
    let nextGroups = groupPriorities;
    let nextObjectives = objectives;
    const action = chip.action;
    switch (action.kind) {
      case "location":
        nextFilters = { ...filters, location: "" };
        break;
      case "travelWindow":
        nextFilters = { ...filters, travelWindowMode: "any", travelMonth: "" };
        break;
      case "lodgingBudget":
        nextFilters = { ...filters, maxPrice: "" };
        break;
      case "stayQuality":
        nextFilters = { ...filters, stars: "" };
        break;
      case "travelLimit":
        nextFilters = { ...filters, maxDriveHours: "" };
        break;
      case "skill":
        nextFilters = { ...filters, skillLevel: "" };
        break;
      case "objective":
        nextObjectives = objectives.filter(
          (item) => item.factor_id !== action.id,
        );
        nextFilters =
          filters.valueObjective === action.id
            ? { ...filters, valueObjective: "" }
            : filters;
        break;
      case "group":
        nextGroups = groupPriorities.filter(
          (item) => item.group_id !== action.id,
        );
        break;
      case "preference":
        nextPreferences = preferences.filter(
          (item) => item.factor_id !== action.id,
        );
        break;
    }
    setFilters(nextFilters);
    setPreferences(nextPreferences);
    setGroupPriorities(nextGroups);
    setObjectives(nextObjectives);
    if (!session || loading) return;
    setLoading(true);
    try {
      await fetchSearch(
        nextFilters,
        assumptions,
        nextPreferences,
        nextGroups,
        nextObjectives,
        answeredQuestionIds,
        brief,
        false,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Search failed.");
    } finally {
      setLoading(false);
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

  const goToSearch = () => navigate("/");
  const goToCurrentTrip = () => navigate("/current-trip");

  if (route.name === "currentTrip") {
    return (
      <AppShell
        active="currentTrip"
        onSearch={goToSearch}
        onCurrentTrip={goToCurrentTrip}
      >
        <CurrentTripView
          trip={currentTrip}
          summary={currentTripSummary}
          onBack={goToSearch}
          onClear={() => {
            void clearCurrentTrip().then(() => setCurrentTrip(null));
          }}
        />
      </AppShell>
    );
  }

  const drawer = (
    <SearchFiltersDrawer
      open={drawerOpen}
      filters={filters}
      preferences={preferences}
      returnFocusRef={adjustFiltersRef}
      onFiltersChange={setFilters}
      onPreferencesChange={setPreferences}
      onObjectivesChange={setObjectives}
      onClose={() => setDrawerOpen(false)}
    />
  );

  if (session) {
    return (
      <AppShell
        active="search"
        onSearch={goToSearch}
        onCurrentTrip={goToCurrentTrip}
        header={
          <SearchCommandHeader
            brief={brief}
            loading={loading}
            onBriefChange={setBrief}
            onSubmit={handleSubmit}
            onSearch={goToSearch}
            onCurrentTrip={goToCurrentTrip}
          />
        }
      >
        <RecommendationBoard
          session={session}
          loading={loading}
          error={error}
          refinementError={refinementError}
          rankFeedback={rankFeedback}
          changedRankGroupIds={changedRankGroupIds}
          canUndo={undoState !== null}
          headingRef={resultsHeadingRef}
          adjustFiltersRef={adjustFiltersRef}
          onOpenFilters={() => setDrawerOpen(true)}
          onRemoveChip={(chip) => void removeChip(chip)}
          onApplyRefinement={(questionId, option) =>
            void applyRefinement(questionId, option)
          }
          onSkipRefinement={(questionId) =>
            setSession((current) =>
              current ? dismissRefinement(current, questionId) : current,
            )
          }
          onToggleGroup={(skiRegionId) =>
            setSession((current) => {
              if (!current) return current;
              const expandedGroupIds = new Set(current.expandedGroupIds);
              if (expandedGroupIds.has(skiRegionId)) {
                expandedGroupIds.delete(skiRegionId);
              } else {
                expandedGroupIds.add(skiRegionId);
              }
              return { ...current, expandedGroupIds };
            })
          }
          onSelectCandidate={(skiRegionId, candidateId) =>
            setSession((current) =>
              current
                ? {
                    ...current,
                    selectedCandidateIdByGroup: {
                      ...current.selectedCandidateIdByGroup,
                      [skiRegionId]: candidateId,
                    },
                  }
                : current,
            )
          }
          onSave={(configuration) => void saveConfiguration(configuration)}
          onUndo={() => void undoRefinement()}
        />
        {drawer}
      </AppShell>
    );
  }

  return (
    <AppShell active="search" onSearch={goToSearch} onCurrentTrip={goToCurrentTrip}>
      <Homepage
        brief={brief}
        loading={loading}
        error={error}
        chips={buildParsedChips(appliedIntent)}
        adjustFiltersRef={adjustFiltersRef}
        onBriefChange={setBrief}
        onSubmit={handleSubmit}
        onOpenFilters={() => setDrawerOpen(true)}
        onRemoveChip={(chip) => void removeChip(chip)}
      />
      {drawer}
    </AppShell>
  );
}

export default App;
