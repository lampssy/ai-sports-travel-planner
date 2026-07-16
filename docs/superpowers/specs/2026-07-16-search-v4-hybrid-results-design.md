# Feature Spec: Search V4 Web Experience

## Status

- Status: accepted by owner; implementation plan prepared
- Owner: solo-builder
- Accepted visual pack:
  `docs/ui-concepts/2026-07-16-search-v4-web-experience/`
- Interactive visuals:
  - homepage:
    <https://p.superdesign.dev/draft/0db8c1de-23d7-496a-9a00-9b55b1d58a31>
  - results:
    <https://p.superdesign.dev/draft/fd59ea10-da9e-4260-a72a-e75dbe5d4e2e>
  - dossier:
    <https://p.superdesign.dev/draft/6338f0ff-0694-49f3-9abc-57a782d7b50a>
- Related product UI spec:
  `docs/superpowers/specs/2026-05-08-web-ui-ux-redesign-design.md`
- Related Search V4 spec:
  `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`
- Related model docs: `docs/search-ranking-model.md`,
  `docs/planning-model.md`, `docs/domain-language.md`
- Related plan:
  `docs/superpowers/plans/2026-07-16-search-v4-web-experience.md`
- Related ADRs:
  `docs/architecture/adr/0012-versioned-search-factor-registry-and-ranking-policy.md`

This spec consolidates the accepted homepage, results board, and recommendation
dossier into one Search V4 web experience. It supersedes the homepage,
post-search, and selected-resort guidance in the May 2026 UI/UX redesign where
the two documents differ. The May spec still governs the current-trip
experience, public resort guide, and general accommodation principles.

## User Outcome

From the first viewport through deep recommendation evidence, a skier can state
a trip intent, see the structured request Snowcast understood, compare complete
trip configurations, refine only decisions that can materially change the
ranking, and inspect the leading destination without losing search context.

The full flow must let the user answer:

- What does Snowcast produce from a natural-language trip brief?
- Why does this ski region lead?
- Which stay base and pass make up the recommended trip configuration?
- What are the practical scale, cost, and access metrics?
- Is the snow conclusion based on climatology, a forecast, or both?
- What snow-depth, snowfall, and temperature evidence supports it?
- How would a refinement change the leading recommendations?
- What additional configurations exist inside the same ski region?
- Can I inspect another result without reconstructing or losing the search?
- What accommodation handoff is available, and is it an estimate or live
  provider inventory?

## Scope

In scope:

- initial homepage command stage and search-to-results transition;
- Search V4 post-search command header;
- interpreted search context and manual-adjustment entry point;
- contextual refinement selection, impact preview, apply, and rerank feedback;
- grouped ski-region recommendation cards;
- deterministic `Trip essentials` selection and presentation;
- independent expansion of multiple recommendation groups;
- dedicated dossier hierarchy, collapsible desktop results navigator, compact
  mobile result switcher, and return-to-results behavior;
- conditional month-only climatology and exact-date forecast-assisted snow
  evidence presentation;
- selected stay-base estimate and provider-agnostic accommodation handoff;
- Search V4 visual system across homepage, results, and dossier, including
  responsive, loading, empty, missing-data, and accessibility states;
- the minimum structured refinement-impact response needed by the approved UI;
- the minimum typed weather-evidence response needed by the approved dossier.

Out of scope:

- changes to ranking weights, factor definitions, or candidate eligibility;
- new catalog, pass, lodging, travel, climate, or forecast data acquisition;
- provider-backed hotel inventory or Booking.com-style result units;
- current-trip, mobile companion, or public resort-guide redesign;
- authentication, booking, affiliate, or payment behavior;
- changing forecast/climatology ranking semantics or evidence thresholds;
- persistent saved searches or reloadable dossier links without search state;
- generic chat or unbounded LLM-generated UI content.

## Product Fit

The experience must feel like a snow-aware decision workspace rather than a
filter-heavy internal tool, generic AI prompt, or accommodation marketplace.
The homepage demonstrates Snowcast's output before asking for commitment. The
results board leads with a recommended trip configuration and its evidence.
The dossier preserves the comparison context while progressively exposing snow,
trip, and accommodation detail.

The UI keeps uncertainty visible through:

- `Trip fit` as a comparative score, never a probability;
- `Snow window` as a planning conclusion for the requested period;
- `Evidence quality` as archive-backed, forecast-assisted, or fallback-heavy;
- explicit labels for estimates, unavailable values, and watchouts;
- an explicit `Historical pattern` or `Forecast-assisted` evidence mode;
- forecast issue time, coverage, and freshness when forecast data is shown;
- a deterministic preview of material refinement effects when available.

The display unit remains a recommendation group. Hotels and accommodation
options remain subordinate to the selected stay base and do not become global
search results.

## Domain Model

- Bounded contexts touched: Planning, Conditions And Weather Evidence, AI
  Assistance, Booking Handoff.
- Existing terms used: recommendation group, trip configuration, trip fit,
  evidence quality, refinement, dossier, ski region, ski area, stay base,
  selected pass, climatological snow reliability, forecast run, forecast head.
- Presentation-only term: `Trip essentials`. This is not a new scoring group or
  domain entity.
- New client-facing view models: refinement option preview and weather evidence
  summary. They expose existing Planning and Weather evidence; they do not
  create new ranking factors or domain entities.
- Domain-language changes: none required; all durable terms already exist in
  `docs/domain-language.md`.

Important state transitions:

1. The homepage parses a trip brief and transitions into Search V4 results.
2. Search results load with the leading recommendation expanded.
3. The user may expand or collapse any recommendation independently.
4. The user selects a refinement option and sees its deterministic impact
   preview when the API provides one.
5. The user applies the option, Search V4 reruns, and changed positions are
   announced without moving the viewport unexpectedly.
6. The user may select an alternative trip configuration inside a ski-region
   group without changing the group's rank.
7. The user opens a dossier for the selected configuration, switches among
   recommendation dossiers from the navigator, and can return to the same
   search, scroll, and expansion context during the current browser session.
8. The dossier presents climatology for month-only searches. For exact dates it
   presents forecast-assisted evidence only when a usable forecast exists.

Invariants:

- each ski region appears once in the primary result list;
- the card represents the region's top trip configuration and contains its
  alternative configurations;
