# Catalog Entity Scope Assessment Implementation Plan

> **For Codex:** REQUIRED SKILL: Use `superpowers:executing-plans` to implement
> this plan task by task. Use `superpowers:test-driven-development` for contract
> and validator changes, and `superpowers:verification-before-completion` before
> the final handoff.

**Goal:** Make full catalog curation and review explicitly prove that the
catalog graph contains the right entities and relationships, while preventing
named connected sectors such as Pengelstein and Resterhöhe from being split
into artificial ski areas.

**Architecture:** Extend the existing curation-report contract with a
backward-compatible schema version and typed, source-aware entity-scope
assessments. Keep historical reports on implicit version 1, require version 2
through the CLI for current full-curation workflows, and make the validator own
cross-reference, evidence, graph-coverage, and anti-over-splitting invariants.
The curation and review skills remain complementary: curation records the
inventory, while review reconstructs it independently before comparing it with
the catalog graph.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Ruff, Markdown-based
Codex skills.

## Decision and Review Gate

- Classification: full design flow / review-gated.
- Developer Decision Checkpoint: resolved by the owner; use typed assessments,
  update both skills symmetrically, and treat discovery signals as insufficient
  creation evidence.
- ADR: no new ADR; ADR 0008 and ADR 0009 already own place and terrain
  boundaries.
- Advisory design review: completed with Data Trust & Source Integrity and
  Backend / API. Its version-gating and graph-coverage findings are incorporated
  below.
- Advisory feature review: run the same two lanes after implementation.

## Task 1: Lock the report contract with failing tests

**Files:**
- Modify: `tests/test_catalog_curation.py`

**Step 1: Add compatibility and required-inventory tests**

Add tests proving that:

- omitted `report_schema_version` parses as version 1 and validates unchanged;
- a version-2 report without `entity_scope_assessments` fails;
- every full reviewed graph target is referenced by an assessment;
- duplicate candidate IDs, unknown evidence IDs, and invalid target references
  fail;
- evidence used only by a scope assessment is accepted.

**Step 2: Add disposition and anti-over-splitting tests**

Cover:

- `represented`, `add_entity`, and `not_separate` require direct,
  verification-capable evidence;
- a new ski area backed only by an official map sector, webcam, limited-area
  ticket, or secondary listing fails;
- a connected named sector may be `not_separate` and reference its existing ski
  area;
- `add_entity` target references match the candidate kind;
- Markdown renders an `Entity Scope Assessments` section.

**Step 3: Run the focused tests and confirm RED**

Run:

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest tests/test_catalog_curation.py -q
```

Expected: failures because the new contract types and fields do not yet exist.

## Task 2: Implement the typed scope contract and validation

**Files:**
- Modify: `app/data/catalog_curation.py`
- Modify: `tests/test_catalog_curation.py`

**Step 1: Add the typed models**

Add:

- `CatalogReportSchemaVersion = Literal[1, 2]`;
- candidate-kind, disposition, and controlled-signal literals;
- `CatalogEntityScopeTargetRef`;
- `CatalogEntityScopeAssessment`;
- `report_schema_version` defaulting to `1` and
  `entity_scope_assessments` defaulting to an empty list on
  `CatalogCurationReport`.

Keep model-level normalization consistent with the existing contract: trim
identifiers and rationale, reject duplicate list values, and expose stable
target keys.

**Step 2: Add report-level invariants**

Extend `validate_catalog_curation_report` to enforce:

- version 2 has a non-empty scope inventory;
- assessment candidate IDs are unique;
- all evidence and target references exist;
- target references match the candidate kind, and `add_entity` has a matching
  identity-field creation change;
- every full reviewed graph target is referenced;
- source-backed dispositions use verification-capable evidence;
- ski-area creation has at least one durable independent-owner signal;
- destination creation has a passing destination-boundary assessment;
- terrain-domain creation uses ski-connected terrain;
- scope-only evidence is exempt from the changed-field matching check.

The validator must not infer an entity from a discovery signal. In particular,
`official_map_sector`, `webcam`, `limited_area_ticket`, and
`secondary_provider_listing` can trigger research but cannot alone justify a
new ski area.

**Step 3: Render the inventory**

Add a Markdown table with candidate, kind, disposition, signals, catalog
targets, evidence, and rationale.

**Step 4: Run the focused tests and reach GREEN**

Run the Task 1 command. Refactor only after all new tests pass.

## Task 3: Require the current schema through the CLI

**Files:**
- Modify: `tests/test_catalog_curation_reconciliation.py`
- Modify: `app/data/validate_catalog_curation.py`

**Step 1: Add failing CLI tests**

Test both `typed` and `reconcile` for:

- rejecting an implicit/version-1 report when invoked with
  `--require-report-schema-version 2`;
- accepting a valid version-2 report with the same flag;
- preserving current behavior when the flag is omitted;
- printing `report_schema_version` in the success summary.

**Step 2: Confirm RED**

Run:

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest tests/test_catalog_curation_reconciliation.py -q
```

