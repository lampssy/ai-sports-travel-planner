from datetime import date

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


def test_llm_parser_returns_valid_structured_extraction() -> None:
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
        cache_repository=LLMCacheRepository(),
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


def test_llm_parser_returns_trip_context_and_clarifications() -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {
                "location": "france",
                "skill_level": "intermediate"
              },
              "trip_context": {
                "budget_mode": "total_trip",
                "budget_min": 1500,
                "budget_max": 1500,
                "party_size": null,
                "trip_duration_nights": 6,
                "origin_text": null
              },
              "confidence": 0.86,
              "unknown_parts": []
            }
            """
        ),
        cache_repository=LLMCacheRepository(),
    )

    payload = parser.parse("France ski trip with a full trip budget")

    assert payload["trip_context"]["budget_mode"] == "total_trip"
    assert payload["trip_context"]["budget_min"] == 1500
    assert payload["trip_context"]["trip_duration_nights"] == 6
    clarification_ids = [item["id"] for item in payload["clarifications"]]
    assert "trip-duration" not in clarification_ids
    assert "party-size" in clarification_ids


def test_llm_parser_normalizes_exact_dates_and_drops_travel_month() -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {
                "location": "france",
                "travel_month": 3,
                "trip_start_date": "2026-03-08",
                "trip_end_date": "2026-03-12"
              },
              "confidence": 0.83,
              "unknown_parts": []
            }
            """
        ),
        cache_repository=LLMCacheRepository(),
    )

    payload = parser.parse("france ski trip from 8 March to 12 March")

    assert payload["filters"]["location"] == "France"
    assert payload["filters"]["trip_start_date"] == "2026-03-08"
    assert payload["filters"]["trip_end_date"] == "2026-03-12"
    assert "travel_month" not in payload["filters"]


def test_llm_parser_keeps_month_only_timing_as_travel_month() -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {
                "location": "austria",
                "trip_start_date": "2027-03-01",
                "trip_end_date": "2027-03-31"
              },
              "confidence": 0.9,
              "unknown_parts": []
            }
            """
        ),
        cache_repository=LLMCacheRepository(),
        reference_date=date(2026, 4, 28),
    )

    payload = parser.parse("cheap March ski trip in Austria for intermediates")

    assert payload["filters"]["location"] == "Austria"
    assert payload["filters"]["travel_month"] == 3
    assert "trip_start_date" not in payload["filters"]
    assert "trip_end_date" not in payload["filters"]


def test_llm_parser_keeps_explicit_full_month_date_range() -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {
                "location": "austria",
                "travel_month": 3,
                "trip_start_date": "2027-03-01",
                "trip_end_date": "2027-03-31"
              },
              "confidence": 0.9,
              "unknown_parts": []
            }
            """
        ),
        cache_repository=LLMCacheRepository(),
        reference_date=date(2026, 4, 28),
    )

    payload = parser.parse("ski in Austria from 1 March to 31 March")

    assert payload["filters"]["location"] == "Austria"
    assert payload["filters"]["trip_start_date"] == "2027-03-01"
    assert payload["filters"]["trip_end_date"] == "2027-03-31"
    assert "travel_month" not in payload["filters"]


