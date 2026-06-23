# Static Catalog Curation Skill Design

## Goal

Replace the current static catalog acquisition workflow with an agent-assisted
catalog curation workflow that is easier to review and more reliable for
slow-changing resort and stay-base facts.

The approved catalog remains git-canonical:

- `app/data/resorts.json`
- `app/data/resort_trust_manifest.json`

The new workflow uses a Snowcast Codex skill to guide source-backed research,
catalog edits, evidence capture, validation, and PR creation. Deterministic
validators enforce schema, trust, and reviewability constraints. The workflow
does not use scraper output or LLM extraction artifacts as runtime truth.

## Problem

The current static acquisition pipeline is not a good fit for most static resort
facts:

- It misses important facts when the right official pages are not discovered or
  selected for extraction.
- It can produce low-value PRs with only small ID/source changes.
- It still requires human review for each PR, so automation does not remove the
  critical review step.
- It creates maintenance burden around brittle scraping, provider rate limits,
  LLM extraction budgets, and patch-generation behavior.
- Most static catalog fields change rarely enough that fully automated scraping
  is not worth the reliability cost.

The product still needs strong reviewability, source trust, and repeatable
validation. The replacement should remove brittle scraping while keeping the
parts that make catalog changes safe to review.

## Scope

In scope:

- Create a Snowcast catalog-curation Codex skill.
- Deprecate and then remove the static catalog acquisition CLI/workflow as the
  normal path for catalog updates.
- Add typed curation and evidence contracts using Pydantic models.
- Keep CLI commands as thin wrappers around reusable schema and policy
  validation.
- Generate a reviewer-friendly Markdown report for catalog PRs.
- Use ranking comparison diagnostics when catalog changes affect ranking or fit
  behavior.

Out of scope:

- Automated daily/live operational status refresh.
- Automatically patching catalog data from Bergfex or other aggregators.
- Runtime reads from curation artifacts.
- Broad changes to production ranking semantics.
- A property-level lodging inventory.

## Decision And Review Gate

Classification: `review-gated`

High-risk domains:

- catalog data correctness
- source trust and evidence quality
- LLM/agent-assisted curation behavior
- CI and GitHub Actions maintenance
- future ranking inputs and resort-fit factors

Developer Decision Checkpoint status:

- Resolved: static slow-changing catalog data should move to an agent-assisted
  curation workflow rather than continuing as a brittle scraper pipeline.
- Resolved: validation should be typed contracts and domain policy checks, not
  ad hoc scripts.
- Resolved: Bergfex should not populate catalog truth; it may later become a
  warning-only freshness sentinel.

ADR status:

- Required during implementation because the change retires an existing
  acquisition architecture path and replaces it with a skill-led maintenance
  model.

Advisory design-review status:

- Required before implementation.
- Suggested reviewers: `data-trust-source-integrity`, `backend-api`,
  `ai-llm-reliability`.

Advisory feature-review status:

- Required before final handoff if the implementation removes or deprecates
  existing acquisition commands/workflows.

## Chosen Approach

Use a skill-led workflow plus deterministic validation.

The skill handles judgment-heavy research:

- finding official source pages;
- deciding whether a source applies to the destination, ski area, stay base, or
  rental;
- summarizing source evidence;
- updating catalog and trust data;
- preparing a reviewable PR.

Reusable validators handle mechanical correctness:

- typed schema validation;
- source-reference and trust-status contracts;
- cross-field consistency;
- evidence completeness;
- ranking/fit behavior impact checks.

This keeps source interpretation flexible while making catalog changes
structured, auditable, and reviewable.

## Data Categories

The replacement workflow is for static and semi-static catalog data.

Static or rare-audit data:

- destination, ski-area, and stay-base IDs;
- destination/ski-area/stay-base topology;
- official source URLs;
- regional data IDs such as OSM, Wikidata, and OpenDataHub;
- coordinates and elevations after review;
- nearest lift geometry for stay bases, unless infrastructure changes.

Semi-static data:

- total piste kilometers;
- lift count;
- piste difficulty split;
- typical or exact season windows;
- adult/default lift-pass price examples;
- rental examples and representative rental price ranges;
- stay-base lodging price bands;
- stay-base access facts and atmosphere tags;
- resort/stay-base characteristics such as quiet, family-friendly, nightlife,
  premium, scenic, pure-skiing, or convenience-oriented.

Frequent operational observations are explicitly separate:

