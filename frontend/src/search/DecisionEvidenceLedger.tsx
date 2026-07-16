import { AlertTriangle, Database, MapPin, Ticket } from "lucide-react";

import type { SearchV4Configuration } from "../types";
import {
  factorLabelForConfiguration,
  factorLabels,
  terrainPresentation,
} from "./searchPresentation";

export function DecisionEvidenceLedger({
  configuration,
}: {
  configuration: SearchV4Configuration;
}) {
  const factors = configuration.factors.filter(
    (factor) => factorLabels[factor.factor_id] && factor.provenance_summary,
  );
  const warnings = [
    ...configuration.constraint_warnings.map((warning) => warning.message),
    ...configuration.factors.flatMap((factor) => factor.warnings),
  ];
  const terrain = terrainPresentation(configuration.selected_pass);

  return (
    <section className="dossier-section evidence-ledger" id="decision-evidence">
      <p className="section-label">Decision evidence</p>
      <h2>Evidence ledger</h2>
      <div className="evidence-ledger__rows">
        {factors.map((factor) => (
          <article key={factor.factor_id}>
            <Database aria-hidden="true" size={19} />
            <div>
              <h3>{factorLabelForConfiguration(configuration, factor.factor_id)}</h3>
              <p>{factor.provenance_summary}</p>
            </div>
            <span>{factor.effective_evidence_cap === 0 ? "Limited evidence" : "Supported"}</span>
          </article>
        ))}
        <article>
          <MapPin aria-hidden="true" size={19} />
          <div>
            <h3>Stay base and lift access</h3>
            <p>
              {configuration.access.nearest_lift_name
                ? `Selected access is anchored to ${configuration.access.nearest_lift_name}.`
                : "Selected access uses the catalog stay-base relationship."}
            </p>
          </div>
          <span>{configuration.access.distance_m != null ? `${configuration.access.distance_m} m` : "Catalog context"}</span>
        </article>
        <article>
          <Ticket aria-hidden="true" size={19} />
          <div>
            <h3>Selected pass</h3>
            <p>{configuration.selected_pass.name} is the pass selected for this configuration.</p>
          </div>
          <span>
            {terrain?.evidenceLabel ?? "Coverage unresolved"}
          </span>
        </article>
        {configuration.lodging_estimate?.provenance ? (
          <article>
            <Database aria-hidden="true" size={19} />
            <div>
              <h3>Lodging estimate</h3>
              <p>{configuration.lodging_estimate.provenance}</p>
            </div>
            <span>Stay-base evidence</span>
          </article>
        ) : null}
      </div>
      {warnings.length ? (
        <div className="evidence-ledger__warnings">
          <AlertTriangle aria-hidden="true" size={18} />
          <div>
            <strong>Warnings and limitations</strong>
            <ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
          </div>
        </div>
      ) : null}
    </section>
  );
}
