import { ArrowLeft } from "lucide-react";
import { useEffect, useRef } from "react";

import type { SearchV4Configuration } from "../types";
import { AccommodationHandoff } from "./AccommodationHandoff";
import { DecisionEvidenceLedger } from "./DecisionEvidenceLedger";
import { DossierVerdict } from "./DossierVerdict";
import { RecommendationNavigator } from "./RecommendationNavigator";
import { ScoringDetails } from "./ScoringDetails";
import { SnowEvidence } from "./SnowEvidence";
import { TripConfigurationDetails } from "./TripConfigurationDetails";
import { findSelectedCandidate, type SearchSession } from "./searchSession";

const anchors = [
  ["snow-evidence", "Snow & weather"],
  ["trip-configuration", "Trip details"],
  ["alternatives", "Alternatives"],
  ["accommodation", "Accommodation"],
  ["decision-evidence", "Why this trip"],
  ["scoring-details", "How ranking works"],
] as const;

export function RecommendationDossier({
  session,
  skiRegionId,
  candidateId,
  onSwitch,
  onReturn,
  onSave,
  saveError = null,
  onSelectCandidate,
  onToggleNavigator,
}: {
  session: SearchSession;
  skiRegionId: string;
  candidateId: string;
  onSwitch: (skiRegionId: string, candidateId: string) => void;
  onReturn: () => void;
  onSave: (configuration: SearchV4Configuration) => void;
  saveError?: string | null;
  onSelectCandidate: (skiRegionId: string, candidateId: string) => void;
  onToggleNavigator: () => void;
}) {
  const group =
    session.response.results.find((item) => item.ski_region_id === skiRegionId) ??
    session.response.results[0];
  const configuration = findSelectedCandidate(group, candidateId);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const unscored = configuration.ranking_status === "unscored";
  const visibleAnchors = unscored
    ? anchors.filter(([id]) => id !== "scoring-details")
    : anchors;

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
          saveError={saveError}
        />

        <nav className="dossier-anchor-nav" aria-label="Dossier sections">
          {visibleAnchors.map(([id, label]) => (
            <a key={id} href={`#${id}`}>
              {label}
            </a>
          ))}
        </nav>

        <SnowEvidence
          intent={session.response.applied_intent}
          skiAreaId={configuration.ski_area_id}
          skiAreaName={configuration.ski_area_name}
        />

        <TripConfigurationDetails
          group={group}
          configuration={configuration}
          onSelectCandidate={onSelectCandidate}
        />

        <AccommodationHandoff configuration={configuration} />

        <DecisionEvidenceLedger configuration={configuration} />

        {!unscored ? (
          <section className="dossier-section" id="scoring-details">
            <p className="section-label">Decision evidence</p>
            <h2>Scoring details</h2>
            <ScoringDetails
              configuration={configuration}
              rankingPolicyVersion={session.response.ranking_policy_version}
            />
          </section>
        ) : null}
      </article>
    </main>
  );
}
