from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.grafana.scripts.dashboard_resources import (
    DashboardManifestError,
    DashboardValidationError,
    GrafanaDashboardClient,
    ManifestEntry,
    deploy_from_manifest,
    load_manifest,
    normalize_dashboard_resource,
    validate_dashboard_resource,
)

SNOWCAST_DASHBOARD_PATH = Path(
    "ops/grafana/dashboards/snowcast-production-overview.dashboard.json"
)


def _load_snowcast_dashboard() -> dict[str, object]:
    return json.loads(SNOWCAST_DASHBOARD_PATH.read_text(encoding="utf-8"))


def _panel(resource: dict[str, object], panel_id: str) -> dict[str, object]:
    spec = resource["spec"]
    assert isinstance(spec, dict)
    elements = spec["elements"]
    assert isinstance(elements, dict)
    panel_resource = elements[panel_id]
    assert isinstance(panel_resource, dict)
    panel_spec = panel_resource["spec"]
    assert isinstance(panel_spec, dict)
    return panel_spec


def _panel_query_exprs(resource: dict[str, object], panel_id: str) -> list[str]:
    panel = _panel(resource, panel_id)
    data = panel["data"]
    assert isinstance(data, dict)
    data_spec = data["spec"]
    assert isinstance(data_spec, dict)
    queries = data_spec["queries"]
    assert isinstance(queries, list)
    exprs: list[str] = []
    for query in queries:
        assert isinstance(query, dict)
        query_spec = query["spec"]
        assert isinstance(query_spec, dict)
        query_payload = query_spec["query"]
        assert isinstance(query_payload, dict)
        payload_spec = query_payload["spec"]
        assert isinstance(payload_spec, dict)
        expr = payload_spec["expr"]
        assert isinstance(expr, str)
        exprs.append(expr)
    return exprs


def _panel_data_queries(
    resource: dict[str, object],
    panel_id: str,
) -> list[dict[str, object]]:
    panel = _panel(resource, panel_id)
    data = panel["data"]
    assert isinstance(data, dict)
    data_spec = data["spec"]
    assert isinstance(data_spec, dict)
    queries = data_spec["queries"]
    assert isinstance(queries, list)
    data_queries: list[dict[str, object]] = []
    for query in queries:
        assert isinstance(query, dict)
        query_spec = query["spec"]
        assert isinstance(query_spec, dict)
        data_query = query_spec["query"]
        assert isinstance(data_query, dict)
        data_queries.append(data_query)
    return data_queries


def _panel_viz_options(
    resource: dict[str, object],
    panel_id: str,
) -> dict[str, object]:
    panel = _panel(resource, panel_id)
    viz_config = panel["vizConfig"]
    assert isinstance(viz_config, dict)
    viz_spec = viz_config["spec"]
    assert isinstance(viz_spec, dict)
    options = viz_spec["options"]
    assert isinstance(options, dict)
    return options


def _row_titles(resource: dict[str, object]) -> list[str]:
    spec = resource["spec"]
    assert isinstance(spec, dict)
    layout = spec["layout"]
    assert isinstance(layout, dict)
    layout_spec = layout["spec"]
    assert isinstance(layout_spec, dict)
    rows = layout_spec["rows"]
    assert isinstance(rows, list)
    titles: list[str] = []
    for row in rows:
        assert isinstance(row, dict)
        row_spec = row["spec"]
        assert isinstance(row_spec, dict)
        title = row_spec["title"]
        assert isinstance(title, str)
        titles.append(title)
    return titles


def _row_panel_names(resource: dict[str, object], row_title: str) -> list[str]:
    spec = resource["spec"]
    assert isinstance(spec, dict)
    layout = spec["layout"]
    assert isinstance(layout, dict)
    layout_spec = layout["spec"]
    assert isinstance(layout_spec, dict)
    rows = layout_spec["rows"]
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, dict)
        row_spec = row["spec"]
        assert isinstance(row_spec, dict)
        if row_spec["title"] != row_title:
            continue
        row_layout = row_spec["layout"]
        assert isinstance(row_layout, dict)
        grid_spec = row_layout["spec"]
        assert isinstance(grid_spec, dict)
        items = grid_spec["items"]
        assert isinstance(items, list)
        names: list[str] = []
        for item in items:
            assert isinstance(item, dict)
            item_spec = item["spec"]
            assert isinstance(item_spec, dict)
            element = item_spec["element"]
            assert isinstance(element, dict)
            name = element["name"]
            assert isinstance(name, str)
            names.append(name)
        return names
    raise AssertionError(f"row {row_title!r} not found")


