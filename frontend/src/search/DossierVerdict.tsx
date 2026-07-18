import {
  AlertTriangle,
  CheckCircle2,
  Footprints,
  MountainSnow,
  Save,
} from "lucide-react";
import type { RefObject } from "react";

import type { SearchV4Configuration } from "../types";
import { EvidenceQualityBadge } from "../ui/EvidenceQualityBadge";
import { TripEntityStack } from "../ui/TripEntityStack";
import {
  buildCandidateNarrative,
  evidenceQualityMode,
  formatAccess,
  formatPassPrice,
  snowWindowLabel,
} from "./searchPresentation";

export function DossierVerdict({
  configuration,
  rank,
  headingRef,
  onSave,
}: {
  configuration: SearchV4Configuration;
  rank: number;
  headingRef: RefObject<HTMLHeadingElement>;
  onSave: (configuration: SearchV4Configuration) => void;
}) {
  const narrative = buildCandidateNarrative(configuration);
  const evidenceMode = evidenceQualityMode(configuration);
  const unscored = configuration.ranking_status === "unscored";
  const reasonHeadingId = unscored ? "why-consider-it" : "why-it-leads";

  return (
    <header className="dossier-verdict">
      <div className="dossier-verdict__title">
        <p className="eyebrow">
          {unscored ? "Unranked option" : `#${rank}`} ·{" "}
          {configuration.stay_destination_name}
        </p>
        <h1 ref={headingRef} tabIndex={-1}>
          {configuration.ski_region_name} - {configuration.stay_base_name}
        </h1>
        <p className="dossier-verdict__selection">
          Selected configuration - stay in {configuration.stay_base_name}
        </p>
        <p className="dossier-verdict__summary">{narrative.verdict}</p>
      </div>

      <div className="dossier-verdict__signals" aria-label="Recommendation verdict">
        <div>
          <strong>{configuration.fit_score?.toFixed(1) ?? "Unscored"}</strong>
          <span>Trip fit</span>
        </div>
        <div>
          <strong>{snowWindowLabel(configuration)}</strong>
          <span>Snow window</span>
        </div>
        <EvidenceQualityBadge mode={evidenceMode} compact />
      </div>

      <button
        type="button"
        className="dossier-save"
        onClick={() => onSave(configuration)}
      >
        <Save aria-hidden="true" size={18} />
        Save as current trip
      </button>

      <section className="dossier-verdict__reasons" aria-labelledby={reasonHeadingId}>
        <p className="section-label" id={reasonHeadingId}>
          {unscored ? "Why consider it" : "Why it leads"}
        </p>
        <div>
          <p>
            <CheckCircle2 aria-hidden="true" size={20} />
            <span>
              <strong>Supported strength</strong>
              {narrative.strength ??
                (unscored
                  ? "This is a complete trip configuration with available supporting evidence."
                  : "This is a complete ranked trip configuration.")}
            </span>
          </p>
          <p>
            <AlertTriangle aria-hidden="true" size={20} />
            <span>
              <strong>Watchout</strong>
              {narrative.watchout ?? "Conditions and operations can change before travel."}
            </span>
          </p>
        </div>
      </section>

      <section className="dossier-verdict__entities" aria-label="Selected trip entities">
        <TripEntityStack
          destination={configuration.stay_destination_name}
          skiArea={configuration.ski_area_name}
          stayBase={configuration.stay_base_name}
        />
        <dl>
          <div>
            <dt>
              <MountainSnow aria-hidden="true" size={17} /> Selected pass
            </dt>
            <dd>
              {configuration.selected_pass.name} · {formatPassPrice(configuration)}
            </dd>
          </div>
          <div>
            <dt>
              <Footprints aria-hidden="true" size={17} /> Access
            </dt>
            <dd>{formatAccess(configuration)}</dd>
          </div>
        </dl>
      </section>
    </header>
  );
}
