import { Database, Layers3 } from "lucide-react";

import type {
  SearchWeatherEvidenceResponse,
  SearchV4Configuration,
  TravelWindow,
} from "../types";
import { Badge } from "../ui/Badge";
import {
  factorLabelForConfiguration,
  factorLabels,
  factorTrustLabelForConfiguration,
  groupLabels,
  technicalEvidenceDetails,
} from "./searchPresentation";
import { WeatherEvidenceTechnicalDetails } from "./WeatherEvidenceTechnicalDetails";

export function ScoringDetails({
  configuration,
  rankingPolicyVersion,
  travelWindow,
  weatherEvidence,
}: {
  configuration: SearchV4Configuration;
  rankingPolicyVersion?: string;
  travelWindow?: TravelWindow;
  weatherEvidence?: SearchWeatherEvidenceResponse | null;
}) {
  const groups = configuration.groups.filter((group) => groupLabels[group.group_id]);
  const factors = configuration.factors.filter(
    (factor) => factorLabels[factor.factor_id],
  );
  const technicalDetails = technicalEvidenceDetails(configuration, travelWindow);
  if (
    !rankingPolicyVersion &&
    !weatherEvidence &&
    !technicalDetails.length &&
    !groups.length &&
    !factors.length
  ) {
    return null;
  }
  return (
    <details className="scoring-details">
      <summary>
        <Layers3 aria-hidden="true" size={17} />
        Technical calculation details
      </summary>
      <div className="scoring-details__content">
        {weatherEvidence ? (
          <section className="scoring-details__weather">
            <h4>Weather calculations and values</h4>
            <WeatherEvidenceTechnicalDetails response={weatherEvidence} />
          </section>
        ) : null}
        {rankingPolicyVersion ? (
          <section className="scoring-details__policy">
            <h4>Ranking policy</h4>
            <code>{rankingPolicyVersion}</code>
          </section>
        ) : null}
        {technicalDetails.length ? (
          <section>
            <h4>Evidence and source context</h4>
            <div className="why-trip__technical-rows">
              {technicalDetails.map((item) => (
                <article key={item.id}>
                  <Database aria-hidden="true" size={18} />
                  <div>
                    <h4>{item.label}</h4>
                    <p>{item.provenance}</p>
                  </div>
                  <Badge
                    variant={
                      item.evidenceLabel === "Limited evidence" ? "warning" : "info"
                    }
                  >
                    {item.evidenceLabel}
                  </Badge>
                </article>
              ))}
            </div>
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
              {factors.map((factor) => {
                const trustLabel = factorTrustLabelForConfiguration(
                  configuration,
                  factor.factor_id,
                );
                return (
                  <div key={factor.factor_id}>
                    <dt>
                      <span>
                        {factorLabelForConfiguration(
                          configuration,
                          factor.factor_id,
                          travelWindow,
                        )}
                      </span>
                      {trustLabel ? (
                        <small className="scoring-details__trust">{trustLabel}</small>
                      ) : null}
                      <code>{factor.factor_id}</code>
                    </dt>
                    <dd>
                      Weight {factor.effective_weight.toFixed(2)}; {factor.contribution_points.toFixed(1)} points; evidence cap {factor.effective_evidence_cap.toFixed(2)}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </section>
        ) : null}
      </div>
    </details>
  );
}
