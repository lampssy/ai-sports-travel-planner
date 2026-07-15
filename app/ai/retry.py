from __future__ import annotations

import logging
import time
from typing import Any

from app.ai.llm_client import LLMClient, LLMClientError
from app.observability.parser import record_llm_retry

TRANSIENT_LLM_RETRY_REASONS = {"network_error", "provider_error"}
DEFAULT_LLM_RETRY_DELAYS_SECONDS = (0.0, 0.0)
BOUNDED_OPERATION_LABELS = {
    "query_parser",
    "recommendation_narrative",
    "official_page_llm",
    "official_link_llm",
    "search_refinement",
}


def complete_with_retries(
    *,
    llm_client: LLMClient,
    operation: str,
    logger: logging.Logger,
    retry_delays_seconds: tuple[float, ...] = DEFAULT_LLM_RETRY_DELAYS_SECONDS,
    **completion_kwargs: Any,
) -> str:
    max_attempts = len(retry_delays_seconds) + 1
    for attempt_index in range(max_attempts):
        try:
            return llm_client.complete(**completion_kwargs)
        except LLMClientError as error:
            is_final_attempt = attempt_index == len(retry_delays_seconds)
            if error.reason not in TRANSIENT_LLM_RETRY_REASONS or is_final_attempt:
                raise
            next_attempt = attempt_index + 2
            record_llm_retry(
                operation=_bounded_operation_label(operation),
                model=llm_client.model,
                reason=error.reason,
            )
            logger.warning(
                "%s LLM call failed with %s; retrying attempt %s/%s",
                operation,
                error.reason,
                next_attempt,
                max_attempts,
            )
            delay_seconds = retry_delays_seconds[attempt_index]
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    raise RuntimeError("unreachable LLM retry state")


def _bounded_operation_label(operation: str) -> str:
    for label in BOUNDED_OPERATION_LABELS:
        if operation == label or operation.startswith(f"{label} "):
            return label
    return "other"