def test_llm_parser_rejects_partial_exact_date_output() -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {
                "location": "france",
                "trip_start_date": "2026-03-08"
              },
              "confidence": 0.83,
              "unknown_parts": []
            }
            """
        ),
        cache_repository=LLMCacheRepository(),
    )

    payload, debug = parser.parse_with_debug("france ski trip around 8 March")

    assert payload["filters"]["location"] == "France"
    assert "trip_start_date" not in payload["filters"]
    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == "invalid_output"


def test_llm_parser_falls_back_to_heuristic_on_invalid_json() -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient("not json"),
        cache_repository=LLMCacheRepository(),
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


def test_llm_parser_falls_back_when_confidence_is_too_low() -> None:
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
        cache_repository=LLMCacheRepository(),
    )

    payload = parser.parse("cheap france ski trip")

    assert payload["filters"]["location"] == "France"
    assert payload["confidence"] != pytest.approx(0.2)

    _, debug = parser.parse_with_debug("cheap france ski trip")
    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == "low_confidence"


def test_llm_parser_uses_cached_response_for_same_query_and_version() -> None:
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
        cache_repository=LLMCacheRepository(),
    )

    first = parser.parse("france intermediate ski trip")
    second = parser.parse("france intermediate ski trip")

    assert first == second
    assert client.calls == 1

    _, debug = parser.parse_with_debug("france intermediate ski trip")
    assert debug.parser_source == "llm_cache"
    assert debug.cache_hit is True


def test_llm_parser_bypasses_old_cache_when_prompt_version_changes() -> None:
    cache_repository = LLMCacheRepository()
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


def test_llm_parser_marks_empty_filters_as_fallback_reason() -> None:
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
        cache_repository=LLMCacheRepository(),
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
    reason, expected
) -> None:
    from app.ai.llm_client import LLMClientError

    parser = LLMBackedQueryParser(
        client=StubLLMClient(error=LLMClientError("failure", reason=reason)),
        cache_repository=LLMCacheRepository(),
    )

    _, debug = parser.parse_with_debug("cheap france ski trip")

    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == expected


def test_llm_parser_truncates_and_sanitizes_raw_preview() -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient("  not   valid \n json " * 40),
        cache_repository=LLMCacheRepository(),
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


@pytest.mark.parametrize(
    "phrase",
    [
        "close to the lift",
        "close to lifts",
        "near the lifts",
        "not too far from the lifts",
    ],
)
def test_heuristic_parser_maps_common_lift_phrasing_to_near(
    phrase: str,
) -> None:
    payload = HeuristicQueryParser().parse(f"ski in austria {phrase}")

    assert payload["filters"]["location"] == "Austria"
    assert payload["filters"]["lift_distance"] == "near"


@pytest.mark.parametrize(
    "phrase",
    ["budget", "budget-friendly", "low budget"],
)
def test_heuristic_parser_maps_budget_phrasing_to_existing_price_filter(
    phrase: str,
) -> None:
    payload = HeuristicQueryParser().parse(f"{phrase} ski trip in france")

    assert payload["filters"]["location"] == "France"
    assert payload["filters"]["max_price"] == 200


def test_trip_context_clarifies_ambiguous_budget_mode() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 1, 1)).parse(
        "France ski trip for two people with EUR 1500 budget"
    )

    assert payload["trip_context"]["budget_min"] == 1500
    assert payload["trip_context"]["budget_max"] == 1500
    assert payload["trip_context"]["budget_mode"] is None
    clarification = payload["clarifications"][0]
    assert clarification["id"] == "budget-mode"
    assert [option["id"] for option in clarification["options"]] == [
        "lodging-nightly",
        "total-trip",
    ]
    lodging_option = clarification["options"][0]
    assert lodging_option["filter_patch"] == {
        "min_price": 1500.0,
        "max_price": 1500.0,
    }


def test_trip_context_clarifies_total_budget_duration_and_origin() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 1, 1)).parse(
        "France ski trip total budget EUR 1500 for two people not too far away"
    )

    ids = [clarification["id"] for clarification in payload["clarifications"]]
    assert "trip-duration" in ids
    assert "travel-origin" in ids
    assert "party-size" not in ids
    assert payload["trip_context"]["budget_mode"] == "total_trip"
    assert payload["trip_context"]["party_size"] == 2


def test_trip_context_extracts_suffix_eur_budget_amount() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 1, 1)).parse(
        "France ski trip 1500 EUR total budget"
    )

    assert payload["trip_context"]["budget_min"] == 1500
    assert payload["trip_context"]["budget_max"] == 1500
    assert payload["trip_context"]["budget_mode"] == "total_trip"


@pytest.mark.parametrize("phrase", ["all-in EUR 1500", "whole-trip EUR 1500"])
def test_trip_context_maps_clear_total_budget_phrasing(phrase: str) -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 1, 1)).parse(
        f"France ski trip {phrase}"
    )

    assert payload["trip_context"]["budget_min"] == 1500
    assert payload["trip_context"]["budget_mode"] == "total_trip"


def test_heuristic_parser_maps_exact_date_range_to_dates() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 1, 1)).parse(
        "ski in france 9 Apr to 16 Apr near lift"
    )

    assert payload["filters"]["location"] == "France"
    assert payload["filters"]["trip_start_date"] == "2026-04-09"
    assert payload["filters"]["trip_end_date"] == "2026-04-16"
    assert "travel_month" not in payload["filters"]


def test_heuristic_parser_infers_next_year_for_past_date_range() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 4, 28)).parse(
        "ski in france 9 Apr to 16 Apr"
    )

    assert payload["filters"]["trip_start_date"] == "2027-04-09"
    assert payload["filters"]["trip_end_date"] == "2027-04-16"


def test_heuristic_parser_keeps_current_year_for_active_date_range() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 4, 12)).parse(
        "ski in france 9 Apr to 16 Apr"
    )

    assert payload["filters"]["trip_start_date"] == "2026-04-09"
    assert payload["filters"]["trip_end_date"] == "2026-04-16"


def test_heuristic_parser_maps_week_style_range_to_dates() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 1, 1)).parse(
        "ski in france first week of March"
    )

    assert payload["filters"]["trip_start_date"] == "2026-03-01"
    assert payload["filters"]["trip_end_date"] == "2026-03-07"
    assert "travel_month" not in payload["filters"]


def test_heuristic_parser_keeps_current_year_for_active_week_range() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 3, 3)).parse(
        "ski in france first week of March"
    )

    assert payload["filters"]["trip_start_date"] == "2026-03-01"
    assert payload["filters"]["trip_end_date"] == "2026-03-07"
