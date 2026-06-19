from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://snowcast.fly.dev"
DEFAULT_LATENCY_THRESHOLD_SECONDS = 15.0
DEFAULT_TIMEOUT_SECONDS = 30.0

JsonPayload = dict[str, Any]
FetchJson = Callable[[str, float], tuple[int, JsonPayload, float]]


@dataclass(frozen=True)
class CanaryResult:
    name: str
    passed: bool
    message: str
    duration_seconds: float


def run_canary(
    *,
    base_url: str,
    latency_threshold_seconds: float = DEFAULT_LATENCY_THRESHOLD_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    fetch_json: FetchJson | None = None,
) -> list[CanaryResult]:
    normalized_base_url = base_url.rstrip("/")
    fetch = fetch_json or _urlopen_fetch_json(normalized_base_url)

    results = [
        _check_status(fetch, "health", "/api/healthz", timeout_seconds),
        _check_status(fetch, "ready", "/api/readyz", timeout_seconds),
        _check_search_readiness(fetch, timeout_seconds),
        _check_search(
            fetch,
            timeout_seconds=timeout_seconds,
            latency_threshold_seconds=latency_threshold_seconds,
        ),
    ]
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Snowcast product canary.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SNOWCAST_BASE_URL", DEFAULT_BASE_URL),
        help="Snowcast base URL. Defaults to SNOWCAST_BASE_URL or production.",
    )
    parser.add_argument(
        "--latency-threshold-seconds",
        default=DEFAULT_LATENCY_THRESHOLD_SECONDS,
        type=float,
        help="Fail when the representative search takes longer than this value.",
    )
    parser.add_argument(
        "--timeout-seconds",
        default=DEFAULT_TIMEOUT_SECONDS,
        type=float,
        help="HTTP timeout for each canary request.",
    )
    args = parser.parse_args()

    results = run_canary(
        base_url=args.base_url,
        latency_threshold_seconds=args.latency_threshold_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    for result in results:
        status = "OK" if result.passed else "FAIL"
        print(
            f"[{status}] {result.name}: {result.message} "
            f"({result.duration_seconds:.2f}s)"
        )
    raise SystemExit(0 if all(result.passed for result in results) else 1)


def _check_status(
    fetch: FetchJson,
    name: str,
    path: str,
    timeout_seconds: float,
) -> CanaryResult:
    status_code, payload, duration_seconds = fetch(path, timeout_seconds)
    passed = status_code == 200 and payload.get("status") == "ok"
    message = f"status_code={status_code} status={payload.get('status')}"
    return CanaryResult(
        name=name,
        passed=passed,
        message=message,
        duration_seconds=duration_seconds,
    )


def _check_search_readiness(
    fetch: FetchJson,
    timeout_seconds: float,
) -> CanaryResult:
    status_code, payload, duration_seconds = fetch(
        "/api/search-readiness",
        timeout_seconds,
    )
    status = payload.get("status")
    checks = payload.get("checks", {})
    passed = (
        status_code == 200
        and status in {"ok", "degraded"}
        and isinstance(checks, dict)
        and checks.get("database") == "ok"
        and checks.get("catalog") == "ok"
    )
    message = f"status_code={status_code} status={status}"
    return CanaryResult(
        name="search-readiness",
        passed=passed,
        message=message,
        duration_seconds=duration_seconds,
    )


def _check_search(
    fetch: FetchJson,
    *,
    timeout_seconds: float,
    latency_threshold_seconds: float,
) -> CanaryResult:
    query = urlencode(
        {
            "location": "France",
            "min_price": 150,
            "max_price": 320,
            "stars": 1,
            "skill_level": "intermediate",
            "travel_month": 3,
            "origin_text": "Berlin",
        }
    )
    status_code, payload, duration_seconds = fetch(
        f"/api/search?{query}",
        timeout_seconds,
    )
    raw_results = payload.get("results")
    result_count = len(raw_results) if isinstance(raw_results, list) else 0
    passed = (
        status_code == 200
        and result_count > 0
        and duration_seconds <= latency_threshold_seconds
    )
    message = (
        f"status_code={status_code} results={result_count} "
        f"threshold={latency_threshold_seconds:.1f}s"
    )
    return CanaryResult(
        name="representative-search",
        passed=passed,
        message=message,
        duration_seconds=duration_seconds,
    )


def _urlopen_fetch_json(base_url: str) -> FetchJson:
    def _fetch(path: str, timeout_seconds: float) -> tuple[int, JsonPayload, float]:
        url = f"{base_url}{path}"
        request = Request(url, headers={"Accept": "application/json"}, method="GET")
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                duration_seconds = time.perf_counter() - started
                body = response.read().decode("utf-8")
                payload = json.loads(body) if body else {}
                return response.status, payload, duration_seconds
        except HTTPError as error:
            duration_seconds = time.perf_counter() - started
            body = error.read().decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = {"error": body}
            return error.code, payload, duration_seconds
        except (URLError, TimeoutError) as error:
            duration_seconds = time.perf_counter() - started
            return 0, {"error": str(error)}, duration_seconds

    return _fetch


if __name__ == "__main__":
    main()
