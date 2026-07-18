import { AlertTriangle, RotateCcw } from "lucide-react";
import type { RefObject } from "react";

import type {
  RefinementOption,
  SearchV4Configuration,
} from "../types";
import { RecommendationCard } from "./RecommendationCard";
import { SearchContextRail } from "./SearchContextRail";
import {
  buildParsedChips,
  selectTripEssentialCategories,
  type ParsedChip,
} from "./searchPresentation";
import type { SearchSession } from "./searchSession";
import type { RefinementLifecycleStatus } from "./searchSession";

export function RecommendationBoard({
  session,
  loading,
  error,
  saveError,
  refinementError,
  refinementStatus,
  refinementControlRef,
  rankFeedback,
  changedRankGroupIds,
  canUndo,
  headingRef,
  adjustFiltersRef,
  onOpenFilters,
  onRemoveChip,
  onApplyRefinement,
  onSkipRefinement,
  onToggleGroup,
  onSelectCandidate,
  onSave,
  onUndo,
}: {
  session: SearchSession;
  loading: boolean;
  error: string | null;
  saveError: string | null;
  refinementError: string | null;
  refinementStatus: RefinementLifecycleStatus;
  refinementControlRef: RefObject<HTMLElement>;
  rankFeedback: string | null;
  changedRankGroupIds: Set<string>;
  canUndo: boolean;
  headingRef: RefObject<HTMLHeadingElement>;
  adjustFiltersRef: RefObject<HTMLButtonElement>;
  onOpenFilters: () => void;
  onRemoveChip: (chip: ParsedChip) => void;
  onApplyRefinement: (questionId: string, option: RefinementOption) => void;
  onSkipRefinement: (questionId: string) => void;
  onToggleGroup: (skiRegionId: string) => void;
  onSelectCandidate: (skiRegionId: string, candidateId: string) => void;
  onSave: (configuration: SearchV4Configuration) => void;
  onUndo: () => void;
}) {
  const response = session.response;
  const essentialCategories = selectTripEssentialCategories(
    session.intent,
    response.results,
  );
  const hardConstraints = buildParsedChips(session.intent).filter((chip) =>
    ["location", "travelWindow", "lodgingBudget", "stayQuality", "travelLimit", "skill"].includes(
      chip.action.kind,
    ),
  );

  return (
    <main className="app-canvas results-workspace">
      <SearchContextRail
        intent={session.intent}
        refinement={session.refinementQueue[0] ?? null}
        refinementStatus={refinementStatus}
        loading={loading}
        refinementError={refinementError}
        refinementControlRef={refinementControlRef}
        adjustFiltersRef={adjustFiltersRef}
        onOpenFilters={onOpenFilters}
        onRemoveChip={onRemoveChip}
        onApplyRefinement={onApplyRefinement}
        onSkipRefinement={onSkipRefinement}
      />

      <section className="results-board" aria-busy={loading || undefined}>
        <div className="results-board__heading">
          <div>
            <p className="eyebrow">Conditions-aware ranking</p>
            <h1 ref={headingRef} tabIndex={-1} aria-label="Recommended ski trips">
              Recommended for you
            </h1>
          </div>
          <p className="eligible-count">
            {response.eligible_candidate_count} eligible configurations
          </p>
        </div>

        {response.ranking_status === "unscored" ? (
          <p className="warning-status">
            <AlertTriangle aria-hidden="true" size={17} />
            Unranked options: comparable scoring is unavailable
          </p>
        ) : null}
        {rankFeedback ? (
          <div className="rerank-feedback">
            <p>{rankFeedback}</p>
            {canUndo ? (
              <button type="button" onClick={onUndo} disabled={loading}>
                <RotateCcw aria-hidden="true" size={17} />
                Undo
              </button>
            ) : null}
          </div>
        ) : null}
        <p className="sr-only" aria-live="polite" aria-atomic="true">
          {rankFeedback ?? ""}
        </p>
        {loading ? (
          <p className="results-loading" role="status">
            Reranking these recommendations with your updated trip decisions.
          </p>
        ) : null}
        {error ? (
          <p className="error-copy" role="alert">
            {error}
          </p>
        ) : null}
        {saveError ? (
          <p className="error-copy" role="alert">
            {saveError}
          </p>
        ) : null}

        {response.results.length ? (
          <div className="recommendation-list">
            {response.results.map((result) => (
              <RecommendationCard
                key={result.ski_region_id}
                result={result}
                selectedCandidateId={
                  session.selectedCandidateIdByGroup[result.ski_region_id]
                }
                expanded={session.expandedGroupIds.has(result.ski_region_id)}
                essentialCategories={essentialCategories}
                changedRank={changedRankGroupIds.has(result.ski_region_id)}
                onToggle={() => onToggleGroup(result.ski_region_id)}
                onSelectCandidate={(candidateId) =>
                  onSelectCandidate(result.ski_region_id, candidateId)
                }
                onSave={onSave}
              />
            ))}
          </div>
        ) : (
          <section className="empty-state" aria-labelledby="no-results-heading">
            <div>
              <h2 id="no-results-heading">No trip matches every hard constraint</h2>
              <p>
                Review {hardConstraints.map((chip) => chip.label).join(", ") || "your trip limits"}.
              </p>
              <button type="button" className="secondary-command" onClick={onOpenFilters}>
                Adjust hard constraints
              </button>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}