def test_normalize_dashboard_resource_removes_volatile_metadata() -> None:
    resource = {
        "apiVersion": "dashboard.grafana.app/v2",
        "kind": "Dashboard",
        "metadata": {
            "name": "lalsvdw",
            "namespace": "stacks-1693732",
            "uid": "f1376b86-2a51-472d-9abc-887dd06b3aa3",
            "resourceVersion": "2067028087521935858",
            "generation": 1,
            "creationTimestamp": "2026-06-16T23:34:34Z",
            "labels": {
                "grafana.app/deprecatedInternalID": "4379458083790848",
                "snowcast": "true",
            },
            "annotations": {
                "grafana.app/createdBy": "user:example",
                "grafana.app/saved-from-ui": "Grafana Cloud",
                "grafana.app/folder": "snowcast",
            },
        },
        "spec": {"title": "Snowcast Production Overview"},
    }

    normalized = normalize_dashboard_resource(
        resource,
        name="snowcast-production-overview",
        folder_uid="",
    )

    assert normalized["metadata"] == {
        "name": "snowcast-production-overview",
        "labels": {"snowcast": "true"},
        "annotations": {"grafana.app/folder": ""},
    }
    assert normalized["spec"]["title"] == "Snowcast Production Overview"
    assert resource["metadata"]["name"] == "lalsvdw"


def test_validate_dashboard_resource_rejects_volatile_metadata() -> None:
    resource = {
        "apiVersion": "dashboard.grafana.app/v2",
        "kind": "Dashboard",
        "metadata": {
            "name": "snowcast-production-overview",
            "namespace": "stacks-1693732",
            "resourceVersion": "1",
        },
        "spec": {"title": "Snowcast Production Overview"},
    }

    errors = validate_dashboard_resource(resource)

    assert "metadata.namespace must be injected at deploy time" in errors
    assert "metadata.resourceVersion is volatile and must not be committed" in errors


