from __future__ import annotations

from pathlib import Path

import yaml

from ops.canary.parse_canary import run_parse_canary
from ops.canary.search_canary import run_canary


def test_product_canary_passes_on_healthy_search_flow() -> None:
    requests: list[tuple[str, str, dict | None]] = []

    def request_json(
        method: str,
        path: str,
        payload: dict | None,
        _timeout_seconds: float,
    ) -> tuple[int, dict, float]:
        requests.append((method, path, payload))
        if path == "/api/healthz":
            return 200, {"status": "ok"}, 0.01
        if path == "/api/readyz":
            return 200, {"status": "ok"}, 0.02
        if path == "/api/search-readiness":
            return (
                200,
                {
                    "status": "degraded",
                    "checks": {"database": "ok", "catalog": "ok"},
                },
                0.03,
            )
        assert method == "POST"
        assert path == "/api/search"
        return (
            200,
            {
                "search_model_version": "search-v4",
                "ranking_policy_version": "search-v4.0.0",
                "ranking_status": "ranked",
                "results": [{"top_configuration": {"fit_score": 82.0}}],
            },
            3.0,
        )

    results = run_canary(
        base_url="https://example.test",
        latency_threshold_seconds=5.0,
        request_json=request_json,
    )

    assert all(result.passed for result in results)
    assert requests[-1][0:2] == ("POST", "/api/search")
    assert requests[-1][2] == {
        "intent": {
            "constraints": {
                "location": {"country": "France"},
                "travel_window": {"month": 3},
            },
            "party": {"skill_levels": ["intermediate"]},
            "travel_context": {"origin_text": "Berlin", "mode": "car"},
            "objectives": [{"factor_id": "pass_terrain_value", "importance": "normal"}],
        },
        "generate_refinements": False,
    }


def test_product_canary_fails_on_empty_representative_search() -> None:
    def request_json(
        _method: str,
        path: str,
        _payload: dict | None,
        _timeout_seconds: float,
    ) -> tuple[int, dict, float]:
        if path == "/api/healthz":
            return 200, {"status": "ok"}, 0.01
        if path == "/api/readyz":
            return 200, {"status": "ok"}, 0.02
        if path == "/api/search-readiness":
            return (
                200,
                {"status": "ok", "checks": {"database": "ok", "catalog": "ok"}},
                0.03,
            )
        assert path == "/api/search"
        return (
            200,
            {
                "search_model_version": "search-v4",
                "ranking_policy_version": "search-v4.0.0",
                "ranking_status": "ranked",
                "results": [],
            },
            2.0,
        )

    results = run_canary(
        base_url="https://example.test",
        latency_threshold_seconds=5.0,
        request_json=request_json,
    )

    assert not results[-1].passed
    assert results[-1].name == "representative-search"
    assert "results=0" in results[-1].message


def test_product_canary_fails_on_slow_representative_search() -> None:
    def request_json(
        _method: str,
        path: str,
        _payload: dict | None,
        _timeout_seconds: float,
    ) -> tuple[int, dict, float]:
        if path == "/api/healthz":
            return 200, {"status": "ok"}, 0.01
        if path == "/api/readyz":
            return 200, {"status": "ok"}, 0.02
        if path == "/api/search-readiness":
            return (
                200,
                {"status": "ok", "checks": {"database": "ok", "catalog": "ok"}},
                0.03,
            )
        assert path == "/api/search"
        return (
            200,
            {
                "search_model_version": "search-v4",
                "ranking_policy_version": "search-v4.0.0",
                "ranking_status": "ranked",
                "results": [{"top_configuration": {"fit_score": 82.0}}],
            },
            20.0,
        )

    results = run_canary(
        base_url="https://example.test",
        latency_threshold_seconds=5.0,
        request_json=request_json,
    )

    assert not results[-1].passed
    assert "threshold=5.0s" in results[-1].message


def test_parse_canary_passes_on_representative_parse() -> None:
    requests: list[tuple[str, dict]] = []

    def post_json(
        path: str,
        payload: dict,
        _timeout_seconds: float,
    ) -> tuple[int, dict, float]:
        requests.append((path, payload))
        return (
            200,
            {
                "filters": {"location": "France", "travel_month": 5},
                "trip_context": {"origin_text": "Prague"},
                "confidence": 0.93,
                "unknown_parts": [],
            },
            1.2,
        )

    results = run_parse_canary(
        base_url="https://example.test",
        post_json=post_json,
    )

    assert all(result.passed for result in results)
    assert requests == [
        (
            "/api/parse-query",
            {"query": "ski in france in may from prague"},
        )
    ]


def test_parse_canary_fails_on_unexpected_parse_shape() -> None:
    def post_json(
        _path: str,
        _payload: dict,
        _timeout_seconds: float,
    ) -> tuple[int, dict, float]:
        return (
            200,
            {
                "filters": {"location": "Austria", "travel_month": 5},
                "trip_context": {"origin_text": "Prague"},
            },
            1.0,
        )

    results = run_parse_canary(
        base_url="https://example.test",
        post_json=post_json,
    )

    assert not results[-1].passed
    assert results[-1].name == "representative-parse"
    assert "location=Austria" in results[-1].message


def test_product_canary_workflow_runs_every_six_hours() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/product-canary.yml").read_text(encoding="utf-8")
    )
    triggers = workflow["on"] if "on" in workflow else workflow[True]

    assert triggers["schedule"] == [{"cron": "17 */6 * * *"}]


def test_parse_canary_workflow_runs_daily() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/parse-canary.yml").read_text(encoding="utf-8")
    )
    triggers = workflow["on"] if "on" in workflow else workflow[True]

    assert triggers["schedule"] == [{"cron": "41 5 * * *"}]
    run_step = "\n".join(
        step.get("run", "")
        for step in workflow["jobs"]["parse-canary"]["steps"]
        if isinstance(step, dict)
    )
    assert "ops/canary/parse_canary.py" in run_step


def test_weather_forecast_refresh_workflow_runs_every_six_hours() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/refresh-weather-forecasts.yml").read_text(
            encoding="utf-8"
        )
    )
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    run_steps = "\n".join(
        step.get("run", "")
        for step in workflow["jobs"]["refresh"]["steps"]
        if isinstance(step, dict)
    )

    assert triggers["schedule"] == [{"cron": "25 */6 * * *"}]
    assert "app.data.refresh_weather_forecasts" in run_steps
    assert "--source" in run_steps
    assert "--ski-area" in run_steps


def test_weather_forecast_retention_workflow_runs_weekly() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/retain-weather-forecasts.yml").read_text(
            encoding="utf-8"
        )
    )
    triggers = workflow["on"] if "on" in workflow else workflow[True]
    run_steps = "\n".join(
        step.get("run", "")
        for step in workflow["jobs"]["retain"]["steps"]
        if isinstance(step, dict)
    )

    assert triggers["schedule"] == [{"cron": "40 3 * * 0"}]
    assert "app.data.retain_weather_forecasts" in run_steps
