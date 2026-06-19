from __future__ import annotations

import argparse
import copy
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

AlertingResource = dict[str, Any]
Transport = Any

DEFAULT_MANIFEST_PATH = Path("ops/grafana/alerting.manifest.json")
PROVENANCE_HEADER = "X-Disable-Provenance"
SENSITIVE_LABEL_PARTS = {
    "email",
    "origin",
    "prompt",
    "query",
    "raw",
    "token",
    "trace",
    "url",
    "user",
}


class AlertingValidationError(ValueError):
    """Raised when alerting resources fail validation."""


class AlertingManifestError(ValueError):
    """Raised when the alerting manifest is invalid."""


@dataclass(frozen=True)
class AlertingManifest:
    root: Path
    folders_path: Path
    contact_points_path: Path
    alert_rules_path: Path

    @property
    def folders_file(self) -> Path:
        return (self.root / self.folders_path).resolve()

    @property
    def contact_points_file(self) -> Path:
        return (self.root / self.contact_points_path).resolve()

    @property
    def alert_rules_file(self) -> Path:
        return (self.root / self.alert_rules_path).resolve()


def load_json(path: Path) -> AlertingResource:
    with path.open(encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise AlertingValidationError(f"{path} must contain a JSON object")
    return loaded


def load_manifest(path: Path) -> AlertingManifest:
    root = path.parent.resolve()
    manifest = load_json(path)
    folders_path = _relative_manifest_path(
        manifest,
        "folders_path",
        root=root,
    )
    contact_points_path = _relative_manifest_path(
        manifest,
        "contact_points_path",
        root=root,
    )
    alert_rules_path = _relative_manifest_path(
        manifest,
        "alert_rules_path",
        root=root,
    )
    return AlertingManifest(
        root=root,
        folders_path=folders_path,
        contact_points_path=contact_points_path,
        alert_rules_path=alert_rules_path,
    )


def validate_folders(resource: AlertingResource) -> list[str]:
    errors: list[str] = []
    raw_folders = resource.get("folders")
    if not isinstance(raw_folders, list):
        return ["folders must be a list"]

    seen_uids: set[str] = set()
    for index, folder in enumerate(raw_folders):
        if not isinstance(folder, dict):
            errors.append(f"folders[{index}] must be an object")
            continue

        uid = folder.get("uid")
        if not isinstance(uid, str) or not uid:
            errors.append(f"folders[{index}].uid is required")
        elif uid in seen_uids:
            errors.append(f"folder uid {uid!r} is duplicated")
        else:
            seen_uids.add(uid)

        title = folder.get("title")
        if not isinstance(title, str) or not title:
            errors.append(f"folders[{index}].title is required")
    return errors


def validate_contact_points(resource: AlertingResource) -> list[str]:
    errors: list[str] = []
    raw_contact_points = resource.get("contact_points")
    if not isinstance(raw_contact_points, list):
        return ["contact_points must be a list"]

    seen_names: set[str] = set()
    for index, contact_point in enumerate(raw_contact_points):
        if not isinstance(contact_point, dict):
            errors.append(f"contact_points[{index}] must be an object")
            continue
        name = contact_point.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"contact_points[{index}].name is required")
        elif name in seen_names:
            errors.append(f"contact point name {name!r} is duplicated")
        else:
            seen_names.add(name)

        contact_type = contact_point.get("type")
        if contact_type != "email":
            errors.append(
                f"contact_points[{index}].type must be 'email' for this phase"
            )

        settings = contact_point.get("settings")
        if not isinstance(settings, dict):
            errors.append(f"contact_points[{index}].settings must be an object")
            continue
        addresses = settings.get("addresses")
        if addresses != "${GRAFANA_ALERT_EMAIL_TO}":
            errors.append(
                "email contact point must use ${GRAFANA_ALERT_EMAIL_TO} "
                "instead of a committed address"
            )
    return errors


