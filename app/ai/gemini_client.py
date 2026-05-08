from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.ai.llm_client import LLMClient, LLMClientError
from app.config.env import load_dotenv_file

GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
PROVIDER_MESSAGE_PREVIEW_MAX_CHARS = 200


class GeminiClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        load_dotenv_file()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model = model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        response_mime_type: str | None = None,
        response_json_schema: dict | None = None,
    ) -> str:
        if not self.api_key:
            raise LLMClientError(
                "GEMINI_API_KEY is not configured.",
                reason="auth_error",
            )

        generation_config: dict[str, object] = {
            "temperature": temperature,
        }
        if response_mime_type is not None:
            generation_config["responseMimeType"] = response_mime_type
        if response_json_schema is not None:
            generation_config["responseJsonSchema"] = response_json_schema

        payload = json.dumps(
            {
                "system_instruction": {
                    "parts": [{"text": system_prompt}],
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_prompt}],
                    }
                ],
                "generationConfig": generation_config,
            }
        ).encode("utf-8")

        request = Request(
            GEMINI_API_URL_TEMPLATE.format(model=self.model),
            data=payload,
            method="POST",
            headers={
                "X-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            reason, provider_status, provider_message = _classify_http_error(error)
            raise LLMClientError(
                f"Gemini request failed with HTTP {error.code}.",
                reason=reason,
                provider_http_status=error.code,
                provider_status=provider_status,
                provider_message=provider_message,
            ) from error
        except (URLError, TimeoutError) as error:
            raise LLMClientError(
                "Gemini request failed due to a network error.",
                reason="network_error",
            ) from error

        try:
            content = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMClientError(
                "Gemini response did not include message content.",
                reason="provider_error",
                provider_status="MISSING_CONTENT",
                provider_message=(
                    "Response did not contain candidates[0].content.parts[0].text."
                ),
            ) from error

        if not isinstance(content, str) or not content.strip():
            raise LLMClientError(
                "Gemini response content was empty.",
                reason="provider_error",
                provider_status="EMPTY_CONTENT",
                provider_message="Response text was empty.",
            )

        return content.strip()


def _classify_http_error(error: HTTPError) -> tuple[str, str | None, str | None]:
    provider_status = None
    provider_message = None

    try:
        payload = json.loads(error.read().decode("utf-8"))
        details = payload.get("error", {})
        provider_status = _string_or_none(details.get("status"))
        provider_message = _sanitize_provider_message(details.get("message"))
    except Exception:
        pass

    if error.code in {401, 403}:
        return "auth_error", provider_status, provider_message
    if error.code == 429:
        return "quota_error", provider_status, provider_message

    if provider_status == "RESOURCE_EXHAUSTED" or (
        provider_message is not None and "quota" in provider_message.lower()
    ):
        return "quota_error", provider_status, provider_message

    return "provider_error", provider_status, provider_message


def _string_or_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _sanitize_provider_message(message: object) -> str | None:
    if not isinstance(message, str):
        return None

    collapsed = " ".join(message.split())
    if not collapsed:
        return None

    redacted = re.sub(r"\bAIza[0-9A-Za-z_-]{20,}\b", "[redacted-api-key]", collapsed)
    if len(redacted) <= PROVIDER_MESSAGE_PREVIEW_MAX_CHARS:
        return redacted

    return f"{redacted[: PROVIDER_MESSAGE_PREVIEW_MAX_CHARS - 3]}..."
