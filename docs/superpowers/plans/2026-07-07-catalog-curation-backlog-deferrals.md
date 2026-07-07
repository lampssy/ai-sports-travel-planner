# Catalog Curation Backlog Deferrals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require every schema-v2 deferred or unresolved catalog entity candidate to point to a real consolidated catalog-curation backlog item, while making in-PR implementation the preferred workflow.

**Architecture:** Keep disposition/reference shape validation in the existing Pydantic curation contract. Put filesystem-aware Markdown heading and candidate-marker validation in a new focused `catalog_curation_backlog.py` module, invoked by both CLI modes. Update curation and review skills symmetrically, while preserving the review skill's read-only boundary.

**Tech Stack:** Python 3.12, Pydantic v2, argparse, pytest, Ruff, Markdown-based Codex skills.

---

## Decision and Review Gate

- Classification: review-gated; shared curation report and data-trust workflow.
- Developer Decision Checkpoints: resolved in the accepted spec.
- ADR: no new ADR; catalog ownership and boundary rules remain in ADR 0008 and
  ADR 0009.
- Advisory design review: completed with Data Trust & Source Integrity and
  Backend / API.
- Advisory feature review: run the same two lanes before final handoff.
- Existing version-1 reports must remain loadable and valid.

### Task 1: Add the versioned `backlog_ref` report contract

**Files:**
- Modify: `tests/test_catalog_curation.py:65-450`
- Modify: `app/data/catalog_curation.py:665-1105`

- [ ] **Step 1: Add failing disposition/reference tests**

Extend `_scope_report_payload` with `backlog_ref: str | None = None` and include
the field in the assessment only when supplied. Add these tests:

```python
@pytest.mark.parametrize("disposition", ["deferred", "unresolved"])
def test_schema_two_deferred_scope_requires_backlog_ref(
    disposition: str,
) -> None:
    payload = _scope_report_payload(disposition=disposition)
    payload["entity_scope_assessments"][0]["target_refs"] = []
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=f"{disposition} requires backlog_ref",
    ):
        validate_catalog_curation_report(report)


def test_schema_one_deferred_scope_remains_backward_compatible() -> None:
    payload = _scope_report_payload(disposition="deferred")
    payload["report_schema_version"] = 1
    payload["entity_scope_assessments"][0]["target_refs"] = []
    report = CatalogCurationReport.model_validate(payload)

    validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    "disposition",
    ["represented", "add_entity", "not_separate", "external_pass_context"],
)
def test_non_deferred_scope_forbids_backlog_ref(disposition: str) -> None:
    payload = _scope_report_payload(
        disposition=disposition,
        backlog_ref="docs/product-backlog.md#kitzski-catalog-extension",
    )
    if disposition == "external_pass_context":
        payload["entity_scope_assessments"][0]["target_refs"] = []
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(CatalogValidationError, match="forbids backlog_ref"):
        validate_catalog_curation_report(report)


def test_backlog_ref_rejects_noncanonical_path_or_anchor() -> None:
    payload = _scope_report_payload(
        disposition="deferred",
        backlog_ref="PROJECT.md#KitzSki Extension",
    )
    payload["entity_scope_assessments"][0]["target_refs"] = []

    with pytest.raises(ValidationError, match="canonical product backlog reference"):
        CatalogCurationReport.model_validate(payload)
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest tests/test_catalog_curation.py -q
```

Expected: failures because `CatalogEntityScopeAssessment` has no
`backlog_ref` and report validation does not enforce disposition linkage.

- [ ] **Step 3: Add the field and canonical-format validation**

In `app/data/catalog_curation.py`, add:

```python
import re

CATALOG_BACKLOG_REF_PREFIX = "docs/product-backlog.md#"
CATALOG_BACKLOG_REF_PATTERN = re.compile(
    rf"^{re.escape(CATALOG_BACKLOG_REF_PREFIX)}"
    r"[a-z0-9]+(?:-[a-z0-9]+)*$"
)
BACKLOG_REQUIRED_SCOPE_DISPOSITIONS = frozenset({"deferred", "unresolved"})
```

Add the field and validator to `CatalogEntityScopeAssessment`:

```python
backlog_ref: str | None = None

@field_validator("backlog_ref")
@classmethod
def validate_backlog_ref(cls, value: str | None) -> str | None:
    value = _validate_optional_non_blank_string(value, "backlog_ref")
    if value is not None and CATALOG_BACKLOG_REF_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "backlog_ref must be a canonical product backlog reference"
        )
    return value
```

