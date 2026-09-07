# Implementation Log: Reliable Full Destination Graph Discovery

Date: 2026-09-07

Branch: `codex/maintainer-full-graph-flow`

## Progress

- Research approved by the owner.
- Implementation plan approved by the owner.
- Implementation phase opened.
- Repository feature specification and ADR 0024 drafted before production code.
- Advisory design review completed in three bounded lanes.
- Review found material gaps in partial-evidence representation, discovery
  expansion bounds, prospective topology, evidence closure, unavailable-evidence
  publication authority, per-root closure, legacy recovery, and rollback.
- Returned to planning and revised the design before any production code change.
- Revised plan approved by the owner; implementation phase resumed.
- Added schema-v5 graph-discovery models, structural source/candidate/relationship
  validation, per-focus-root known-catalog closure, and deterministic Markdown.
- Added explicit discovery versus final reconciliation, strict final topology and
  unavailable-evidence gates, and current-catalog enforcement for schema-v5 CLI
  validation. Replaced the maintainer's six-label inventory heuristic with the
  shared graph-discovery contract across curation and proposal validation.
- Added the first-class `graph-discovery` generation stage, its persisted progress
  summary, and projection rules for initial, partial, and complete discovery.
- Added report-only Git safety, exact checkpoint validation, typed partial-resume
  actions, exact unavailable-evidence publication authority, and inspection output
  for discovery counts and checkpoint time.
- Preserved recovery of already-started legacy inventory transactions while
  rejecting any new inventory-completion transaction or private disposition input.
- Replaced the active two-pass inventory-completion guidance with schema-v5
  report-owned graph discovery, partial checkpoint resumption, bounded one-hop
  expansion, post-discovery dual review, and exact unavailable-evidence routing.
- Added durable graph-discovery language to the domain glossary and engineering
  notes, and marked the old simplification design's reactive inventory sections
  as historical rationale superseded by ADR 0024.
- Advisory feature review completed in backend/API, data-trust, and operations
  lanes. It found incomplete-checkpoint recovery, unchanged initial reports,
  partial-packet relationship validation, prospective topology, one-hop closure,
  candidate/source closure, stale activation wording, and rollback precision gaps.
- Made known-edge checks conditional on both endpoint neighborhoods being complete,
  while retaining all structural checks for genuine partial checkpoints.
- Added per-root candidate connectivity, evidence-to-declared-source-family closure,
  direct-covering pass discovery, and explicitly bounded one-hop domain/pass
  traversal. Added equivalent adversarial proposal validation.
- Added successor-run restoration of an exact `checkpoint-started` head, including
  recovery of already-started legacy inventory transactions. Completed graph
  checkpoints now resume semantic review rather than restarting discovery.
- Added a narrow initial-prepared-head exception for reports that are already valid
  schema v5, while every later discovery update still requires the exact report
  JSON/Markdown pair to change on a descendant commit.
- Clarified that post-activation rollback is a forward compatibility change that
  preserves schema-v5/event parsing; an old parser is never restored over new
  durable state.
- Addressed final review findings by making partial discovery monotonic, requiring
  candidate evidence from an allowed same-kind source neighborhood, root-scoping
  prospective relationships, and recording one-hop destination ownership without
  importing the neighbor's internal stay/access graph.
- Separated local checkpoint `head` from remote publication `expected_head`, forced
  interrupted checkpoint recovery back through ordinary preparation, added safe
  invalidation for confirmed remote drift or missing refs, and kept legacy
  inventory recovery on its historical report-only contract.
- Made `MaintainerError` traceback-safe across context-manager cleanup so typed
  validation failures cannot be masked by a frozen-dataclass assignment error.

## Decision and Review Gate

- Classification: review-gated / full design flow.
- Developer Decision Checkpoint: resolved by plan approval.
- ADR: ADR 0024 accepted.
- Advisory design review: completed with blocking findings addressed in design.
- Advisory feature review: completed and actionable findings addressed. Two
  final independent re-review attempts stalled without returning findings, so
  they were closed; a focused direct exact-diff review found no remaining
  Blocker, High, or Medium issue.
- Installed skills: intentionally unchanged until the repository contract is merged.

## Verification

- Pre-implementation research baseline: 115 focused tests passed.
- Catalog-curation schema slice: 173 tests passed.
- Schema, reconciliation, CLI, and maintainer-validation slice: 281 tests passed.
- Generation state and projection slice: 26 tests passed.
- Graph checkpoint/publication slice: 13 tests passed.
- Corrected lifecycle regression slice: 8 tests passed.
- Full changed catalog-curation and maintainer control-plane slice: 788 tests
  passed.
- Post-review focused recovery, graph-closure, proposal-parity, and rollback tests:
  23 tests passed across the targeted slices.
- Final affected catalog/maintainer suite: 1,329 tests passed and 10 tests
  deselected by marker.
- Repository-wide database-free suite: 2,712 tests passed and 430 tests
  deselected by marker or the explicit PostgreSQL-opening test exclusion.
- Final maintainer-validation/error/runtime-contract regression slice after
  replacing the literal graph-kind count with the shared contract constant:
  144 tests passed.
- Ruff passed for every touched Python module and test.
- Database-backed verification is unavailable because the local Docker daemon is
  not running. The one incorrectly database-opening `db_free` search-v4 test was
  excluded from the broad run and separately confirmed to fail only on PostgreSQL
  connection refusal.
- `git diff --check origin/main` passed and the branch contains only the intended
  repository implementation and structured-development artifacts.

## Deviations

- The first approved plan was returned to planning after advisory review exposed
  material architecture gaps. This follows the plan's explicit re-plan gate.
