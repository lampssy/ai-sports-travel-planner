from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from app.ai.llm_client import LLMClient, LLMClientError


@dataclass(frozen=True)
class LLMRateLimitConfig:
    min_interval_seconds: float = 0.0
    request_budget: int = 0

    def __post_init__(self) -> None:
        if self.min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be non-negative")
        if self.request_budget < 0:
            raise ValueError("request_budget must be non-negative")


class RateLimitedLLMClient(LLMClient):
    """Run-local guard for LLM provider rate and quota limits."""

    def __init__(
        self,
        wrapped: LLMClient,
        config: LLMRateLimitConfig,
        *,
        logger: logging.Logger,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._wrapped = wrapped
        self._config = config
        self._logger = logger
        self._clock = clock
        self._sleeper = sleeper
        self._request_count = 0
        self._last_request_started_at: float | None = None
        self._disabled_reason: str | None = None

    @property
    def model(self) -> str:
        return self._wrapped.model

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def disabled_reason(self) -> str | None:
        return self._disabled_reason

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        response_mime_type: str | None = None,
        response_json_schema: dict | None = None,
    ) -> str:
        if self._disabled_reason is not None:
            raise LLMClientError(
                "LLM calls are disabled for this acquisition run after "
                f"{self._disabled_reason}.",
                reason=self._disabled_reason,
            )
        if (
            self._config.request_budget > 0
            and self._request_count >= self._config.request_budget
        ):
            self._disabled_reason = "quota_error"
            raise LLMClientError(
                "LLM request budget exhausted for this acquisition run.",
                reason="quota_error",
            )

        self._wait_for_rate_limit()
        self._request_count += 1
        try:
            return self._wrapped.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                response_mime_type=response_mime_type,
                response_json_schema=response_json_schema,
            )
        except LLMClientError as error:
            if error.reason == "quota_error":
                self._disabled_reason = "quota_error"
            raise

    def _wait_for_rate_limit(self) -> None:
        now = self._clock()
        if self._last_request_started_at is not None:
            elapsed_seconds = now - self._last_request_started_at
            wait_seconds = self._config.min_interval_seconds - elapsed_seconds
            if wait_seconds > 0:
                self._logger.info(
                    "LLM rate limit sleep seconds=%.2f request_count=%s",
                    wait_seconds,
                    self._request_count,
                )
                self._sleeper(wait_seconds)
                now = self._clock()
        self._last_request_started_at = now