In `_validate_entity_scope_assessments`, after duplicate-candidate validation,
add schema-v2-only rules:

```python
if report.report_schema_version == 2:
    for assessment in assessments:
        requires_backlog = (
            assessment.disposition in BACKLOG_REQUIRED_SCOPE_DISPOSITIONS
        )
        if requires_backlog and assessment.backlog_ref is None:
            issues.append(
                f"{assessment.candidate_id}: {assessment.disposition} "
                "requires backlog_ref"
            )
        if not requires_backlog and assessment.backlog_ref is not None:
            issues.append(
                f"{assessment.candidate_id}: {assessment.disposition} "
                "forbids backlog_ref"
            )
```

- [ ] **Step 4: Add renderer coverage**

Update `test_scope_assessment_markdown_is_rendered` to use a valid deferred
assessment and assert:

```python
assert "| Backlog |" in rendered
assert "`docs/product-backlog.md#kitzski-catalog-extension`" in rendered
```

Extend the entity-scope table with a `Backlog` column and render
`assessment.backlog_ref` as a code cell, or an empty string when absent.

- [ ] **Step 5: Run focused tests and reach GREEN**

Run the Step 2 command. Expected: all tests pass.

- [ ] **Step 6: Commit the contract change**

```bash
git add app/data/catalog_curation.py tests/test_catalog_curation.py
git commit -m "feat: link catalog deferrals to backlog items"
```

### Task 2: Add filesystem-aware catalog backlog validation

**Files:**
- Create: `app/data/catalog_curation_backlog.py`
- Create: `tests/test_catalog_curation_backlog.py`

- [ ] **Step 1: Write failing parser and validation tests**

Create `tests/test_catalog_curation_backlog.py` with these complete helpers:

```python
from pathlib import Path

import pytest

from app.data.catalog_curation import (
    CatalogCurationReport,
    CatalogValidationError,
)
from app.data.catalog_curation_backlog import (
    validate_catalog_curation_backlog_refs,
)

BACKLOG_REF = "docs/product-backlog.md#kitzski-catalog-extension"


def _deferred_report_with_candidates(
    *candidates: tuple[str, str],
) -> CatalogCurationReport:
    return CatalogCurationReport.model_validate(
        {
            "report_schema_version": 2,
            "title": "Deferred catalog candidates",
            "summary": "Tracks justified regional catalog extensions.",
            "reviewed_targets": [],
            "entity_scope_assessments": [
                {
                    "candidate_id": candidate_id,
                    "candidate_name": candidate_id.replace("-", " ").title(),
                    "candidate_kind": candidate_kind,
                    "disposition": "deferred",
                    "signals": ["official_independent_identity"],
                    "evidence_refs": [f"scope-{candidate_id}"],
                    "target_refs": [],
                    "rationale": "A wider regional recuration is required.",
                    "backlog_ref": BACKLOG_REF,
                }
                for candidate_kind, candidate_id in candidates
            ],
        }
    )


def _deferred_report() -> CatalogCurationReport:
    return _deferred_report_with_candidates(("ski_area", "horn"))


def _write_backlog(tmp_path: Path, item_markdown: str) -> Path:
    path = tmp_path / "product-backlog.md"
    path.write_text(
        "# Product Backlog\n\n"
        "## Catalog Curation Refinements\n\n"
        f"{item_markdown}",
        encoding="utf-8",
    )
    return path
```

Then cover:

```python
def test_backlog_validation_requires_path_for_references() -> None:
    report = _deferred_report()

    with pytest.raises(CatalogValidationError, match="product backlog path"):
        validate_catalog_curation_backlog_refs(report, None)


def test_backlog_validation_rejects_heading_outside_curation_section(
    tmp_path: Path,
) -> None:
    path = tmp_path / "product-backlog.md"
    path.write_text(
        "# Backlog\n\n## Current Backlog\n\n### KitzSki Catalog Extension\n"
        "- `ski_area:horn`\n",
        encoding="utf-8",
    )

    with pytest.raises(CatalogValidationError, match="unknown backlog reference"):
        validate_catalog_curation_backlog_refs(_deferred_report(), path)


def test_backlog_validation_rejects_missing_candidate_marker(tmp_path: Path) -> None:
    path = _write_backlog(
        tmp_path,
        "### KitzSki Catalog Extension\n\n- `ski_area:another-area`\n",
    )

    with pytest.raises(CatalogValidationError, match="missing candidate marker"):
        validate_catalog_curation_backlog_refs(_deferred_report(), path)


