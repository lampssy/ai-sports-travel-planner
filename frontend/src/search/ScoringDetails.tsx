import { Layers3 } from "lucide-react";

import type { SearchV4Configuration } from "../types";
import { factorLabels, groupLabels } from "./searchPresentation";

export function ScoringDetails({
  configuration,
}: {
  configuration: SearchV4Configuration;
}) {
  const groups = configuration.groups.filter((group) => groupLabels[group.group_id]);
  const factors = configuration.factors.filter(
    (factor) => factorLabels[factor.factor_id],
  );
  if (!groups.length && !factors.length) return null;
  return (
    <details className="scoring-details">
      <summary>
        <Layers3 aria-hidden="true" size={17} />
        Show scoring details
      </summary>
      <div className="scoring-details__content">
        {groups.length ? (
          <section>
            <h4>Decision groups</h4>
            <dl className="scoring-details__groups">
              {groups.map((group) => (
                <div key={group.group_id}>
                  <dt>{groupLabels[group.group_id]}</dt>
                  <dd>{group.contribution_points.toFixed(1)} points</dd>
                </div>
              ))}
            </dl>
          </section>
        ) : null}
        {factors.length ? (
          <section>
            <h4>Factor evidence</h4>
            <dl className="scoring-details__factors">
              {factors.map((factor) => (
                <div key={factor.factor_id}>
                  <dt>{factorLabels[factor.factor_id]}</dt>
                  <dd>
                    {factor.effective_evidence_cap === 0
                      ? "Limited evidence"
                      : `${factor.contribution_points.toFixed(1)} points`}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        ) : null}
      </div>
    </details>
  );
}
