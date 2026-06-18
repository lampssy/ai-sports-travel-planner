from __future__ import annotations

import argparse
import copy
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

DashboardResource = dict[str, Any]
Transport = Any

API_VERSION = "dashboard.grafana.app/v2"
KIND = "Dashboard"

VOLATILE_METADATA_FIELDS = {
    "namespace",
    "uid",
    "resourceVersion",
    "generation",
    "creationTimestamp",
}
VOLATILE_LABELS = {"grafana.app/deprecatedInternalID"}
VOLATILE_ANNOTATIONS = {
    "grafana.app/createdBy",
    "grafana.app/saved-from-ui",
}


class DashboardValidationError(ValueError):
    """Raised when dashboard resources fail validation."""


class DashboardManifestError(ValueError):
    """Raised when the dashboard manifest is invalid."""


@dataclass(frozen=True)
class ManifestEntry:
    name: str
    path: Path
    folder_uid: str | None
    title: str | None
    root: Path

    @property
    def dashboard_path(self) -> Path:
        return (self.root / self.path).resolve()

    def load_dashboard(self) -> DashboardResource:
        resource = load_json(self.dashboard_path)
        return normalize_dashboard_resource(
            resource,
            name=self.name,
            folder_uid=self.folder_uid,
        )


def load_json(path: Path) -> DashboardResource:
    with path.open(encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise DashboardValidationError(f"{path} must contain a JSON object")
    return loaded


def write_json(path: Path, value: DashboardResource) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2, sort_keys=True)
        file.write("\n")


def normalize_dashboard_resource(
    resource: DashboardResource,
    *,
    name: str | None = None,
    folder_uid: str | None = None,
) -> DashboardResource:
    normalized = copy.deepcopy(resource)
    metadata = _require_mapping(normalized, "metadata")
    spec = _require_mapping(normalized, "spec")

    normalized["apiVersion"] = normalized.get("apiVersion", API_VERSION)
    normalized["kind"] = normalized.get("kind", KIND)

    for field in VOLATILE_METADATA_FIELDS:
        metadata.pop(field, None)

    if name is not None:
        metadata["name"] = name
    elif not metadata.get("name"):
        metadata["name"] = _slugify(str(spec.get("title") or "dashboard"))

    labels = metadata.get("labels")
    if isinstance(labels, dict):
        for label in VOLATILE_LABELS:
            labels.pop(label, None)
        if not labels:
            metadata.pop("labels", None)

    annotations = metadata.get("annotations")
    if isinstance(annotations, dict):
        for annotation in VOLATILE_ANNOTATIONS:
            annotations.pop(annotation, None)
    elif annotations is not None:
        metadata.pop("annotations", None)
        annotations = None

    if folder_uid is not None:
        annotations = metadata.setdefault("annotations", {})
        annotations["grafana.app/folder"] = folder_uid

    if isinstance(metadata.get("annotations"), dict) and not metadata["annotations"]:
        metadata.pop("annotations", None)

    return normalized


def validate_dashboard_resource(resource: DashboardResource) -> list[str]:
    errors: list[str] = []
    if resource.get("apiVersion") != API_VERSION:
        errors.append(f"apiVersion must be {API_VERSION}")
    if resource.get("kind") != KIND:
        errors.append(f"kind must be {KIND}")

    metadata = resource.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata must be an object")
        metadata = {}
    if not metadata.get("name"):
        errors.append("metadata.name is required")

    for field in VOLATILE_METADATA_FIELDS:
        if field in metadata:
            if field == "namespace":
                errors.append("metadata.namespace must be injected at deploy time")
            else:
                errors.append(f"metadata.{field} is volatile and must not be committed")

    labels = metadata.get("labels")
    if isinstance(labels, dict):
        for label in VOLATILE_LABELS:
            if label in labels:
                errors.append(f"metadata.labels[{label!r}] is volatile")

    annotations = metadata.get("annotations")
    if isinstance(annotations, dict):
        for annotation in VOLATILE_ANNOTATIONS:
            if annotation in annotations:
                errors.append(f"metadata.annotations[{annotation!r}] is volatile")

    spec = resource.get("spec")
    if not isinstance(spec, dict):
        errors.append("spec must be an object")
    elif not spec.get("title"):
        errors.append("spec.title is required")

    return errors


def validate_or_raise(resource: DashboardResource, *, source: str) -> None:
    errors = validate_dashboard_resource(resource)
    if errors:
        joined = "\n- ".join(errors)
        raise DashboardValidationError(f"{source} is invalid:\n- {joined}")


