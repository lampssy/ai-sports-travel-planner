# Trip-Market Catalog Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the destination-nested catalog and search contract with a normalized trip-market graph while preserving all ski-area weather evidence.

**Architecture:** Execute four sequential plans on one feature branch. Build and validate the new catalog contract first, add evidence-safe persistence second, implement topology-first `search_v3` third, and perform one coordinated backend/web/mobile cutover last. Do not deploy an intermediate phase.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, psycopg/PostgreSQL, pytest, React/TypeScript/Vite, Flutter/Dart, Ruff.

---

## Decision Gate Before Execution

- Classification: review-gated, full design flow
- High-risk domains touched: catalog truth, persistence, historical evidence,
  ranking/grouping, API contracts, web/mobile clients, deploy and rollback
- Resolved owner decisions:
  - rank one trip-market group with a concrete winning configuration;
  - keep weather and climatology attached only to stable `ski_area_id` values;
  - normalize stay destinations, bases, ski areas, access links, regions,
    terrain domains, passes, and rental facts;
  - keep one `catalog.json` for solo authoring;
  - use a coordinated pre-public cutover instead of compatibility layers;
  - preserve current `search_v2` global scoring semantics in `search_v3`;
  - use pass fit only to choose/explain a pass and keep resilience non-ranking.
- Accepted assumptions: current saved/current-trip records are disposable demo
  state and may be cleared/reseeded
- Unresolved owner decisions: none at architecture level; Phase 1 includes a
  required review of the generated catalog mapping before it is committed
- ADR status: ADR 0009 accepted
- Advisory review status: core-panel design review completed; one focused
  feature review runs after the complete cutover, not after every phase

## Execution Rules

- Use one isolated `codex/` worktree/branch for all four plans.
- Finish each phase's tests and commit before starting the next phase.
- Do not merge or deploy Phases 1-3 independently.
- Do not run `reset_database()` against a database containing evidence that must
  be preserved.
- Before the Phase 4 production cutover, capture a database backup and record
  archive/climatology/current-condition/condition-history row counts by
  `ski_area_id`.
- Rollback across the cutover restores the matching database backup and previous
  application image together. Mixed old/new schemas are unsupported.
- Keep advisory work bounded: one final focused feature review after Phase 4,
  with an earlier review only if a phase exposes a new material decision.

## Phase Order

- [ ] Execute `docs/superpowers/plans/2026-07-01-normalized-catalog-contract.md`.
- [ ] Review and approve the generated catalog migration report.
- [ ] Execute `docs/superpowers/plans/2026-07-01-normalized-catalog-persistence.md`.
- [ ] Execute `docs/superpowers/plans/2026-07-01-search-v3-trip-market-ranking.md`.
- [ ] Execute `docs/superpowers/plans/2026-07-01-trip-market-client-cutover.md`.
- [ ] Run the final focused advisory review and verification matrix from Phase 4.
- [ ] Merge and deploy only the complete cutover.

## Final Product Acceptance

- One top-level search slot exists per trip-market region.
- Each result names its winning stay destination, stay base, focus ski area,
  access link, and recommended pass.
- The selected ski area's evidence seasons and conditions remain the primary
  weather explanation.
- Pass choice and resilience do not change `search_v3` global ordering.
- No catalog sync or schema migration deletes archive weather, climatology,
  current conditions, or condition-history snapshots for retained ski-area
  IDs.
- Backend, web, mobile, public pages, handoffs, and companion APIs use the new
  IDs and contracts.
- Old nested catalog files, `TerrainGroup`, `Destination` ownership,
  `ResortRepository`, `search_v1`, `search_v2`, and obsolete comparison code are
  removed after the cutover.
