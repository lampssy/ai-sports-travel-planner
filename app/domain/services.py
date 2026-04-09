from app.ai.narrative import RecommendationNarrativeGenerator, get_narrative_generator
from app.domain.models import Activity, SearchDebugInfo, SearchFilters, SearchResult
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


def search_resorts(
    filters: SearchFilters,
    *,
    narrative_generator: RecommendationNarrativeGenerator | None = None,
) -> list[SearchResult]:
    results = search_resorts_impl(filters)
    if not results:
        return results

    generator = narrative_generator or get_narrative_generator()
    try:
        narrative = generator.generate(results[0])
    except Exception:
        narrative = None
    results[0] = results[0].model_copy(update={"recommendation_narrative": narrative})
    return results


def search_resorts_with_debug(
    filters: SearchFilters,
    *,
    narrative_generator: RecommendationNarrativeGenerator | None = None,
) -> tuple[list[SearchResult], SearchDebugInfo]:
    results = search_resorts_impl(filters)
    if not results:
        return (
            results,
            SearchDebugInfo(
                narrative_source="none",
                narrative_cache_hit=False,
                narrative_error=None,
                narrative_model=None,
                top_result_resort_id=None,
            ),
        )

    generator = narrative_generator or get_narrative_generator()
    try:
        narrative, debug = generator.generate_with_debug(results[0])
    except Exception:
        narrative = None
        debug = SearchDebugInfo(
            narrative_source="none",
            narrative_cache_hit=False,
            narrative_error="provider_error",
            narrative_model=None,
            top_result_resort_id=results[0].resort_id,
        )
    if not isinstance(debug, SearchDebugInfo):
        debug = SearchDebugInfo.model_validate(debug)

    results[0] = results[0].model_copy(update={"recommendation_narrative": narrative})
    return results, debug
