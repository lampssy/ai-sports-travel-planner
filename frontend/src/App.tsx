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
  buildDossierHref,
  navigate,
  parseAppRoute,
  type AppRoute,
} from "./navigation";
import { Homepage } from "./search/Homepage";
import { RecommendationDossier } from "./search/RecommendationDossier";
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
  findSelectedCandidate,
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

interface PendingRerankScrollRestore {
  scrollY: number;
  response: SearchSession["response"] | null;
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
  const pendingRerankScrollRestoreRef =
    useRef<PendingRerankScrollRestore | null>(null);
  const routeRef = useRef(route);
  const pendingDossierScrollRestoreRef = useRef(false);
  const [rerankRestoreRequest, setRerankRestoreRequest] = useState(0);

  useEffect(() => {
    const syncRoute = () => {
      const nextRoute = parseAppRoute(window.location);
      if (nextRoute.name === "search" && window.location.pathname !== "/") {
        window.history.replaceState(null, "", "/");
      }
      if (nextRoute.name !== "search") {
        pendingRerankScrollRestoreRef.current = null;
      }
      if (nextRoute.name === "search" && routeRef.current.name === "dossier") {
        pendingDossierScrollRestoreRef.current = true;
      }
      routeRef.current = nextRoute;
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
    const handleDossierLinkClick = (event: MouseEvent) => {
      if (
        route.name !== "search" ||
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey ||
        !(event.target instanceof Element)
      ) {
        return;
      }
      const anchor = event.target.closest<HTMLAnchorElement>(
        'a[href^="/recommendations/"]',
      );
      if (!anchor || anchor.target === "_blank") return;
      const destination = new URL(anchor.href, window.location.href);
      if (destination.origin !== window.location.origin) return;

      event.preventDefault();
      const resultsScrollY = window.scrollY;
      const nextRoute = parseAppRoute(destination as unknown as Location);
      setSession((current) =>
        current
          ? {
              ...current,
              resultsScrollY,
              dossierGroupId:
                nextRoute.name === "dossier" ? nextRoute.skiRegionId : null,
            }
          : current,
      );
      navigate(`${destination.pathname}${destination.search}`);
      window.scrollTo(0, 0);
    };

    document.addEventListener("click", handleDossierLinkClick);
    return () => document.removeEventListener("click", handleDossierLinkClick);
  }, [route.name]);

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
      resultsHeadingRef.current?.focus({ preventScroll: true });
    }
  }, [focusRequest]);

  useEffect(() => {
    if (route.name !== "search" || !pendingDossierScrollRestoreRef.current) {
      return;
    }
    if (!session) {
      pendingDossierScrollRestoreRef.current = false;
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      if (routeRef.current.name !== "search") return;
      window.scrollTo(0, session.resultsScrollY);
      pendingDossierScrollRestoreRef.current = false;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [route.name, session]);

  useEffect(() => {
    const pending = pendingRerankScrollRestoreRef.current;
    if (
      route.name !== "search" ||
      !pending ||
      pending.response !== session?.response
    ) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      if (
        route.name !== "search" ||
        pendingRerankScrollRestoreRef.current !== pending
      ) {
        return;
      }
      window.scrollTo(0, pending.scrollY);
      pendingRerankScrollRestoreRef.current = null;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [route.name, session, rerankRestoreRequest]);

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

  const dossierSelection = useMemo(() => {
    if (route.name !== "dossier" || !session) return null;
    const group =
      session.response.results.find(
        (item) => item.ski_region_id === route.skiRegionId,
      ) ?? session.response.results[0];
    if (!group) return null;
    const configuration = findSelectedCandidate(
      group,
      group.ski_region_id === route.skiRegionId
        ? route.candidateId ?? undefined
        : undefined,
    );
    return { group, configuration };
  }, [route, session]);

  useEffect(() => {
    if (route.name !== "dossier" || !dossierSelection) return;
    const { group, configuration } = dossierSelection;
    const canonicalHref = buildDossierHref(
      group.ski_region_id,
      configuration.candidate_id,
    );
    if (`${window.location.pathname}${window.location.search}` !== canonicalHref) {
      window.history.replaceState(null, "", canonicalHref);
      const canonicalRoute = parseAppRoute(window.location);
      routeRef.current = canonicalRoute;
      setRoute(canonicalRoute);
    }
    setSession((current) => {
      if (
        !current ||
        (current.dossierGroupId === group.ski_region_id &&
          current.selectedCandidateIdByGroup[group.ski_region_id] ===
            configuration.candidate_id)
      ) {
        return current;
      }
      return {
        ...current,
        dossierGroupId: group.ski_region_id,
        selectedCandidateIdByGroup: {
          ...current.selectedCandidateIdByGroup,
          [group.ski_region_id]: configuration.candidate_id,
        },
      };
    });
  }, [route, dossierSelection]);

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
    const pendingScrollRestore: PendingRerankScrollRestore = {
      scrollY: window.scrollY,
      response: null,
    };
    pendingRerankScrollRestoreRef.current = pendingScrollRestore;
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
      if (!nextResponse) {
        if (pendingRerankScrollRestoreRef.current === pendingScrollRestore) {
          pendingRerankScrollRestoreRef.current = null;
        }
        return;
      }
      pendingScrollRestore.response = nextResponse;
      setRerankRestoreRequest((current) => current + 1);
      setPreferences(nextPreferences);
      setObjectives(nextObjectives);
      setGroupPriorities(nextGroups);
      setAnsweredQuestionIds(nextAnswered);
      setUndoState(previousState);
      setFocusRequest((current) => current + 1);
      if (previousResponse) {
        const summary = rankChangeSummary(previousResponse, nextResponse);
        setRankFeedback(summary.announcement);
        setChangedRankGroupIds(summary.changedGroupIds);
        window.setTimeout(() => setChangedRankGroupIds(new Set()), 2400);
      }
    } catch (caught) {
      if (pendingRerankScrollRestoreRef.current === pendingScrollRestore) {
        pendingRerankScrollRestoreRef.current = null;
      }
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
      setFocusRequest((current) => current + 1);
      setRankFeedback("Previous trip decisions restored.");
      setChangedRankGroupIds(new Set());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not restore results.");
    } finally {
      setLoading(false);
    }
  }

  async function removeChip(chip: ParsedChip) {
    if (loading) return;
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
    if (!session) return;
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
  const switchDossier = (skiRegionId: string, candidateId: string) => {
    setSession((current) =>
      current
        ? {
            ...current,
            dossierGroupId: skiRegionId,
            selectedCandidateIdByGroup: {
              ...current.selectedCandidateIdByGroup,
              [skiRegionId]: candidateId,
            },
          }
        : current,
    );
    navigate(buildDossierHref(skiRegionId, candidateId));
    window.scrollTo(0, 0);
  };
  const openFilters = () => {
    if (loading) return;
    setDrawerOpen(true);
  };

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

  if (route.name === "dossier") {
    if (!session || !dossierSelection) {
      return (
        <AppShell
          active="search"
          onSearch={goToSearch}
          onCurrentTrip={goToCurrentTrip}
        >
          <main className="app-canvas dossier-recovery">
            <p className="eyebrow">Recommendation context unavailable</p>
            <h1>Run a search first</h1>
            <p>
              This recommendation needs the ranked results from your current browser
              session.
            </p>
            <button type="button" className="primary-command" onClick={goToSearch}>
              Return to search
            </button>
          </main>
        </AppShell>
      );
    }
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
        <RecommendationDossier
          session={session}
          skiRegionId={dossierSelection.group.ski_region_id}
          candidateId={dossierSelection.configuration.candidate_id}
          onSwitch={switchDossier}
          onReturn={goToSearch}
          onSave={(configuration) => void saveConfiguration(configuration)}
          onSelectCandidate={switchDossier}
          onToggleNavigator={() =>
            setSession((current) =>
              current
                ? {
                    ...current,
                    dossierNavigatorCollapsed:
                      !current.dossierNavigatorCollapsed,
                  }
                : current,
            )
          }
        />
      </AppShell>
    );
  }

  const drawer = (
    <SearchFiltersDrawer
      open={drawerOpen}
      disabled={loading}
      filters={filters}
      preferences={preferences}
      returnFocusRef={adjustFiltersRef}
      onFiltersChange={(nextFilters) => {
        if (!loading) setFilters(nextFilters);
      }}
      onPreferencesChange={(nextPreferences) => {
        if (!loading) setPreferences(nextPreferences);
      }}
      onObjectivesChange={(nextObjectives) => {
        if (!loading) setObjectives(nextObjectives);
      }}
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
          onOpenFilters={openFilters}
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
        onOpenFilters={openFilters}
        onRemoveChip={(chip) => void removeChip(chip)}
      />
      {drawer}
    </AppShell>
  );
}

export default App;
