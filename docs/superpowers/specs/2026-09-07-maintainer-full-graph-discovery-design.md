# Feature Spec: Maintainer Full Destination Graph Discovery

## Status

- Status: implemented and feature-reviewed; activation remains pending merge
- Owner: solo-builder
- Related plan: `docs/superpowers/plans/2026-09-07-maintainer-full-graph-discovery.md`
- Related ADR: `docs/architecture/adr/0024-require-durable-full-graph-discovery.md`
- Existing boundary ADRs:
  - `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
  - `docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md`
  - `docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md`
  - `docs/architecture/adr/0023-require-trip-level-consequences-for-ski-area-boundaries.md`

## User Outcome

Catalog curation PRs consistently investigate the complete plausible destination
graph before they are accepted. A reviewer can see which stay destinations, stay
bases, ski areas, access edges, terrain domains, and lift-pass products were found,
explicitly ruled out, or could not be established from available evidence.

Maintainer cycles interrupted during discovery resume from an exact durable report
checkpoint instead of repeating research or publishing a misleading terminal
`review-incomplete` result.

## Problem

The current helper validates closure over entities already represented in the
catalog and checks that the evidence envelope mentions all six graph candidate-kind
labels. It cannot distinguish:

- an authoritative search that found no additional candidate;
- a candidate that was found and assessed; and
- a candidate kind that was merely named to satisfy the structural validator.

Semantic skills ask reviewers to investigate the wider graph, but that work has no
first-class durable result before ordinary review. The later private
`inventory-completion` path is reactive, duplicates state outside the canonical
report, and cannot recover the missing initial candidate universe reliably.

## Scope

In scope:

- schema-v5 graph-discovery coverage in canonical curation reports;
- deterministic structural validation of coverage and cross-links;
- one report-only graph-discovery checkpoint supporting partial resumption;
- identical completeness gates for curation and proposal validation;
- retirement of the private inventory-completion lifecycle;
- compatibility with historical report schemas and persisted helper events; and
- synchronized runtime contract and post-merge skill activation.

Out of scope:

- changing Snowcast destination or ski-area boundary policy;
- using deterministic code to interpret source meaning;
- allowing discovered regional debt to expand selected-PR mutation authority;
- recurating an active destination in this implementation change;
- rewriting historical report files; and
- changing leases, exact-head preparation, recovery refs, push journals, final
  validation, or CI continuation.

## Product Fit

- Snowcast recommendations remain grounded in skier-facing destinations and
  conditions-owning terrain rather than whichever entities happen to exist in the
  current catalog.
- Missing and unavailable evidence stays explicit rather than being converted into
  false certainty.
- The change is catalog-maintenance infrastructure; it adds no generic travel or
  unsupported marketplace behavior.

## Domain Model

Bounded contexts touched:

- Catalog Curation: owns the canonical discovery record and candidate disposition.
- Maintainer Control Plane: owns exact-head checkpoint, resumption, validation, and
  publication sequencing.
- Catalog Review: owns semantic verification of source meaning and completeness.

New term:

- **graph discovery coverage**: the durable per-focus-root, per-candidate-kind record
  of established candidates and whether that source neighborhood is complete, still
  in progress, or exhausted without sufficient evidence.

Existing terms remain distinct:

- **resulting graph** is the graph represented after curation;
- **review scope** determines which findings may block the selected PR; and
- **mutation scope** determines what that PR may change.

New report models:

```python
class CatalogGraphDiscoveryCoverage(...):
    focus_stay_destination_id: str
    candidate_kind: CatalogScopeCandidateKind
    coverage_state: Literal["complete", "in_progress", "evidence_unavailable"]
    candidate_ids: list[str]
    source_family_ids: list[str]
    evidence_refs: list[str]
    rationale: str


class CatalogGraphDiscoveryRelationship(...):
    relationship_type: CatalogGraphRelationshipType
    from_candidate_id: str
    to_candidate_id: str
    evidence_refs: list[str]


