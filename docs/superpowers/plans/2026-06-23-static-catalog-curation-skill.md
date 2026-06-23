# Static Catalog Curation Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static catalog acquisition PR workflow with a Snowcast catalog-curation skill plus typed evidence/report validation.

**Architecture:** Approved catalog truth remains in `app/data/resorts.json` and `app/data/resort_trust_manifest.json`. Agent-assisted curation handles source research and edits, while new Pydantic contracts and policy validators enforce evidence shape, trust constraints, cross-field consistency, and reviewer-friendly Markdown reports. The old GitHub Actions acquisition entry point is removed from the primary workflow, but internal acquisition modules are left in place until a separate cleanup classifies salvageable provider helpers.

**Tech Stack:** Python, Pydantic, pytest, Markdown report rendering, existing Snowcast catalog validator, existing ranking comparison diagnostics, Codex skill files under `/Users/awownysz/.codex/skills`.

---

## Scope Check

This plan implements the static catalog curation replacement path only.

It does not build the future operational-status refresh pipeline. It does not implement Bergfex freshness alerts. It does not delete all `app/data/resort_acquisition/` modules in the first pass because the current acquisition test suite is large and some helpers may still be useful for future sentinel/source diagnostics.

## File Structure

- Create `app/data/catalog_curation.py`: Pydantic models, report loader, report validator, and Markdown renderer for static catalog curation evidence.
- Create `app/data/validate_catalog_curation.py`: thin CLI wrapper around `catalog_curation` contracts.
- Create `app/data/catalog_policy.py`: reusable cross-field consistency checks for loaded `Destination` models.
- Modify `app/data/validate_resort_catalog.py`: call `catalog_policy` and expose policy warnings/errors without mixing policy code into the CLI.
- Create `tests/test_catalog_curation.py`: unit tests for curation contracts, validation, Markdown output, and CLI behavior.
- Modify `tests/test_catalog_validation.py`: tests for the new cross-field catalog policy checks.
- Modify `tests/test_resort_acquisition.py`: remove the test that asserts the static catalog acquisition workflow can create PRs.
- Delete `.github/workflows/catalog-acquisition.yml`: remove the primary static acquisition Actions entry point.
- Create `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`: local Codex skill for source-backed static catalog curation.
- Create `docs/architecture/adr/0004-static-catalog-curation-skill.md`: durable architecture decision record.
- Modify `README.md`: replace static acquisition instructions with the skill-led curation workflow.
- Modify `docs/data-trust-model.md`: document typed evidence/report contracts.
- Modify `docs/engineering-notes.md`: record the curation model and Bergfex boundary.

## Task 1: Advisory Design Review Gate

**Files:**
- Read: `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`
- Read: `docs/operating-model/advisory-reviewers.md`
- Read: `docs/operating-model/review-playbook.md`

- [ ] **Step 1: Run design review**

Use the Snowcast review system in `design-review` mode with these reviewers:

```text
data-trust-source-integrity
backend-api
ai-llm-reliability
```

Review target:

```text
docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md
```

Expected: no blocker findings, or concrete findings to resolve before Task 2.

- [ ] **Step 2: Resolve review findings**

If the review finds issues, update the design spec before continuing. Keep the scope limited to static catalog curation, typed validation, report reviewability, and static acquisition deprecation.

- [ ] **Step 3: Commit review-driven spec edits if any**

If Step 2 changed files:

```bash
git add docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md
git commit -m "docs: refine static catalog curation design"
```

Expected: no commit if there were no design-review edits.

## Task 2: Architecture Decision Record

**Files:**
- Create: `docs/architecture/adr/0004-static-catalog-curation-skill.md`

- [ ] **Step 1: Write the ADR**

Create `docs/architecture/adr/0004-static-catalog-curation-skill.md`:

```markdown
# ADR 0004: Use Skill-Led Static Catalog Curation

Status: accepted
Date: 2026-06-23

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`
- `docs/superpowers/specs/2026-05-04-static-resort-data-acquisition-design.md`
- `docs/superpowers/specs/2026-05-06-catalog-acquisition-patch-pr-design.md`

Related docs:
- `README.md`
- `docs/data-trust-model.md`
- `docs/engineering-notes.md`
- `docs/product-backlog.md`

## Context