def test_backlog_validation_rejects_duplicate_normalized_anchor(
    tmp_path: Path,
) -> None:
    path = _write_backlog(
        tmp_path,
        "### KitzSki Catalog Extension\n\n- `ski_area:horn`\n\n"
        "### KitzSki: Catalog Extension\n\n- `ski_area:horn`\n",
    )

    with pytest.raises(CatalogValidationError, match="duplicate backlog anchor"):
        validate_catalog_curation_backlog_refs(_deferred_report(), path)


def test_backlog_validation_accepts_shared_regional_item(tmp_path: Path) -> None:
    report = _deferred_report_with_candidates(
        ("ski_area", "horn"),
        ("stay_destination", "kirchberg"),
    )
    path = _write_backlog(
        tmp_path,
        "### KitzSki Catalog Extension\n\n"
        "- `ski_area:horn`\n"
        "- `stay_destination:kirchberg`\n",
    )

    validate_catalog_curation_backlog_refs(report, path)
```

Also test an unreadable/missing path, a nonexistent anchor, a report with no
references and no path, and Unicode heading normalization such as
`Kitzbühel Catalog Extension` -> `kitzbuhel-catalog-extension`.

- [ ] **Step 2: Run the new test file and confirm RED**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest tests/test_catalog_curation_backlog.py -q
```

Expected: collection fails because `app.data.catalog_curation_backlog` does not
exist.

- [ ] **Step 3: Implement the focused validator module**

Create `app/data/catalog_curation_backlog.py`:

```python
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from app.data.catalog_curation import (
    CATALOG_BACKLOG_REF_PREFIX,
    CatalogCurationReport,
    CatalogValidationError,
)

CATALOG_CURATION_SECTION = "Catalog Curation Refinements"


def markdown_heading_anchor(heading: str) -> str:
    decomposed = unicodedata.normalize("NFKD", heading)
    without_marks = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "-", without_marks.lower()).strip("-")


def _catalog_curation_items(markdown: str) -> tuple[dict[str, str], set[str]]:
    items: dict[str, list[str]] = {}
    duplicate_anchors: set[str] = set()
    in_section = False
    current_anchor: str | None = None

    for line in markdown.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            in_section = line.removeprefix("## ").strip() == CATALOG_CURATION_SECTION
            current_anchor = None
            continue
        if not in_section:
            continue
        if line.startswith("### "):
            current_anchor = markdown_heading_anchor(
                line.removeprefix("### ").strip()
            )
            if current_anchor in items:
                duplicate_anchors.add(current_anchor)
            else:
                items[current_anchor] = []
            continue
        if current_anchor is not None:
            items[current_anchor].append(line)

    return (
        {anchor: "\n".join(lines) for anchor, lines in items.items()},
        duplicate_anchors,
    )


def validate_catalog_curation_backlog_refs(
    report: CatalogCurationReport,
    backlog_path: Path | None,
) -> None:
    assessments = [
        assessment
        for assessment in report.entity_scope_assessments
        if assessment.backlog_ref is not None
    ]
    if not assessments:
        return
    if backlog_path is None:
        raise CatalogValidationError(
            ["product backlog path is required when backlog_ref is present"]
        )
    try:
        markdown = backlog_path.read_text(encoding="utf-8")
    except OSError as error:
        raise CatalogValidationError(
            [f"Unable to read product backlog at {backlog_path}: {error}"]
        ) from error

    items, duplicate_anchors = _catalog_curation_items(markdown)
    issues = [
        f"duplicate backlog anchor in Catalog Curation Refinements: {anchor}"
        for anchor in sorted(duplicate_anchors)
    ]
    for assessment in assessments:
        backlog_ref = assessment.backlog_ref
        if backlog_ref is None:
            continue
        anchor = backlog_ref.removeprefix(CATALOG_BACKLOG_REF_PREFIX)
        item_body = items.get(anchor)
        if item_body is None:
            issues.append(
                f"{assessment.candidate_id}: unknown backlog reference "
                f"{backlog_ref}"
            )
            continue
        candidate_marker = (
            f"`{assessment.candidate_kind}:{assessment.candidate_id}`"
        )
        if candidate_marker not in item_body:
            issues.append(
                f"{assessment.candidate_id}: backlog item {anchor} is missing "
                f"candidate marker {candidate_marker}"
            )
    if issues:
        raise CatalogValidationError(sorted(set(issues)))
```

- [ ] **Step 4: Run tests and reach GREEN**