- `Trip essentials` never changes ranking and never implies ranking weight;
- missing or estimated data is never presented as live or exact;
- month-only searches never present current conditions or a forecast as target-
  date evidence;
- exact-date searches never imply forecast coverage beyond usable forecast
  dates, and historical evidence remains separately identifiable;
- raw factor IDs, group budgets, contribution points, search-model versions,
  and ranking-policy versions stay behind `Show scoring details` or out of the
  user-facing web UI;
- expanding a card never navigates to the dossier;
- opening the dossier never doubles as an expansion control;
- selecting an alternative configuration changes card details, dossier context,
  and save context, but not the recommendation group's rank;
- every weather value remains scoped to the selected ski area and representative
  elevation band;
- all values in design visualizations are illustrative, not product fixtures.

## Decision And Review Gate

- Classification: review-gated
- High-risk domains touched: planning/ranking explainability, evidence and
  estimate trust, shared API contract, and product-facing navigation.
- Developer Decision Checkpoints:
  - resolved: one first-viewport homepage command stage with a concrete example
    recommendation instead of generic process cards;
  - resolved: hybrid decision-board structure;
  - resolved: no more than three intent-aware `Trip essentials` metrics;
  - resolved: midnight shell with restrained alpenglow and powder atmosphere;
  - resolved: independent multi-card expansion;
  - resolved: dossier as a separate deep-inspection route;
  - resolved: collapsible desktop results navigator and compact mobile result
    switcher inside the dossier;
  - resolved: conditional weather evidence where month-only searches use
    climatology and exact-date searches use forecast-assisted evidence only
    when usable forecast rows exist;
  - resolved: stay-base estimates and accommodation-search handoff remain
    subordinate to the ski-trip recommendation;
  - resolved: deterministic per-option impact metadata supports the approved
    pre-apply ranking preview without exposing score deltas;
  - resolved: detailed weather profiles load on demand for the selected dossier
    after the uncapped grouped-response benchmark exceeded every response-cost
    guardrail;
  - resolved: use `lucide-react` as the presentation-only icon system instead
    of maintaining local icon SVGs;
  - accepted assumption: implementation does not add a routing dependency,
    persist search state beyond the browser session, or introduce provider
    inventory unless a new owner checkpoint approves it.
  - unresolved: none.
- ADR status: accepted ADR 0014 owns the on-demand dossier weather-evidence
  boundary. If implementation adopts a router library, persists search state
  beyond the browser session, adds a provider request or server cache, freezes
  result snapshots server-side, or moves ranking/evidence interpretation to
  the client, pause for a new decision and reassess ADR need.
- Advisory design-review:
  - reviewers: Product / Strategy, Backend / API, Data Trust & Source
    Integrity, UI / UX, Security & Privacy, Observability / Ops, Accessibility,
    Performance, Monetization / Partnerships
  - status: completed on 2026-07-16 for the consolidated full-flow revision; no
    Blocker or High finding remains open
- Advisory feature-review before final handoff:
  - reviewers: Product / Strategy, Backend / API, Data Trust & Source
    Integrity, UI / UX, Security & Privacy, Observability / Ops, Accessibility,
    Performance, Monetization / Partnerships
  - status: planned

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Product / Domain | Homepage value demonstration | The first screen must explain Snowcast through its product output, not a generic AI process | Process steps; marketing hero; actionable command stage with sample result | Actionable command stage with a concrete example recommendation | Demonstrates snow-aware decision support while preserving immediate search access | This spec |
| Product / Domain | Results-page structure | Determines whether Search V4 feels like a trip decision tool or a filter dashboard | Flat form and list; strict step flow; hybrid decision board | Hybrid decision board with contextual rail and grouped recommendations | Preserves Search V4 flexibility while restoring Snowcast's decision hierarchy | This spec |
| Product / Domain | Practical card metrics | Too few facts feel abstract; too many create a dashboard and obscure evidence | Fixed metrics; all available metrics; maximum three intent-aware metrics | Maximum three intent-aware `Trip essentials` metrics | Gives concrete scale and cost without implying that every metric drives ranking | This spec |
| Product / Domain | Result disclosure | Dossier-only inspection interrupts comparison; permanently expanded results create excessive density | Dossier-only; accordion; independent expansion | Independent expansion, with result 1 open by default | Supports direct comparison while preserving progressive disclosure | This spec |
| Mixed | Refinement impact preview | Exact movement claims require deterministic server evidence and a stable API contract | Generic copy; apply immediately; structured per-option preview | Structured per-option preview with rank changes, no score deltas | Matches the approved UI and keeps calculation authority on the server | This spec and implementation plan |
| Product / Domain | Visual identity | The current white/blue V4 UI is clear but generic; a saturated pink theme would weaken evidence semantics | Minimal white/blue; light watercolor; midnight shell with restrained color | Midnight shell, neutral cards, soft alpenglow/powder atmosphere | Restores brand distinction while preserving semantic green and amber | This spec |
| Technical | Dossier navigation | A missing route removed a key explanation surface | Modal; inline-only; dedicated route | Dedicated dossier route with return-state preservation | Keeps results scannable and lets the dossier own deep evidence | Implementation plan |
| Technical | Icon system | Repeated local SVGs would drift visually and add accessibility boilerplate across the new surfaces | Continue local SVGs; add `lucide-react` | Add `lucide-react` as the only new frontend dependency | Gives the accepted UI a consistent icon vocabulary while icons remain decorative or explicitly labelled by their controls | This spec and implementation plan |
| Mixed | Dossier result switching | Users need comparison context without turning the detail view into another full results board | Back-only navigation; persistent full results; compact master-detail navigator | Collapsible desktop navigator plus compact mobile switcher | Preserves orientation and quick switching without duplicating card content | This spec and implementation plan |
| Product / Domain | Weather evidence mode | Forecast and climate evidence answer different questions and must not be blended opaquely | Raw weather table; always-on forecast; conditional evidence mode | Month-only climatology; exact-date forecast-assisted evidence with historical context when usable | Matches Search V4 semantics and keeps uncertainty legible | This spec and `docs/planning-model.md` |
| Mixed | Weather evidence delivery | Generic factor payloads are unsafe for charts, while full profiles on every result exceeded all real-cardinality response-cost limits | Parse factor internals; attach every profile; top-results-only profiles; one on-demand dossier endpoint | Versioned typed one-area endpoint using stored Search V4 evidence | Keeps interpretation deterministic and complete for every dossier without making each search transfer every profile | ADR 0014, this spec, and implementation plan |
| Product / Domain | Accommodation depth | Property inventory would make the flow appear more complete but is not available yet | Hide lodging; simulate hotels; estimate and provider-agnostic handoff | Honest stay-base estimate and accommodation-search handoff | Supports booking intent without fake marketplace completeness | This spec |

