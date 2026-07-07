# Feature Spec: Catalog Entity Scope Assessment

## Status

- Status: accepted
- Owner: solo-builder
- Related docs: `docs/domain-language.md`, `docs/data-trust-model.md`
- Related plan: `docs/superpowers/plans/2026-07-07-catalog-entity-scope-assessment.md`
- Related ADRs: ADR 0008 and ADR 0009

## User Outcome

Full catalog curation and review must establish that the catalog contains the
right destinations, stay bases, ski areas, access edges, terrain domains, and
pass coverage before accepting individual field values. Named sectors and map
filters must be assessed without automatically becoming new entities.

## Scope

In scope:

- add a backward-compatible versioned curation-report contract and an explicit
  CLI gate that requires version 2 in current curation workflows;
- add typed entity-scope assessments with source evidence, catalog disposition,
  controlled boundary signals, and optional catalog target references;
- render and validate the new assessments;
- require the version-2 contract for future full curation in both catalog
  skills;
- add completeness and anti-over-splitting guidance;
- test KitzSki-style connected sectors and genuinely independent ski-area
  candidates.

Out of scope:

- changing current catalog entities or PR #14;
- automatically extracting candidates from websites or maps;
- changing destination, ski-area, or terrain-domain definitions;
- making every accommodation neighborhood, piste sector, webcam, or lift a
  catalog entity.

## Domain Model

- Bounded context: Catalog and Data Trust.
- Existing domain entities remain unchanged.
- `CatalogEntityScopeAssessment` is a curation-contract concept, not persisted
  catalog truth.
- Every material place, base, terrain unit, connected aggregate, or pass scope
  found during full curation receives an explicit disposition: represented,
  add entity, not separate, external pass context, deferred, or unresolved.
- A named official sector is a discovery signal. It is not sufficient boundary
  proof by itself.
- A `TerrainDomain` may aggregate only ski areas that independently merit
  separate identities; sectors must not be split merely to manufacture a
  domain.

## Decision and Review Gate

- Classification: review-gated
- High-risk domains touched: catalog data correctness, source integrity, shared
  curation-report contract, future maintenance workflow
- Developer Decision Checkpoints:
  - resolved: use typed assessments rather than prose-only guidance;
  - resolved: update curation and review skills symmetrically;
  - resolved: discovery must not imply creation; connected KitzSki sectors such
    as Pengelstein and Resterhöhe stay together without independent boundary
    evidence;
  - accepted assumptions: existing reports remain readable as schema version 1;
  - unresolved: none.
- ADR status: no new ADR; ADR 0008 and ADR 0009 already own the boundaries.
- Advisory design-review:
  - reviewers: data-trust-source-integrity, backend-api
  - status: completed; the design now requires an explicit CLI minimum-version
    gate and inventory coverage for every full graph target
- Advisory feature-review before final handoff:
  - reviewers: data-trust-source-integrity, backend-api
  - status: completed; cross-kind target references and `add_entity` without a
    matching creation delta were found and fixed; no blocker/high finding
    remains

## Architecture Decisions

`CatalogCurationReport.report_schema_version` defaults to `1`, preserving all
checked-in reports. New full curations use explicit version `2`, and both skills
invoke validation and reconciliation with
`--require-report-schema-version 2`. Version 2 requires typed entity-scope
assessments, validates them against report evidence and reviewed targets, and
requires every full graph target (`stay_destination`, `stay_base`, `ski_area`,
`ski_area_access`, `terrain_domain`, and `lift_pass_product`) to appear in at
least one assessment. Every target reference must match the candidate kind, and
`add_entity` must point to a matching identity-field creation change.

Each assessment records:

- a report-local candidate ID and display name;
- candidate kind: stay destination, stay base, ski area, ski-area access,
  terrain domain, or lift-pass product;
- disposition;
- controlled discovery/boundary signals;
- evidence IDs;
- zero or more typed catalog target references;
- concise rationale.

Adding a ski-area candidate requires at least one durable independent-owner
signal: official independent identity, separate operator, independent status or
schedule, independent weather presentation, child-scoped terrain metrics, or a
full local pass. `official_map_sector`, `webcam`, `limited_area_ticket`,
`secondary_provider_listing`, `disconnected_terrain`, and distinct access or
elevation are supporting signals only. They may trigger research but cannot
alone make a ski area.

The validator cannot discover candidates from the internet. Reliability comes
from two complementary checks: the curator records a typed inventory, and the
reviewer independently reconstructs candidates from official maps, passes,
status pages, access points, and accommodation markets before comparing that
inventory with the catalog graph.

## Data Trust and Source Integrity

- Represented, added, or `not_separate` decisions require at least one direct
  verification-capable evidence item.
- Deferred or unresolved candidates may preserve weaker discovery evidence but
  must explain the missing proof.
- Evidence used only by an entity-scope assessment is valid report evidence and
  need not correspond to a changed field.
- Existing entities are not grandfathered when a full curation changes terrain
  metrics, official maps, pass coverage, access links, or other facts that imply
  owner scope.
- Secondary providers corroborate official scope; they do not override it.

## AI / LLM Use

- Candidate discovery, disposition validation, and report reconciliation remain
  deterministic and human-reviewed.
- An LLM may assist source research but cannot create catalog truth or satisfy
  scope evidence by itself.

## Security, Privacy, and Operations

- No user data, secrets, runtime migrations, background workers, or production
  operational behavior are involved.
- Existing report JSON remains loadable; new validation failures are confined to
  explicit version-2 reports.

## Acceptance Criteria

- Existing version-1 reports load and validate unchanged.
- A version-2 report without entity-scope assessments fails validation.
- The CLI minimum-version gate rejects a version-1 report in current curation
  workflows without breaking historical report loading.
- Every full graph target in a version-2 report is referenced by at least one
  entity-scope assessment.
- Duplicate candidates, missing evidence, invalid or cross-kind target
  references, unsupported source-backed decisions, and `add_entity` without a
  matching creation change fail validation.
- A new ski area justified only by map-sector, webcam, limited-ticket, or
  secondary-provider signals fails validation.
- A connected sector assessed as `not_separate` renders successfully with its
  existing ski-area target.
- Markdown includes an `Entity Scope Assessments` table.
- Curation guidance requires source-first candidate discovery, typed
  disposition, graph completeness, and owner-scope proof.
- Review guidance independently reconstructs the candidate inventory and checks
  missing destinations, stay bases, ski areas, access edges, domains, and pass
  coverage.
- Both skills explicitly prevent over-splitting named sectors and prohibit
  creating terrain domains from artificial child areas.

## Verification

- Focused unit tests: `tests/test_catalog_curation.py`.
- Reconciliation regression tests:
  `tests/test_catalog_curation_reconciliation.py`.
- Catalog model/trust tests remain green.
- Full backend test suite and repository lint checks run before handoff.
- Skill scenarios cover KitzSki connected sectors, an independent Kitzbüheler
  Horn-style candidate, a simple one-town/one-area resort, and missing stay-base
  discovery.

## Advisory Review

- Design reviewers: Data Trust & Source Integrity; Backend / API.
- Feature reviewers: Data Trust & Source Integrity; Backend / API.
- Feature-review result: completed with no remaining blocker/high findings.
- Main residual risk: typed assessments can enforce disposition consistency but
  cannot automatically prove that the curator found every internet source; the
  review skill's independent source-first inventory remains necessary.
