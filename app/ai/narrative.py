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
from app.domain.models import SearchDebugInfo, SearchResult

NARRATIVE_PROMPT_VERSION = "v1"
NARRATIVE_SCHEMA_VERSION = "v1"

NARRATIVE_RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation_narrative": {"type": "string"},
    },
    "required": ["recommendation_narrative"],
}
logger = logging.getLogger(__name__)


class NarrativePayload(BaseModel):
    recommendation_narrative: str = Field(min_length=1)


class RecommendationNarrativeGenerator(ABC):
    def generate(self, result: SearchResult) -> str | None:
        raise NotImplementedError

    def generate_with_debug(
        self, result: SearchResult
    ) -> tuple[str | None, SearchDebugInfo]:
        return (
            self.generate(result),
            SearchDebugInfo(
                narrative_source="none",
                narrative_cache_hit=False,
                narrative_error=None,
                narrative_model=None,
                top_result_resort_id=result.resort_id,
            ),
        )


class LLMRecommendationNarrativeGenerator(RecommendationNarrativeGenerator):
    def __init__(
        self,
        *,
        client: LLMClient | None = None,
        cache_repository: LLMCacheRepository | None = None,
        model: str | None = None,
        prompt_version: str = NARRATIVE_PROMPT_VERSION,
        schema_version: str = NARRATIVE_SCHEMA_VERSION,
    ) -> None:
        self._client = client or GeminiClient(model=model)
        self._cache = cache_repository or LLMCacheRepository()
        self._prompt_version = prompt_version
        self._schema_version = schema_version

    def generate(self, result: SearchResult) -> str | None:
        narrative, _ = self.generate_with_debug(result)
        return narrative

    def generate_with_debug(
        self, result: SearchResult
    ) -> tuple[str | None, SearchDebugInfo]:
        signature = self._result_signature(result)
        cache_key = self._cache_key(signature)
        cached = self._cache.get_narrative_cache(cache_key)
        if cached is not None:
            return (
                cached["recommendation_narrative"],
                SearchDebugInfo(
                    narrative_source="llm_cache",
                    narrative_cache_hit=True,
                    narrative_error=None,
                    narrative_model=self._client.model,
                    top_result_resort_id=result.resort_id,
                ),
            )

        system_prompt = (
            "You write a short ski-trip recommendation narrative. "
            "Use only the supplied structured facts. Do not invent new resort facts. "
            "Return strict JSON with one key: recommendation_narrative. "
            "Keep it to 1-2 concise sentences."
        )
        user_prompt = (
            "Write a grounded recommendation narrative for the top search result.\n"
            f"{signature}"
        )

        try:
            raw_response = self._client.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                response_mime_type="application/json",
                response_json_schema=NARRATIVE_RESPONSE_JSON_SCHEMA,
            )
            payload = NarrativePayload.model_validate(json.loads(raw_response))
        except (LLMClientError, ValidationError, json.JSONDecodeError) as error:
            error_reason = "provider_error"
            if isinstance(error, LLMClientError):
                error_reason = error.reason
            if isinstance(error, (ValidationError, json.JSONDecodeError)):
                error_reason = "invalid_output"
            logger.warning(
                "Narrative generation degraded to null.",
                extra={
                    "reason": error_reason,
                    "model": self._client.model,
                    "resort_id": result.resort_id,
                },
            )
            return (
                None,
                SearchDebugInfo(
                    narrative_source="none",
                    narrative_cache_hit=False,
                    narrative_error=error_reason,
                    narrative_model=self._client.model,
                    top_result_resort_id=result.resort_id,
                ),
            )

        response = payload.model_dump()
        self._cache.set_narrative_cache(
            cache_key=cache_key,
            result_signature=signature,
            model=self._client.model,
            prompt_version=self._prompt_version,
            schema_version=self._schema_version,
            response=response,
            created_at=datetime.now(UTC).isoformat(),
        )
        return (
            response["recommendation_narrative"],
            SearchDebugInfo(
                narrative_source="llm",
                narrative_cache_hit=False,
                narrative_error=None,
                narrative_model=self._client.model,
                top_result_resort_id=result.resort_id,
            ),
        )

    def _cache_key(self, signature: str) -> str:
        return sha256(
            "|".join(
                [
                    signature,
                    self._client.model,
                    self._prompt_version,
                    self._schema_version,
                ]
            ).encode("utf-8")
        ).hexdigest()

    def _result_signature(self, result: SearchResult) -> str:
        payload = {
            "resort_name": result.resort_name,
            "region": result.region,
            "selected_ski_area_name": result.selected_ski_area_name,
            "selected_stay_base_name": result.selected_stay_base_name,
            "conditions_summary": result.conditions_summary,
            "snow_confidence_label": result.snow_confidence_label,
            "availability_status": result.availability_status,
            "highlights": [item.label for item in result.explanation.highlights],
            "risks": [item.label for item in result.explanation.risks],
            "recommendation_confidence": result.recommendation_confidence,
        }
        return json.dumps(payload, sort_keys=True)


def get_narrative_generator() -> RecommendationNarrativeGenerator:
    return LLMRecommendationNarrativeGenerator()
