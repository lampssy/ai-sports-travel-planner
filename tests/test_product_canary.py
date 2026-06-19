from __future__ import annotations

from ops.canary.search_canary import run_canary


def test_product_canary_passes_on_healthy_search_flow() -> None:
    def fetch_json(path: str, _timeout_seconds: float) -> tuple[int, dict, float]:
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
        assert path.startswith("/api/search?")
        return 200, {"results": [{"resort_id": "tignes"}]}, 3.0

    results = run_canary(
        base_url="https://example.test",
        latency_threshold_seconds=5.0,
        fetch_json=fetch_json,
    )

    assert all(result.passed for result in results)


def test_product_canary_fails_on_empty_representative_search() -> None:
    def fetch_json(path: str, _timeout_seconds: float) -> tuple[int, dict, float]:
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
        assert path.startswith("/api/search?")
        return 200, {"results": []}, 2.0

    results = run_canary(
        base_url="https://example.test",
        latency_threshold_seconds=5.0,
        fetch_json=fetch_json,
    )

    assert not results[-1].passed
    assert results[-1].name == "representative-search"
    assert "results=0" in results[-1].message


def test_product_canary_fails_on_slow_representative_search() -> None:
    def fetch_json(path: str, _timeout_seconds: float) -> tuple[int, dict, float]:
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
        assert path.startswith("/api/search?")
        return 200, {"results": [{"resort_id": "tignes"}]}, 20.0

    results = run_canary(
        base_url="https://example.test",
        latency_threshold_seconds=5.0,
        fetch_json=fetch_json,
    )

    assert not results[-1].passed
    assert "threshold=5.0s" in results[-1].message
