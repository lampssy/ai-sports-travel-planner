from __future__ import annotations

import hashlib
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

import httpx

_IGNORED_TAGS = {"script", "style", "noscript"}
_WHITESPACE_RE = re.compile(r"\s+")
_USER_AGENT = "SnowcastCatalogAcquisition/1.0"
_SUPPORTED_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}
_TRANSPORT_RETRY_DELAYS_SECONDS = (0.25, 1.0)
_HTTP_STATUS_RETRY_DELAYS_SECONDS = (1.0, 4.0, 12.0)
_HTTP_STATUS_RETRY_JITTER_RATIO = 0.2
_MAX_HTTP_RETRY_DELAY_SECONDS = 30.0
_TRANSIENT_HTTP_STATUS_CODES = {429, 502, 503, 504}


@dataclass(frozen=True)
class FetchedPage:
    url: str
    final_url: str
    status_code: int | None
    fetched_at: datetime
    text: str
    content_hash: str | None
    truncated: bool
    error: str | None = None


@dataclass(frozen=True)
class FetchedHtmlDocument:
    url: str
    final_url: str
    status_code: int
    fetched_at: datetime
    raw_html: str
    visible_text: str
    content_hash: str
    truncated: bool


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _IGNORED_TAGS:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._parts.append(data)

    def text(self) -> str:
        return _WHITESPACE_RE.sub(" ", " ".join(self._parts)).strip()


def html_to_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    return parser.text()


def stable_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_with_transport_retries(
    client: httpx.Client,
    url: str,
    *,
    headers: dict[str, str],
) -> httpx.Response:
    max_retry_count = max(
        len(_TRANSPORT_RETRY_DELAYS_SECONDS),
        len(_HTTP_STATUS_RETRY_DELAYS_SECONDS),
    )
    for attempt_index in range(max_retry_count + 1):
        try:
            response = client.get(url, headers=headers)
            if (
                response.status_code in _TRANSIENT_HTTP_STATUS_CODES
                and attempt_index < len(_HTTP_STATUS_RETRY_DELAYS_SECONDS)
            ):
                delay_seconds = _http_status_retry_delay_seconds(
                    response,
                    attempt_index,
                )
                response.close()
                time.sleep(delay_seconds)
                continue
            return response
        except httpx.TransportError:
            if attempt_index >= len(_TRANSPORT_RETRY_DELAYS_SECONDS):
                raise
            time.sleep(_TRANSPORT_RETRY_DELAYS_SECONDS[attempt_index])

    raise RuntimeError("unreachable transport retry state")


def _http_status_retry_delay_seconds(
    response: httpx.Response,
    attempt_index: int,
) -> float:
    if response.status_code == 429:
        retry_after_seconds = _retry_after_delay_seconds(
            response.headers.get("retry-after"),
        )
        if retry_after_seconds is not None:
            return min(retry_after_seconds, _MAX_HTTP_RETRY_DELAY_SECONDS)

    base_delay = _HTTP_STATUS_RETRY_DELAYS_SECONDS[attempt_index]
    jitter = random.uniform(0.0, base_delay * _HTTP_STATUS_RETRY_JITTER_RATIO)
    return min(base_delay + jitter, _MAX_HTTP_RETRY_DELAY_SECONDS)


def _retry_after_delay_seconds(header_value: str | None) -> float | None:
    if header_value is None or not header_value.strip():
        return None

    stripped_value = header_value.strip()
    try:
        delay_seconds = float(stripped_value)
    except ValueError:
        delay_seconds = _retry_after_http_date_delay_seconds(stripped_value)
    if delay_seconds is None:
        return None
    return max(0.0, delay_seconds)


def _retry_after_http_date_delay_seconds(header_value: str) -> float | None:
    try:
        retry_at = parsedate_to_datetime(header_value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return (retry_at - datetime.now(timezone.utc)).total_seconds()


def _error_page(
    *,
    url: str,
    final_url: str,
    status_code: int | None,
    fetched_at: datetime,
    error: str,
) -> FetchedPage:
    return FetchedPage(
        url=url,
        final_url=final_url,
        status_code=status_code,
        fetched_at=fetched_at,
        text="",
        content_hash=None,
        truncated=False,
        error=error,
    )


def _normalized_content_type(response: httpx.Response) -> str | None:
    content_type = response.headers.get("content-type")
    if content_type is None:
        return None
    return content_type.split(";", maxsplit=1)[0].strip().lower()


def fetch_url(
    url: str,
    max_chars: int = 30000,
    timeout_seconds: float = 15.0,
    max_bytes: int = 1_000_000,
) -> FetchedPage:
    fetched_at = datetime.now(timezone.utc)
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = get_with_transport_retries(
                client,
                url,
                headers={"User-Agent": _USER_AGENT},
            )
            response.raise_for_status()
    except httpx.HTTPError as error:
        response = error.response if isinstance(error, httpx.HTTPStatusError) else None
        return _error_page(
            url=url,
            final_url=str(response.url) if response is not None else url,
            status_code=response.status_code if response is not None else None,
            fetched_at=fetched_at,
            error=str(error),
        )

    content_type = _normalized_content_type(response)
    if content_type is not None and content_type not in _SUPPORTED_CONTENT_TYPES:
        return _error_page(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            fetched_at=fetched_at,
            error=f"Unsupported content type: {content_type}",
        )

    content_length = len(response.content)
    if content_length > max_bytes:
        return _error_page(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            fetched_at=fetched_at,
            error=f"Response too large: {content_length} bytes",
        )

    full_text = html_to_text(response.text)
    truncated = len(full_text) > max_chars
    return FetchedPage(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        fetched_at=fetched_at,
        text=full_text[:max_chars] if truncated else full_text,
        content_hash=stable_content_hash(full_text),
        truncated=truncated,
    )


def fetch_html_document(
    url: str,
    *,
    timeout_seconds: float = 15.0,
    max_bytes: int = 1_000_000,
) -> FetchedHtmlDocument:
    fetched_at = datetime.now(timezone.utc)
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        response = get_with_transport_retries(
            client,
            url,
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()

    content_type = _normalized_content_type(response)
    supported_html_types = {
        "text/html",
        "application/xhtml+xml",
        "application/xml",
        "text/xml",
    }
    if content_type is not None and content_type not in supported_html_types:
        raise ValueError(f"Unsupported content type: {content_type}")

    content = response.content
    truncated = len(content) > max_bytes
    capped_content = content[:max_bytes] if truncated else content
    encoding = response.encoding or "utf-8"
    raw_html = capped_content.decode(encoding, errors="replace")

    return FetchedHtmlDocument(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        fetched_at=fetched_at,
        raw_html=raw_html,
        visible_text=html_to_text(raw_html),
        content_hash=stable_content_hash(raw_html),
        truncated=truncated,
    )
