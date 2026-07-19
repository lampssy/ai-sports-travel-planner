import type {
  SearchV4Configuration,
  SearchV4RecommendationGroup,
} from "../types";
import { TripEssentials } from "./TripEssentials";
import { formatAccess, formatPassPrice } from "./searchPresentation";

export function TripConfigurationDetails({
  group,
  configuration,
  onSelectCandidate,
}: {
  group: SearchV4RecommendationGroup;
  configuration: SearchV4Configuration;
  onSelectCandidate: (skiRegionId: string, candidateId: string) => void;
}) {
  const candidates = [group.top_configuration, ...group.alternative_configurations];

  return (
    <section className="dossier-section trip-configuration" id="trip-configuration">
      <p className="section-label">Trip details</p>
      <h2>{configuration.stay_base_name} and {configuration.selected_pass.name}</h2>
      <dl className="dossier-facts">
        <div><dt>Destination</dt><dd>{configuration.stay_destination_name}</dd></div>
        <div><dt>Ski area</dt><dd>{configuration.ski_area_name}</dd></div>
        <div><dt>Recommended place to stay</dt><dd>{configuration.stay_base_name}</dd></div>
        <div><dt>Selected pass</dt><dd>{configuration.selected_pass.name}</dd></div>
        <div><dt>Pass price</dt><dd>{formatPassPrice(configuration)}</dd></div>
        <div><dt>Access</dt><dd>{formatAccess(configuration)}</dd></div>
      </dl>

      <TripEssentials
        configuration={configuration}
        categories={["terrain", "passValue", "liftAccess", "lodging"]}
      />

      <div className="trip-configuration__alternatives" id="alternatives">
        <p className="section-label">Alternatives</p>
        <h3>Configurations in {group.ski_region_name}</h3>
        <div className="dossier-alternatives">
          {candidates.map((candidate) => {
            const selected = candidate.candidate_id === configuration.candidate_id;
            return (
              <button
                type="button"
                key={candidate.candidate_id}
                aria-label={`Select ${candidate.stay_base_name} with ${candidate.selected_pass.name}`}
                aria-pressed={selected}
                onClick={() => onSelectCandidate(group.ski_region_id, candidate.candidate_id)}
              >
                <span aria-hidden="true" className="dossier-alternatives__radio" />
                <span>
                  <strong>{candidate.stay_base_name}</strong>
                  <small>{candidate.selected_pass.name}</small>
                </span>
                <em>{selected ? "Current" : "Alternative"}</em>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