## Architecture Decisions

- The backend owns user-facing weather-evidence mode selection and typed
  summary construction. The client owns presentation and local disclosure state
  only.
- Search V4 remains the ranking and reranking boundary. Dossier navigation uses
  the ranked response already present in browser-session state.
- `POST /api/search/weather-evidence` is a separate read-only dossier boundary
  for one selected ski area and applied travel window. It shares Search V4
  weather policy and stored repositories but does not rank, acquire provider
  data, or invoke an LLM.
- `lucide-react` is the approved presentation-only icon dependency. Icon choice
  must not encode status without adjacent text, and no other UI or chart
  dependency is introduced by this implementation.
- Detailed weather profiles are not part of `SearchV4Configuration`. Result
  cards retain Search V4's bounded decision summaries; the dossier loads one
  typed profile envelope and caches it until its server-declared validity time
  within the browser session.
- ADR 0014 records the accepted evidence boundary and its alternatives.

## Experience Architecture

### Homepage Command Stage

The homepage is the planning product, not a landing page. One full-width
midnight command stage owns the first viewport and contains:

- Snowcast identity and `Search` / `Current trip` navigation;
- the literal product offer: conditions-aware ski-trip planning;
- one natural-language trip brief input and `Find resorts` action;
- editable parsed-state chips after a brief has been interpreted;
- a compact planning signal that demonstrates snow-window expertise;
- one concrete example recommendation using the same concepts as real results:
  ski region, recommended stay base, snow window, evidence quality, trip fit,
  leading reason, and watchout.

The example recommendation is clearly labelled as an example and uses
illustrative values. It is not fetched as a live recommendation, does not imply
availability, and does not reuse a real user's search. It replaces the generic
`Describe / Review / Compare` process cards because it demonstrates the
distinctive product outcome.

Use one `Example recommendation` label; do not add a second `Proof of result`
label. Primary action copy should remain on one line at supported desktop widths
and reflow as a full-width button on mobile rather than wrapping awkwardly.

The input, parsed chips, and example result form one visual unit that overlaps
or closely follows the command stage on desktop. Their content edges align to a
shared maximum-width grid. The page must not read as a wide hero followed by an
unrelated narrow prototype card.

Initial behavior:

1. The user enters a brief and submits.
2. Parse/search loading keeps the command stage visible and names the work.
3. When Search V4 succeeds, the interface transitions to the results board and
   preserves the editable brief and parsed intent in the compact header.
4. Parse ambiguity may produce bounded clarification, but the initial viewport
   never becomes a permanent filter form or chat transcript.

### Compact Search Command Header

The post-search header is a compact midnight band containing:

- Snowcast logo;
- current natural-language brief in an editable search field;
- `Update results` primary action;
- `Current trip` navigation.

It does not contain a hero, a full filter form, model versions, or a planning
signal card. This visual contraction makes the transition from planning entry
to comparison explicit. On small screens, the query occupies its own row and
the header may stop being sticky when a sticky state would consume too much
viewport height.

### Search Context And Refinement Rail

Desktop uses a narrow left rail and a wide recommendation board.

The rail contains:

1. `Search understood`, split into hard constraints and preferences;
2. `Adjust`, which opens the manual filter drawer;
3. at most one primary contextual refinement card;
4. an optional compact summary of the currently selected recommendation after
   the first implementation increment, if it does not duplicate the main card.

The rail is not a permanent filter form. On mobile it becomes normal document
flow above the recommendations.

### Contextual Refinement

The primary refinement card shows:

- why another answer can materially change the result;
- one question;
- two to four bounded options with one-line tradeoffs;
- selected option state;
- structured impact preview when available;
- `Apply and rerank` and `Skip for now` actions.

Search V4 may return several validated refinement questions. The results rail
shows one primary question at a time and keeps the remaining questions in a
bounded client-side queue. Applying, skipping, or dismissing the current
question advances to the next still-relevant question. Applying a question
reruns Search V4, so the returned queue replaces any unanswered questions from
the previous response rather than carrying stale refinements forward.

Selecting an option does not immediately mutate the applied intent. The UI
enters a preview state. Applying sends the option's typed patches to Search V4.
Clearing the preview returns to the unselected state.

The preview text is rendered deterministically from structured rank changes.
Examples:

- `Val Thorens would move from #3 to #2; Cervinia stays #1.`
- `This choice would replace one result in your top three.`
- `This choice may change eligibility for 4 trip configurations.`

When preview metadata is missing, the UI uses the generic validated statement
`This answer can materially reorder your results` and still allows apply. It
must not invent exact movement.

After apply, reranking preserves the viewport and briefly marks changed ranks.
The feedback strip states what changed and provides `Undo` only when the client
can safely restore the previous typed intent and rerun the search.

### Recommendation Board

The board begins with:

- `Recommended for you`;
- eligible-configuration count in secondary text;
- active refinement preview or post-rerank feedback;
- grouped recommendation cards.

Do not display filtered-out counts, search-model versions, or ranking-policy
versions in the primary board header.

## Recommendation Group Cards

### Collapsed State

A collapsed card shows enough information to decide whether to inspect it:

- rank;
- ski region and country/region context;
- recommended stay base;
- one-line reason or role in the ranking;
- `Trip fit`;
- `Snow window`;
- chevron expansion control.

The expansion control uses `aria-expanded` and an accessible name. `View
dossier` is not used as the expansion affordance.

### Expanded State

Every recommendation can expand to the same semantic anatomy. Lower-ranked
cards may use tighter spacing, but they do not lose essential evidence.

Expanded anatomy:

1. rank, region context, ski-region name, and recommended stay base;
2. `Trip fit` and `Snow window`;
3. one-line recommendation verdict and rationale;
4. `Trip essentials`;
5. evidence quality and selected pass;
6. one supported strength and one relevant watchout when present;
7. `View dossier` and `Save as current trip` actions;
8. alternative trip configurations inside the same ski region;
9. `Show scoring details` disclosure.

