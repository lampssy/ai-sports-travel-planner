from urllib.parse import quote_plus

from app.data.loader import load_resorts
from app.domain.models import Area, Rental, SearchFilters, SearchResult
from app.domain.ranking import (
    budget_penalty,
    lift_distance_matches,
    lift_distance_score,
    package_price,
    quality_score,
    skill_fit_score,
    skill_level_matches,
)


def _build_result(
    resort_name: str,
    country: str,
    area: Area,
    rental: Rental,
    filters: SearchFilters,
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
    score = quality * 0.7 + price_component + skill_bonus + lift_bonus - penalty

    return SearchResult(
        resort_name=resort_name,
        selected_area_name=area.name,
        selected_area_lift_distance=area.lift_distance,
        area_price_range=area.price_range,
        rental_name=rental.name,
        rental_price_range=rental.price_range,
        rating_estimate=quality,
        link=f"https://example.com/search?q={quote_plus(f'{resort_name} {country}')}",
        score=score,
        budget_penalty=penalty,
    )


def search_resorts(filters: SearchFilters) -> list[SearchResult]:
    normalized_location = filters.location.strip().lower()
    results: list[SearchResult] = []

    for resort in load_resorts():
        if resort.country.lower() != normalized_location:
            continue

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
                    resort_name=resort.name,
                    country=resort.country,
                    area=area,
                    rental=rental,
                    filters=filters,
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
