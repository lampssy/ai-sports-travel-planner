from __future__ import annotations

import json
import logging
import math
import re
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.ai.llm_client import LLMClient, LLMClientError
from app.data.resort_acquisition.fetching import FetchedPage
from app.data.resort_acquisition.llm_retry import complete_with_retries
from app.data.resort_acquisition.models import (
    CandidateFact,
    LiftPassPriceCandidate,
    SourceReference,
)

PROMPT_VERSION = "official-page-v3"
SCHEMA_VERSION = "official-page-schema-v1"
LOGGER = logging.getLogger(__name__)

ALLOWED_LLM_FACT_FIELDS = {
    "total_piste_km",
    "total_lift_count",
    "piste_km_by_difficulty",
    "ski_area_official_url",
    "ski_pass_url",
    "rental_url",
    "season_dates_url",
    "season_windows",
    "trail_map_url",
    "official_status_url",
    "rental_facts",
}

LLM_URL_FACT_FIELDS = {
    "ski_area_official_url",
    "ski_pass_url",
    "rental_url",
    "season_dates_url",
    "trail_map_url",
    "official_status_url",
}

DIFFICULTY_KEYS = ("beginner", "intermediate", "advanced")
DIFFICULTY_KEY_SET = set(DIFFICULTY_KEYS)
RENTAL_FACT_KEYS = {
    "provider_name",
    "provider_url",
    "price_range",
    "quality_tier",
    "lift_distance",
}


class ExtractedFact(BaseModel):
    field_path: str
    value: Any = None
    evidence: str | None = None
    confidence: float = Field(ge=0, le=1)


class ExtractedOfficialPage(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list)
    lift_pass_prices: list[LiftPassPriceCandidate] = Field(default_factory=list)


class _RawExtractedOfficialPage(BaseModel):
    facts: list[Any] = Field(default_factory=list)
    lift_pass_prices: list[Any] = Field(default_factory=list)


class _LLMExtractionCacheEntry(BaseModel):
    raw_response: str


