# Feature Spec: Catalog Curation Backlog Deferrals

## Status

- Status: accepted
- Owner: solo-builder
- Related docs: `docs/product-backlog.md`,
  `docs/superpowers/specs/2026-07-07-catalog-entity-scope-assessment-design.md`
- Related ADRs: ADR 0008 and ADR 0009

## User Outcome

Catalog curation should add missing destinations, bases, ski areas, access
edges, domains, and pass products in the active PR whenever that work is
reasonably sourceable and belongs to the same coherent scope. Backlog deferral
is an explicit exception for work that would make the PR unmanageably broad,
mix unrelated model changes, depend on uncurated entities, or remain genuinely
unresolved.

No missing material entity may disappear between a curation report and future
work: every accepted `deferred` or `unresolved` entity-scope assessment must
link to a real consolidated entry under `Catalog Curation Refinements` in
`docs/product-backlog.md`.

## Scope

In scope:

- add a typed backlog reference to entity-scope assessments;
- require backlog references for `deferred` and `unresolved` dispositions;
- validate that referenced Markdown entries exist in the dedicated catalog
  curation section;
- render backlog references in curation reports;
- make in-PR completion the first choice in the curation skill;
- make unjustified deferral and missing backlog coverage explicit review
  findings;
- keep the review skill read-only while producing ready-to-apply backlog text;
- consolidate related candidates into one regional refinement entry.

Out of scope:

- automatically creating catalog entities from candidate discovery;
- automatically editing the backlog from the review skill;
- changing destination or ski-area boundary definitions;
- creating a generic issue tracker or replacing `docs/product-backlog.md`;
- requiring backlog entries for `represented`, `add_entity`, `not_separate`, or
  ordinary `external_pass_context` assessments;
- adding every named piste sector, lift, webcam, or pass perk to the backlog.

## Decision and Review Gate

- Classification: review-gated; this changes a shared curation-report contract
  and catalog-completeness workflow.
- Developer Decision Checkpoints:
  - resolved: curation writes qualifying backlog updates directly;
  - resolved: review remains read-only and proposes paste-ready updates;
  - resolved: related candidates use one consolidated regional entry;
  - resolved: in-PR completion is preferred over deferral;
  - resolved: typed `backlog_ref` is required for accepted `deferred` and
    `unresolved` candidates;
  - unresolved: none.
- ADR status: no new ADR; this strengthens workflow traceability without moving
  domain ownership or changing the catalog architecture.
- Advisory design review: completed with Data Trust & Source Integrity and
  Backend / API; candidate-level backlog membership, duplicate-anchor handling,
  and historical version gating were clarified before implementation.
- Advisory feature review: the same two lanes before final handoff.

## Deferral Decision Policy

The curator must first attempt to implement a material candidate in the active
PR. Use `add_entity` when the candidate is source-backed, naturally belongs to
the current destination or related batch, and can be added without introducing
a separate owner decision or unrelated model change.

Deferral is acceptable only when at least one concrete condition applies:

- adding the candidate would exceed the normal batch limit or turn a focused
  destination PR into a broad regional recuration;
- it requires a separate schema, product-model, or source-semantics refinement;
- it requires a stable-ID or weather-history migration and owner checkpoint;
- it depends on other destinations, bases, areas, access edges, or domains that
  are not yet curated;
- the available sources remain insufficient or genuinely contradictory after
  reasonable research;
- it mixes a materially different concern such as pass-selection policy or
  comparable terrain-metric redesign into a static destination curation.

Convenience, time pressure, or the existence of a backlog section are not valid
deferral reasons. The assessment rationale must name the applicable condition.
The review skill should flag a manageable, source-backed candidate that was
deferred instead of added.

`not_separate` is a completed boundary decision and needs no backlog item.
`external_pass_context` needs a backlog item only if the curator determines
that a concrete destination, base, ski area, or relationship should eventually
be modeled; in that case use `deferred` for that candidate instead of hiding it
inside generic pass context.

## Report Contract

Add the optional field below to `CatalogEntityScopeAssessment`:

```text
backlog_ref: str | None
```

The canonical value is a repository-relative Markdown reference:

```text
docs/product-backlog.md#kitzski-catalog-extension
```

Contract rules for schema-version-2 reports:

- `deferred` and `unresolved` require one non-blank `backlog_ref`;
- all other dispositions forbid `backlog_ref`;
- the path must be exactly `docs/product-backlog.md`;
- the fragment must be a normalized Markdown heading anchor;
- several related assessments may and should share one reference;
- the report renderer adds a `Backlog` column to the entity-scope table.

The nested model owns normalization and reference format. Report-level
validation owns the version-2 disposition requirements so historical
version-1 loading remains unchanged. File-aware validation remains outside the
Pydantic model so report objects stay deterministic and independent of the
process working directory.

## Backlog Reference Validation

Both `typed` and `reconcile` accept:

```text
--product-backlog-path docs/product-backlog.md
```

When a report contains a backlog reference:

