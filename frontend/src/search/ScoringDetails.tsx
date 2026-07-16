import { Layers3 } from "lucide-react";

import type { SearchV4Configuration } from "../types";
import {
  factorLabelForConfiguration,
  factorLabels,
  groupLabels,
} from "./searchPresentation";

export function ScoringDetails({
  configuration,
  rankingPolicyVersion,
}: {
  configuration: SearchV4Configuration;
  rankingPolicyVersion?: string;
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
        {rankingPolicyVersion ? (
          <section className="scoring-details__policy">
            <h4>Ranking policy</h4>
            <code>{rankingPolicyVersion}</code>
          </section>
        ) : null}
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
            <h4>Raw factor contributions</h4>
            <dl className="scoring-details__factors">
              {factors.map((factor) => (
                <div key={factor.factor_id}>
                  <dt>
                    <span>
                      {factorLabelForConfiguration(configuration, factor.factor_id)}
                    </span>
                    <code>{factor.factor_id}</code>
                  </dt>
                  <dd>
                    Weight {factor.effective_weight.toFixed(2)}; {factor.contribution_points.toFixed(1)} points; evidence cap {factor.effective_evidence_cap.toFixed(2)}
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
