# ADR 0004: Use Skill-Led Static Catalog Curation

Status: accepted
Date: 2026-06-23

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`
- `docs/superpowers/specs/2026-05-04-static-resort-data-acquisition-design.md`
- `docs/superpowers/specs/2026-05-06-catalog-acquisition-patch-pr-design.md`

Related docs:
- `README.md`
- `docs/data-trust-model.md`
- `docs/engineering-notes.md`
- `docs/product-backlog.md`

## Context

Snowcast's static catalog acquisition pipeline fetches official/open/provider pages, extracts candidate facts, generates review artifacts, and can create conservative patch PRs. In practice it is not reliable enough to replace human review for static resort and stay-base facts. It can miss the right official pages, produce low-value PRs, hit provider rate limits, and still require owner review before any source-backed value becomes canonical.

Most static catalog facts change slowly. Terrain totals, source URLs, stay-base topology, lift-pass examples, and source-backed characteristics benefit more from careful source interpretation and reviewable evidence than from broad scraping.

Future operational-status data is different. Open lifts, open piste kilometers, reported snow depth, and live operating status need timestamped observations and automated refresh. That work should not inherit the static catalog PR workflow.

## Decision

Use a skill-led static catalog curation workflow as the primary path for slow-changing catalog updates.

Codex uses a Snowcast catalog-curation skill to research official/open sources, update `app/data/resorts.json`, update `app/data/resort_trust_manifest.json`, generate a reviewable evidence report, run validation, and prepare a PR.

Typed Pydantic contracts and reusable policy validators replace broad static scraping as the safety mechanism. The validators check report shape, trust evidence coverage, source-link reviewability, cross-field consistency, and ranking-impact visibility.

Remove the manual GitHub Actions static catalog acquisition workflow from the primary maintenance path. Keep internal acquisition modules only while implementation classifies whether individual helpers are useful for future source diagnostics or freshness sentinels.

Bergfex is not a source of catalog truth. It may later be used as a warning-only freshness sentinel that points reviewers back to official sources.

## Consequences

Static catalog PRs should become easier to review because changed values, target entities, trust labels, and evidence links are prepared directly for owner review.

The system no longer spends effort maintaining a brittle scraper/LLM extraction path for data that still requires review.

The catalog remains stable because runtime code continues reading only approved catalog files.

The project adds a new curation-report contract and skill. These must stay lightweight so catalog updates do not become process-heavy.

Future operational-status automation remains a separate design with timestamped database observations, freshness, source-specific parsers, and alerting.

## Alternatives Considered

- Continue improving the static acquisition pipeline. This preserves existing work, but keeps the core mismatch: brittle scraping for slow-changing facts that still require review.
- Keep acquisition as the primary path and use the skill only for exceptions. This leaves the confusing low-value PR path in place.
- Fully manual catalog editing with no typed report. This is simpler, but loses repeatable validation and makes PRs less consistently reviewable.

## Revisit When

Revisit this decision if reliable official/provider APIs become available for most static catalog facts, if the catalog grows enough that skill-led curation becomes the bottleneck, or if future operational-status source onboarding proves that some deterministic source adapters should be reused for warning-only static freshness checks.
