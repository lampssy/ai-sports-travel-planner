import pytest

from app.ai.narrative import LLMRecommendationNarrativeGenerator
from app.data.repositories import LLMCacheRepository, ResortRepository
from app.domain.models import (
    ConfidenceContributor,
    ExplanationItem,
    ProvenanceInfo,
    SearchExplanation,
    SearchResult,
)


class StubLLMClient:
    def __init__(self, response: str | None = None, *, error=None) -> None:
        self.response = response
        self.model = "stub-model"
        self.calls = 0
        self.error = error
        self.last_response_mime_type = None
        self.last_response_json_schema = None

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        response_mime_type: str | None = None,
        response_json_schema: dict | None = None,
    ) -> str:
        self.calls += 1
        self.last_response_mime_type = response_mime_type
        self.last_response_json_schema = response_json_schema
        if self.error is not None:
            raise self.error
        return self.response


def build_result() -> SearchResult:
    resort = next(
        item for item in ResortRepository().list_resorts() if item.name == "Tignes"
    )
    return SearchResult(
        resort_id=resort.resort_id,
        resort_name=resort.name,
        region=resort.region,
        selected_area_name=resort.areas[0].name,
        selected_area_lift_distance=resort.areas[0].lift_distance,
        area_price_range=resort.areas[0].price_range,
        rental_name=resort.rentals[0].name,
        rental_price_range=resort.rentals[0].price_range,
        rating_estimate=3,
        link="https://example.com/search?q=Tignes+France",
        score=2.5,
        budget_penalty=0,
        conditions_summary="Fair snow outlook with stable weather.",
        snow_confidence_score=0.48,
        snow_confidence_label="fair",
        availability_status="open",
        conditions_score=0.53,
        conditions_provenance=ProvenanceInfo(
            source_name="open-meteo",
            source_type="forecast",
            updated_at="2026-04-12T09:00:00+00:00",
            freshness_status="fresh",
            basis_summary=(
                "Using a current forecast-based conditions signal from the latest "
                "weather refresh."
            ),
        ),
        explanation=SearchExplanation(
            highlights=[ExplanationItem(label="Le Lac supports intermediate skiers.")],
            risks=[],
            confidence_contributors=[
                ConfidenceContributor(
                    label="Skill match is strong for the requested intermediate level.",
                    direction="positive",
                )
            ],
        ),
        recommendation_confidence=0.81,
    )


def test_narrative_generator_returns_cached_result_for_same_signature(tmp_path) -> None:
    cache_repository = LLMCacheRepository(tmp_path / "planner.db")
    client = StubLLMClient(
        (
            '{"recommendation_narrative": '
            '"Tignes is a balanced pick with reliable fit and solid conditions."}'
        )
    )
    generator = LLMRecommendationNarrativeGenerator(
        client=client,
        cache_repository=cache_repository,
    )

    first = generator.generate(build_result())
    second = generator.generate(build_result())

    assert first == second
    assert client.calls == 1
    assert client.last_response_mime_type == "application/json"
    assert client.last_response_json_schema is not None


def test_narrative_generator_bypasses_old_cache_when_prompt_version_changes(
    tmp_path,
) -> None:
    cache_repository = LLMCacheRepository(tmp_path / "planner.db")
    client = StubLLMClient(
        (
            '{"recommendation_narrative": '
            '"Tignes remains a strong overall recommendation."}'
        )
    )
    generator_v1 = LLMRecommendationNarrativeGenerator(
        client=client,
        cache_repository=cache_repository,
        prompt_version="v1",
    )
    generator_v2 = LLMRecommendationNarrativeGenerator(
        client=client,
        cache_repository=cache_repository,
        prompt_version="v2",
    )

    generator_v1.generate(build_result())
    generator_v2.generate(build_result())

    assert client.calls == 2


def test_narrative_generator_returns_none_on_invalid_response(tmp_path) -> None:
    generator = LLMRecommendationNarrativeGenerator(
        client=StubLLMClient("not-json"),
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    assert generator.generate(build_result()) is None


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("quota_error", "quota_error"),
        ("auth_error", "auth_error"),
        ("network_error", "network_error"),
        ("provider_error", "provider_error"),
    ],
)
def test_narrative_generator_maps_typed_client_errors_to_debug_reason(
    tmp_path, reason, expected
) -> None:
    from app.ai.llm_client import LLMClientError

    generator = LLMRecommendationNarrativeGenerator(
        client=StubLLMClient(error=LLMClientError("failure", reason=reason)),
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    narrative, debug = generator.generate_with_debug(build_result())

    assert narrative is None
    assert debug.narrative_error == expected
