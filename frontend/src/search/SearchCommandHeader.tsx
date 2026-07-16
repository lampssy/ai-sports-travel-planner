import {
  AlertTriangle,
  ChevronDown,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import type { FormEvent, RefObject } from "react";

import type {
  RefinementOption,
  SearchV4Configuration,
  SearchV4RecommendationGroup,
} from "../types";
import { SnowcastLogo } from "../ui/SnowcastLogo";
import {
  buildParsedChips,
  factorLabels,
  formatAccess,
  formatLodging,
  formatPassPrice,
  groupLabels,
  type ParsedChip,
} from "./searchPresentation";
import { findSelectedCandidate, type SearchSession } from "./searchSession";

export function SearchCommandHeader({
  brief,
  loading,
  onBriefChange,
  onSubmit,
  onSearch,
  onCurrentTrip,
}: {
  brief: string;
  loading: boolean;
  onBriefChange: (brief: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSearch: () => void;
  onCurrentTrip: () => void;
}) {
  return (
    <header className="search-command-header">
      <div className="app-canvas search-command-header__inner">
        <button
          type="button"
          className="logo-button"
          aria-label="Go to search"
          onClick={onSearch}
        >
          <SnowcastLogo compact />
        </button>
        <form className="compact-search-form" onSubmit={onSubmit}>
          <label htmlFor="compact-trip-brief">Trip brief</label>
          <input
            id="compact-trip-brief"
            value={brief}
            onChange={(event) => onBriefChange(event.target.value)}
          />
          <button type="submit" disabled={loading}>
            <Search aria-hidden="true" size={18} />
            {loading ? "Updating recommendations" : "Update results"}
          </button>
        </form>
        <nav aria-label="Primary navigation" className="compact-nav">
          <button type="button" aria-current="page" onClick={onSearch}>
            Search
          </button>
          <button type="button" onClick={onCurrentTrip}>
            Current trip
          </button>
        </nav>
      </div>
    </header>
  );
}

export function SearchResultsWorkspace({
  session,
  loading,
  error,
  headingRef,
  adjustFiltersRef,
  onOpenFilters,
  onRemoveChip,
  onApplyRefinement,
  onToggleGroup,
  onSave,
}: {
  session: SearchSession;
  loading: boolean;
  error: string | null;
  headingRef: RefObject<HTMLHeadingElement>;
  adjustFiltersRef: RefObject<HTMLButtonElement>;
  onOpenFilters: () => void;
  onRemoveChip: (chip: ParsedChip) => void;
  onApplyRefinement: (questionId: string, option: RefinementOption) => void;
  onToggleGroup: (skiRegionId: string) => void;
  onSave: (configuration: SearchV4Configuration) => void;
}) {
  const chips = buildParsedChips(session.intent);
  const response = session.response;
  return (
    <main className="app-canvas results-workspace">
      <aside className="search-context" aria-label="Search context">
        <div className="search-context__heading">
          <ShieldCheck aria-hidden="true" size={20} />
          <div>
            <span>Search understood</span>
            <strong>{chips.length} active trip signals</strong>
          </div>
        </div>
        <ParsedChips chips={chips} onRemove={onRemoveChip} />
        <button
          type="button"
          ref={adjustFiltersRef}
          className="secondary-command"
          onClick={onOpenFilters}
        >
          <SlidersHorizontal aria-hidden="true" size={18} />
          Adjust filters
        </button>
      </aside>

      <section className="results-board" aria-live="polite">
        <div className="results-board__heading">
          <div>
            <p className="eyebrow">Conditions-aware ranking</p>
            <h1 ref={headingRef} tabIndex={-1}>
              Recommended ski trips
            </h1>
            <p>
              {response.eligible_candidate_count} eligible configurations ·{" "}
              {response.excluded_candidate_count} filtered out
            </p>
          </div>
          {response.ranking_status === "unscored" ? (
            <span className="warning-status">
              <AlertTriangle aria-hidden="true" size={17} />
              Unranked: {response.unscored_reason}
            </span>
          ) : null}
        </div>

        {loading ? (
          <p className="results-loading" role="status">
            Updating the ranking with your latest trip brief.
          </p>
        ) : null}
        {error ? (
          <p className="error-copy" role="alert">
            {error}
          </p>
        ) : null}
        <Refinements
          session={session}
          loading={loading}
          onApply={onApplyRefinement}
        />
        {response.results.length ? (
          <div className="result-list">
            {response.results.map((result) => (
              <ResultCard
                key={result.ski_region_id}
                result={result}
                selectedCandidateId={
                  session.selectedCandidateIdByGroup[result.ski_region_id]
                }
                expanded={session.expandedGroupIds.has(result.ski_region_id)}
                onToggle={() => onToggleGroup(result.ski_region_id)}
                onSave={onSave}
              />
            ))}
          </div>
        ) : (
          <EmptyState text="No configuration satisfies all hard constraints." />
        )}
      </section>
    </main>
  );
}

function ParsedChips({
  chips,
  onRemove,
}: {
  chips: ParsedChip[];
  onRemove: (chip: ParsedChip) => void;
}) {
  if (!chips.length) return <p className="muted-copy">No active filters.</p>;
  return (
    <div className="search-context__chips">
      {chips.map((chip) => (
        <button
          type="button"
          key={chip.id}
          className="context-chip"
          aria-label={`Remove ${chip.label}`}
          onClick={() => onRemove(chip)}
        >
          <span>{chip.label}</span>
          <X aria-hidden="true" size={14} />
        </button>
      ))}
    </div>
  );
}

function Refinements({
  session,
  loading,
  onApply,
}: {
  session: SearchSession;
  loading: boolean;
  onApply: (questionId: string, option: RefinementOption) => void;
}) {
  if (!session.response.refinements.length) return null;
  return (
    <div className="refinement-list">
      {session.response.refinements.map((item) => (
        <article key={item.question_id} className="refinement-card">
          <p className="eyebrow">This can reorder your results</p>
          <h2>{item.question}</h2>
          <p>{item.reason}</p>
          <div className="refinement-card__options">
            {item.options.map((option) => (
              <button
                type="button"
                key={option.label}
                onClick={() => onApply(item.question_id, option)}
                disabled={loading}
                title={option.description}
              >
                {option.label}
              </button>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function ResultCard({
  result,
  selectedCandidateId,
  expanded,
  onToggle,
  onSave,
}: {
  result: SearchV4RecommendationGroup;
  selectedCandidateId: string | undefined;
  expanded: boolean;
  onToggle: () => void;
  onSave: (configuration: SearchV4Configuration) => void;
}) {
  const configuration = findSelectedCandidate(result, selectedCandidateId);
  const explanationId = `result-evidence-${result.ski_region_id}`;
  return (
    <article className="result-card">
      <div className="result-card__summary">
        <div>
          <div className="result-card__rank-line">
            <span className="rank-marker">
              {configuration.ranking_status === "ranked"
                ? `#${result.rank}`
                : "Unranked option"}
            </span>
            <span>
              {configuration.stay_destination_name} · {configuration.stay_base_name}
            </span>
          </div>
          <h2>{result.ski_region_name}</h2>
          <p>
            Ski {configuration.ski_area_name} with {configuration.selected_pass.name}
          </p>
          <div className="result-card__metrics">
            <Pill>{formatAccess(configuration)}</Pill>
            <Pill>
              {configuration.selected_pass.accessible_piste_km != null
                ? `${configuration.selected_pass.accessible_piste_km} km pass coverage`
                : "Pass terrain unresolved"}
            </Pill>
            <Pill>{formatPassPrice(configuration)}</Pill>
            <Pill>{formatLodging(configuration)}</Pill>
          </div>
        </div>
        <div className="result-card__score">
          {configuration.fit_score != null ? (
            <div>
              <strong>{configuration.fit_score.toFixed(1)}</strong>
              <span>fit / 100</span>
            </div>
          ) : (
            <span className="warning-status">Unranked</span>
          )}
          <button type="button" onClick={() => onSave(configuration)}>
            Save trip
          </button>
        </div>
      </div>
      <button
        type="button"
        className="result-card__toggle"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={explanationId}
      >
        <span>
          {expanded
            ? "Hide evidence"
            : configuration.ranking_status === "ranked"
              ? "Why this fit?"
              : "Show evidence"}
        </span>
        <ChevronDown aria-hidden="true" size={20} />
      </button>
      {expanded ? (
        <RankingExplanation id={explanationId} configuration={configuration} />
      ) : null}
    </article>
  );
}

function RankingExplanation({
  id,
  configuration,
}: {
  id: string;
  configuration: SearchV4Configuration;
}) {
  return (
    <div id={id} className="ranking-explanation">
      <h3>Group contributions</h3>
      <div className="ranking-explanation__groups">
        {configuration.groups.map((group) => (
          <div key={group.group_id}>
            <strong>{groupLabels[group.group_id] ?? group.group_id}</strong>
            <span>
              {(group.normalized_share * 100).toFixed(0)}% budget ·{" "}
              {group.contribution_points.toFixed(1)} points
            </span>
          </div>
        ))}
      </div>
      <h3>Factor evidence</h3>
      <div className="ranking-explanation__factors">
        {configuration.factors.map((factor) => (
          <div key={factor.factor_id}>
            <strong>{factorLabels[factor.factor_id] ?? factor.factor_id}</strong>
            <p>{factor.provenance_summary}</p>
            {factor.warnings.length ? (
              <p className="watchout">{factor.warnings.join(" · ")}</p>
            ) : null}
            <span>
              {factor.effective_evidence_cap === 0
                ? "Unknown"
                : `${factor.contribution_points.toFixed(1)} points`}
            </span>
          </div>
        ))}
      </div>
      {configuration.constraint_warnings.length ? (
        <div className="constraint-warning">
          <strong>Constraint uncertainty</strong>
          {configuration.constraint_warnings.map((warning) => (
            <p key={`${warning.constraint_id}-${warning.code}`}>{warning.message}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return <span className="result-pill">{children}</span>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}
