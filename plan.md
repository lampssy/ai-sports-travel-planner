# Implementation Plan: Reliable Full Destination Graph Discovery

Date: 2026-09-07

Branch: `codex/maintainer-full-graph-flow`

Classification: full design flow / review-gated

Research: `research.md`

## Objective

Make full destination-graph discovery an explicit, durable prerequisite of a
Snowcast catalog review. A maintainer must record what it found, what it did not
find, and what evidence was unavailable for every relevant graph entity kind
before ordinary source-trust and graph-scope review can finish.

At the same time, remove the reactive private `inventory-completion` detour that
was added to compensate for incomplete reviews. Preserve the controls that protect
real repository and GitHub mutations: exact heads and bases, leases, generation
checkpoints, recovery refs, deterministic validation, push journals, terminal
publication, and post-push CI continuation.

## Revised Direction Requiring Reapproval

The first plan was approved, then the required advisory design review exposed
material gaps before production code began. This revision keeps the approved
architecture but makes the following consequences explicit. Reapproval confirms
all nine decisions.

1. The canonical curation report advances to schema version 5 and owns graph
   discovery coverage.
2. Partial discovery is durable and resumable through a report-only helper
   checkpoint.
3. The two independent source-trust and graph-scope review lanes remain, but they
   run only after discovery is structurally complete.
4. Active reports normalize to schema v5 when next prepared; historical v1-v4
   reports remain readable without bulk rewriting.
5. The private inventory-disposition format and terminal inventory-completion
   path are retired after compatibility has been verified.
6. Discovery is bounded to the complete direct trip graph of each focus destination;
   external regional links are assessed one hop and are non-recursive unless the
   selected PR changes an edge that depends on the external graph.
7. Coverage state and candidate enumeration are separate, so known candidates are
   retained even when completeness remains in progress or evidence becomes
   unavailable.
8. The packet records minimal typed prospective graph edges and direct discovery
   evidence, making topology and candidate-to-source closure reviewable before
   catalog mutation.
9. Terminal `evidence-unavailable`, legacy transaction recovery, and rollback each
   retain exact helper authority; they are not left to skill prose.

## Target Flow

```text
inspect both workers and recover durable work first
                         |
                         v
prepare exact PR head + exact base
                         |
                         v
normalize canonical report to schema v5
                         |
                         v
FULL GRAPH DISCOVERY
rooted at every focused stay destination
  - destination / accommodation sources
  - terrain / operator / map sources
  - access / transport sources
  - pass / tariff sources
                         |
             +-----------+-----------+
             |                       |
             v                       v
       status=in_progress       status=complete
       report-only checkpoint   report-only checkpoint
             |                       |
             v                       v
       next run resumes        independent source-trust
       exact report/head       + graph-scope review
                                     |
                          +----------+----------+
                          |                     |
                          v                     v
                    findings exist          review clean
                    ordinary delta          reviewed checkpoint
                    remediation loop              |
                          |                       v
                          +--------------> final validation
                                                  |
                                                  v
                                            push journal
                                                  |
                                                  v
                                              push + CI
```

The evidence envelope is derived from discovery. A list containing all six entity
kind names is no longer considered evidence that all six kinds were investigated.

## Scope

### In scope

- Schema-v5 graph-discovery data in the canonical JSON report and deterministic
  Markdown rendering.
- Structural validation of roots, source neighborhoods, outcomes, candidate
  cross-links, known catalog closure, and completeness.
- A first-class, report-only, resumable graph-discovery checkpoint.
- The same graph-discovery gate for curation and discovery/proposal validation.
- Removal of the current private inventory-completion lifecycle where it becomes
  redundant.
- Backward-compatible reading of historical report versions and persisted helper
  events.
- Runtime contract, activation guide, domain language, engineering notes, and
  post-merge installed-skill alignment.

### Out of scope

- Changing destination, stay-base, ski-area, terrain-domain, or pass boundary
  policy. Existing ADRs continue to own those decisions.
- Automatically proving that a web source is exhaustive. Independent semantic
  review remains responsible for source meaning and real-world completeness.
- Expanding a selected PR's mutation authority merely because discovery identifies
  a linked or regional candidate.
- Recurating Livigno or another active catalog PR in this implementation PR.
- Rewriting all historical v1-v4 reports.
- Simplifying leases, exact-head checks, recovery refs, validation authority,
  publication journals, or CI continuation.
- Installing dependencies or changing the production search/ranking model.

## Core Data Contract

### Schema-v5 models

**File:** `app/data/catalog_curation.py:56-69, 668-694, 1088-1145, 1270-1310`