Result 1 starts expanded. Other results start collapsed. Expansion state is an
independent set of recommendation-group IDs, so multiple cards may remain open.
After reranking, preserve expanded groups that still exist and expand the new
winner. Removed groups are removed from the expansion set.

The header's non-action area or an explicit chevron button toggles expansion.
Do not wrap nested controls in the expansion button. Actions such as `View
dossier`, `Save as current trip`, and alternative-configuration controls must
not trigger the header toggle.

Alternative-configuration controls select a candidate inside the group. The
card then updates the stay base, selected pass, `Trip essentials`, evidence,
watchouts, dossier target, and save target for that candidate. The ski-region
rank does not change because the display unit remains the recommendation group.
The currently selected candidate is visually and programmatically identified.

### Trip Essentials

Show at most three practical metrics. They summarize the selected trip
configuration; they do not expose factor contribution points.

Metric categories are selected once per search response so that visible cards
remain directly comparable. Selection is deterministic:

1. Include metrics directly requested by active objectives, preferences, or
   hard constraints when trustworthy data exists.
2. Fill remaining positions from this default order: terrain, pass value, lift
   access, lodging estimate, travel effort.
3. Prefer categories with display-ready values across all visible top-three
   recommendation groups. Use the same category order on every card.
4. Avoid repeating `Trip fit`, `Snow window`, evidence quality, or the selected
   pass name.
5. If fewer than three comparable categories have trustworthy coverage, render
   one or two categories rather than substituting different categories per
   card or showing weak placeholders.
6. Keep category order stable: terrain, cost, access/effort.

Examples:

- `Terrain - 360 km`
- `Terrain - Estimated 31 km (ski area only)`
- `Pass value - EUR 58/day`
- `Lift access - 250 m walk`
- `Estimated stay - EUR 220-310/night`
- `Travel effort - 3h 20m transfer`

Terrain remains a core metric, but the typed response keeps the kilometre value
paired with field-level evidence: trust status, source scope (`pass`,
`terrain_domain`, or `ski_area`), source entity ID, and owning trust-manifest
field group. A ski-area fallback remains visible when useful, but it is labelled
as ski-area-only and never presented as verified pass-accessible coverage.

Use `Estimated`, `Approx.`, or `From` when required by source semantics. A
lodging estimate with no provider inventory never appears as a live hotel rate.

## Dossier Boundary

`View dossier` navigates to
`/recommendations/:ski_region_id?candidate=:candidate_id`. The ski-region path
preserves the recommendation-group identity; the candidate query identifies the
currently selected trip configuration.

The dossier uses this hierarchy:

1. compact editable search command;
2. results navigator or compact recommendation switcher;
3. verdict and selected trip configuration;
4. `Why it leads` and principal watchout;
5. conditional snow evidence for the requested window;
6. selected configuration, pass, and practical trip essentials;
7. alternative configurations within the recommendation group;
8. stay-base estimate and accommodation handoff;
9. decision evidence ledger and collapsed scoring details;
10. save-current-trip action.

The dossier is an evidence-led decision surface, not a collection of equal
cards. It uses full-width bands and unframed content groups for major sections,
with cards reserved for repeated result rows, metric cells, and bounded
sub-options.

### Dossier Results Navigator

At wide desktop widths the dossier uses a master-detail shell:

- a `260px` recommendation navigator;
- a `24px` gutter;
- a flexible dossier column;
- a control that collapses the navigator to an icon/rank rail of approximately
  `64px` without removing the dossier from view.

Each row shows only rank, ski-region name, selected stay base, `Trip fit`, and a
short snow-window label. The current dossier is visibly and programmatically
selected. Rows navigate directly to the session-selected configuration they
display for that recommendation group; they do not reset the group to its top
configuration, expand into result cards, or duplicate full evidence.

The compact navigator shows the top three recommendation groups. If the current
dossier is outside that set, it shows the top two plus the current group. The
rail therefore contains at most three result rows plus `All results`; it never
becomes a second scrollable results board.

`All results` returns to the board. At widths below the desktop master-detail
breakpoint, the rail is replaced with a compact `Recommendation N of M`
switcher above the dossier. Opening it reveals the same bounded result list in
normal document flow. The mobile switcher must be operable without hover and
must not create a nested viewport scroll.

Switching results:

- updates route, selected group, and candidate;
- keeps the original query and ranked response;
- resets dossier scroll to the top;
- announces the new recommendation title;
- never reruns search unless the underlying result state is unavailable.

### Dossier Verdict And Configuration

The dossier header names the ski region and recommended stay base first. It
shows `Trip fit`, `Snow window`, and evidence quality as secondary decision
signals. `Why it leads` follows immediately and contains one supported strength
and one material watchout where present.

Destination, ski area, stay base, selected pass, and access remain explicitly
labelled. The interface does not collapse these entities into a generic
`resort` label when they differ.

### Conditional Snow Evidence

Snow evidence is tied to the requested window and selected ski area. It is a
decision summary, not a raw weather dashboard.

Month-only searches:

- title the section `Snow evidence for <Month>`;
- show the badge `Historical pattern`;
- state that month searches use climatology rather than a live forecast;
- identify the representative elevation band and evidence-season coverage;
- show a compact distribution/profile chart and up to five decision metrics:
  median snow depth, interquartile depth range, average daily snowfall,
  probability of depth above the policy-relevant threshold, and average maximum
  temperature;
- keep the daily climatology profile behind a disclosure when it would add
  substantial density.

Exact-date searches with usable forecast evidence:

- title the section `Snow evidence for your dates`;
- show `Forecast-assisted` and the forecast issue/freshness state;
- provide a segmented `Forecast` / `Historical context` control;
- show a compact daily strip or chart for forecast snow depth, snowfall, and
  temperature, with rain/thaw or wind warnings only when materially relevant;
- state usable-date coverage and forecast share without describing the share as
  recommendation confidence;
- preserve historical context as a separate view rather than blending values
  into an unexplained synthetic forecast.

Exact-date searches without usable forecast evidence fall back to the
month/window climatology state and explicitly say why forecast evidence is not
being used. Stale, incomplete, or missing forecast rows never appear as fresh.

Chart accessibility requirements:

- provide a concise textual interpretation before or beside the chart;
- expose the underlying summary values in accessible text;
- do not require color to distinguish historical range, median, and forecast;
- provide a table or structured list inside the detail disclosure for users who
  cannot interpret the chart;
