from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ops.canary.search_canary import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    CanaryResult,
)

DEFAULT_PARSE_QUERY = "ski in france in may from prague"

JsonPayload = dict[str, Any]
PostJson = Callable[[str, JsonPayload, float], tuple[int, JsonPayload, float]]


def run_parse_canary(
    *,
    base_url: str,
    query: str = DEFAULT_PARSE_QUERY,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    post_json: PostJson | None = None,
) -> list[CanaryResult]:
    normalized_base_url = base_url.rstrip("/")
    post = post_json or _urlopen_post_json(normalized_base_url)

    return [
        _check_representative_parse(
            post,
            query=query,
            timeout_seconds=timeout_seconds,
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Snowcast parse canary.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SNOWCAST_BASE_URL", DEFAULT_BASE_URL),
        help="Snowcast base URL. Defaults to SNOWCAST_BASE_URL or production.",
    )
    parser.add_argument(
        "--query",
        default=os.getenv("SNOWCAST_PARSE_CANARY_QUERY", DEFAULT_PARSE_QUERY),
        help="Representative free-text query to parse.",
    )
    parser.add_argument(
        "--timeout-seconds",
        default=DEFAULT_TIMEOUT_SECONDS,
        type=float,
        help="HTTP timeout for the parse canary request.",
    )
    args = parser.parse_args()

    results = run_parse_canary(
        base_url=args.base_url,
        query=args.query,
        timeout_seconds=args.timeout_seconds,
    )
    for result in results:
        status = "OK" if result.passed else "FAIL"
        print(
            f"[{status}] {result.name}: {result.message} "
            f"({result.duration_seconds:.2f}s)"
        )
    raise SystemExit(0 if all(result.passed for result in results) else 1)


def _check_representative_parse(
    post: PostJson,
    *,
    query: str,
    timeout_seconds: float,
) -> CanaryResult:
    status_code, payload, duration_seconds = post(
        "/api/parse-query",
        {"query": query},
        timeout_seconds,
    )
    filters = payload.get("filters")
    trip_context = payload.get("trip_context")
    location = filters.get("location") if isinstance(filters, dict) else None
    travel_month = filters.get("travel_month") if isinstance(filters, dict) else None
    origin = trip_context.get("origin_text") if isinstance(trip_context, dict) else None
    confidence = payload.get("confidence")
    passed = (
        status_code == 200
        and _normalized_text(location) == "france"
        and travel_month == 5
        and _normalized_text(origin) == "prague"
        and isinstance(confidence, int | float)
    )
    message = (
        f"status_code={status_code} location={location} "
        f"travel_month={travel_month} origin={origin} confidence={confidence}"
    )
    return CanaryResult(
        name="representative-parse",
        passed=passed,
        message=message,
        duration_seconds=duration_seconds,
    )


def _normalized_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().casefold()


def _urlopen_post_json(base_url: str) -> PostJson:
    def _post(
        path: str,
        payload: JsonPayload,
        timeout_seconds: float,
    ) -> tuple[int, JsonPayload, float]:
        url = f"{base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                duration_seconds = time.perf_counter() - started
                response_body = response.read().decode("utf-8")
                response_payload = json.loads(response_body) if response_body else {}
                return response.status, response_payload, duration_seconds
        except HTTPError as error:
            duration_seconds = time.perf_counter() - started
            response_body = error.read().decode("utf-8")
            try:
                response_payload = json.loads(response_body) if response_body else {}
            except json.JSONDecodeError:
                response_payload = {"error": response_body}
            return error.code, response_payload, duration_seconds
        except (URLError, TimeoutError) as error:
            duration_seconds = time.perf_counter() - started
            return 0, {"error": str(error)}, duration_seconds

    return _post


if __name__ == "__main__":
    main()
