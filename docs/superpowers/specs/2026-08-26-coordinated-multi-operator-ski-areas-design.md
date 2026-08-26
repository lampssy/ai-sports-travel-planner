# Feature Spec: Coordinated Multi-Operator Ski Areas

## Status

- Status: implementation and clean Data Trust / Backend API feature re-review
  complete; installed repository-skill activation remains pending merge to main
- Owner: solo-builder
- Related docs: `docs/domain-language.md`, `docs/data-trust-model.md`
- Related plan: `docs/superpowers/plans/2026-08-26-coordinated-multi-operator-ski-areas.md`
- Related ADRs: ADR 0008, ADR 0016, ADR 0021, accepted ADR 0022

## User Outcome

Snowcast can model one coherent ski area even when several lift companies operate
its component sectors, provided authoritative sources establish one durable,
complete skier-facing operations boundary. This prevents artificial splitting of
areas such as Livigno's west side without allowing regional passes or marketing
umbrellas to become ski areas.

## Scope

In scope:

- define a coordinated multi-operator ski area as an alternative to a
  single-operator evidence-owner boundary;
- extend schema-version-3 ski-area boundary assessments with explicit
  coordinated ownership and component reconciliation;
- add deterministic validation for the minimum coordinated-area evidence packet;
- align domain language, curation guidance, review guidance, and boundary
  adjudication;
- add focused contract tests for accepted and rejected coordinated areas;
- make a later PR #36 maintainer cycle able to assess the proposed Livigno
  Carosello-side graph under the new rule.

Out of scope:

- adding `SkiSubArea` as a runtime entity;
- changing search, ranking, recommendation-card, or pass-selection behavior;
- treating every shared pass, consortium, valley, or regional brand as a ski
  area;
- automatically activating weather sampling for a new composite area;
- directly modifying PR #36 or migrating Livigno weather history in this policy
  change.

## Product Fit

- Search results retain terrain units that match a skier's practical experience
  instead of exposing every lift company as a separate option.
- Weather, operating status, terrain metrics, and passes remain attached to a
  defensible complete area rather than an arbitrary marketing umbrella.
- Uncertainty remains explicit: coordinated ownership can pass while weather
  sampling remains deferred under the independent weather-geometry policy.
- The rule does not turn Snowcast into a generic pass marketplace or reproduce
  provider taxonomy without source review.

## Domain Model

- Bounded contexts touched: Catalog and Data Trust.
- Domain term introduced: `coordinated multi-operator ski area`.
- Runtime entities remain unchanged: the result is still one `SkiArea`.
- `SkiArea` evidence ownership describes a durable publication and operating
  boundary, not necessarily one legal company.
- The report-only owner-scope type is split into operational and weather aliases.
  `operational_scope` gains `coordinated`; `weather_scope` retains its existing
  values and cannot use `coordinated`.
- A coordinated parent records `component_candidate_ids`, typed
  `coordination_evidence_families`, and aggregate
  `coordination_evidence_refs`. Each family record has `family`, non-empty
  `evidence_refs`, and non-empty `covered_component_candidate_ids`. Existing
  non-coordinated assessments leave all three lists empty.
- Scope signals gain:
  - `official_complete_lift_inventory`;
  - `coordinated_status_or_schedule`;
  - `common_full_coverage_pass`.
- `common_full_coverage_pass` means one pass covers every coordinated component.
  It may also cover a separately modeled adjacent area; pass coverage does not
  define the coordinated boundary by itself. The parent's `pass_scope` may be
  `full_local` or `shared_only`.

Invariants:

1. The existing complete-terrain and material-separation gates remain required.
2. A coordinated area has official evidence for all five typed families. Every
   family covers the parent's exact component set, and the family evidence refs
   are included in both boundary and scope evidence.
3. Each coordinated child is assessed exactly once with
   `disposition=not_separate`, `parent_ski_area_id` equal to the coordinated
   parent, a target reference to that parent, and `operational_scope=coordinated`.
   The coordinated parent is a distinct candidate and is not included in its own
   component list.
