from abc import ABC, abstractmethod

from app.domain.models import ParsedQueryResponse


class QueryParsingError(ValueError):
    """Raised when the parser cannot produce valid structured filters."""


class QueryParser(ABC):
    @abstractmethod
    def parse(self, query: str) -> dict:
        raise NotImplementedError


class HeuristicQueryParser(QueryParser):
    def parse(self, query: str) -> dict:
        normalized = query.lower()
        filters: dict[str, str | int | float] = {}
        unknown_parts: list[str] = []

        if "france" in normalized:
            filters["location"] = "France"
        elif "austria" in normalized:
            filters["location"] = "Austria"
        elif "switzerland" in normalized:
            filters["location"] = "Switzerland"

        if "beginner" in normalized:
            filters["skill_level"] = "beginner"
        elif "intermediate" in normalized:
            filters["skill_level"] = "intermediate"
        elif "advanced" in normalized:
            filters["skill_level"] = "advanced"

        if "close to lift" in normalized or "near lift" in normalized:
            filters["lift_distance"] = "near"
        elif "medium distance" in normalized:
            filters["lift_distance"] = "medium"
        elif "far from lift" in normalized:
            filters["lift_distance"] = "far"

        if "cheap" in normalized:
            filters["max_price"] = 200
            unknown_parts.append("cheap")

        confidence = 0.25
        if filters:
            confidence = min(0.4 + (len(filters) * 0.12), 0.92)

        response = ParsedQueryResponse(
            filters=filters,
            confidence=confidence,
            unknown_parts=unknown_parts,
        )
        return response.model_dump()


def get_query_parser() -> QueryParser:
    return HeuristicQueryParser()