class CatalogGraphDiscovery(...):
    status: Literal["in_progress", "complete"]
    coverage: list[CatalogGraphDiscoveryCoverage]
    relationships: list[CatalogGraphDiscoveryRelationship]
```

The new layer reuses:

- `CatalogReviewSourceFamily` for source neighborhoods; and
- `CatalogEntityScopeAssessment` for candidate disposition, evidence, boundary
  policy, target refs, graph impact, and backlog handling.

It does not introduce a second candidate or boundary model. The relationship record
owns only prospective edges between existing assessment identities.

## Invariants

Every schema-v5 report has `graph_discovery`.

Each coverage row:

- identifies one focused stay destination and one graph candidate kind;
- references only known source families that declare that kind;
- includes at least one appropriate authoritative source neighborhood;
- uses unique candidate IDs under every coverage state;
- directly references evidence using URLs from the declared source families; and
- gives a nonblank rationale for its state.

`complete` with candidate IDs means exhaustive enumeration. `complete` without
candidate IDs is the explicit none-found result. `in_progress` and
`evidence_unavailable` retain candidates already established rather than discarding
partial truth.

Every candidate resolves to one same-kind entity-scope assessment and shares direct
evidence with its coverage row. Every scope assessment is linked from at least one
coverage row. Coverage evidence is a first-class evidence consumer.

A complete packet has exactly one coverage row for every focus destination and each
of the six graph candidate kinds and no `in_progress` row. It includes every entity
and direct edge in the known catalog closure under its actual focus root, but is not
limited to that closure. Closure is computed independently per root so entities
cannot be swapped between roots.

An in-progress packet may omit root/kind rows. Rows already present remain fully
validated.

`evidence_unavailable` means the relevant source neighborhood was attempted. It
may coexist with known candidates and permits the discovery attempt to enter
semantic review, but it does not authorize a catalog mutation or final/proposal
validation. The only terminal route is exact-head evidence-unavailable publication
from the completed discovery checkpoint.

`ski_region` is grouping context outside the six mutable discovery kinds. Existing
resulting-graph validation still covers known region membership.

Discovery and mutation remain separate. A provisional `add_entity` disposition can
exist at the report-only discovery checkpoint before its catalog delta, but final
validation still requires the corresponding entity-creation change.

Prospective relationships connect assessed candidates using a closed relationship
vocabulary for destination/base membership, access origin and target, domain/area
membership, and pass availability/default/coverage. Endpoints must have the expected
kinds and direct relationship evidence. Known direct topology is checked per root;
new topology remains provisional until strict reconciliation.

## Bounded Expansion

Full discovery means the complete direct trip graph of every focus destination. A
candidate enters that graph when an authoritative source presents it as:

- part of the focus destination's bookable stay market;
- a primary lift-served ski option directly accessible from an admitted stay base;
- the access edge connecting an admitted base and area;
- a terrain domain containing an admitted area; or
- a locally available/default pass or a pass directly covering an admitted area or
  domain.

Each admitted edge is followed one hop to identify and assess its other endpoint.
An external destination reached only through a regional pass, marketing umbrella,
or shared domain is recorded as a non-recursive regional-follow-up candidate; its
internal graph is not automatically expanded.

If the selected PR creates or changes an edge whose validity depends on that
external destination's internal graph, the external destination must become an
explicit focus root and receive all six coverage rows. This separates complete
local discovery from unbounded regional research while preventing new edges from
depending on unreviewed graphs.

## Source Neighborhoods

The structural validator requires at least one appropriate source kind per coverage
row:

| Candidate kind | Minimum source neighborhood |
| --- | --- |
| `stay_destination` | `destination_booking` |
| `stay_base` | `destination_booking` |
| `ski_area` | `ski_area_operator` |
| `ski_area_access` | `access_transport` or `ski_area_operator` |
| `terrain_domain` | `ski_area_operator` or `pass_tariff` |
| `lift_pass_product` | `pass_tariff` |

Supplemental dependency sources may support a row but cannot be its only source.
Every referenced family must contribute at least one direct coverage evidence item,
and every candidate assessment must intersect that evidence set. Independent
reviewers determine whether the chosen pages genuinely enumerate the relevant
neighborhood and whether the recorded candidates and edges match them.

## Lifecycle

```text
inspect/recover
      |