def validate_alert_rules(
    resource: AlertingResource,
    *,
    known_folder_uids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    defaults = resource.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}
        errors.append("defaults must be an object")

    rules = resource.get("rules")
    if not isinstance(rules, list):
        return [*errors, "rules must be a list"]

    seen_uids: set[str] = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"rules[{index}] must be an object")
            continue
        folder_uid = rule.get("folder_uid") or defaults.get("folder_uid")
        if not isinstance(folder_uid, str) or not folder_uid:
            errors.append(f"rules[{index}].folder_uid is required")
        elif known_folder_uids is not None and folder_uid not in known_folder_uids:
            errors.append(
                f"rules[{index}].folder_uid {folder_uid!r} is not declared "
                "in alerting folders"
            )

        uid = rule.get("uid")
        if not isinstance(uid, str) or not uid:
            errors.append(f"rules[{index}].uid is required")
        elif uid in seen_uids:
            errors.append(f"alert rule uid {uid!r} is duplicated")
        else:
            seen_uids.add(uid)

        title = rule.get("title")
        if not isinstance(title, str) or not title:
            errors.append(f"rules[{index}].title is required")

        expr = rule.get("expr")
        if not isinstance(expr, str) or not expr:
            errors.append(f"rules[{index}].expr is required")
            continue
        errors.extend(_validate_promql(expr, index=index))

        operator = rule.get("operator")
        if operator not in {"gt", "lt"}:
            errors.append(f"rules[{index}].operator must be 'gt' or 'lt'")
        if not isinstance(rule.get("threshold"), (int, float)):
            errors.append(f"rules[{index}].threshold must be numeric")

        labels = _merged_mapping(defaults.get("labels"), rule.get("labels"))
        severity = labels.get("severity")
        if severity not in {"warning", "critical"}:
            errors.append(f"rules[{index}] must set severity warning or critical")
        for required_label in ("managed_by", "service", "team"):
            if required_label not in labels:
                errors.append(f"rules[{index}] is missing label {required_label!r}")
        for key in labels:
            if _has_sensitive_label_part(str(key)):
                errors.append(f"rules[{index}] has sensitive label key {key!r}")

        annotations = _merged_mapping(
            defaults.get("annotations"),
            rule.get("annotations"),
        )
        for required_annotation in ("summary", "description", "runbook_url"):
            if not annotations.get(required_annotation):
                errors.append(
                    f"rules[{index}] is missing annotation {required_annotation!r}"
                )

        if not isinstance(rule.get("for"), str) or not rule.get("for"):
            errors.append(f"rules[{index}].for is required")
        if rule.get("no_data_state") not in {"NoData", "OK", "Alerting"}:
            errors.append(f"rules[{index}].no_data_state is invalid")
        if rule.get("exec_error_state") not in {"Error", "OK", "Alerting"}:
            errors.append(f"rules[{index}].exec_error_state is invalid")
    return errors


def validate_or_raise(manifest_path: Path) -> None:
    manifest = load_manifest(manifest_path)
    folders_resource = load_json(manifest.folders_file)
    folder_errors = validate_folders(folders_resource)
    known_folder_uids = {
        str(folder["uid"])
        for folder in folders_resource.get("folders", [])
        if isinstance(folder, dict) and isinstance(folder.get("uid"), str)
    }
    contact_point_errors = validate_contact_points(
        load_json(manifest.contact_points_file)
    )
    alert_rule_errors = validate_alert_rules(
        load_json(manifest.alert_rules_file),
        known_folder_uids=known_folder_uids,
    )
    errors = [
        *(f"{manifest.folders_file}: {error}" for error in folder_errors),
        *(f"{manifest.contact_points_file}: {error}" for error in contact_point_errors),
        *(f"{manifest.alert_rules_file}: {error}" for error in alert_rule_errors),
    ]
    if errors:
        joined = "\n- ".join(errors)
        raise AlertingValidationError(
            f"Grafana alerting resources are invalid:\n- {joined}"
        )


class GrafanaAlertingClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        namespace: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.namespace = namespace
        self._transport = transport or _urlopen_transport

    def apply_folder(self, folder: AlertingResource) -> str:
        uid = str(folder["uid"])
        payload = _folder_payload(folder)
        status_code, existing = self._request("GET", self._folder_url(uid), None)
        if status_code == 404:
            status_code, _ = self._request("POST", self._folders_url(), payload)
            if status_code not in {200, 201, 202}:
                raise AlertingValidationError(
                    f"Grafana folder create failed with HTTP {status_code}"
                )
            return "created"
        if status_code != 200:
            raise AlertingValidationError(
                f"Grafana folder lookup failed with HTTP {status_code}"
            )
        if _folder_title(existing) == folder["title"]:
            return "unchanged"

        update_payload = _folder_payload(folder, existing=existing)
        status_code, _ = self._request("PUT", self._folder_url(uid), update_payload)
        if status_code not in {200, 201, 202}:
            raise AlertingValidationError(
                f"Grafana folder update failed with HTTP {status_code}"
            )
        return "updated"

    def apply_contact_point(self, contact_point: AlertingResource) -> str:
        name = str(contact_point["name"])
        status_code, existing = self._request("GET", self._contact_points_url(), None)
        if status_code != 200:
            raise AlertingValidationError(
                f"Grafana contact point lookup failed with HTTP {status_code}"
            )
        existing_uid = _find_contact_point_uid(existing, name=name)
        payload = _contact_point_payload(contact_point)
        if existing_uid is None:
            status_code, _ = self._request(
                "POST",
                self._contact_points_url(),
                payload,
            )
            if status_code not in {200, 201, 202}:
                raise AlertingValidationError(
                    f"Grafana contact point create failed with HTTP {status_code}"
                )
            return "created"

        payload["uid"] = existing_uid
        status_code, _ = self._request(
            "PUT",
            self._contact_point_url(existing_uid),
            payload,
        )
        if status_code not in {200, 201, 202}:
            raise AlertingValidationError(
                f"Grafana contact point update failed with HTTP {status_code}"
            )
        return "updated"

    def apply_alert_rule(self, rule: AlertingResource) -> str:
        uid = str(rule["uid"])
        payload = _alert_rule_payload(rule)
        status_code, _existing = self._request("GET", self._alert_rule_url(uid), None)
        if status_code == 404:
            status_code, _ = self._request("POST", self._alert_rules_url(), payload)
            if status_code not in {200, 201, 202}:
                raise AlertingValidationError(
                    f"Grafana alert rule create failed with HTTP {status_code}"
                )
            return "created"
        if status_code != 200:
            raise AlertingValidationError(
                f"Grafana alert rule lookup failed with HTTP {status_code}"
            )

        status_code, _ = self._request("PUT", self._alert_rule_url(uid), payload)
        if status_code not in {200, 201, 202}:
            raise AlertingValidationError(
                f"Grafana alert rule update failed with HTTP {status_code}"
            )
        return "updated"

    def _contact_points_url(self) -> str:
        return f"{self.base_url}/api/v1/provisioning/contact-points"

    def _contact_point_url(self, uid: str) -> str:
        return f"{self._contact_points_url()}/{quote(uid, safe='')}"

    def _alert_rules_url(self) -> str:
        return f"{self.base_url}/api/v1/provisioning/alert-rules"

    def _alert_rule_url(self, uid: str) -> str:
        return f"{self._alert_rules_url()}/{quote(uid, safe='')}"

    def _folders_url(self) -> str:
        namespace = self._required_namespace()
        return (
            f"{self.base_url}/apis/folder.grafana.app/v1/"
            f"namespaces/{quote(namespace, safe='')}/folders"
        )

    def _folder_url(self, uid: str) -> str:
        return f"{self._folders_url()}/{quote(uid, safe='')}"

    def _required_namespace(self) -> str:
        if not self.namespace:
            raise AlertingValidationError(
                "GRAFANA_DASHBOARD_NAMESPACE environment variable is required "
                "to create or update alert folders"
            )
        return self.namespace

    def _request(
        self,
        method: str,
        url: str,
        payload: AlertingResource | None,
    ) -> tuple[int, Any]:
        return self._transport(
            method,
            url,
            payload,
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                PROVENANCE_HEADER: "true",
            },
        )


