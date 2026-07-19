import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";

import {
  ApiError,
  clearCurrentTrip,
  fetchSearchRefinements,
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
  clearResolvedTopicsForManualChange,
  createSearchSession,
  defaultSearchFilters,
  dismissRefinement,
  findSelectedCandidate,
  isPassValueObjective,
  mergeObjectivePatches,
  mergeParsedFilters,
  rankChangeSummary,
  reconcileSearchSession,
  replaceRefinements,
  upsertBy,
  upsertResolvedRefinementTopic,
  validateSearchFilters,
  type SearchSession,
  type RefinementLifecycleStatus,
} from "./search/searchSession";
import type {
  CurrentTrip,
  CurrentTripSummary,
  FactorPreferencePatch,
  GroupPriorityPatch,
  RefinementOption,
  RefinementProposal,
  ResolvedRefinementTopic,
  SearchFilters,
  SearchIntent,
  SearchObjective,
  SearchV4RefinementResponse,
  SearchV4Configuration,
} from "./types";
import { AppShell, CurrentTripView } from "./ui/AppShell";

const CURRENT_TRIP_RETRY_MESSAGE = "Check your connection and try again.";

interface PreviousSearchState {
  brief: string;
  filters: SearchFilters;
  intent: SearchIntent;
  assumptions: string[];
  preferences: FactorPreferencePatch[];
  groupPriorities: GroupPriorityPatch[];
  objectives: SearchObjective[];
  resolvedTopics: ResolvedRefinementTopic[];
  editorBefore: RefinementEditorPatchState;
  editorAfter: RefinementEditorPatchState;
}

interface RefinementEditorPatchState {
  valueObjective: SearchFilters["valueObjective"];
  preferences: FactorPreferencePatch[];
  groupPriorities: GroupPriorityPatch[];
  objectives: SearchObjective[];
}

interface FetchSearchOptions {
  exactIntent?: SearchIntent;
  syncEditorFromResponse?: boolean;
}

interface PendingRerankScrollRestore {
  scrollY: number;
  response: SearchSession["response"] | null;
}

interface ChipEditorState {
  filters: SearchFilters;
  preferences: FactorPreferencePatch[];
  groupPriorities: GroupPriorityPatch[];
  objectives: SearchObjective[];
}

function resolvedQuestionIds(topics: ResolvedRefinementTopic[]): string[] {
  return topics.map((item) => item.questionId);
}

function resolvedTopicIds(topics: ResolvedRefinementTopic[]): string[] {
  return topics.map((item) => item.topicId);
}

function hardRefinementContext(intent: SearchIntent) {
  return {
    constraints: intent.constraints,
    skillLevels: intent.party.skill_levels,
    travelContext: intent.travel_context,
  };
}

function changedDecisionFactorIds(
  previous: SearchIntent,
  next: SearchIntent,
): Set<string> {
  const changed = new Set<string>();
  const compareById = <T,>(
    before: T[],
    after: T[],
    key: (item: T) => string,
  ) => {
    const beforeById = new Map(before.map((item) => [key(item), item]));
    const afterById = new Map(after.map((item) => [key(item), item]));
    for (const id of new Set([...beforeById.keys(), ...afterById.keys()])) {
      if (JSON.stringify(beforeById.get(id)) !== JSON.stringify(afterById.get(id))) {
        changed.add(id);
      }
    }
  };
  compareById(
    previous.factor_preferences,
    next.factor_preferences,
    (item) => item.factor_id,
  );
  compareById(previous.objectives, next.objectives, (item) => item.factor_id);
  compareById(
    previous.group_priorities,
    next.group_priorities,
    (item) => item.group_id,
  );
  return changed;
}

function resolvedTopicsAfterManualIntentChange(
  current: ResolvedRefinementTopic[],
  previousBrief: string,
  previousIntent: SearchIntent,
  nextBrief: string,
  nextIntent: SearchIntent,
): ResolvedRefinementTopic[] {
  const startsNewContext =
    previousBrief.trim() !== nextBrief.trim() ||
    JSON.stringify(hardRefinementContext(previousIntent)) !==
      JSON.stringify(hardRefinementContext(nextIntent));
  return clearResolvedTopicsForManualChange(current, {
    startsNewContext,
    changedFactorIds: changedDecisionFactorIds(previousIntent, nextIntent),
  });
}