def extract_official_page_candidates(
    *,
    resort_id: str,
    page: FetchedPage,
    page_role: str,
    llm_client: LLMClient,
    cache_dir: Path,
) -> tuple[list[CandidateFact], list[str]]:
    if not page.text.strip() or page.content_hash is None:
        return [], [f"{page.url}: no fetched text available for LLM extraction"]

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = sha256(
        "|".join(
            [
                page.url,
                page.content_hash,
                SCHEMA_VERSION,
                PROMPT_VERSION,
                llm_client.model,
                page_role,
            ]
        ).encode("utf-8")
    ).hexdigest()
    cache_path = cache_dir / f"{cache_key}.json"
    cache_hit = cache_path.exists()

    if cache_hit:
        try:
            cache_entry = _LLMExtractionCacheEntry.model_validate(
                json.loads(cache_path.read_text(encoding="utf-8"))
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as error:
            return [], [f"{page.url}: invalid LLM cache entry: {error}"]
        raw_response = cache_entry.raw_response
    else:
        try:
            raw_response = complete_with_retries(
                llm_client=llm_client,
                operation=f"official_page_llm url={page.url}",
                logger=LOGGER,
                system_prompt=_system_prompt(),
                user_prompt=_user_prompt(page_role, page.final_url, page.text),
                temperature=0.0,
                response_mime_type="application/json",
                response_json_schema=_response_json_schema(),
            )
        except LLMClientError as error:
            return [], [f"{page.url}: LLM extraction failed: {error.reason}"]

    try:
        extraction = _RawExtractedOfficialPage.model_validate(json.loads(raw_response))
    except (json.JSONDecodeError, ValidationError) as error:
        return [], [f"{page.url}: invalid LLM extraction output: {error}"]

    source = SourceReference(source_type="official", source_url=page.final_url)
    candidates: list[CandidateFact] = []
    errors: list[str] = []

    for raw_fact in extraction.facts:
        try:
            fact = ExtractedFact.model_validate(raw_fact)
        except ValidationError as error:
            errors.append(
                f"{page.url}: invalid LLM extraction output for fact: {error}"
            )
            continue
        if fact.value is None:
            continue
        if fact.field_path not in ALLOWED_LLM_FACT_FIELDS:
            errors.append(f"{page.url}: unsupported LLM fact field: {fact.field_path}")
            continue
        if not _has_evidence(fact.evidence):
            errors.append(
                f"{page.url}: missing evidence for LLM fact: {fact.field_path}"
            )
            continue
        try:
            proposed_value = _validated_llm_fact_value(fact.field_path, fact.value)
        except ValueError as error:
            errors.append(
                f"{page.url}: invalid LLM extraction output for "
                f"{fact.field_path}: {error}"
            )
            continue
        try:
            candidates.append(
                CandidateFact(
                    resort_id=resort_id,
                    field_path=fact.field_path,
                    proposed_value=proposed_value,
                    source=source,
                    extraction_method="official_page_llm",
                    fetched_at=page.fetched_at,
                    confidence=fact.confidence,
                    evidence=fact.evidence,
                )
            )
        except ValidationError as error:
            errors.append(
                f"{page.url}: invalid LLM extraction output for "
                f"{fact.field_path}: {error}"
            )

    for raw_price in extraction.lift_pass_prices:
        try:
            price = LiftPassPriceCandidate.model_validate(raw_price)
        except ValidationError as error:
            errors.append(
                f"{page.url}: invalid LLM extraction output for "
                f"lift_pass_prices: {error}"
            )
            continue
        if not _has_evidence(price.evidence):
            errors.append(f"{page.url}: missing evidence for LLM lift pass price")
            continue
        if not _is_supported_lift_pass_audience(price.audience):
            errors.append(
                f"{page.url}: unsupported LLM lift pass audience: {price.audience}"
            )
            continue
        try:
            candidates.append(
                CandidateFact(
                    resort_id=resort_id,
                    field_path="lift_pass_prices",
                    proposed_value=price.model_dump(mode="json"),
                    source=source,
                    extraction_method="official_page_llm",
                    fetched_at=page.fetched_at,
                    confidence=price.confidence,
                    evidence=price.evidence,
                )
            )
        except ValidationError as error:
            errors.append(
                f"{page.url}: invalid LLM extraction output for "
                f"lift_pass_prices: {error}"
            )

    if not cache_hit and not errors:
        cache_path.write_text(
            json.dumps({"raw_response": raw_response}, ensure_ascii=True),
            encoding="utf-8",
        )

    return candidates, errors


def _has_evidence(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _is_supported_lift_pass_audience(audience: str) -> bool:
    normalized = audience.lower()
    excluded_terms = (
        "child",
        "children",
        "kid",
        "kids",
        "kinder",
        "junior",
        "youth",
        "teen",
        "senior",
        "family",
        "familie",
        "bambin",
        "ragazz",
        "enfant",
        "jeune",
    )
    if any(term in normalized for term in excluded_terms):
        return False
    adult_terms = (
        "adult",
        "adults",
        "erwachsene",
        "adulto",
        "adulti",
        "adulte",
        "default",
        "standard",
        "regular",
        "full price",
        "vollzahler",
    )
    return any(term in normalized for term in adult_terms)


def _validated_llm_fact_value(field_path: str, value: Any) -> Any:
    if field_path == "total_piste_km":
        return _finite_non_negative_number(value, "value")
    if field_path == "total_lift_count":
        return _finite_non_negative_whole_number(value, "value")
    if field_path in LLM_URL_FACT_FIELDS:
        return _http_url(value, "value")
    if field_path == "piste_km_by_difficulty":
        return _piste_km_by_difficulty(value)
    if field_path == "rental_facts":
        return _rental_facts(value)
    if field_path == "season_windows":
        return _season_window(value)
    raise ValueError("unsupported field_path")


def _finite_non_negative_number(value: Any, field_label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field_label} must be a number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field_label} must be finite")
    if normalized < 0:
        raise ValueError(f"{field_label} must be non-negative")
    return normalized


def _finite_non_negative_whole_number(value: Any, field_label: str) -> int:
    normalized = _finite_non_negative_number(value, field_label)
    if not normalized.is_integer():
        raise ValueError(f"{field_label} must be a whole number")
    return int(normalized)


def _http_url(value: Any, field_label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_label} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_label} must be non-empty")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError(f"{field_label} must start with http:// or https://")
    return normalized


