# Feature Spec: Lift-Pass Validity Windows

## Status

- Status: accepted design; implementation not started
- Owner: solo-builder
- Related docs:
  - `docs/domain-language.md`
  - `docs/data-trust-model.md`
  - `docs/planning-model.md`
  - `docs/search-ranking-model.md`
- Related plan:
  `docs/superpowers/plans/2026-07-21-lift-pass-validity-windows.md`
- Related ADRs:
  - `docs/architecture/adr/0005-catalog-scope-model.md`
  - `docs/architecture/adr/0019-separate-pass-validity-from-ski-area-operation.md`

## User Outcome

Snowcast must recommend a lift-pass product only when the product is applicable
to the requested trip dates and the selected ski area is expected to operate.
It must keep a useful future-season recommendation when the next tariff has not
yet been published, while clearly avoiding a false claim that exact pass dates
are confirmed.

## Problem

`SkiArea` already owns machine-readable operating-season windows, but
`LiftPassProduct` has no machine-readable validity window. Pass coverage is
therefore unconditional in the catalog graph and Search V4 candidate expansion.
Dates embedded in a price `season_label` or `external_validity_summary` are
display text and cannot safely control eligibility.

The Zillertaler products expose the distinction:

- Mayrhofen's published operating window and the Zillertaler Superskipass
  window happen to align for winter 2026/27.
- Hintertux operates for a longer period, while valley-wide Superskipass
  coverage applies only during the main winter window.

Ski-area operation and ticket entitlement therefore need separate owners even
when their dates coincide.

Reviewed primary examples:

- Mayrhofen winter operation and Zillertaler Superskipass tariff:
  <https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter>
- Hintertux local and wider Zillertal validity periods:
  <https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/>

## Scope

In scope:

- optional machine-readable validity windows on lift-pass products;
- deterministic date applicability during candidate generation and selection;
- intersection with ski-area operating-season evidence;
- cautious future-season fallback when a previously dated pass has no window
  for the requested season yet;
- catalog, persistence, trust, curation-report, validation, API-summary, and
  focused-test updates required by the new field;
- migration of source-backed seasonal products such as the Zillertaler
  Superskipass into products whose static coverage is true throughout each
  product's modeled validity windows.

Out of scope:

- live lift-status or temporary closure handling;
- per-lift operating calendars;
- arbitrary date windows on individual pass-to-ski-area edges;
- dynamic recalculation of pass terrain from whichever component areas happen
  to be operating;
- inferring a future tariff by repeating the previous year's dates;
- acquisition of exact pass windows for every existing catalog product;
- ranking-weight changes.

## Domain Model

`SkiArea.season_windows` remains the canonical owner of planned or estimated
terrain operation. `LiftPassProduct.validity_windows` becomes the canonical
owner of a separately published ticket-entitlement window.

The product field reuses the existing typed catalog season-window shape:

```text
LiftPassProduct
  validity_windows: zero or more {season_label, start_date, end_date, status}
```

The field is optional and defaults to an empty tuple for backward compatibility.
An empty value means **no additional modeled pass-date restriction**. It does
not copy ski-area dates into the pass and does not claim that the product is
valid indefinitely.

Window dates become authoritative for exclusion or confirmation only when the
owning pass trust group is source-backed and the window status is `planned`.
An `estimated` window may preserve reviewed context, but it cannot confirm exact
ticket entitlement or exclude a candidate; runtime treats it as unverified.

When one requested season contains mixed window evidence, use cautious
precedence:

1. A source-backed `planned` window containing the complete trip confirms it.
2. Otherwise, if any same-season window is estimated or its owning trust is not
   source-backed, keep the result unverified; that evidence may cover dates the
   authoritative windows do not.
3. Exclude only when at least one same-season window is authoritative and every
   same-season window is authoritative enough to rule out complete-trip
   containment.
4. With no same-season window, use the existing future-season unverified
   fallback.

A pass product keeps static `valid_ski_area_ids` and `terrain_domain_ids`.
When the same publisher-facing ticket has materially different coverage in
different date regimes, Snowcast models separate product variants whose static
coverage is accurate throughout their respective validity windows. The initial
implementation does not add date windows to individual coverage edges.

Examples:

- `zillertaler-superskipass`: one main-winter validity window; modeled
  Mayrhofen and Hintertux coverage.
- local Hintertux multi-day variant: local Hintertux coverage; one window before
  and one window after the regional main-winter window.
- ordinary local pass without separately published dates: no pass validity
  window; applicability is limited by the selected ski area's operation.

For a requested trip, runtime derives rather than stores:

```text
contract_covered_ski_area_ids
operating_covered_ski_area_ids
unavailable_covered_ski_area_ids
unverified_covered_ski_area_ids
coverage_status = full | partial | unverified
```

The contract set remains the catalog truth. The operating and unavailable sets
are date-specific projections of that truth through source-backed ski-area
season evidence. The unverified set preserves covered areas whose operation
cannot be confirmed for the requested season, including areas whose season
trust is `estimated` or `needs_source`.

