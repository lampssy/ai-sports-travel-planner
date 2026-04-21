from app.ai.narrative import RecommendationNarrativeGenerator, get_narrative_generator
from app.domain.models import SearchDebugInfo, SearchFilters, SearchResult
from app.domain.search_service import search_resorts as search_resorts_impl


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
