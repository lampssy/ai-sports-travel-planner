from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.data.resort_acquisition.models import (
    AcquisitionRunOutput,
    FetchLogEntry,
    Proposal,
)

_STATUS_SEVERITY = {
    "conflict": 0,
    "warning": 1,
    "changed": 2,
    "new": 3,
    "rejected": 4,
    "same": 5,
}
_REPEATABLE_FIELD_PATHS = {"lift_pass_prices", "rental_facts"}
_SEASON_WINDOW_IDENTITY_FIELDS = ("start_date", "end_date", "status")


@dataclass(frozen=True)
class _ProposalGroupKey:
    resort_id: str
    target_entity_type: str
    target_entity_id: str
    field_path: str


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
    lines.extend(_source_health_markdown_lines(output))

    if not output.proposals:
        lines.append("No proposals generated.")
        return "\n".join(lines) + "\n"

    grouped_proposals: dict[_ProposalGroupKey, list[Proposal]] = defaultdict(list)
    for proposal in output.proposals:
        grouped_proposals[_group_key(proposal)].append(proposal)

    last_resort_id: str | None = None
    for key, proposals in sorted(
        grouped_proposals.items(), key=_proposal_group_sort_key
    ):
        if key.resort_id != last_resort_id:
            lines.extend([f"## {_markdown_code_span(key.resort_id)}", ""])
            last_resort_id = key.resort_id
        lines.extend(_proposal_group_markdown_lines(key, proposals))

    return "\n".join(lines).rstrip() + "\n"


def _source_health_markdown_lines(output: AcquisitionRunOutput) -> list[str]:
    failures = [entry for entry in output.fetch_log if entry.status == "failed"]
    warnings = [entry for entry in output.fetch_log if entry.status == "warning"]
    if not failures and not warnings:
        return ["## Source Health", "", "No source fetch failures or warnings.", ""]

    lines = ["## Source Health", ""]
    if failures:
        lines.append(f"Fetch failures: `{len(failures)}`")
        lines.extend(_source_health_entries_markdown_lines(failures))
        lines.append("")
    if warnings:
        lines.append(f"Fetch warnings: `{len(warnings)}`")
        lines.extend(_source_health_entries_markdown_lines(warnings))
        lines.append("")
    return lines


def _source_health_entries_markdown_lines(entries: list[FetchLogEntry]) -> list[str]:
    lines: list[str] = []
    for entry in sorted(entries, key=lambda item: (item.resort_id, item.url)):
        details = [
            f"resort={_markdown_inline(entry.resort_id)}",
            f"url={_markdown_inline(entry.url)}",
        ]
        if entry.extraction_method:
            details.append(f"method={entry.extraction_method}")
        if entry.status_code is not None:
            details.append(f"status_code={entry.status_code}")
        if entry.error:
            details.append(f"error={_markdown_inline(entry.error)}")
        lines.append(f"- {'; '.join(details)}")
    return lines


def _proposal_group_markdown_lines(
    key: _ProposalGroupKey, proposals: list[Proposal]
) -> list[str]:
    first_proposal = proposals[0]
    target_label = f"{key.target_entity_type}:{key.target_entity_id}"
    statuses = sorted({proposal.status for proposal in proposals}, key=_status_severity)
    heading = (
        f"### {_markdown_code_span(target_label)} / "
        f"{_markdown_code_span(key.field_path)}"
    )
    lines = [
        heading,
        "",
        f"- Statuses: {', '.join(statuses)}",
        f"- Target: {_markdown_code_span(target_label)}",
        f"- Current value: {_json_markdown_inline(first_proposal.current_value)}",
        f"- Recommended value: {_recommended_value(key, proposals)}",
    ]
    for proposal in sorted(proposals, key=_proposal_evidence_sort_key):
        lines.append(_proposal_evidence_bullet(proposal))
    lines.append("")
    return lines