function waitForRefinementRetry(
  delayMs: number,
  signal: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("The operation was aborted.", "AbortError"));
      return;
    }
    const onAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException("The operation was aborted.", "AbortError"));
    };
    const timer = window.setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, delayMs);
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

function restoreRefinementDraftItems<T>(
  current: T[],
  before: T[],
  after: T[],
  key: (item: T) => string,
): T[] {
  const beforeByKey = new Map(before.map((item) => [key(item), item]));
  const afterByKey = new Map(after.map((item) => [key(item), item]));
  const currentByKey = new Map(current.map((item) => [key(item), item]));
  const touchedKeys = new Set([...beforeByKey.keys(), ...afterByKey.keys()]);
  const changedKeys = [...touchedKeys].filter(
    (itemKey) =>
      JSON.stringify(beforeByKey.get(itemKey)) !==
      JSON.stringify(afterByKey.get(itemKey)),
  );
  const restored = current.filter((item) => !changedKeys.includes(key(item)));
  for (const itemKey of changedKeys) {
    const currentItem = currentByKey.get(itemKey);
    const afterItem = afterByKey.get(itemKey);
    if (JSON.stringify(currentItem) !== JSON.stringify(afterItem)) {
      if (currentItem) restored.push(currentItem);
      continue;
    }
    const beforeItem = beforeByKey.get(itemKey);
    if (beforeItem) restored.push(beforeItem);
  }
  return restored;
}

