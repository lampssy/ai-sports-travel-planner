import { GitBranch, RotateCcw, X } from "lucide-react";
import { useEffect, useState } from "react";

import type { RefinementOption, RefinementProposal } from "../types";
import { refinementPreviewCopy } from "./searchPresentation";

export function RefinementCard({
  refinement,
  loading,
  error,
  onApply,
  onSkip,
}: {
  refinement: RefinementProposal;
  loading: boolean;
  error: string | null;
  onApply: (questionId: string, option: RefinementOption) => void;
  onSkip: (questionId: string) => void;
}) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  useEffect(() => setSelectedIndex(null), [refinement.question_id]);
  const selected = selectedIndex == null ? null : refinement.options[selectedIndex];

  return (
    <article className="contextual-refinement">
      <p className="contextual-refinement__eyebrow">
        <GitBranch aria-hidden="true" size={17} />
        Next refinement
      </p>
      <h2>{refinement.reason}</h2>
      <p className="contextual-refinement__question">{refinement.question}</p>
      <fieldset className="refinement-options">
        <legend className="sr-only">Refinement options</legend>
        {refinement.options.map((option, index) => (
          <label key={`${refinement.question_id}-${option.label}`}>
            <input
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
          {refinementPreviewCopy(selected.preview)}
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
          {error ? "Retry apply and rerank" : "Apply and rerank"}
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