- open lift count;
- open piste kilometers or count;
- reported snow depth;
- live resort status;
- last reported provider update.

Those future fields need timestamped database observations and freshness
handling, not PR-reviewed static catalog edits.

## Skill Workflow

The new Snowcast skill should guide Codex through this sequence:

1. Identify the target destination, ski area, stay base, or rental scope.
2. Inspect current catalog, trust manifest, source refs, and relevant model docs.
3. Research official sources first:
   - official ski-area/resort facts pages;
   - official ticket/price pages;
   - official season/opening pages;
   - official trail-map or status pages as source pointers;
   - official rental/partner pages when relevant.
4. Use open structured sources only for appropriate facts:
   - OSM for coordinates, topology, and distance-related facts;
   - Wikidata for entity identity and coarse metadata;
   - OpenDataHub where the destination is in provider coverage.
5. Use third-party providers only as fallback or corroborating evidence.
6. Update catalog data and trust/source refs.
7. Generate or update the catalog curation report.
8. Run validation and focused diagnostics.
9. Create a PR with a concise reviewer-oriented summary.

The skill should require source-backed evidence for any field promoted to
`verified` or `verified_with_adjustment`. It should keep uncertain,
conflicting, or weakly sourced facts out of canonical catalog fields unless they
are explicitly marked as estimates.

## Curation Contract Models

Add typed contracts for catalog curation artifacts. These models should live in
normal application/data modules and be reusable from tests and CLIs.

Suggested model groups:

- `CatalogCurationReport`
- `CatalogChangeSummary`
- `CatalogEvidenceItem`
- `CatalogSourceReference`
- `CatalogValidationIssue`
- `CatalogValidationReport`

Evidence item shape:

```json
{
  "target_type": "ski_area",
  "target_id": "kitzsteinhorn",
  "field_path": "total_piste_km",
  "before": null,
  "after": 61,
  "trust_status": "verified",
  "source_type": "official",
  "source_url": "https://example.com/ski-area",
  "source_title": "Official ski area page",
  "evidence_summary": "Official page lists 61 piste kilometers.",
  "normalization_note": null
}
```

The model should enforce:

- allowed target types;
- nonblank target IDs and field paths;
- allowed source types;
- valid source URLs;
- nonblank evidence summaries for source-backed changes;
- explicit normalization notes when source value and catalog value differ;
- valid trust statuses;
- JSON-serializable before/after values.

## Deterministic Validators

Validators should be reusable policy functions with thin CLI wrappers.

### Schema And Invariant Validation

Continue validating catalog shape and expand typed coverage where useful:

- explicit `ski_areas` and `stay_bases`;
- stable nonblank IDs;
- unique destination, ski-area, and stay-base IDs;
- plausible coordinates and elevations;
- valid season months and season windows;
- valid lift-pass price objects;
- valid stay-base price ranges;
- allowed access modes, base types, quality tiers, lift-distance buckets, and
  skill levels.

### Trust Manifest Validation

Trust validation should enforce:

- every critical field group has trust coverage;
- `verified` and `verified_with_adjustment` statuses have external source refs;
- `app/data/resorts.json` is not the only source for source-backed status;
- new high-impact fields do not silently bypass trust classification;
- source refs identify the target field group clearly enough for review.

### Evidence Completeness Validation

For catalog PRs, validate the curation report:

- every changed high-impact field has a matching evidence item;
- each evidence item points at the correct target entity;
- source URLs are clickable and syntactically valid;
- `verified` changes use official/open/reviewed editorial sources;
- third-party-only evidence cannot promote a field to `verified`;
- normalization notes exist for adjusted values;
- changed ranking inputs are flagged for ranking comparison.

This check validates reviewability, not the truth of the webpage content.

### Cross-Field Consistency Validation

Add named policy checks for common catalog mistakes:

- piste difficulty kilometers should approximately sum to total piste
  kilometers;
- exact season windows should align with month fallback fields;
- destination-level terrain aggregates are invalid unless explicitly modeled as
  aggregate facts;
- a stay base marked walkable should not have a large nearest-lift distance
  without an explanation;
- a car-recommended stay base with a very small nearest-lift distance should be
  flagged;
- destination-level elevations should stay plausible relative to ski-area
  elevations;
- multi-area destinations should keep ski-area facts under the correct
  `ski_areas[]` entry.

### Behavior Impact Validation

When changed fields affect ranking or fit factors, run ranking comparison
diagnostics and include the result in the PR/report.

Examples:

