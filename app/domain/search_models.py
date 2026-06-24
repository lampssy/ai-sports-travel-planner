from __future__ import annotations

import os
from dataclasses import dataclass

from app.config.env import load_dotenv_file
from app.domain.models import SearchModelVersion

SEARCH_MODEL_ENV_VAR = "SNOWCAST_SEARCH_MODEL"
ALLOW_SEARCH_MODEL_OVERRIDE_ENV_VAR = "SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE"
DEFAULT_SEARCH_MODEL: SearchModelVersion = "search_v1"
VALID_SEARCH_MODELS: tuple[SearchModelVersion, ...] = ("search_v1", "search_v2")


class InvalidSearchModelError(ValueError):
    pass


@dataclass(frozen=True)
class SearchModelSelection:
    configured_search_model: SearchModelVersion
    requested_search_model: SearchModelVersion | None
    effective_search_model: SearchModelVersion
    override_allowed: bool
    override_applied: bool


def resolve_search_model_selection(
    *,
    requested_model: str | None = None,
) -> SearchModelSelection:
    load_dotenv_file()
    configured_search_model = _parse_search_model(
        os.getenv(SEARCH_MODEL_ENV_VAR, DEFAULT_SEARCH_MODEL),
        source=SEARCH_MODEL_ENV_VAR,
    )
    requested_search_model = (
        _parse_search_model(requested_model, source="search_model")
        if requested_model is not None
        else None
    )
    override_allowed = _env_bool(ALLOW_SEARCH_MODEL_OVERRIDE_ENV_VAR)
    override_applied = requested_search_model is not None and override_allowed
    return SearchModelSelection(
        configured_search_model=configured_search_model,
        requested_search_model=requested_search_model,
        effective_search_model=(
            requested_search_model if override_applied else configured_search_model
        ),
        override_allowed=override_allowed,
        override_applied=override_applied,
    )


def _parse_search_model(value: str, *, source: str) -> SearchModelVersion:
    normalized = value.strip()
    if normalized in VALID_SEARCH_MODELS:
        return normalized
    valid = ", ".join(VALID_SEARCH_MODELS)
    raise InvalidSearchModelError(f"{source} must be one of: {valid}; got {value!r}")


def _env_bool(name: str) -> bool:
    value = os.getenv(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}