Add one compact coverage layer while reusing existing source families and entity
scope assessments:

```python
CatalogGraphDiscoveryCoverageState = Literal[
    "complete",
    "in_progress",
    "evidence_unavailable",
]
CatalogGraphDiscoveryStatus = Literal["in_progress", "complete"]

CatalogGraphRelationshipType = Literal[
    "stay_destination_contains_stay_base",
    "ski_area_access_originates_at_stay_base",
    "ski_area_access_reaches_ski_area",
    "terrain_domain_contains_ski_area",
    "lift_pass_available_from_stay_destination",
    "lift_pass_default_for_stay_destination",
    "lift_pass_covers_ski_area",
    "lift_pass_covers_terrain_domain",
]


class CatalogGraphDiscoveryCoverage(CatalogCurationContractModel):
    focus_stay_destination_id: str = Field(min_length=1)
    candidate_kind: CatalogScopeCandidateKind
    coverage_state: CatalogGraphDiscoveryCoverageState
    candidate_ids: list[str] = Field(default_factory=list)
    source_family_ids: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class CatalogGraphDiscoveryRelationship(CatalogCurationContractModel):
    relationship_type: CatalogGraphRelationshipType
    from_candidate_id: str = Field(min_length=1)
    to_candidate_id: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)


class CatalogGraphDiscovery(CatalogCurationContractModel):
    status: CatalogGraphDiscoveryStatus
    coverage: list[CatalogGraphDiscoveryCoverage] = Field(default_factory=list)
    relationships: list[CatalogGraphDiscoveryRelationship] = Field(
        default_factory=list
    )


class CatalogCurationReport(...):
    ...
    graph_discovery: CatalogGraphDiscovery | None = None
```

Advance:

```python
CatalogReportSchemaVersion = Literal[1, 2, 3, 4, 5]
CURRENT_CATALOG_CURATION_REPORT_SCHEMA_VERSION = 5
```

Do not add another candidate or boundary model. Each `candidate_id` must resolve to
the existing `CatalogEntityScopeAssessment` with the same `candidate_kind`. The
relationship model records only edges between those assessments; it does not own
candidate identity or boundary disposition.

### Coverage invariants

Centralize the rules in `app/data/catalog_curation.py` so the standalone report
validator, maintainer helper, and proposal path cannot drift.

For every coverage row:

- `(focus_stay_destination_id, candidate_kind)` is unique;
- the focus ID exists in `resulting_graph.focus_stay_destination_ids`;
- candidate IDs are unique but may be present under any coverage state;
- `complete` with candidates means the source neighborhood was exhaustively
  enumerated;
- `complete` without candidates is the explicit `none found` representation;
- `in_progress` retains candidates already established while indicating that the
  source neighborhood is not yet exhausted;
- `evidence_unavailable` retains any established candidates while indicating that
  bounded attempts could not establish completeness;
- every state has a concise nonblank rationale;
- every source-family ID exists in `review_evidence_envelope`;
- each referenced source family declares the same candidate kind; and
- at least one referenced family belongs to an appropriate source neighborhood;
- every evidence ref exists; and
- for every referenced source family, at least one coverage evidence item uses one
  of that family's URLs.

Use a centralized minimum-source mapping rather than scattered conditionals:

```python
GRAPH_DISCOVERY_SOURCE_KINDS = {
    "stay_destination": frozenset({"destination_booking"}),
    "stay_base": frozenset({"destination_booking"}),
    "ski_area": frozenset({"ski_area_operator"}),
    "ski_area_access": frozenset({"access_transport", "ski_area_operator"}),
    "terrain_domain": frozenset({"ski_area_operator", "pass_tariff"}),
    "lift_pass_product": frozenset({"pass_tariff"}),
}
```

Supplemental families such as `linked_pr_dependency` may be referenced, but cannot
be the sole source neighborhood for any concluded row.

For every row containing candidates:

- every candidate maps to exactly one same-kind entity-scope assessment;
- each candidate assessment shares at least one evidence ref with the coverage row;
- every entity-scope assessment is linked from at least one discovery row; and
- one candidate may be relevant to more than one focus root without duplicating its
  assessment.

Coverage evidence is included in the generic consumed-evidence set. This gives
`complete`-empty and `evidence_unavailable` rows a proper evidence consumer instead
of manufacturing an unrelated field change.

For `status=complete`:

- exactly one row exists for every Cartesian pair of focus destination and the six
  `CatalogScopeCandidateKind` values;
- no row remains `in_progress`;
- every known catalog entity in `catalog_resulting_graph_scope()` is enumerated and
  assessed under its actual root, validated by computing closure separately for
  each focus destination; and
