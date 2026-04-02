from urllib.parse import quote_plus

from app.data.loader import load_resorts
from app.domain.models import (
    Area,
    Rental,
    ResortConditions,
    SearchFilters,
    SearchResult,
)
from app.domain.ranking import (
    budget_penalty,
    lift_distance_matches,
    lift_distance_score,
    package_price,
    quality_score,
    skill_fit_score,
    skill_level_matches,
)
from app.integrations.conditions import get_conditions_provider


def _build_result(
    resort_id: str,
    resort_name: str,
    country: str,
    region: str,
    area: Area,
    rental: Rental,
    filters: SearchFilters,
    conditions: ResortConditions | None,
) -> SearchResult | None:
    price = package_price(area, rental)
    penalty = budget_penalty(
        price=price,
        min_price=filters.min_price,
        max_price=filters.max_price,
        budget_flex=filters.budget_flex,
    )
    if penalty is None:
        return None

    quality = quality_score(area.quality)
    skill_bonus = skill_fit_score(area, filters.skill_level)
    lift_bonus = lift_distance_score(area.lift_distance) / 10
    price_component = (1 / price) * 0.3
    conditions_score = conditions.conditions_score if conditions else 0.4
    conditions_confidence = conditions.confidence if conditions else 0.5
    score = (
        quality * 0.55
        + price_component
        + skill_bonus
        + lift_bonus
        + conditions_score * 0.35
        - penalty
    )
    reasons = [
        f"Matched {filters.skill_level} skill level support in {area.name}.",
        f"Area quality meets the requested {filters.stars}-star threshold.",
        (
            "Current conditions are "
            f"{conditions.snow_quality if conditions else 'unknown'} "
            f"with {conditions_confidence:.0%} confidence."
        ),
    ]
    if penalty > 0:
        tradeoff_summary = (
            "Recommended despite being slightly outside budget due to stronger "
            "fit and conditions."
        )
    else:
        tradeoff_summary = (
            "Balanced fit across budget, skill level, and current mountain conditions."
        )

    return SearchResult(
        resort_id=resort_id,
        resort_name=resort_name,
        region=region,
        selected_area_name=area.name,
        selected_area_lift_distance=area.lift_distance,
        area_price_range=area.price_range,
        rental_name=rental.name,
        rental_price_range=rental.price_range,
        rating_estimate=quality,
        link=f"https://example.com/search?q={quote_plus(f'{resort_name} {country}')}",
        score=score,
        budget_penalty=penalty,
        conditions_summary=(
            conditions.weather_summary
            if conditions
            else "No live conditions signal available for this resort."
        ),
        conditions_score=conditions_score,
        recommendation_reasons=reasons,
        recommendation_confidence=min(
            (quality / 3) * 0.5 + conditions_confidence * 0.5,
            1.0,
        ),
        tradeoff_summary=tradeoff_summary,
    )


def search_resorts(filters: SearchFilters) -> list[SearchResult]:
    normalized_location = filters.location.strip().lower()
    results: list[SearchResult] = []
    conditions_provider = get_conditions_provider()

    for resort in load_resorts():
        if resort.country.lower() != normalized_location:
            continue

        resort_conditions = conditions_provider.get_conditions_for_resort(resort.name)
        matching_pairs: list[SearchResult] = []
        for area in resort.areas:
            if quality_score(area.quality) < filters.stars:
                continue
            if not skill_level_matches(area, filters.skill_level):
                continue
            if not lift_distance_matches(area.lift_distance, filters.lift_distance):
                continue

            for rental in resort.rentals:
                if filters.lift_distance and not lift_distance_matches(
                    rental.lift_distance, filters.lift_distance
                ):
                    continue

                result = _build_result(
                    resort_id=resort.resort_id,
                    resort_name=resort.name,
                    country=resort.country,
                    region=resort.region,
                    area=area,
                    rental=rental,
                    filters=filters,
                    conditions=resort_conditions,
                )
                if result is not None:
                    matching_pairs.append(result)

        if matching_pairs:
            results.append(
                sorted(
                    matching_pairs,
                    key=lambda result: (
                        -result.score,
                        result.resort_name,
                        result.selected_area_name,
                    ),
                )[0]
            )

    return sorted(
        results,
        key=lambda result: (
            -result.score,
            result.resort_name,
            result.selected_area_name,
        ),
    )[:3]