Snowcast's static catalog acquisition pipeline fetches official/open/provider pages, extracts candidate facts, generates review artifacts, and can create conservative patch PRs. In practice it is not reliable enough to replace human review for static resort and stay-base facts. It can miss the right official pages, produce low-value PRs, hit provider rate limits, and still require owner review before any source-backed value becomes canonical.

Most static catalog facts change slowly. Terrain totals, source URLs, stay-base topology, lift-pass examples, and source-backed characteristics benefit more from careful source interpretation and reviewable evidence than from broad scraping.

Future operational-status data is different. Open lifts, open piste kilometers, reported snow depth, and live operating status need timestamped observations and automated refresh. That work should not inherit the static catalog PR workflow.

## Decision

Use a skill-led static catalog curation workflow as the primary path for slow-changing catalog updates.

Codex uses a Snowcast catalog-curation skill to research official/open sources, update `app/data/resorts.json`, update `app/data/resort_trust_manifest.json`, generate a reviewable evidence report, run validation, and prepare a PR.

Typed Pydantic contracts and reusable policy validators replace broad static scraping as the safety mechanism. The validators check report shape, trust evidence coverage, source-link reviewability, cross-field consistency, and ranking-impact visibility.

Remove the manual GitHub Actions static catalog acquisition workflow from the primary maintenance path. Keep internal acquisition modules only while implementation classifies whether individual helpers are useful for future source diagnostics or freshness sentinels.

Bergfex is not a source of catalog truth. It may later be used as a warning-only freshness sentinel that points reviewers back to official sources.

## Consequences

Static catalog PRs should become easier to review because changed values, target entities, trust labels, and evidence links are prepared directly for owner review.

The system no longer spends effort maintaining a brittle scraper/LLM extraction path for data that still requires review.

The catalog remains stable because runtime code continues reading only approved catalog files.

The project adds a new curation-report contract and skill. These must stay lightweight so catalog updates do not become process-heavy.

Future operational-status automation remains a separate design with timestamped database observations, freshness, source-specific parsers, and alerting.

## Alternatives Considered

- Continue improving the static acquisition pipeline. This preserves existing work, but keeps the core mismatch: brittle scraping for slow-changing facts that still require review.
- Keep acquisition as the primary path and use the skill only for exceptions. This leaves the confusing low-value PR path in place.
- Fully manual catalog editing with no typed report. This is simpler, but loses repeatable validation and makes PRs less consistently reviewable.

## Revisit When

Revisit this decision if reliable official/provider APIs become available for most static catalog facts, if the catalog grows enough that skill-led curation becomes the bottleneck, or if future operational-status source onboarding proves that some deterministic source adapters should be reused for warning-only static freshness checks.
```

- [ ] **Step 2: Commit the ADR**

```bash
git add docs/architecture/adr/0004-static-catalog-curation-skill.md
git commit -m "docs: record static catalog curation decision"
```

Expected: one ADR-only commit.

## Task 3: Curation Contract Models And Markdown Renderer

**Files:**
- Create: `app/data/catalog_curation.py`
- Create: `tests/test_catalog_curation.py`

- [ ] **Step 1: Write failing model and renderer tests**

Create `tests/test_catalog_curation.py`:

```python
import json

import pytest
from pydantic import ValidationError

from app.data.catalog_curation import (
    CatalogChangeSummary,
    CatalogCurationReport,
    CatalogEvidenceItem,
    CatalogValidationError,
    render_catalog_curation_report_markdown,
    validate_catalog_curation_report,
)


def _valid_report() -> CatalogCurationReport:
    return CatalogCurationReport(
        title="Zell am See-Kaprun catalog curation",
        summary="Adds reviewed Kitzsteinhorn terrain facts.",
        changed_entities=["zell-am-see-kaprun", "ski_area:kitzsteinhorn"],
        changes=[
            CatalogChangeSummary(
                target_type="ski_area",
                target_id="kitzsteinhorn",
                field_path="total_piste_km",
                before=None,
                after=61,
                trust_status="verified",
                ranking_relevant=True,
            )
        ],
        evidence=[
            CatalogEvidenceItem(
                target_type="ski_area",
                target_id="kitzsteinhorn",
                field_path="total_piste_km",
                source_type="official",
                source_url="https://www.kitzsteinhorn.at/en/winter/kitzsteinhorn-ski-board",
                source_title="Kitzsteinhorn ski and board",
                source_value=61,
                evidence_summary="Official page lists 61 piste kilometres.",
            )
        ],
        validation_commands=[
            "UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog"
        ],
        ranking_comparison_summary="Ranking comparison showed no top-result changes.",
    )