- no unlinked assessment remains.

For `status=in_progress`, present rows must be internally valid, but root/kind pairs
may be missing. This is the only form accepted by the partial checkpoint.

`evidence_unavailable` means a relevant source neighborhood was actually attempted
and the gap is recorded. It permits the overall discovery attempt to be marked
complete and reviewed, but final curation and proposal validation reject every
remaining unavailable row. The only terminal route is the exact-head
`evidence-unavailable` publication gate described below.

`ski_region` remains deliberate grouping context outside the six mutable discovery
candidate kinds. Resulting-graph validation continues to cover known region
membership, but schema-v5 discovery neither invents region candidates nor treats a
region as a trip configuration. Encode the exact candidate-kind-to-scope-attribute
mapping once and add a two-root candidate-swapping rejection test.

### Bounded expansion and termination

Full discovery means the complete **direct trip graph** for each focus destination,
not recursive exploration of an entire regional pass network.

Admit a candidate when an authoritative source presents it as one of:

- a stay destination or stay base in the focus destination's bookable stay market;
- a primary lift-served ski option directly accessible from an admitted stay base;
- the access edge connecting an admitted base to an admitted ski area;
- a terrain domain containing an admitted ski area; or
- a pass locally available/default from the focus destination or directly covering
  an admitted ski area/domain.

Follow each admitted edge one hop far enough to identify and assess its other end.
Do not recursively inventory the internal bases, areas, passes, or domains of an
external destination reached only through a regional pass, marketing umbrella, or
shared-domain edge. Record that external node as a typed candidate with
`graph_impact=regional_followup` and a backlog anchor.

If the selected PR creates or changes an edge whose correctness depends on an
external destination's internal graph, that destination must be added explicitly to
`focus_stay_destination_ids`; it then receives all six coverage rows. This keeps
discovery bounded while preventing a new cross-destination edge from relying on an
unreviewed graph.

### Prospective topology

`CatalogGraphDiscovery.relationships` records the proposed direct graph before
catalog mutation. Relationship endpoints must both resolve to enumerated candidate
assessments and match the endpoint kinds implied by `relationship_type`.

Each relationship has direct evidence. Its evidence must be included in at least
one coverage row for either endpoint and use a URL from a source family referenced
by that row. Duplicate relationship triples are forbidden.

For known catalog entities, compare relationships separately per focus root against
the current catalog topology. Missing known direct edges fail discovery validation.
Prospective additions may introduce new relationships without catalog deltas at the
report-only checkpoint; final reconciliation requires those edges to be materialized
or reclassified.

### Discovery-phase versus final validation

Graph discovery occurs before catalog remediation, so an assessment may correctly
say `add_entity` before the corresponding catalog delta exists. Add a clearly named
validation mode rather than weakening final report validation:

```python
validate_catalog_graph_discovery(
    report,
    catalog,
    *,
    require_complete: bool,
    allow_pending_scope_changes: bool,
)
```

The graph-discovery checkpoint uses `allow_pending_scope_changes=True`; it still
validates assessment shape, evidence references, ski-area boundary records,
prospective relationships, and discovery cross-links, but defers only:

- the rule requiring an `add_entity` assessment to already have a matching catalog
  creation delta; and
- the reconciliation parity check for that same not-yet-materialized identity and
  its prospective graph relationships.

Propagate this explicit phase into `app/data/catalog_curation_reconciliation.py`;
do not place a helper-only exception around a strict reconciliation call. Ordinary
delta, reviewed, final, and proposal publication validation keep strict
catalog-delta and topology parity.

This exception must be narrow and covered by negative tests proving that final and
proposal publication validation still reject unmaterialized `add_entity`
dispositions and prospective edges.

Schema-v5 validation always requires a current catalog snapshot. The standalone CLI
must reject complete schema-v5 validation without `--current-catalog-path`; any
weaker parse-only operation must use an explicitly named mode and cannot print a
complete-validation success result.

### Rendering

**File:** `app/data/catalog_curation.py:3290-3405`

Render a deterministic `## Graph Discovery` section before the existing evidence
envelope. Include:

- a per-root count summary by candidate kind and coverage state;
- candidate name and ID;
- disposition and graph impact;
- prospective direct relationships;
- direct evidence links and source-family IDs;
- concise rationale; and
- a prominent unavailable-evidence summary.

Derive names, dispositions, impact, and links from existing assessments and evidence
rather than duplicating them in canonical coverage rows. Sort by focus destination
and canonical candidate-kind order. Do not render an empty graph-discovery section
for historical schemas.