- omitting the path is a validation error;
- an unreadable file is a validation error;
- the referenced anchor must resolve to an `###` item inside the
  `## Catalog Curation Refinements` section;
- headings elsewhere in the backlog do not satisfy the reference;
- duplicate normalized anchors inside that section are a validation error;
- the referenced item body must contain the exact candidate marker
  `` `<candidate_kind>:<candidate_id>` `` for each assessment using that
  reference;
- duplicate references across assessments are valid and represent
  consolidation.

Reports without deferred/unresolved candidates do not require the CLI option.
Historical version-1 loading remains unchanged. The curation and review skills
always pass the option for current full-curation reports so later deferrals do
not silently weaken validation.

## Backlog Entry Shape

The curation skill upserts one `### <Regional Scope> Catalog Extension` item for
related candidates. It updates an existing matching item instead of creating a
duplicate.

Each entry contains:

- `Status: parked` and `Area: Data Trust`;
- `Source:` with the originating curation or review PR;
- why the missing graph coverage matters;
- a candidate checklist grouped by entity kind, with one exact machine-checkable
  marker such as `` `ski_area:kitzbuheler-horn` `` for every referenced
  assessment;
- direct source links or concise evidence summaries;
- why each candidate was not added in the active PR;
- dependencies or owner checkpoints;
- explicit `Not now` boundaries;
- a concrete promotion trigger.

An unresolved candidate must be worded as a boundary question, not as a
confirmed future entity. A deferred candidate may state the likely entity only
to the strength supported by its evidence.

## Skill Behavior

### Curation skill

Before accepting a deferral, the curator must answer:

1. Can this be sourced and added correctly in the current PR?
2. Is it needed to make a fact, relationship, or owner scope in the PR true?
3. Would adding it remain inside the normal batch and review scope?

If the first two answers are yes and the third is also yes, use `add_entity`.
Otherwise, record the concrete deferral reason, upsert the regional backlog
item, add its `backlog_ref`, and validate the reference.

The curation completion gate rejects:

- avoidable deferrals;
- deferred/unresolved assessments without a backlog link;
- links to entries outside `Catalog Curation Refinements`;
- one backlog item per small sector when a regional entry already exists;
- backlog items based only on names, webcams, map filters, or generic pass
  marketing.

### Review skill

The reviewer independently decides whether the candidate could reasonably be
implemented in the PR. It does not accept `deferred` merely because the report
uses that disposition.

- Treat a manageable omitted entity required for current catalog correctness as
  a substantive finding and request in-PR implementation.
- Treat an accepted deferral with no valid backlog reference as a contract
  finding.
- Verify consolidation and evidence quality.
- If the backlog update is missing, output a complete ready-to-paste item under
  `Suggested Catalog Curation Backlog Update`.
- Do not edit the PR branch, backlog, or GitHub review unless the user asks for
  fixes or publication.

## Error Handling

- A missing or invalid `backlog_ref` fails report validation with the candidate
  ID and disposition.
- A missing heading identifies the unresolved reference and backlog path.
- A missing candidate marker identifies the candidate and resolved heading.
- Duplicate normalized headings are rejected rather than resolved by position.
- Existing reports with no deferrals remain valid.
- Backlog parsing is limited to Markdown headings; it does not interpret prose
  or attempt semantic deduplication.
- The curator/reviewer owns consolidation judgment when two differently named
  headings appear to describe the same regional extension.

## Acceptance Criteria

- `deferred` and `unresolved` cannot validate without `backlog_ref`.
- Other dispositions cannot carry a backlog reference.
- The CLI rejects nonexistent references and headings outside the catalog
  curation section.
- The CLI rejects a valid heading whose item body omits the referenced
  candidate marker, and rejects duplicate normalized anchors.
- Multiple assessments can share one valid regional reference.
- Rendering shows the backlog reference.
- Curation guidance requires in-PR implementation whenever reasonably possible
  and records concrete reasons for exceptions.
- Review guidance challenges avoidable deferrals and remains read-only.
- Existing regional backlog entries are updated rather than duplicated.
- `not_separate` and generic external pass context do not create backlog noise.
- A KitzSki-style scenario adds a sourceable Horn entity in the active PR,
  retains Pengelstein/Resterhoehe as `not_separate`, and consolidates genuinely
  wider Kirchberg/Jochberg/Pinzgau expansion work under one backlog reference.

## Verification

- Unit tests for disposition/reference combinations and Markdown rendering.
- CLI tests for missing files, missing anchors, wrong-section headings, and a
  shared valid regional entry.
- Historical report compatibility tests.
- Curation-skill scenarios for manageable in-PR addition, justified regional
  deferral, consolidation, and deduplication.
- Review-skill scenarios for unjustified deferral and paste-ready read-only
  output.
- Focused catalog tests plus the full backend suite and repository lint checks.

## Residual Risk

The typed reference proves that deferred work has a durable destination, not
that the backlog item is perfectly scoped or that the deferral was justified.
Independent review remains responsible for challenging scope avoidance and
weak boundary evidence.