def test_catalog_curation_report_accepts_source_backed_change() -> None:
    report = _valid_report()

    validate_catalog_curation_report(report)

    assert report.changes[0].target_key == (
        "ski_area",
        "kitzsteinhorn",
        "total_piste_km",
    )


def test_catalog_curation_report_rejects_invalid_source_url() -> None:
    with pytest.raises(ValidationError):
        CatalogEvidenceItem(
            target_type="ski_area",
            target_id="kitzsteinhorn",
            field_path="total_piste_km",
            source_type="official",
            source_url="notaurl",
            source_title="Broken source",
            source_value=61,
            evidence_summary="Official page lists 61 piste kilometres.",
        )


def test_catalog_curation_report_requires_evidence_for_verified_change() -> None:
    report = _valid_report().model_copy(update={"evidence": []})

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("missing evidence" in issue for issue in error.value.issues)


def test_catalog_curation_report_rejects_third_party_only_verified_change() -> None:
    report = _valid_report()
    report.evidence[0].source_type = "third_party"

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("third_party source cannot verify" in issue for issue in error.value.issues)


def test_catalog_curation_report_requires_normalization_note_for_adjusted_value() -> None:
    report = _valid_report()
    report.evidence[0].source_value = 61.4

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog_curation_report(report)

    assert any("normalization_note" in issue for issue in error.value.issues)


def test_render_catalog_curation_report_markdown_contains_clickable_evidence() -> None:
    markdown = render_catalog_curation_report_markdown(_valid_report())

    assert "# Zell am See-Kaprun catalog curation" in markdown
    assert "| `ski_area:kitzsteinhorn` | `total_piste_km` | `null` | `61` | `verified` |" in markdown
    assert "[Kitzsteinhorn ski and board](https://www.kitzsteinhorn.at/en/winter/kitzsteinhorn-ski-board)" in markdown
    assert "Ranking comparison showed no top-result changes." in markdown


def test_catalog_curation_report_round_trips_json() -> None:
    payload = _valid_report().model_dump(mode="json")

    report = CatalogCurationReport.model_validate(json.loads(json.dumps(payload)))

    assert report.evidence[0].source_url.startswith("https://www.kitzsteinhorn.at/")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_curation.py -q
```

Expected: import failure because `app.data.catalog_curation` does not exist.

- [ ] **Step 3: Implement `app/data/catalog_curation.py`**

Create `app/data/catalog_curation.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

CatalogTargetType = Literal["destination", "ski_area", "stay_base", "rental"]
CatalogSourceType = Literal["official", "open_data", "reviewed_editorial", "third_party"]
CatalogTrustStatus = Literal[
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
]
CatalogIssueSeverity = Literal["error", "warning"]
JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]

SOURCE_BACKED_TRUST_STATUSES = {"verified", "verified_with_adjustment"}
VERIFICATION_SOURCE_TYPES = {"official", "open_data", "reviewed_editorial"}