def load_manifest(path: Path) -> list[ManifestEntry]:
    root = path.parent.resolve()
    manifest = load_json(path)
    raw_dashboards = manifest.get("dashboards")
    if not isinstance(raw_dashboards, list):
        raise DashboardManifestError("dashboards must be a list")

    entries: list[ManifestEntry] = []
    seen_names: set[str] = set()
    for index, raw_entry in enumerate(raw_dashboards):
        if not isinstance(raw_entry, dict):
            raise DashboardManifestError(f"dashboards[{index}] must be an object")
        name = _required_string(raw_entry, "name", index=index)
        if name in seen_names:
            raise DashboardManifestError(f"dashboard name {name!r} is duplicated")
        seen_names.add(name)

        raw_path = _required_string(raw_entry, "path", index=index)
        relative_path = Path(raw_path)
        if relative_path.is_absolute():
            raise DashboardManifestError(
                f"dashboard path {raw_path!r} must be relative"
            )

        resolved = (root / relative_path).resolve()
        if not resolved.is_relative_to(root):
            raise DashboardManifestError(
                f"dashboard path {raw_path!r} must stay inside {root}"
            )

        folder_uid = raw_entry.get("folder_uid")
        if folder_uid is not None and not isinstance(folder_uid, str):
            raise DashboardManifestError(
                f"dashboards[{index}].folder_uid must be a string or null"
            )
        title = raw_entry.get("title")
        if title is not None and not isinstance(title, str):
            raise DashboardManifestError(
                f"dashboards[{index}].title must be a string or null"
            )
        entries.append(
            ManifestEntry(
                name=name,
                path=relative_path,
                folder_uid=folder_uid,
                title=title,
                root=root,
            )
        )
    return entries


class GrafanaDashboardClient:
    def __init__(
        self,
        *,
        base_url: str,
        namespace: str,
        token: str,
        transport: Transport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.namespace = namespace
        self.token = token
        self._transport = transport or _urlopen_transport

    def apply_dashboard(self, resource: DashboardResource) -> str:
        name = str(resource["metadata"]["name"])
        status_code, existing = self._request("GET", self._dashboard_url(name), None)
        if status_code == 404:
            status_code, _ = self._request("POST", self._collection_url(), resource)
            if status_code not in {200, 201, 202}:
                raise DashboardValidationError(
                    f"Grafana dashboard create failed with HTTP {status_code}"
                )
            return "created"

        if status_code != 200:
            raise DashboardValidationError(
                f"Grafana dashboard lookup failed with HTTP {status_code}"
            )

        update_resource = _with_existing_resource_version(resource, existing)
        status_code, _ = self._request(
            "PUT",
            self._dashboard_url(name),
            update_resource,
        )
        if status_code not in {200, 201, 202}:
            raise DashboardValidationError(
                f"Grafana dashboard update failed with HTTP {status_code}"
            )
        return "updated"

    def _collection_url(self) -> str:
        namespace = quote(self.namespace, safe="")
        return (
            f"{self.base_url}/apis/dashboard.grafana.app/v2/"
            f"namespaces/{namespace}/dashboards"
        )

    def _dashboard_url(self, name: str) -> str:
        return f"{self._collection_url()}/{quote(name, safe='')}"

    def _request(
        self,
        method: str,
        url: str,
        payload: DashboardResource | None,
    ) -> tuple[int, DashboardResource]:
        return self._transport(
            method,
            url,
            payload,
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )


def deploy_from_manifest(
    *,
    manifest_path: Path,
    client: GrafanaDashboardClient | None,
    apply: bool,
) -> list[tuple[str, str]]:
    actions: list[tuple[str, str]] = []
    for entry in load_manifest(manifest_path):
        resource = entry.load_dashboard()
        validate_or_raise(resource, source=str(entry.dashboard_path))
        if apply:
            if client is None:
                raise DashboardValidationError(
                    "Grafana client is required when apply=True"
                )
            action = client.apply_dashboard(resource)
        else:
            action = "dry-run"
        actions.append((entry.name, action))
    return actions


def manifest_path_from_args(args: argparse.Namespace) -> Path:
    return Path(args.manifest).resolve()


def client_from_env() -> GrafanaDashboardClient:
    base_url = _required_env("GRAFANA_URL")
    namespace = _required_env("GRAFANA_DASHBOARD_NAMESPACE")
    token = _required_env("GRAFANA_SERVICE_ACCOUNT_TOKEN")
    return GrafanaDashboardClient(base_url=base_url, namespace=namespace, token=token)


def _urlopen_transport(
    method: str,
    url: str,
    payload: DashboardResource | None,
    headers: dict[str, str],
) -> tuple[int, DashboardResource]:
    encoded_payload = None
    if payload is not None:
        encoded_payload = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=encoded_payload,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as error:
        if error.code == 404:
            return 404, {}
        body = error.read().decode("utf-8")
        raise DashboardValidationError(
            f"Grafana API {method} {url} failed with HTTP {error.code}: {body}"
        ) from error


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise DashboardValidationError(f"{name} environment variable is required")
    return value


def _with_existing_resource_version(
    resource: DashboardResource,
    existing: DashboardResource,
) -> DashboardResource:
    resource_version = None
    existing_metadata = existing.get("metadata")
    if isinstance(existing_metadata, dict):
        resource_version = existing_metadata.get("resourceVersion")
    if not resource_version:
        return resource

    update_resource = copy.deepcopy(resource)
    metadata = _require_mapping(update_resource, "metadata")
    metadata["resourceVersion"] = resource_version
    return update_resource


def _require_mapping(resource: DashboardResource, key: str) -> DashboardResource:
    value = resource.get(key)
    if not isinstance(value, dict):
        value = {}
        resource[key] = value
    return value


def _required_string(entry: DashboardResource, key: str, *, index: int) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DashboardManifestError(f"dashboards[{index}].{key} is required")
    return value


def _slugify(value: str) -> str:
    slug = "".join(
        character.lower() if character.isalnum() else "-" for character in value
    )
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "dashboard"