def _proposal_evidence_bullet(proposal: Proposal) -> str:
    details = [
        f"Source: {_source_label(proposal)}",
        f"Method: {proposal.extraction_method}",
        f"Confidence: {proposal.confidence}",
        f"Proposed value: {_json_markdown_inline(proposal.proposed_value)}",
    ]
    evidence = _markdown_inline(proposal.evidence) if proposal.evidence else "(none)"
    details.append(f"Evidence: {evidence}")
    validation_notes = (
        "; ".join(_markdown_inline(note) for note in proposal.validation_notes)
        if proposal.validation_notes
        else "(none)"
    )
    details.append(f"Validation notes: {validation_notes}")
    return f"- {'; '.join(details)}"


def _group_key(proposal: Proposal) -> _ProposalGroupKey:
    return _ProposalGroupKey(
        resort_id=proposal.resort_id,
        target_entity_type=proposal.target.entity_type,
        target_entity_id=proposal.target.entity_id,
        field_path=proposal.field_path,
    )


def _group_severity(proposals: list[Proposal]) -> int:
    return min(_status_severity(proposal.status) for proposal in proposals)


def _proposal_group_sort_key(
    group: tuple[_ProposalGroupKey, list[Proposal]],
) -> tuple[int, str, str, str, str]:
    key, proposals = group
    return (
        _group_severity(proposals),
        key.resort_id,
        key.target_entity_type,
        key.target_entity_id,
        key.field_path,
    )


def _status_severity(status: str) -> int:
    return _STATUS_SEVERITY.get(status, len(_STATUS_SEVERITY))


def _recommended_value(key: _ProposalGroupKey, proposals: list[Proposal]) -> str:
    if any(proposal.status == "conflict" for proposal in proposals):
        return "review required"
    if key.field_path == "season_windows":
        recommended = _recommended_matching_season_window(proposals)
        if recommended is not None:
            return _markdown_inline(_json_inline(recommended.proposed_value))
    distinct_values = {
        _json_inline(proposal.proposed_value)
        for proposal in proposals
        if proposal.status != "rejected"
    }
    if len(distinct_values) == 1:
        return _markdown_inline(next(iter(distinct_values)))
    if key.field_path in _REPEATABLE_FIELD_PATHS and len(distinct_values) > 1:
        return "multiple proposals"
    return "review required"


def _recommended_matching_season_window(proposals: list[Proposal]) -> Proposal | None:
    candidates = [proposal for proposal in proposals if proposal.status != "rejected"]
    if not candidates:
        return None
    identity_keys = {
        _season_window_identity_key(proposal.proposed_value) for proposal in candidates
    }
    if len(identity_keys) != 1 or None in identity_keys:
        return None
    return max(candidates, key=lambda proposal: proposal.confidence)


def _proposal_evidence_sort_key(proposal: Proposal) -> tuple[int, str, str, str]:
    return (
        _status_severity(proposal.status),
        proposal.extraction_method,
        _source_label(proposal),
        _json_inline(proposal.proposed_value),
    )


def _source_label(proposal: Proposal) -> str:
    if proposal.source.source_url:
        return _markdown_inline(proposal.source.source_url)
    if proposal.source.source_name:
        return _markdown_inline(proposal.source.source_name)
    return "(unknown)"


def _json_inline(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _season_window_identity_key(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    identity = {
        field: value.get(field)
        for field in _SEASON_WINDOW_IDENTITY_FIELDS
        if value.get(field) is not None
    }
    if set(identity) != set(_SEASON_WINDOW_IDENTITY_FIELDS):
        return None
    return _json_inline(identity)


def _json_markdown_inline(value: object) -> str:
    return _markdown_inline(_json_inline(value))


def _markdown_inline(value: str) -> str:
    text = re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "\\`")
    )


def _markdown_code_span(value: str) -> str:
    text = re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    longest_backtick_run = max(
        (len(match.group(0)) for match in re.finditer(r"`+", text)),
        default=0,
    )
    fence = "`" * (longest_backtick_run + 1)
    if longest_backtick_run:
        return f"{fence} {text} {fence}"
    return f"{fence}{text}{fence}"


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