prepare exact head/base
      |
normalize schema v5
      |
discover graph from authoritative source neighborhoods
      |
      +-- in progress --> report-only checkpoint --> resume next cycle
      |
      `-- complete ----> report-only checkpoint
                               |
                        source-trust + graph-scope review
                               |
                  +------------+--------------------+
                  |                                 |
          unavailable confirmed              no unavailable rows
                  |                                 |
          exact blocked outcome          ordinary remediation loop
                                                    |
                                    reviewed checkpoint -> validate
                                                    |
                                               push -> CI
```

The helper adds checkpoint stage `graph-discovery` and recipe
`checkpoint_curation_graph_discovery`. It derives discovery status from the exact
report and persists status plus covered/required pair, candidate, and unavailable
counts with the generation event for inspection.

`in_progress` projects to `prepare_curation`; preparation restores the exact report
and returns reason `discovery-required` with the typed graph-discovery checkpoint
action. `complete` without unavailable rows projects to the existing
reviewed-checkpoint action. `complete` with unavailable rows projects to the exact
evidence-unavailable publication recipe. Both are clean-review branches and may be
invoked only after both semantic review lanes confirm the checkpointed report.
Reviewer-requested discovery corrections are limited to a report-only descendant,
another graph-discovery checkpoint, and a fresh run of both lanes.

An initial prepared head that already contains a valid schema-v5 report may receive
its first graph-discovery checkpoint without an artificial report edit. This exact-
head exception is not available after the first checkpoint. If a process persists
the checkpoint-start event but stops before checkpoint completion, a successor
restores the recorded local head and retries that same typed transaction before it
may prepare or supersede any generation.

Graph discovery remains monotonic after its checkpoint. The generation projection
retains the latest completed graph-discovery checkpoint independently of newer
delta and reviewed checkpoints. Every descendant report mutation, including an
ordinary remediation delta, is compared with that immutable discovery report:
established root/kind rows and candidates cannot disappear, complete coverage
cannot regress, and unavailable coverage can only stay unavailable or be replaced
by complete coverage backed by stronger evidence. Candidate conclusions must share
direct evidence with a source family allowed for their own candidate kind.

The one-hop boundary includes the stay destination that owns access to a linked
area, but not that destination's internal bases or access edges. Relationships are
root-scoped and cannot chain two regional-followup candidates into a recursive
external graph.

A time cutoff during discovery preserves a partial checkpoint without publishing a
GitHub blocked label. Helper transport and mutation failures retain existing
recovery semantics.

Strict delta, reviewed, final, and proposal validation requires a complete packet
without unavailable rows. Terminal `evidence-unavailable` publication instead
requires the exact completed discovery checkpoint, matching actual local head,
immutable schema-v5 report, at least one unavailable row, and unchanged remote PR
head. The private disposition file is not replacement authority.

## Simplification

New flows stop using:

- `checkpoint curation --inventory-completion`;
- recipe `checkpoint_curation_inventory_completion`;
- private `CurationInventoryDisposition*` objects;
- publication input kind `inventory-disposition`;
- inventory marker/head projection fields;
- special terminal gates comparing private disposition to that marker; and
- the separate two-pass inventory-completion review loop.

Old persisted events remain parseable. An incomplete legacy inventory transaction
has one deprecated recovery-only recipe that cannot start a new marker. A completed
legacy marker routes through preparation into schema-v5 discovery. Already-journaled
terminal publication may consume its existing private input for exact recovery, but
new private inventory inputs cannot be created. Compatibility does not confer
obsolete semantic or mutation authority.

## Decision and Review Gate

- Classification: review-gated / full design flow.
- High-risk domains: catalog data correctness, source trust, scheduled maintainer
  reliability, durable report schema, and recovery semantics.
