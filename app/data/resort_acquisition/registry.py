from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.data.resort_acquisition.models import OfficialUrlRole, SourceRegistry

DEFAULT_SOURCE_REGISTRY_PATH = Path(__file__).with_name("sources.json")


def load_source_registry(path: Path = DEFAULT_SOURCE_REGISTRY_PATH) -> SourceRegistry:
    try:
        raw_registry = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read source registry JSON: {path}") from exc

    _validate_raw_registry(raw_registry)
    return SourceRegistry.model_validate(raw_registry)


def _validate_raw_registry(raw_registry: Any) -> None:
    if not isinstance(raw_registry, dict):
        raise ValueError("source registry must be a JSON object")

    resorts = raw_registry.get("resorts")
    if not isinstance(resorts, dict):
        raise ValueError("source registry resorts must be a JSON object")

    for resort_id, resort_config in resorts.items():
        if not isinstance(resort_id, str) or not resort_id.strip():
            raise ValueError("source registry resort IDs must be non-empty strings")
        if not isinstance(resort_config, dict):
            raise ValueError(
                f"source registry resort entry must be an object: {resort_id}"
            )

        if "official_urls" not in resort_config:
            raise ValueError(f"official_urls must be an object: {resort_id}")
        official_urls = resort_config["official_urls"]
        if not isinstance(official_urls, dict):
            raise ValueError(f"official_urls must be an object: {resort_id}")

        _validate_official_url_roles(resort_id, official_urls)


def _validate_official_url_roles(resort_id: str, official_urls: dict[Any, Any]) -> None:
    supported_roles = set(OfficialUrlRole.__args__)
    for role in official_urls:
        if role not in supported_roles:
            raise ValueError(f"unsupported official URL role for {resort_id}: {role}")