## Applicability Rules

For an exact-date trip, a pass/area configuration is applicable only when:

```text
ski_area_applicable
AND
pass_applicable
```

Where:

```text
ski_area_applicable =
  the complete trip is inside a source-backed ski-area operating window,
  or the existing cautious unknown-season fallback applies

pass_applicable =
  the pass has no validity windows,
  or the complete trip is inside a source-backed planned validity window for
  the requested season,
  or the future-season fallback applies
```

Partial overlap is not enough: a pass window must cover the complete requested
trip. Month-only searches continue using the existing cautious seasonal
behavior; they must not manufacture exact pass dates.

### Partial Coverage

One closed covered ski area does not invalidate the pass for every other
covered area. Generate and retain candidates only for covered ski areas that
are season-applicable to the requested trip. Exclude a candidate focused on a
known closed area. If every covered area is known unavailable, no candidate for
that pass remains. Areas with insufficient season evidence remain eligible only
through the explicit unverified fallback; they are never counted as operating.

When only part of the pass network is operating:

- expose both operating and unavailable covered area IDs;
- expose unverified covered areas separately rather than treating them as open;
- set `coverage_status=partial` when at least one area is known unavailable and
  another covered candidate remains; use `unverified` when complete effective
  coverage cannot otherwise be confirmed;
- preserve the official full-network terrain figure only as contextual catalog
  information;
- label that figure as published full-network coverage, warn that practical
  terrain is lower, and state that Snowcast has not recalculated it;
- do not use the unadjusted aggregate for terrain-scale ranking or pass-terrain
  value scoring;
- prefer a source-backed metric for the selected operating ski area or another
  wholly operating terrain scope; otherwise treat the date-adjusted terrain
  value as unavailable and neutral.

The initial implementation must not sum component ski-area values. Such a sum
is reliable only when every component and its season state are known, the
metrics use compatible scopes, and no terrain overlaps or is double-counted.

### Future-Season Fallback

If a pass has explicit windows but none belongs to the requested future season,
Snowcast retains the candidate when the ski area remains season-applicable. The
pass validity outcome is `unverified_for_requested_season`, and public copy must
say that exact pass dates are not yet confirmed.

Derive the requested season year with the existing ski-area season-year rule:
use the selected ski area's `season_start_month` and the trip date, never a
free-text pass or price `season_label`. Classify each pass window by applying
that same rule to its `start_date`; do not compare the raw start year. This keeps
cross-calendar winter seasons deterministic and correctly associates a
post-main-winter window such as April-May 2027 with Hintertux's 2026/27 season.

If every requested-season window is authoritative and the trip falls outside
all of them, the pass is inapplicable. Snowcast must not fall back merely because
the exact window is inconvenient. A same-season estimated or untrusted window
keeps the result unverified unless another authoritative window contains the
complete trip.

Snowcast never projects the previous season's calendar dates into the future.

For a month-only search without a concrete year, pass windows do not create an
exact-date exclusion. The existing month-level ski-area season behavior remains
the practical gate, and the pass summary may present a known seasonal context
without claiming confirmed applicability for an unspecified year.

## Product And API Behavior

- Date-aware candidate generation must not create a configuration for a pass
  known to be invalid for the requested trip.
- A pass with no additional validity restriction remains usable only while its
  selected ski area is season-applicable.
- A future-season fallback may remain eligible but must expose an uncertainty
  marker in the pass summary and explanation inputs. The public warning is
  required when pass validity is unverified even if all covered ski areas have
  confirmed operation.
- Pass-date and ski-area-operation uncertainty use separate public warnings. An
  unverified pass alone says only that exact pass dates are unconfirmed; it must
  not cast doubt on confirmed area operation. Unverified area operation uses its
  own warning. Emit both in deterministic order only when both conditions apply.
- A partially operating pass must expose its contract, operating, and
  unavailable area sets plus a coverage warning; season-unknown covered areas
  must remain explicitly unverified.
- A published full-network terrain metric may remain visible under partial
  coverage, but must be marked non-date-adjusted and excluded from ranking and
  value scoring.
- A known out-of-window pass is excluded rather than merely down-ranked.
- Existing clients remain compatible: the catalog field is additive and API
  uncertainty fields must use optional/default-safe additions.
- Product applicability and price validity stay distinct. A pass window does
  not prove that a stored price applies to the requested season; price matching
  continues to use its own reviewed slice and uncertainty behavior.

## Data Trust And Curation

- Exact pass dates require direct operator, tariff, or official regional-pass
  evidence.
- Pass validity evidence belongs to the existing lift-pass
  `identity_scope_availability` trust group; coverage evidence remains in the
  `coverage` group.
- Empty validity windows are not a verified assertion of year-round validity.
  Curation reports must distinguish `no separate window modeled` from
  `explicit window verified`.
- Schema-v3 curation reports and their resulting graph must include new or
  changed pass validity windows when they are material to the proposal.
