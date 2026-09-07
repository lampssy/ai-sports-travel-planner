# ADR 0024: Require Durable Full Destination Graph Discovery

Status: accepted
Date: 2026-09-07

Supersedes: the reactive inventory-completion portion of
`docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`

Superseded by: N/A

Related ADRs:

- `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
- `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`
- `docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md`
- `docs/architecture/adr/0020-use-generation-based-pre-push-curation-authority.md`
- `docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md`
- `docs/architecture/adr/0023-require-trip-level-consequences-for-ski-area-boundaries.md`

Related docs:

- `docs/domain-language.md`
- `docs/operating-model/maintainer-runtime-command-contract.md`
- `docs/superpowers/specs/2026-09-07-maintainer-full-graph-discovery-design.md`

## Context

Snowcast catalog curation must investigate more than the graph already stored in
the catalog. Official destination, terrain, operator, access, and pass sources may
expose plausible stay destinations, stay bases, ski areas, access edges, terrain
domains, or lift-pass products that do not have catalog rows yet.

The existing deterministic guard computes closure from the current catalog and
requires reviewed targets and entity-scope assessments for those known entities. It
also requires the evidence envelope to mention all six candidate-kind labels. That
proves known-graph coverage but not real discovery: a report can name a kind without
recording candidates, an explicit negative result, or unavailable evidence.

Semantic skills instruct reviewers to reconstruct the wider graph, but the result
is not durable before ordinary review. A later private inventory-completion loop was
added to repair incomplete reviews. It starts too late, duplicates semantic state
outside the canonical report, and cannot give a later PR reviewer a complete source
and candidate record.

At the same time, the generation-based helper already provides valuable exact-head,
recovery, validation, and publication safety. The problem is not insufficient
orchestration safety; it is the missing semantic discovery artifact and its place in
the lifecycle.

## Decision

Newly finalized catalog curation reports use schema version 5 and contain canonical
**graph discovery coverage**.

For every focused stay destination and every graph candidate kind, coverage records
candidate IDs separately from one of three states:

- `complete`: the source neighborhood is exhausted; an empty candidate list is the
  explicit none-found result;
- `in_progress`: established candidates are retained while research continues; or
- `evidence_unavailable`: established candidates are retained, but bounded attempts
  could not establish completeness.

Each row references an appropriate authoritative source neighborhood, direct
evidence, and a rationale. Every candidate cross-links to the existing typed
entity-scope assessment of the same kind and shares evidence with its coverage row.
The existing assessment remains the sole owner of representation, addition,
folding, external context, deferral, unresolved status, boundary evidence, graph
impact, and backlog handling.

Discovery checkpoint progression is monotonic. A later checkpoint cannot remove a
prior root/kind row or established candidate, complete coverage cannot regress, and
unavailable coverage may only remain unavailable or advance to complete. Shared
candidate evidence must come from a source family allowed for that candidate kind,
not only from a supplemental dependency source.

The discovery packet also records a minimal closed set of evidence-backed
prospective relationships: destination/base membership, access origin and target,
domain/area membership, and pass availability/default/coverage. Relationship
endpoints are assessment identities; the edge record does not duplicate candidate
or boundary ownership.

The deterministic validator checks:

- root/kind completeness and uniqueness;
- coverage-state and candidate-retention rules;
- source-family existence, kind declaration, and minimum source neighborhood;
- direct coverage evidence and candidate-to-source-family closure;
- candidate-to-assessment cross-links and typed relationship endpoints;
- assessment-to-coverage closure; and
- inclusion of the current catalog-derived nodes and direct edges separately for
  each focus destination.

The validator does not claim that a URL is authoritative or exhaustive. Independent
source-trust and graph-scope reviewers verify source meaning and real-world
completeness after the discovery checkpoint.

Discovery scope, review/blocking scope, and mutation scope remain separate. Full
discovery starts from each focus destination even when a PR changes one field.
Diff-causality rules still determine which findings may block the PR and which
entities it may mutate.

Full discovery is bounded to the direct trip graph of each focus destination. It
includes the destination's bookable stay market, primary lift-served ski options,
their access edges, containing terrain domains, and locally available/default or
directly covering passes. Each admitted edge is followed one hop to identify and
assess its other endpoint. An external destination reached only through a regional
pass, marketing umbrella, or shared domain is a non-recursive regional follow-up.
That one-hop record includes the neighboring stay destination that owns linked-area
access, while excluding its internal bases and access edges. Prospective
relationships are scoped to one focus root and cannot connect two regional-followup
candidates into another expansion.
If the selected PR creates or changes an edge that depends on that external
destination's internal graph, that destination becomes an explicit focus root and
receives full coverage.

`ski_region` remains grouping context outside the six mutable discovery candidate
kinds. Existing resulting-graph validation continues to cover known region
membership.

The maintainer adds a report-only `graph-discovery` generation checkpoint:

- `in_progress` preserves valid partial coverage and resumes on a later cycle;
- `complete` permits the existing independent semantic review lanes to run; and
- a cycle cutoff during discovery does not publish terminal `review-incomplete`.

The helper derives discovery status and progress counts from the exact checkpointed
report. It validates the actual head, exact base, clean worktree, canonical report
JSON/Markdown pair, unchanged catalog/trust blobs, discovery-mode reconciliation,
and deterministic rendering.

The initial checkpoint may use the prepared head without an artificial edit when
that exact head already contains a valid schema-v5 report pair. Later discovery
updates require a report-only descendant. A persisted checkpoint-start event is
durable recovery authority: successor preparation restores and completes that exact
transaction instead of closing or replacing its generation.

Discovery may provisionally assess a candidate as `add_entity` and record prospective
edges before catalog remediation. Discovery-mode report validation and reconciliation
defer only the matching catalog creation and edge-delta invariants. Ordinary delta,
reviewed, proposal publication, and final validation remain strict, require those
entities and edges to be materialized, require complete discovery, and reject every
remaining unavailable row.

Terminal `evidence-unavailable` publication is authorized only from the exact latest
completed graph-discovery checkpoint and after both semantic review lanes confirm
that report. The remote selected head, actual local head, checkpoint report path,
immutable schema-v5 report, complete discovery status, and presence of at least one
unavailable row must all match. A requested discovery correction is limited to a
report-only descendant checkpoint followed by fresh review. The private disposition
file is not replacement authority.

The reactive private inventory-completion lifecycle is retired for new generations:

- no normal inventory-completion CLI flag or recipe;
- no new private inventory-disposition payload;
- no inventory marker/head projection state; and
- no special terminal publication gate derived from that private payload.

Historical report schemas 1-4 remain parseable. An incomplete legacy inventory
transaction retains one deprecated recovery-only recipe that cannot initiate new
work. A completed legacy marker routes through preparation into schema-v5 discovery.
An already-journaled terminal publication may read its existing private input for
exact recovery, while new private inventory inputs are rejected. Compatibility does
not create new semantic, mutation, or publication authority.

Rollback after activation is forward repair, not deployment of an old parser.
Before schema-v5 state exists, the repository and installed skills may be reverted
together while schedules remain paused. After schema-v5 reports or events exist,
keep schedules paused and ship a reviewed repair that retains their parsers while
correcting generation, projection, or recipe behavior. There is no separate runtime
graph-discovery kill switch. Helper refs and events are archived or invalidated only
through registered authority.

Installed skills are updated only after merged repository code supports schema v5
and the new recipe. The three installed Snowcast skills are activated together and
verified against the merged runtime contract.

## Consequences

- PR reports show both positive and negative discovery conclusions.
- Partial and unavailable evidence no longer discards candidates already established.
- The prospective topology is reviewable before catalog mutation.
- The direct-trip one-hop rule gives full discovery an explicit stopping boundary.
- A category label can no longer stand in for candidate discovery.
- Interrupted research resumes from an exact durable report head.
- Newly discovered candidates enter the ordinary finding/remediation loop.
- Existing dual semantic reviews remain necessary; no third review lane is added.
- Report schema and state projection gain one explicit stage while the private
  inventory/disposition detour is removed.
- Active reports require lazy schema-v5 normalization before their next review.
- Historical catalog data and report files require no bulk migration.
- Runtime and installed-skill activation must remain coordinated.
- Initial operation repeats discovery per curation generation; cross-PR reuse is
  deferred until freshness and graph-fingerprint semantics are designed.

## Alternatives Considered

- **Keep discovery only in helper-private state.** Rejected because reviewers cannot
  inspect it in the PR and the helper becomes semantic authority.
- **Strengthen skill prose without a schema change.** Rejected because there is no
  typed negative result or candidate-to-source closure and the Livigno failure can
  recur.
- **Keep the reactive inventory-completion loop and add more gates.** Rejected
  because it begins after an incomplete review and duplicates information that
  belongs in the report.
- **Automatically infer the full graph from the current catalog.** Rejected because
  unmodeled real-world candidates have no catalog rows to traverse.
- **Remove independent semantic review after structural completeness.** Rejected
  because deterministic code cannot establish source authority, meaning, or
  exhaustiveness.
- **Bulk-rewrite historical reports and helper state.** Rejected because lazy
  normalization and backward-compatible parsing are safer and less noisy.
- **Recursively close every regional pass or domain link.** Rejected because it turns
  bounded destination curation into unbounded regional research; dependent external
  graphs become explicit focus roots instead.
- **Record candidate IDs without prospective edges.** Rejected because reviewers
  could not verify the graph shape before mutation.

## Revisit When

- a stable provider supplies a machine-readable authoritative destination graph;
- graph-discovery report size becomes operationally significant;
- repeated reviews show that the six candidate kinds or source-neighborhood taxonomy
  cannot express important real-world cases; or
- maintainer orchestration moves from local Codex execution to a service with a
  different durable workflow engine.