## Maintainer Lifecycle Changes

### Typed checkpoint stage and recipe

**Files:**

- `ops/maintainer/curation_state.py:75-90, 306-329, 560-780`
- `ops/maintainer/models.py`
- `ops/maintainer/cli.py:160-200`
- `ops/maintainer/capabilities.py:850-1045`

Add:

```python
class CurationCheckpointStage(StrEnum):
    GRAPH_DISCOVERY = "graph-discovery"
    DELTA_VALIDATED = "delta-validated"
    REVIEWED = "reviewed"


class CurationRecipeId(StrEnum):
    ...
    CHECKPOINT_GRAPH_DISCOVERY = "checkpoint_curation_graph_discovery"
```

The registered command is:

```bash
python -m ops.maintainer.cli checkpoint curation \
  --pr <PR> \
  --generation-id <GENERATION_ID> \
  --head <HEAD> \
  --report <REPORT> \
  --stage graph-discovery \
  --base-dir <EXACT_BASE_DIR> \
  --run-id <RUN_ID>
```

Remove `--inventory-completion` from normal recipes and documentation. Retain a
deprecated recovery-only parser/recipe path that is accepted exclusively when the
current projection contains an already-started legacy inventory transaction; it
cannot initiate a new marker.

Persist a helper-derived discovery summary on the checkpoint-started event so
projection does not need to reread a mutable checkout:

```python
class CurationGraphDiscoveryCheckpoint(...):
    status: Literal["in_progress", "complete"]
    covered_pairs: int
    required_pairs: int
    candidate_count: int
    unavailable_pairs: int
```

Inspection exposes this summary and checkpoint time so repeated partial runs are
diagnosable. Continue parsing the old optional `inventory_completion` event field
for backward compatibility, but never emit it for new generations.

### Report-only checkpoint safety

**File:** `ops/maintainer/git_ops.py:874-910`

Rename and generalize:

```python
verify_report_only_graph_discovery(
    previous_head: str,
    discovery_head: str,
    report_path: str,
) -> None
```

Keep the existing safety properties:

- the new head descends from the latest helper checkpoint;
- local `HEAD` equals the submitted head;
- the worktree is clean; and
- the only changed files are the canonical report JSON and Markdown pair.

Do not infer report-only scope from caller prose. Validate the actual Git diff.

### Dedicated graph-discovery validation

**Files:**

- `ops/maintainer/validation.py:536-598, 650-805`
- `ops/maintainer/capabilities.py:880-1045`

Replace `_require_primary_destination_graph_inventory()` with a call to the shared
schema-v5 graph-discovery validator. Keep its useful known-catalog closure behavior
inside that shared validator.

Add a helper path used by `checkpoint ... --stage graph-discovery` that checks:

- exact PR, generation, head, report path, and prepare-time base;
- schema-v5 typed report;
- report-only repository scope;
- catalog and trust blobs unchanged from the prior checkpoint;
- deterministic JSON/Markdown parity;
- exact-base discovery-mode reconciliation for the unchanged catalog/trust state;
  and
- graph discovery in either valid `in_progress` or valid `complete` form.

Ordinary delta/reviewed/final validation requires `graph_discovery.status=complete`.
Apply the same complete gate in `validate_proposal()` before a proposal can become
validated or publishable. Reviewed/final/proposal validation also rejects any
remaining `coverage_state=evidence_unavailable` row.

### Projection and resumption

**File:** `ops/maintainer/curation_state.py:597-770`

Projection behavior becomes:

| Latest durable state | Typed next action | Meaning |
| --- | --- | --- |
| prepared, no discovery checkpoint | `checkpoint_curation_graph_discovery` | Build initial candidate inventory |
| graph-discovery, in progress | `prepare_curation` | Restore and continue the exact partial report |
| graph-discovery, complete, no unavailable rows | `checkpoint_curation_reviewed` | Run both independent semantic lanes, then checkpoint only if clean |
| graph-discovery, complete, unavailable rows | `publish_evidence_unavailable_outcome` | Run both independent semantic lanes, then publish only if they confirm the exact report |
| delta-validated | `checkpoint_curation_reviewed` | Existing post-remediation review path |
| reviewed | `validate_curation` | Existing final validation path |
| fully validated | `publish_push` | Existing publication path |

`prepare_curation` must return reason `discovery-required` and the complete typed
`checkpoint_curation_graph_discovery` next action when it restores a partial
discovery checkpoint. Repeated partial report-only checkpoints are allowed only on
descendant heads within the same generation. After complete discovery, a
reviewer-requested discovery correction may also create one report-only descendant
checkpoint; both lanes then run again.

