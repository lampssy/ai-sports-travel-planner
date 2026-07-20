import {
  AlertTriangle,
  CalendarDays,
  MountainSnow,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  TrendingUp,
  X,
} from "lucide-react";
import type { FormEvent, RefObject } from "react";

import type { ParsedChip } from "./searchPresentation";

export function Homepage({
  brief,
  loading,
  error,
  chips,
  adjustFiltersRef,
  onBriefChange,
  onSubmit,
  onOpenFilters,
  onRemoveChip,
}: {
  brief: string;
  loading: boolean;
  error: string | null;
  chips: ParsedChip[];
  adjustFiltersRef: RefObject<HTMLButtonElement>;
  onBriefChange: (brief: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onOpenFilters: (trigger: HTMLButtonElement) => void;
  onRemoveChip: (chip: ParsedChip) => void;
}) {
  return (
    <main className="homepage">
      <section className="homepage-stage">
        <div className="app-canvas homepage-stage__intro">
          <div>
            <p className="homepage-stage__eyebrow">Conditions-aware planning</p>
            <h1>Conditions-aware ski trips, planned around your window.</h1>
            <p className="homepage-stage__summary">
              Snowcast compares complete ski trips using snow fit for your dates,
              mountain fit, where to stay, travel effort, value, and evidence.
            </p>
          </div>
          <div className="planning-signal">
            <MountainSnow aria-hidden="true" size={22} />
            <div>
              <span>Planning signal</span>
              <strong>Late-season trips favor altitude and glacier access.</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="homepage-workspace app-canvas" aria-label="Plan a ski trip">
        <div className="command-surface">
          <form className="command-form" onSubmit={onSubmit}>
            <label htmlFor="trip-brief" className="command-form__label">
              Describe your ski trip
            </label>
            <div className="command-form__row">
              <textarea
                id="trip-brief"
                value={brief}
                onChange={(event) => onBriefChange(event.target.value)}
                placeholder="A snow-reliable intermediate trip in the Alps for March, close to the lifts"
                rows={2}
              />
              <button type="submit" className="primary-command" disabled={loading}>
                <Search aria-hidden="true" size={22} />
                {loading ? "Finding trip options" : "Find trip options"}
              </button>
            </div>
            <div className="command-form__context">
              <div className="parsed-chips" aria-label="Search understood">
                {chips.map((chip) => (
                  <button
                    type="button"
                    key={chip.id}
                    className="parsed-chip"
                    aria-label={`Remove ${chip.label}`}
                    onClick={() => onRemoveChip(chip)}
                  >
                    <span>{chip.label}</span>
                    <X aria-hidden="true" size={14} />
                  </button>
                ))}
              </div>
              <div className="understood-status">
                <ShieldCheck aria-hidden="true" size={20} />
                <span>{chips.length} trip details understood</span>
              </div>
              <button
                type="button"
                ref={adjustFiltersRef}
                className="text-action"
                onClick={(event) => onOpenFilters(event.currentTarget)}
              >
                <SlidersHorizontal aria-hidden="true" size={18} />
                Adjust filters
              </button>
            </div>
            {loading ? (
              <p className="loading-copy" role="status">
                Interpreting your brief and evaluating catalog, pass, climate,
                and forecast evidence.
              </p>
            ) : null}
            {error ? (
              <p role="alert" className="error-copy">
                {error}
              </p>
            ) : null}
          </form>

          <article className="example-recommendation">
            <div className="example-recommendation__label">
              Example trip option
            </div>
            <div className="example-recommendation__grid">
              <div className="example-recommendation__identity">
                <span className="rank-marker">#1</span>
                <p>Italy · Aosta Valley</p>
                <h2>Cervinia</h2>
                <strong>Stay in Breuil-Cervinia</strong>
              </div>
              <div className="example-metric">
                <TrendingUp aria-hidden="true" size={20} />
                <span>Trip fit</span>
                <strong>Excellent match</strong>
              </div>
              <div className="example-metric">
                <CalendarDays aria-hidden="true" size={20} />
                <span>Snow fit for your dates</span>
                <strong>Strong fit</strong>
              </div>
              <div className="example-metric">
                <ShieldCheck aria-hidden="true" size={20} />
                <span>Evidence quality</span>
                <strong>Archive-backed</strong>
              </div>
            </div>
            <div className="example-recommendation__reasoning">
              <p>
                <MountainSnow aria-hidden="true" size={19} />
                <span>High-elevation terrain supports a strong snow fit for March.</span>
              </p>
              <p className="watchout">
                <AlertTriangle aria-hidden="true" size={19} />
                <span>Lower slopes can soften during warm March periods.</span>
              </p>
            </div>
            <p className="example-disclaimer">
              Illustrative planning example, not live availability.
            </p>
          </article>
        </div>
      </section>
    </main>
  );
}
