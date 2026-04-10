from __future__ import annotations

import json
import logging
from abc import ABC
from datetime import UTC, datetime
from hashlib import sha256

from pydantic import BaseModel, Field, ValidationError

from app.ai.gemini_client import GeminiClient
from app.ai.llm_client import LLMClient, LLMClientError
from app.data.repositories import LLMCacheRepository
from app.domain.models import ParsedQueryResponse, ParseQueryDebugInfo

PARSER_PROMPT_VERSION = "v1"
PARSER_SCHEMA_VERSION = "v1"
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


class LLMParsedQueryPayload(BaseModel):
    filters: ParsedFiltersPayload
    confidence: float = Field(ge=0, le=1)
    unknown_parts: list[str] = Field(default_factory=list)


class HeuristicQueryParser(QueryParser):
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
    ) -> None:
        self._client = client or GeminiClient()
        self._fallback = fallback_parser or HeuristicQueryParser()
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
            "lift_distance, budget_flex. "
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
            parsed = self._normalize_payload(json.loads(raw_response))
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

    def _normalize_payload(self, payload: dict) -> dict:
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
