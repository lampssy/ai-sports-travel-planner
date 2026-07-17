from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://snowcast.fly.dev"
DEFAULT_LATENCY_THRESHOLD_SECONDS = 15.0
DEFAULT_REFINEMENT_LATENCY_THRESHOLD_SECONDS = 6.0
DEFAULT_TIMEOUT_SECONDS = 30.0

JsonPayload = dict[str, Any]
RequestJson = Callable[
    [str, str, JsonPayload | None, float],
    tuple[int, JsonPayload, float],
]


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
    refinement_latency_threshold_seconds: float = (
        DEFAULT_REFINEMENT_LATENCY_THRESHOLD_SECONDS
    ),
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    request_json: RequestJson | None = None,
) -> list[CanaryResult]:
    normalized_base_url = base_url.rstrip("/")
    request = request_json or _urlopen_request_json(normalized_base_url)

    results = [
        _check_status(request, "health", "/api/healthz", timeout_seconds),
        _check_status(request, "ready", "/api/readyz", timeout_seconds),
        _check_search_readiness(request, timeout_seconds),
    ]
    search_result, search_payload = _check_search(
        request,
        timeout_seconds=timeout_seconds,
        latency_threshold_seconds=latency_threshold_seconds,
    )
    results.append(search_result)
    if search_result.passed:
        refinement_result, retry_handoff = _check_refinements(
            request,
            search_payload=search_payload,
            timeout_seconds=timeout_seconds,
            latency_threshold_seconds=refinement_latency_threshold_seconds,
        )
        if retry_handoff:
            retry_search_result, retry_search_payload = _check_search(
                request,
                timeout_seconds=timeout_seconds,
                latency_threshold_seconds=latency_threshold_seconds,
            )
            results.append(retry_search_result)
            if retry_search_result.passed:
                refinement_result, _ = _check_refinements(
                    request,
                    search_payload=retry_search_payload,
                    timeout_seconds=timeout_seconds,
                    latency_threshold_seconds=(refinement_latency_threshold_seconds),
                )
        results.append(refinement_result)
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
        "--refinement-latency-threshold-seconds",
        default=DEFAULT_REFINEMENT_LATENCY_THRESHOLD_SECONDS,
        type=float,
        help="Fail when post-search refinement takes longer than this value.",
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
        refinement_latency_threshold_seconds=(
            args.refinement_latency_threshold_seconds
        ),
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
    request: RequestJson,
    name: str,
    path: str,
    timeout_seconds: float,
) -> CanaryResult:
    status_code, payload, duration_seconds = request("GET", path, None, timeout_seconds)
    passed = status_code == 200 and payload.get("status") == "ok"
    message = f"status_code={status_code} status={payload.get('status')}"
    return CanaryResult(
        name=name,
        passed=passed,
        message=message,
        duration_seconds=duration_seconds,
    )


def _check_search_readiness(
    request: RequestJson,
    timeout_seconds: float,
) -> CanaryResult:
    status_code, payload, duration_seconds = request(
        "GET",
        "/api/search-readiness",
        None,
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
    request: RequestJson,
    *,
    timeout_seconds: float,
    latency_threshold_seconds: float,
) -> tuple[CanaryResult, JsonPayload]:
    request_payload: JsonPayload = {
        "intent": {
            "constraints": {
                "location": {"country": "France"},
                "travel_window": {"month": 3},
            },
            "party": {"skill_levels": ["intermediate"]},
            "travel_context": {"origin_text": "Berlin", "mode": "car"},
            "objectives": [{"factor_id": "pass_terrain_value", "importance": "normal"}],
        },
    }
    status_code, payload, duration_seconds = request(
        "POST",
        "/api/search",
        request_payload,
        timeout_seconds,
    )
    raw_results = payload.get("results")
    result_count = len(raw_results) if isinstance(raw_results, list) else 0
    ranking_status = payload.get("ranking_status")
    top_configuration = (
        raw_results[0].get("top_configuration")
        if result_count and isinstance(raw_results[0], dict)
        else None
    )
    fit_shape_ok = False
    if isinstance(top_configuration, dict):
        fit_score = top_configuration.get("fit_score")
        fit_shape_ok = (
            isinstance(fit_score, (int, float))
            if ranking_status == "ranked"
            else fit_score is None
        )
    passed = (
        status_code == 200
        and result_count > 0
        and payload.get("search_model_version") == "search-v4"
        and isinstance(payload.get("ranking_policy_version"), str)
        and bool(payload.get("ranking_policy_version"))
        and ranking_status in {"ranked", "unscored"}
        and fit_shape_ok
        and duration_seconds <= latency_threshold_seconds
    )
    message = (
        f"status_code={status_code} results={result_count} "
        f"model={payload.get('search_model_version')} "
        f"ranking_status={ranking_status} "
        f"threshold={latency_threshold_seconds:.1f}s"
    )
    return (
        CanaryResult(
            name="representative-search",
            passed=passed,
            message=message,
            duration_seconds=duration_seconds,
        ),
        payload,
    )


