from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from html import escape
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class PublicErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    AUTHENTICATION_REQUIRED = "authentication_required"
    SESSION_EXPIRED = "session_expired"
    SIGN_IN_FAILED = "sign_in_failed"
    SIGN_IN_UNAVAILABLE = "sign_in_unavailable"
    SEARCH_REQUEST_INVALID = "search_request_invalid"
    WEATHER_AREA_NOT_FOUND = "weather_area_not_found"
    REFINEMENT_RATE_LIMITED = "refinement_rate_limited"
    TRIP_OPTION_INVALID = "trip_option_invalid"
    CURRENT_TRIP_NOT_FOUND = "current_trip_not_found"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    REQUEST_FAILED = "request_failed"


_STATUS_BY_CODE: dict[PublicErrorCode, int] = {
    PublicErrorCode.INVALID_REQUEST: 422,
    PublicErrorCode.AUTHENTICATION_REQUIRED: 401,
    PublicErrorCode.SESSION_EXPIRED: 401,
    PublicErrorCode.SIGN_IN_FAILED: 401,
    PublicErrorCode.SIGN_IN_UNAVAILABLE: 503,
    PublicErrorCode.SEARCH_REQUEST_INVALID: 422,
    PublicErrorCode.WEATHER_AREA_NOT_FOUND: 422,
    PublicErrorCode.REFINEMENT_RATE_LIMITED: 429,
    PublicErrorCode.TRIP_OPTION_INVALID: 422,
    PublicErrorCode.CURRENT_TRIP_NOT_FOUND: 404,
    PublicErrorCode.NOT_FOUND: 404,
    PublicErrorCode.METHOD_NOT_ALLOWED: 405,
    PublicErrorCode.REQUEST_FAILED: 500,
}

_OPERATIONAL_PATHS = {
    "/api/healthz",
    "/api/readyz",
    "/api/search-readiness",
}
_ACCOMMODATION_PATH_ROOT = "/api/outbound/accommodation"


class PublicError(BaseModel):
    code: PublicErrorCode


class PublicErrorResponse(BaseModel):
    error: PublicError


class PublicApiError(Exception):
    def __init__(
        self,
        code: PublicErrorCode,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(code.value)
        self.code = code
        self.headers = dict(headers) if headers is not None else None


def public_error_status(code: PublicErrorCode) -> int:
    return _STATUS_BY_CODE[code]


def public_error_response(
    code: PublicErrorCode,
    *,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=public_error_status(code),
        content={"error": {"code": code.value}},
        headers=headers,
    )


def public_error_responses(
    *status_codes: int,
    descriptions: Mapping[int, str] | None = None,
    headers: Mapping[int, dict[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    descriptions = descriptions or {}
    headers = headers or {}
    responses: dict[int, dict[str, Any]] = {}
    for status_code in status_codes:
        response: dict[str, Any] = {
            "model": PublicErrorResponse,
            "description": descriptions.get(status_code, "Public API error"),
        }
        if status_code in headers:
            response["headers"] = headers[status_code]
        responses[status_code] = response
    return responses


def is_customer_api_path(path: str) -> bool:
    return (
        (path == "/api" or path.startswith("/api/"))
        and path not in _OPERATIONAL_PATHS
        and not is_accommodation_path(path)
    )


def is_accommodation_path(path: str) -> bool:
    return path == _ACCOMMODATION_PATH_ROOT or path.startswith(
        f"{_ACCOMMODATION_PATH_ROOT}/"
    )


def install_public_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(PublicApiError, _public_api_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)


def branded_html_response(
    *,
    status_code: int,
    title: str,
    heading: str,
    explanation: str,
    return_href: str,
    return_label: str,
    headers: Mapping[str, str] | None = None,
) -> HTMLResponse:
    safe_title = escape(title)
    safe_heading = escape(heading)
    safe_explanation = escape(explanation)
    safe_return_href = escape(return_href, quote=True)
    safe_return_label = escape(return_label)
    return HTMLResponse(
        status_code=status_code,
        headers=headers,
        content=f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_title} | Snowcast</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #f5f9fc;
        color: #0a1f3d;
      }}
      main {{
        width: min(32rem, calc(100% - 3rem));
        padding: 2rem;
        border: 1px solid #cbd9e8;
        border-radius: 8px;
        background: white;
      }}
      p {{ color: #4c6079; line-height: 1.6; }}
      a {{
        display: inline-block;
        margin-top: 0.75rem;
        color: #075fc6;
        font-weight: 700;
      }}
    </style>
  </head>
  <body>
    <main>
      <p>SNOWCAST</p>
      <h1>{safe_heading}</h1>
      <p>{safe_explanation}</p>
      <a href="{safe_return_href}">{safe_return_label}</a>
    </main>
  </body>
</html>""",
    )


def accommodation_recovery_response(
    request: Request,
    *,
    status_code: int,
    headers: Mapping[str, str] | None = None,
) -> HTMLResponse:
    return_href = _same_origin_trip_details_href(request)
    return branded_html_response(
        status_code=status_code,
        title="Trip option unavailable",
        heading="This trip option is no longer available",
        explanation=(
            "The trip details may have changed. Return to Snowcast and choose the "
            "trip option again."
        ),
        return_href=return_href or "/",
        return_label="Return to trip details" if return_href else "Return to Snowcast",
        headers=headers,
    )


async def _public_api_error_handler(
    _request: Request,
    error: PublicApiError,
) -> JSONResponse:
    return public_error_response(error.code, headers=error.headers)


async def _validation_error_handler(
    request: Request,
    error: RequestValidationError,
):
    if is_accommodation_path(request.url.path):
        return accommodation_recovery_response(request, status_code=422)
    if is_customer_api_path(request.url.path):
        return public_error_response(PublicErrorCode.INVALID_REQUEST)
    return await request_validation_exception_handler(request, error)


async def _http_error_handler(request: Request, error: StarletteHTTPException):
    if is_accommodation_path(request.url.path):
        return accommodation_recovery_response(
            request,
            status_code=error.status_code,
            headers=error.headers,
        )
    if is_customer_api_path(request.url.path):
        return public_error_response(
            _residual_http_error_code(error.status_code),
            headers=error.headers,
        )
    return await http_exception_handler(request, error)


async def _unexpected_error_handler(request: Request, _error: Exception):
    if is_customer_api_path(request.url.path):
        return public_error_response(PublicErrorCode.REQUEST_FAILED)
    return PlainTextResponse("Internal Server Error", status_code=500)


def _residual_http_error_code(status_code: int) -> PublicErrorCode:
    return {
        401: PublicErrorCode.AUTHENTICATION_REQUIRED,
        404: PublicErrorCode.NOT_FOUND,
        405: PublicErrorCode.METHOD_NOT_ALLOWED,
        422: PublicErrorCode.INVALID_REQUEST,
        429: PublicErrorCode.REFINEMENT_RATE_LIMITED,
        500: PublicErrorCode.REQUEST_FAILED,
        503: PublicErrorCode.SIGN_IN_UNAVAILABLE,
    }.get(status_code, PublicErrorCode.REQUEST_FAILED)


def _same_origin_trip_details_href(request: Request) -> str | None:
    referer = request.headers.get("referer")
    if not referer:
        return None
    parsed = urlsplit(referer)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != request.url.netloc:
        return None
    if not parsed.path.startswith("/recommendations/"):
        return None
    return parsed.path + (f"?{parsed.query}" if parsed.query else "")