def deploy_from_manifest(
    *,
    manifest_path: Path,
    client: GrafanaAlertingClient | None,
    apply: bool,
    env: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    validate_or_raise(manifest_path)
    manifest = load_manifest(manifest_path)
    raw_folders = load_json(manifest.folders_file)["folders"]
    raw_contact_points = load_json(manifest.contact_points_file)["contact_points"]
    raw_rules_file = load_json(manifest.alert_rules_file)
    raw_rules = _materialize_rules(raw_rules_file)
    actions: list[tuple[str, str]] = []

    for folder in raw_folders:
        assert isinstance(folder, dict)
        uid = str(folder["uid"])
        action = _apply_or_dry_run(
            apply=apply,
            client=client,
            name=uid,
            payload=folder,
            apply_func="apply_folder",
        )
        actions.append((f"folder:{uid}", action))

    for contact_point in raw_contact_points:
        assert isinstance(contact_point, dict)
        name = str(contact_point["name"])
        payload = (
            _substitute_env(contact_point, env=env or os.environ)
            if apply
            else contact_point
        )
        action = _apply_or_dry_run(
            apply=apply,
            client=client,
            name=name,
            payload=payload,
            apply_func="apply_contact_point",
        )
        actions.append((f"contact-point:{name}", action))

    for rule in raw_rules:
        uid = str(rule["uid"])
        action = _apply_or_dry_run(
            apply=apply,
            client=client,
            name=uid,
            payload=rule,
            apply_func="apply_alert_rule",
        )
        actions.append((f"alert-rule:{uid}", action))
    return actions


def manifest_path_from_args(args: argparse.Namespace) -> Path:
    return Path(args.manifest).resolve()


def client_from_env() -> GrafanaAlertingClient:
    base_url = _required_env("GRAFANA_URL")
    token = _required_env("GRAFANA_SERVICE_ACCOUNT_TOKEN")
    namespace = _required_env("GRAFANA_DASHBOARD_NAMESPACE")
    return GrafanaAlertingClient(base_url=base_url, namespace=namespace, token=token)


def _apply_or_dry_run(
    *,
    apply: bool,
    client: GrafanaAlertingClient | None,
    name: str,
    payload: AlertingResource,
    apply_func: str,
) -> str:
    if not apply:
        return "dry-run"
    if client is None:
        raise AlertingValidationError("Grafana client is required when apply=True")
    method = getattr(client, apply_func)
    return str(method(payload))


def _materialize_rules(resource: AlertingResource) -> list[AlertingResource]:
    defaults = resource.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}
    raw_rules = resource.get("rules")
    if not isinstance(raw_rules, list):
        return []

    materialized: list[AlertingResource] = []
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            continue
        rule = copy.deepcopy(raw_rule)
        rule["datasource_uid"] = rule.get("datasource_uid") or defaults.get(
            "datasource_uid"
        )
        rule["folder_uid"] = rule.get("folder_uid") or defaults.get("folder_uid")
        rule["evaluation_group"] = rule.get("evaluation_group") or defaults.get(
            "evaluation_group"
        )
        rule["relative_time_range_seconds"] = rule.get(
            "relative_time_range_seconds",
            defaults.get("relative_time_range_seconds", 1800),
        )
        rule["labels"] = _merged_mapping(defaults.get("labels"), rule.get("labels"))
        rule["annotations"] = _merged_mapping(
            defaults.get("annotations"),
            rule.get("annotations"),
        )
        materialized.append(rule)
    return materialized


def _contact_point_payload(contact_point: AlertingResource) -> AlertingResource:
    return {
        "name": contact_point["name"],
        "type": contact_point["type"],
        "settings": contact_point["settings"],
        "disableResolveMessage": bool(contact_point.get("disable_resolve_message")),
    }


def _folder_payload(
    folder: AlertingResource,
    *,
    existing: AlertingResource | None = None,
) -> AlertingResource:
    metadata: AlertingResource = {"name": folder["uid"]}
    if existing is not None:
        existing_metadata = existing.get("metadata")
        if isinstance(existing_metadata, dict) and existing_metadata.get(
            "resourceVersion"
        ):
            metadata["resourceVersion"] = existing_metadata["resourceVersion"]
    return {
        "kind": "Folder",
        "apiVersion": "folder.grafana.app/v1",
        "metadata": metadata,
        "spec": {"title": folder["title"]},
    }


