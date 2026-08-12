from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.db_free

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ACTIVATION_PATH = (
    REPOSITORY_ROOT / "docs/operating-model/local-maintainer-activation.md"
)
DESIGN_PATH = (
    REPOSITORY_ROOT
    / "docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md"
)
RUNTIME_CONTRACT_PATH = (
    REPOSITORY_ROOT / "docs/operating-model/maintainer-runtime-command-contract.md"
)


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split()).lower()


def test_incomplete_inventory_enters_completion_before_blocking() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "inventory-completion" in contract, path
        assert "at most two inventory-completion passes" in contract, path
        assert "fresh independent source-trust and graph-scope" in contract, path
        assert "strictly smaller" in contract, path
        assert "review-incomplete" in contract, path


def test_inventory_completion_cannot_mutate_catalog_or_trust() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "exactly the canonical report path" in contract, path
        assert "catalog and trust blobs and object ids remain identical" in contract, (
            path
        )
        assert "does not consume a remediation cycle" in contract, path
        assert "cannot authorize catalog or trust remediation" in contract, path


def test_inventory_completion_uses_structured_missing_item_checklists() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        for field in (
            "missing_item_id",
            "category",
            "candidate_keys",
            "missing_evidence",
            "acceptance_criterion",
            "scope_class",
            "graph_impact",
        ):
            assert field in contract, (path, field)


def test_inventory_completion_stops_on_no_progress_or_unsafe_scope() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "no measurable progress" in contract, path
        assert "evidence remains unavailable" in contract, path
        assert "unsafe scope expansion" in contract, path
        assert "second completion pass" in contract, path
        assert "inventory-completion pass count" in contract, path
        assert "remaining unresolved checklist count" in contract, path


def test_inventory_completion_creates_no_helper_owned_recovery_authority() -> None:
    contract = _normalized(RUNTIME_CONTRACT_PATH)
    assert "inventory-completion" in contract
    assert "does not persist" in contract
    assert "no helper continuation" in contract
