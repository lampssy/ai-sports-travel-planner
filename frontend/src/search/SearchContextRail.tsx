import { SlidersHorizontal } from "lucide-react";
import type { ReactNode, RefObject } from "react";

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
  action,
}: {
  label: string;
  chips: ParsedChip[];
  disabled: boolean;
  onRemove: (chip: ParsedChip) => void;
  action?: ReactNode;
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
      {action}
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
  onRetryRefinement,
  onKeepResults,
}: {
  intent: SearchIntent;
  refinement: RefinementProposal | null;
  refinementStatus: RefinementLifecycleStatus;
  loading: boolean;
  refinementError: string | null;
  refinementControlRef: RefObject<HTMLElement>;
  adjustFiltersRef: RefObject<HTMLButtonElement>;
  onOpenFilters: (trigger: HTMLButtonElement) => void;
  onRemoveChip: (chip: ParsedChip) => void;
  onApplyRefinement: (
    refinement: RefinementProposal,
    option: RefinementOption,
  ) => void;
  onSkipRefinement: (refinement: RefinementProposal) => void;
  onRetryRefinement?: () => void;
  onKeepResults?: () => void;
}) {
  const chips = buildParsedChips(intent);
  const requiredFactorIds = new Set(
    intent.factor_preferences
      .filter((preference) => preference.mode === "require")
      .map((preference) => preference.factor_id),
  );
  const hard = chips.filter((chip) =>
    ["location", "travelWindow", "lodgingBudget", "stayQuality", "travelLimit", "skill"].includes(
      chip.action.kind,
    ) ||
      (chip.action.kind === "preference" &&
        requiredFactorIds.has(chip.action.id)),
  );
  const preferences = chips.filter((chip) => !hard.includes(chip));
  const visiblePreferences = preferences.slice(0, 3);
  const hasHiddenPreferences = preferences.length > visiblePreferences.length;
  const lifecycleCopy = REFINEMENT_STATUS_COPY[refinementStatus];
  const terminalFailure =
    !refinement &&
    refinementStatus === "temporarily_unavailable" &&
    refinementError;
  const refinementAnnouncement = terminalFailure
    ? null
    : refinement
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
          onClick={(event) => onOpenFilters(event.currentTarget)}
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
        chips={visiblePreferences}
        disabled={loading}
        onRemove={onRemoveChip}
        action={
          hasHiddenPreferences ? (
            <div className="search-context__group-action">
              <button
                type="button"
                className="text-action search-context__view-all"
                disabled={loading}
                onClick={(event) => onOpenFilters(event.currentTarget)}
              >
                View all {preferences.length} preferences
              </button>
            </div>
          ) : null
        }
      />
      {refinement ? (
        <RefinementCard
          key={refinement.question_id}
          refinement={refinement}
          loading={loading}
          error={refinementError}
          focusControlRef={refinementControlRef}
          onApply={onApplyRefinement}
          onSkip={onSkipRefinement}
        />
      ) : null}
      {terminalFailure ? (
        <div className="contextual-refinement contextual-refinement--error">
          <p className="contextual-refinement__eyebrow">Follow-up unavailable</p>
          <p className="refinement-error" role="alert">
            {refinementError}
          </p>
          <div className="refinement-actions">
            <button
              type="button"
              className="primary-refinement-action"
              disabled={loading}
              onClick={onRetryRefinement}
            >
              Try again
            </button>
            <button
              type="button"
              className="text-action"
              disabled={loading}
              onClick={onKeepResults}
            >
              Keep these results
            </button>
          </div>
        </div>
      ) : null}
      {!refinement && !terminalFailure && lifecycleCopy ? (
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