4. A component that independently passes the normal complete-area ownership
   gates remains a separate `SkiArea`. Evaluate source-backed signals rather
   than trusting its `not_separate`, `redundant`, or `coordinated` declarations:
   connected complete terrain needs two owner categories including operations
   or weather, while transfer-required or disconnected complete terrain needs
   one owner category.
5. A material transfer-required or weather-distinct complete area cannot be
   hidden inside a coordinated area. Minor nursery or satellite lifts may remain
   components when the common inventory, status, pass, and stay market cover
   them, they do not create materially distinct weather or season semantics, and
   they have no independent recommendation value.
6. Shared branding, a shared pass, an operator directory, map proximity, or one
   common website cannot establish a coordinated boundary alone.
7. Coordinated operational ownership does not imply valid weather sampling.
   ADR 0021 must pass independently before `weather_sampling_status=active`.

## Decision and Review Gate

- Classification: review-gated
- High-risk domains touched: catalog graph correctness, source integrity,
  weather-evidence ownership, shared curation-report contract, maintainer
  convergence
- Developer Decision Checkpoints:
  - resolved: support a coordinated multi-operator area rather than requiring a
    single legal operator;
  - resolved: keep the existing complete-scope and material-separation gates;
  - resolved: allow minor satellite or nursery lifts inside the coordinated area
    when they share its complete local product and lack independent ski-area
    value;
  - resolved: represent the distinction explicitly rather than broadening the
    meaning of `independent` or waiving the owner gate;
  - accepted assumptions: schema version 3 can be extended additively because
    historical reports remain valid and no existing field meaning changes;
  - unresolved: none.
- ADR status: ADR 0022 accepted; it extends ADR 0016 and is constrained by ADR
  0021.
- Advisory design-review:
  - reviewers: data-trust-source-integrity, backend-api
  - status: completed; the design now separates operations and weather types,
    supports exact component-addressable subsets of broader official status and
    pass sources, and retains independent weather activation
- Advisory feature-review before final handoff:
  - reviewers: data-trust-source-integrity, backend-api
  - status: implementation and clean Data Trust / Backend API feature re-review
    complete; installed repository-skill activation remains pending merge to main

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Mixed | How multi-operator terrain can own one ski-area identity | Controls graph granularity and all weather/operations attribution | Require one operator; explicit coordinated boundary; waive ownership | Explicit coordinated boundary | Preserves auditability without over-splitting | ADR 0022 |
| Product / Domain | Whether minor disconnected lifts may remain components | A literal connectivity rule would create low-value nursery ski areas | Require piste connectivity; allow bounded minor satellites | Allow bounded minor satellites | Safe only with common complete inventory, status, pass, and no independent value | ADR 0022 and domain language |
| Technical | Whether this requires report schema version 4 | A new version would increase report and maintainer migration cost | Additive schema-v3 extension; schema v4 | Additive schema-v3 extension | Existing reports remain valid; new coordinated claims receive stricter validation | This spec |

## Architecture Decisions

The normal ski-area owner gate remains the default. A represented or newly added
ski area passes owner validation through one of two explicit paths:

1. `operational_scope=independent`, using the existing single-owner operations,
   weather, or full-local-pass evidence; or
2. `operational_scope=coordinated`, using the coordinated-area contract below.

For `coordinated`, deterministic validation requires:

- `terrain_scope=complete` and `separation_value=material`;
- `official_complete_lift_inventory`, `coordinated_status_or_schedule`, and
  `common_full_coverage_pass` signals;
- `pass_scope` set to `full_local` or `shared_only`;
- at least two `component_candidate_ids`;
- non-empty `coordination_evidence_refs`, all included in the assessment's normal
  `evidence_refs`;
- exactly one `coordination_evidence_families` item for each typed `family`:
  `complete_terrain_lift_inventory`,
  `exhaustive_component_operator_roster`,
  `component_addressable_operations_status`,
  `every_component_pass_coverage`, and
  `direct_component_parent_assignment`;
