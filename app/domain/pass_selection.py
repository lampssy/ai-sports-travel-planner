from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.catalog import CatalogLiftPassPrice, LiftPassProduct
from app.domain.catalog_graph import CatalogGraph
from app.domain.search_v3_models import PassOption, PassPriceExample


@dataclass(frozen=True)
class PassSelection:
    selected: PassOption
    alternatives: tuple[PassOption, ...]


@dataclass(frozen=True)
class _PassFacts:
    product: LiftPassProduct
    area_ids: tuple[str, ...]
    terrain_label: str
    piste_km: float | None
    price: CatalogLiftPassPrice | None
    price_value: float | None


def select_pass(
    *,
    products: tuple[LiftPassProduct, ...],
    graph: CatalogGraph,
    stay_destination_id: str,
    focus_ski_area_id: str,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> PassSelection:
    if not products:
        raise ValueError("pass selection requires at least one product")
    duration_days = _trip_duration_days(trip_start_date, trip_end_date)
    facts = tuple(
        _build_pass_facts(
            product=product,
            graph=graph,
            duration_days=duration_days,
        )
        for product in products
    )
    coverage_scores = _normalized_coverage_scores(facts)
    price_scores = _normalized_price_scores(facts) if duration_days else {}
    options = {
        item.product.lift_pass_product_id: _build_pass_option(
            facts=item,
            coverage_score=coverage_scores[item.product.lift_pass_product_id],
            price_score=price_scores.get(item.product.lift_pass_product_id),
            duration_days=duration_days,
        )
        for item in facts
    }

    if duration_days is None:
        ordered_products = sorted(
            products,
            key=lambda product: (
                stay_destination_id not in product.default_for_stay_destination_ids,
                -options[product.lift_pass_product_id].pass_fit_score,
                product.lift_pass_product_id,
            ),
        )
    else:
        ordered_products = sorted(
            products,
            key=lambda product: (
                -options[product.lift_pass_product_id].pass_fit_score,
                stay_destination_id not in product.default_for_stay_destination_ids,
                product.lift_pass_product_id,
            ),
        )
    ordered = tuple(options[item.lift_pass_product_id] for item in ordered_products)
    return PassSelection(selected=ordered[0], alternatives=ordered[1:4])


def _trip_duration_days(start: date | None, end: date | None) -> int | None:
    if start is None and end is None:
        return None
    if start is None or end is None:
        raise ValueError("trip start and end dates must be provided together")
    duration_days = (end - start).days + 1
    if duration_days < 1:
        raise ValueError("trip end date must not precede start date")
    return duration_days


def _build_pass_facts(
    *,
    product: LiftPassProduct,
    graph: CatalogGraph,
    duration_days: int | None,
) -> _PassFacts:
    area_ids = _covered_area_ids(product, graph)
    price = (
        _exact_adult_price(product, duration_days)
        if duration_days is not None
        else _representative_adult_price(product)
    )
    return _PassFacts(
        product=product,
        area_ids=area_ids,
        terrain_label=_terrain_label(product, area_ids, graph),
        piste_km=_accessible_piste_km(product, area_ids, graph),
        price=price,
        price_value=_price_value(price),
    )


def _covered_area_ids(
    product: LiftPassProduct,
    graph: CatalogGraph,
) -> tuple[str, ...]:
    area_ids = set(product.valid_ski_area_ids)
    for domain_id in product.terrain_domain_ids:
        area_ids.update(graph.domains_by_id[domain_id].ski_area_ids)
    return tuple(sorted(area_ids))


def _accessible_piste_km(
    product: LiftPassProduct,
    area_ids: tuple[str, ...],
    graph: CatalogGraph,
) -> float | None:
    aggregate = product.pass_accessible_terrain
    if aggregate is not None and aggregate.total_piste_km is not None:
        return aggregate.total_piste_km
    if len(product.terrain_domain_ids) == 1:
        domain = graph.domains_by_id[product.terrain_domain_ids[0]]
        if set(product.valid_ski_area_ids).issubset(domain.ski_area_ids):
            if domain.total_piste_km is not None:
                return domain.total_piste_km
    area_values = [graph.areas_by_id[area_id].total_piste_km for area_id in area_ids]
    if not area_values or any(value is None for value in area_values):
        return None
    return sum(value for value in area_values if value is not None)


def _terrain_label(
    product: LiftPassProduct,
    area_ids: tuple[str, ...],
    graph: CatalogGraph,
) -> str:
    if product.pass_accessible_terrain is not None:
        return product.name
    if len(product.terrain_domain_ids) == 1 and not product.valid_ski_area_ids:
        return graph.domains_by_id[product.terrain_domain_ids[0]].name
    return ", ".join(graph.areas_by_id[area_id].name for area_id in area_ids)


def _exact_adult_price(
    product: LiftPassProduct,
    duration_days: int,
) -> CatalogLiftPassPrice | None:
    matches = [
        price
        for price in product.prices
        if price.audience.casefold() == "adult" and price.duration_days == duration_days
    ]
    return min(matches, key=_price_sort_key, default=None)


def _representative_adult_price(
    product: LiftPassProduct,
) -> CatalogLiftPassPrice | None:
    matches = [
        price for price in product.prices if price.audience.casefold() == "adult"
    ]
    return min(
        matches,
        key=lambda price: (price.duration_days, _price_sort_key(price)),
        default=None,
    )


def _price_sort_key(price: CatalogLiftPassPrice) -> tuple[float, str]:
    value = _price_value(price)
    return (float("inf") if value is None else value, price.currency)


def _price_value(price: CatalogLiftPassPrice | None) -> float | None:
    if price is None:
        return None
    if price.amount is not None:
        return price.amount
    if price.amount_min is not None and price.amount_max is not None:
        return (price.amount_min + price.amount_max) / 2
    return None


def _normalized_coverage_scores(facts: tuple[_PassFacts, ...]) -> dict[str, float]:
    known_values = [item.piste_km for item in facts if item.piste_km is not None]
    maximum = max(known_values, default=0)
    return {
        item.product.lift_pass_product_id: (
            0 if item.piste_km is None or maximum == 0 else item.piste_km / maximum
        )
        for item in facts
    }


def _normalized_price_scores(facts: tuple[_PassFacts, ...]) -> dict[str, float]:
    currencies = {
        item.price.currency
        for item in facts
        if item.price is not None and item.price_value is not None
    }
    if len(currencies) != 1:
        return {}
    values = [item.price_value for item in facts if item.price_value is not None]
    if not values:
        return {}
    minimum = min(values)
    maximum = max(values)
    return {
        item.product.lift_pass_product_id: (
            0
            if item.price_value is None
            else 1
            if minimum == maximum
            else (maximum - item.price_value) / (maximum - minimum)
        )
        for item in facts
    }


def _build_pass_option(
    *,
    facts: _PassFacts,
    coverage_score: float,
    price_score: float | None,
    duration_days: int | None,
) -> PassOption:
    fit_score = (
        coverage_score
        if duration_days is None
        else 0.6 * coverage_score + 0.4 * (price_score or 0)
    )
    return PassOption(
        lift_pass_product_id=facts.product.lift_pass_product_id,
        name=facts.product.name,
        validity_scope=facts.product.validity_scope,
        accessible_ski_area_ids=list(facts.area_ids),
        accessible_terrain_label=facts.terrain_label,
        accessible_piste_km=facts.piste_km,
        price_example=_price_example(facts.price, duration_days),
        pass_fit_score=fit_score,
        tradeoff_summary=_tradeoff_summary(facts),
    )


def _price_example(
    price: CatalogLiftPassPrice | None,
    duration_days: int | None,
) -> PassPriceExample | None:
    if price is None:
        return None
    return PassPriceExample(
        duration_days=price.duration_days,
        audience=price.audience,
        amount=price.amount,
        amount_min=price.amount_min,
        amount_max=price.amount_max,
        currency=price.currency,
        match_kind="exact_duration" if duration_days is not None else "representative",
    )


def _tradeoff_summary(facts: _PassFacts) -> str:
    if len(facts.area_ids) == 1:
        return "Focused pass for the selected ski area."
    return f"Access to {len(facts.area_ids)} modeled ski areas."
