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


@pytest.mark.parametrize("retired_model", ["search_v1", "search_v2"])
def test_search_model_selection_rejects_retired_configured_models(
    monkeypatch, retired_model: str
) -> None:
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", retired_model)

    with pytest.raises(InvalidSearchModelError, match="search_v3"):
        resolve_search_model_selection()


@pytest.mark.parametrize("retired_model", ["search_v1", "search_v2"])
def test_search_model_selection_rejects_retired_request_overrides(
    monkeypatch, retired_model: str
) -> None:
    monkeypatch.delenv("SNOWCAST_SEARCH_MODEL", raising=False)
    monkeypatch.setenv("SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE", "true")

    with pytest.raises(InvalidSearchModelError, match="search_v3"):
        resolve_search_model_selection(requested_model=retired_model)


def test_search_model_selection_rejects_unknown_model(monkeypatch) -> None:
    monkeypatch.setenv("SNOWCAST_SEARCH_MODEL", "search_v4")

    with pytest.raises(InvalidSearchModelError):
        resolve_search_model_selection()
