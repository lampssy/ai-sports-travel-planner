from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.domain.catalog import (
    CatalogSnapshot,
    LiftPassProduct,
    RentalDisplayFact,
    SkiArea,
    SkiAreaAccess,
    SkiRegion,
    StayBase,
    StayDestination,
    TerrainDomain,
)


@dataclass(frozen=True)
class CatalogGraph:
    snapshot: CatalogSnapshot
    regions_by_id: Mapping[str, SkiRegion]
    destinations_by_id: Mapping[str, StayDestination]
    bases_by_id: Mapping[str, StayBase]
    areas_by_id: Mapping[str, SkiArea]
    accesses_by_base_id: Mapping[str, tuple[SkiAreaAccess, ...]]
    domains_by_id: Mapping[str, TerrainDomain]
    passes_by_id: Mapping[str, LiftPassProduct]
    passes_by_destination_area: Mapping[tuple[str, str], tuple[LiftPassProduct, ...]]
    rentals_by_destination_id: Mapping[str, tuple[RentalDisplayFact, ...]]

    @classmethod
    def from_snapshot(cls, snapshot: CatalogSnapshot) -> "CatalogGraph":
        domains_by_id = {
            domain.terrain_domain_id: domain for domain in snapshot.terrain_domains
        }
        passes_by_destination_area: dict[tuple[str, str], list[LiftPassProduct]] = (
            defaultdict(list)
        )
        for product in snapshot.lift_pass_products:
            covered_ids = set(product.valid_ski_area_ids)
            for domain_id in product.terrain_domain_ids:
                covered_ids.update(domains_by_id[domain_id].ski_area_ids)
            for destination_id in product.available_from_stay_destination_ids:
                for area_id in covered_ids:
                    passes_by_destination_area[(destination_id, area_id)].append(
                        product
                    )

        return cls(
            snapshot=snapshot,
            regions_by_id=MappingProxyType(
                {region.ski_region_id: region for region in snapshot.ski_regions}
            ),
            destinations_by_id=MappingProxyType(
                {
                    destination.stay_destination_id: destination
                    for destination in snapshot.stay_destinations
                }
            ),
            bases_by_id=MappingProxyType(
                {base.stay_base_id: base for base in snapshot.stay_bases}
            ),
            areas_by_id=MappingProxyType(
                {area.ski_area_id: area for area in snapshot.ski_areas}
            ),
            accesses_by_base_id=_group_accesses(snapshot.ski_area_access),
            domains_by_id=MappingProxyType(domains_by_id),
            passes_by_id=MappingProxyType(
                {
                    product.lift_pass_product_id: product
                    for product in snapshot.lift_pass_products
                }
            ),
            passes_by_destination_area=MappingProxyType(
                {
                    key: tuple(
                        sorted(
                            products,
                            key=lambda item: item.lift_pass_product_id,
                        )
                    )
                    for key, products in passes_by_destination_area.items()
                }
            ),
            rentals_by_destination_id=_group_rentals(snapshot.rental_display_facts),
        )


def _group_accesses(
    accesses: tuple[SkiAreaAccess, ...],
) -> Mapping[str, tuple[SkiAreaAccess, ...]]:
    grouped: dict[str, list[SkiAreaAccess]] = defaultdict(list)
    for access in accesses:
        grouped[access.stay_base_id].append(access)
    return MappingProxyType(
        {
            base_id: tuple(sorted(values, key=lambda access: access.ski_area_access_id))
            for base_id, values in grouped.items()
        }
    )


def _group_rentals(
    rentals: tuple[RentalDisplayFact, ...],
) -> Mapping[str, tuple[RentalDisplayFact, ...]]:
    grouped: dict[str, list[RentalDisplayFact]] = defaultdict(list)
    for rental in rentals:
        grouped[rental.stay_destination_id].append(rental)
    return MappingProxyType(
        {
            destination_id: tuple(
                sorted(
                    values,
                    key=lambda rental: rental.rental_display_fact_id,
                )
            )
            for destination_id, values in grouped.items()
        }
    )
