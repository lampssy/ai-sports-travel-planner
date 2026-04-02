from app.domain.models import (
    Area,
    AvailabilityStatus,
    LiftDistance,
    Rental,
    SkillLevel,
)

QUALITY_SCORES = {
    "budget": 1,
    "standard": 2,
    "premium": 3,
}

LIFT_DISTANCE_SCORES = {
    "near": 3,
    "medium": 2,
    "far": 1,
}

SKILL_LEVEL_SCORES = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
}

AVAILABILITY_PENALTIES = {
    "open": 0.0,
    "limited": 0.12,
    "temporarily_closed": 0.38,
}


def midpoint(minimum: float, maximum: float) -> float:
    return (minimum + maximum) / 2


def quality_score(quality: str) -> int:
    return QUALITY_SCORES[quality]


def lift_distance_score(distance: LiftDistance) -> int:
    return LIFT_DISTANCE_SCORES[distance]


def lift_distance_matches(
    candidate: LiftDistance, requested: LiftDistance | None
) -> bool:
    if requested is None:
        return True
    return lift_distance_score(candidate) >= lift_distance_score(requested)


def skill_level_matches(area: Area, requested: SkillLevel) -> bool:
    return requested in area.supported_skill_levels


def skill_fit_score(area: Area, requested: SkillLevel) -> float:
    if requested not in area.supported_skill_levels:
        return 0.0
    return 1 / len(area.supported_skill_levels)


def package_price(area: Area, rental: Rental) -> float:
    return (
        midpoint(area.price_min, area.price_max)
        + midpoint(rental.price_min, rental.price_max)
    ) / 2


def budget_penalty(
    price: float,
    min_price: float,
    max_price: float,
    budget_flex: float | None,
) -> float | None:
    if min_price <= price <= max_price:
        return 0.0
    if budget_flex is None:
        return None

    tolerated_min = min_price * (1 - budget_flex)
    tolerated_max = max_price * (1 + budget_flex)
    if price < tolerated_min or price > tolerated_max:
        return None

    if price < min_price:
        return (min_price - price) / max(min_price, 1)
    return (price - max_price) / max(max_price, 1)


def availability_penalty(status: AvailabilityStatus) -> float | None:
    if status == "out_of_season":
        return None
    return AVAILABILITY_PENALTIES[status]
