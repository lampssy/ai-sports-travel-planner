from app.domain.models import Activity, SearchFilters, SearchResult
from app.domain.search_service import search_resorts as search_resorts_impl

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


def recommend_activities(sport: str, region: str, difficulty: str) -> list[Activity]:
    return [
        activity
        for activity in ACTIVITIES
        if activity.sport == sport
        and activity.region == region
        and activity.difficulty == difficulty
    ]


def search_resorts(filters: SearchFilters) -> list[SearchResult]:
    return search_resorts_impl(filters)
