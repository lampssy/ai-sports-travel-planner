import pytest

from app.ai.parser import (
    HeuristicQueryParser,
    LLMBackedQueryParser,
    QueryParser,
    QueryParsingError,
)
from app.data.repositories import LLMCacheRepository


class StubParser(QueryParser):
    def parse(self, query: str):
        return {
            "filters": {
                "location": "France",
                "max_price": 200,
                "skill_level": "intermediate",
                "lift_distance": "near",
            },
            "confidence": 0.81,
            "unknown_parts": ["cheap"],
        }


class LowConfidenceParser(QueryParser):
    def parse(self, query: str):
        return {
            "filters": {"location": "France"},
            "confidence": 0.2,
            "unknown_parts": [],
        }


class BrokenParser(QueryParser):
    def parse(self, query: str):
        raise QueryParsingError("bad model output")


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


def test_parser_returns_valid_structured_extraction() -> None:
    payload = StubParser().parse("cheap france ski trip close to lift")

    assert payload["filters"]["location"] == "France"
    assert payload["filters"]["skill_level"] == "intermediate"
    assert payload["confidence"] == pytest.approx(0.81)


def test_parser_exposes_low_confidence_for_fallback() -> None:
    payload = LowConfidenceParser().parse("something ambiguous")

    assert payload["confidence"] < 0.5


def test_parser_raises_for_malformed_model_output() -> None:
    with pytest.raises(QueryParsingError):
        BrokenParser().parse("broken output")


def test_llm_parser_returns_valid_structured_extraction(tmp_path) -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {
                "location": "france",
                "max_price": 200,
                "skill_level": "intermediate",
                "lift_distance": "near",
                "travel_month": 3
              },
              "confidence": 0.83,
              "unknown_parts": ["cheap"]
            }
            """
        ),
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    payload = parser.parse("cheap france ski trip close to lift")

    assert payload["filters"]["location"] == "France"
    assert payload["filters"]["skill_level"] == "intermediate"
    assert payload["filters"]["travel_month"] == 3
    assert payload["confidence"] == pytest.approx(0.83)

    debug_payload, debug = parser.parse_with_debug(
        "cheap france ski trip close to lift"
    )
    assert debug_payload == payload
    assert debug.parser_source == "llm_cache"
    assert parser._client.last_response_mime_type == "application/json"
    assert parser._client.last_response_json_schema is not None


def test_llm_parser_falls_back_to_heuristic_on_invalid_json(tmp_path) -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient("not json"),
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    payload = parser.parse("cheap france ski trip close to lift for intermediate")

    assert payload["filters"]["location"] == "France"
    assert payload["confidence"] == pytest.approx(0.88)

    _, debug = parser.parse_with_debug(
        "cheap france ski trip close to lift for intermediate"
    )
    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == "invalid_output"
    assert debug.raw_response_preview == "not json"


def test_llm_parser_falls_back_when_confidence_is_too_low(tmp_path) -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {"location": "France"},
              "confidence": 0.2,
              "unknown_parts": []
            }
            """
        ),
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    payload = parser.parse("cheap france ski trip")

    assert payload["filters"]["location"] == "France"
    assert payload["confidence"] != pytest.approx(0.2)

    _, debug = parser.parse_with_debug("cheap france ski trip")
    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == "low_confidence"


def test_llm_parser_uses_cached_response_for_same_query_and_version(
    tmp_path,
) -> None:
    client = StubLLMClient(
        """
        {
          "filters": {"location": "France", "skill_level": "intermediate"},
          "confidence": 0.8,
          "unknown_parts": []
        }
        """
    )
    parser = LLMBackedQueryParser(
        client=client,
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    first = parser.parse("france intermediate ski trip")
    second = parser.parse("france intermediate ski trip")

    assert first == second
    assert client.calls == 1

    _, debug = parser.parse_with_debug("france intermediate ski trip")
    assert debug.parser_source == "llm_cache"
    assert debug.cache_hit is True


def test_llm_parser_bypasses_old_cache_when_prompt_version_changes(tmp_path) -> None:
    cache_repository = LLMCacheRepository(tmp_path / "planner.db")
    client = StubLLMClient(
        """
        {
          "filters": {"location": "France"},
          "confidence": 0.8,
          "unknown_parts": []
        }
        """
    )
    parser_v1 = LLMBackedQueryParser(
        client=client,
        cache_repository=cache_repository,
        prompt_version="v1",
    )
    parser_v2 = LLMBackedQueryParser(
        client=client,
        cache_repository=cache_repository,
        prompt_version="v2",
    )

    parser_v1.parse("france ski trip")
    parser_v2.parse("france ski trip")

    assert client.calls == 2


def test_llm_parser_marks_empty_filters_as_fallback_reason(tmp_path) -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {},
              "confidence": 0.9,
              "unknown_parts": []
            }
            """
        ),
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    _, debug = parser.parse_with_debug("somewhere snowy and nice")

    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == "empty_filters"
    assert debug.raw_response_preview is None


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("quota_error", "quota_error"),
        ("auth_error", "auth_error"),
        ("network_error", "network_error"),
        ("provider_error", "provider_error"),
    ],
)
def test_llm_parser_maps_typed_client_errors_to_fallback_reason(
    tmp_path, reason, expected
) -> None:
    from app.ai.llm_client import LLMClientError

    parser = LLMBackedQueryParser(
        client=StubLLMClient(error=LLMClientError("failure", reason=reason)),
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    _, debug = parser.parse_with_debug("cheap france ski trip")

    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == expected


def test_llm_parser_truncates_and_sanitizes_raw_preview(tmp_path) -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient("  not   valid \n json " * 40),
        cache_repository=LLMCacheRepository(tmp_path / "planner.db"),
    )

    _, debug = parser.parse_with_debug("cheap france ski trip")

    assert debug.fallback_reason == "invalid_output"
    assert debug.raw_response_preview is not None
    assert "\n" not in debug.raw_response_preview
    assert "  " not in debug.raw_response_preview
    assert len(debug.raw_response_preview) <= 200


def test_heuristic_parser_maps_month_names_to_travel_month() -> None:
    payload = HeuristicQueryParser().parse("ski in france in march near lift")

    assert payload["filters"]["location"] == "France"
    assert payload["filters"]["lift_distance"] == "near"
    assert payload["filters"]["travel_month"] == 3
