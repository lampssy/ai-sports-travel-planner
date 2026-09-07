# Research: Reliable Full Destination Graph Discovery

Date: 2026-09-07

Branch: `codex/maintainer-full-graph-flow` (based on `origin/main` at `12b70af`)

Classification: full design flow / review-gated

## Objective

Understand why recent Snowcast maintainer cycles can validate a narrow catalog
graph without investigating plausible missing stay destinations, stay bases, ski
areas, access edges, terrain domains, and lift-pass products. Identify a corrected
flow that restores full graph discovery while removing machinery that becomes
redundant.

This is a repository-grounded investigation. External web research is not needed
to identify the architectural defect: the problem is what the report can express,
what the helper can validate, and when semantic research occurs.

## Executive Finding

The maintainer currently has a **known-graph closure check**, not a full graph
discovery proof.

The deterministic validator can establish that every entity already connected to
a focused destination in `app/data/catalog.json` is reviewed. It also checks that
the evidence envelope mentions all six candidate-kind labels. It cannot establish
that the maintainer looked for unmodeled candidates or that an authoritative source
contained no additional candidates.

The semantic instructions do ask two reviewers to discover missing candidates, but
that obligation is buried inside a large review/remediation lifecycle and has no
first-class, durable output. The later `inventory-completion` phase is a reactive
repair after an incomplete review. It does not make initial discovery happen, and
its own documentation says it creates no cross-run semantic authority.

The result is visible in the active Livigno report: it has one assessment for each
already-modeled graph entity and can satisfy the current structural gate by putting
`terrain_domain` in a source family's `candidate_kinds`, despite having no concrete
terrain-domain candidate, no explicit `none found` result, and no assessments for
Mottolino, Carosello 3000, SITAS, Trepalle, or other plausible graph candidates.

## Current Architecture

### Responsibility split

```text
Codex and skills                         Deterministic helper
------------------------------------    --------------------------------------
research source meaning                 lease and exact-head ownership
discover candidate entities             prepare/rebase/conflict boundaries
apply Snowcast boundary policy          checkpoint and recovery refs
classify findings and fix catalog        schema/reconciliation/test execution
decide whether semantic review is clean push journal and GitHub publication

CatalogCurationReport
  |- reviewed_targets                    <- modeled review scope
  |- evidence                            <- claim-level sources
  |- review_evidence_envelope            <- source URLs + candidate-kind labels
  |- entity_scope_assessments            <- concrete candidate dispositions
  `- resulting_graph.focus_*             <- discovery roots
```

This responsibility split is sound. A deterministic validator cannot prove what a
web page means or whether an internet search found every real-world candidate. It
can, however, require a complete and internally consistent record for an independent
reviewer to verify.

### Current curation lifecycle

The installed maintainer skill currently describes this flow in
`/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md:56-132`:

```text
inspect/recover
      |
prepare exact PR head
      |
normalize report around existing graph
      |
build provisional evidence envelope
      |
parallel source-trust + graph-scope review
      |
      +-- incomplete --> report-only inventory-completion (up to two passes)
      |                    |
      |                    `-> special checkpoint marker / blocked publication
      |
      `-- complete ----> finding ledger -> remediation loops
                                           |
                                           `-> reviewed checkpoint
                                               -> validation -> push -> CI
```

The full-discovery instruction exists at
`/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md:66-79`, and the catalog
review skill asks graph-scope review to reconstruct the complete inventory at
`/Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md:80-87`. However,
neither is represented as a distinct prerequisite with a durable completeness
record before ordinary review starts.

## What the Current Validator Proves

`ops/maintainer/validation.py:536-598` implements
`_require_primary_destination_graph_inventory()`:

```python
graph_scope = catalog_resulting_graph_scope(
    catalog,
    frozenset(report.resulting_graph.focus_stay_destination_ids),
)

required_targets = {
    (target_type, target_id)
    for target_type, scope_attribute in _PRIMARY_DESTINATION_GRAPH_TARGETS
    for target_id in getattr(graph_scope, scope_attribute)
}

discovered_candidate_kinds = {
    candidate_kind
    for family in report.review_evidence_envelope
    for candidate_kind in family.candidate_kinds
}
```

It correctly requires:

1. a reviewed graph target for every entity in the catalog-derived closure;
2. an entity-scope assessment referencing every entity in that closure; and
3. all six candidate-kind strings somewhere in the evidence envelope.

The guard runs for ordinary delta/final validation through
`ops/maintainer/validation.py:768-806` and for discovery proposals through
`ops/maintainer/validation.py:652-728`.

This was intentionally documented as structural only in
`docs/operating-model/maintainer-runtime-command-contract.md:509-525`.

