import { CheckCircle2, TriangleAlert } from "lucide-react";

import type { SearchV4Configuration, TravelWindow } from "../types";
import { Alert } from "../ui/Alert";
import { SectionHeader } from "../ui/SectionHeader";
import {
  decisionEvidencePresentation,
  type DecisionEvidenceId,
} from "./searchPresentation";

export function DecisionEvidenceLedger({
  configuration,
  travelWindow,
  primaryDetails = [],
  primaryEvidenceIds = [],
}: {
  configuration: SearchV4Configuration;
  travelWindow?: TravelWindow;
  primaryDetails?: Array<string | undefined>;
  primaryEvidenceIds?: readonly DecisionEvidenceId[];
}) {
  const presentation = decisionEvidencePresentation(configuration, travelWindow);
  const primaryDetailSet = new Set(primaryDetails.filter(Boolean));
  const primaryEvidenceIdSet = new Set(primaryEvidenceIds);
  const supports = presentation.supports.filter(
    (item) => !primaryDetailSet.has(item.detail),
  );
  const uncertainties = presentation.uncertainties.filter(
    (item) =>
      !primaryEvidenceIdSet.has(item.id) && !primaryDetailSet.has(item.detail),
  );

  return (
    <section className="dossier-section why-trip" id="decision-evidence">
      <SectionHeader
        eyebrow="Decision evidence"
        title="Why this trip"
        description="Why Snowcast recommends this trip, including important limits."
      />

      {supports.length ? (
        <div className="why-trip__supports">
          <h3>What supports this choice</h3>
          <div className="why-trip__findings">
            {supports.map((item) => (
              <article key={item.id}>
                <CheckCircle2 aria-hidden="true" size={19} />
                <div>
                  <h4>{item.title}</h4>
                  <p>{item.detail}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {uncertainties.length ? (
        <Alert variant="warning" className="why-trip__uncertainties">
          <TriangleAlert aria-hidden="true" size={19} />
          <div>
            <h3>What remains uncertain</h3>
            <ul>
              {uncertainties.map((item) => (
                <li key={item.id}>{item.detail}</li>
              ))}
            </ul>
          </div>
        </Alert>
      ) : null}
    </section>
  );
}