- use units in every metric and explain the elevation band.

### Accommodation Handoff

The dossier keeps accommodation under the selected stay base. Until
provider-backed inventory exists, the section shows:

- `Stay-base estimate, not live hotel inventory`;
- honest nightly or trip estimate with currency and trust label;
- lift-access and rental context when supported;
- `Open accommodation search` or equivalent provider-agnostic handoff.

It never renders invented hotel names, availability, ratings, amenities, or
provider freshness. When provider-backed suggested stays are introduced later,
they remain subordinate to the selected stay base and follow the May 2026
accommodation evidence rules.

Returning from the dossier restores the current query, applied intent, ranked
response, selected candidate per group, scroll position, and expanded-card set
for the browser session. The initial implementation does not require a new
deep-link dossier API. A direct load or reload without the required
browser-session search state shows a recoverable state that explains the
missing context and returns the user to search. Fully reloadable dossier links
remain outside this spec.

## Visual System

Use the existing Snowcast tokens.

- Midnight `#021a35`: sticky command header and rare selected brand surfaces.
- Alpine blue `#0b5fb8`: primary actions, data, selected controls, links.
- Alpenglow `#ff5f8f`: refinement and brand accents only.
- Alpenglow soft `#ffe1eb`: restrained upper-left/left-edge atmosphere.
- Powder `#dbeaf5` and ice `#edf6fb`: restrained upper-right/right-edge
  atmosphere and secondary data surfaces.
- Snow `#f8fbff`: main canvas.
- White: recommendation and evidence surfaces.
- Pine `#087f68`: supported evidence and positive fit.
- Amber `#f59e0b`: cautions, watchouts, and disruption.

Color rules:

- pink never indicates warning severity, trust, or snow status;
- cards remain neutral and readable over the atmospheric canvas;
- green and amber always include iconography and text labels;
- do not introduce purple, saturated gradients, decorative orbs, or tinted card
  interiors;
- the page-edge treatment must remain subtle enough that removing it does not
  change information hierarchy.

Typography remains Sora for compact headings and Manrope for body and controls.
Use stable metric-cell widths and no viewport-scaled font sizes.

## API And Client Contract

Existing endpoint:

- `POST /api/search` remains the Search V4 request and rerank boundary.

Required response extension:

- each validated `RefinementOption` may include a deterministic preview;
- the preview is computed from server-side variant ranking simulation;
- preview construction reuses the current candidate evaluations and variant
  simulation; it must not add another LLM call or repeat catalog/database
  acquisition;
- the dossier may request one typed, display-ready weather summary for the
  selected configuration's ski area and the current applied intent;
- the client never recomputes scores or eligibility.

Proposed client contract:

```text
RefinementOption.preview?:
  top_rank_changes:
    - ski_region_id
      previous_rank: integer or null
      preview_rank: integer or null
  eligible_candidate_count_delta: integer
```

Rules:

- compare each option's simulated ranking with the baseline ranking for the
  current applied intent;
- include at most three changed recommendation groups, ordered by the earliest
  affected baseline or preview rank;
- include only groups where either the baseline or preview rank is inside the
  visible top-three set; summarize additional movement generically;
- do not expose score deltas, group contributions, factor IDs, or policy values;
- `null` previous rank means the group enters the visible ranked set;
- `null` preview rank means the group leaves the visible ranked set;
- preview absence is valid and falls back to generic material-impact copy;
- the optional additive field does not break clients that ignore it;
- the response remains usable when refinement generation fails or is disabled.

Accepted weather endpoint contract:

```text
POST /api/search/weather-evidence

request:
  intent: SearchIntent
  ski_area_id: string

response:
  weather_evidence_version: search-weather-evidence-v1
  status: available | unavailable
  ski_area_id: string
  evaluated_at: ISO timestamp
  cache_valid_until: ISO timestamp
  when status=unavailable:
    unavailable_reason: travel_window_missing | historical_evidence_unavailable
    limitations: string[]
  when status=available:
    evidence:
    mode: climatology | forecast_assisted
    window_label: string
    elevation_band: mid_mountain
    elevation_status: exact | mixed | unavailable
    elevation_m: integer or null
    interpretation: string
    limitations: string[]
    historical:
      source_label: string
      source_model: string or null
      computed_at: ISO timestamp or null
      baseline_start_year: integer or null
      baseline_end_year: integer or null
      evidence_seasons: integer or null
      latest_archive_year: integer or null
      provenance_status: homogeneous | mixed
      sources: HistoricalWeatherSource[]
      snow_depth_cm_p25: number or null
      snow_depth_cm_p50: number or null
      snow_depth_cm_p75: number or null
      probability_snow_depth_ge_30cm: number or null
      average_daily_snowfall_cm: number or null
      average_max_temperature_c: number or null
      daily_profile: WeatherEvidencePoint[]
    forecast: null or
      source_label: string
      source_model: string or null
      issued_at: ISO timestamp or null
      provenance_status: homogeneous | mixed
      sources: ForecastWeatherSource[]
      coverage_status: complete | partial
      usable_date_count: integer
      requested_date_count: integer
      average_forecast_share: number
      daily_profile: WeatherEvidencePoint[]

WeatherEvidencePoint:
  date_or_month_day: string
  snow_depth_cm: number or null
  snow_depth_cm_p25: number or null
  snow_depth_cm_p50: number or null
  snow_depth_cm_p75: number or null
  snowfall_cm: number or null
  temperature_min_c: number or null
  temperature_max_c: number or null
  rain_risk: number or null
  thaw_risk: number or null
  wind_gust_kmh: number or null
```

Weather contract rules:

- detailed profiles are absent from `SearchV4Configuration` and therefore do
  not scale the grouped search response;
- the endpoint accepts the exact applied typed intent plus one canonical
  catalog ski-area ID and rejects unknown IDs before repository access;
- the backend maps existing typed climatology and forecast records into the
  summary; the client must not parse `raw_value` or `explanation_inputs` to
  infer the evidence mode or chart values;
- `mode=climatology` requires `forecast=null`;
- `mode=forecast_assisted` requires at least one usable forecast date and keeps
  the historical section present;
- stale forecast runs are not usable target-date evidence, so they cannot
  produce `mode=forecast_assisted`; their exclusion is described in
  `limitations` while the summary falls back to climatology;
