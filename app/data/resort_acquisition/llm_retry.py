from __future__ import annotations

import logging
import time
from typing import Any

from app.ai.llm_client import LLMClient, LLMClientError

TRANSIENT_LLM_RETRY_REASONS = {"network_error", "provider_error"}
DEFAULT_LLM_RETRY_DELAYS_SECONDS = (0.0, 0.0)


def complete_with_retries(
    *,
    llm_client: LLMClient,
    operation: str,
    logger: logging.Logger,
    **completion_kwargs: Any,
) -> str:
    delays = DEFAULT_LLM_RETRY_DELAYS_SECONDS
    max_attempts = len(delays) + 1
    for attempt_index in range(max_attempts):
        try:
            return llm_client.complete(**completion_kwargs)
        except LLMClientError as error:
            is_final_attempt = attempt_index == len(delays)
            if error.reason not in TRANSIENT_LLM_RETRY_REASONS or is_final_attempt:
                raise
            next_attempt = attempt_index + 2
            logger.warning(
                "%s LLM call failed with %s; retrying attempt %s/%s",
                operation,
                error.reason,
                next_attempt,
                max_attempts,
            )
            delay_seconds = delays[attempt_index]
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    raise RuntimeError("unreachable LLM retry state")
