# Feature Spec: Ski-Area Trip-Consequence Boundaries

## Status

- Status: accepted
- Owner: solo-builder
- Related docs:
  - `docs/domain-language.md`
  - `docs/data-trust-model.md`
  - `docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md`
  - `docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md`
- Related plan:
  - `docs/superpowers/plans/2026-09-01-ski-area-trip-consequence-boundaries.md`
- Related ADR:
  - `docs/architecture/adr/0023-require-trip-level-consequences-for-ski-area-boundaries.md`

## User Outcome

Snowcast models ski areas at a level that changes a real trip choice. Operator
names, maps, status pages, town boundaries, or transfer labels cannot split a
normal skier-facing area unless the split materially changes pass value,
stay-to-terrain access, durable conditions or season suitability, or terrain fit.

## Scope

In scope:

- make material trip-level recommendation value a typed ski-area boundary gate;
- preserve independent and coordinated evidence ownership as a separate gate;
- keep historical report schemas 1-3 parseable;
- require schema version 4 for newly finalized maintainer curation reports;
- align deterministic validation, Markdown rendering, maintainer intent,
  curation/review skills, and model documentation.

Out of scope:

- changing the runtime catalog graph in this change;
- migrating Livigno or any other destination;
- introducing `SkiSubArea` or runtime operator/component entities;
- changing search scoring or result grouping;
- moving or rebuilding historical weather evidence.

## Product Fit

- Ski-area IDs continue to own weather and operational evidence.
- Ski-region grouping continues to prevent one trip market from occupying
  several result slots.
- Pass products continue to represent access across non-connected ski areas.
- Unresolved materiality stays explicit instead of being guessed from provider
  structure.

## Domain Model

- Bounded contexts touched: static catalog curation and maintainer validation.
- Changed term: `material separation value` is supported by typed
  `material_trip_consequences`.
- New runtime entities: none.
- New report contract field: `material_trip_consequences`, containing typed
  records with `consequence_type`, `decision_effect`, `comparison_basis`,
  `comparison_target_id`, `evidence_refs`, and a concise rationale comparing
  the candidate with its parent ski area, sibling ski area, or stay-market
  baseline.

Allowed consequence types are:

1. `pass_price_or_coverage`: a real local product changes price or accessible
   terrain for the candidate;
2. `stay_access_or_transfer`: choosing a stay base or switching terrain changes
   practical ski-day access, and the candidate is a primary selectable ski day
   rather than an excursion or internal sector;
3. `weather_or_season`: source-backed elevation, exposure, season, or weather
   behavior can materially change trip suitability;
4. `terrain_character_or_skill_fit`: substantial terrain characteristics can
   materially change suitability for a user or party.

Every consequence must identify one affected decision:

- `selected_ski_area`;
- `stay_to_ski_configuration`;
- `lift_pass_choice`;
- `conditions_evidence_profile`.

It must also identify one comparison basis: `parent_ski_area`,
`sibling_ski_area`, or `stay_market_baseline`.
Several records may share a consequence type when they represent different
decision effects, comparisons, evidence, or rationales; exact duplicates are
invalid.

The common materiality test applies to every consequence category: compared
with the nearest parent or sibling, the candidate must be a substantial primary
ski-day option and the durable difference must plausibly change one of those
normal-trip decisions. A same-day route preference, ordinary intra-area
variation, novelty or individual-lift ticket, temporary closure, one forecast,
or isolated incident is insufficient.

Every consequence declares `comparison_basis=parent_ski_area`,
`sibling_ski_area`, or `stay_market_baseline`. A destination's sole root
downhill area uses the stay-market baseline; a parentless area that competes
with another ski area uses the sibling basis. `comparison_target_id` names the
actual catalog entity ID resolved through typed assessment `target_refs`, never
a report-local candidate alias: the declared parent, another represented or
added ski area with the same parent, or a represented or added stay destination.
One stay destination can have only one stay-market-baseline root, and that root
cannot also participate in a sibling comparison.

Invariants:

- a separate ski area still requires complete terrain and independent or
  coordinated evidence ownership;
- schema-v4 `represented` and `add_entity` partition candidates require at
  least one typed material consequence with claim-specific evidence;
- materiality is assessed independently for every ski-area candidate;
- every comparison resolves to one concrete assessed entity rather than an
  uncheckable category or prose-only claim;
