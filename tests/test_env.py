import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from app.ai.gemini_client import GeminiClient
from app.ai.llm_client import LLMClientError
from app.config import env as env_module


class StubHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_gemini_client_loads_api_key_and_model_from_dotenv(
    tmp_path, monkeypatch
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "GEMINI_API_KEY=test-key\nGEMINI_MODEL=test-model\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(env_module, "ENV_PATH", dotenv_path)
    monkeypatch.setattr(env_module, "_loaded", False)

    client = GeminiClient()

    assert client.api_key == "test-key"
    assert client.model == "test-model"


def test_dotenv_does_not_override_existing_environment(tmp_path, monkeypatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "GEMINI_API_KEY=file-key\nGEMINI_MODEL=file-model\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    monkeypatch.setenv("GEMINI_MODEL", "env-model")
    monkeypatch.setattr(env_module, "ENV_PATH", dotenv_path)
    monkeypatch.setattr(env_module, "_loaded", False)

    client = GeminiClient()

    assert client.api_key == "env-key"
    assert client.model == "env-model"


def test_gemini_client_returns_text_from_valid_response(monkeypatch) -> None:
    client = GeminiClient(api_key="test-key", model="gemini-2.5-flash")

    def fake_urlopen(request, timeout=20):
        return StubHTTPResponse(
            json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": '{"filters":{"location":"France"}}'}]
                            }
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("app.ai.gemini_client.urlopen", fake_urlopen)

    content = client.complete(
        system_prompt="Reply with JSON",
        user_prompt="test",
        temperature=0,
        response_mime_type="application/json",
        response_json_schema={"type": "object"},
    )

    assert content == '{"filters":{"location":"France"}}'


def test_gemini_client_sends_response_schema_and_mime_type(monkeypatch) -> None:
    client = GeminiClient(api_key="test-key", model="gemini-2.5-flash")
    captured_request = {}

    def fake_urlopen(request, timeout=20):
        captured_request["payload"] = json.loads(request.data.decode("utf-8"))
        return StubHTTPResponse(
            json.dumps(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": '{"recommendation_narrative":"ok"}'}]
                            }
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("app.ai.gemini_client.urlopen", fake_urlopen)

    client.complete(
        system_prompt="Reply with JSON",
        user_prompt="test",
        temperature=0,
        response_mime_type="application/json",
        response_json_schema={"type": "object", "required": ["foo"]},
    )

    generation_config = captured_request["payload"]["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert generation_config["responseJsonSchema"] == {
        "type": "object",
        "required": ["foo"],
    }


@pytest.mark.parametrize(
    ("error", "expected_reason"),
    [
        (
            HTTPError(
                url="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=BytesIO(b'{"error":{"message":"bad key"}}'),
            ),
            "auth_error",
        ),
        (
            HTTPError(
                url="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                code=429,
                msg="Too Many Requests",
                hdrs=None,
                fp=BytesIO(
                    json.dumps(
                        {
                            "error": {
                                "message": "quota exceeded",
                                "status": "RESOURCE_EXHAUSTED",
                            }
                        }
                    ).encode("utf-8")
                ),
            ),
            "quota_error",
        ),
    ],
)
def test_gemini_client_classifies_http_errors(
    monkeypatch, error, expected_reason
) -> None:
    client = GeminiClient(api_key="test-key", model="gemini-2.5-flash")

    def raise_error(request, timeout=20):
        raise error

    monkeypatch.setattr("app.ai.gemini_client.urlopen", raise_error)

    with pytest.raises(LLMClientError) as raised:
        client.complete(
            system_prompt="Reply with ok",
            user_prompt="test",
            temperature=0,
        )

    assert raised.value.reason == expected_reason


def test_gemini_client_marks_malformed_response_as_provider_error(
    monkeypatch,
) -> None:
    client = GeminiClient(api_key="test-key", model="gemini-2.5-flash")

    def fake_urlopen(request, timeout=20):
        return StubHTTPResponse(json.dumps({"candidates": []}).encode("utf-8"))

    monkeypatch.setattr("app.ai.gemini_client.urlopen", fake_urlopen)

    with pytest.raises(LLMClientError) as raised:
        client.complete(
            system_prompt="Reply with ok",
            user_prompt="test",
            temperature=0,
        )

    assert raised.value.reason == "provider_error"


def test_gemini_client_classifies_network_error(monkeypatch) -> None:
    client = GeminiClient(api_key="test-key", model="gemini-2.5-flash")

    def raise_error(request, timeout=20):
        raise URLError("network down")

    monkeypatch.setattr("app.ai.gemini_client.urlopen", raise_error)

    with pytest.raises(LLMClientError) as raised:
        client.complete(
            system_prompt="Reply with ok",
            user_prompt="test",
            temperature=0,
        )

    assert raised.value.reason == "network_error"