- piste kilometers;
- difficulty split;
- lift count;
- season windows;
- stay-base price range;
- stay-base access fields;
- supported skill levels;
- derived factor policy inputs.

Behavior impact checks should not block every change. They should make ranking
or grouping changes visible to the reviewer.

## Reviewer-Friendly Report

Each meaningful catalog curation PR should include a Markdown report. The report
may be generated into the PR body, checked in under a review-docs directory, or
both. The implementation should choose one durable convention and keep it
consistent.

Required sections:

- summary of destinations, ski areas, stay bases, and rentals touched;
- changed-fields table with before/after values;
- evidence table with clickable source links;
- trust-status changes;
- normalization notes;
- cross-field validation summary;
- ranking comparison summary when relevant;
- exact verification commands run;
- unresolved caveats or follow-up items.

Example changed-field row:

```markdown
| Target | Field | Before | After | Trust | Evidence |
| --- | --- | --- | --- | --- | --- |
| ski_area:kitzsteinhorn | total_piste_km | null | 61 | verified | [Official ski page](https://example.com/ski-area) |
```

The report should be concise enough to review in GitHub, but complete enough
that the owner does not need to reverse-engineer why a catalog value changed.

## Bergfex Boundary

Bergfex should move out of static catalog population.

Allowed future role:

- warning-only freshness sentinel;
- secondary discrepancy detection;
- stale-source alerting;
- corroborating evidence that points a reviewer back to official sources.

Disallowed role:

- automatic catalog patching;
- source of truth for `verified` status;
- official-page LLM extraction input;
- routine full-catalog scraping.

Example future sentinel behavior:

- Snowcast catalog says a ski area has 61 piste kilometers.
- Bergfex or another secondary source appears to show a materially different
  value.
- The sentinel creates a warning artifact: "possible stale terrain fact; review
  official ski-area source."
- No catalog value changes automatically.

## Deprecation Plan

Implementation should retire the old static acquisition path in stages:

1. Introduce the curation skill and typed curation report validation.
2. Update README and engineering notes to make skill-led curation the primary
   static catalog path.
3. Disable or remove PR-creation mode from the existing acquisition workflow.
4. Remove the static acquisition GitHub Actions workflow if no longer useful.
5. Remove or archive acquisition modules that exist only for static scraping and
   patch generation.
6. Keep reusable validators, audit commands, ranking comparison diagnostics, and
   domain models.

The exact module deletion list should be decided during implementation after
checking imports and tests.

## Testing And Verification

Test coverage should focus on contracts and policy:

- Pydantic model validation for curation reports and evidence items;
- trust-manifest validation cases;
- cross-field consistency checks;
- report rendering for clickable evidence links;
- CLI exit codes for hard failures versus warning-only issues;
- skill workflow smoke documentation, if the skill includes examples;
- focused catalog validation after any catalog fixture changes.

Implementation verification should include:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

For changes that affect ranking inputs:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison
```

For new validation modules:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py tests/test_resort_acquisition.py -q
```

The exact test list may change during implementation if acquisition tests are
removed or split.

## Documentation Impact

Update:

- `README.md`: replace static acquisition instructions with skill-led catalog
  curation workflow.
- `docs/engineering-notes.md`: record the architecture decision and Bergfex
  boundary.
- `docs/product-backlog.md`: keep operational status acquisition as future
  work.
- `docs/data-trust-model.md`: describe the curation report and typed evidence
  contract.
- `docs/architecture/adr/`: add an ADR retiring static acquisition as the
  primary catalog maintenance path.

## Risks

- Agent-assisted curation can still make source-interpretation mistakes. The
  mitigation is typed evidence, clickable links, and owner review.
- Removing acquisition too quickly could drop useful helper code. The
  implementation should classify modules before deletion.
- Report requirements can become heavy. The first version should cover changed
  high-impact fields and avoid forcing long reports for tiny metadata fixes.
- Future operational-status automation must not inherit the static curation
  workflow. It needs timestamped observations, freshness, and source-specific
  parsers.

## Success Criteria

- Static catalog updates no longer depend on the broad acquisition scraper or
  Bergfex fallback.
- A catalog PR is easier to review than the current acquisition-generated PRs.
- Every important changed value has a clear target, before/after value, trust
  status, and clickable evidence link.
- Validation failures come from typed contracts and named policy checks.
- Runtime application behavior continues to read only approved catalog data.
- Operational status remains separated as future automated observation work.