- a `not_separate` child may record a material consequence when it fails the
  complete-terrain or evidence-owner gate;
- connectivity, operator identity, provider consensus, a dedicated map, a
  status page, a stay-destination boundary, and a shared pass are supporting
  signals only;
- `stay_access_or_transfer` requires a primary selectable ski-day relationship,
  not merely a shuttle, excursion, connector, or map distance;
- coordinated-child closure evaluates all three ordinary gates, so independent
  owner evidence without material trip value does not force a child split;
- schema-v4 coordinated parents may use explicit component assignment or a
  reproducible derivation from the complete official terrain topology, exact
  roster, and addressable operations view; pass, branding, or proximity alone
  remains insufficient;
- aggregate pass terrain stays on the pass and is not copied to child ski areas.
- `external_pass_context` is invalid for a concrete ski-area candidate; use a
  typed deferred or unresolved boundary instead;
- `not_separate` requires resolved parent connectivity; unknown connectivity is
  not evidence for folding.

## Decision and Review Gate

- Classification: review-gated
- High-risk domains touched: catalog correctness, evidence trust, weather-owner
  boundaries, maintainer publication contract
- Developer Decision Checkpoints:
  - resolved: use complete terrain + evidence ownership + material trip-level
    consequence;
  - resolved: operator/site/map/transfer/stay-market signals are not sufficient
    independently;
  - resolved: use a generic rule and do not add a ski-sub-area layer;
  - accepted implementation: schema version 4 preserves historical reports
    while enforcing the rule for new maintainer output;
  - unresolved: none.
- ADR status: accepted ADR 0023 added by this change
- Advisory design-review:
  - reviewers: product-strategy, backend-api, data-trust-source-integrity
  - status: completed; claim-scoped evidence, independent materiality,
    durability, strict schema inheritance, lifecycle, and calibration findings
    incorporated
- Advisory feature-review before final handoff:
  - reviewers: backend-api, data-trust-source-integrity
  - status: completed; external-context bypass, schema cutover, stale
    operator-first wording, root comparison, unknown connectivity, and
    consequence multiplicity findings incorporated

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Product / Domain | What makes a ski-area split useful? | Ski-area IDs drive weather, ranking, and user-facing terrain choices. | Operator-first is reproducible but over-splits; marketing-first is familiar but hides real differences; trip-consequence gate preserves both evidence and user value. | Trip-consequence gate. | Existing catalog mostly follows this model; Livigno can become Mottolino plus coordinated Livigno West without splitting Sitas/Carosello. | ADR 0023 |
| Technical | How should enforcement coexist with historical reports? | Tightening schema 3 in place would invalidate reviewed evidence packets. | Rewrite all historical reports; accept an unenforced optional field; or introduce schema 4. | Schema 4. | Versioning is the narrowest enforceable compatibility boundary. | Maintainer runtime contract |

## Architecture Decisions

- Durable decision: evidence ownership establishes where facts can attach;
  material trip consequences establish whether another ski-area identity is
  useful.
- Existing constraints: ADRs 0008, 0016, 0021, and 0022 remain in force.
- Revisit when: Snowcast introduces runtime ski sub-areas or reliable
  piste-level operating and weather products.

## API and Client Contract

- Public API and clients: unchanged.
- Catalog schema: unchanged.
- Curation report schema: version 4 adds typed ski-area trip consequences.
- Historical report schemas 1-3 remain accepted outside maintainer finalization.

## Data Trust and Source Integrity

- Every material consequence record must cite verification-capable evidence
  included in both the boundary and scope evidence sets, and every cited item
  must include the assessed candidate in `boundary_target_ids`.
- Comparison targets are graph-validated: parent targets must equal the
  declared parent and differ from the subject; sibling targets must be other
  represented or added ski areas with the same parent; stay-market targets must
  be represented or added stay destinations with one sole root area. Resolution
  uses a unique typed target reference rather than `candidate_id`.
- Evidence must support the claimed user consequence, not only the operator or
  provider identity.
- Conflicting or incomplete consequence evidence produces an unresolved
  boundary rather than an owner-choice substitute.

## AI / LLM Use

