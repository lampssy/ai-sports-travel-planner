from app.domain.catalog import SkiArea, SkiAreaAccess
from app.domain.models import AvailabilityStatus, LiftDistance, SkillLevel

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

AVAILABILITY_PENALTIES = {
    "open": 0.0,
    "limited": 0.12,
    "temporarily_closed": 0.38,
}


def quality_score(quality: str) -> int:
    return QUALITY_SCORES[quality]


def ski_area_skill_level_matches(
    ski_area: SkiArea,
    requested: SkillLevel,
) -> bool:
    return requested in ski_area.supported_skill_levels


def ski_area_access_lift_distance_matches(
    access: SkiAreaAccess,
    requested: LiftDistance | None,
) -> bool:
    if requested is None:
        return True
    return LIFT_DISTANCE_SCORES[access.lift_distance] >= LIFT_DISTANCE_SCORES[requested]


def budget_range_penalty(
    price_min: float,
    price_max: float,
    min_price: float,
    max_price: float,
    budget_flex: float | None,
) -> float | None:
    if price_min <= max_price and price_max >= min_price:
        return 0.0
    if budget_flex is None:
        return None

    tolerated_min = min_price * (1 - budget_flex)
    tolerated_max = max_price * (1 + budget_flex)
    if price_min > tolerated_max or price_max < tolerated_min:
        return None

    if price_max < min_price:
        return (min_price - price_max) / max(min_price, 1)
    return (price_min - max_price) / max(max_price, 1)


def availability_penalty(status: AvailabilityStatus) -> float | None:
    if status == "out_of_season":
        return None
    return AVAILABILITY_PENALTIES[status]
