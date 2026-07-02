from __future__ import annotations

from dataclasses import dataclass

from app.domain.catalog import (
    LiftPassProduct,
    RentalDisplayFact,
    SkiArea,
    SkiAreaAccess,
    SkiRegion,
    StayBase,
    StayDestination,
)
from app.domain.catalog_graph import CatalogGraph
from app.domain.models import SearchFilters
from app.domain.ranking import (
    budget_range_penalty,
    quality_score,
    ski_area_access_lift_distance_matches,
    ski_area_skill_level_matches,
)


@dataclass(frozen=True)
class TripConfigurationSeed:
    region: SkiRegion
    stay_destination: StayDestination
    stay_base: StayBase
    ski_area: SkiArea
    access: SkiAreaAccess
    candidate_passes: tuple[LiftPassProduct, ...]
    rental_facts: tuple[RentalDisplayFact, ...]
    budget_penalty: float


def generate_candidate_seeds(
    graph: CatalogGraph,
    filters: SearchFilters,
) -> tuple[TripConfigurationSeed, ...]:
    requested_location = filters.location.strip().casefold()
    seeds: list[TripConfigurationSeed] = []
    for stay_base in graph.snapshot.stay_bases:
        destination = graph.destinations_by_id[stay_base.stay_destination_id]
        if destination.country.strip().casefold() != requested_location:
            continue
        if quality_score(stay_base.quality) < filters.stars:
            continue
        budget_penalty = budget_range_penalty(
            stay_base.price_min,
            stay_base.price_max,
            filters.min_price,
            filters.max_price,
            filters.budget_flex,
        )
        if budget_penalty is None:
            continue

        region = graph.regions_by_id[destination.trip_market_region_id]
        for access in graph.accesses_by_base_id.get(stay_base.stay_base_id, ()):
            ski_area = graph.areas_by_id[access.ski_area_id]
            if not ski_area_skill_level_matches(ski_area, filters.skill_level):
                continue
            if not ski_area_access_lift_distance_matches(access, filters.lift_distance):
                continue
            candidate_passes = graph.passes_by_destination_area.get(
                (destination.stay_destination_id, ski_area.ski_area_id),
                (),
            )
            if not candidate_passes:
                continue
            seeds.append(
                TripConfigurationSeed(
                    region=region,
                    stay_destination=destination,
                    stay_base=stay_base,
                    ski_area=ski_area,
                    access=access,
                    candidate_passes=candidate_passes,
                    rental_facts=graph.rentals_by_destination_id.get(
                        destination.stay_destination_id,
                        (),
                    ),
                    budget_penalty=budget_penalty,
                )
            )

    return tuple(sorted(seeds, key=_candidate_seed_sort_key))


def _candidate_seed_sort_key(seed: TripConfigurationSeed) -> tuple[str, ...]:
    return (
        seed.region.ski_region_id,
        seed.stay_destination.stay_destination_id,
        seed.stay_base.stay_base_id,
        seed.ski_area.ski_area_id,
    )