- non-empty family `evidence_refs` that resolve only to `source_type=official`
  evidence and are included in the boundary and scope evidence refs;
- family `covered_component_candidate_ids` equal to the parent's exact
  `component_candidate_ids`, with neither omissions nor extras;
- aggregate `coordination_evidence_refs` equal to the union of every family's
  evidence refs;
- every component ID to resolve to a ski-area assessment with
  `disposition=not_separate`, `parent_ski_area_id` set to the coordinated area,
  `operational_scope=coordinated`, and a target ref to that area;
- no duplicate component membership within the report.

Report-wide child closure independently evaluates contradictory source-backed
evidence. A child is viable only after `terrain_scope=complete` and at least one
terrain-identity signal. Owner categories are derived directly from signals:
operations uses `separate_operator` or `independent_status_or_schedule`, weather
uses `independent_weather_presentation`, and pass requires `full_local_pass`
together with `pass_scope=full_local`. Connected children require two categories,
including operations or weather; transfer-required or disconnected children
require one. The child's declared `not_separate`, `redundant`, coordinated or
parent-owned scopes, shared branding, and provider consensus cannot override
those gates. Sector terrain and one connected pass-only category remain valid
component evidence rather than separate-area proof.

The three coordination metadata lists belong only to a `represented` or
`add_entity` parent assessment. A coordinated `not_separate` child retains its
coordinated operational scope and parent target but leaves those lists empty.
Any coordinated scope or metadata requires report schema version 3; schema
versions 1 and 2 cannot make a coordinated claim.

The validator proves report consistency, not internet completeness. Curation and
review must independently reconstruct the official operator/member inventory and
confirm that all material components were included. Boundary adjudication returns
`evidence_insufficient` when the complete roster, operating publication, or pass
scope cannot be established.

No runtime `SkiArea` schema field is required. The coordinated structure is
curation provenance used to justify the durable catalog boundary. A future
runtime requirement for component-level status or hotel-level terrain choice can
revisit `SkiSubArea` without changing this decision retroactively.

Revisit when:

- component-level open-lift or piste availability becomes user-facing;
- coordinated areas routinely contain materially different weather or season
  behavior that one `ski_area_id` cannot represent;
- a reliable provider supplies a canonical operational ownership graph.

## API and Client Contract

- Backend endpoints or response fields: unchanged.
- Web UI states: unchanged.
- Mobile companion states: unchanged.
- Backward compatibility: existing non-coordinated schema-version-3 reports
  remain parseable and retain byte-for-byte Markdown because the additive
  coordination lists default empty and their columns remain conditional. Only
  reports claiming `operational_scope=coordinated` must provide the complete
  typed metadata and official evidence.

## Data Trust and Source Integrity

Required evidence families for a coordinated area:

1. `complete_terrain_lift_inventory`: an official complete map or lift inventory
   defining the bounded terrain;
2. `exhaustive_component_operator_roster`: an official operator/consortium
   roster or equivalent exhaustive component inventory;
3. `component_addressable_operations_status`: an official current lift-status
   or operating-schedule publication in which every selected component is
   exactly addressable;
4. `every_component_pass_coverage`: an official pass covering every selected
   component, even if it also covers a separately modeled adjacent ski area;
5. `direct_component_parent_assignment`: official direct parent-assignment
   evidence for every component. A common official source may own this family
   when it makes every assignment explicit; unresolved assignment fails closed.

The sources may be published by a consortium or common operating portal; a
single hostname is not required. Broader sources must expose exact component
membership or status so the coordinated subset is reproducible. Regional pass
coverage, a member list without common operations, or an area-wide map without
an exhaustive component disposition is insufficient.

For Livigno, the intended later assessment is:

- keep Mottolino-Trepalle separate because it is a complete transfer-required
  area with material operations and weather value;
- assess the 23-lift west side as one coordinated area only if the official
  member roster, complete numbered map, common live operations page, and Livigno
  local pass reconcile all Carosello, Sitas, and smaller west-side components;
- keep each smaller presentation as `not_separate` provenance rather than a
  runtime ski area;
