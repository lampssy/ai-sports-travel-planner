from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.maintainer.boundary_adjudication import validate_boundary_adjudication
from ops.maintainer.cli import main
from ops.maintainer.errors import ErrorCheck, ErrorKind, ErrorReason, MaintainerError

pytestmark = pytest.mark.db_free


def _gate(status: str, evidence_ref: str) -> dict[str, object]:
    return {
        "status": status,
        "evidence_refs": [evidence_ref],
        "rationale": "The frozen evidence packet supports this gate outcome.",
    }


def _material_consequence(target_id: str) -> dict[str, object]:
    return {
        "consequence_type": "stay_access_or_transfer_mechanics",
        "decision_effect": "selected_ski_area",
        "comparison_basis": "sibling_ski_area",
        "comparison_target_id": target_id,
        "evidence_refs": ["mottolino-transfer"],
        "rationale": (
            "The primary ski-day choice changes because the areas require a transfer."
        ),
    }


def _separate_candidate(
    candidate_id: str,
    comparison_target_id: str,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "decision": "separate_ski_area",
        "terrain_gate": _gate("pass", f"{candidate_id}-terrain"),
        "evidence_ownership_gate": _gate("pass", f"{candidate_id}-owner"),
        "materiality_gate": _gate("pass", f"{candidate_id}-materiality"),
        "material_trip_consequence": _material_consequence(comparison_target_id),
    }


def _valid_payload() -> dict[str, object]:
    return {
        "outcome": "policy_determined",
        "candidates": [
            _separate_candidate("mottolino", "livigno-west"),
            _separate_candidate("livigno-west", "mottolino"),
            {
                "candidate_id": "sitas",
                "decision": "fold_into_parent",
                "parent_ski_area_id": "livigno-west",
                "terrain_gate": _gate("pass", "sitas-terrain"),
                "evidence_ownership_gate": _gate("pass", "sitas-owner"),
                "materiality_gate": _gate("fail", "sitas-no-materiality"),
                "material_trip_consequence": None,
            },
        ],
    }


def _write_payload(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "boundary-adjudication.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_policy_determined_accepts_separate_area_with_all_gates_and_folded_component(
    tmp_path: Path,
) -> None:
    result = validate_boundary_adjudication(_write_payload(tmp_path, _valid_payload()))

    assert result.outcome == "policy_determined"
    assert result.separate_ski_area_ids == ("livigno-west", "mottolino")
    assert result.folded_candidate_ids == ("sitas",)


def test_policy_determined_rejects_promoted_area_without_material_consequence(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    candidates[0]["material_trip_consequence"] = None

    with pytest.raises(MaintainerError) as exc_info:
        validate_boundary_adjudication(_write_payload(tmp_path, payload))

    assert exc_info.value.reason is ErrorReason.VALIDATION_FAILED
    assert exc_info.value.check is ErrorCheck.BOUNDARY_ADJUDICATION
    assert exc_info.value.kind is ErrorKind.MISMATCH


def test_policy_determined_rejects_material_consequence_without_evidence(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    consequence = candidates[0]["material_trip_consequence"]
    assert isinstance(consequence, dict)
    consequence["evidence_refs"] = []

    with pytest.raises(MaintainerError) as exc_info:
        validate_boundary_adjudication(_write_payload(tmp_path, payload))

    assert exc_info.value.check is ErrorCheck.BOUNDARY_ADJUDICATION


def test_policy_determined_rejects_promoted_area_without_a_valid_comparison_target(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    consequence = candidates[0]["material_trip_consequence"]
    assert isinstance(consequence, dict)
    consequence["comparison_target_id"] = "unknown-area"

    with pytest.raises(MaintainerError) as exc_info:
        validate_boundary_adjudication(_write_payload(tmp_path, payload))

    assert exc_info.value.check is ErrorCheck.BOUNDARY_ADJUDICATION


def test_policy_determined_rejects_self_referential_sibling_comparison(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    consequence = candidates[0]["material_trip_consequence"]
    assert isinstance(consequence, dict)
    consequence["comparison_target_id"] = "mottolino"

    with pytest.raises(MaintainerError) as exc_info:
        validate_boundary_adjudication(_write_payload(tmp_path, payload))

    assert exc_info.value.check is ErrorCheck.BOUNDARY_ADJUDICATION


def test_policy_determined_rejects_an_evidence_insufficient_candidate(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    candidates[2]["decision"] = "evidence_insufficient"
    candidates[2]["materiality_gate"] = _gate(
        "evidence_insufficient",
        "sitas-materiality-gap",
    )
    candidates[2]["parent_ski_area_id"] = None

    with pytest.raises(MaintainerError) as exc_info:
        validate_boundary_adjudication(_write_payload(tmp_path, payload))

    assert exc_info.value.check is ErrorCheck.BOUNDARY_ADJUDICATION


def test_cli_returns_the_validated_boundary_adjudication(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_payload(tmp_path, _valid_payload())

    code = main(
        [
            "validate",
            "boundary-adjudication",
            "--input",
            str(path),
            "--run-id",
            "1" * 32,
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["adjudication"] == {
        "outcome": "policy_determined",
        "separate_ski_area_ids": ["livigno-west", "mottolino"],
        "folded_candidate_ids": ["sitas"],
        "evidence_insufficient_candidate_ids": [],
    }
