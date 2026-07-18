import { SlidersHorizontal } from "lucide-react";
import type { RefObject } from "react";

import type {
  RefinementOption,
  RefinementProposal,
  SearchIntent,
} from "../types";
import {
  buildParsedChips,
  type ParsedChip,
} from "./searchPresentation";
import { RefinementCard } from "./RefinementCard";
import type { RefinementLifecycleStatus } from "./searchSession";

const REFINEMENT_STATUS_COPY: Partial<
  Record<RefinementLifecycleStatus, string>
> = {
  loading: "Checking whether one answer could improve this ranking.",
  slow:
    "Your ranking is ready. Snowcast is checking whether one answer could improve it.",
  retrying:
    "Snowcast is waiting a moment before checking for another useful question.",
  stale: "A newer ranking replaced this refinement check.",
  not_needed: "No follow-up would materially change these results.",
  skipped: "Follow-up skipped. Results unchanged.",
};

const REFINEMENT_ANNOUNCEMENT_COPY: Partial<
  Record<RefinementLifecycleStatus, string>
> = {
  ...REFINEMENT_STATUS_COPY,
  temporarily_unavailable:
    "No additional refinement is available right now. Your results are unchanged.",
};

function ContextGroup({
  label,
  chips,
  disabled,
  onRemove,
}: {
  label: string;
  chips: ParsedChip[];
  disabled: boolean;
  onRemove: (chip: ParsedChip) => void;
}) {
  if (!chips.length) return null;
  return (
    <div className="search-context__group" role="group" aria-label={label}>
      <p>{label}</p>
      <div className="search-context__chips">
        {chips.map((chip) => (
          <button
            type="button"
            key={chip.id}
            className="context-chip"
            aria-label={`Remove ${chip.label}`}
            disabled={disabled}
            onClick={() => onRemove(chip)}
          >
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function SearchContextRail({
  intent,
  refinement,
  refinementStatus,
  loading,
  refinementError,
  refinementControlRef,
  adjustFiltersRef,
  onOpenFilters,
  onRemoveChip,
  onApplyRefinement,
  onSkipRefinement,
}: {
  intent: SearchIntent;
  refinement: RefinementProposal | null;
  refinementStatus: RefinementLifecycleStatus;
  loading: boolean;
  refinementError: string | null;
  refinementControlRef: RefObject<HTMLInputElement>;
  adjustFiltersRef: RefObject<HTMLButtonElement>;
  onOpenFilters: () => void;
  onRemoveChip: (chip: ParsedChip) => void;
  onApplyRefinement: (questionId: string, option: RefinementOption) => void;
  onSkipRefinement: (questionId: string) => void;
}) {
  const chips = buildParsedChips(intent);
  const hard = chips.filter((chip) =>
    ["location", "travelWindow", "lodgingBudget", "stayQuality", "travelLimit", "skill"].includes(
      chip.action.kind,
    ),
  );
  const preferences = chips.filter((chip) => !hard.includes(chip));
  const lifecycleCopy = REFINEMENT_STATUS_COPY[refinementStatus];
  const refinementAnnouncement = refinement
    ? `A refinement question is ready. ${refinement.question}`
    : REFINEMENT_ANNOUNCEMENT_COPY[refinementStatus];

  return (
    <aside className="search-context" aria-label="Search context">
      {refinementAnnouncement ? (
        <p
          className="sr-only"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          {refinementAnnouncement}
        </p>
      ) : null}
      <div className="search-context__heading">
        <div>
          <span>Search understood</span>
          <strong>Your active trip decisions</strong>
        </div>
        <button
          type="button"
          ref={adjustFiltersRef}
          className="text-action search-context__adjust"
          disabled={loading}
          onClick={onOpenFilters}
        >
          <SlidersHorizontal aria-hidden="true" size={17} />
          Adjust
        </button>
      </div>
      <ContextGroup
        label="Hard constraints"
        chips={hard}
        disabled={loading}
        onRemove={onRemoveChip}
      />
      <ContextGroup
        label="Preferences"
        chips={preferences}
        disabled={loading}
        onRemove={onRemoveChip}
      />
      {refinement ? (
        <RefinementCard
          key={refinement.question_id}
          refinement={refinement}
          loading={loading}
          error={refinementError}
          firstOptionRef={refinementControlRef}
          onApply={onApplyRefinement}
          onSkip={onSkipRefinement}
        />
      ) : null}
      {!refinement && lifecycleCopy ? (
        <div className="contextual-refinement">
          <p>{lifecycleCopy}</p>
          {refinementError ? (
            <p className="refinement-error">{refinementError}</p>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}