## What It Cannot Prove

### The graph closure starts from catalog rows

`catalog_resulting_graph_scope()` in
`app/data/catalog_curation.py:2887-2967` walks only normalized entities already in
the catalog:

```text
focused destinations
  -> their stay bases
  -> their access edges
  -> referenced ski areas
  -> available/default passes
  -> referenced terrain domains and their ski areas
```

This is the correct implementation for rendering and validating the **resulting
catalog graph**. It cannot discover an unmodeled village, lift system, pass, or
domain because such an entity has no row or edge to traverse.

### Source families declare kinds, not results

`CatalogReviewSourceFamily` at `app/data/catalog_curation.py:668-694` stores only:

```python
class CatalogReviewSourceFamily(CatalogCurationContractModel):
    family_id: str
    source_kind: CatalogReviewSourceKind
    source_urls: list[str]
    candidate_kinds: list[CatalogScopeCandidateKind]
```

It does not record:

- which discovery root was searched;
- whether the source is an authoritative enumerator or only supporting evidence;
- the concrete candidates found for each kind;
- an explicit `none_found` result;
- an `evidence_unavailable` result and rationale; or
- a cross-link proving every found candidate has a typed disposition.

The generic report validator checks URL/evidence references and assessment shape at
`app/data/catalog_curation.py:1338-1473`. It cannot distinguish "this page was
searched and contains no terrain domain" from "terrain_domain was added to an
array to satisfy validation."

### Concrete assessments are capable but not exhaustive

`CatalogEntityScopeAssessment` at `app/data/catalog_curation.py:1088-1145` already
has the right place to record concrete candidates: ID, kind, disposition, signals,
evidence, catalog targets, backlog link, graph impact, and rationale. The missing
piece is a discovery-coverage record that says which candidates an authoritative
source neighborhood exposed and requires each one to have an assessment.

## Concrete Regression Evidence

### Livigno: structurally complete, semantically narrow

The active report on `origin/pr-36-review` contains only five scope assessments:

| Candidate kind | Count |
| --- | ---: |
| stay destination | 1 |
| stay base | 1 |
| ski area | 1 |
| ski-area access | 1 |
| lift-pass product | 1 |
| terrain domain | 0 |

The assessments begin at
`origin/pr-36-review:docs/catalog-curation/2026-07-05-livigno-v2-enrichment.json:1116`.
The evidence envelope begins at line 1226; at line 1237 a single operator family
declares `ski_area`, `ski_area_access`, and `terrain_domain`. That declaration is
enough for the candidate-kind check even though no terrain-domain assessment exists.

### Tignes and Val d'Isere: the desired full-area picture

The historical report on `origin/pr-42-review` recorded 65 concrete assessments:

| Candidate kind | Count |
| --- | ---: |
| stay destination | 2 |
| stay base | 28 |
| ski area | 13 |
| ski-area access | 15 |
| terrain domain | 1 |
| lift-pass product | 6 |

Its assessments begin at
`origin/pr-42-review:docs/catalog-curation/2026-07-05-tignes-val-disere-v2-enrichment.json:7941`.
For example, named booking/map subareas such as `tignes-val-claret-centre` and
`tignes-le-lac-les-almes` are explicitly assessed as `not_separate` around lines
8106 and 8194. Other candidates are represented, deferred, unresolved, or treated
as external pass context. This makes both inclusion and rejection reviewable.

The difference is not explained by destination size alone. The older flow created
a concrete candidate inventory; the current flow can stop after categorizing the
known catalog graph.

## Root Causes

### 1. Discovery begins too late

The report is normalized around the existing catalog before the source inventory is
complete. Reviewers then receive that report and its provisional envelope. Although
they are told to discover independently, the bounded input naturally anchors review
to what the report already names.

### 2. Category coverage is mistaken for candidate coverage

Requiring all six labels answers "which entity types did the report mention?" It
does not answer "which concrete candidates did the official source neighborhood
expose, and how was each candidate classified?"

### 3. There is no negative discovery record

A complete investigation often legitimately finds no terrain domain or no additional
stay destination. The current schema has no typed way to distinguish that conclusion
from skipped work. This encourages either unverifiable prose or placeholder category
labels.

### 4. Inventory completion is reactive and non-durable

The report-only completion mechanism is described at
`docs/operating-model/maintainer-runtime-command-contract.md:527-550`. It begins only
after a reviewer notices missing inventory. It persists a special checkpoint marker
but explicitly does not persist its checklist, source conclusions, or cross-run
semantic authority.

The implementation spans:

- CLI flag: `ops/maintainer/cli.py:171-197`;
- private disposition models: `ops/maintainer/curation_state.py:92-170`;
- marker/event projection: `ops/maintainer/curation_state.py:306-329,582-650`;
- report-only checkpoint checks: `ops/maintainer/capabilities.py:880-1045`;
- terminal publication gates: `ops/maintainer/capabilities.py:3153-3193`;
- report-only git scope check: `ops/maintainer/git_ops.py:874-910`; and
- phrase-level contract tests: `tests/test_maintainer_inventory_completion_contract.py:1-256`.

It protects a terminal incomplete-review publication, but it does not establish the
initial candidate universe. This is why more guardrails did not fix Livigno.

### 5. Mutation scope and discovery scope are easy to conflate

Diff causality was added to stop unrelated linked-destination debt from blocking a
bounded PR. That rule is valid for **who may be changed**. It must not restrict
**what must be investigated** inside a focused destination. Current prose states
this distinction, but a first-class discovery packet would make it structural.

## Complexity Assessment

Current control-plane size:

- `ops/maintainer/*.py`: 15,695 lines;
- `tests/test_maintainer*.py`: 27,234 lines;
- installed maintainer skill: 230 lines;
- runtime contract plus activation guide: roughly 1,750 lines.

The six commits that introduced and tightened inventory completion plus the known
graph guard added 2,039 lines and removed 164 (net +1,875). The current inventory
completion/disposition terms appear 134 times across 13 implementation, test,
contract, and skill files.

Not all of this is accidental complexity. Exact-head preparation, leases, durable
generation checkpoints, validation receipts, push journals, terminal publication,
and post-push CI continuations protect real mutation and recovery boundaries. They
should remain.

The complexity to simplify is the **semantic inventory detour**: a two-pass private
checklist, a special boolean checkpoint marker, private publication input, and
terminal gates that duplicate information which should live in the canonical report.

The baseline focused test suite is currently green:

```text
115 passed in 10.34s
```

Command:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q \
  tests/test_maintainer_validation.py \
  tests/test_maintainer_curation_state.py \
  tests/test_maintainer_inventory_completion_contract.py
```

## Required Properties of a Corrected Flow

1. **Discovery is a named phase before ordinary semantic review.** It starts from
   every `resulting_graph.focus_stay_destination_ids` root, not from changed fields.
2. **Authoritative source neighborhoods are explicit.** At minimum they cover
   destination/accommodation listings, terrain/operator/map listings, access and
   transport, and pass/tariff coverage.
3. **Every candidate kind receives a result per root.** The result is concrete
   candidates, `none_found`, or `evidence_unavailable`; a kind label alone is not a
   result.
4. **Every concrete candidate is assessed.** Existing
   `entity_scope_assessments` remain the single place for represented, add, fold,
   external, deferred, or unresolved dispositions. Do not duplicate boundary logic.
5. **Known graph closure remains required.** The current catalog-derived check is a
   useful subset and should stay.
6. **Discovery evidence is durable and reviewable.** A later cycle should not need
   to reconstruct a successfully checkpointed candidate universe from automation
   memory.
7. **Deterministic validation stays structural.** It validates roots, source-family
   references, candidate cross-links, allowed outcomes, and completeness. An
   independent reviewer verifies source meaning and real-world exhaustiveness.
8. **Mutation ownership stays separate.** Discovery may identify linked or regional
   candidates without authorizing changes outside the selected PR.
9. **Proposal and curation paths use the same gate.** New destination proposals must
   not bypass discovery completeness.
10. **Incomplete work resumes instead of becoming a terminal review state.** A time
    limit or interruption should preserve a typed partial discovery checkpoint;
    only genuine evidence unavailability or a real owner decision should block.

## Candidate Target Shape

The smallest useful schema addition is a coverage layer that reuses the existing
source families and entity assessments:

```python
class CatalogGraphDiscoveryCoverage(...):
    focus_stay_destination_id: str
    candidate_kind: CatalogScopeCandidateKind
    outcome: Literal["enumerated", "none_found", "evidence_unavailable"]
    candidate_ids: list[str]
    source_family_ids: list[str]
    rationale: str
