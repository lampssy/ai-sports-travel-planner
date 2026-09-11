# ADR 0025: Bound Cross-Boundary Discovery By Focus Impact

Status: accepted
Date: 2026-09-11

Supersedes: the cross-boundary one-hop ownership rule in ADR 0024

Superseded by: N/A

Related specs:

- `docs/superpowers/specs/2026-09-07-maintainer-full-graph-discovery-design.md`
- `docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md`

Related docs:

- `docs/operating-model/local-maintainer-activation.md`
- `docs/architecture/adr/0024-require-durable-full-graph-discovery.md`

## Context

Durable full graph discovery must find entities that can make a selected
destination graph wrong. ADR 0024 bounded that work by following every admitted
regional pass, marketing umbrella, or shared-domain edge one hop and recording the
owning stay destination for each linked area.

That structural boundary is finite, but it is not always relevant to the selected
PR. A regional pass that directly covers one focus ski area can expose dozens of
clearly external members. Requiring candidate-exact owning stay destinations for
every member turns a local curation PR into regional network research even when the
pass is additive, deferred, and has no effect on the selected resulting graph.

The discovery boundary must still prevent a real active/default pass, connected
terrain domain, or ambiguous ownership edge from being hidden as a follow-up. The
boundary therefore needs to depend on focus-graph impact rather than graph distance
alone.

## Decision

Follow cross-boundary pass, domain, or umbrella references only far enough to
classify their effect on the selected focus graph. For an item classified
`regional_followup`, record the external product or network, its direct relationship
to the focus root, authoritative evidence, and a canonical follow-up owner. Do not
require individual external members or their owning stay destinations. Promote an
external entity into full discovery only when the selected PR changes it, the focus
graph depends on it, or it remains unclear whether it belongs inside the focus
graph.

The direct focus relationship is an allowed graph edge to the root destination or
an admitted focus entity. Examples include pass availability from the destination,
pass coverage of its ski area, or domain membership of its ski area.

A source-declared external member list may remain evidence or follow-up context. Its
members do not become entity-scope assessments or prospective relationships in the
selected PR merely because the list is reachable from an admitted product or
domain.

Graph discovery is monotonic in discovery knowledge, not immutable in active
topology. When an earlier checkpoint expanded a cross-boundary graph beyond this
focus-impact rule, its prospective relationship may be removed or replaced only
through the generation's typed discovery correction action after a reviewer names
the exact edge. Retain its endpoint candidates and evidence, record the reason as
`disproved`, `superseded`, or `scope_reclassified` in the affected assessment
rationale, include a replacement when superseded, and preserve validated
current-catalog closure. Both independent review perspectives still apply.
Uncertainty alone cannot authorize relationship removal. If the edge is
materialized in the catalog or its removal changes the focus graph, use typed
ordinary remediation and keep the finding graph-blocking until the resulting graph
is valid.

For a relationship-only correction whose endpoints and evidence already exist,
the existing source-trust and graph-scope lanes perform a targeted correction
review independently on the exact corrected head. They inspect only the changed
relationships, their endpoint assessments, evidence, focus-graph impact, and
current-catalog closure; they do not repeat unaffected candidate enumeration or
source-neighborhood research. Escalate to a fresh full dual review if the
correction adds a candidate or source neighborhood, changes a candidate's
disposition, `graph_impact`, or boundary, changes focus-graph connectivity or a
materialized catalog relationship, introduces a replacement with a new endpoint,
causes lane disagreement, or exposes another plausible omission. This uses the
existing lanes and helper actions without adding a review state or schema field.

Promotion into full discovery is required when any of these conditions applies:

- the selected PR creates, removes, or changes the external entity or a relationship
  to it;
- the focus destination's resulting behavior, ownership, access, connected terrain,
  default pass, or materialized pass coverage depends on the external graph; or
- authoritative evidence does not establish whether the entity is external or part
  of the focus graph.

Once promoted, the external stay destination becomes a focus root and receives the
normal six-kind discovery coverage. A graph-critical unknown with no conservative
representation remains `graph_blocking` or `evidence_unavailable`; this decision
does not weaken fail-closed behavior for the selected graph.

Discovery completeness is evaluated against the selected focus graph and every
promoted focus root. It is not global completeness for every external network named
by a source.

## Consequences

- Local curation PRs retain a complete, source-backed focus graph without expanding
  into unrelated regional member ownership.
- Regional products and networks remain visible, evidence-backed, and owned by a
  durable follow-up rather than disappearing from discovery.
- Large pass-network pages do not create stop conditions solely because their
  external accommodation markets are not established.
- A separate regional discovery slice must enumerate and own the complete member
  graph before that network is materialized as complete catalog coverage.
- Reviewers must make an explicit impact classification instead of treating every
  source-linked endpoint as equally in scope.
- No report schema or helper command changes are required; this is a semantic
  discovery and review boundary.

## Alternatives Considered

- **Keep one-hop owner closure.** This is structurally simple but still expands one
  regional product into every directly named area and stay market, regardless of PR
  relevance.
- **Use a numeric candidate or time cap.** This limits cost but can truncate a small
  graph that genuinely affects the focus destination and does not define semantic
  correctness.
- **Ignore external regional products entirely.** This is cheap but can hide a pass
  or domain relationship that actually changes what the focus destination offers.
- **Recursively model every network.** This maximizes global completeness but makes
  bounded destination curation impractical.

## Revisit When

- a materialized regional product can be represented safely without complete member
  coverage;
- focus-impact classification repeatedly hides relationships later found to affect
  ranking or planning;
- an authoritative machine-readable provider graph makes full regional closure
  cheap and deterministic; or
- report schema needs a first-class external-network summary instead of evidence and
  backlog handoff context.