def test_load_manifest_rejects_paths_outside_ops_grafana(tmp_path: Path) -> None:
    manifest_path = tmp_path / "dashboards.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dashboards": [
                    {
                        "name": "bad",
                        "path": "../outside.json",
                        "folder_uid": "",
                        "title": "Bad",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DashboardManifestError, match="must stay inside"):
        load_manifest(manifest_path)


def test_client_creates_missing_dashboard() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def transport(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        headers: dict[str, str],
    ) -> tuple[int, dict[str, object]]:
        requests.append((method, url, payload))
        if method == "GET" and "/api/search?" in url:
            return 200, []
        if method == "GET":
            return 404, {"message": "not found"}
        assert headers["Authorization"] == "Bearer token"
        return 201, {"status": "created"}

    client = GrafanaDashboardClient(
        base_url="https://example.grafana.net/",
        namespace="stacks-1",
        token="token",
        transport=transport,
    )
    resource = {
        "apiVersion": "dashboard.grafana.app/v2",
        "kind": "Dashboard",
        "metadata": {"name": "snowcast-production-overview"},
        "spec": {"title": "Snowcast Production Overview"},
    }

    action = client.apply_dashboard(resource)

    assert action == "created"
    assert requests[0][0] == "GET"
    assert requests[0][1].endswith(
        "/apis/dashboard.grafana.app/v2/namespaces/stacks-1/dashboards/"
        "snowcast-production-overview"
    )
    assert requests[1][0] == "GET"
    assert "/api/search?" in requests[1][1]
    assert requests[2][0] == "POST"
    assert requests[2][2] == resource


def test_client_adopts_single_title_match_when_named_resource_is_missing() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def transport(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        _headers: dict[str, str],
    ) -> tuple[int, dict[str, object] | list[dict[str, object]]]:
        requests.append((method, url, payload))
        if method == "GET" and url.endswith("/dashboards/snowcast-production-overview"):
            return 404, {"message": "not found"}
        if method == "GET" and "/api/search?" in url:
            return 200, [
                {
                    "folderUid": "",
                    "title": "Snowcast Production Overview",
                    "type": "dash-db",
                    "uid": "existing-ui-dashboard",
                    "url": "/d/existing-ui-dashboard/snowcast-production-overview",
                }
            ]
        if method == "GET" and url.endswith("/dashboards/existing-ui-dashboard"):
            return 200, {
                "metadata": {
                    "name": "existing-ui-dashboard",
                    "resourceVersion": "42",
                }
            }
        return 200, {"status": "updated"}

    client = GrafanaDashboardClient(
        base_url="https://example.grafana.net",
        namespace="stacks-1",
        token="token",
        transport=transport,
    )
    resource = {
        "apiVersion": "dashboard.grafana.app/v2",
        "kind": "Dashboard",
        "metadata": {
            "annotations": {"grafana.app/folder": ""},
            "name": "snowcast-production-overview",
        },
        "spec": {"title": "Snowcast Production Overview"},
    }

    action = client.apply_dashboard(
        resource,
        title="Snowcast Production Overview",
    )

    assert action == "updated-by-title"
    assert [request[0] for request in requests] == ["GET", "GET", "GET", "PUT"]
    assert requests[-1][1].endswith("/dashboards/existing-ui-dashboard")
    put_payload = requests[-1][2]
    assert put_payload is not None
    assert put_payload["metadata"]["name"] == "existing-ui-dashboard"
    assert put_payload["metadata"]["resourceVersion"] == "42"


def test_client_rejects_ambiguous_title_matches() -> None:
    def transport(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        _headers: dict[str, str],
    ) -> tuple[int, dict[str, object] | list[dict[str, object]]]:
        if method == "GET" and url.endswith("/dashboards/snowcast-production-overview"):
            return 404, {"message": "not found"}
        if method == "GET" and "/api/search?" in url:
            return 200, [
                {
                    "folderUid": "",
                    "title": "Snowcast Production Overview",
                    "type": "dash-db",
                    "uid": "first-dashboard",
                },
                {
                    "folderUid": "",
                    "title": "Snowcast Production Overview",
                    "type": "dash-db",
                    "uid": "second-dashboard",
                },
            ]
        return 500, {"message": "unexpected request"}

    client = GrafanaDashboardClient(
        base_url="https://example.grafana.net",
        namespace="stacks-1",
        token="token",
        transport=transport,
    )
    resource = {
        "apiVersion": "dashboard.grafana.app/v2",
        "kind": "Dashboard",
        "metadata": {
            "annotations": {"grafana.app/folder": ""},
            "name": "snowcast-production-overview",
        },
        "spec": {"title": "Snowcast Production Overview"},
    }

    with pytest.raises(DashboardValidationError, match="Multiple Grafana dashboards"):
        client.apply_dashboard(resource, title="Snowcast Production Overview")


def test_client_updates_existing_dashboard() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def transport(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        headers: dict[str, str],
    ) -> tuple[int, dict[str, object]]:
        requests.append((method, url, payload))
        if method == "GET":
            return 200, {
                "metadata": {
                    "name": "snowcast-production-overview",
                    "resourceVersion": "42",
                }
            }
        return 200, {"status": "updated"}

    client = GrafanaDashboardClient(
        base_url="https://example.grafana.net",
        namespace="stacks-1",
        token="token",
        transport=transport,
    )
    resource = {
        "apiVersion": "dashboard.grafana.app/v2",
        "kind": "Dashboard",
        "metadata": {"name": "snowcast-production-overview"},
        "spec": {"title": "Snowcast Production Overview"},
    }

    action = client.apply_dashboard(resource)

    assert action == "updated"
    assert [request[0] for request in requests] == ["GET", "PUT"]
    put_payload = requests[1][2]
    assert put_payload is not None
    assert put_payload["metadata"]["resourceVersion"] == "42"
    assert "resourceVersion" not in resource["metadata"]


def test_manifest_entry_loads_normalized_dashboard(tmp_path: Path) -> None:
    dashboard_path = tmp_path / "dashboards" / "snowcast.dashboard.json"
    dashboard_path.parent.mkdir()
    dashboard_path.write_text(
        json.dumps(
            {
                "apiVersion": "dashboard.grafana.app/v2",
                "kind": "Dashboard",
                "metadata": {"name": "exported", "namespace": "stacks-1"},
                "spec": {"title": "Snowcast Production Overview"},
            }
        ),
        encoding="utf-8",
    )
    entry = ManifestEntry(
        name="snowcast-production-overview",
        path=dashboard_path.relative_to(tmp_path),
        folder_uid="",
        title="Snowcast Production Overview",
        root=tmp_path,
    )

    loaded = entry.load_dashboard()

    assert loaded["metadata"]["name"] == "snowcast-production-overview"
    assert "namespace" not in loaded["metadata"]


def test_deploy_from_manifest_dry_run_does_not_need_client(tmp_path: Path) -> None:
    dashboard_path = tmp_path / "dashboards" / "snowcast.dashboard.json"
    dashboard_path.parent.mkdir()
    dashboard_path.write_text(
        json.dumps(
            {
                "apiVersion": "dashboard.grafana.app/v2",
                "kind": "Dashboard",
                "metadata": {"name": "snowcast-production-overview"},
                "spec": {"title": "Snowcast Production Overview"},
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "dashboards.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dashboards": [
                    {
                        "name": "snowcast-production-overview",
                        "path": "dashboards/snowcast.dashboard.json",
                        "folder_uid": "",
                        "title": "Snowcast Production Overview",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    actions = deploy_from_manifest(
        manifest_path=manifest_path,
        client=None,
        apply=False,
    )

    assert actions == [("snowcast-production-overview", "dry-run")]


def test_snowcast_dashboard_uses_user_impacting_error_and_empty_metrics() -> None:
    dashboard = _load_snowcast_dashboard()

    http_5xx_expr = _panel_query_exprs(dashboard, "panel-46")[0]
    assert 'status_class="5xx"' in http_5xx_expr
    assert 'status_class="4xx"' not in http_5xx_expr
    assert 'route=~"/api/.*"' in http_5xx_expr
    assert "clamp_min" in http_5xx_expr
    assert "or vector(0)" in http_5xx_expr

    empty_search_stat_expr = _panel_query_exprs(dashboard, "panel-48")[0]
    empty_search_trend_expr = _panel_query_exprs(dashboard, "panel-58")[0]
    assert "snowcast_search_empty_results_total" in empty_search_stat_expr
    assert "snowcast_search_empty_results_total" in empty_search_trend_expr
    assert "clamp_min" in empty_search_stat_expr
    assert "or vector(0)" in empty_search_stat_expr
    assert "snowcast_search_results_total_bucket" not in empty_search_stat_expr
    assert "snowcast_search_results_total_bucket" not in empty_search_trend_expr


def test_snowcast_dashboard_separates_expected_4xx_noise_from_5xx() -> None:
    dashboard = _load_snowcast_dashboard()

    non_2xx_exprs = _panel_query_exprs(dashboard, "panel-53")

    assert len(non_2xx_exprs) == 2
    assert 'status_class="5xx"' in non_2xx_exprs[0]
    assert "/api/current-trip" not in non_2xx_exprs[0]
    assert 'status_class="4xx"' in non_2xx_exprs[1]
    assert "/api/current-trip.*" in non_2xx_exprs[1]


def test_snowcast_dashboard_tracks_freshness_and_llm_fallbacks() -> None:
    dashboard = _load_snowcast_dashboard()

    condition_age_stat_expr = _panel_query_exprs(dashboard, "panel-50")[0]
    condition_age_by_source_expr = _panel_query_exprs(dashboard, "panel-65")[0]
    refresh_rate_exprs = _panel_query_exprs(dashboard, "panel-67")
    fallback_expr = _panel_query_exprs(dashboard, "panel-68")[0]

    assert "snowcast_conditions_refresh_age_seconds" in condition_age_stat_expr
    assert "snowcast_conditions_refresh_age_seconds" in condition_age_by_source_expr
    assert 'job=~"snowcast|snowcast-jobs"' in condition_age_stat_expr
    assert 'job=~"snowcast|snowcast-jobs"' in condition_age_by_source_expr
    assert _panel_viz_options(dashboard, "panel-50")["colorMode"] == "value"
    assert any(
        "snowcast_conditions_refresh_success_total" in expr
        and 'job=~"snowcast|snowcast-jobs"' in expr
        for expr in refresh_rate_exprs
    )
    assert any(
        "snowcast_conditions_refresh_failure_total" in expr
        and 'job=~"snowcast|snowcast-jobs"' in expr
        for expr in refresh_rate_exprs
    )
    assert "snowcast_llm_fallbacks_total" in fallback_expr


def test_snowcast_dashboard_tracks_data_quality_audit_metrics() -> None:
    dashboard = _load_snowcast_dashboard()

    completeness_expr = _panel_query_exprs(dashboard, "panel-72")[0]
    archive_missing_expr = _panel_query_exprs(dashboard, "panel-73")[0]
    weak_climatology_expr = _panel_query_exprs(dashboard, "panel-74")[0]
    catalog_gap_expr = _panel_query_exprs(dashboard, "panel-75")[0]
    trust_gap_expr = _panel_query_exprs(dashboard, "panel-76")[0]
    all_exprs = "\n".join(
        [
            completeness_expr,
            archive_missing_expr,
            weak_climatology_expr,
            catalog_gap_expr,
            trust_gap_expr,
        ]
    )

    assert "snowcast_data_completeness_ratio" in completeness_expr
    assert "snowcast_data_missing_days" in archive_missing_expr
    assert "snowcast_climatology_weak_coverage_groups" in weak_climatology_expr
    assert "snowcast_catalog_field_groups" in catalog_gap_expr
    assert "snowcast_catalog_trust_status" in trust_gap_expr
    assert 'job=~"snowcast|snowcast-jobs"' in all_exprs
    assert "snowcast_data_completeness_entities_total" not in all_exprs
    assert "snowcast_catalog_field_groups_total" not in all_exprs
    assert "snowcast_catalog_trust_status_total" not in all_exprs

    assert _panel_viz_options(dashboard, "panel-72")["colorMode"] == "background"
    assert (
        _panel(dashboard, "panel-72")["vizConfig"]["spec"]["fieldConfig"]["defaults"][
            "unit"
        ]
        == "percentunit"
    )
    assert _row_panel_names(dashboard, "Weather / Data Freshness") == [
        "panel-65",
        "panel-67",
        "panel-72",
        "panel-73",
        "panel-74",
        "panel-75",
        "panel-76",
    ]


def test_snowcast_dashboard_displays_parse_confidence_as_percent_unit() -> None:
    dashboard = _load_snowcast_dashboard()
    parse_confidence = _panel(dashboard, "panel-60")
    viz_config = parse_confidence["vizConfig"]
    assert isinstance(viz_config, dict)
    viz_spec = viz_config["spec"]
    assert isinstance(viz_spec, dict)
    field_config = viz_spec["fieldConfig"]
    assert isinstance(field_config, dict)
    defaults = field_config["defaults"]
    assert isinstance(defaults, dict)

    assert defaults["unit"] == "percentunit"
    assert defaults["min"] == 0
    assert defaults["max"] == 1


def test_snowcast_dashboard_compares_http_and_domain_search_timing() -> None:
    dashboard = _load_snowcast_dashboard()

    timing_exprs = _panel_query_exprs(dashboard, "panel-71")
    timing_queries = _panel_data_queries(dashboard, "panel-71")

    assert "snowcast_search_duration_seconds_bucket" in timing_exprs[0]
    assert "snowcast_http_request_duration_seconds_bucket" in timing_exprs[1]
    assert 'route="/api/search"' in timing_exprs[1]
    assert timing_queries[0]["spec"]["legendFormat"] == "domain search p95"
    assert timing_queries[1]["spec"]["legendFormat"] == "HTTP /api/search p95"


def test_snowcast_dashboard_includes_tempo_trace_drilldown_panels() -> None:
    dashboard = _load_snowcast_dashboard()

    phase_query = _panel_data_queries(dashboard, "panel-69")[0]
    phase_query_spec = phase_query["spec"]
    assert isinstance(phase_query_spec, dict)
    assert phase_query["group"] == "tempo"
    assert phase_query["datasource"] == {
        "name": "grafanacloud-tallgoldfinch1476-traces"
    }
    assert phase_query_spec["queryType"] == "traceql"
    assert "quantile_over_time(span:duration, 0.95)" in phase_query_spec["query"]
    assert 'span:name =~ "search\\\\..*"' in phase_query_spec["query"]
    assert phase_query_spec["legendFormat"] == "{{name}} p95"
    assert _panel_viz_options(dashboard, "panel-69")["legend"]["calcs"] == ["max"]

    slow_trace_query = _panel_data_queries(dashboard, "panel-70")[0]
    slow_trace_query_spec = slow_trace_query["spec"]
    assert isinstance(slow_trace_query_spec, dict)
    assert slow_trace_query["group"] == "tempo"
    assert slow_trace_query_spec["queryType"] == "traceql"
    assert 'span:name = "api.search"' in slow_trace_query_spec["query"]
    assert "span:duration > 5s" in slow_trace_query_spec["query"]

    trace_help = _panel(dashboard, "panel-66")
    trace_help_options = trace_help["vizConfig"]["spec"]["options"]
    assert isinstance(trace_help_options, dict)
    assert "OTEL_TRACES_SAMPLER_ARG=1.0" in trace_help_options["content"]


def test_snowcast_dashboard_layout_prioritizes_search_before_http() -> None:
    dashboard = _load_snowcast_dashboard()

    assert _row_titles(dashboard)[:5] == [
        "Executive Status",
        "Search Performance",
        "Query Parsing & LLM",
        "Weather / Data Freshness",
        "User-Facing HTTP",
    ]