- daily profiles are bounded to the requested window or one calendar month and
  are ordered chronologically, with no more than 31 points per profile;
- each historical and forecast source collection contains at most 31 records;
- top-level elevation is exact only when all selected historical and forecast
  source records use one elevation; mixed elevations produce
  `elevation_status=mixed` and `elevation_m=null`, and every source record keeps
  its exact elevation;
- `coverage_status` describes requested-date coverage, not source freshness;
  every selected forecast row is fresh at `evaluated_at` by construction;
- `average_forecast_share` is a model blend input, not user confidence, and the
  UI labels it `Forecast coverage in this assessment` rather than `Confidence`;
- missing numeric values remain `null`; the backend does not manufacture zeros;
- homogeneous rows retain exact top-level source metadata; mixed rows expose
  typed per-source records and nullable top-level source scalars rather than a
  synthetic baseline, model, computed time, or forecast issue time;
- interpretation and limitation strings are selected from deterministic
  templates and do not include raw provider errors or policy internals;
- summary construction reuses the same stored repositories, freshness test,
  source selection, and versioned weather policy as Search V4; it adds no
  provider call, LLM call, or ranking pass;
- maximum-cardinality one-area route envelopes are bounded to 128 KiB
  uncompressed JSON and 25 ms p95 in-memory service construction over 100 warm
  iterations;
- if implementation cannot build a trustworthy summary, `status=unavailable`
  carries a bounded reason and limitations; the dossier does not scrape generic
  factor internals;
- available and unavailable responses are cached only in the current browser
  session by canonical travel window and ski-area ID and only while
  `now < cache_valid_until`; transport failures are retryable and are not
  cached;
- forecast-assisted validity ends at the earliest selected forecast run's
  freshness expiry; responses without usable forecast evidence use a five-
  minute revalidation interval;
- the existing bounded-route HTTP duration metric records endpoint latency.

Client state includes:

- current query and applied typed intent;
- selected but unapplied refinement option;
- optional preview metadata;
- `expandedRecommendationGroupIds`;
- `selectedCandidateIdByRecommendationGroup`;
- results scroll position and dossier return state;
- dossier navigator collapsed state and current recommendation-group ID;
- selected weather evidence view (`forecast` or `historical`) for the current
  dossier only;
- unexpired dossier weather responses keyed by canonical travel window and ski
  area for the current browser session only.

No new routing library is assumed. The implementation plan must either use the
existing history-based navigation or raise a new owner checkpoint before adding
a dependency.

## Data Trust And Source Integrity

- Terrain values come from the selected pass or ski-area coverage already in
  the Search V4 response. Use selected-pass accessible terrain rather than a
  broader ski-region marketing total.
- Pass value appears only when amount and duration support a deterministic
  per-day derivation. Ranges remain ranges rather than midpoint estimates.
- Lift access uses the selected stay-base access evidence. Show an exact
  distance or duration only when the response provides it; otherwise use the
  supported access mode such as `Near` or `Ski-in/out`.
- Lodging values retain `verified`, `verified with adjustment`, `estimated`, or
  `needs source` semantics. `Estimated` is allowed only with an explicit label;
  `needs source` numeric values do not enter `Trip essentials`.
- Travel effort remains approximate when derived from fallback routing.
- Evidence quality continues to distinguish archive-backed,
  forecast-assisted, and fallback-heavy recommendations.
- Month-only evidence comes from `SnowClimatologyDaily` rows for the selected
  ski area and representative mid-mountain band. The baseline years, evidence
  seasons, and latest archive year remain visible or available in the detail
  disclosure.
- Exact-date forecast evidence comes only from the selected eligible forecast
  head and usable valid dates. It must not mix providers into an opaque average
  or substitute the latest current-condition snapshot for target-date evidence.
- Snow depth is modelled depth at the representative elevation band. It is not
  open-piste percentage, lift status, skiable-terrain coverage, or an official
  resort report.
- Temperature, rain, thaw, and wind values are evidence/context. They do not
  imply additional ranking weight beyond `docs/planning-model.md` and the
  versioned policy.
- Forecast issue time, usable-date coverage, and stale/partial status are shown
  when the forecast view is available.
- Missing data reduces visible metric count; it does not create fabricated
  values or generic `Not available` tiles.

## AI / LLM Use

Deterministic code owns:

- result grouping and ordering;
- `Trip essentials` selection and formatting;
- refinement option validation;
- per-option rank preview simulation;
- impact-copy templates;
- weather-evidence mode selection, aggregation, interpretation templates, and
  limitation labels;
- evidence and estimate labels.

The LLM may continue to propose bounded refinement question wording, option
wording, and typed patches under the existing Search V4 policy. It does not
generate recommendation explanations, metric values, rank changes, or dossier
facts on the client.

Search results remain fully usable when refinement generation fails, times out,
or is disabled.

## Loading, Empty, And Failure States

- Homepage parsing/search loading keeps the command stage stable, disables
  duplicate submission, and uses one concise status line rather than a blank
  page or indeterminate chat animation.
- Initial loading copy names the work in product language: evaluating snow
  window, stay fit, travel effort, pass value, and evidence.
- Reranking keeps existing results visible with a local busy state where safe;
  it does not replace the board with a blank screen.
- No-results copy names conflicting hard constraints and provides reversible
  relaxation actions.
- Missing refinement preview uses generic material-impact copy.
- A failed refinement apply preserves the selected option and current results,
  announces the error, and permits retry or clear.
- A failed dossier load offers return to the preserved search state.
- A typed unavailable weather response shows `Snow evidence is not available
  for this configuration` plus the server's bounded reason and limitations. It
  never falls back to parsing debug fields in the browser.
- Forecast-unavailable and forecast-stale states retain historical context and
  explain why the forecast view is absent or limited.
- Dossier evidence loading completion, typed unavailability, retryable failure,
  and successful retry are announced through one polite status region without
  moving focus or replacing the dossier verdict.
- A failed recommendation switch leaves the current dossier intact and offers
  retry or `All results`.

## Responsive And Accessibility Behavior

Desktop:

- maximum content width remains approximately `92rem`;
- homepage command content and search workspace share the same grid edges;
- decision rail is approximately `20rem` and the board uses remaining width;
- two expanded cards create natural page height, never nested viewport scroll;
- metric tiles use stable equal-width tracks;
- dossier uses a `260px` navigator, `24px` gutter, and flexible detail column at
  the wide master-detail breakpoint;
