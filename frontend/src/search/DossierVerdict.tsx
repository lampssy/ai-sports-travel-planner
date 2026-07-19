import {
  AlertTriangle,
  CheckCircle2,
  Footprints,
  MountainSnow,
  Save,
} from "lucide-react";
import type { RefObject } from "react";

import type { SearchV4Configuration, TravelWindow } from "../types";
import { EvidenceQualityBadge } from "../ui/EvidenceQualityBadge";
import { TripEntityStack } from "../ui/TripEntityStack";
import {
  buildCandidateNarrative,
  evidenceQualityMode,
  formatAccess,
  formatPassPrice,
  snowFitPresentation,
} from "./searchPresentation";

export function DossierVerdict({
  configuration,
  rank,
  travelWindow,
  headingRef,
  onSave,
  saveError,
}: {
  configuration: SearchV4Configuration;
  rank: number;
  travelWindow?: TravelWindow;
  headingRef: RefObject<HTMLHeadingElement>;
  onSave: (configuration: SearchV4Configuration) => void;
  saveError: string | null;
}) {
  const narrative = buildCandidateNarrative(configuration, travelWindow);
  const evidenceMode = evidenceQualityMode(configuration);
  const unscored = configuration.ranking_status === "unscored";
  const snowFit = snowFitPresentation(configuration, travelWindow);

  return (
    <header className="dossier-verdict">
      <div className="dossier-verdict__title">
        <p className="eyebrow">
          {unscored ? "Fit comparison unavailable" : `#${rank}`} ·{" "}
          {configuration.stay_destination_name}
        </p>
        <h1 ref={headingRef} tabIndex={-1}>
          {configuration.ski_region_name} - {configuration.stay_base_name}
        </h1>
        <p className="dossier-verdict__selection">
          Recommended place to stay: {configuration.stay_base_name}
        </p>
        <p className="dossier-verdict__summary">{narrative.verdict}</p>
      </div>

      <div className="dossier-verdict__signals" aria-label="Recommendation verdict">
        <div>
          <strong>{configuration.fit_score?.toFixed(1) ?? "—"}</strong>
          <span>Trip fit</span>
        </div>
        <div>
          <strong>{snowFit.value}</strong>
          <span>{snowFit.label}</span>
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
      {saveError ? (
        <p className="error-copy" role="alert">
          {saveError}
        </p>
      ) : null}

      <section className="dossier-verdict__reasons" aria-label="Trip reasons">
        <div>
          <p>
            <CheckCircle2 aria-hidden="true" size={20} />
            <span>
              <strong>Why it fits</strong>
              {narrative.strength ??
                (unscored
                  ? "This trip option is shown without a fit comparison because key details are unavailable."
                  : "This trip option has available supporting evidence.")}
            </span>
          </p>
          <p>
            <AlertTriangle aria-hidden="true" size={20} />
            <span>
              <strong>Main concern</strong>
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
