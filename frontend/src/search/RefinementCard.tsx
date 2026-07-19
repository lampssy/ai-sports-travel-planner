import { ChevronDown, GitBranch, RotateCcw, X } from "lucide-react";
import { useEffect, useId, useRef, useState, type Ref } from "react";

import type { RefinementOption, RefinementProposal } from "../types";
import { refinementPreviewCopy } from "./searchPresentation";

export function RefinementCard({
  refinement,
  loading,
  error,
  focusControlRef,
  onApply,
  onSkip,
}: {
  refinement: RefinementProposal;
  loading: boolean;
  error: string | null;
  focusControlRef?: Ref<HTMLElement>;
  onApply: (refinement: RefinementProposal, option: RefinementOption) => void;
  onSkip: (refinement: RefinementProposal) => void;
}) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(false);
  const isNarrow = useNarrowRefinementViewport();
  const firstOptionRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    setSelectedIndex(null);
    setExpanded(false);
  }, [refinement.question_id]);
  useEffect(() => {
    if (isNarrow && expanded) firstOptionRef.current?.focus();
  }, [expanded, isNarrow]);
  const selected = selectedIndex == null ? null : refinement.options[selectedIndex];
  const questionHeadingId = useId();
  const disclosureBodyId = useId();
  const showBody = !isNarrow || expanded;

  return (
    <article className="contextual-refinement">
      <p className="contextual-refinement__eyebrow">
        <GitBranch aria-hidden="true" size={17} />
        Next refinement
      </p>
      <h2 id={questionHeadingId}>{refinement.question}</h2>
      {isNarrow ? (
        <button
          ref={focusControlRef as Ref<HTMLButtonElement>}
          type="button"
          className="refinement-disclosure"
          aria-expanded={expanded}
          aria-controls={disclosureBodyId}
          onClick={() => setExpanded((current) => !current)}
        >
          Choose a preference
          <ChevronDown aria-hidden="true" size={17} />
        </button>
      ) : null}
      <div
        id={disclosureBodyId}
        className="refinement-disclosure__body"
        hidden={!showBody}
      >
        <p className="contextual-refinement__reason">{refinement.reason}</p>
        <fieldset className="refinement-options" aria-labelledby={questionHeadingId}>
          {refinement.options.map((option, index) => (
            <label key={`${refinement.question_id}-${option.label}`}>
              <input
                ref={
                  index === 0
                    ? isNarrow
                      ? firstOptionRef
                      : (focusControlRef as Ref<HTMLInputElement>)
                    : undefined
                }
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
        {selected && !error ? (
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
            onClick={() => selected && onApply(refinement, selected)}
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
            onClick={() => onSkip(refinement)}
          >
            Skip this question
          </button>
        </div>
      </div>
    </article>
  );
}

function useNarrowRefinementViewport(): boolean {
  const query = "(max-width: 56rem)";
  const [isNarrow, setIsNarrow] = useState(
    () => typeof window !== "undefined" && window.matchMedia?.(query).matches,
  );

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const media = window.matchMedia(query);
    const update = () => setIsNarrow(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return isNarrow;
}