- collapsed dossier navigation is approximately `64px` and cannot overlap the
  dossier content.

Mobile:

- command header, context, refinement, and results stack in document order;
- homepage headline, planning signal, input, chips, and example result reflow
  without detached floating panels or clipped text;
- the query and update action occupy separate rows when necessary;
- card scores and expansion control remain visible in the collapsed header;
- actions stack full width;
- `Trip essentials` uses one column on the narrowest viewport and up to three
  equal columns when content fits;
- dossier navigation becomes a compact recommendation switcher above the
  dossier; the desktop rail is not rendered as an off-canvas overlay;
- weather metrics use two columns when they fit and one column at the narrowest
  viewport; charts use the content width and never require horizontal scroll;
- no horizontal scrolling is required.

Accessibility:

- card toggles are keyboard-operable buttons with `aria-expanded` and
  `aria-controls`;
- the homepage trip brief has a persistent label, and removable parsed-state
  chips are buttons with names such as `Remove France`;
- after homepage search completes, focus moves to the results heading unless
  an error or clarification requires focus first;
- rank movement is announced through a polite live region after rerank;
- focus remains on the triggering control after expand/collapse;
- dossier navigation has a clear accessible name and is not nested inside the
  expansion button;
- desktop navigator collapse and mobile recommendation switcher expose their
  expanded/selected state and preserve a predictable focus order;
- changing dossier result moves focus to the new dossier heading or announces
  it through a polite live region;
- forecast/historical controls use a labelled tab or segmented-control pattern,
  with keyboard operation matching the chosen semantic role;
- charts have equivalent accessible text or structured values;
- semantic status never relies on color alone;
- body text meets 4.5:1 contrast and control boundaries meet 3:1;
- reduced-motion mode removes card-reorder and expansion animation while
  preserving state changes.

## Security, Privacy, And Abuse

- Raw trip briefs, prompts, and LLM responses must stay out of logs, metrics,
  and traces.
- UI analytics may record interaction type, rank position, and coarse result
  identifiers, but not free-text briefs or typed accommodation/travel details.
- Refinement preview metadata is server-produced and treated as untrusted input
  for rendering; the client uses text rendering, not HTML injection.
- Existing rate limits and timeout behavior for refinement generation remain in
  force.

## Observability And Operations

Useful aggregate events:

- homepage search submitted and bounded clarification shown;
- recommendation expanded/collapsed by rank;
- dossier opened by rank;
- dossier recommendation switched by source rank and destination rank;
- dossier navigator collapsed/expanded;
- weather evidence view changed between forecast and historical context;
- refinement preview selected, applied, cleared, failed;
- missing `Trip essentials` category;
- missing weather-evidence summary or forecast-unavailable state;
- dossier return-state restoration failed.

Do not attach raw search briefs, factor IDs, metric values, candidate IDs, or
weather dates/values to metric labels. Result identifiers may appear only in a
bounded structured event when separately approved. UI failures must not block
deterministic search results.

## Acceptance Criteria

- Homepage, results, and dossier match the accepted visual hierarchy and share
  one Snowcast design system.
- The homepage first viewport contains the actionable trip brief, planning
  signal, and a clearly labelled example recommendation using real Snowcast
  concepts rather than generic process cards.
- Homepage command content and search workspace align to a coherent page grid.
- Submitting the homepage brief transitions to results without losing the brief
  or parsed intent.
- The compact midnight command header replaces the permanent Search V4 form.
- Hard constraints and preferences are visible in user language and editable
  through the manual-adjustment entry point.
- The board displays one recommendation group per ski region.
- Result 1 starts expanded; results 2 and later start collapsed.
- Any result can expand independently and multiple results can remain open.
- Collapsed cards show rank, ski region, stay base, rationale, `Trip fit`,
  `Snow window`, and a chevron.
- Expanded cards show no more than three trustworthy `Trip essentials` metrics.
- `Trip essentials` follow active intent and omit unavailable values.
- All visible recommendation cards use the same `Trip essentials` categories
  and order for a search response.
- Selecting an alternative configuration updates the card, dossier target, and
  current-trip save target without changing the group's rank.
- Dossier and save actions never toggle expansion.
- `View dossier` opens the dedicated recommendation dossier.
- The dossier begins with the selected trip verdict and keeps deep evidence in
  progressive sections rather than equal-weight dashboard cards.
- Wide desktop shows the collapsible result navigator; narrower layouts show a
  compact recommendation switcher.
- Every result in the navigator/switcher can open its corresponding dossier
  without rerunning search.
- Switching dossier resets detail scroll, announces the new result, and retains
  query/ranking context.
- Returning from the dossier restores the current browser-session search state.
- Month-only dossiers show `Historical pattern`, climatology coverage, selected
  elevation band, and supported snow-depth/snowfall/temperature metrics; they do
  not show a target-date forecast.
- Exact-date dossiers show `Forecast-assisted` only with usable forecast rows,
  expose freshness and coverage, and keep historical context separate.
- Missing or stale forecast evidence falls back honestly without fabricating
  current conditions or forecast certainty.
- The frontend consumes a typed weather-evidence summary and does not infer
  chart values or evidence mode from generic factor internals.
- Weather charts have equivalent accessible text or structured values.
- Accommodation remains an explicitly labelled stay-base estimate and handoff
  until provider-backed inventory exists.
- A selected refinement option shows exact rank movement only when structured
  preview metadata supports it.
- Applying a refinement reranks in place and announces changed positions.
- Search remains usable without refinement generation or preview metadata.
- Raw ranking internals and model versions are absent from primary result UI.
- Pink is limited to brand/refinement accents; green and amber preserve their
  evidence and warning semantics.
- Desktop and mobile layouts have no horizontal overflow or overlapping text.
- Keyboard, focus, live-region, contrast, and reduced-motion requirements pass.

## Verification

Unit tests:

- deterministic `Trip essentials` selection, ordering, omission, and estimate
  labels;
- refinement preview formatting for movement, entry, exit, and absent preview;
- typed weather-evidence mapping for climatology, forecast-assisted, partial
  coverage, stale exclusion, and unavailable cases;
