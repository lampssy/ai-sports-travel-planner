import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Save,
} from "lucide-react";

import { buildDossierHref } from "../navigation";
import type {
  SearchV4Configuration,
  SearchV4RecommendationGroup,
  TravelWindow,
} from "../types";
import { EvidenceQualityBadge } from "../ui/EvidenceQualityBadge";
import { TripEntityStack } from "../ui/TripEntityStack";
import {
  buildCandidateNarrative,
  evidenceQualityMode,
  snowFitPresentation,
  terrainPresentation,
  type TripEssentialCategory,
} from "./searchPresentation";
import { findSelectedCandidate } from "./searchSession";
import { ScoringDetails } from "./ScoringDetails";
import { TripEssentials } from "./TripEssentials";

export function RecommendationCard({
  result,
  travelWindow,
  selectedCandidateId,
  expanded,
  essentialCategories,
  changedRank,
  saveError = null,
  onToggle,
  onSelectCandidate,
  onSave,
}: {
  result: SearchV4RecommendationGroup;
  travelWindow?: TravelWindow;
  selectedCandidateId: string | undefined;
  expanded: boolean;
  essentialCategories: TripEssentialCategory[];
  changedRank: boolean;
  saveError?: string | null;
  onToggle: () => void;
  onSelectCandidate: (candidateId: string) => void;
  onSave: (configuration: SearchV4Configuration) => void;
}) {
  const configuration = findSelectedCandidate(result, selectedCandidateId);
  const terrain = terrainPresentation(configuration.selected_pass);
  const detailsId = `recommendation-${result.ski_region_id}`;
  const narrative = buildCandidateNarrative(configuration);
  const evidenceMode = evidenceQualityMode(configuration);
  const snowFit = snowFitPresentation(configuration, travelWindow);
  const candidates = [result.top_configuration, ...result.alternative_configurations];

  return (
    <article
      className={`recommendation-card${changedRank ? " recommendation-card--changed" : ""}`}
      data-rank-changed={changedRank || undefined}
    >
      <header className="recommendation-card__header">
        <span className="rank-marker">
          {configuration.ranking_status === "ranked"
            ? `#${result.rank}`
            : "Fit comparison unavailable"}
        </span>
        <span className="recommendation-card__identity">
          <span className="eyebrow">
            {configuration.stay_destination_name}
          </span>
          <h2 className="recommendation-card__title">
            {result.ski_region_name}{" "}
            <span>— stay in {configuration.stay_base_name}</span>
          </h2>
          <span className="recommendation-card__verdict">{narrative.verdict}</span>
        </span>
        <span className="recommendation-card__scores">
          <span>
            <strong>
              {configuration.fit_score != null
                ? configuration.fit_score.toFixed(1)
                : "—"}
            </strong>
            <small>Trip fit</small>
          </span>
          <span>
            <strong>{snowFit.value}</strong>
            <small>{snowFit.label}</small>
          </span>
        </span>
        <button
          type="button"
          className="recommendation-card__toggle"
          aria-label={`${expanded ? "Collapse" : "Expand"} ${result.ski_region_name}. Stay in ${configuration.stay_base_name}. Trip fit ${configuration.fit_score != null ? configuration.fit_score.toFixed(1) : "not scored"}. ${snowFit.label}: ${snowFit.value}.`}
          aria-expanded={expanded}
          aria-controls={detailsId}
          title={`${expanded ? "Collapse" : "Expand"} trip option details`}
          onClick={onToggle}
        >
          <ChevronDown aria-hidden="true" size={22} />
        </button>
      </header>

      {expanded ? (
        <div id={detailsId} className="recommendation-card__details">
          <div className="recommendation-card__main">
            <TripEntityStack
              destination={configuration.stay_destination_name}
              skiArea={configuration.ski_area_name}
              stayBase={configuration.stay_base_name}
              compact
            />
            <TripEssentials
              configuration={configuration}
              categories={essentialCategories}
            />
            <div className="recommendation-card__evidence-grid">
              <EvidenceQualityBadge mode={evidenceMode} compact />
              <section className="selected-pass" aria-label="Selected pass">
                <p className="section-label">Selected pass</p>
                <strong>{configuration.selected_pass.name}</strong>
                {terrain ? <span>{terrain.evidenceLabel}</span> : null}
              </section>
            </div>
            <div className="recommendation-card__signals">
              {narrative.strength ? (
                <p className="strength">
                  <CheckCircle2 aria-hidden="true" size={18} />
                  <span>{narrative.strength}</span>
                </p>
              ) : null}
              {narrative.watchout ? (
                <p className="watchout">
                  <AlertTriangle aria-hidden="true" size={18} />
                  <span>{narrative.watchout}</span>
                </p>
              ) : null}
            </div>
          </div>

          <aside className="recommendation-card__actions" aria-label="Trip option actions">
            <a
              className="primary-card-action"
              href={buildDossierHref(result.ski_region_id, configuration.candidate_id)}
            >
              <ArrowRight aria-hidden="true" size={18} />
              View trip details
            </a>
            <button
              type="button"
              className="secondary-card-action"
              onClick={() => onSave(configuration)}
            >
              <Save aria-hidden="true" size={18} />
              Save as current trip
            </button>
            {saveError ? (
              <p className="error-copy" role="alert">
                {saveError}
              </p>
            ) : null}
            {candidates.length > 1 ? (
              <section className="alternative-configurations">
                <p className="section-label">Alternative trip options</p>
                <div>
                  {candidates.map((candidate) => {
                    const selected = candidate.candidate_id === configuration.candidate_id;
                    return (
                      <button
                        type="button"
                        key={candidate.candidate_id}
                        aria-label={`Select ${candidate.stay_base_name} with ${candidate.selected_pass.name}`}
                        aria-pressed={selected}
                        onClick={() => onSelectCandidate(candidate.candidate_id)}
                      >
                        <span>{candidate.stay_base_name}</span>
                        <small>{candidate.selected_pass.name}</small>
                      </button>
                    );
                  })}
                </div>
              </section>
            ) : null}
          </aside>
          {configuration.ranking_status === "ranked" ? (
            <ScoringDetails configuration={configuration} travelWindow={travelWindow} />
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
