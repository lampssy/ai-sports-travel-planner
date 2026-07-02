import pytest

from app.domain.search_models import (
    InvalidSearchModelError,
    resolve_search_model_selection,
)


def test_search_model_selection_defaults_to_v3(monkeypatch) -> None:
    monkeypatch.delenv("SNOWCAST_SEARCH_MODEL", raising=False)
    monkeypatch.delenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", raising=False)

    selection = resolve_search_model_selection()

    assert selection.configured_search_model == "search_v3"
    assert selection.requested_search_model is None
    assert selection.effective_search_model == "search_v3"
    assert selection.override_allowed is False
    assert selection.override_applied is False


def test_search_model_selection_reads_configured_model(monkeypatch) -> None:
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v2")
    monkeypatch.delenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", raising=False)

    selection = resolve_search_model_selection()

    assert selection.configured_search_model == "search_v2"
    assert selection.effective_search_model == "search_v2"


def test_search_model_selection_applies_request_override_only_when_allowed(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v1")
    monkeypatch.delenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", raising=False)

    disabled = resolve_search_model_selection(requested_model="search_v2")

    assert disabled.configured_search_model == "search_v1"
    assert disabled.requested_search_model == "search_v2"
    assert disabled.effective_search_model == "search_v1"
    assert disabled.override_allowed is False
    assert disabled.override_applied is False

    monkeypatch.setenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", "true")

    enabled = resolve_search_model_selection(requested_model="search_v2")

    assert enabled.configured_search_model == "search_v1"
    assert enabled.requested_search_model == "search_v2"
    assert enabled.effective_search_model == "search_v2"
    assert enabled.override_allowed is True
    assert enabled.override_applied is True


def test_search_model_selection_rejects_unknown_model(monkeypatch) -> None:
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v4")

    with pytest.raises(InvalidSearchModelError):
        resolve_search_model_selection()
