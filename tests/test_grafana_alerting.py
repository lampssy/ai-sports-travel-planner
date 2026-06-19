from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ops.grafana.scripts.alerting_resources import (
    AlertingValidationError,
    GrafanaAlertingClient,
    deploy_from_manifest,
    load_json,
    validate_alert_rules,
    validate_contact_points,
    validate_or_raise,
)

ALERT_MANIFEST_PATH = Path("ops/grafana/alerting.manifest.json")
ALERT_RULES_PATH = Path("ops/grafana/alerting/alert-rules.json")
CONTACT_POINTS_PATH = Path("ops/grafana/alerting/contact-points.json")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _minimal_temp_manifest(tmp_path: Path) -> Path:
    _write_json(
        tmp_path / "contact-points.json",
        {
            "contact_points": [
                {
                    "disable_resolve_message": False,
                    "name": "snowcast-owner-email",
                    "settings": {
                        "addresses": "${GRAFANA_ALERT_EMAIL_TO}",
                        "singleEmail": True,
                    },
                    "type": "email",
                }
            ]
        },
    )
    _write_json(
        tmp_path / "alert-rules.json",
        {
            "defaults": {
                "annotations": {
                    "runbook_url": "https://example.test/runbook",
                },
                "datasource_uid": "grafanacloud-prom",
                "evaluation_group": "snowcast-production",
                "folder_uid": "",
                "labels": {
                    "managed_by": "repo",
                    "service": "snowcast",
                    "team": "snowcast",
                },
                "relative_time_range_seconds": 1800,
            },
            "rules": [
                {
                    "annotations": {
                        "description": "Search p95 stayed above threshold.",
                        "summary": "Search p95 is high.",
                    },
                    "exec_error_state": "Error",
                    "expr": (
                        "histogram_quantile(0.95, sum by (le) "
                        "(rate(snowcast_search_duration_seconds_bucket"
                        '{job="snowcast"}[15m])))'
                    ),
                    "for": "10m",
                    "labels": {"severity": "warning"},
                    "no_data_state": "NoData",
                    "operator": "gt",
                    "threshold": 6,
                    "title": "Snowcast search p95 is high",
                    "uid": "snowcast-search-p95-warning",
                }
            ],
        },
    )
    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "contact_points_path": "contact-points.json",
            "alert_rules_path": "alert-rules.json",
        },
    )
    return manifest_path


def test_repo_grafana_alerting_resources_validate() -> None:
    validate_or_raise(ALERT_MANIFEST_PATH)


def test_alert_contact_point_uses_email_placeholder() -> None:
    resource = load_json(CONTACT_POINTS_PATH)

    errors = validate_contact_points(resource)

    assert errors == []
    serialized = json.dumps(resource)
    assert "${GRAFANA_ALERT_EMAIL_TO}" in serialized
    assert "@example" not in serialized


def test_alert_rules_use_safe_labels_and_promql_patterns() -> None:
    resource = load_json(ALERT_RULES_PATH)
    rules = resource["rules"]
    assert isinstance(rules, list)

    errors = validate_alert_rules(resource)

    assert errors == []
    assert len(rules) >= 8
    for rule in rules:
        assert isinstance(rule, dict)
        expr = rule["expr"]
        assert isinstance(expr, str)
        assert "irate(" not in expr
        if "histogram_quantile(" in expr:
            assert "sum by (le)" in expr
        if " / " in expr:
            assert "clamp_min(" in expr
        if "_total" in expr or "_bucket" in expr:
            assert "[" in expr and "]" in expr
        labels = rule.get("labels", {})
        assert isinstance(labels, dict)
        assert labels["severity"] in {"warning", "critical"}
        assert not any(
            sensitive in key
            for key in labels
            for sensitive in ("email", "origin", "prompt", "query", "token", "user")
        )


def test_alerting_dry_run_does_not_require_grafana_credentials() -> None:
    actions = deploy_from_manifest(
        manifest_path=ALERT_MANIFEST_PATH,
        client=None,
        apply=False,
    )

    assert ("contact-point:snowcast-owner-email", "dry-run") in actions
    assert any(name == "alert-rule:snowcast-search-p95-warning" for name, _ in actions)