- Developer Decision Checkpoints:
  - resolved in first approval: canonical schema-v5 ownership, partial resumption,
    retained dual review, active-report normalization, and inventory-loop
    retirement;
  - revised decisions approved: partial-candidate preservation, direct
    one-hop expansion, typed topology/evidence closure, and explicit
    unavailable/legacy/rollback authority;
  - accepted assumptions: historical reports remain read-only compatible;
  - unresolved: none.
- ADR status: ADR 0024 accepted.
- Advisory design review:
  - reviewers: core panel, with emphasis on backend/API, data trust/source
    integrity, observability/ops, and release/change management;
  - status: completed; all High findings incorporated into this revision.
- Advisory feature review:
  - reviewers: backend/API, data trust/source integrity, observability/ops, and
    release/change management;
  - status: completed; actionable findings were addressed and focused re-review
    found no remaining Blocker, High, or Medium issue.

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Mixed | Durable discovery ownership | Determines whether PR reviewers and future cycles can inspect and reuse discovery | Canonical report is reviewable; helper-private state is smaller but hidden; prose is not enforceable | Schema-v5 canonical report | Correctly separates durable semantic evidence from mechanical helper state | ADR 0024 |
| Technical | Partial progress | Determines interruption recovery and repeat research | Durable partial checkpoint adds one stage; restart is simpler but wasteful | Durable `in_progress` checkpoint | Existing generation refs can safely carry the report-only state | ADR 0024 |
| Mixed | Review topology | Controls confidence and workflow complexity | Keep dual semantic review after discovery; adding a third lane duplicates work | Retain two lanes, remove inventory loop | Preserves semantic defense without another review layer | Runtime contract |
| Technical | Migration | Controls compatibility and activation risk | Bulk rewrite is noisy; lazy normalization limits scope | Normalize active reports, parse v1-v4 | Appropriate for an internal pre-public product | Activation guide |
| Product / Domain | Expansion boundary | Prevents both shallow local review and unbounded pass-network research | Recursive regional closure is exhaustive but impractical; known-graph closure is too narrow | Complete direct trip graph, one-hop external assessment, explicit root promotion for edited dependent edges | Gives “full graph” an objective stopping rule | ADR 0024 |
| Mixed | Partial evidence and topology | Determines whether the packet can represent known candidates and their proposed graph honestly | Exclusive outcomes lose partial facts; IDs alone hide topology | Separate coverage state from candidates and add typed evidence-backed edges | Adds the minimum structure needed for a reviewable graph | ADR 0024 |
| Technical | Unavailable and legacy authority | Controls safe terminal publication, upgrade, and rollback | Skill-only prose is simpler but not recoverable | Exact checkpoint gate plus recovery-only legacy shim and forward-compatible repair | Preserves helper authority without retaining the old normal flow | Runtime contract |

## Architecture Decisions

- The canonical report owns graph discovery coverage.
- Deterministic code validates structure, not web-source truth.
- Discovery completion precedes ordinary semantic review.
- Partial discovery is a report-only generation checkpoint.
- Coverage state is independent from candidate enumeration.
- The discovery boundary is the direct trip graph plus one-hop external assessment.
- Prospective graph relationships and candidate evidence are typed.
- Diff causality limits mutation and blocking scope, not discovery scope.
- ADR required: `0024-require-durable-full-graph-discovery.md`.
- Revisit if discovery becomes machine-acquired from a stable authoritative graph
  provider or report size becomes operationally material.

## API and Client Contract

- Public backend endpoints: unchanged.
- Web and mobile clients: unchanged.
- Maintainer CLI: adds `--stage graph-discovery`; removes
  `--inventory-completion` for new commands while retaining an inaccessible-to-new-
  work recovery shim.
- Historical schema v1-v4 files remain readable.
- Existing helper events containing the legacy marker remain parseable.

## Data Trust and Source Integrity

- Evidence comes from the existing source-family taxonomy.
- Source URLs and claim-level evidence remain in the canonical report.
- Complete-empty, partial, and unavailable states require direct evidence, rationale,
  and attempted source neighborhoods.
- Candidate assessments and prospective relationships are tied to the discovery
  evidence that established them.
