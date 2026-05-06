from __future__ import annotations

import json
import logging
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.ai.llm_client import LLMClientError
from app.data.resort_acquisition.llm_retry import complete_with_retries
from app.data.resort_acquisition.official_links import (
    OFFICIAL_LINK_ROLES,
    OfficialLinkCandidate,
)
from app.data.resort_acquisition.source_context import (
    MAX_EFFECTIVE_OFFICIAL_URLS_PER_ROLE,
)

PROMPT_VERSION = "official-link-classifier-v1"
SCHEMA_VERSION = "official-link-classifier-schema-v1"
MAX_LLM_LINK_CLASSIFICATION_CANDIDATES = 30
MIN_LLM_LINK_CLASSIFICATION_CONFIDENCE = 0.5
LOGGER = logging.getLogger(__name__)


class ClassifiedOfficialLink(BaseModel):
    url: str
    confidence: float = Field(strict=True, ge=0, le=1)
    reason: str
    language_hint: str | None = None

    @field_validator("url", "reason")
    @classmethod
    def _nonblank_string(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value


class _LLMLinkClassification(BaseModel):
    roles: dict[str, list[ClassifiedOfficialLink]]


class _LLMLinkClassificationCacheEntry(BaseModel):
    raw_response: str


def classify_official_links_with_llm(
    *,
    resort_id: str,
    link_candidates: list[OfficialLinkCandidate],
    llm_client: Any,
    cache_dir: Path,
    model: str | None = None,
) -> tuple[dict[str, list[ClassifiedOfficialLink]], list[str]]:
    classification_candidates = _llm_classification_candidates(link_candidates)
    if not classification_candidates:
        return {}, []

    cache_dir.mkdir(parents=True, exist_ok=True)
    resolved_model = model or getattr(llm_client, "model", None) or "unknown-model"
    cache_path = (
        cache_dir
        / f"{_cache_key(resort_id, classification_candidates, resolved_model)}.json"
    )
    cache_hit = cache_path.exists()

    if cache_hit:
        try:
            cache_entry = _LLMLinkClassificationCacheEntry.model_validate(
                json.loads(cache_path.read_text(encoding="utf-8"))
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as error:
            return {}, [f"invalid LLM link classification cache entry: {error}"]
        raw_response = cache_entry.raw_response
    else:
        try:
            raw_response = complete_with_retries(
                llm_client=llm_client,
                operation=f"official_link_llm resort={resort_id}",
                logger=LOGGER,
                system_prompt=_system_prompt(),
                user_prompt=_user_prompt(resort_id, classification_candidates),
                temperature=0.0,
                response_mime_type="application/json",
                response_json_schema=_response_json_schema(),
            )
        except LLMClientError as error:
            return {}, [f"LLM link classification failed: {error.reason}"]

    classified, errors = _validated_classification(
        raw_response,
        classification_candidates,
    )
    if not cache_hit and not errors:
        cache_path.write_text(
            json.dumps({"raw_response": raw_response}, ensure_ascii=True),
            encoding="utf-8",
        )
    return classified, errors


def _llm_classification_candidates(
    link_candidates: list[OfficialLinkCandidate],
) -> list[OfficialLinkCandidate]:
    role_bearing_candidates = [
        candidate
        for candidate in link_candidates
        if max(candidate.deterministic_scores.values(), default=0.0) > 0
    ]
    return sorted(
        role_bearing_candidates,
        key=_classification_candidate_sort_key,
    )[:MAX_LLM_LINK_CLASSIFICATION_CANDIDATES]


def _classification_candidate_sort_key(
    candidate: OfficialLinkCandidate,
) -> tuple[float, float, int, int, str]:
    role_scores = tuple(candidate.deterministic_scores.values())
    return (
        -max(role_scores, default=0.0),
        -sum(role_scores),
        1 if candidate.is_external else 0,
        len(candidate.url),
        candidate.url,
    )


def _validated_classification(
    raw_response: str,
    link_candidates: list[OfficialLinkCandidate],
) -> tuple[dict[str, list[ClassifiedOfficialLink]], list[str]]:
    try:
        output = _LLMLinkClassification.model_validate(json.loads(raw_response))
    except (json.JSONDecodeError, ValidationError) as error:
        return {}, [f"invalid LLM link classification output: {error}"]

    candidate_urls = {candidate.url for candidate in link_candidates}
    classified: dict[str, list[ClassifiedOfficialLink]] = {}
    errors: list[str] = []

    for role, links in output.roles.items():
        if role not in OFFICIAL_LINK_ROLES:
            errors.append(f"LLM link classification returned unknown role: {role}")
            continue

        accepted_links: list[ClassifiedOfficialLink] = []
        for link in links:
            if link.url not in candidate_urls:
                errors.append(
                    f"LLM link classification returned unknown URL: {link.url}"
                )
                continue
            if link.confidence < MIN_LLM_LINK_CLASSIFICATION_CONFIDENCE:
                continue
            if len(accepted_links) >= MAX_EFFECTIVE_OFFICIAL_URLS_PER_ROLE:
                continue
            accepted_links.append(link)

        if accepted_links:
            classified[role] = accepted_links

    return classified, errors


def _cache_key(
    resort_id: str,
    link_candidates: list[OfficialLinkCandidate],
    model: str,
) -> str:
    candidate_payload = sorted(
        (asdict(candidate) for candidate in link_candidates),
        key=_candidate_key,
    )
    return sha256(
        json.dumps(
            {
                "resort_id": resort_id,
                "link_candidates": candidate_payload,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "model": model,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _candidate_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("url", "")),
        str(candidate.get("source_page_url", "")),
        str(candidate.get("link_text", "")),
    )


def _sorted_candidate_json(
    link_candidates: list[OfficialLinkCandidate],
) -> str:
    return json.dumps(
        sorted(
            (asdict(candidate) for candidate in link_candidates),
            key=_candidate_key,
        ),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _system_prompt() -> str:
    return (
        "Classify official ski resort link candidates into the allowed roles. "
        "Use only the provided candidates. Return strict JSON matching the schema. "
        "Only assign confidence 0.5 or higher when the URL and surrounding text "
        "clearly identify the requested ski-resort role; otherwise omit it."
    )


def _user_prompt(
    resort_id: str,
    link_candidates: list[OfficialLinkCandidate],
) -> str:
    roles = ", ".join(OFFICIAL_LINK_ROLES)
    return (
        f"Resort ID: {resort_id}\n"
        f"Allowed roles: {roles}\n\n"
        "Classify these candidate links. Return only URLs from this JSON:\n"
        f"{_sorted_candidate_json(link_candidates)}"
    )


def _response_json_schema() -> dict[str, Any]:
    link_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
            "language_hint": {"type": "string"},
        },
        "required": ["url", "confidence", "reason"],
    }
    return {
        "type": "object",
        "properties": {
            "roles": {
                "type": "object",
                "properties": {
                    role: {"type": "array", "items": link_schema}
                    for role in OFFICIAL_LINK_ROLES
                },
            }
        },
        "required": ["roles"],
    }
