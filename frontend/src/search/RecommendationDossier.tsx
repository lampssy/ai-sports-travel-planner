import { ArrowLeft } from "lucide-react";
import { useEffect, useRef } from "react";

import type { SearchV4Configuration } from "../types";
import { DossierVerdict } from "./DossierVerdict";
import { RecommendationNavigator } from "./RecommendationNavigator";
import { ScoringDetails } from "./ScoringDetails";
import {
  formatPassPrice,
} from "./searchPresentation";
import { findSelectedCandidate, type SearchSession } from "./searchSession";

const anchors = [
  ["snow-evidence", "Snow evidence"],
  ["trip-configuration", "Trip configuration"],
  ["alternatives", "Alternatives"],
  ["accommodation", "Accommodation"],
  ["scoring-details", "Scoring details"],
] as const;

export function RecommendationDossier({
  session,
  skiRegionId,
  candidateId,
  onSwitch,
  onReturn,
  onSave,
  onSelectCandidate,
  onToggleNavigator,
}: {
  session: SearchSession;
  skiRegionId: string;
  candidateId: string;
  onSwitch: (skiRegionId: string, candidateId: string) => void;
  onReturn: () => void;
  onSave: (configuration: SearchV4Configuration) => void;
  onSelectCandidate: (skiRegionId: string, candidateId: string) => void;
  onToggleNavigator: () => void;
}) {
  const group =
    session.response.results.find((item) => item.ski_region_id === skiRegionId) ??
    session.response.results[0];
  const configuration = findSelectedCandidate(group, candidateId);
  const candidates = [group.top_configuration, ...group.alternative_configurations];
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, [group.ski_region_id, configuration.candidate_id]);

  return (
    <main
      className={`dossier-page${
        session.dossierNavigatorCollapsed
          ? " dossier-page--navigator-collapsed"
          : ""
      }`}
    >
      <RecommendationNavigator
        session={session}
        currentGroup={group}
        onSwitch={onSwitch}
        onReturn={onReturn}
        onToggle={onToggleNavigator}
      />

      <article className="dossier-content">
        <button type="button" className="text-action dossier-back" onClick={onReturn}>
          <ArrowLeft aria-hidden="true" size={17} />
          Back to results
        </button>

        <p className="sr-only" aria-live="polite" aria-atomic="true">
          Showing {configuration.ski_region_name}, stay in {configuration.stay_base_name}
        </p>

        <DossierVerdict
          configuration={configuration}
          rank={group.rank}
          headingRef={headingRef}
          onSave={onSave}
        />

        <nav className="dossier-anchor-nav" aria-label="Dossier sections">
          {anchors.map(([id, label]) => (
            <a key={id} href={`#${id}`}>
              {label}
            </a>
          ))}
        </nav>

        <section className="dossier-section" id="snow-evidence">
          <p className="section-label">Snow evidence</p>
          <h2>Snow evidence for your search window</h2>
        </section>

        <section className="dossier-section" id="trip-configuration">
          <p className="section-label">Selected trip configuration</p>
          <h2>{configuration.stay_base_name} and {configuration.selected_pass.name}</h2>
          <dl className="dossier-facts">
            <div><dt>Destination</dt><dd>{configuration.stay_destination_name}</dd></div>
            <div><dt>Ski area</dt><dd>{configuration.ski_area_name}</dd></div>
            <div><dt>Stay base</dt><dd>{configuration.stay_base_name}</dd></div>
            <div><dt>Selected pass</dt><dd>{configuration.selected_pass.name}</dd></div>
            <div><dt>Pass price</dt><dd>{formatPassPrice(configuration)}</dd></div>
            <div>
              <dt>Accessible terrain</dt>
              <dd>
                {configuration.selected_pass.accessible_piste_km != null
                  ? `${configuration.selected_pass.accessible_piste_km} km`
                  : "Not available"}
              </dd>
            </div>
          </dl>
        </section>

        <section className="dossier-section" id="alternatives">
          <p className="section-label">Alternatives</p>
          <h2>Configurations in {group.ski_region_name}</h2>
          <div className="dossier-alternatives">
            {candidates.map((candidate) => {
              const selected = candidate.candidate_id === configuration.candidate_id;
              return (
                <button
                  type="button"
                  key={candidate.candidate_id}
                  aria-label={`Select ${candidate.stay_base_name} with ${candidate.selected_pass.name}`}
                  aria-pressed={selected}
                  onClick={() => onSelectCandidate(group.ski_region_id, candidate.candidate_id)}
                >
                  <span aria-hidden="true" className="dossier-alternatives__radio" />
                  <span>
                    <strong>{candidate.stay_base_name}</strong>
                    <small>{candidate.selected_pass.name}</small>
                  </span>
                  <em>{selected ? "Current" : `#${group.rank}`}</em>
                </button>
              );
            })}
          </div>
        </section>

        <section className="dossier-section dossier-accommodation" id="accommodation">
          <p className="section-label">Accommodation</p>
          <h2>Stay in {configuration.stay_base_name}</h2>
        </section>

        <section className="dossier-section" id="scoring-details">
          <p className="section-label">Decision evidence</p>
          <h2>Scoring details</h2>
          <ScoringDetails configuration={configuration} />
        </section>
      </article>
    </main>
  );
}
