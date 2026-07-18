import { GitBranch, RotateCcw, X } from "lucide-react";
import { useEffect, useId, useState, type RefObject } from "react";

import type { RefinementOption, RefinementProposal } from "../types";
import { refinementPreviewCopy } from "./searchPresentation";

export function RefinementCard({
  refinement,
  loading,
  error,
  firstOptionRef,
  onApply,
  onSkip,
}: {
  refinement: RefinementProposal;
  loading: boolean;
  error: string | null;
  firstOptionRef?: RefObject<HTMLInputElement>;
  onApply: (questionId: string, option: RefinementOption) => void;
  onSkip: (questionId: string) => void;
}) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  useEffect(() => setSelectedIndex(null), [refinement.question_id]);
  const selected = selectedIndex == null ? null : refinement.options[selectedIndex];
  const questionHeadingId = useId();

  return (
    <article className="contextual-refinement">
      <p className="contextual-refinement__eyebrow">
        <GitBranch aria-hidden="true" size={17} />
        Next refinement
      </p>
      <h2 id={questionHeadingId}>{refinement.question}</h2>
      <p className="contextual-refinement__reason">{refinement.reason}</p>
      <fieldset
        className="refinement-options"
        aria-labelledby={questionHeadingId}
      >
        {refinement.options.map((option, index) => (
          <label key={`${refinement.question_id}-${option.label}`}>
            <input
              ref={index === 0 ? firstOptionRef : undefined}
              type="radio"
              name={`refinement-${refinement.question_id}`}
              checked={selectedIndex === index}
              onChange={() => setSelectedIndex(index)}
              disabled={loading}
            />
            <span>
              <strong>{option.label}</strong>
              <small>{option.description}</small>
            </span>
          </label>
        ))}
      </fieldset>
      {selected ? (
        <p className="refinement-preview" role="status">
          {refinementPreviewCopy(selected.preview, selected.intent_changed)}
        </p>
      ) : null}
      {error ? (
        <p className="refinement-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="refinement-actions">
        <button
          type="button"
          className="primary-refinement-action"
          disabled={!selected || loading}
          onClick={() => selected && onApply(refinement.question_id, selected)}
        >
          {error ? <RotateCcw aria-hidden="true" size={17} /> : null}
          {error
            ? "Retry apply and rerank"
            : selected?.intent_changed === false
              ? "Keep current ranking"
              : "Apply and rerank"}
        </button>
        {selected ? (
          <button
            type="button"
            className="text-action"
            disabled={loading}
            onClick={() => setSelectedIndex(null)}
          >
            <X aria-hidden="true" size={16} />
            Clear
          </button>
        ) : null}
        <button
          type="button"
          className="text-action"
          disabled={loading}
          onClick={() => onSkip(refinement.question_id)}
        >
          Skip for now
        </button>
      </div>
    </article>
  );
}
