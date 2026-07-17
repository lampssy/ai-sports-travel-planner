import { ExternalLink, Footprints, Hotel } from "lucide-react";

import { buildAccommodationBookingRedirectUrl } from "../api";
import type { SearchV4Configuration } from "../types";
import {
  formatAccommodationAccessContext,
  formatAccommodationEstimate,
  lodgingTrustLabel,
} from "./searchPresentation";

export function AccommodationHandoff({
  configuration,
}: {
  configuration: SearchV4Configuration;
}) {
  const estimate = configuration.lodging_estimate;
  const formattedEstimate = formatAccommodationEstimate(configuration);
  const url = buildAccommodationBookingRedirectUrl(
    {
      stay_destination_id: configuration.stay_destination_id,
      stay_base_id: configuration.stay_base_id,
      focus_ski_area_id: configuration.ski_area_id,
    },
    "recommendation_dossier",
  );
  const access = formatAccommodationAccessContext(configuration);

  return (
    <section className="dossier-section accommodation-handoff" id="accommodation">
      <p className="section-label">Stay-base estimate, not live hotel inventory</p>
      <h2>Find a stay in {configuration.stay_base_name}</h2>
      <p className="accommodation-handoff__intro">
        Continue with the selected stay-base context for this trip configuration.
      </p>
      <div className="accommodation-handoff__panel">
        <div>
          <Hotel aria-hidden="true" size={21} />
          <span className="accommodation-handoff__label">Stay estimate</span>
          {formattedEstimate ? (
            <strong>{formattedEstimate}</strong>
          ) : (
            <strong>No supported lodging estimate is available.</strong>
          )}
          <span className="accommodation-handoff__trust">
            {estimate ? lodgingTrustLabel(estimate.trust_status) : "Unavailable"}
          </span>
          {estimate?.provenance ? (
            <small>{estimate.provenance}</small>
          ) : null}
          {access ? (
            <p className="accommodation-handoff__access">
              <Footprints aria-hidden="true" size={17} />
              {access}
            </p>
          ) : null}
        </div>
        <div className="accommodation-handoff__action">
          <a className="primary-command" href={url}>
            Open accommodation search
            <ExternalLink aria-hidden="true" size={17} />
          </a>
          <small>Opens a search using this stay base, without claiming live inventory.</small>
        </div>
      </div>
    </section>
  );
}