- run the independent weather-geometry gate and backfill handoff for the new ID.

## AI / LLM Use

- Boundary validation, component reconciliation, and required-signal checks are
  deterministic.
- An LLM may assist source discovery and summarize source meaning but cannot
  assert coordination, invent missing components, or waive a required evidence
  family.
- No new prompts, caches, or request-path LLM calls are introduced.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| Later merge of a new active ski-area ID | Existing targeted historical-weather completion and climatology rebuild | Existing weather completion worker | The curation PR must retain the normal post-merge handoff; this policy change does not run it. |

## Security, Privacy, and Abuse

- No user data, secrets, permissions, or privacy-sensitive logging are involved.
- External source URLs remain subject to existing bounded evidence and trust
  rules.

## Observability and Operations

- No production runtime metrics or alerts change.
- Validator errors must name missing signals, unresolved components, duplicate
  membership, or invalid parent targeting directly.
- Maintainer review should converge to a policy-determined result when the
  coordinated evidence packet is complete and remain fail-closed otherwise.

## Acceptance Criteria

- A complete multi-operator area with an official inventory, coordinated current
  status, a common full-coverage pass, reconciled child assessments, and material
  separation passes schema-v3 validation.
- `weather_scope=coordinated` is rejected; coordinated operations and valid
  weather sampling remain separate conclusions.
- A shared pass plus member directory without coordinated current operations
  fails.
- A common map plus status page with an incomplete component inventory fails.
- A regional network pass spanning transfer-separated complete ski areas cannot
  create a coordinated ski area.
- A connected complete child with operations and full-local-pass evidence cannot
  be folded into the coordinated parent, while a connected pass-only child does
  not pass solely on that category.
- A material transfer-required component that passes the ordinary ski-area gates
  cannot be folded into the coordinated parent.
- Minor satellite or nursery lifts can remain `not_separate` when all coordinated
  evidence and no-independent-value conditions pass.
- Existing non-coordinated schema-version-3 reports and their deterministic
  Markdown rendering remain unchanged.
- Curation and review skills use the same coordinated-area definition and
  evidence checklist.
- Livigno can be reviewed as Mottolino-Trepalle plus one coordinated west-side
  ski area without treating legal operator plurality as evidence insufficiency.
- Weather sampling for that west-side area remains independently gated.

## Verification

- Unit tests: `tests/test_catalog_curation.py` for model and deterministic
  boundary validation.
- Reconciliation tests: `tests/test_catalog_curation_reconciliation.py` for
  coordinated component and parent-target deltas.
- Rendering tests: deterministic Markdown includes coordinated ownership and
  component IDs.
- Skill checks: paired Livigno positive case and regional-pass negative case in
  curation/review guidance.
- Regression: existing catalog validation and focused catalog suites remain
  green.

## Advisory Review

- Design reviewers: Data Trust & Source Integrity; Backend / API.
- Design-review result: completed with no remaining Blocker or High findings.
  Review corrections separated the operations/weather type aliases, allowed
  exact component-addressable subsets of broader official publications, and
  distinguished complete component pass coverage from an exclusive local pass.
- Feature reviewers: Data Trust & Source Integrity; Backend / API.
- Feature re-review: completed clean at exact HEAD
  `e6c3b69f5639d5405ecdcedf53dcc5a4107d7bcb`; Data Trust & Source Integrity
  found no findings and confirmed the Blocker resolved, while Backend / API
  found no Blocker, High, Medium, or Low findings and confirmed both High
  findings resolved. Both reviewers marked the feature merge-ready.
- Feature-review corrections: official evidence is typed across all five
  required families with exact component coverage; schema-v3 enforcement and
  parent-only metadata enforcement are explicit. A follow-up High review
  correction makes report-wide child closure derive ordinary owner categories
  directly from source-backed signals, preventing coordinated declarations from
  hiding an independently viable complete component while preserving sector and
  connected pass-only cases.
- Known residual risk: deterministic validation can enforce a complete declared
  inventory but cannot discover an operator omitted from the source packet;
  independent review remains necessary.
