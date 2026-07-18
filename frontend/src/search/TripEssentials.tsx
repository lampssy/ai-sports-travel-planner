import { Euro, Footprints, Hotel, Map, Route } from "lucide-react";

import type { SearchV4Configuration } from "../types";
import {
  formatTripEssential,
  type TripEssentialCategory,
} from "./searchPresentation";

const icons = {
  terrain: Map,
  passValue: Euro,
  liftAccess: Footprints,
  lodging: Hotel,
  travelEffort: Route,
} as const;

export function TripEssentials({
  configuration,
  categories,
}: {
  configuration: SearchV4Configuration;
  categories: TripEssentialCategory[];
}) {
  const essentials = categories.flatMap((category) => {
    const essential = formatTripEssential(category, configuration);
    return essential ? [essential] : [];
  });
  if (!essentials.length) return null;

  return (
    <section className="trip-essentials" aria-label="Trip essentials">
      <p className="section-label">Trip essentials</p>
      <dl className="trip-essentials__grid">
        {essentials.map((essential) => {
          const Icon = icons[essential.category];
          return (
            <div key={essential.category} className="trip-essential">
              <Icon aria-hidden="true" size={19} />
              <dt>{essential.label}</dt>
              <dd>{essential.value}</dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}