A time cutoff during discovery checkpoints partial progress and exits without a
GitHub blocked label. A transport failure follows the existing helper recovery
contract. A genuine `evidence_unavailable` conclusion remains in the canonical
report and may support a terminal blocked publication only after independent review.

### Exact unavailable-evidence publication authority

**Files:**

- `ops/maintainer/capabilities.py:3120-3210`
- `ops/maintainer/validation.py`

Replace the private inventory-disposition gate with immutable report authority.
`publish ... --reason evidence-unavailable` requires:

- the requested remote PR head still equals the generation's selected head;
- the latest completed helper checkpoint is `graph-discovery` with derived status
  `complete`;
- actual local `HEAD` equals that checkpoint head;
- the report path equals the checkpointed report path;
- the immutable report at that head is schema v5 and passes complete discovery
  validation;
- at least one coverage row is `evidence_unavailable`; and
- no later checkpoint or local commit exists.

The independent-review obligation remains in the skill contract, as it is today;
the helper proves that the exact durable evidence packet supporting the semantic
outcome exists. `review-incomplete` is not a new terminal route for partial
discovery.

### Review and remediation behavior

After a complete graph-discovery checkpoint:

1. Run the existing independent source-trust lane.
2. Run the existing independent graph-scope lane.
3. Require reviewers to verify that source families are appropriate enumerators and
   that the declared candidates/results match the source meaning.
4. Convert omissions or wrong dispositions into actionable finding families.
5. For an unavailable packet, correct discovery only through a report-only
   descendant graph checkpoint and rerun both lanes.
6. Once no unavailable rows remain, apply catalog/report/trust/backlog changes
   through the existing delta checkpoint and fresh-review loop. Every delta is
   compared with the immutable completed graph-discovery report, so remediation
   cannot remove a discovered root/kind row or candidate.

There is no third inventory review lane. Discovery completeness is a prerequisite;
semantic correctness remains the responsibility of the existing two lanes.

## Simplification and Compatibility

### Remove new uses of the reactive inventory path

**Files:**

- `ops/maintainer/cli.py`
- `ops/maintainer/curation_state.py`
- `ops/maintainer/capabilities.py`
- `ops/maintainer/git_ops.py`
- `ops/maintainer/publication.py` and `ops/maintainer/models.py` where referenced
- `tests/test_maintainer_inventory_completion_contract.py`

Delete or retire from new flows:

- recipe `checkpoint_curation_inventory_completion` and CLI flag
  `--inventory-completion`, except for the narrow recovery-only compatibility path
  below;
- new construction of `CurationInventorySourceAttempt`,
  `CurationInventoryDispositionItem`, and `CurationInventoryDisposition`;
- creation of publication input kind `inventory-disposition`;
- projected `inventory_completion_checkpointed` and marker-head fields;
- special terminal `review-incomplete` gates that compare a private disposition to
  an inventory marker;
- the two-pass run-local inventory-completion instructions; and
- phrase-only tests that assert the old prose rather than behavior.

Compatibility behavior is deterministic:

- an incomplete legacy inventory checkpoint projects only to its deprecated
  recovery recipe; the handler accepts the old flag only when its transaction ID
  exactly matches that existing incomplete event;
- after that transaction completes, or when a completed legacy marker is loaded,
  projection routes to `prepare_curation` and preparation returns
  `discovery-required` for schema-v5 normalization;
- no command can initiate a new legacy inventory checkpoint;
- an already-journaled terminal publication may still read its existing private
  input for exact recovery, but new publication-input creation rejects that kind;
  and
- transaction-ID and event parsing remain compatible.

Do not preserve obsolete semantic or mutation authority. Add fixtures proving
incomplete, completed, superseded, and journaled legacy states behave exactly as
specified.

Before activation, inspect both current worker inventories. The compatibility shim
allows safe recovery if a live transaction appeared after design-time inspection;
do not silently discard it.

### Preserve these controls unchanged

- worker inspection and recovery priority;
- one-item selection and lease ownership;
- exact remote head and exact prepare-time base;
- deterministic checkpoint transactions and helper-owned refs;
- validation-remediation continuation;
- guarded push journal and recovery;
- lifecycle publication authority;
- post-push CI priority and repair continuation; and
- approval/merge safety boundaries.

## Documentation and Architecture Records

### Feature specification

**Create:**
`docs/superpowers/specs/2026-09-07-maintainer-full-graph-discovery-design.md`

Capture the problem, target flow, schema-v5 contract, responsibility split,
resumption semantics, simplification boundary, rollout, and acceptance criteria.