```

Structural rules can then require:

- exactly one coverage record for every focus root and candidate kind;
- `enumerated` has at least one candidate ID;
- `none_found` and `evidence_unavailable` have no candidate IDs and explain why;
- every source family exists and uses an appropriate official source neighborhood;
- every enumerated candidate resolves to one same-kind
  `entity_scope_assessment`;
- every known graph entity is enumerated and assessed; and
- every graph-blocking assessment belongs to at least one focus-root coverage record.

The source pages still cannot prove themselves. The graph-scope reviewer checks that
the declared enumerator pages are appropriate and that the candidates actually match
them.

## Design Options

### Option A: Schema-v5 durable discovery packet (recommended)

Add typed discovery coverage to the canonical report and require it for newly
finalized work. Historical schemas remain readable. Replace the special
inventory-completion lifecycle with a first-class graph-discovery checkpoint.

Advantages:

- directly fixes the missing information;
- makes positive and negative discovery reviewable in the PR report;
- supports exact-head resumption;
- allows deterministic cross-link validation without pretending to validate web
  truth; and
- provides a clean reason to delete the private checklist/publication machinery.

Costs:

- current active curation PR reports need normalization to schema v5;
- model, renderer, validator, maintainer state/action, docs, and skills change; and
- the version change requires a durable ADR.

### Option B: Helper-private discovery artifact

Keep schema v4 and persist a typed discovery packet only in helper state.

Advantages: fewer report migrations.

Costs: the report no longer tells reviewers why the graph is complete; helper state
becomes semantic authority; PR review cannot inspect the packet; and this repeats the
main weakness of the current run-local checklist.

### Option C: Guidelines and stronger heuristics only

Keep schema v4 and require reviewers to produce more detailed prose or infer
completeness from assessment counts/source-family labels.

Advantages: smallest code change.

Costs: no explicit negative result, no reliable candidate-to-source closure, and no
durable proof. This is likely to recreate the Livigno failure under different words.

## Recommended Conceptual Flow

```text
inspect/recover
      |
prepare exact PR head and base
      |
normalize report structure only
      |
GRAPH DISCOVERY (mandatory, rooted, source-neighborhood based)
      |
      +-- partial/interrupted --> durable partial discovery checkpoint
      |                           -> next cycle resumes discovery
      |
      `-- structurally complete --> discovery checkpoint
                                     |
                                     v
                         independent source-trust + graph-scope review
                                     |
                          findings and ordinary remediation
                                     |
                         fresh exact-head review until clean
                                     |
                         reviewed checkpoint -> validate -> push -> CI
```

Important behavioral changes:

- The evidence envelope is built from discovery, rather than discovery being hoped
  for during review of an already narrow envelope.
- A missing graph candidate becomes an ordinary actionable finding once discovered.
  It does not enter a separate report-only inventory loop.
- A cycle interrupted during discovery preserves typed progress and does not publish
  `review-incomplete` merely because the clock ended.
- Genuine `evidence_unavailable` is recorded in the report and can support one
  evidence-unavailable terminal outcome without a second private JSON format.

## Simplification Boundary

If Option A is chosen, the plan should evaluate removing or replacing:

- `checkpoint curation --inventory-completion` and its dedicated recipe;
- `CheckpointStartedEvent.inventory_completion` and projection marker fields;
- `CurationInventoryDisposition*` private models;
- the `inventory-disposition` publication-input kind;
- special `review-incomplete` marker/head/disposition publication gates;
- `verify_report_only_inventory_completion()` under that name;
- the two-pass run-local inventory-completion prose; and
- phrase-assertion tests in `test_maintainer_inventory_completion_contract.py`.

The report-only git-scope check is still useful and should be renamed/reused for the
graph-discovery checkpoint. Existing ordinary delta/reviewed checkpoints, generation
recovery, validation, publication, and CI safety remain outside this simplification.

## Questions and Decisions Before Planning

1. **Durable format:** accept schema-v5 report coverage (Option A), or keep discovery
   outside the report despite the reviewability tradeoff?
2. **Partial progress:** should a report carry `discovery_status=in_progress|complete`
   so the helper can checkpoint and resume partial discovery? The recommendation is
   yes; it directly prevents another cycle from starting from scratch.
3. **Review topology:** retain the existing two independent source-trust and
   graph-scope lanes after the discovery checkpoint, but remove the separate
   inventory-completion loop. This preserves semantic defense in depth without a
   third review layer.
4. **Migration scope:** active schema-v4 curation PRs would normalize to v5 when next
   prepared. Historical v1-v4 reports remain readable and need no bulk rewrite.
5. **Architecture record:** this changes durable report ownership and maintainer
   lifecycle semantics, so a new ADR is warranted. Existing ADRs 0008, 0016, 0022,
   and 0023 continue to own destination/ski-area classification; the new ADR should
   own only discovery completeness and lifecycle.

## Decision and Review Gate Status

- Developer Decision Checkpoint: **required before planning** for report ownership,
  partial-resume behavior, and removal of the current terminal inventory machinery.
- ADR: **required if Option A is accepted**; not written during research.
- Advisory review: **required at design-review after an approved plan/spec**, because
  this changes catalog trust and maintainer recovery semantics.
- Implementation: **not started**.

