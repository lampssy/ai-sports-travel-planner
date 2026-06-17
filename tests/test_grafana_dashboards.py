from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.grafana.scripts.dashboard_resources import (
    DashboardManifestError,
    GrafanaDashboardClient,
    ManifestEntry,
    deploy_from_manifest,
    load_manifest,
    normalize_dashboard_resource,
    validate_dashboard_resource,
)


def test_normalize_dashboard_resource_removes_volatile_metadata() -> None:
    resource = {
        "apiVersion": "dashboard.grafana.app/v1",
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
        "apiVersion": "dashboard.grafana.app/v1",
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
        "apiVersion": "dashboard.grafana.app/v1",
        "kind": "Dashboard",
        "metadata": {"name": "snowcast-production-overview"},
        "spec": {"title": "Snowcast Production Overview"},
    }

    action = client.apply_dashboard(resource)

    assert action == "created"
    assert requests[0][0] == "GET"
    assert requests[0][1].endswith(
        "/apis/dashboard.grafana.app/v1/namespaces/stacks-1/dashboards/"
        "snowcast-production-overview"
    )
    assert requests[1][0] == "POST"
    assert requests[1][2] == resource


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
        "apiVersion": "dashboard.grafana.app/v1",
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
                "apiVersion": "dashboard.grafana.app/v1",
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
                "apiVersion": "dashboard.grafana.app/v1",
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