def _folder_title(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        raise AlertingValidationError(
            "Grafana folder lookup returned an unexpected payload"
        )
    spec = payload.get("spec")
    if not isinstance(spec, dict):
        return None
    title = spec.get("title")
    return title if isinstance(title, str) else None


def _alert_rule_payload(rule: AlertingResource) -> AlertingResource:
    datasource_uid = str(rule["datasource_uid"])
    return {
        "uid": rule["uid"],
        "title": rule["title"],
        "condition": "C",
        "folderUID": rule["folder_uid"],
        "ruleGroup": rule["evaluation_group"],
        "data": [
            {
                "refId": "A",
                "datasourceUid": datasource_uid,
                "relativeTimeRange": {
                    "from": int(rule["relative_time_range_seconds"]),
                    "to": 0,
                },
                "model": {
                    "datasource": {"type": "prometheus", "uid": datasource_uid},
                    "expr": rule["expr"],
                    "instant": False,
                    "intervalMs": 1000,
                    "legendFormat": "__auto",
                    "maxDataPoints": 43200,
                    "range": True,
                    "refId": "A",
                },
            },
            _expression_query(
                ref_id="B",
                expression="A",
                model_type="reduce",
                extra={"reducer": "last"},
            ),
            _threshold_query(rule),
        ],
        "for": rule["for"],
        "noDataState": rule["no_data_state"],
        "execErrState": rule["exec_error_state"],
        "annotations": rule["annotations"],
        "labels": rule["labels"],
        "isPaused": bool(rule.get("is_paused", False)),
    }


def _expression_query(
    *,
    ref_id: str,
    expression: str,
    model_type: str,
    extra: AlertingResource,
) -> AlertingResource:
    model = {
        "datasource": {"type": "__expr__", "uid": "__expr__"},
        "expression": expression,
        "hide": False,
        "intervalMs": 1000,
        "maxDataPoints": 43200,
        "refId": ref_id,
        "type": model_type,
    }
    model.update(extra)
    return {
        "refId": ref_id,
        "datasourceUid": "__expr__",
        "relativeTimeRange": {"from": 0, "to": 0},
        "model": model,
    }


def _threshold_query(rule: AlertingResource) -> AlertingResource:
    return _expression_query(
        ref_id="C",
        expression="B",
        model_type="threshold",
        extra={
            "conditions": [
                {
                    "evaluator": {
                        "params": [rule["threshold"]],
                        "type": rule["operator"],
                    },
                    "operator": {"type": "and"},
                    "query": {"params": ["C"]},
                    "reducer": {"params": [], "type": "last"},
                    "type": "query",
                }
            ],
        },
    )


def _urlopen_transport(
    method: str,
    url: str,
    payload: AlertingResource | None,
    headers: dict[str, str],
) -> tuple[int, Any]:
    encoded_payload = None
    if payload is not None:
        encoded_payload = json.dumps(payload).encode("utf-8")
    request = Request(url, data=encoded_payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as error:
        if error.code == 404:
            return 404, {}
        body = error.read().decode("utf-8")
        raise AlertingValidationError(
            f"Grafana API {method} {url} failed with HTTP {error.code}: {body}"
        ) from error


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise AlertingValidationError(f"{name} environment variable is required")
    return value


def _substitute_env(value: Any, *, env: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _substitute_env(item, env=env) for key, item in value.items()}
    if isinstance(value, list):
        return [_substitute_env(item, env=env) for item in value]
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        replacement = env.get(name)
        if not replacement:
            raise AlertingValidationError(f"{name} environment variable is required")
        return replacement

    return re.sub(r"\$\{([A-Z0-9_]+)\}", replace, value)


def _relative_manifest_path(
    manifest: AlertingResource,
    key: str,
    *,
    root: Path,
) -> Path:
    raw_path = manifest.get(key)
    if not isinstance(raw_path, str) or not raw_path:
        raise AlertingManifestError(f"{key} is required")
    path = Path(raw_path)
    if path.is_absolute():
        raise AlertingManifestError(f"{key} must be relative")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise AlertingManifestError(f"{key} must stay inside {root}")
    return path


def _merged_mapping(*values: object) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for value in values:
        if isinstance(value, dict):
            merged.update(value)
    return merged


def _validate_promql(expr: str, *, index: int) -> list[str]:
    errors: list[str] = []
    if "irate(" in expr:
        errors.append(f"rules[{index}].expr must not use irate for alerts")
    if "histogram_quantile(" in expr and "sum by (le)" not in expr:
        errors.append(f"rules[{index}].expr histogram_quantile must aggregate by le")
    if ("_total" in expr or "_bucket" in expr) and not re.search(
        r"\[[0-9]+[smhd]\]",
        expr,
    ):
        errors.append(f"rules[{index}].expr counter/histogram alerts must use a range")
    if _uses_arithmetic_division(expr) and "clamp_min(" not in expr:
        errors.append(f"rules[{index}].expr ratio denominator must use clamp_min")
    return errors


def _uses_arithmetic_division(expr: str) -> bool:
    return bool(re.search(r"\)\s*/\s*", expr))


def _find_contact_point_uid(payload: Any, *, name: str) -> str | None:
    if not isinstance(payload, list):
        raise AlertingValidationError(
            "Grafana contact point lookup returned an unexpected payload"
        )
    matches: list[str] = []
    for contact_point in payload:
        if not isinstance(contact_point, dict):
            continue
        if contact_point.get("name") != name:
            continue
        uid = contact_point.get("uid")
        if isinstance(uid, str) and uid:
            matches.append(uid)
    unique_matches = sorted(set(matches))
    if not unique_matches:
        return None
    if len(unique_matches) > 1:
        raise AlertingValidationError(
            f"Multiple Grafana contact points named {name!r} were found"
        )
    return unique_matches[0]


def _has_sensitive_label_part(label: str) -> bool:
    return any(part in label.lower() for part in SENSITIVE_LABEL_PARTS)