**Step 3: Implement the shared CLI option**

Add the option to both subcommands, compare it after loading the report, and
return a normal catalog-validation issue when the report is older. Keep loading
and validating historical reports unchanged when no minimum is requested.

**Step 4: Run the reconciliation tests and reach GREEN**

Run the Task 3 command.

## Task 4: Record the durable catalog-boundary guidance

**Files:**
- Modify: `docs/engineering-notes.md`

Add a concise catalog-curation note that explains:

- inventory-first graph assessment;
- discovery versus creation evidence;
- owner-scope signals required for independent ski areas;
- why connected official sectors remain one `SkiArea` without durable
  independent identity;
- why `TerrainDomain` cannot be manufactured by first over-splitting sectors;
- how separate accommodation markets can still be distinct stay destinations
  while sharing one ski area.

Do not describe this as scoring behavior or modify domain definitions.

## Task 5: Update the catalog curation skill

**Files:**
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`

Add a mandatory full-curation phase that:

1. discovers candidates from official maps, status/weather pages, ticket
   products, access points, and accommodation markets before editing;
2. records every material candidate and catalog graph target in typed
   `entity_scope_assessments`;
3. distinguishes discovery/supporting signals from independent-owner boundary
   signals;
4. tests destinations, stay bases, ski areas, access edges, domains, and pass
   coverage for completeness;
5. uses `not_separate` for named connected sectors lacking independent owner
   scope;
6. forbids artificial child ski areas created only to form a terrain domain;
7. runs both typed validation and reconciliation with
   `--require-report-schema-version 2`.

Include three compact examples: KitzSki connected sectors, a stronger
independent Horn-style candidate, and a simple one-town/one-area resort.

## Task 6: Update the catalog review skill symmetrically

**Files:**
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md`

Require the reviewer to independently reconstruct the source-first candidate
inventory rather than trusting the PR report. The review must compare that
inventory with both typed assessments and the actual catalog graph, flag
missing graph entities or relationships, and also flag unsupported
over-splitting. Apply the same source hierarchy, anti-over-splitting rule,
examples, and schema-version CLI gate as the curation skill.

## Task 7: Verify the complete change and run advisory feature review

**Files:**
- Verify all modified files.

**Step 1: Run focused and adjacent tests**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py tests/test_catalog_models.py tests/test_catalog_trust.py -q
```

**Step 2: Run repository checks**

```bash
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync ruff check app/data/catalog_curation.py app/data/validate_catalog_curation.py tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py
UV_PROJECT_ENVIRONMENT="/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv" uv run --no-config --no-sync pytest -q
```

**Step 3: Validate skills and scenarios**

- inspect both skills for the exact schema-version command;
- confirm both cover the same entity kinds and source hierarchy;
- replay the KitzSki scenario: Pengelstein/Resterhöhe are discovered but stay
  within KitzSki; a Horn-style independently evidenced candidate is separately
  assessed; Kirchberg may be a distinct accommodation market while sharing the
  ski area;
- confirm neither skill mentions scoring.

**Step 4: Run advisory feature review**

Apply the Data Trust & Source Integrity and Backend / API reviewer contracts to
the final diff. Resolve all blocker/high findings and record any accepted lower
risk in the handoff.

**Step 5: Commit the branch**

Review `git diff --check`, `git status`, and the final diff before committing.
Do not push or open a PR without a separate explicit request.
