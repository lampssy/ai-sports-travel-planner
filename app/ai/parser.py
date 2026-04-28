from __future__ import annotations

import json
import logging
import re
from abc import ABC
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256

from pydantic import BaseModel, Field, ValidationError

from app.ai.gemini_client import GeminiClient
from app.ai.llm_client import LLMClient, LLMClientError
from app.data.repositories import LLMCacheRepository
from app.domain.models import ParsedQueryResponse, ParseQueryDebugInfo

PARSER_PROMPT_VERSION = "v4"
PARSER_SCHEMA_VERSION = "v4"
MIN_LLM_PARSE_CONFIDENCE = 0.45
RAW_RESPONSE_PREVIEW_MAX_CHARS = 200

PARSER_RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "filters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "min_price": {"type": "number"},
                "max_price": {"type": "number"},
                "stars": {"type": "integer"},
                "skill_level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                },
                "lift_distance": {
                    "type": "string",
                    "enum": ["near", "medium", "far"],
                },
                "budget_flex": {"type": "number"},
                "travel_month": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 12,
                },
                "trip_start_date": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                },
                "trip_end_date": {
                    "type": "string",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                },
            },
        },
        "confidence": {"type": "number"},
        "unknown_parts": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["filters", "confidence", "unknown_parts"],
}
logger = logging.getLogger(__name__)


class QueryParsingError(ValueError):
    """Raised when the parser cannot produce valid structured filters."""


class QueryParser(ABC):
    def parse(self, query: str) -> dict:
        raise NotImplementedError

    def parse_with_debug(self, query: str) -> tuple[dict, ParseQueryDebugInfo]:
        payload = self.parse(query)
        return (
            payload,
            ParseQueryDebugInfo(
                parser_source="heuristic_fallback",
                fallback_reason=None,
                llm_confidence=None,
                cache_hit=False,
                model=None,
            ),
        )


class ParsedFiltersPayload(BaseModel):
    location: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    stars: int | None = Field(default=None, ge=1, le=3)
    skill_level: str | None = None
    lift_distance: str | None = None
    budget_flex: float | None = Field(default=None, ge=0, le=0.5)
    travel_month: int | None = Field(default=None, ge=1, le=12)
    trip_start_date: date | None = None
    trip_end_date: date | None = None


class LLMParsedQueryPayload(BaseModel):
    filters: ParsedFiltersPayload
    confidence: float = Field(ge=0, le=1)
    unknown_parts: list[str] = Field(default_factory=list)


class HeuristicQueryParser(QueryParser):
    def __init__(self, *, reference_date: date | None = None) -> None:
        self._reference_date = reference_date or datetime.now(UTC).date()

    def parse(self, query: str) -> dict:
        payload, _ = self.parse_with_debug(query)
        return payload

    def parse_with_debug(self, query: str) -> tuple[dict, ParseQueryDebugInfo]:
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

        date_range = _extract_heuristic_date_range(
            normalized,
            reference_date=self._reference_date,
        )
        if date_range is not None:
            start_date, end_date = date_range
            filters["trip_start_date"] = start_date.isoformat()
            filters["trip_end_date"] = end_date.isoformat()

        month_match = _MONTH_NAME_PATTERN.search(normalized)
        if date_range is None and month_match is not None:
            filters["travel_month"] = MONTH_NAME_TO_NUMBER[month_match.group("month")]

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
        return (
            response.model_dump(),
            ParseQueryDebugInfo(
                parser_source="heuristic_fallback",
                fallback_reason=None,
                llm_confidence=None,
                cache_hit=False,
                model=None,
            ),
        )