### Architecture decision record

**Create:**
`docs/architecture/adr/0024-require-durable-full-graph-discovery.md`

Record why the canonical report owns discovery coverage, why deterministic checks
remain structural, why partial discovery is checkpointed, and why private inventory
dispositions are retired. Link existing destination/ski-area policy ADRs rather than
duplicating their boundary rules.

### Operating-model documents

**Modify:**

- `docs/operating-model/maintainer-runtime-command-contract.md`
- `docs/operating-model/local-maintainer-activation.md`
- `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`
- `docs/domain-language.md`
- `docs/engineering-notes.md`

The runtime contract must contain the exact registered recipe, substitutions,
outcomes, stage transitions, recovery behavior, and publication boundary. Mark the
old inventory-completion design as superseded instead of leaving two apparently
active workflows.

Domain language should define **graph discovery coverage** as the durable statement
of investigated candidate kinds and distinguish it from:

- resulting graph: entities and edges represented after curation;
- review scope: fields and linked dependencies that may block the selected PR; and
- mutation scope: files/entities the selected PR may change.

## Installed Skills and Activation Boundary

**Post-merge files:**

- `/Users/awownysz/.codex/skills/snowcast-maintainer/SKILL.md`
- `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`
- `/Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md`

Do not update these installed global skills while the implementation exists only on
the feature branch. The scheduled maintainer reads the merged repository contract;
updating the skill first would intentionally trigger a contract mismatch.

After repository changes are merged to `main`:

1. inspect both helper workers and verify no unresolved mutation/recovery record;
2. pause maintainer schedules for the short activation window if they are active;
3. update all three installed skills together from the merged contract;
4. verify every command and lifecycle term against `main`;
5. run a bounded helper inspection/smoke test; and
6. resume schedules.

The maintainer skill will own lifecycle sequencing. The curation skill will own
source-neighborhood discovery and report construction. The review skill will verify
the real-world completeness and dispositions of the checkpointed packet.

## Advisory Review Gate

Design review completed in three bounded lanes covering the core panel plus release
management. It found blocking gaps in partial evidence, expansion bounds,
prospective topology, source closure, unavailable-evidence authority, per-root known
closure, legacy recovery, and rollback. This revision addresses them and has
returned to owner plan review before production code.

At implementation completion, run a focused advisory `feature-review` on the exact
diff. Advisory reviewers review only; implementation remains in the main task.

## Test-First Implementation Strategy

### 1. Schema and renderer tests

**Files:**

- `tests/test_catalog_curation.py`
- `tests/test_catalog_curation_reconciliation.py`

Add failing tests first for:

- schema-v5 parsing and required graph-discovery field;
- unique root/kind rows;
- valid `complete`, `in_progress`, and `evidence_unavailable` coverage states;
- complete-empty as explicit none-found;
- partial and unavailable rows retaining already established candidates;
- unknown or wrong-kind candidate IDs;
- unknown source families and wrong source neighborhoods;
- candidate-to-coverage evidence intersection and family URL closure;
- complete Cartesian root/kind coverage;
- known catalog closure coverage separately per root;
- two-root candidate swapping rejection;
- explicit exclusion of `ski_region` from discovery kinds;
- relationship endpoint kinds, duplicates, evidence, and known-topology closure;
- unlinked entity-scope assessments;
- pending `add_entity` accepted only during discovery checkpoint validation;
- pending entities/edges rejected during strict reconciliation and final validation;
- deterministic Markdown ordering and parity; and
- historical v1-v4 parsing without graph discovery.

### 2. Maintainer validation tests

**File:** `tests/test_maintainer_validation.py`

Add failing tests proving:

- a Livigno-like report with five known assessments and all six kind labels is
  rejected;
- explicit candidates or explicit negative outcomes satisfy structural coverage;
- an in-progress packet is accepted only by graph-discovery checkpoint validation;
- ordinary delta/reviewed/final validation requires complete discovery;
- final validation rejects unavailable coverage;
- known closure remains mandatory per focus root;
- schema-v5 complete validation rejects a missing current catalog;
- proposal validation uses the same complete gate; and
- `evidence_unavailable` records do not silently authorize catalog changes.

### 3. Generation projection and compatibility tests

**File:** `tests/test_maintainer_curation_state.py`

Add failing tests for:

- initial graph-discovery next action;
- in-progress checkpoint -> prepare/resume;
- complete checkpoint -> review checkpoint;
- repeated descendant graph-discovery checkpoints;
- projected discovery counts and unavailable-pair diagnostics;
- delta/reviewed/validation/push behavior remaining unchanged;
- incomplete transaction recovery;
- incomplete legacy inventory transaction -> deprecated recovery-only action;
- completed legacy marker -> prepare/schema-v5 discovery; and
- superseded and journaled legacy states remaining parseable and safe.