- This additive field does not require a catalog schema-version bump or a new
  curation report schema. Existing catalog schema v2 and report schema v3 gain
  the field through their normal typed change and reconciliation paths.
- Conflicting official dates remain visible as a trust caveat; deterministic
  code must not average or invent a window.
- `estimated` pass windows and non-source-backed pass or ski-area trust states
  remain unverified at runtime; they cannot create a confirmed applicability
  claim or an authoritative exclusion.

## Persistence And Migration

- Add pass validity-window storage through the existing catalog snapshot and
  normalized repository/sync paths.
- Existing products migrate with an empty tuple and preserve current behavior
  except that ski-area operation becomes an explicit applicability gate.
- Curated products with source-backed dates receive explicit windows.
- Product splitting is required only when one static coverage set cannot remain
  true throughout the modeled window. IDs must remain stable once accepted.

## AI / LLM Use

- Applicability, window containment, season matching, and fallback selection
  are deterministic.
- Catalog discovery or curation may use Codex to interpret official tariff
  language and propose product boundaries, subject to the existing source,
  report, review, and owner gates.
- No request-path LLM call is introduced.

## Decision And Review Gate

- Classification: review-gated
- High-risk domains: catalog correctness, planning eligibility, source trust,
  persistence, and shared Search V4 behavior
- Developer Decision Checkpoints:
  - resolved: keep pass validity separate from ski-area operation;
  - resolved: absent pass windows impose no additional date constraint;
  - resolved: future seasons without a newly published pass window remain
    eligible with explicit unverified-date wording;
  - resolved: partial coverage retains operating-area candidates, displays a
    warning, and does not recalculate or rank on the full-network aggregate;
  - unresolved: none.
- ADR status: ADR 0019 accepted with this design
- Advisory design-review: `backend-api` and
  `data-trust-source-integrity`, completed after documentation corrections; no
  unresolved Blocker, High, or material Medium findings
- Advisory feature-review: `backend-api` and
  `data-trust-source-integrity`, required before implementation handoff

## Alternatives Considered

1. **Inherit pass dates from ski-area operation.** Smaller, but conflates lift
   operation with ticket entitlement and fails when a long-season area accepts
   a regional product only during a shorter window.
2. **Separate pass validity and intersect it with operation.** Selected. It
   preserves ownership, supports ordinary undated passes, and keeps the runtime
   rule deterministic.
3. **Date every pass-to-area coverage edge.** Most expressive, but adds schema,
   persistence, curation, and explanation complexity that current product use
   does not justify.
4. **Exclude a previously dated pass until next season's tariff is published.**
   Source-conservative but too destructive for forward planning.
5. **Repeat last year's dates.** Convenient but presents inference as tariff
   truth and is rejected.

## Verification And Acceptance Criteria

Before implementation, tests should cover:

- undated pass plus in-season area is applicable;
- undated pass plus out-of-season area is not applicable;
- dated pass plus in-window area is applicable;
- dated pass outside its known requested-season window is not applicable;
- pass in-window plus area out-of-season is not applicable;
- complete-trip containment is required for both windows;
- a future season with no matching pass window remains eligible and reports
  unverified pass dates;
- a post-main-winter pass window is associated with the selected ski area's
  cross-calendar season by applying the season-year rule to both trip and window;
- estimated or non-source-backed pass windows never confirm or exclude;
- a trusted planned same-season miss plus an estimated or untrusted same-season
  window remains unverified, while a trusted planned containing window confirms;
- non-source-backed ski-area season evidence remains eligible and explicitly
  unverified rather than being treated as operating or unavailable;
- a previous season's exact dates are never presented as future dates;
- one closed covered area produces partial coverage without excluding candidates
  for other operating covered areas;
- a candidate focused on a closed covered area is excluded;
- all covered areas closed produces no candidate for that pass;
- partial coverage exposes the unavailable area and warning while retaining the
  published full-network figure only as non-date-adjusted context;
- partial coverage prevents the full-network aggregate from influencing
  terrain-scale and pass-terrain-value scoring;
- selected-area terrain may be used when source-backed and not known closed;
  an unverified operating season must remain visible in the explanation;
- pass-date-only uncertainty and area-operation-only uncertainty produce their
  respective warning, while combined uncertainty produces both in stable order;
- catalog round-trip persistence preserves zero, one, and multiple validity
  windows;
- trust and schema-v3 curation validation bind changed windows to direct source
  evidence at the reconciled root `validity_windows` field path;
- Search V4 candidate, constraint, pass-summary, and explanation outputs remain
  deterministic and backward-compatible.

Focused implementation verification must include catalog model/repository/sync
tests, planning and Search V4 tests, schema-v3 curation validation, diff checks,
and advisory feature review.

## Revisit Criteria

Revisit relationship-level coverage windows only when a materially used ticket
cannot be represented as stable product variants without confusing identity,
pricing, or user-facing selection. Revisit date-adjusted terrain calculation
only when complete, compatible, non-overlapping component metrics and operating
states can make the result reproducible.
