# ADR 0020: Use Generation-Based Pre-Push Curation Authority

Status: accepted
Date: 2026-08-15

Supersedes in part:
- `docs/architecture/adr/0011-local-codex-maintainer-control-plane.md`

Related spec:
- `docs/superpowers/specs/2026-08-15-maintainer-curation-generation-checkpoints-design.md`

Related plan:
- `docs/superpowers/plans/2026-08-15-maintainer-curation-generation-checkpoints.md`

## Context

The maintainer currently persists pre-push curation progress in separate
remediation and reviewed-continuation records. Preparation, checkpointing,
validation, and recovery then exchange several related but independently
validated payloads. A mechanically valid local curation head can pass semantic
review and local checks yet become unusable because one capability rejects a
slightly different continuation shape or cannot prove which checkpoint is
authoritative.

This fragmentation has produced repeated `invalid-command` stops and discarded
useful work without improving the safety of the eventual GitHub mutation. The
post-push push journal, CI continuation, and terminal publication recovery do
not have the same ownership problem and should remain unchanged.

## Decision

Represent each pre-push curation attempt as one bounded, immutable generation
document with an append-only event timeline. A generation begins from an exact
selected PR head and prepared base. Within that generation, checkpoint events
advance a single latest local head through these stages:

- prepared;
- delta-validated;
- reviewed;
- fully validated;
- consumed, superseded, or invalidated.

Use one idempotent two-phase checkpoint capability for both delta-validated and
reviewed stages. Its deterministic transaction identity binds the generation,
stage, local head, report, and validation base. It records the intended private
refs before ref mutation and records completion only after both refs exist.
Inspection can therefore return the exact same typed retry action after an
interruption instead of asking Codex to reconstruct a command.

Persist each generation in its own size-bounded Pydantic document under the
private maintainer state directory. Event order, time, head lineage, report
identity, checkpoint refs, and validation authority are validated as one unit.
Inspection exposes typed recipe identifiers and typed substitutions, never
shell command strings.

Keep reviewed and validated authority as distinct projections. A reviewed head
may support the existing manual-check publication path after bounded semantic
work, while ordinary push still requires exact fully validated authority.
Validation failure remains a retryable event on the same reviewed generation;
it does not destroy or silently promote the reviewed checkpoint.

On cutover, archive all legacy unpublished pre-push curation state and refs in
a private manifest and restart open curation PRs from their exact remote heads.
Rollback to the archived shape is allowed only before any new generation or
external publication authority is created.

This decision changes only unpublished pre-push curation authority. Existing
push journals, post-push CI continuations, terminal publication recovery,
GitHub label/comment publication, approval rules, and the prohibition on
automatic merge remain unchanged.

## Consequences

The helper has one answer to "what local curation head is authoritative?" and
one checkpoint transition to recover. A newer delta checkpoint naturally
supersedes an older reviewed projection in the same generation, while prior
generation files preserve a bounded audit trail.

Checkpoint retries can distinguish dispatch syntax errors from persisted state
transitions. Capability failures no longer need to be flattened into generic
`invalid-command` results after dispatch. The runtime contract can instruct the
maintainer to execute an exact typed recipe returned by inspection.

The generation store adds a migration and more explicit state modeling. The
event schema must remain compact and must not become a store for review prose,
test output, source material, or CI state. Those artifacts continue to live in
the report, Codex task, or existing post-push records.

Existing unpublished continuations are intentionally discarded at cutover.
This sacrifices recoverable local work once in exchange for removing ambiguous
legacy authority. Remote PR branches remain untouched and are the restart
source of truth.

## Alternatives Considered

- **Keep separate remediation and reviewed continuations and add more
  adapters.** This preserves current files but leaves multiple authorities and
  command shapes to reconcile.
- **Use one mutable current-state file.** This is smaller, but interrupted ref
  mutation has no durable transaction boundary and prior authority is harder to
  audit.
- **Store one unbounded timeline document for all PRs.** This centralizes state
  but creates an ever-growing corruption and contention boundary.
- **Treat local commits or refs as sufficient authority.** Git objects prove
  content identity but do not prove report reconciliation, semantic review, or
  final validation.

## Revisit When

Revisit when pre-push curation moves to a hosted multi-worker service, multiple
maintainers need concurrent ownership of one PR, or the bounded generation
documents become too numerous for simple private-file inspection.
