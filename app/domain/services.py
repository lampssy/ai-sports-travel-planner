from app.ai.narrative import RecommendationNarrativeGenerator, get_narrative_generator
from app.domain.models import SearchDebugInfo, SearchFilters, SearchResult
from app.domain.search_models import (
    SearchModelSelection,
    resolve_search_model_selection,
)
from app.domain.search_service import search_resorts as search_resorts_impl


def search_resorts(
    filters: SearchFilters,
    *,
    narrative_generator: RecommendationNarrativeGenerator | None = None,
    search_model_selection: SearchModelSelection | None = None,
) -> list[SearchResult]:
    selection = search_model_selection or resolve_search_model_selection()
    results = search_resorts_impl(
        filters,
        search_model=selection.effective_search_model,
    )
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
    search_model_selection: SearchModelSelection | None = None,
) -> tuple[list[SearchResult], SearchDebugInfo]:
    selection = search_model_selection or resolve_search_model_selection()
    results = search_resorts_impl(
        filters,
        search_model=selection.effective_search_model,
    )
    if not results:
        return (
            results,
            _with_search_model_debug(
                SearchDebugInfo(
                    narrative_source="none",
                    narrative_cache_hit=False,
                    narrative_error=None,
                    narrative_model=None,
                    top_result_resort_id=None,
                ),
                selection,
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
    return results, _with_search_model_debug(debug, selection)


def _with_search_model_debug(
    debug: SearchDebugInfo,
    selection: SearchModelSelection,
) -> SearchDebugInfo:
    return debug.model_copy(
        update={
            "configured_search_model": selection.configured_search_model,
            "requested_search_model": selection.requested_search_model,
            "effective_search_model": selection.effective_search_model,
            "search_model_override_applied": selection.override_applied,
        }
    )
