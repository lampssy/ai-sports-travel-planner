from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace

from app.observability.context import current_request_id

SENSITIVE_LOG_FIELDS = {
    "authorization",
    "identity_token",
    "access_token",
    "refresh_token",
    "token",
    "api_key",
    "password",
    "query",
    "prompt",
    "raw_response",
    "user_prompt",
    "system_prompt",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in _STANDARD_LOG_RECORD_FIELDS:
                continue
            if key.lower() in SENSITIVE_LOG_FIELDS:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                payload[key] = value
        payload.setdefault("request_id", current_request_id())
        trace_id = _current_trace_id()
        if trace_id:
            payload.setdefault("trace_id", trace_id)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging() -> None:
    root = logging.getLogger()
    level = os.getenv("LOG_LEVEL", "INFO")
    if os.getenv("LOG_FORMAT", "text").strip().lower() == "json":
        _configure_json_logging(root, level)
        return
    if root.handlers:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def safe_log_extra(extra: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in extra.items()
        if key.lower() not in SENSITIVE_LOG_FIELDS
        and (isinstance(value, (str, int, float, bool)) or value is None)
    }


def _configure_json_logging(root: logging.Logger, level: str) -> None:
    for handler in root.handlers:
        if isinstance(handler.formatter, JsonLogFormatter):
            root.setLevel(level)
            return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root.handlers = [handler]
    root.setLevel(level)


def _current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return f"{span_context.trace_id:032x}"


_STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}
