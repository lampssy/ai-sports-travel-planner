import { expect, test } from "vitest";

import type {
  SearchIntent,
  SearchResponse,
  SearchV4RecommendationGroup,
} from "../types";
import {
  createSearchSession,
  findSelectedCandidate,
  mergeObjectivePatches,
  rankChangeSummary,
  reconcileSearchSession,
} from "./searchSession";

test("replaces the exclusive pass-value objective family but only exact unrelated IDs", () => {
  expect(
    mergeObjectivePatches(
      [
        { factor_id: "pass_terrain_value", importance: "normal" },
        { factor_id: "terrain_scale", importance: "normal" },
      ],
      [
        { factor_id: "pass_price_per_day", importance: "high" },
        { factor_id: "terrain_scale", importance: "high" },
      ],
    ),
  ).toEqual([
    { factor_id: "pass_price_per_day", importance: "high" },
    { factor_id: "terrain_scale", importance: "high" },
  ]);
});

const intent: SearchIntent = {
  constraints: { location: { country: "France" } },
  party: { skill_levels: ["intermediate"] },
  travel_context: {},
  objectives: [],
  group_priorities: [],
  factor_preferences: [],
  assumptions: [],
};

function group(
  skiRegionId: string,
  topCandidateId: string,
  alternativeCandidateIds: string[] = [],
): SearchV4RecommendationGroup {
  const configuration = (candidateId: string) => ({
    candidate_id: candidateId,
    ski_region_id: skiRegionId,
  });
  return {
    ski_region_id: skiRegionId,
    ski_region_name: skiRegionId,
    rank: 1,
    fit_score: 80,
    top_configuration: configuration(topCandidateId),
    alternative_configurations: alternativeCandidateIds.map(configuration),
  } as SearchV4RecommendationGroup;
}

function response(
  groups: SearchV4RecommendationGroup[],
  appliedIntent: SearchIntent = intent,
): SearchResponse {
  return {
    search_model_version: "search-v4",
    ranking_policy_version: "test-policy",
    baseline_fingerprint: "baseline-a",
    ranking_status: "ranked",
    unscored_reason: null,
    applied_intent: appliedIntent,
    eligible_candidate_count: groups.length,
    excluded_candidate_count: 0,
    results: groups,
    refinements: [],
  };
}

test("creates an in-memory session with the winner expanded and selected", () => {
  const serverIntent = { ...intent, assumptions: ["Server-applied"] };
  const session = createSearchSession(
    "A March trip in France",
    response(
      [group("region-a", "candidate-a"), group("region-b", "candidate-b")],
      serverIntent,
    ),
  );

  expect(session.brief).toBe("A March trip in France");
  expect(session.intent).toEqual(serverIntent);
  expect(session.expandedGroupIds).toEqual(new Set(["region-a"]));
  expect(session.resultsScrollY).toBe(0);
  expect(session.dossierNavigatorCollapsed).toBe(false);
  expect(session.dossierGroupId).toBeNull();
  expect(session.selectedCandidateIdByGroup).toEqual({
    "region-a": "candidate-a",
    "region-b": "candidate-b",
  });
  expect(session.refinementQueue).toEqual([]);
  expect(session.resultsScrollY).toBe(0);
});

test("does not hydrate or reconcile the refinement queue from the legacy search field", () => {
  const legacyRefinement = {
    question_id: "legacy-question",
    question: "Legacy question?",
    reason: "Returned only for compatibility.",
    options: [],
  };
  const initialResponse = {
    ...response([group("region-a", "candidate-a")]),
    refinements: [legacyRefinement],
  };
  const session = createSearchSession("France", initialResponse);

  expect(session.refinementQueue).toEqual([]);

  const currentWithLoadedRefinement = {
    ...session,
    refinementQueue: [legacyRefinement],
  };
  const next = reconcileSearchSession(
    currentWithLoadedRefinement,
    {
      ...response([group("region-a", "candidate-a")]),
      refinements: [legacyRefinement],
    },
  );

  expect(next.refinementQueue).toEqual([]);
});

test("rerank preserves present selections, expansions, and scroll and expands the new winner", () => {
  const initial = createSearchSession(
    "A March trip in France",
    response([
      group("region-a", "candidate-a", ["candidate-a-alt"]),
      group("region-b", "candidate-b"),
      group("region-old", "candidate-old"),
    ]),
  );
  initial.expandedGroupIds = new Set(["region-a", "region-old"]);
  initial.selectedCandidateIdByGroup["region-a"] = "candidate-a-alt";
  initial.resultsScrollY = 640;

  const nextIntent = { ...intent, assumptions: ["Reranked"] };
  const reranked = reconcileSearchSession(
    initial,
    response(
      [
        group("region-b", "candidate-b"),
        group("region-a", "candidate-a", ["candidate-a-alt"]),
        group("region-new", "candidate-new"),
      ],
      nextIntent,
    ),
  );

  expect(reranked.brief).toBe(initial.brief);
  expect(reranked.intent).toEqual(nextIntent);
  expect(reranked.response.results[0].ski_region_id).toBe("region-b");
  expect(reranked.expandedGroupIds).toEqual(new Set(["region-a", "region-b"]));
  expect(reranked.selectedCandidateIdByGroup).toEqual({
    "region-a": "candidate-a-alt",
    "region-b": "candidate-b",
    "region-new": "candidate-new",
  });
  expect(reranked.resultsScrollY).toBe(640);
});

test("does not announce a changed ranking when result positions are unchanged", () => {
  const unchanged = response([group("region-a", "candidate-a")]);

  expect(rankChangeSummary(unchanged, unchanged)).toEqual({
    changedGroupIds: new Set(),
    announcement: "Ranking unchanged.",
  });
});

test("selected candidate lookup falls back to the current group winner", () => {
  const result = group("region-a", "candidate-a", ["candidate-a-alt"]);

  expect(findSelectedCandidate(result, "candidate-a-alt")?.candidate_id).toBe(
    "candidate-a-alt",
  );
  expect(findSelectedCandidate(result, "missing")?.candidate_id).toBe(
    "candidate-a",
  );
});