class LLMBackedQueryParser(QueryParser):
    def __init__(
        self,
        *,
        client: LLMClient | None = None,
        fallback_parser: QueryParser | None = None,
        cache_repository: LLMCacheRepository | None = None,
        prompt_version: str = PARSER_PROMPT_VERSION,
        schema_version: str = PARSER_SCHEMA_VERSION,
        min_confidence: float = MIN_LLM_PARSE_CONFIDENCE,
        reference_date: date | None = None,
    ) -> None:
        self._client = client or GeminiClient()
        self._reference_date = reference_date or datetime.now(UTC).date()
        self._fallback = fallback_parser or HeuristicQueryParser(
            reference_date=self._reference_date
        )
        self._cache = cache_repository or LLMCacheRepository()
        self._prompt_version = prompt_version
        self._schema_version = schema_version
        self._min_confidence = min_confidence

    def parse(self, query: str) -> dict:
        payload, _ = self.parse_with_debug(query)
        return payload

    def parse_with_debug(self, query: str) -> tuple[dict, ParseQueryDebugInfo]:
        cache_key = self._cache_key(query)
        cached = self._cache.get_parse_cache(cache_key)
        if cached is not None:
            return (
                ParsedQueryResponse.model_validate(cached).model_dump(),
                ParseQueryDebugInfo(
                    parser_source="llm_cache",
                    fallback_reason=None,
                    llm_confidence=cached.get("confidence"),
                    cache_hit=True,
                    model=self._client.model,
                ),
            )

        system_prompt = (
            "You extract structured ski trip search filters from a free-text query. "
            "Return strict JSON with keys filters, confidence, unknown_parts. "
            "Only use these filter keys when supported by the query: "
            "location, min_price, max_price, stars, skill_level, "
            "lift_distance, budget_flex, travel_month, "
            "trip_start_date, trip_end_date. "
            "Use travel_month for month-only timing. Do not expand a month-only "
            "phrase into the first and last day of that month. Use trip_start_date "
            "and trip_end_date as YYYY-MM-DD only for exact date ranges or week-style "
            "ranges. If exact dates are present, do not include travel_month. "
            "Infer missing years as "
            f"the next occurrence relative to {self._reference_date.isoformat()}. "
            "If something is uncertain, leave it out and mention it in unknown_parts."
        )
        user_prompt = f"Extract structured ski trip filters from this query:\n{query}"
        raw_response: str | None = None

        try:
            raw_response = self._client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=PARSER_RESPONSE_JSON_SCHEMA,
            )
            parsed = self._normalize_payload(json.loads(raw_response), query=query)
        except (
            LLMClientError,
            ValidationError,
            json.JSONDecodeError,
            QueryParsingError,
        ) as error:
            reason = "provider_error"
            if isinstance(error, LLMClientError):
                reason = error.reason
            if isinstance(
                error,
                (ValidationError, json.JSONDecodeError, QueryParsingError),
            ):
                reason = "invalid_output"
            logger.warning(
                "Parser falling back to heuristic parser.",
                extra={
                    "reason": reason,
                    "model": self._client.model,
                },
            )
            return self._fallback_with_debug(
                query,
                fallback_reason=reason,
                raw_response_preview=_sanitize_raw_response_preview(raw_response),
            )

        if not parsed["filters"]:
            logger.info(
                "Parser produced empty filters; using heuristic fallback.",
                extra={"model": self._client.model},
            )
            return self._fallback_with_debug(
                query,
                fallback_reason="empty_filters",
                llm_confidence=parsed["confidence"],
            )

        if parsed["confidence"] < self._min_confidence:
            logger.info(
                "Parser confidence below threshold; using heuristic fallback.",
                extra={
                    "confidence": parsed["confidence"],
                    "model": self._client.model,
                },
            )
            return self._fallback_with_debug(
                query,
                fallback_reason="low_confidence",
                llm_confidence=parsed["confidence"],
            )

        self._cache.set_parse_cache(
            cache_key=cache_key,
            query_text=query,
            model=self._client.model,
            prompt_version=self._prompt_version,
            schema_version=self._schema_version,
            response=parsed,
            created_at=datetime.now(UTC).isoformat(),
        )
        return (
            parsed,
            ParseQueryDebugInfo(
                parser_source="llm",
                fallback_reason=None,
                llm_confidence=parsed["confidence"],
                cache_hit=False,
                model=self._client.model,
            ),
        )

    def _normalize_payload(self, payload: dict, *, query: str = "") -> dict:
        normalized = LLMParsedQueryPayload.model_validate(payload)
        filters = normalized.filters.model_dump(exclude_none=True)
        if "location" in filters:
            filters["location"] = str(filters["location"]).strip().title()
        if "skill_level" in filters:
            value = str(filters["skill_level"]).strip().lower()
            if value not in {"beginner", "intermediate", "advanced"}:
                raise QueryParsingError("Invalid skill_level in model output")
            filters["skill_level"] = value
        if "lift_distance" in filters:
            value = str(filters["lift_distance"]).strip().lower()
            if value not in {"near", "medium", "far"}:
                raise QueryParsingError("Invalid lift_distance in model output")
            filters["lift_distance"] = value
        if "travel_month" in filters:
            value = int(filters["travel_month"])
            if value < 1 or value > 12:
                raise QueryParsingError("Invalid travel_month in model output")
            filters["travel_month"] = value
        if ("trip_start_date" in filters) != ("trip_end_date" in filters):
            raise QueryParsingError(
                "trip_start_date and trip_end_date must be provided together"
            )
        if "trip_start_date" in filters and "trip_end_date" in filters:
            start_date = filters["trip_start_date"]
            end_date = filters["trip_end_date"]
            if not isinstance(start_date, date) or not isinstance(end_date, date):
                raise QueryParsingError("Invalid trip date in model output")
            if end_date < start_date:
                raise QueryParsingError("trip_end_date must be on or after start date")
            if _is_full_month_range_without_explicit_date_signal(
                query,
                start_date=start_date,
                end_date=end_date,
            ):
                filters.pop("trip_start_date", None)
                filters.pop("trip_end_date", None)
                filters["travel_month"] = start_date.month
            else:
                filters["trip_start_date"] = start_date.isoformat()
                filters["trip_end_date"] = end_date.isoformat()
                filters.pop("travel_month", None)

        response = ParsedQueryResponse(
            filters=filters,
            confidence=normalized.confidence,
            unknown_parts=normalized.unknown_parts,
        )
        return response.model_dump()

    def _fallback_with_debug(
        self,
        query: str,
        *,
        fallback_reason: str,
        llm_confidence: float | None = None,
        raw_response_preview: str | None = None,
    ) -> tuple[dict, ParseQueryDebugInfo]:
        payload = self._fallback.parse(query)
        return (
            payload,
            ParseQueryDebugInfo(
                parser_source="heuristic_fallback",
                fallback_reason=fallback_reason,
                llm_confidence=llm_confidence,
                cache_hit=False,
                model=self._client.model,
                raw_response_preview=(
                    raw_response_preview
                    if fallback_reason == "invalid_output"
                    else None
                ),
            ),
        )

    def _cache_key(self, query: str) -> str:
        return sha256(
            "|".join(
                [
                    query,
                    self._client.model,
                    self._prompt_version,
                    self._schema_version,
                    self._reference_date.isoformat(),
                ]
            ).encode("utf-8")
        ).hexdigest()