### 4. CLI and capability integration tests

**Files:**

- `tests/test_maintainer_cli.py`
- `tests/test_maintainer_runtime.py`
- `tests/test_maintainer_runtime_command_contract.py`
- `tests/test_maintainer_publication_input.py`

Cover:

- partial report-only checkpoint and typed next action;
- complete report-only checkpoint and typed next action;
- prepare restoring partial discovery with all substitutions;
- actual-head, exact-base, report-substitution, and dirty-worktree rejection;
- final blocked/evidence-unavailable derived from the exact immutable canonical
  report and latest discovery checkpoint;
- absence of the private inventory-disposition input in new recipes; and
- parser, documentation, and recipe-registry parity.

### 5. Git safety tests

**File:** `tests/test_maintainer_git_ops.py`

Rename existing report-only tests and retain negative coverage for:

- non-descendant head;
- local HEAD movement;
- extra catalog/trust/backlog/test changes;
- missing JSON or Markdown pair; and
- dirty worktree.

### 6. Replace phrase tests with behavior tests

Delete `tests/test_maintainer_inventory_completion_contract.py` only after all
meaningful behavior has moved into schema, state, CLI, validation, and runtime
contract tests. Do not preserve tests that merely search skill prose for old terms.

### 7. End-to-end scenarios

Exercise these scenarios through the real helper API/CLI:

1. Sparse known graph plus six category labels is rejected.
2. Complete-with-candidates and complete-empty rows represent enumeration and
   none-found without losing partial candidates.
3. A partial or unavailable row retains established candidate IDs and evidence.
4. Partial checkpoint -> inspect -> prepare -> resume preserves exact progress.
5. Complete checkpoint exposes review authority but no mutation authority.
6. A discovered new candidate and prospective edge become an ordinary
   remediation/delta cycle.
7. Two focus roots cannot swap known closure entities.
8. A regional one-hop candidate does not recursively expand unless an edited edge
   promotes its destination to a focus root.
9. Proposal validation cannot bypass the discovery gate.
10. Evidence unavailable is terminal only after review and from the exact report
   head.
11. Legacy incomplete markers recover through the deprecated recipe; completed
    markers route into schema-v5 discovery.
12. Legacy and schema-v5 persisted events can be inspected safely after deployment.

## Verification Commands

Run focused tests continuously after each implementation slice:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py
```

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q \
  tests/test_maintainer_validation.py \
  tests/test_maintainer_curation_state.py \
  tests/test_maintainer_cli.py \
  tests/test_maintainer_git_ops.py \
  tests/test_maintainer_runtime_command_contract.py
```

Then run the broader maintainer/catalog unit suite:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py \
  tests/test_maintainer_*.py
```

Run static checks on touched Python files:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check \
  app/data/catalog_curation.py \
  ops/maintainer \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py \
  tests/test_maintainer_*.py
```

Run repository validators and rendered-report checks using schema-v5 fixtures. Run
the full test suite if local PostgreSQL/storage prerequisites are healthy; otherwise
report the exact skipped infrastructure-dependent boundary and preserve the green
database-free unit evidence.

Before handoff:

```bash
git diff --check
git status --short
```

## Rollout and Migration

1. Merge repository code, tests, spec, ADR, and operating-model docs together.
2. Keep historical schema v1-v4 reports readable.
3. Normalize an active curation report to v5 only when its next generation is
   prepared.
4. Preserve legacy generation event parsing and its recovery-only recipe; do not
   bulk-edit helper state.
5. Pause scheduled cycles before the merge/activation window and inspect current
   helper state. Recover any incomplete legacy transaction through the compatibility
   path rather than discarding it.
6. Update installed skills together only after merged `main` contains the new
   parser and recipes.
7. Smoke-test helper inspection and one non-mutating prepare/checkpoint fixture.
8. Re-enable scheduled cycles.

The first real active curation cycle after activation should be observed through its
graph-discovery checkpoint before unattended runs continue broadly.

## Rollback Plan

Before activation, rollback is an ordinary feature-branch/PR revert and installed
skills remain untouched.

After merge but before skill activation, keep schedules paused: the old installed
skill should fail closed with contract mismatch against the new repository rather
than infer commands.

After activation, do not deploy an old binary that cannot parse schema-v5 reports or
`graph-discovery` events. Keep schedules paused and ship a **forward-compatible
repair**:

- correct generation, projection, or recipe behavior while retaining schema-v5 and
  new-event parsing; there is no separate runtime graph-discovery kill switch;
- restore a matching compatibility version of the runtime contract and installed
  skills together;
- preserve helper refs and events rather than deleting state;
- archive or invalidate a specific schema-v5 generation only through registered
  helper authority if prior behavior cannot consume it;
- do not revert catalog data merely to roll back orchestration.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Schema v5 adds report size | Add compact coverage and edge rows; derive names/dispositions/links in Markdown |
| Deterministic validation pretends to prove web truth | Validate structure only; retain independent semantic review |
| Partial evidence loses known candidates | Separate coverage state from candidate enumeration |
| Discovery candidate cannot yet have an `add_entity` delta | Narrow discovery-phase validation and reconciliation exception; strict paths stay strict |
| Partial checkpoints create more state branches | Use the existing generation transaction/ref mechanism and one new stage |
| Old helper events become unreadable | Preserve parser, transaction identity, and a recovery-only legacy recipe |
| Installed skill drifts from merged commands | Activate all three skills only after merge and verify recipe parity |
| Broader discovery expands unrelated PR mutations | Keep discovery scope separate from diff causality and mutation authority |
| Regional links expand research without bound | Use the direct-trip one-hop rule and promote only edge-dependent destinations to focus roots |
| Unavailable evidence reaches final validation | Reject unavailable rows on strict paths and require exact checkpoint authority for terminal publication |
| Simplification accidentally removes recovery safety | Explicitly exclude leases, refs, journals, final validation, and CI from cleanup |

## Open Questions

No owner decision is required before implementation beyond approval of this plan.
During implementation, stop and return for a new Developer Decision Checkpoint if:

- the discovery-phase `add_entity` exception cannot be isolated from final
  validation;
- proposal/discovery artifacts cannot use the same schema without materially
  changing acquisition behavior; or
- the one-hop expansion or typed relationship vocabulary cannot represent a real
  catalog fixture without introducing ambiguous topology.

Minor naming or file-placement adjustments that preserve this architecture are
mechanical and do not require another checkpoint.

## Decision and Review Gate

- Developer Decision Checkpoint: **resolved**. The owner approved the nine
  decisions under "Revised Direction Requiring Reapproval."
- ADR: **accepted** as ADR 0024.
- Advisory design review: **completed**; all Blocker/High findings are addressed in
  the revised design, with production code still untouched.
- Advisory feature review: **completed**; actionable findings were addressed and
  the final exact diff received a direct focused re-review after two independent
  re-review attempts stalled without returning findings.
- Implementation: **complete and PR-ready**.
- Dependencies: **no package installation or dependency change planned**.

## Implementation Todo List

- [DONE] Record the first plan approval and open the design-review gate.
- [DONE] Create the schema-v5 feature spec and ADR 0024.
- [DONE] Run advisory design review and incorporate its findings into the design.
- [DONE] Obtain owner approval of the revised plan and return `.structured-dev-state`
  to implementation.
- [DONE] Add failing schema-v5 graph-discovery model and rendering tests.
- [DONE] Implement graph-discovery models, invariants, validation modes, and rendering.
- [DONE] Add failing maintainer validation tests for curation and proposal paths.
- [DONE] Replace the known-kind-label guard with shared graph-discovery validation.
- [DONE] Add failing state/projection tests for partial and complete discovery.
- [DONE] Implement the graph-discovery checkpoint stage, recipe, event data, and typed actions.
- [DONE] Add failing CLI/capability/git-safety tests for report-only checkpointing and resumption.
- [DONE] Implement report-only graph-discovery checkpoint validation and resumption.
- [DONE] Add legacy event fixtures and verify backward-compatible projection.
- [DONE] Remove new production uses of inventory completion and private inventory disposition.
- [DONE] Replace phrase-only inventory tests with behavioral lifecycle tests.
- [DONE] Update runtime contract, activation guide, superseded design, domain language, and engineering notes.
- [DONE] Run focused schema and maintainer test suites.
- [DONE] Run Ruff and broader database-free catalog/maintainer tests.
- [DONE] Run full tests where local infrastructure permits and document any external limitation.
- [DONE] Run advisory feature review and address actionable findings.
- [DONE] Preserve completed graph-discovery authority across ordinary remediation
  and reject descendant reports that remove established discovery.
- [DONE] Re-run exact verification, `git diff --check`, and worktree inspection.
- [DONE] Prepare a PR-ready implementation handoff without changing installed global skills.
- [ ] After merge, inspect helper state, update all three installed skills together, verify parity, and smoke-test activation.
