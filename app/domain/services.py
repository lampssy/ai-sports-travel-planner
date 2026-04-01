from urllib.parse import quote_plus

from app.domain.models import (
    Activity,
    Area,
    Rental,
    Resort,
    SearchResult,
)


ACTIVITIES: tuple[Activity, ...] = (
    Activity(
        name="Alpine Start",
        destination="Innsbruck",
        region="Alps",
        sport="ski",
        type="resort",
        difficulty="beginner",
        description="Gentle alpine resort with beginner-friendly slopes.",
        price_per_day=79.0,
        currency="EUR",
    ),
    Activity(
        name="Summit Charge",
        destination="Chamonix",
        region="Alps",
        sport="ski",
        type="resort",
        difficulty="advanced",
        description="Steep alpine terrain for confident advanced skiers.",
        price_per_day=112.0,
        currency="EUR",
    ),
    Activity(
        name="Atlantic Glide",
        destination="Tarifa",
        region="Atlantic",
        sport="windsurf",
        type="spot",
        difficulty="intermediate",
        description="Reliable wind conditions for progressing windsurfers.",
        price_per_day=64.0,
        currency="EUR",
    ),
    Activity(
        name="Baltic Breeze",
        destination="Hel",
        region="Baltic",
        sport="windsurf",
        type="spot",
        difficulty="intermediate",
        description="Flat-water spot popular with intermediate riders.",
        price_per_day=48.0,
        currency="EUR",
    ),
)

RESORTS: tuple[Resort, ...] = (
    Resort(
        name="Tyrol Summit",
        country="Austria",
        price_level="medium",
        areas=[
            Area(
                name="Nord Village",
                price_range="EUR 150-210",
                quality="standard",
                distance_to_lift="5 min walk",
            ),
            Area(
                name="Peak Lodge",
                price_range="EUR 230-310",
                quality="premium",
                distance_to_lift="ski-in/ski-out",
            ),
        ],
        rentals=[
            Rental(
                name="Tyrol Ski Hire",
                price_range="EUR 40-60",
                quality="standard",
                distance_to_lift="2 min walk",
            ),
            Rental(
                name="Summit Elite Rental",
                price_range="EUR 70-90",
                quality="premium",
                distance_to_lift="at lift base",
            ),
        ],
    ),
    Resort(
        name="Kitz Alpine",
        country="Austria",
        price_level="high",
        areas=[
            Area(
                name="Old Town Stay",
                price_range="EUR 360-440",
                quality="premium",
                distance_to_lift="8 min shuttle",
            ),
            Area(
                name="Valley Rooms",
                price_range="EUR 190-240",
                quality="standard",
                distance_to_lift="12 min walk",
            ),
        ],
        rentals=[
            Rental(
                name="Kitz Gear House",
                price_range="EUR 65-85",
                quality="premium",
                distance_to_lift="3 min walk",
            ),
            Rental(
                name="Valley Rental Hub",
                price_range="EUR 45-65",
                quality="standard",
                distance_to_lift="6 min walk",
            ),
        ],
    ),
    Resort(
        name="Matterhorn Peak",
        country="Switzerland",
        price_level="high",
        areas=[
            Area(
                name="Glacier Terrace",
                price_range="EUR 250-330",
                quality="premium",
                distance_to_lift="ski-in/ski-out",
            ),
            Area(
                name="Village Center",
                price_range="EUR 190-240",
                quality="standard",
                distance_to_lift="7 min walk",
            ),
        ],
        rentals=[
            Rental(
                name="Matterhorn Pro Rental",
                price_range="EUR 60-80",
                quality="premium",
                distance_to_lift="next to gondola",
            ),
            Rental(
                name="Village Ski Rent",
                price_range="EUR 35-55",
                quality="standard",
                distance_to_lift="5 min walk",
            ),
        ],
    ),
    Resort(
        name="Alpine Horizon",
        country="France",
        price_level="medium",
        areas=[
            Area(
                name="Snowline Quarter",
                price_range="EUR 180-240",
                quality="premium",
                distance_to_lift="4 min walk",
            ),
            Area(
                name="Pine Chalet Zone",
                price_range="EUR 150-190",
                quality="standard",
                distance_to_lift="8 min walk",
            ),
        ],
        rentals=[
            Rental(
                name="Horizon Rentals",
                price_range="EUR 120-160",
                quality="premium",
                distance_to_lift="1 min walk",
            ),
            Rental(
                name="Budget Ski Stop",
                price_range="EUR 30-45",
                quality="budget",
                distance_to_lift="6 min walk",
            ),
        ],
    ),
    Resort(
        name="Mont Blanc Escape",
        country="France",
        price_level="high",
        areas=[
            Area(
                name="Summit View",
                price_range="EUR 210-270",
                quality="premium",
                distance_to_lift="ski-in/ski-out",
            ),
            Area(
                name="River Lane",
                price_range="EUR 160-210",
                quality="standard",
                distance_to_lift="10 min shuttle",
            ),
        ],
        rentals=[
            Rental(
                name="Escape Ski Lab",
                price_range="EUR 50-70",
                quality="standard",
                distance_to_lift="3 min walk",
            ),
            Rental(
                name="Blanc Premium Gear",
                price_range="EUR 110-140",
                quality="premium",
                distance_to_lift="at lift base",
            ),
        ],
    ),
    Resort(
        name="Savoy Snowfield",
        country="France",
        price_level="medium",
        areas=[
            Area(
                name="Savoy Base",
                price_range="EUR 170-230",
                quality="standard",
                distance_to_lift="5 min walk",
            ),
            Area(
                name="Forest Ridge",
                price_range="EUR 140-180",
                quality="budget",
                distance_to_lift="12 min shuttle",
            ),
        ],
        rentals=[
            Rental(
                name="Savoy Ride Rent",
                price_range="EUR 130-170",
                quality="premium",
                distance_to_lift="4 min walk",
            ),
            Rental(
                name="Basecamp Rental",
                price_range="EUR 35-50",
                quality="budget",
                distance_to_lift="7 min walk",
            ),
        ],
    ),
    Resort(
        name="Pyrenees Drift",
        country="France",
        price_level="low",
        areas=[
            Area(
                name="Drift Village",
                price_range="EUR 120-160",
                quality="budget",
                distance_to_lift="9 min walk",
            ),
            Area(
                name="Ridge Apartments",
                price_range="EUR 150-200",
                quality="standard",
                distance_to_lift="6 min shuttle",
            ),
        ],
        rentals=[
            Rental(
                name="Drift Boards & Skis",
                price_range="EUR 25-40",
                quality="budget",
                distance_to_lift="5 min walk",
            ),
            Rental(
                name="Ridge Rental Point",
                price_range="EUR 40-55",
                quality="standard",
                distance_to_lift="3 min walk",
            ),
        ],
    ),
)