def _piste_km_by_difficulty(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        raise ValueError("value must be an object")
    keys = set(value)
    if keys != DIFFICULTY_KEY_SET:
        expected = ", ".join(DIFFICULTY_KEYS)
        raise ValueError(f"value must contain exactly keys: {expected}")
    return {
        key: _finite_non_negative_number(value[key], key) for key in DIFFICULTY_KEYS
    }


def _rental_facts(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("value must be an object")
    keys = set(value)
    if not keys:
        raise ValueError("value must contain at least one rental fact")
    unknown_keys = keys - RENTAL_FACT_KEYS
    if unknown_keys:
        raise ValueError(
            f"value contains unknown keys: {', '.join(sorted(unknown_keys))}"
        )

    normalized: dict[str, str] = {}
    for key, nested_value in value.items():
        if key == "provider_url":
            normalized[key] = _http_url(nested_value, key)
            continue
        if not isinstance(nested_value, str):
            raise ValueError(f"{key} must be a string")
        stripped_value = nested_value.strip()
        if not stripped_value:
            raise ValueError(f"{key} must be non-empty")
        normalized[key] = stripped_value
    return normalized


def _season_window(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("value must be an object")
    start_date = _iso_date(value.get("start_date"), "start_date")
    end_date = _iso_date(value.get("end_date"), "end_date")
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    status = value.get("status", "planned")
    if status not in {"planned", "estimated"}:
        raise ValueError("status must be planned or estimated")
    season_label = value.get("season_label")
    if season_label is None:
        season_label = _season_label(start_date, end_date)
    elif not isinstance(season_label, str) or not season_label.strip():
        raise ValueError("season_label must be a non-empty string when provided")
    return {
        "season_label": season_label.strip(),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "status": status,
    }


def _iso_date(value: Any, field_label: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field_label} must be an ISO date string")
    normalized = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        raise ValueError(f"{field_label} must use YYYY-MM-DD format")
    try:
        return date.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{field_label} must be a valid date") from error


def _season_label(start_date: date, end_date: date) -> str:
    if start_date.year == end_date.year:
        return str(start_date.year)
    return f"{start_date.year}-{end_date.year}"


def _system_prompt() -> str:
    return (
        "Extract structured ski resort facts from official or provider page text. "
        "Use only facts explicitly supported by the page text. Return strict JSON "
        "matching the schema. Every returned fact and price must include short "
        "verbatim evidence from the page text. Do not guess missing values. "
        "For season_windows, return exact date ranges only when explicit full "
        "calendar dates are present, using YYYY-MM-DD dates. "
        "For lift_pass_prices, extract only adult/default public ski pass prices; "
        "omit child, youth, senior, family, free promotional, and companion prices."
    )


def _user_prompt(page_role: str, url: str, text: str) -> str:
    allowed_fields = ", ".join(sorted(ALLOWED_LLM_FACT_FIELDS))
    return (
        f"Page role: {page_role}\n"
        f"URL: {url}\n"
        f"Allowed fact field_path values: {allowed_fields}\n\n"
        "For season_windows, return value as an object with season_label, "
        "start_date, end_date, and status. Use YYYY-MM-DD dates and status "
        "planned unless the page clearly marks the dates as estimated.\n\n"
        "Extract only clearly supported facts and adult/default lift pass prices "
        "from this text:\n"
        f"{text}"
    )


def _response_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field_path": {
                            "type": "string",
                            "enum": sorted(ALLOWED_LLM_FACT_FIELDS),
                        },
                        "value": {},
                        "evidence": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["field_path", "value", "evidence", "confidence"],
                },
            },
            "lift_pass_prices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "duration_days": {"type": "integer", "minimum": 1},
                        "audience": {"type": "string"},
                        "amount": {"type": "number", "minimum": 0},
                        "amount_min": {"type": "number", "minimum": 0},
                        "amount_max": {"type": "number", "minimum": 0},
                        "currency": {"type": "string"},
                        "price_kind": {
                            "type": "string",
                            "enum": ["fixed", "from", "range", "unknown"],
                        },
                        "season_label": {"type": "string"},
                        "source_url": {"type": "string"},
                        "evidence": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": [
                        "duration_days",
                        "audience",
                        "currency",
                        "price_kind",
                        "source_url",
                        "evidence",
                        "confidence",
                    ],
                },
            },
        },
        "required": ["facts", "lift_pass_prices"],
    }