def get_query_parser() -> QueryParser:
    return LLMBackedQueryParser()


def _sanitize_raw_response_preview(raw_response: str | None) -> str | None:
    if not raw_response:
        return None

    collapsed = " ".join(raw_response.split())
    if not collapsed:
        return None

    if len(collapsed) <= RAW_RESPONSE_PREVIEW_MAX_CHARS:
        return collapsed

    return f"{collapsed[: RAW_RESPONSE_PREVIEW_MAX_CHARS - 3]}..."


MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_MONTH_PATTERN = "|".join(sorted(MONTH_NAME_TO_NUMBER.keys(), key=len, reverse=True))
_MONTH_NAME_PATTERN = re.compile(rf"\b(?P<month>{_MONTH_PATTERN})\b")
_DATE_RANGE_PATTERN = re.compile(
    rf"\b(?P<start_day>\d{{1,2}})"
    rf"(?:st|nd|rd|th)?\s+"
    rf"(?P<start_month>{_MONTH_PATTERN})"
    rf"(?:\s+(?P<start_year>\d{{4}}))?"
    rf"\s*(?:to|-|until|through|\u2013|\u2014)\s*"
    rf"(?P<end_day>\d{{1,2}})"
    rf"(?:st|nd|rd|th)?\s+"
    rf"(?P<end_month>{_MONTH_PATTERN})"
    rf"(?:\s+(?P<end_year>\d{{4}}))?\b",
)
_WEEK_RANGE_PATTERN = re.compile(
    rf"\b(?P<ordinal>first|second|third|fourth)\s+week\s+of\s+"
    rf"(?P<month>{_MONTH_PATTERN})(?:\s+(?P<year>\d{{4}}))?\b",
)
_WEEK_START_DAY = {
    "first": 1,
    "second": 8,
    "third": 15,
    "fourth": 22,
}


