import { CheckCircle2, TriangleAlert } from "lucide-react";

import type { SearchV4Configuration, TravelWindow } from "../types";
import { Alert } from "../ui/Alert";
import { SectionHeader } from "../ui/SectionHeader";
import { decisionEvidencePresentation } from "./searchPresentation";

export function DecisionEvidenceLedger({
  configuration,
  travelWindow,
}: {
  configuration: SearchV4Configuration;
  travelWindow?: TravelWindow;
}) {
  const presentation = decisionEvidencePresentation(configuration, travelWindow);

  return (
    <section className="dossier-section why-trip" id="decision-evidence">
      <SectionHeader
        eyebrow="Decision evidence"
        title="Why this trip"
        description="Why Snowcast recommends this trip, including important limits."
      />

      {presentation.supports.length ? (
        <div className="why-trip__supports">
          <h3>What supports this choice</h3>
          <div className="why-trip__findings">
            {presentation.supports.map((item) => (
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

      {presentation.uncertainties.length ? (
        <Alert variant="warning" className="why-trip__uncertainties">
          <TriangleAlert aria-hidden="true" size={19} />
          <div>
            <h3>What remains uncertain</h3>
            <ul>
              {presentation.uncertainties.map((item) => (
                <li key={item.id}>{item.detail}</li>
              ))}
            </ul>
          </div>
        </Alert>
      ) : null}
    </section>
  );
}