Run the Step 2 command. Expected: all backlog-validator tests pass.

- [ ] **Step 5: Run contract and backlog tests together**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest tests/test_catalog_curation.py tests/test_catalog_curation_backlog.py -q
```

- [ ] **Step 6: Commit the validator**

```bash
git add app/data/catalog_curation_backlog.py tests/test_catalog_curation_backlog.py
git commit -m "feat: validate catalog backlog references"
```

### Task 3: Integrate backlog validation into both CLI modes

**Files:**
- Modify: `app/data/validate_catalog_curation.py:1-130`
- Modify: `tests/test_catalog_curation_reconciliation.py:160-450`

- [ ] **Step 1: Add failing CLI tests**

Add these helpers:

```python
def _schema_two_deferred_report() -> CatalogCurationReport:
    payload = _schema_two_relationship_report().model_dump(mode="json")
    assessment = payload["entity_scope_assessments"][0]
    assessment["disposition"] = "deferred"
    assessment["target_refs"] = []
    assessment["backlog_ref"] = (
        "docs/product-backlog.md#example-region-catalog-extension"
    )
    return CatalogCurationReport.model_validate(payload)


def _write_valid_backlog(tmp_path: Path) -> Path:
    backlog_path = tmp_path / "product-backlog.md"
    backlog_path.write_text(
        "# Product Backlog\n\n"
        "## Catalog Curation Refinements\n\n"
        "### Example Region Catalog Extension\n\n"
        "- `ski_area_access:example-access`\n",
        encoding="utf-8",
    )
    return backlog_path