def _extract_heuristic_date_range(
    query: str,
    *,
    reference_date: date,
) -> tuple[date, date] | None:
    date_range_match = _DATE_RANGE_PATTERN.search(query)
    if date_range_match is not None:
        return _date_range_from_match(date_range_match, reference_date=reference_date)

    week_match = _WEEK_RANGE_PATTERN.search(query)
    if week_match is not None:
        return _week_range_from_match(week_match, reference_date=reference_date)

    return None


def _is_full_month_range_without_explicit_date_signal(
    query: str,
    *,
    start_date: date,
    end_date: date,
) -> bool:
    if start_date.day != 1:
        return False
    if start_date.year != end_date.year or start_date.month != end_date.month:
        return False

    first_day_next_month = (
        date(start_date.year + 1, 1, 1)
        if start_date.month == 12
        else date(start_date.year, start_date.month + 1, 1)
    )
    if end_date != first_day_next_month - timedelta(days=1):
        return False

    normalized = query.lower()
    mentioned_months = {
        MONTH_NAME_TO_NUMBER[match.group("month")]
        for match in _MONTH_NAME_PATTERN.finditer(normalized)
    }
    if start_date.month not in mentioned_months:
        return False

    return not _has_explicit_date_signal(normalized)


def _has_explicit_date_signal(query: str) -> bool:
    if _DATE_RANGE_PATTERN.search(query) or _WEEK_RANGE_PATTERN.search(query):
        return True

    day_before_month = re.search(
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTH_PATTERN})\b",
        query,
    )
    month_before_day = re.search(
        rf"\b(?:{_MONTH_PATTERN})\s+\d{{1,2}}(?:st|nd|rd|th)?\b",
        query,
    )
    return day_before_month is not None or month_before_day is not None


def _date_range_from_match(
    match: re.Match[str],
    *,
    reference_date: date,
) -> tuple[date, date]:
    start_month = MONTH_NAME_TO_NUMBER[match.group("start_month")]
    end_month = MONTH_NAME_TO_NUMBER[match.group("end_month")]
    start_day = int(match.group("start_day"))
    end_day = int(match.group("end_day"))
    start_year_text = match.group("start_year")
    end_year_text = match.group("end_year")

    if start_year_text is None and end_year_text is None:
        start_date = date(reference_date.year, start_month, start_day)
        end_date = date(reference_date.year, end_month, end_day)
        if end_date < start_date:
            end_date = date(reference_date.year + 1, end_month, end_day)
        if end_date < reference_date:
            start_date = date(reference_date.year + 1, start_month, start_day)
            end_year = start_date.year + (1 if end_month < start_month else 0)
            end_date = date(end_year, end_month, end_day)
        return start_date, end_date

    if start_year_text is not None:
        start_year = int(start_year_text)
    else:
        if end_year_text is None:
            raise QueryParsingError("Unable to infer date range year")
        start_year = int(end_year_text)

    end_year = int(end_year_text) if end_year_text is not None else start_year
    start_date = date(start_year, start_month, start_day)
    end_date = date(end_year, end_month, end_day)
    if end_date < start_date and end_year_text is None:
        end_date = date(end_year + 1, end_month, end_day)
    return start_date, end_date


def _week_range_from_match(
    match: re.Match[str],
    *,
    reference_date: date,
) -> tuple[date, date]:
    month = MONTH_NAME_TO_NUMBER[match.group("month")]
    start_day = _WEEK_START_DAY[match.group("ordinal")]
    year_text = match.group("year")
    year = int(year_text) if year_text is not None else reference_date.year
    start_date = date(year, month, start_day)
    end_date = start_date + timedelta(days=6)
    if year_text is None and end_date < reference_date:
        start_date = date(year + 1, month, start_day)
        end_date = start_date + timedelta(days=6)
    return start_date, end_date