def _check_refinements(
    request: RequestJson,
    *,
    search_payload: JsonPayload,
    timeout_seconds: float,
    latency_threshold_seconds: float,
) -> tuple[CanaryResult, bool]:
    applied_intent = search_payload.get("applied_intent")
    baseline_fingerprint = search_payload.get("baseline_fingerprint")
    ranking_policy_version = search_payload.get("ranking_policy_version")
    if not isinstance(applied_intent, dict) or not isinstance(
        baseline_fingerprint, str
    ):
        return (
            CanaryResult(
                name="representative-refinement",
                passed=False,
                message="ranking response omitted refinement baseline fields",
                duration_seconds=0.0,
            ),
            False,
        )

    status_code, payload, duration_seconds = request(
        "POST",
        "/api/search/refinements",
        {
            "intent": applied_intent,
            "brief": "Product canary representative search",
            "baseline_fingerprint": baseline_fingerprint,
            "already_answered_question_ids": [],
        },
        timeout_seconds,
    )
    status = payload.get("refinement_status")
    baseline_status = payload.get("baseline_status")
    refinements = payload.get("refinements")
    question_count = len(refinements) if isinstance(refinements, list) else -1
    status_shape_ok = (status == "questions_available" and question_count > 0) or (
        status in {"not_needed", "temporarily_unavailable"} and question_count == 0
    )
    passed = (
        status_code == 200
        and payload.get("search_model_version") == "search-v4"
        and payload.get("ranking_policy_version") == ranking_policy_version
        and payload.get("baseline_fingerprint") == baseline_fingerprint
        and baseline_status == "current"
        and isinstance(payload.get("fallback_used"), bool)
        and status_shape_ok
        and duration_seconds <= latency_threshold_seconds
    )
    retry_handoff = (
        status_code == 200
        and payload.get("search_model_version") == "search-v4"
        and payload.get("ranking_policy_version") == ranking_policy_version
        and payload.get("baseline_fingerprint") == baseline_fingerprint
        and status == "temporarily_unavailable"
        and baseline_status in {"stale", "unverified"}
        and isinstance(payload.get("fallback_used"), bool)
        and question_count == 0
        and duration_seconds <= latency_threshold_seconds
    )
    message = (
        f"status_code={status_code} status={status} baseline={baseline_status} "
        f"questions={question_count} "
        f"threshold={latency_threshold_seconds:.1f}s"
    )
    return (
        CanaryResult(
            name="representative-refinement",
            passed=passed,
            message=message,
            duration_seconds=duration_seconds,
        ),
        retry_handoff,
    )


def _urlopen_request_json(base_url: str) -> RequestJson:
    def _request(
        method: str,
        path: str,
        payload: JsonPayload | None,
        timeout_seconds: float,
    ) -> tuple[int, JsonPayload, float]:
        url = f"{base_url}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=headers, method=method)
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

    return _request


if __name__ == "__main__":
    main()