- Semantic reviewers verify source authority, scope, freshness where relevant, and
  candidate completeness.
- Missing evidence never becomes implicit permission to omit a graph candidate.

## AI / LLM Use

- Deterministic logic validates only typed structure and repository state.
- Codex performs source research and semantic classification under the curation and
  review skills.
- No new LLM API call, prompt cache, model dependency, or request-path behavior is
  introduced.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| Scheduled or manual maintainer cycle | Discover, review, remediate, validate, and publish one catalog item | Local Snowcast maintainer | Existing scheduler; lifecycle changes only before semantic review |

## Security, Privacy, and Abuse

- No user data is involved.
- Source URLs and report rationale remain bounded by existing report limits.
- Helper commands retain strict typed substitutions and do not accept arbitrary
  shell recipes.
- No credentials, raw prompts, or auth material enter reports or logs.

## Observability and Operations

- Inspection exposes the latest discovery checkpoint, progress counts, checkpoint
  time, and typed next action.
- Partial discovery is distinguishable from blocked review and validation failure.
- Recovery remains event/ref based and idempotent.
- Installed skills change only after merged runtime support is available.
- The first activated curation cycle is observed through discovery checkpoint and
  resumption before broad unattended use.

## Acceptance Criteria

- A report that merely names all six candidate kinds but assesses only the existing
  catalog graph is rejected.
- Complete-empty represents none-found; partial and unavailable rows retain already
  established candidates.
- Successive checkpoints retain all established coverage rows and candidates and
  permit only forward coverage-state transitions.
- Candidates, assessments, source families, direct evidence, and prospective edges
  form a complete typed cross-link.
- Known catalog closure and direct topology remain mandatory separately per root.
- Regional exploration follows the direct-trip one-hop stopping rule.
- One-hop ownership includes the neighboring stay destination without recursively
  importing its bases/access graph, and prospective relationships cannot cross
  focus roots.
- Curation and proposal validation use the same complete gate.
- Partial report-only discovery can checkpoint and resume at the exact head.
- Complete discovery permits existing dual review. With no unavailable rows it
  permits ordinary remediation; confirmed unavailable evidence permits only the
  exact terminal outcome.
- Final and proposal validation reject unavailable rows and provisional additions or
  edges not materialized in the catalog.
- Terminal evidence-unavailable publication is bound to the exact immutable complete
  discovery checkpoint.
- New runtime flows contain no private inventory-disposition handoff.
- Historical reports and helper events remain safely readable; incomplete legacy
  transactions have one recovery-only route.
- Exact-head, lease, recovery, publication, and CI protections remain green.

## Verification

- The final affected database-free catalog and maintainer suite passed 1,332
  tests.
- The repository-wide database-free suite passed 2,712 tests, with 430 tests
  deselected by markers or the explicit PostgreSQL-opening test exclusion.
- Schema-v5 model, rendering, reconciliation, state/projection, CLI/capability,
  proposal-path, recovery, and lifecycle-bypass regressions passed.
- Ruff check, Ruff format verification, and `git diff --check` passed.
- PostgreSQL-backed verification was unavailable because the local Docker daemon
  was not running. The database-opening search-v4 test was excluded from the
  database-free run and separately confirmed to fail only on PostgreSQL connection
  refusal.

## Advisory Review

- Design reviewers: completed across Product / Strategy, Backend / API, Data Trust &
  Source Integrity, UI / UX, Security & Privacy, Observability / Ops, and Release /
  Change Management.
- Blocking design findings: incorporated into the approved revision before runtime
  implementation.
- Feature reviewers: completed on the exact implementation diff; actionable
  findings were fixed and reverified.
- Known residual risk: deterministic completeness remains structural; independent
  semantic review is still needed to catch an inappropriate or non-exhaustive source
  neighborhood.
- Accepted follow-up: cross-PR reuse of recently accepted graph discovery is deferred.
  Initial schema-v5 operation intentionally revalidates the graph for each curation
  generation; a future optimization needs explicit freshness and graph-fingerprint
  semantics.