- null preservation and chronological bounding of weather profile points;
- deterministic weather interpretation and limitation templates;
- expansion-set preservation across reranks;
- dossier return-state serialization/restoration.

API and integration tests:

- per-option preview is derived from deterministic variant rankings;
- preview omits score and policy internals;
- refinement response without preview remains schema-valid;
- applying the same option produces ranking movement consistent with preview;
- month-only weather endpoint response produces climatology-only evidence;
- exact-date weather endpoint response includes forecast evidence only for usable dates and
  retains historical context;
- weather endpoint rejects unknown ski-area IDs before repository access;
- weather summary uses the requested ski area/elevation band and omits unsupported
  numeric values;
- grouped Search V4 responses contain no detailed weather profiles;
- the weather endpoint invokes neither ranking, provider acquisition, nor an
  LLM and remains within its one-area payload/construction bounds;
- Search V4 succeeds when refinement generation fails.

UI tests:

- homepage search preserves brief and parsed intent through navigation;
- result 1 is open initially;
- results 1 and 2 can remain open simultaneously;
- nested dossier/save actions do not toggle expansion;
- selecting an alternative updates details and actions without reranking the
  group;
- collapsed and expanded accessible states are correct;
- missing metrics do not leave broken or empty tiles;
- desktop dossier navigator collapses, expands, and switches results;
- mobile recommendation switcher is keyboard/touch operable;
- switching dossier retains ranked state and resets detail scroll;
- month-only, exact-date forecast, forecast-unavailable, and missing-evidence
  dossier variants render the correct labels and controls;
- forecast/historical controls and chart alternatives are accessible;
- estimate-only accommodation copy never renders provider-backed claims;
- loading, no-results, apply-failure, and dossier-failure paths remain usable.

Visual and manual checks:

- Playwright screenshots for homepage, results, and dossier at desktop, tablet,
  and narrow mobile viewports;
- no horizontal overflow at supported widths;
- card content and controls do not overlap at 200% zoom;
- reduced-motion behavior;
- homepage/result/dossier visual-grid consistency;
- dossier rail collapse and mobile switcher behavior;
- chart text alternative and keyboard operation;
- return from dossier restores query, scroll, and expansion state;
- color semantics remain understandable in grayscale and common color-vision
  deficiency simulations.

## Advisory Review

- Design reviewers: Product / Strategy, Backend / API, Data Trust & Source
  Integrity, UI / UX, Security & Privacy, Observability / Ops, Accessibility,
  Performance, Monetization / Partnerships.
- Feature reviewers: Product / Strategy, Backend / API, Data Trust & Source
  Integrity, UI / UX, Security & Privacy, Observability / Ops, Accessibility,
  Performance, Monetization / Partnerships.
- Design-review status: completed on 2026-07-16.
- Outcome: proceed to implementation planning after owner review of this spec.
- Consolidated-flow findings resolved in this revision:
  - [High] Backend / API: session-long weather caching could outlive forecast
    freshness. Every response now carries server-owned evaluation and validity
    timestamps; forecast-assisted validity follows selected run expiry and all
    other responses revalidate after five minutes.
  - [Medium] Backend / API, Data Trust, Performance, and Accessibility: typed
    unavailability, coverage naming, elevation provenance, source cardinality,
    route-level verification, and async announcements were incomplete. The
    status-discriminated contract and implementation plan now define each
    requirement explicitly.
  - [Medium] Backend / API and Data Trust & Source Integrity: the initial weather
    contract allowed a stale forecast inside `forecast_assisted` mode and omitted
    climatology provenance. Stale runs are now excluded from that mode, fallback
    limitations are explicit, and historical/forecast source metadata is typed.
  - [Medium] Performance: the real uncapped grouped-response benchmark failed
    every accepted profile-cost guardrail: 1,092,264 additive bytes, 2.133007x
    baseline size, and 32.510 ms p95 construction across 39 summaries. The owner
    approved the ADR 0014 one-area dossier endpoint. Profiles remain capped at
    31 points and the revised endpoint has explicit one-area payload and
    construction budgets.
  - [Medium] UI / UX: an unbounded dossier navigator could become a duplicate
    scrollable results board. It now contains at most the top three groups, or
    the top two plus the current out-of-band group, and retains `All results`.
  - [Medium] Accessibility: homepage-to-results focus, removable-chip naming,
    route-change announcement, weather-control semantics, and chart alternatives
    were not all explicit. They are now acceptance and verification requirements.
  - [Low] Product / Strategy: a homepage example can look like a live resort
    claim. It is explicitly labelled as illustrative and does not imply live
    availability or current recommendation data.
- Earlier results-board findings that remain resolved:
  - [High] Backend / API: dossier navigation originally identified only the ski
    region and could not reliably preserve the selected trip configuration.
    The route now carries `candidate_id`, and the state contract names selected
    candidate preservation explicitly.
  - [Medium] Product / Strategy: the visual's `Save to list` action implied a
    saved-list model that Snowcast does not have. Production copy now uses the
    existing `Save as current trip` behavior.
  - [Medium] UI / UX: independently selected practical metrics could prevent
    direct card comparison. Metric categories are now chosen once per response
    and kept consistent across visible cards.
  - [Medium] Data Trust & Source Integrity: practical metric readiness was
    underspecified. The spec now excludes `needs source` numeric claims,
    preserves ranges, and requires supported access evidence for exact values.
  - [Medium] Backend / API: refinement movement previews lacked baseline,
    cardinality, and request-path constraints. The contract now compares each
    option with the applied-intent baseline, caps visible movement, and reuses
    existing deterministic simulation.
  - [Low] Accessibility: allowing the whole card header to be an expansion
    button could create nested interactive controls. The expansion target is
    now limited to the non-action header area or explicit chevron.
- No defensible design finding remains for Security & Privacy, Observability /
  Ops, or Monetization / Partnerships after the telemetry,
  no-extra-request-work, and estimate-only accommodation constraints.
- Known residual risks:
  - expanded cards can produce long pages when many results are opened;
  - practical metrics depend on uneven catalog and provider coverage;
  - exact refinement previews require a new structured response field;
  - browser-session return-state preservation needs careful history handling;
  - the one-area weather endpoint still needs exact-head payload, construction,
    repository-call, and browser-cache verification;
  - the final dossier responsive behavior still needs Playwright verification at
    narrow mobile and 200% zoom during implementation.
