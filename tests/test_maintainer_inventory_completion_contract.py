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
SKI_AREA_BOUNDARY_ADR_PATH = (
    REPOSITORY_ROOT
    / "docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md"
)


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").replace("`", "").split()).lower()


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
        assert "canonical json report and deterministic markdown companion" in (
            contract
        ), path
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


def test_inventory_completion_persists_only_a_terminal_gate_marker() -> None:
    contract = _normalized(RUNTIME_CONTRACT_PATH)
    assert "inventory-completion" in contract
    assert "does not persist its checklist" in contract
    assert "completed-checkpoint marker" in contract
    assert "direct delta from the previous checkpoint" in contract
    assert "canonical json report and its deterministic markdown companion" in contract
    assert "local head still equal to the marked head" in contract
    assert "no helper continuation" in contract


def test_inventory_items_are_classified_before_the_completion_gate() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "inventory_outcome" in contract, path
        for outcome in (
            "inventory_missing",
            "verified_complete",
            "actionable_finding",
            "defensible_deferred",
            "evidence_unavailable",
        ):
            assert outcome in contract, (path, outcome)


def test_actionable_findings_and_deferrals_leave_the_missing_checklist() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "promote it to the finding ledger" in contract, path
        assert "remove it from the missing-inventory checklist" in contract, path
        assert (
            "requires a catalog, trust, backlog, rendered-report, or "
            "focused-test change"
        ) in contract, path
        assert "does not by itself make review incomplete" in contract, path


def test_optional_scalar_evidence_gaps_are_actionable_not_review_incomplete() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "optional scalar fact" in contract, path
        assert "must be actionable_finding" in contract, path
        assert "retain it as a clearly labeled proxy" in contract, path
        assert "verified_with_adjustment" in contract, path
        assert "remove or clear the unsupported value" in contract, path
        assert "must not be evidence_unavailable" in contract, path
        assert "does not block evidence-envelope freeze" in contract, path


def test_evidence_unavailable_is_reserved_for_graph_critical_unknowns() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert (
            "graph-critical identity, ownership, access, or pass-validity fact"
            in contract
        ), path
        assert "no graph-safe conservative representation" in contract, path


def test_terminal_unavailable_outcomes_require_researched_disposition() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "research_required_candidate" in contract, path
        assert "exact missing fact" in contract, path
        assert "affected target ids" in contract, path
        assert "source attempts" in contract, path
        assert "mixed set remains review-incomplete" in contract, path


def test_stale_rendered_report_is_an_actionable_finding() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "stale rendered markdown" in contract, path
        assert "actionable_finding" in contract, path
        assert "does not make review incomplete" in contract, path


def test_report_mutations_keep_json_and_markdown_in_sync_before_checkpoint() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "canonical json report and deterministic markdown companion" in (
            contract
        ), path
        assert "before any delta or reviewed checkpoint" in contract, path
        assert "boundary_target_ids" in contract, path
        assert "same fixer pass" in contract, path


def test_strictly_smaller_checklist_requires_the_permitted_second_pass() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "must run the second inventory-completion pass" in contract, path
        assert (
            "a prediction that the second pass will not complete every item is "
            "not a stop condition"
        ) in contract, path


def test_deferral_graph_impact_controls_remediation_obligation() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "graph-blocking defensible deferral" in contract, path
        assert "create an actionable graph-safety finding" in contract, path
        assert (
            "make the selected graph internally valid without the deferred dependency"
            in contract
        ), path
        assert "regional-followup defensible deferral" in contract, path
        assert "requires no remediation finding" in contract, path


def test_conflicting_inventory_outcomes_remain_fail_closed() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "conflicting inventory outcomes or graph-impact classifications" in (
            contract
        ), path
        assert "remains inventory_missing until reconciled" in contract, path


def test_mixed_unavailable_items_do_not_cancel_researchable_work() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "exclude evidence_unavailable items from further research" in (
            contract
        ), path
        assert "does not cancel the second pass for inventory_missing items" in (
            contract
        ), path


def test_new_actionable_blockers_enter_the_ledger_not_the_checklist() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "new actionable graph blocker enters the finding ledger" in (contract), (
            path
        )
        assert "does not prevent the second inventory-completion pass" in contract, path


def test_second_pass_uses_the_objective_new_work_cutoff() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "before the 210-minute new-work cutoff" in contract, path
        assert "item-specific unsafe scope boundary" in contract, path


def test_activation_requires_installed_skill_transition_parity() -> None:
    contract = _normalized(ACTIVATION_PATH)
    assert "all five inventory outcomes" in contract
    assert "graph-impact deferral transition" in contract
    assert "lane-conflict aggregation rule" in contract
    assert "mixed unavailable/researchable second-pass rule" in contract
    assert "optional-scalar disposition rule" in contract
    assert "keep both schedules paused as contract-mismatch" in contract


def test_operations_ownership_research_covers_official_sources() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH, SKI_AREA_BOUNDARY_ADR_PATH):
        contract = _normalized(path)
        assert "operator or consortium member directory" in contract, path
        assert "candidate-scoped live status or opening presentation" in contract, path
        assert "separate hostname" in contract, path


def test_official_sources_can_jointly_prove_operations_ownership() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH, SKI_AREA_BOUNDARY_ADR_PATH):
        contract = _normalized(path)
        assert "jointly establish operations ownership" in contract, path
        assert "separate company or member page alone" in contract, path
        assert "supporting evidence only" in contract, path


def test_operations_ownership_requires_source_family_exhaustion() -> None:
    for path in (ACTIVATION_PATH, DESIGN_PATH):
        contract = _normalized(path)
        assert "before evidence_unavailable" in contract, path
        assert "record the exact source families attempted" in contract, path
