from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClientError(RuntimeError):
    """Raised when provider output cannot be retrieved safely."""

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        provider_http_status: int | None = None,
        provider_status: str | None = None,
        provider_message: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.provider_http_status = provider_http_status
        self.provider_status = provider_status
        self.provider_message = provider_message


class LLMClient(ABC):
    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        response_mime_type: str | None = None,
        response_json_schema: dict | None = None,
    ) -> str:
        raise NotImplementedError
