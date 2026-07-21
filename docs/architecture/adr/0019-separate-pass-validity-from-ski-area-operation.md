# ADR 0019: Separate Pass Validity From Ski-Area Operation

Status: accepted
Date: 2026-07-21

Supersedes: N/A

Superseded by: N/A

Related ADRs:
- `docs/architecture/adr/0005-catalog-scope-model.md`
- `docs/architecture/adr/0009-normalized-trip-market-catalog.md`
- `docs/architecture/adr/0010-use-typed-source-aware-catalog-facts.md`

Related docs:
- `docs/domain-language.md`
- `docs/planning-model.md`
- `docs/search-ranking-model.md`
- `docs/superpowers/specs/2026-07-21-lift-pass-validity-windows-design.md`

## Context

ADR 0005 made named lift-pass products explicit catalog entities but deferred
machine-readable pass-validity dates until production behavior needed them.
Search now consumes pass products, while the model still treats
`valid_ski_area_ids` and `terrain_domain_ids` as unconditional.

Ski-area operation and pass entitlement can overlap without being the same
fact. Mayrhofen's main winter operation and the Zillertaler Superskipass window
align in the reviewed 2026/27 sources. Hintertux operates for longer, while
valley-wide Superskipass entitlement applies only during the shorter main
winter window. Inheriting pass dates from ski areas would therefore assert
ticket coverage that the source does not grant.

Forward planning creates a second tension: a known current-season tariff may
expire before the operator publishes the next season's exact dates. Excluding
the pass entirely would turn missing future evidence into a false negative;
copying last year's dates would turn an estimate into a false fact.

The reviewed primary examples are the official Mayrhofen winter operation and
tariff page
<https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter>
and the official Hintertux local/regional validity tariff
<https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/>.

## Decision

Keep the two date concepts independently owned:

- `SkiArea.season_windows` owns planned or estimated terrain operation.
- optional `LiftPassProduct.validity_windows` owns separately published ticket
  entitlement.

Effective pass usability is the deterministic intersection of pass
applicability and ski-area applicability. A known out-of-window result is
ineligible. A missing pass window imposes no additional date constraint; the
ski-area season still applies and no independent pass-date guarantee is made.

When a product has explicit windows but none for the requested future season,
retain the otherwise season-applicable candidate with pass validity marked
unverified for that season. Do not reuse or shift the previous season's dates.
When an authoritative explicit window exists for the requested season, require
the complete trip to fit inside it.

Use the selected ski area's existing season-year calculation to associate an
exact trip and pass window. Apply the same calculation to both the trip start
and each pass window start; comparing a pass window's raw start year would
misclassify post-main-winter windows in a cross-calendar season. Do not parse
free-text season labels. A month-only request with no concrete year keeps the
existing cautious month-level ski-area gate and does not claim exact pass-window
applicability.

Preserve the existing trust boundary when deriving applicability. Ski-area
operation can be confirmed or declared unavailable only from source-backed
season evidence. Pass windows can confirm or exclude only when the pass's
`identity_scope_availability` evidence is source-backed and the window status is
`planned`. Estimated or non-source-backed evidence remains eligible only as
unverified and must not become a confirmed public claim.

For mixed evidence in one season, a trusted planned window containing the trip
may confirm it. If none contains the trip and any same-season window is
estimated or untrusted, keep the result unverified. Exclude only when the
same-season evidence is wholly authoritative and rules out complete-trip
containment. This precedence prevents one authoritative miss from overriding a
second window that is not authoritative enough to confirm or deny entitlement.

Keep pass-date uncertainty separate from area-operation uncertainty in public
copy. Emit a pass-date warning when only ticket dates are unverified, an area
operation warning when only operating evidence is unverified, and both in a
stable order when both conditions apply.

Keep pass coverage static within each modeled product. If the publisher-facing
ticket has materially different coverage in different date regimes, model
separate product variants with stable coverage and appropriate validity
windows. Do not add date windows to individual pass-to-area edges yet.

For each trip, derive the operating subset of the pass's static contract
coverage from the covered ski areas' season evidence. A closed covered area
invalidates only candidates focused on that area, not the pass for other
operating areas. Expose partial coverage and unavailable areas explicitly.
Keep season-unknown covered areas separate and mark effective coverage
unverified rather than treating missing evidence as confirmed operation.

Under partial coverage, retain an official full-network terrain figure only as
labeled contextual information with a warning that practical terrain is lower
and has not been recalculated. Do not use the unadjusted aggregate for ranking
or pass-value scoring. Prefer source-backed terrain for the selected operating
area or another wholly operating scope; otherwise leave the date-adjusted value
unavailable. Do not dynamically sum component areas until Snowcast can prove
complete membership, compatible metric scopes, no overlap, and applicable
operating state.

## Consequences

- Ticket entitlement is not inferred from lift operation.
- Common local passes can omit separate validity dates without duplicating ski-
  area season data.
- Seasonal regional products can be excluded accurately for known dates.
- Future-season planning remains useful while uncertainty stays visible.
- Existing catalog trust statuses continue to control whether exact season and
  pass dates are authoritative; deterministic containment alone does not upgrade
  estimated or source-needed evidence.
- Catalog, persistence, trust, curation, Search V4, and API-summary paths must
  carry and enforce the new optional windows.
- The additive, defaulted field does not by itself require a catalog version or
  curation-report schema-version increment.
- Some publisher-facing tickets may appear as multiple internal product
  variants when their usable coverage materially changes by date.
- A pass can remain usable with `partial` coverage while closed covered areas
  are removed from trip-specific candidates.
- Full-network terrain can remain visible as published context, but partial
  operation prevents it from influencing ranking or pass-value calculations.
- Live closures remain a separate operational concern and do not rewrite either
  canonical window.

## Alternatives Considered

- **Inherit from every covered ski area.** Rejected because operation does not
  establish ticket entitlement and covered areas may have different seasons.
- **Treat missing dates as unavailable.** Rejected because it suppresses useful
  forward planning and makes absence of future tariffs look like known
  ineligibility.
- **Infer future windows from the latest season.** Rejected because calendar
  boundaries can change and Snowcast must not present inferred dates as an
  official tariff.
- **Add validity windows to every pass-to-area edge.** Deferred because product
  variants cover the current use cases with a smaller and clearer contract.
- **Invalidate the whole pass when one covered area is closed.** Rejected
  because entitlement and useful coverage remain for other operating areas.
- **Recalculate partial terrain by summing open areas.** Deferred because
  independently sourced figures may use incompatible scopes or overlap.
- **Keep dates only in labels and curation notes.** Rejected because runtime
  eligibility cannot safely depend on prose parsing.

## Revisit When

- A materially used pass cannot be represented by stable product variants
  without confusing identity or price selection.
- A provider supplies structured per-area entitlement calendars.
- Complete, compatible, non-overlapping component terrain metrics make
  date-adjusted pass terrain reproducible.
- Live operational status becomes part of exact-trip eligibility and needs an
  explicit relationship to planned season and pass entitlement.
