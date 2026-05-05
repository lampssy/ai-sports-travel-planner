from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

from app.data.resort_acquisition.models import AcquisitionRunOutput, Proposal


def write_run_outputs(output_dir: Path, output: AcquisitionRunOutput) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _recreate_empty_directory(output_dir / "source-snapshots")

    (output_dir / "proposals.json").write_text(
        json.dumps(output.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "fetch-log.json").write_text(
        json.dumps(
            [entry.model_dump(mode="json") for entry in output.fetch_log],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (output_dir / "evidence.md").write_text(
        render_evidence_markdown(output),
        encoding="utf-8",
    )


def render_evidence_markdown(output: AcquisitionRunOutput) -> str:
    selected_resorts = (
        ", ".join(_markdown_inline(resort_id) for resort_id in output.selected_resorts)
        or "(none)"
    )
    lines = [
        "# Resort Catalog Acquisition Evidence",
        "",
        f"Generated at: `{output.generated_at.isoformat()}`",
        f"Selected resorts: {selected_resorts}",
        "",
    ]

    if not output.proposals:
        lines.append("No proposals generated.")
        return "\n".join(lines) + "\n"

    proposals_by_resort: dict[str, list[Proposal]] = defaultdict(list)
    for proposal in output.proposals:
        proposals_by_resort[proposal.resort_id].append(proposal)

    for resort_id in sorted(proposals_by_resort):
        lines.extend([f"## {_markdown_inline(resort_id)}", ""])
        proposals = sorted(
            enumerate(proposals_by_resort[resort_id], start=1),
            key=lambda indexed_proposal: (
                indexed_proposal[1].target.entity_type,
                indexed_proposal[1].target.entity_id,
                indexed_proposal[1].field_path,
            ),
        )
        for ordinal, proposal in proposals:
            lines.extend(_proposal_markdown_lines(proposal, ordinal))

    return "\n".join(lines).rstrip() + "\n"


def _proposal_markdown_lines(proposal: Proposal, ordinal: int) -> list[str]:
    lines = [
        f"### `{proposal.field_path}` proposal {ordinal}",
        "",
        f"- Status: {proposal.status}",
        f"- Target: `{_markdown_inline(_target_label(proposal))}`",
        f"- Current value: `{_json_inline(proposal.current_value)}`",
        f"- Proposed value: `{_json_inline(proposal.proposed_value)}`",
        f"- Source: {_source_label(proposal)}",
        f"- Method: {proposal.extraction_method}",
        f"- Confidence: {proposal.confidence}",
    ]
    if proposal.evidence:
        lines.append(f"- Evidence: {_markdown_inline(proposal.evidence)}")
    if proposal.validation_notes:
        validation_notes = "; ".join(
            _markdown_inline(note) for note in proposal.validation_notes
        )
        lines.append(f"- Validation notes: {validation_notes}")
    lines.append("")
    return lines


def _target_label(proposal: Proposal) -> str:
    return f"{proposal.target.entity_type}:{proposal.target.entity_id}"


def _source_label(proposal: Proposal) -> str:
    if proposal.source.source_url:
        return _markdown_inline(proposal.source.source_url)
    if proposal.source.source_name:
        return _markdown_inline(proposal.source.source_name)
    return "(unknown)"


def _json_inline(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _markdown_inline(value: str) -> str:
    text = re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "\\`")
    )


def _recreate_empty_directory(directory: Path) -> None:
    if directory.is_symlink() or directory.is_file():
        directory.unlink()
    elif directory.exists():
        for child in directory.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    directory.mkdir(exist_ok=True)