- Deterministic Pydantic and report validators own the structural contract.
- Codex may research and summarize evidence but cannot bypass the typed gate.
- No runtime LLM behavior changes.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| N/A | N/A | N/A | Runtime graph and weather IDs do not change in this contract-only change. |

## Security, Privacy, and Abuse

- No user or sensitive data is involved.

## Observability and Operations

- Invalid schema-v4 reports fail with candidate-scoped deterministic messages.
- Existing maintainer generation/recovery behavior remains unchanged.

Compatibility lifecycle:

| Stage | Accepted report versions | Authority |
| --- | --- | --- |
| Historical load and deterministic render | 1-4 | Historical only |
| Preparation input | 1-3 | Untrusted input to normalize |
| New proposal or remediation output | 4 | Requires semantic review |
| Reviewed intent, reconciliation, and finalization | 4 | Current publication authority |

Schema version 4 preserves every schema-version-3 structural and trust
invariant while replacing its literal direct-assignment family with the current
generic component-assignment family. Normalizing an in-flight schema-v3
generation to version 4 is a semantic change and cannot reuse earlier reviewed
authority.

## Acceptance Criteria

- schema-v4 separate ski areas require at least one typed material consequence;
- schema-v4 root areas use a stay-market comparison, while parentless competing
  areas use a sibling comparison;
- each consequence's evidence is non-empty, known, verification-capable,
  included in both boundary and scope evidence, and candidate-scoped through
  `boundary_target_ids`;
- schema-v4 `not_separate` children may retain material consequences when
  another ordinary gate fails;
- a coordinated child with owner evidence but no material consequence remains
  valid inside its coordinated parent;
- a coordinated child with all three gates is rejected as independently viable;
- schema-v4 uses `component_parent_assignment`, while schema-v3 retains its
  historical `direct_component_parent_assignment`; derived assignment requires
  unique candidate-specific official terrain placement and documented
  normalization;
- schema-v3 reports retain their existing behavior and deterministic Markdown;
- maintainer finalization requires schema version 4;
- installed curation and review skills state the same generic rule.

Disposition consistency:

| Disposition | Separation value | Consequences |
| --- | --- | --- |
| `represented`, `add_entity` | `material` | at least one with an explicit comparison basis |
| `not_separate` | `redundant` or `material` | empty when redundant; at least one when material; at least one other gate must fail when material |
| `deferred`, `unresolved` | `unresolved` | may retain already verified consequences without implying a final boundary |

Calibration examples are non-normative and never become resort-specific
validator branches:

| Expected result | Examples | Why |
| --- | --- | --- |
| Fold internal sectors | KitzSki, Mayrhofen, Val Gardena, Verbier sector, Sitas and Carosello inside Livigno West | Named sectors or operators do not by themselves change a normal trip configuration. |
| Separate primary ski-day choices inside one trip market | Mottolino and Livigno West; Chamonix's independently selectable mountains | Substantial terrain plus evidence ownership and durable access, conditions, pass, or terrain-fit consequences can change the selected ski area while regional grouping prevents duplicate result slots. |

## Verification

- 319 focused catalog-curation, reconciliation, maintainer-intent, and
  maintainer-validation tests passed, including schema inheritance, child
  closure, comparison-target graph validation, and Markdown rendering;
- 161 maintainer git-operations tests passed;
- the broader catalog/maintainer wildcard run passed 1,455 tests; 76 setup
  errors were limited to the unavailable local PostgreSQL fixture;
- catalog and trust validation passed with the checked-in 28 regions, 47 stay
  destinations, 44 ski areas, and 384 trust entries;
- Ruff and `git diff --check` passed;
- backend/API and data-trust feature review completed.

## Advisory Review

- Design reviewers: product-strategy, backend-api, and
  data-trust-source-integrity completed review before implementation.
- Incorporated findings: claim-scoped consequence records, a common primary
  ski-day materiality threshold, durable evidence bases, independent three-gate
  truth table, strict schema-v4 inheritance, maintainer lifecycle, and
  non-normative calibration examples.
- Feature reviewers: backend-api and data-trust-source-integrity completed the
  implementation review. Findings about external pass context, schema cutover,
  comparison-target closure, unknown connectivity, and exact duplicate records
  were incorporated.
- Known residual risk: semantic truth still requires reviewer judgment that a
  cited source supports a material user consequence.