function removeChipFromEditor(
  state: ChipEditorState,
  action: ParsedChip["action"],
): ChipEditorState {
  const next = { ...state };
  switch (action.kind) {
    case "location":
      return { ...next, filters: { ...state.filters, location: "" } };
    case "travelWindow":
      return {
        ...next,
        filters: { ...state.filters, travelWindowMode: "any" },
      };
    case "lodgingBudget":
      return { ...next, filters: { ...state.filters, maxPrice: "" } };
    case "stayQuality":
      return { ...next, filters: { ...state.filters, stars: "" } };
    case "travelLimit":
      return { ...next, filters: { ...state.filters, maxDriveHours: "" } };
    case "travelOrigin":
      return {
        ...next,
        filters: { ...state.filters, originText: "", maxDriveHours: "" },
      };
    case "skill":
      return { ...next, filters: { ...state.filters, skillLevel: "" } };
    case "objective": {
      const removesPassValueFamily = isPassValueObjective(action.id);
      const keepObjective = (item: SearchObjective) =>
        removesPassValueFamily
          ? !isPassValueObjective(item.factor_id)
          : item.factor_id !== action.id;
      return {
        ...next,
        filters:
          removesPassValueFamily || state.filters.valueObjective === action.id
            ? { ...state.filters, valueObjective: "" }
            : state.filters,
        objectives: state.objectives.filter(keepObjective),
      };
    }
    case "group":
      return {
        ...next,
        groupPriorities: state.groupPriorities.filter(
          (item) => item.group_id !== action.id,
        ),
      };
    case "preference":
      return {
        ...next,
        preferences: state.preferences.filter(
          (item) => item.factor_id !== action.id,
        ),
      };
  }
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
  const [resolvedTopics, setResolvedTopics] = useState<
    ResolvedRefinementTopic[]
  >([]);
  const [session, setSession] = useState<SearchSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [refinementError, setRefinementError] = useState<string | null>(null);
  const [refinementStatus, setRefinementStatus] =
    useState<RefinementLifecycleStatus>("idle");
  const [rankFeedback, setRankFeedback] = useState<string | null>(null);
  const [changedRankGroupIds, setChangedRankGroupIds] = useState<Set<string>>(
    new Set(),
  );
  const [undoState, setUndoState] = useState<PreviousSearchState | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [focusRequest, setFocusRequest] = useState(0);
  const [refinementFocusRequest, setRefinementFocusRequest] = useState(0);
  const [currentTrip, setCurrentTrip] = useState<CurrentTrip | null>(null);
  const [currentTripSummary, setCurrentTripSummary] =
    useState<CurrentTripSummary | null>(null);
  const [currentTripLoadError, setCurrentTripLoadError] = useState<string | null>(
    null,
  );
  const [currentTripSummaryLoadError, setCurrentTripSummaryLoadError] = useState<
    string | null
  >(null);
  const [currentTripClearError, setCurrentTripClearError] = useState<string | null>(
    null,
  );
  const [currentTripLoadRequest, setCurrentTripLoadRequest] = useState(0);
  const [currentTripSummaryLoadRequest, setCurrentTripSummaryLoadRequest] =
    useState(0);
  const currentTripRef = useRef<CurrentTrip | null>(null);
  const currentTripLoadIdentityRef = useRef(0);
  const currentTripSummaryLoadIdentityRef = useRef(0);
  const adjustFiltersRef = useRef<HTMLButtonElement>(null);
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);
  const refinementControlRef = useRef<HTMLElement>(null);
  const pendingRerankScrollRestoreRef =
    useRef<PendingRerankScrollRestore | null>(null);
  const routeRef = useRef(route);
  const pendingDossierScrollRestoreRef = useRef(false);
  const pendingDossierFocusHrefRef = useRef<string | null>(null);
  const refinementAbortRef = useRef<AbortController | null>(null);
  const refinementRequestIdRef = useRef(0);
  const refinementSlowTimerRef = useRef<number | null>(null);
  const [rerankRestoreRequest, setRerankRestoreRequest] = useState(0);

  useEffect(
    () => () => {
      refinementRequestIdRef.current += 1;
      refinementAbortRef.current?.abort();
      if (refinementSlowTimerRef.current !== null) {
        window.clearTimeout(refinementSlowTimerRef.current);
      }
    },
    [],
  );

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
      pendingDossierFocusHrefRef.current = `${destination.pathname}${destination.search}`;
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
    const identity = ++currentTripLoadIdentityRef.current;
    setCurrentTripLoadError(null);
    void getCurrentTrip()
      .then((trip) => {
        if (identity !== currentTripLoadIdentityRef.current) return;
        if (currentTripRef.current === trip) return;
        currentTripRef.current = trip;
        setCurrentTrip(trip);
      })
      .catch(() => {
        if (identity === currentTripLoadIdentityRef.current) {
          setCurrentTripLoadError(CURRENT_TRIP_RETRY_MESSAGE);
        }
      });
    return () => {
      if (identity === currentTripLoadIdentityRef.current) {
        currentTripLoadIdentityRef.current += 1;
      }
    };
  }, [currentTripLoadRequest]);

  useEffect(() => {
    if (!currentTrip) {
      setCurrentTripSummary(null);
      setCurrentTripSummaryLoadError(null);
      return;
    }
    if (route.name !== "currentTrip") return;
    const identity = ++currentTripSummaryLoadIdentityRef.current;
    setCurrentTripSummaryLoadError(null);
    void getCurrentTripSummary()
      .then((summary) => {
        if (identity === currentTripSummaryLoadIdentityRef.current) {
          setCurrentTripSummary(summary);
        }
      })
      .catch(() => {
        if (identity === currentTripSummaryLoadIdentityRef.current) {
          setCurrentTripSummaryLoadError(CURRENT_TRIP_RETRY_MESSAGE);
        }
      });
    return () => {
      if (identity === currentTripSummaryLoadIdentityRef.current) {
        currentTripSummaryLoadIdentityRef.current += 1;
      }
    };
  }, [route.name, currentTrip, currentTripSummaryLoadRequest]);

  useEffect(() => {
    if (focusRequest > 0 && session) {
      resultsHeadingRef.current?.focus({ preventScroll: true });
    }
  }, [focusRequest]);

  useEffect(() => {
    if (refinementFocusRequest > 0) {
      refinementControlRef.current?.focus({ preventScroll: true });
    }
  }, [refinementFocusRequest]);

  useEffect(() => {
    if (route.name !== "search" || !pendingDossierScrollRestoreRef.current) {
      return;
    }
    if (!session) {
      pendingDossierScrollRestoreRef.current = false;
      return;
    }
    let focusFrame = 0;
    let focusTimer = 0;
    const scrollFrame = window.requestAnimationFrame(() => {
      if (routeRef.current.name !== "search") return;
      window.scrollTo(0, session.resultsScrollY);
      focusFrame = window.requestAnimationFrame(() => {
        if (routeRef.current.name !== "search") return;
        const originHref = pendingDossierFocusHrefRef.current;
        const restoreFocus = () => {
          if (routeRef.current.name !== "search") return;
          const origin = originHref
            ? [
                ...document.querySelectorAll<HTMLAnchorElement>(
                  'a[href^="/recommendations/"]',
                ),
              ].find((anchor) => anchor.getAttribute("href") === originHref)
            : null;
          (origin ?? resultsHeadingRef.current)?.focus({ preventScroll: true });
        };
        restoreFocus();
        focusTimer = window.setTimeout(() => {
          if (
            document.activeElement === document.body ||
            document.activeElement === document.documentElement
          ) {
            restoreFocus();
          }
        }, 100);
        pendingDossierFocusHrefRef.current = null;
        pendingDossierScrollRestoreRef.current = false;
      });
    });
    return () => {
      window.cancelAnimationFrame(scrollFrame);
      window.cancelAnimationFrame(focusFrame);
      window.clearTimeout(focusTimer);
    };
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

  const draftIntent = useMemo(
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

  async function loadRefinements(
    rankingResponse: SearchSession["response"],
    nextBrief: string,
    nextResolvedTopics: ResolvedRefinementTopic[],
  ): Promise<boolean> {
    const belongsToRanking = (current: SearchSession | null) =>
      current?.response.baseline_fingerprint ===
        rankingResponse.baseline_fingerprint &&
      current.response.ranking_policy_version ===
        rankingResponse.ranking_policy_version;
    const requestId = refinementRequestIdRef.current + 1;
    refinementRequestIdRef.current = requestId;
    refinementAbortRef.current?.abort();
    if (refinementSlowTimerRef.current !== null) {
      window.clearTimeout(refinementSlowTimerRef.current);
      refinementSlowTimerRef.current = null;
    }
    setRefinementError(null);
    setSession((current) =>
      belongsToRanking(current) && current
        ? replaceRefinements(current, [])
        : current,
    );

    if (
      rankingResponse.eligible_candidate_count === 0 ||
      rankingResponse.results.length === 0
    ) {
      setRefinementStatus("idle");
      return false;
    }

    const controller = new AbortController();
    refinementAbortRef.current = controller;
    const clearSlowTimer = () => {
      if (refinementSlowTimerRef.current !== null) {
        window.clearTimeout(refinementSlowTimerRef.current);
        refinementSlowTimerRef.current = null;
      }
    };
    const startAttempt = () => {
      setRefinementStatus("loading");
      clearSlowTimer();
      refinementSlowTimerRef.current = window.setTimeout(() => {
        if (
          refinementRequestIdRef.current === requestId &&
          !controller.signal.aborted
        ) {
          setRefinementStatus("slow");
        }
      }, 2_500);
    };
    const request = {
      intent: rankingResponse.applied_intent,
      brief: nextBrief.trim().slice(0, 2_000) || null,
      baseline_fingerprint: rankingResponse.baseline_fingerprint,
      already_answered_question_ids: resolvedQuestionIds(nextResolvedTopics),
      resolved_topic_ids: resolvedTopicIds(nextResolvedTopics),
    };

    try {
      let refinementResponse: SearchV4RefinementResponse | undefined;
      for (let attempt = 0; attempt < 2; attempt += 1) {
        startAttempt();
        try {
          refinementResponse = await fetchSearchRefinements(
            request,
            controller.signal,
          );
          break;
        } catch (caught) {
          clearSlowTimer();
          const canRetry =
            attempt === 0 &&
            caught instanceof ApiError &&
            caught.status === 429 &&
            caught.retryAfterSeconds !== null &&
            caught.retryAfterSeconds <= 15 &&
            refinementRequestIdRef.current === requestId &&
            !controller.signal.aborted;
          if (!canRetry) throw caught;
          setRefinementStatus("retrying");
          await waitForRefinementRetry(
            caught.retryAfterSeconds * 1_000,
            controller.signal,
          );
          if (refinementRequestIdRef.current !== requestId) return false;
        }
      }
      if (!refinementResponse) return false;
      if (refinementRequestIdRef.current !== requestId) return false;

      if (refinementResponse.baseline_status === "unverified") {
        setRefinementStatus("temporarily_unavailable");
        setSession((current) =>
          belongsToRanking(current) && current
            ? replaceRefinements(current, [])
            : current,
        );
        return false;
      }

      const baselineMatches =
        refinementResponse.baseline_status === "current" &&
        refinementResponse.baseline_fingerprint ===
          rankingResponse.baseline_fingerprint &&
        refinementResponse.ranking_policy_version ===
          rankingResponse.ranking_policy_version;
      if (!baselineMatches) {
        setRefinementStatus("stale");
        setSession((current) =>
          belongsToRanking(current) && current
            ? replaceRefinements(current, [])
            : current,
        );
        return false;
      }

      const refinements =
        refinementResponse.refinement_status === "questions_available"
          ? refinementResponse.refinements
          : [];
      const status = refinements.length
        ? "questions_available"
        : refinementResponse.refinement_status === "questions_available"
          ? "not_needed"
          : refinementResponse.refinement_status;
      setSession((current) =>
        belongsToRanking(current) && current
          ? replaceRefinements(current, refinements)
          : current,
      );
      setRefinementStatus(status);
      return refinements.length > 0;
    } catch {
      if (
        controller.signal.aborted ||
        refinementRequestIdRef.current !== requestId
      ) {
        return false;
      }
      setRefinementStatus("temporarily_unavailable");
      setRefinementError(null);
      return false;
    } finally {
      if (refinementRequestIdRef.current === requestId) {
        clearSlowTimer();
        if (refinementAbortRef.current === controller) {
          refinementAbortRef.current = null;
        }
      }
    }
  }

  async function fetchSearch(
    nextFilters: SearchFilters,
    nextAssumptions: string[],
    nextPreferences: FactorPreferencePatch[],
    nextGroupPriorities: GroupPriorityPatch[],
    nextObjectives: SearchObjective[],
    nextResolvedTopics: ResolvedRefinementTopic[],
    nextBrief: string,
    focusResults: boolean,
    options: FetchSearchOptions = {},
  ) {
    const validationError = validateSearchFilters(nextFilters);
    if (validationError) {
      setError(validationError);
      return null;
    }
    const intent =
      options.exactIntent ??
      buildSearchIntent(
        nextFilters,
        nextAssumptions,
        nextPreferences,
        nextGroupPriorities,
        nextObjectives,
      );
    refinementRequestIdRef.current += 1;
    refinementAbortRef.current?.abort();
    refinementAbortRef.current = null;
    if (refinementSlowTimerRef.current !== null) {
      window.clearTimeout(refinementSlowTimerRef.current);
      refinementSlowTimerRef.current = null;
    }
    setRefinementStatus("idle");
    const response = await searchResorts({ intent });
    if (options.syncEditorFromResponse !== false) {
      setFilters(nextFilters);
      setAssumptions([...response.applied_intent.assumptions]);
      setPreferences([...response.applied_intent.factor_preferences]);
      setGroupPriorities([...response.applied_intent.group_priorities]);
      setObjectives([...response.applied_intent.objectives]);
    }
    setSession((current) => {
      const next = current
        ? reconcileSearchSession(current, response, nextFilters)
        : createSearchSession(nextBrief, response, nextFilters);
      return { ...next, brief: nextBrief };
    });
    setUndoState(null);
    setRankFeedback(null);
    setChangedRankGroupIds(new Set());
    setError(null);
    if (focusResults) setFocusRequest((current) => current + 1);
    void loadRefinements(response, nextBrief, nextResolvedTopics);
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
      const nextIntent = buildSearchIntent(
        nextFilters,
        nextAssumptions,
        preferences,
        groupPriorities,
        objectives,
      );
      const nextResolvedTopics = session
        ? resolvedTopicsAfterManualIntentChange(
            resolvedTopics,
            session.brief,
            session.response.applied_intent,
            brief,
            nextIntent,
          )
        : [];
      const nextResponse = await fetchSearch(
        nextFilters,
        nextAssumptions,
        preferences,
        groupPriorities,
        objectives,
        nextResolvedTopics,
        brief,
        true,
      );
      if (nextResponse) setResolvedTopics(nextResolvedTopics);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not complete the search.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function applyRefinement(
    refinement: RefinementProposal,
    option: RefinementOption,
  ) {
    const baselineSession = session;
    if (loading || !baselineSession) return;
    const baselineIntent = baselineSession.response.applied_intent;
    const nextResolvedTopics = upsertResolvedRefinementTopic(
      resolvedTopics,
      refinement,
    );
    if (!option.intent_changed) {
      setResolvedTopics(nextResolvedTopics);
      setSession((current) =>
        current ? dismissRefinement(current, refinement.question_id) : current,
      );
      setRefinementError(null);
      setRankFeedback("Current ranking kept.");
      setChangedRankGroupIds(new Set());
      const hasNextRefinement = await loadRefinements(
        baselineSession.response,
        baselineSession.brief,
        nextResolvedTopics,
      );
      if (hasNextRefinement) {
        setRefinementFocusRequest((current) => current + 1);
      } else {
        setFocusRequest((current) => current + 1);
      }
      return;
    }
    const nextPreferences = upsertBy(
      [...baselineIntent.factor_preferences].filter(
        (item) =>
          !option.objective_patches.some(
            (patch) => patch.factor_id === item.factor_id,
          ),
      ),
      option.factor_preference_patches,
      (item) => item.factor_id,
    );
    const nextObjectives = mergeObjectivePatches(
      [...baselineIntent.objectives].filter(
        (item) =>
          !option.factor_preference_patches.some(
            (patch) => patch.factor_id === item.factor_id,
          ),
      ),
      option.objective_patches,
    );
    const nextGroups = upsertBy(
      [...baselineIntent.group_priorities],
      option.group_priority_patches,
      (item) => item.group_id,
    );
    const nextEditorPreferences = upsertBy(
      [...preferences].filter(
        (item) =>
          !option.objective_patches.some(
            (patch) => patch.factor_id === item.factor_id,
          ),
      ),
      option.factor_preference_patches,
      (item) => item.factor_id,
    );
    const nextEditorObjectives = mergeObjectivePatches(
      [...objectives].filter(
        (item) =>
          !option.factor_preference_patches.some(
            (patch) => patch.factor_id === item.factor_id,
          ),
      ),
      option.objective_patches,
    );
    const nextEditorGroups = upsertBy(
      [...groupPriorities],
      option.group_priority_patches,
      (item) => item.group_id,
    );
    const selectedValueObjective = option.objective_patches.find(
      (patch) =>
        patch.factor_id === "pass_terrain_value" ||
        patch.factor_id === "pass_price_per_day",
    )?.factor_id as SearchFilters["valueObjective"] | undefined;
    const nextEditorValueObjective = selectedValueObjective
      ? selectedValueObjective
      : option.factor_preference_patches.some(
            (patch) => patch.factor_id === filters.valueObjective,
          )
        ? ""
        : filters.valueObjective;
    const previousState: PreviousSearchState = {
      brief: baselineSession.brief,
      filters: baselineSession.appliedFilters,
      intent: baselineIntent,
      assumptions: [...baselineIntent.assumptions],
      preferences: [...baselineIntent.factor_preferences],
      groupPriorities: [...baselineIntent.group_priorities],
      objectives: [...baselineIntent.objectives],
      resolvedTopics,
      editorBefore: {
        valueObjective: filters.valueObjective,
        preferences: [...preferences],
        groupPriorities: [...groupPriorities],
        objectives: [...objectives],
      },
      editorAfter: {
        valueObjective: nextEditorValueObjective,
        preferences: nextEditorPreferences,
        groupPriorities: nextEditorGroups,
        objectives: nextEditorObjectives,
      },
    };
    const nextIntent: SearchIntent = {
      ...baselineIntent,
      factor_preferences: nextPreferences,
      group_priorities: nextGroups,
      objectives: nextObjectives,
    };
    const previousResponse = baselineSession.response;
    const pendingScrollRestore: PendingRerankScrollRestore = {
      scrollY: window.scrollY,
      response: null,
    };
    pendingRerankScrollRestoreRef.current = pendingScrollRestore;
    setLoading(true);
    setRefinementError(null);
    try {
      const nextResponse = await fetchSearch(
        baselineSession.appliedFilters,
        [...baselineIntent.assumptions],
        nextPreferences,
        nextGroups,
        nextObjectives,
        nextResolvedTopics,
        baselineSession.brief,
        false,
        {
          exactIntent: nextIntent,
          syncEditorFromResponse: false,
        },
      );
      if (!nextResponse) {
        if (pendingRerankScrollRestoreRef.current === pendingScrollRestore) {
          pendingRerankScrollRestoreRef.current = null;
        }
        return;
      }
      pendingScrollRestore.response = nextResponse;
      setRerankRestoreRequest((current) => current + 1);
      setResolvedTopics(nextResolvedTopics);
      setFilters((current) => ({
        ...current,
        valueObjective: nextEditorValueObjective,
      }));
      setPreferences(nextEditorPreferences);
      setGroupPriorities(nextEditorGroups);
      setObjectives(nextEditorObjectives);
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

  async function skipRefinement(refinement: RefinementProposal) {
    const baselineSession = session;
    if (loading || !baselineSession) return;
    const nextResolvedTopics = upsertResolvedRefinementTopic(
      resolvedTopics,
      refinement,
    );
    setResolvedTopics(nextResolvedTopics);
    setSession((current) =>
      current ? dismissRefinement(current, refinement.question_id) : current,
    );
    setRefinementError(null);
    setRefinementStatus("skipped");
    const hasNextRefinement = await loadRefinements(
      baselineSession.response,
      baselineSession.brief,
      nextResolvedTopics,
    );
    if (hasNextRefinement) {
      setRefinementFocusRequest((current) => current + 1);
    } else {
      setFocusRequest((current) => current + 1);
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
        undoState.resolvedTopics,
        undoState.brief,
        false,
        {
          exactIntent: undoState.intent,
          syncEditorFromResponse: false,
        },
      );
      setFilters((current) => ({
        ...current,
        valueObjective:
          current.valueObjective === undoState.editorAfter.valueObjective
            ? undoState.editorBefore.valueObjective
            : current.valueObjective,
      }));
      setPreferences((current) =>
        restoreRefinementDraftItems(
          current,
          undoState.editorBefore.preferences,
          undoState.editorAfter.preferences,
          (item) => item.factor_id,
        ),
      );
      setGroupPriorities((current) =>
        restoreRefinementDraftItems(
          current,
          undoState.editorBefore.groupPriorities,
          undoState.editorAfter.groupPriorities,
          (item) => item.group_id,
        ),
      );
      setObjectives((current) =>
        restoreRefinementDraftItems(
          current,
          undoState.editorBefore.objectives,
          undoState.editorAfter.objectives,
          (item) => item.factor_id,
        ),
      );
      setResolvedTopics(undoState.resolvedTopics);
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
    const baselineSession = session;
    if (loading) return;
    const nextEditor = removeChipFromEditor(
      { filters, preferences, groupPriorities, objectives },
      chip.action,
    );
    if (!baselineSession) {
      setFilters(nextEditor.filters);
      setPreferences(nextEditor.preferences);
      setGroupPriorities(nextEditor.groupPriorities);
      setObjectives(nextEditor.objectives);
      return;
    }
    const baselineIntent = baselineSession.response.applied_intent;
    let nextFilters = baselineSession.appliedFilters;
    let nextConstraints = { ...baselineIntent.constraints };
    let nextTravelContext = { ...baselineIntent.travel_context };
    let nextSkillLevels = [...baselineIntent.party.skill_levels];
    let nextPreferences = [...baselineIntent.factor_preferences];
    let nextGroups = [...baselineIntent.group_priorities];
    let nextObjectives = [...baselineIntent.objectives];
    const action = chip.action;
    switch (action.kind) {
      case "location":
        delete nextConstraints.location;
        nextFilters = { ...nextFilters, location: "" };
        break;
      case "travelWindow":
        delete nextConstraints.travel_window;
        nextFilters = { ...nextFilters, travelWindowMode: "any" };
        break;
      case "lodgingBudget":
        delete nextConstraints.lodging_budget;
        nextFilters = { ...nextFilters, maxPrice: "" };
        break;
      case "stayQuality":
        delete nextConstraints.minimum_stay_quality;
        nextFilters = { ...nextFilters, stars: "" };
        break;
      case "travelLimit":
        delete nextConstraints.travel_limit;
        nextFilters = { ...nextFilters, maxDriveHours: "" };
        break;
      case "travelOrigin":
        delete nextConstraints.travel_limit;
        nextTravelContext = {};
        nextFilters = { ...nextFilters, originText: "", maxDriveHours: "" };
        break;
      case "skill":
        nextSkillLevels = [];
        nextFilters = { ...nextFilters, skillLevel: "" };
        break;
      case "objective": {
        const removesPassValueFamily = isPassValueObjective(action.id);
        const keepObjective = (item: SearchObjective) =>
          removesPassValueFamily
            ? !isPassValueObjective(item.factor_id)
            : item.factor_id !== action.id;
        nextObjectives = nextObjectives.filter(keepObjective);
        nextFilters =
          removesPassValueFamily || nextFilters.valueObjective === action.id
            ? { ...nextFilters, valueObjective: "" }
            : nextFilters;
        break;
      }
      case "group":
        nextGroups = nextGroups.filter((item) => item.group_id !== action.id);
        break;
      case "preference":
        nextPreferences = nextPreferences.filter(
          (item) => item.factor_id !== action.id,
        );
        break;
    }
    const nextIntent: SearchIntent = {
      ...baselineIntent,
      constraints: nextConstraints,
      party: { skill_levels: nextSkillLevels },
      travel_context: nextTravelContext,
      factor_preferences: nextPreferences,
      group_priorities: nextGroups,
      objectives: nextObjectives,
    };
    const nextResolvedTopics = resolvedTopicsAfterManualIntentChange(
      resolvedTopics,
      baselineSession.brief,
      baselineIntent,
      baselineSession.brief,
      nextIntent,
    );
    setLoading(true);
    try {
      const nextResponse = await fetchSearch(
        nextFilters,
        [...baselineIntent.assumptions],
        nextPreferences,
        nextGroups,
        nextObjectives,
        nextResolvedTopics,
        baselineSession.brief,
        false,
        {
          exactIntent: nextIntent,
          syncEditorFromResponse: false,
        },
      );
      if (!nextResponse) return;
      setFilters(nextEditor.filters);
      setPreferences(nextEditor.preferences);
      setGroupPriorities(nextEditor.groupPriorities);
      setObjectives(nextEditor.objectives);
      setResolvedTopics(nextResolvedTopics);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  async function saveConfiguration(
    configuration: SearchV4Configuration,
    appliedIntent: SearchSession["response"]["applied_intent"],
  ) {
    const travelWindow = appliedIntent.constraints.travel_window;
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
          typeof travelWindow?.month === "number" ? travelWindow.month : null,
        trip_start_date:
          travelWindow?.start_date ?? null,
        trip_end_date:
          travelWindow?.end_date ?? null,
        booking_status: "not_booked_yet",
      });
      currentTripLoadIdentityRef.current += 1;
      currentTripSummaryLoadIdentityRef.current += 1;
      currentTripRef.current = saved;
      setCurrentTrip(saved);
      setCurrentTripSummary(null);
      setCurrentTripLoadError(null);
      setCurrentTripSummaryLoadError(null);
      setSaveError(null);
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : "Could not save trip.");
    }
  }

  async function handleClearCurrentTrip() {
    setCurrentTripClearError(null);
    try {
      await clearCurrentTrip();
      currentTripLoadIdentityRef.current += 1;
      currentTripSummaryLoadIdentityRef.current += 1;
      currentTripRef.current = null;
      setCurrentTrip(null);
      setCurrentTripSummary(null);
      setCurrentTripLoadError(null);
      setCurrentTripSummaryLoadError(null);
    } catch (caught) {
      setCurrentTripClearError(
        caught instanceof Error
          ? caught.message
          : "Unable to remove current trip. Check your connection and try again.",
      );
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
          tripLoadError={currentTripLoadError}
          summaryLoadError={currentTripSummaryLoadError}
          clearError={currentTripClearError}
          onBack={goToSearch}
          onRetryTripLoad={() =>
            setCurrentTripLoadRequest((current) => current + 1)
          }
          onRetrySummaryLoad={() =>
            setCurrentTripSummaryLoadRequest((current) => current + 1)
          }
          onClear={() => {
            void handleClearCurrentTrip();
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
        {saveError ? <p className="error-copy" role="alert">{saveError}</p> : null}
        <RecommendationDossier
          session={session}
          skiRegionId={dossierSelection.group.ski_region_id}
          candidateId={dossierSelection.configuration.candidate_id}
          onSwitch={switchDossier}
          onReturn={goToSearch}
          onSave={(configuration) =>
            void saveConfiguration(configuration, session.response.applied_intent)
          }
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
      objectives={objectives}
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
          saveError={saveError}
          refinementError={refinementError}
          refinementStatus={refinementStatus}
          refinementControlRef={refinementControlRef}
          rankFeedback={rankFeedback}
          changedRankGroupIds={changedRankGroupIds}
          canUndo={undoState !== null}
          headingRef={resultsHeadingRef}
          adjustFiltersRef={adjustFiltersRef}
          onOpenFilters={openFilters}
          onRemoveChip={(chip) => void removeChip(chip)}
          onApplyRefinement={(refinement, option) =>
            void applyRefinement(refinement, option)
          }
          onSkipRefinement={(refinement) => void skipRefinement(refinement)}
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
          onSave={(configuration) =>
            void saveConfiguration(configuration, session.response.applied_intent)
          }
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
        chips={buildParsedChips(draftIntent)}
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