QUALITY_SCORES = {
    "budget": 1,
    "standard": 2,
    "premium": 3,
}


def recommend_activities(sport: str, region: str, difficulty: str) -> list[Activity]:
    return [
        activity
        for activity in ACTIVITIES
        if activity.sport == sport
        and activity.region == region
        and activity.difficulty == difficulty
    ]


def _parse_price_range(price_range: str) -> tuple[float, float]:
    normalized = price_range.replace("EUR", "").replace("€", "").strip()
    lower_bound, upper_bound = normalized.split("-", maxsplit=1)
    return float(lower_bound.strip()), float(upper_bound.strip())


def _midpoint(price_range: str) -> float:
    minimum, maximum = _parse_price_range(price_range)
    return (minimum + maximum) / 2


def _quality_score(quality: str) -> int:
    return QUALITY_SCORES[quality]


def _select_area(resort: Resort, minimum_rating: int) -> Area | None:
    matching_areas = [
        area for area in resort.areas if _quality_score(area.quality) >= minimum_rating
    ]
    if not matching_areas:
        return None
    return max(
        matching_areas,
        key=lambda area: (_quality_score(area.quality), -_midpoint(area.price_range)),
    )


def _select_rental(resort: Resort) -> Rental:
    return max(
        resort.rentals,
        key=lambda rental: (
            _quality_score(rental.quality),
            -_midpoint(rental.price_range),
        ),
    )


def _build_search_result(
    resort: Resort,
    area: Area,
    rental: Rental,
) -> SearchResult:
    area_midpoint = _midpoint(area.price_range)
    rental_midpoint = _midpoint(rental.price_range)
    package_price = (area_midpoint + rental_midpoint) / 2
    rating = _quality_score(area.quality)
    score = rating * 0.7 + (1 / package_price) * 0.3

    return SearchResult(
        resort_name=resort.name,
        selected_area_name=area.name,
        area_price_range=area.price_range,
        rental_name=rental.name,
        rental_price_range=rental.price_range,
        rating_estimate=rating,
        link=(
            "https://example.com/search?q="
            f"{quote_plus(f'{resort.name} {resort.country}')}"
        ),
        score=score,
    )


def search_resorts(
    location: str,
    min_price: float,
    max_price: float,
    stars: int,
) -> list[SearchResult]:
    normalized_location = location.strip().lower()
    minimum_rating = stars
    results: list[SearchResult] = []

    for resort in RESORTS:
        if resort.country.lower() != normalized_location:
            continue

        area = _select_area(resort, minimum_rating)
        if area is None:
            continue

        rental = _select_rental(resort)
        result = _build_search_result(resort, area, rental)
        package_price = (
            _midpoint(result.area_price_range) + _midpoint(result.rental_price_range)
        ) / 2
        if package_price < min_price or package_price > max_price:
            continue

        results.append(result)

    return sorted(results, key=lambda result: result.score, reverse=True)[:3]