def _validate_json_value(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            _validate_json_value(nested_value)
        return value
    if isinstance(value, list):
        for nested_value in value:
            _validate_json_value(nested_value)
        return value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise ValueError("value must be JSON-serializable")


def _target_key(target_type: str, target_id: str, field_path: str) -> tuple[str, str, str]:
    return (target_type, target_id, field_path)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _json_cell(value: JsonValue) -> str:
    return f"`{json.dumps(value, ensure_ascii=False, sort_keys=True)}`"


class CatalogValidationError(ValueError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(issues))


class CatalogValidationIssue(BaseModel):
    severity: CatalogIssueSeverity
    message: str = Field(min_length=1)
    target_type: CatalogTargetType | None = None
    target_id: str | None = None
    field_path: str | None = None


class CatalogChangeSummary(BaseModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    before: JsonValue = None
    after: JsonValue = None
    trust_status: CatalogTrustStatus
    ranking_relevant: bool = False

    @field_validator("field_path")
    @classmethod
    def validate_field_path(cls, value: str) -> str:
        segments = value.split(".")
        if any(not segment.strip() for segment in segments):
            raise ValueError("field_path cannot contain blank segments")
        return value

    @field_validator("before", "after")
    @classmethod
    def validate_json_value(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)

    @property
    def target_key(self) -> tuple[str, str, str]:
        return _target_key(self.target_type, self.target_id, self.field_path)


class CatalogEvidenceItem(BaseModel):
    target_type: CatalogTargetType
    target_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    source_type: CatalogSourceType
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_value: JsonValue = None
    evidence_summary: str = Field(min_length=1)
    normalization_note: str | None = None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        if not _is_http_url(value):
            raise ValueError("source_url must be an http(s) URL")
        return value

    @field_validator("source_value")
    @classmethod
    def validate_source_value(cls, value: JsonValue) -> JsonValue:
        return _validate_json_value(value)

    @property
    def target_key(self) -> tuple[str, str, str]:
        return _target_key(self.target_type, self.target_id, self.field_path)


class CatalogCurationReport(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    changed_entities: list[str] = Field(default_factory=list)
    changes: list[CatalogChangeSummary] = Field(default_factory=list)
    evidence: list[CatalogEvidenceItem] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    ranking_comparison_summary: str | None = None
    unresolved_caveats: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_changes(self) -> "CatalogCurationReport":
        if not self.changes:
            raise ValueError("curation report must include at least one change")
        return self


def load_catalog_curation_report(path: Path) -> CatalogCurationReport:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CatalogValidationError([f"Unable to read curation report at {path}: {error}"]) from error
    except json.JSONDecodeError as error:
        raise CatalogValidationError([f"Invalid JSON in curation report at {path}: {error}"]) from error
    return CatalogCurationReport.model_validate(payload)


def validate_catalog_curation_report(report: CatalogCurationReport) -> None:
    issues: list[str] = []
    evidence_by_key: dict[tuple[str, str, str], list[CatalogEvidenceItem]] = {}
    for evidence in report.evidence:
        evidence_by_key.setdefault(evidence.target_key, []).append(evidence)

    for change in report.changes:
        matching_evidence = evidence_by_key.get(change.target_key, [])
        if change.trust_status in SOURCE_BACKED_TRUST_STATUSES and not matching_evidence:
            issues.append(
                f"{change.target_type}:{change.target_id} {change.field_path}: missing evidence for {change.trust_status}"
            )
            continue
        for evidence in matching_evidence:
            if (
                change.trust_status in SOURCE_BACKED_TRUST_STATUSES
                and evidence.source_type not in VERIFICATION_SOURCE_TYPES
            ):
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    f"{evidence.source_type} source cannot verify {change.trust_status}"
                )
            if evidence.source_value != change.after and not evidence.normalization_note:
                issues.append(
                    f"{change.target_type}:{change.target_id} {change.field_path}: "
                    "normalization_note is required when source_value differs from after"
                )
    if issues:
        raise CatalogValidationError(sorted(set(issues)))


def render_catalog_curation_report_markdown(report: CatalogCurationReport) -> str:
    lines = [
        f"# {report.title}",
        "",
        report.summary,
        "",
        "## Changed Fields",
        "",
        "| Target | Field | Before | After | Trust | Ranking Relevant |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for change in report.changes:
        target = f"{change.target_type}:{change.target_id}"
        lines.append(
            "| "
            f"`{target}` | "
            f"`{change.field_path}` | "
            f"{_json_cell(change.before)} | "
            f"{_json_cell(change.after)} | "
            f"`{change.trust_status}` | "
            f"{'yes' if change.ranking_relevant else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "| Target | Field | Source | Source Value | Evidence | Normalization |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for evidence in report.evidence:
        target = f"{evidence.target_type}:{evidence.target_id}"
        source = f"[{evidence.source_title}]({evidence.source_url})"
        lines.append(
            "| "
            f"`{target}` | "
            f"`{evidence.field_path}` | "
            f"{source} | "
            f"{_json_cell(evidence.source_value)} | "
            f"{evidence.evidence_summary} | "
            f"{evidence.normalization_note or ''} |"
        )

    if report.ranking_comparison_summary:
        lines.extend(["", "## Ranking Impact", "", report.ranking_comparison_summary])

    if report.validation_commands:
        lines.extend(["", "## Verification", ""])
        for command in report.validation_commands:
            lines.append(f"- `{command}`")

    if report.unresolved_caveats:
        lines.extend(["", "## Caveats", ""])
        for caveat in report.unresolved_caveats:
            lines.append(f"- {caveat}")

    lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_curation.py -q
```

Expected: all tests in `tests/test_catalog_curation.py` pass.

- [ ] **Step 5: Commit contract models**

```bash
git add app/data/catalog_curation.py tests/test_catalog_curation.py
git commit -m "feat: add catalog curation evidence contracts"
```

## Task 4: Curation Report Validation CLI

**Files:**
- Create: `app/data/validate_catalog_curation.py`
- Modify: `tests/test_catalog_curation.py`

- [ ] **Step 1: Add failing CLI tests**

Append to `tests/test_catalog_curation.py`:

```python
from app.data.validate_catalog_curation import main as validate_curation_main


def test_validate_catalog_curation_cli_accepts_valid_report(tmp_path, capsys) -> None:
    report_path = tmp_path / "curation-report.json"
    markdown_path = tmp_path / "curation-report.md"
    report_path.write_text(
        json.dumps(_valid_report().model_dump(mode="json")),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "--report-path",
            str(report_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    assert exit_code == 0
    assert "[catalog-curation-valid]" in capsys.readouterr().out
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Zell am See-Kaprun catalog curation"
    )


def test_validate_catalog_curation_cli_rejects_invalid_report(tmp_path, capsys) -> None:
    report = _valid_report().model_copy(update={"evidence": []})
    report_path = tmp_path / "curation-report.json"
    report_path.write_text(
        json.dumps(report.model_dump(mode="json")),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(["--report-path", str(report_path)])

    assert exit_code == 1
    assert "[catalog-curation-invalid]" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_curation.py::test_validate_catalog_curation_cli_accepts_valid_report tests/test_catalog_curation.py::test_validate_catalog_curation_cli_rejects_invalid_report -q
```

Expected: import failure because `app.data.validate_catalog_curation` does not exist.

- [ ] **Step 3: Implement CLI**

Create `app/data/validate_catalog_curation.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from pydantic import ValidationError

from app.data.catalog_curation import (
    CatalogValidationError,
    load_catalog_curation_report,
    render_catalog_curation_report_markdown,
    validate_catalog_curation_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Snowcast catalog curation report."
    )
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = load_catalog_curation_report(args.report_path)
        validate_catalog_curation_report(report)
    except (CatalogValidationError, ValidationError) as error:
        if isinstance(error, CatalogValidationError):
            issues = error.issues
        else:
            issues = (str(error),)
        for issue in issues:
            print(f"[catalog-curation-invalid] {issue}")
        return 1

    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(
            render_catalog_curation_report_markdown(report),
            encoding="utf-8",
        )

    print(
        "[catalog-curation-valid] "
        f"changes={len(report.changes)} "
        f"evidence={len(report.evidence)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_curation.py -q
```

Expected: all curation tests pass.

- [ ] **Step 5: Commit CLI**

```bash
git add app/data/validate_catalog_curation.py tests/test_catalog_curation.py
git commit -m "feat: validate catalog curation reports"
```

## Task 5: Cross-Field Catalog Policy Checks

**Files:**
- Create: `app/data/catalog_policy.py`
- Modify: `app/data/validate_resort_catalog.py`
- Modify: `tests/test_catalog_validation.py`

- [ ] **Step 1: Add failing policy tests**

Append to `tests/test_catalog_validation.py`:

```python
def test_validate_catalog_rejects_mismatched_piste_difficulty_totals(tmp_path) -> None:
    payload = _valid_resort_payload()
    payload[0]["ski_areas"][0]["total_piste_km"] = 100
    payload[0]["ski_areas"][0]["piste_km_by_difficulty"] = {
        "beginner": 10,
        "intermediate": 20,
        "advanced": 30,
    }
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("difficulty piste total" in issue for issue in error.value.issues)


def test_validate_catalog_rejects_walk_access_with_far_nearest_lift(tmp_path) -> None:
    payload = _valid_resort_payload()
    stay_base = payload[0]["stay_bases"][0]
    stay_base["access_mode"] = "walk"
    stay_base["nearest_lift_name"] = "Distant lift"
    stay_base["nearest_lift_distance_m"] = 2500
    resorts_path = tmp_path / "resorts.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            trust_manifest_path=manifest_path,
        )

    assert any("walk access conflicts" in issue for issue in error.value.issues)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py::test_validate_catalog_rejects_mismatched_piste_difficulty_totals tests/test_catalog_validation.py::test_validate_catalog_rejects_walk_access_with_far_nearest_lift -q
```

Expected: both tests fail because the new policy checks do not exist.

- [ ] **Step 3: Implement catalog policy checks**

Create `app/data/catalog_policy.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.models import Destination

CatalogPolicySeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class CatalogPolicyIssue:
    severity: CatalogPolicySeverity
    message: str


def catalog_policy_issues(resorts: list[Destination]) -> list[CatalogPolicyIssue]:
    issues: list[CatalogPolicyIssue] = []
    for resort in resorts:
        issues.extend(_ski_area_policy_issues(resort))
        issues.extend(_stay_base_policy_issues(resort))
    return issues


def _ski_area_policy_issues(resort: Destination) -> list[CatalogPolicyIssue]:
    issues: list[CatalogPolicyIssue] = []
    for ski_area in resort.ski_areas:
        difficulty = ski_area.piste_km_by_difficulty
        if ski_area.total_piste_km is not None and difficulty is not None:
            difficulty_total = (
                difficulty.beginner + difficulty.intermediate + difficulty.advanced
            )
            tolerance = max(1.0, ski_area.total_piste_km * 0.05)
            if abs(difficulty_total - ski_area.total_piste_km) > tolerance:
                issues.append(
                    CatalogPolicyIssue(
                        severity="error",
                        message=(
                            f"{ski_area.ski_area_id}: difficulty piste total "
                            f"{difficulty_total:g} does not match total_piste_km "
                            f"{ski_area.total_piste_km:g}"
                        ),
                    )
                )
    return issues


def _stay_base_policy_issues(resort: Destination) -> list[CatalogPolicyIssue]:
    issues: list[CatalogPolicyIssue] = []
    for stay_base in resort.stay_bases:
        distance = stay_base.nearest_lift_distance_m
        if stay_base.access_mode == "walk" and distance is not None and distance > 1500:
            issues.append(
                CatalogPolicyIssue(
                    severity="error",
                    message=(
                        f"{resort.resort_id}:{stay_base.stay_base_id}: walk access "
                        f"conflicts with nearest_lift_distance_m={distance}"
                    ),
                )
            )
    return issues
```

- [ ] **Step 4: Wire policy checks into catalog validation**

Modify `app/data/validate_resort_catalog.py`:

```python
from app.data.catalog_policy import catalog_policy_issues
```

In `validate_catalog`, after `_validate_loaded_catalog(resorts, issues)`, add:

```python
    for policy_issue in catalog_policy_issues(resorts):
        if policy_issue.severity == "error":
            issues.append(policy_issue.message)
```

- [ ] **Step 5: Run policy tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py::test_validate_catalog_rejects_mismatched_piste_difficulty_totals tests/test_catalog_validation.py::test_validate_catalog_rejects_walk_access_with_far_nearest_lift -q
```

Expected: both tests pass.

- [ ] **Step 6: Run full catalog validation tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py -q
```

Expected: all catalog validation tests pass.

- [ ] **Step 7: Commit catalog policy checks**

```bash
git add app/data/catalog_policy.py app/data/validate_resort_catalog.py tests/test_catalog_validation.py
git commit -m "feat: add catalog consistency policy checks"
```

## Task 6: Snowcast Catalog Curation Skill

**Files:**
- Create: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p /Users/awownysz/.codex/skills/snowcast-catalog-curation
```

- [ ] **Step 2: Create the skill file**

Create `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`:

````markdown
---
name: snowcast-catalog-curation
description: Use when source-backed static Snowcast resort, ski-area, stay-base, rental, pricing, terrain, season, or catalog-trust data needs to be researched, edited, validated, and prepared for PR review.
---

# Snowcast Catalog Curation

Use this skill only for:

```text
/Users/awownysz/repos/personal_projects/ai-sports-travel-planner
```

This skill replaces the static catalog acquisition workflow for slow-changing
catalog facts. It does not refresh live operational status.

## Required Context

Read these first:

- `docs/data-trust-model.md`
- `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`
- `app/data/resorts.json`
- `app/data/resort_trust_manifest.json`

Read these when ranking or fit inputs change:

- `docs/superpowers/specs/2026-06-20-resort-fit-data-model-design.md`
- `docs/superpowers/plans/2026-06-22-ranking-comparison-diagnostics.md`
- `app/domain/resort_fit.py`
- `app/data/compare_ranking.py`

## Source Rules

Prefer sources in this order:

1. Official ski-area, resort, ticket, season, status, trail-map, and rental pages.
2. Open structured sources for identity, topology, coordinates, and IDs:
   OpenDataHub, OSM, Wikidata.
3. Reviewed editorial or provider sources only as fallback/corroborating evidence.

Bergfex must not populate catalog truth. Use it only as a warning or
corroborating signal that points review back to official sources.

Do not use acquisition artifacts as runtime truth.

## Workflow

1. Identify the requested destination, ski area, stay base, or rental scope.
2. Inspect current catalog values and trust statuses before researching.
3. Gather official/open source links and keep them directly clickable.
4. Update `app/data/resorts.json` only with reviewed values.
5. Update `app/data/resort_trust_manifest.json` when trust status or source refs change.
6. Create a catalog curation report JSON for meaningful high-impact changes.
7. Render the report Markdown for the PR body or checked-in review artifact.
8. Run validation.
9. Run ranking comparison when changed fields affect ranking or fit behavior.
10. Prepare a PR summary with changed fields, evidence links, validation commands, and caveats.

## Required Evidence For Verified Fields

For any field moved to `verified` or `verified_with_adjustment`, include:

- target entity and field path;
- before and after values;
- trust status;
- source URL;
- source title;
- source type;
- evidence summary;
- normalization note when the catalog value differs from the source value.

## Verification

Always run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

When a curation report exists, run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  --report-path docs/catalog-curation/2026-06-23-zell-am-see-kaprun.json \
  --markdown-output docs/catalog-curation/2026-06-23-zell-am-see-kaprun.md
```

When ranking or fit inputs change, run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking \
  --output-dir artifacts/ranking-comparison
```

## PR Handoff

The PR summary should include:

- destinations and entities changed;
- changed-field table;
- clickable evidence links;
- trust-status changes;
- normalization notes;
- ranking comparison summary when relevant;
- exact validation commands run;
- unresolved caveats.
````

- [ ] **Step 3: Verify the skill file exists**

```bash
test -f /Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md
```

Expected: command exits `0`.

## Task 7: Deprecate Static Acquisition Workflow Entry Point

**Files:**
- Delete: `.github/workflows/catalog-acquisition.yml`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Remove the workflow file**

```bash
rm .github/workflows/catalog-acquisition.yml
```

- [ ] **Step 2: Remove the workflow-specific acquisition test**

Delete the entire `test_catalog_acquisition_workflow_can_create_draft_pr_only_when_requested`
function from `tests/test_resort_acquisition.py`. The function starts with:

```python
def test_catalog_acquisition_workflow_can_create_draft_pr_only_when_requested() -> None:
```

and ends before the next top-level `def` or the end of the file.

Keep the provider, parser, proposal, and helper tests in `tests/test_resort_acquisition.py` unchanged in this task.

- [ ] **Step 3: Run focused tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py tests/test_catalog_curation.py tests/test_catalog_validation.py -q
```

Expected: acquisition helper tests still pass; there is no workflow-file failure.

- [ ] **Step 4: Commit workflow deprecation**

```bash
git add .github/workflows/catalog-acquisition.yml tests/test_resort_acquisition.py
git commit -m "chore: retire catalog acquisition workflow"
```

Expected: deleted workflow and adjusted test are committed.

## Task 8: Documentation Update For Skill-Led Curation

**Files:**
- Modify: `README.md`
- Modify: `docs/data-trust-model.md`
- Modify: `docs/engineering-notes.md`

- [ ] **Step 1: Replace README acquisition section**

In `README.md`, replace the static acquisition instructions from "To generate local catalog acquisition proposals" through the acquisition troubleshooting/free-tier guidance with a concise "Static catalog curation" section:

````markdown
### Static catalog curation

Slow-changing resort, ski-area, stay-base, rental, terrain, price, and season
facts are maintained through source-backed catalog curation rather than the old
static acquisition workflow.

Use the `snowcast-catalog-curation` Codex skill for catalog updates. The skill
guides source research, catalog edits, trust-manifest updates, evidence capture,
validation, ranking comparison when needed, and PR review summaries.

Approved truth remains in:

- `app/data/resorts.json`
- `app/data/resort_trust_manifest.json`

Meaningful high-impact catalog changes should include a catalog curation report
with before/after values, target entities, trust statuses, clickable source
links, normalization notes, validation commands, and ranking-impact notes when
relevant.

Validate catalog changes with:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

Validate a curation report and render Markdown with:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  --report-path docs/catalog-curation/2026-06-23-zell-am-see-kaprun.json \
  --markdown-output docs/catalog-curation/2026-06-23-zell-am-see-kaprun.md
```

When ranking or resort-fit inputs change, also run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking \
  --output-dir artifacts/ranking-comparison
```

Bergfex is not a catalog source of truth. It may be used later as a
warning-only freshness sentinel, but it must not auto-populate catalog values.
````

- [ ] **Step 2: Update data trust model**

In `docs/data-trust-model.md`, add a short subsection after "Trust Statuses":

```markdown
## Catalog Curation Reports

Source-backed catalog changes should be accompanied by a typed curation report
when they affect high-impact fields such as ski areas, stay bases, price ranges,
season windows, terrain facts, lift-pass examples, or resort-fit inputs.

The report records target entity, field path, before/after value, trust status,
source type, source URL, evidence summary, and normalization notes. Validators
check report shape and reviewability, while the owner still reviews source
meaning and final catalog changes in the PR.
```

- [ ] **Step 3: Update engineering notes**

In `docs/engineering-notes.md`, replace the "Resort Catalog Acquisition" section with:

```markdown
## Resort Catalog Curation

Static and semi-static catalog facts now use skill-led source-backed curation as
the primary maintenance workflow. The old broad static acquisition workflow is
retired as the primary path because it was brittle, produced low-value PRs, and
still required owner review for slow-changing facts.

Approved catalog truth remains in `app/data/resorts.json` and
`app/data/resort_trust_manifest.json`. The curation workflow uses typed
Pydantic evidence/report contracts, named catalog policy validators, clickable
evidence links, and ranking comparison diagnostics when resort-fit inputs
change.

Bergfex is not a catalog source of truth. It may later serve as a warning-only
freshness sentinel that flags possible stale data and points review back to
official sources.

Frequent operational status remains separate future work. Open lifts, open
piste kilometers, reported snow depth, and live status need timestamped
database observations, source freshness, and source-specific parser review.
```

- [ ] **Step 4: Run docs grep checks**

```bash
rg -n "catalog acquisition|run_catalog_acquisition|generate_catalog_patch|Catalog Acquisition" README.md docs/engineering-notes.md docs/data-trust-model.md
```

Expected: remaining matches should be historical spec references or explicitly labeled as retired old workflow. There should be no active README instruction telling users to run static acquisition.

- [ ] **Step 5: Commit documentation updates**

```bash
git add README.md docs/data-trust-model.md docs/engineering-notes.md
git commit -m "docs: document skill-led catalog curation"
```

## Task 9: Final Verification And Feature Review

**Files:**
- Current diff

- [ ] **Step 1: Run focused tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_curation.py tests/test_catalog_validation.py tests/test_resort_acquisition.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run catalog validation**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

Expected: prints `[catalog-valid]`.

- [ ] **Step 3: Run lint and format checks**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/catalog_curation.py app/data/validate_catalog_curation.py app/data/catalog_policy.py tests/test_catalog_curation.py tests/test_catalog_validation.py tests/test_resort_acquisition.py
UV_CACHE_DIR=.uv-cache uv run --no-config ruff format --check app/data/catalog_curation.py app/data/validate_catalog_curation.py app/data/catalog_policy.py tests/test_catalog_curation.py tests/test_catalog_validation.py tests/test_resort_acquisition.py
```

Expected: both commands pass.

- [ ] **Step 4: Run advisory feature review**

Use the Snowcast review system in `feature-review` mode with these reviewers:

```text
data-trust-source-integrity
backend-api
ai-llm-reliability
release-change-management
```

Review target:

```text
current diff since origin/main
```

Expected: no blocker/high findings. Resolve any blocker/high findings before final handoff.

- [ ] **Step 5: Inspect final status**

```bash
git status --short --branch
git log --oneline origin/main..HEAD
```

Expected: working tree contains only intentional uncommitted review fixes, or is clean after final commits. Commit history includes the spec, plan, ADR, validation/report implementation, workflow deprecation, and docs updates.