```

Then add tests proving:

```python
def test_typed_cli_requires_backlog_path_for_deferred_report(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(
        _schema_two_deferred_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(["typed", str(report_path)])

    assert exit_code == 1
    assert "product backlog path is required" in capsys.readouterr().out


def test_typed_cli_accepts_valid_deferred_backlog_reference(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "report.json"
    backlog_path = _write_valid_backlog(tmp_path)
    report_path.write_text(
        _schema_two_deferred_report().model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = validate_curation_main(
        [
            "typed",
            str(report_path),
            "--product-backlog-path",
            str(backlog_path),
        ]
    )

    assert exit_code == 0
    assert "backlog_refs=1" in capsys.readouterr().out
```

Add the equivalent successful `reconcile` case using `_relationship_snapshots`
so both subcommands exercise the same validator.

- [ ] **Step 2: Run CLI tests and confirm RED**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest tests/test_catalog_curation_reconciliation.py -q
```

Expected: failures because the option and validation call do not exist.

- [ ] **Step 3: Add the shared CLI option and validator call**

In `app/data/validate_catalog_curation.py`, import
`validate_catalog_curation_backlog_refs` and add:

```python
def _add_product_backlog_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--product-backlog-path",
        type=Path,
        help=(
            "Validate deferred entity-scope references against the catalog "
            "curation backlog."
        ),
    )
```

Call it for both `typed_parser` and `reconcile_parser`. In `main`, immediately
after `validate_catalog_curation_report(report)`, add:

```python
validate_catalog_curation_backlog_refs(report, args.product_backlog_path)
```

Extend the success summary:

```python
backlog_ref_count = sum(
    assessment.backlog_ref is not None
    for assessment in report.entity_scope_assessments
)
summary += f" backlog_refs={backlog_ref_count}"
```

- [ ] **Step 4: Run CLI and adjacent tests**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest tests/test_catalog_curation_reconciliation.py tests/test_catalog_curation_backlog.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit CLI integration**

```bash
git add app/data/validate_catalog_curation.py tests/test_catalog_curation_reconciliation.py
git commit -m "feat: enforce backlog references in curation CLI"
```

### Task 4: Document the backlog convention and update both skills

**Files:**
- Modify: `docs/product-backlog.md:58-105`
- Modify: `docs/engineering-notes.md:711-790`
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md`

Use the `superpowers:writing-skills` sub-skill for Steps 2-4 because this task
changes executable skill instructions and scenario coverage.

- [ ] **Step 1: Add the repository-owned backlog convention**

Under `## Catalog Curation Refinements`, document:

```markdown
Full curation should add sourceable, in-scope missing entities in the active PR.
Use this section only when the extension would make the PR unmanageably broad,
mix a separate model concern, depend on uncurated graph nodes, require a weather
identity migration, or remain genuinely unresolved.

Schema-version-2 deferred and unresolved scope assessments reference one
consolidated regional item through `backlog_ref`. Each item must include the
exact markers used by its reports, for example:

- `ski_area:kitzbuheler-horn`
- `stay_destination:kirchberg`

Update an existing regional item rather than creating one item per sector.
`not_separate` decisions do not belong here.
```

Add a concise matching convention under `Entity-scope assessment during
curation` in `docs/engineering-notes.md`.

- [ ] **Step 2: Update the curation skill**

Add a `Deferral And Backlog Gate` subsection after `Entity Scope Inventory`
that requires the three-question in-PR completion check from the spec. Require:

- concrete rationale for every accepted deferral;
- consolidated regional upsert under `Catalog Curation Refinements`;
- exact candidate markers;
- canonical `backlog_ref` on the report assessment;
- no backlog entry for `not_separate`;
- no generic pass-perk or map-sector noise.

Add this argument to both validation commands:

```text
--product-backlog-path docs/product-backlog.md
```

Add pre-PR blockers for avoidable deferral, missing candidate marker, missing
backlog reference, and duplicate regional entries.

- [ ] **Step 3: Update the read-only review skill**

Add the same decision gate, but keep the existing no-write boundary. Require
the reviewer to:

- independently decide whether the candidate belongs in the current PR;
- flag manageable omissions rather than accepting `deferred` automatically;
- verify the reference, heading, marker, evidence, and consolidation;
- emit the following exact section when a valid deferral lacks coverage:

```markdown
## Suggested Catalog Curation Backlog Update

### <Regional Scope> Catalog Extension

Status: parked
Area: Data Trust
Source: <curation/review PR>

Why it matters:
- ...

Candidate inventory:
- `<candidate_kind>:<candidate_id>` — <evidence-bounded description>

Why deferred:
- ...

Not now:
- ...

Promotion trigger:
- ...
```

Add `--product-backlog-path docs/product-backlog.md` to the reconciliation
command.

- [ ] **Step 4: Verify skill symmetry and scenarios**

Run:

```bash
rg -n "Deferral And Backlog Gate|backlog_ref|product-backlog-path|Suggested Catalog Curation Backlog Update|not_separate" \
  /Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md \
  /Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md
```

Manually replay these scenarios:

1. A sourceable Horn area inside a Kitzbühel PR is added now, not deferred.
2. Wider Kirchberg/Jochberg/Pinzgau work shares one KitzSki extension entry.
3. Pengelstein/Resterhoehe `not_separate` decisions create no backlog noise.
4. Review outputs a paste-ready item but does not edit the backlog.

- [ ] **Step 5: Commit repository documentation**

External skill files are user-level configuration and are not staged in the
repository. Commit only repository docs:

```bash
git add docs/product-backlog.md docs/engineering-notes.md
git commit -m "docs: define catalog curation deferral policy"
```

### Task 5: Complete verification and advisory feature review

**Files:**
- Verify all modified files.
- Update: `docs/superpowers/specs/2026-07-07-catalog-curation-backlog-deferrals-design.md`
  only if the feature review requires a clarification.

- [ ] **Step 1: Run focused catalog tests**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_backlog.py \
  tests/test_catalog_curation_reconciliation.py \
  tests/test_catalog_models.py \
  tests/test_catalog_trust.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run repository lint and formatting checks**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync ruff check .
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync ruff format --check .
git diff --check
```

Expected: all checks pass.

- [ ] **Step 3: Run the full backend suite**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest -q
```

Expected: all tests pass.

- [ ] **Step 4: Run advisory feature review**

Apply the Data Trust & Source Integrity and Backend / API reviewer contracts to
the final diff. Resolve all Blocker and High findings. Specifically verify:

- historical reports remain compatible;
- candidate markers prevent false backlog coverage;
- duplicate anchors fail deterministically;
- the CLI does not depend on an implicit working directory;
- review remains read-only;
- skill guidance does not make deferral easier than implementation.

- [ ] **Step 5: Review final state and commit any review fixes**

```bash
git status --short --branch
git diff --check
git log --oneline --decorate -8
```

If advisory review required repository changes, stage only those files and
commit:

```bash
git add \
  app/data/catalog_curation.py \
  app/data/catalog_curation_backlog.py \
  app/data/validate_catalog_curation.py \
  docs/engineering-notes.md \
  docs/product-backlog.md \
  docs/superpowers/specs/2026-07-07-catalog-curation-backlog-deferrals-design.md \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_backlog.py \
  tests/test_catalog_curation_reconciliation.py
git commit -m "fix: address catalog backlog review findings"
```

Do not push, merge, or remove the worktree without an explicit owner request.