def test_alerting_apply_creates_contact_point_and_rule(tmp_path: Path) -> None:
    manifest_path = _minimal_temp_manifest(tmp_path)
    requests: list[tuple[str, str, dict[str, Any] | None, dict[str, str]]] = []

    def transport(
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> tuple[int, Any]:
        requests.append((method, url, payload, headers))
        if method == "GET" and url.endswith("/contact-points"):
            return 200, []
        if method == "GET" and url.endswith("/alert-rules/snowcast-search-p95-warning"):
            return 404, {}
        return 201, {}

    client = GrafanaAlertingClient(
        base_url="https://grafana.example.test",
        token="token",
        transport=transport,
    )

    actions = deploy_from_manifest(
        manifest_path=manifest_path,
        client=client,
        apply=True,
        env={"GRAFANA_ALERT_EMAIL_TO": "owner@example.test"},
    )

    assert actions == [
        ("contact-point:snowcast-owner-email", "created"),
        ("alert-rule:snowcast-search-p95-warning", "created"),
    ]
    contact_create = next(
        payload
        for method, url, payload, _headers in requests
        if method == "POST" and url.endswith("/contact-points")
    )
    assert contact_create is not None
    assert contact_create["settings"]["addresses"] == "owner@example.test"
    assert any(
        headers.get("X-Disable-Provenance") == "true" for *_unused, headers in requests
    )


def test_alerting_apply_updates_existing_resources(tmp_path: Path) -> None:
    manifest_path = _minimal_temp_manifest(tmp_path)
    requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def transport(
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        _headers: dict[str, str],
    ) -> tuple[int, Any]:
        requests.append((method, url, payload))
        if method == "GET" and url.endswith("/contact-points"):
            return 200, [{"name": "snowcast-owner-email", "uid": "cp-123"}]
        if method == "GET" and url.endswith("/alert-rules/snowcast-search-p95-warning"):
            return 200, {"uid": "snowcast-search-p95-warning"}
        return 200, {}

    client = GrafanaAlertingClient(
        base_url="https://grafana.example.test",
        token="token",
        transport=transport,
    )

    actions = deploy_from_manifest(
        manifest_path=manifest_path,
        client=client,
        apply=True,
        env={"GRAFANA_ALERT_EMAIL_TO": "owner@example.test"},
    )

    assert actions == [
        ("contact-point:snowcast-owner-email", "updated"),
        ("alert-rule:snowcast-search-p95-warning", "updated"),
    ]
    assert any(
        method == "PUT" and url.endswith("/contact-points/cp-123")
        for method, url, _payload in requests
    )
    assert any(
        method == "PUT" and url.endswith("/alert-rules/snowcast-search-p95-warning")
        for method, url, _payload in requests
    )


def test_contact_point_validation_rejects_committed_email() -> None:
    errors = validate_contact_points(
        {
            "contact_points": [
                {
                    "name": "owner",
                    "type": "email",
                    "settings": {"addresses": "owner@example.test"},
                }
            ]
        }
    )

    assert any("GRAFANA_ALERT_EMAIL_TO" in error for error in errors)


def test_alert_rule_validation_rejects_brittle_promql() -> None:
    resource = load_json(ALERT_RULES_PATH)
    broken = json.loads(json.dumps(resource))
    broken["rules"][0]["expr"] = (
        "histogram_quantile(0.95, rate(snowcast_search_duration_seconds_bucket[15m]))"
    )

    errors = validate_alert_rules(broken)

    assert any("aggregate by le" in error for error in errors)


def test_alert_rule_validation_requires_clamped_ratio_denominator() -> None:
    resource = load_json(ALERT_RULES_PATH)
    broken = json.loads(json.dumps(resource))
    broken["rules"][3]["expr"] = (
        "sum(increase(snowcast_search_empty_results_total[30m])) "
        "/ sum(increase(snowcast_search_requests_total[30m]))"
    )

    errors = validate_alert_rules(broken)

    assert any("clamp_min" in error for error in errors)


def test_alerting_apply_requires_placeholder_value(tmp_path: Path) -> None:
    manifest_path = _minimal_temp_manifest(tmp_path)
    client = GrafanaAlertingClient(
        base_url="https://grafana.example.test",
        token="token",
        transport=lambda *_args: (200, []),
    )

    with pytest.raises(AlertingValidationError, match="GRAFANA_ALERT_EMAIL_TO"):
        deploy_from_manifest(
            manifest_path=manifest_path,
            client=client,
            apply=True,
            env={},
        )
