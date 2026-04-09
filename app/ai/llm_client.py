from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClientError(RuntimeError):
    """Raised when provider output cannot be retrieved safely."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


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
