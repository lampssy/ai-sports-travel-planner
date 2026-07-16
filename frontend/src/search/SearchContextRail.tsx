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

  return (
    <aside className="search-context" aria-label="Search context">
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
    </aside>
  );
}
