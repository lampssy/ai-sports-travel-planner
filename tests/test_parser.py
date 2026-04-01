import pytest

from app.ai.parser import QueryParser, QueryParsingError


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
