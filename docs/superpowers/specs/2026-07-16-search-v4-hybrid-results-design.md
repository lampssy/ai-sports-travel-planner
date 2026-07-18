# Feature Spec: Search V4 Web Experience

## Status

- Status: implemented; follow-up trust, refinement-lifecycle, weather-evidence,
  responsive-polish, and exact-state advisory review complete on 2026-07-17
- Owner: solo-builder
- Active search contract: `search-v4`
- Active ranking policy: `search-v4-policy-1`
- Active refinement presentation policy: `search-refinement-presentation-1`
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
- Active follow-up plan:
  `docs/superpowers/plans/2026-07-17-search-v4-trust-and-ui-polish.md`
- Related ADRs:
  `docs/architecture/adr/0012-versioned-search-factor-registry-and-ranking-policy.md`,
  `docs/architecture/adr/0015-load-search-refinements-after-ranking.md`

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
- the minimum typed weather-evidence response needed by the approved dossier;
- an explicit refinement-availability outcome and a deterministic, materially
  validated registry-backed factor fallback when the bounded LLM proposal path
  is unavailable;
- plain-language decision evidence with technical provenance available only in
  a secondary disclosure;
- a small Snowcast-owned React UI foundation for repeated actions, statuses,
  metrics, section headings, disclosures, tabs, and async states;
- action-scoped search, refinement, save, and weather errors that preserve
  usable prior state without presenting stale failures as current-page errors;
- a restrained creamy-pink to snow-white to powder-blue application canvas and
  the responsive/focus polish identified during browser review.

Out of scope:

- changes to ranking weights, factor definitions, or candidate eligibility;
- new catalog, pass, lodging, travel, climate, or forecast data acquisition;
- provider-backed hotel inventory or Booking.com-style result units;
- current-trip, mobile companion, or public resort-guide redesign;
- authentication, booking, affiliate, or payment behavior;
- changing forecast/climatology ranking semantics or evidence thresholds;
- persistent saved searches or reloadable dossier links without search state;
- generic chat or unbounded LLM-generated UI content;
- a full shadcn migration, a generic component marketplace, or a Storybook
  deployment;
- deterministic questions that bypass the existing materiality thresholds or
  alter ranking weights, candidate eligibility, or evidence semantics.

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
- New post-search response state: `refinement_status`, with
  `questions_available`, `not_needed`, or `temporarily_unavailable`. This is an
  orchestration outcome, not a ranking factor or confidence score.
- Domain-language changes: none required; all durable terms already exist in
  `docs/domain-language.md`.

Important state transitions:

1. The homepage parses a trip brief and transitions into Search V4 results.
2. Search results load with the leading recommendation expanded without
   waiting for an LLM.
3. The client requests an optional refinement using the returned canonical
   applied intent and baseline fingerprint. The server reads the exact
   short-lived evaluated baseline stored by ranking; the refinement rail loads
   independently and stale requests are cancelled or discarded when the intent
   changes.
4. The user may expand or collapse any recommendation independently while the
   refinement request is pending.
5. The user selects a refinement option and sees its deterministic impact
   preview when the API provides one.
6. The user applies the option, Search V4 reruns with the updated intent, stores
   a new evaluated baseline, and changed positions are announced without moving
   the viewport unexpectedly. The client immediately requests the next
   refinement from that new baseline.
7. The user may select an alternative trip configuration inside a ski-region
   group without changing the group's rank.
8. The user opens a dossier for the selected configuration, switches among
   recommendation dossiers from the navigator, and can return to the same
   search, scroll, and expansion context during the current browser session.
9. The dossier presents climatology for month-only searches. For exact dates it
   presents forecast-assisted evidence only when a usable forecast exists.
10. When the bounded LLM path produces no usable proposal, Snowcast may offer
    one registry-backed factor question only after the existing variant
    simulation proves that its typed options can materially change the ranking.
11. A failed search update keeps the previous ranked response visible and
    identifies it as the previous ranking; returning from a dossier does not
    issue another search request or surface unrelated stale errors.

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
- raw provenance enums, source-reference counts, and internal field-group
  wording never appear in the primary decision explanation;
- deterministic fallback refinements use the same typed patches, validation,
  materiality thresholds, answered-question suppression, and rerank path as
  LLM-proposed refinements;
- refinement questions are factor-topic-only in this slice. Group-priority
  patches remain part of Search V4 intent but are not generated as refinement
  questions;
- `not_needed` means no material follow-up is available, while
  `temporarily_unavailable` means the exact baseline handoff is unavailable or
  mismatched, or proposal generation failed and no validated fallback could be
  produced;
- `POST /api/search` never invokes an LLM; refinement loading is optional and
  cannot make an otherwise successful ranking fail;
- the refinement request uses the ranking response's canonical applied intent
  and baseline fingerprint, reads only the exact stored evaluated baseline, and
  is ignored when it no longer matches the active search session;
- a public baseline fingerprint is not trusted without a matching SHA-256
  digest recomputed from the request's canonical intent; canonical serialization
  supplies the equality binding without storing a full intent or performing a
  second typed-equality check;
- missing, expired, evicted, restarted, or mismatched baseline state never
  reruns deterministic search or invokes Gemini;
- a delivered question remains answerable after the 60-second server handoff
  expires; applying it performs a deliberate full rerank and creates a new
  baseline;
- weather charts render only typed historical or forecast rows returned by the
  weather-evidence endpoint, preserve missing-data gaps, and keep an equivalent
  accessible value table.

## Decision And Review Gate

- Classification: `review-gated`, full design flow
- High-risk domains touched: planning/ranking explainability, evidence and
  estimate trust, shared API contract, and product-facing navigation.
- Developer Decision Checkpoints:
  - resolved by the owner on 2026-07-17 for the evaluated-baseline snapshot
    handoff recorded in ADR 0015;
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
  - resolved: replace the technical evidence ledger with a plain-language
    `Why this trip` summary, keeping raw provenance in a collapsed
    `Sources and calculation details` disclosure;
  - resolved: add explicit refinement availability and use a deterministic
    fallback only when the existing variant simulation proves material impact;
  - resolved: use a small Snowcast-owned React component foundation and avoid a
    full shadcn migration; headless third-party primitives remain opt-in only
    for genuinely complex interaction behavior;
  - resolved: add Recharts for the typed snow/weather visualization while
    preserving the accessible table and truthful missing-data gaps;
  - resolved: show `Snow depth`, `Fresh snow`, and `Temperature` as separate
    segmented chart views so one plotted view has one unit and one Y axis;
  - resolved: after deterministic ranking, store a typed, lightweight
    evaluated-baseline snapshot in a thread-safe process-local LRU/TTL store
    with a 60-second TTL and maximum 64 entries;
  - resolved: bind refinement lookup to both the public baseline fingerprint and
    the SHA-256 digest recomputed from canonical request intent; this digest
    comparison supplies equality binding and a fingerprint alone is not trusted;
  - resolved: retain no full `SearchIntent` or origin text, full
    `CatalogSnapshot` or `CatalogTrustManifest`, brief, or provider secrets in
    the baseline store;
  - resolved: a missing, expired, evicted, restarted, or mismatched baseline
    returns `temporarily_unavailable` without deterministic search or Gemini;
  - resolved: the 60-second TTL covers only the server handoff for generating a
    question. A delivered question remains answerable; applying it reruns full
    search, stores a new baseline, and immediately requests the next refinement;
  - resolved: protect the anonymous refinement endpoint with two concurrent
    requests and six requests per minute per client with burst two in the
    current one-machine deployment;
  - resolved: apply a subtle creamy-pink to snow-white to powder-blue canvas
    gradient while keeping content surfaces neutral and semantic statuses
    independent from brand color;
  - accepted assumption: the process-local store fits the current
    single-instance deployment. Horizontal scaling requires sticky routing,
    shared state, or a redesigned handoff; no durable search-session persistence
    or provider inventory is introduced.
  - unresolved: none.
- ADR status: accepted ADR 0014 owns the on-demand dossier weather-evidence
  boundary. ADR 0015 is required and records the accepted process-local
  evaluated-baseline handoff. If implementation adopts a router library,
  persists or shares search state, scales to multiple web processes without an
  approved routing/state design, stores full catalog/trust snapshots, adds
  provider acquisition, or moves ranking/evidence interpretation to the client,
  pause for a new decision and reassess ADR need.
- Advisory design-review:
  - reviewers: Product / Strategy, Backend / API, Data Trust & Source
    Integrity, UI / UX, Security & Privacy, Observability / Ops, Accessibility,
    Performance, Monetization / Partnerships
  - status: completed on 2026-07-16 for the consolidated full-flow revision; no
    Blocker or High finding remains open
- Original advisory feature-review:
  - reviewers: Product / Strategy, Backend / API, Data Trust & Source
    Integrity, UI / UX, Security & Privacy, Observability / Ops, Accessibility,
    Performance, Monetization / Partnerships
  - status: completed on 2026-07-16; approved with Blocker: 0 and High: 0.
    The two worthwhile Medium residuals are tracked in `docs/product-backlog.md`:
    weather-evidence outcome metrics and scope-aware `pass_terrain_value`
    wording.
- Follow-up advisory review:
  - exact-state feature-review completed on 2026-07-17 after all implementation
    fixes; no Blocker, High, Medium, or Low finding remains open.

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
| Technical | Reusable UI foundation | One-off global CSS and repeated markup make responsive and semantic states drift | Keep page-local markup; full shadcn migration; small Snowcast-owned primitives | Small Snowcast-owned primitives, with selective headless primitives only when interaction complexity justifies them | Encodes brand geometry and accessibility states without re-theming the application or forcing every section into a generic card | This spec and follow-up plan |
| Mixed | Refinement availability | An empty queue currently conflates no useful question with LLM or validation failure | Silent empty state; always ask; explicit status plus validated fallback | Explicit status and one registry-backed factor fallback only after existing materiality validation | Keeps questions useful and truthful while removing provider variability from the primary workflow | This spec, Search V4 model docs, and follow-up plan |
| Technical | Refinement request boundary | Optional remote-model latency blocks ranking, while repeated evaluation can drift from the exact ranked view | Keep refinement inline; rerun from canonical intent; store a lightweight evaluated baseline; persist or share full state | Load after ranking from a typed process-local evaluated-baseline snapshot with a 60-second TTL and 64-entry maximum | Keeps ranking fast and failure-isolated while preserving exact-view materiality and preview consistency; temporary unavailability is accepted when the handoff is gone | ADR 0015, this spec, and follow-up plan |
| Technical | Refinement admission policy | A separate anonymous endpoint can repeat deterministic and paid provider work after browser cancellation | No guard; require auth; application-local limits; shared managed limiter | Application-local two-concurrent, six-per-minute-per-client, burst-two guard for the current single machine | Protects current provider capacity without changing anonymous search; reset and per-machine limitations are explicit and require replacement before scale-out | ADR 0015, this spec, and follow-up plan |
| Product / Domain | Decision evidence hierarchy | Internal provenance summaries are accurate for diagnostics but artificial and difficult for travellers to interpret | Keep ledger; compact evidence table; plain-language summary with raw details collapsed | `Why this trip` summary with strengths, uncertainties, and collapsed technical provenance | Makes trust evidence understandable without hiding auditable source detail | This spec and follow-up plan |
| Technical | Weather chart implementation | The hand-built SVG lacks axes, tooltips, threshold context, and robust gap handling | Extend local SVG; use a low-level visualization toolkit; add Recharts | Add Recharts and keep the accessible data table | Improves chart semantics and responsiveness while retaining typed server data as the only source | This spec and follow-up plan |
| Product / Technical | Weather chart units | Plotting depth, snowfall, and temperature together makes scales and visual comparison ambiguous | Multi-axis chart; normalized values; separate metric views | Segmented Snow depth / Fresh snow / Temperature views | Keeps each view interpretable without hiding any typed metric or inventing normalization | This spec and follow-up plan |
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
  dependency was introduced by the original implementation.
- The follow-up adds Recharts as the only chart dependency. It receives typed
  historical and forecast points from the weather-evidence endpoint and never
  derives, interpolates, or fabricates weather observations.
- Snowcast owns a small internal UI layer under `frontend/src/ui`. Primitives
  expose semantic variants and stable accessibility behavior; feature
  components remain in `frontend/src/search`. A full shadcn migration is not
  part of this increment.
- Search V4 owns refinement availability and fallback selection. The AI module
  reports whether proposal generation produced questions, found none, or was
  unavailable; the domain fallback resolves approved factor-answer IDs through
  the versioned presentation registry and reuses the existing deterministic
  materiality validator.
- The LLM selects registered factor topics and approved answer IDs and writes
  only a bounded question from selected-topic approved vocabulary. The server
  owns reason copy, option labels, descriptions, typed actions, and deterministic
  fallback for unsafe, sensitive, unsupported, or ungrounded question text.
  Group-priority refinement questions are outside this slice.
- After deterministic ranking, `POST /api/search` stores the minimum typed
  evaluated baseline needed for refinement validation and previews in a
  thread-safe, process-local LRU/TTL store. Entries live for 60 seconds and the
  store holds at most 64. It does not retain a full catalog/trust snapshot,
  brief, or provider secrets.
- `POST /api/search/refinements` consumes only the exact stored baseline bound
  to both the public baseline fingerprint and the SHA-256 digest recomputed from
  canonical request intent. The full intent is not stored, and there is no
  separate typed-equality check. A missing, expired, evicted, restarted, or
  mismatched handoff is
  `temporarily_unavailable`; it triggers neither deterministic search nor
  Gemini.
- The process-local handoff is accepted only for the current single-instance
  deployment. Horizontal scaling requires sticky routing, shared state, or a
  redesigned handoff.
- The frontend projects response-shaped `SearchIntent` values back to the
  request schema before calling the weather-evidence endpoint. Computed
  response fields never cross the request boundary.
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
- two to five bounded options with one-line tradeoffs;
- selected option state;
- structured impact preview when available;
- `Apply and rerank` or truthful `Keep current ranking`, plus `Skip for now`.

At the existing single-column breakpoint, the eyebrow and concrete question
remain visible while the answer body starts collapsed behind a real `Choose a
preference` disclosure. Opening it reveals the server-owned reason, options,
preview, and actions and focuses the first radio. Desktop remains expanded.
Replacing the current question resets the narrow disclosure to collapsed, and
recommendations remain reachable without opening it.

Search V4 may return several validated refinement questions. The results rail
shows one primary question at a time and keeps the remaining questions in a
bounded client-side queue. Applying, skipping, or dismissing the current
question advances to the next still-relevant question. Applying a question
reruns Search V4 first, then starts a new refinement request from the returned
applied intent and newly stored baseline. The new queue replaces unanswered
questions from the previous request rather than carrying stale refinements
forward.

The refinement rail is a progressive state. It initially says
`Checking whether one answer could improve this ranking.`; after 2.5 seconds it
changes to `Your ranking is ready. Snowcast is checking whether one answer could
improve it.` without cancelling the request. A bounded admission `429` with a
valid `Retry-After` of at most 15 seconds enters `retrying`, waits, and retries
once while the results remain usable. Success resolves to a validated question
or `No follow-up would materially change these results.` A terminal optional
failure is announced politely without a visible persistent error or refinement
card. Results remain fully interactive in every refinement state.

The baseline snapshot's 60-second TTL limits only how long the server accepts
the ranking-to-refinement handoff for question generation. Once delivered, a
question and its typed patches remain answerable after that TTL. Applying the
answer starts a full rerank, which creates a new snapshot before the client asks
for the next question. A deliberate ranking refresh does the same. Cache loss
or expiry can remove optional refinement, but never makes the visible ranking
unusable.

Selecting an option does not immediately mutate the applied intent. The UI
enters a preview state. Applying sends the option's typed patches to Search V4.
Clearing the preview returns to the unselected state.

One validated baseline option may reproduce the current intent when another
option is materially distinct. The response exposes `intent_changed` for every
option. A false value uses baseline-preserving preview and action copy, records
the question as answered, advances the queue, and does not issue an unnecessary
rerank or announce ranking movement.

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
9. plain-language `Why this trip`, collapsed source/calculation details, and
   collapsed scoring details;
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

### Conditional Snow And Weather Evidence

Snow and weather evidence is tied to the requested window and selected ski
area. It is a decision summary, not a raw weather dashboard. The section starts
with a compact conclusion, representative elevation, and evidence mode. It then
shows a stable metric row for the values that exist, followed by one chart and
progressively disclosed source detail.

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

Chart presentation requirements:

- provide segmented `Snow depth`, `Fresh snow`, and `Temperature` views and
  plot only one unit with one labelled Y axis at a time;
- use labelled date and value axes, a responsive tooltip, and a labelled 30 cm
  planning reference when snow depth is available;
- render the historical interquartile range as a range area and median as a
  separate line; forecast snow depth, snowfall, and temperature remain
  distinguishable by label and line/area treatment rather than color alone;
- preserve null values as visible gaps and never connect a line across missing
  observations;
- emit and display one ordered row per requested date or month-day; a date with
  no stored observation remains present with null values rather than
  disappearing from the timeline;
- keep source, climatology baseline, issued-at time, freshness, and coverage in
  a compact provenance strip or disclosure rather than a paragraph of internal
  metadata;
- show limitations in a semantic warning state and remove implementation terms
  such as `typed evidence` from traveller-facing copy.

### Why This Trip

The former `Evidence ledger` becomes `Why this trip`.

The default view contains:

- `What supports this choice`: up to four deterministic, plain-language
  findings derived from the selected configuration's factor results, access,
  pass, and stay estimate;
- `What remains uncertain`: deduplicated material limitations and warnings;
- `Sources and calculation details`: a collapsed disclosure containing factor
  labels, technical provenance summaries, source-reference counts, evidence
  caps, selected-pass scope, access anchors, and lodging provenance for users
  who need audit detail.

The primary findings never expose raw factor IDs, trust enums such as
`verified_with_adjustment`, or phrases such as `Catalog field-group evidence`.
Technical provenance remains verbatim only inside the explicitly technical
disclosure.

### Reusable UI Foundation

Repeated interface behavior is encoded in Snowcast-owned primitives rather
than copied page markup. The initial foundation covers buttons, icon buttons,
badges, alerts, metric tiles, section headings, disclosures, segmented tabs,
and async states. Each primitive has semantic variants, keyboard/focus
behavior, stable dimensions, and focused component tests.

Domain components such as recommendation cards, refinement cards, evidence
summaries, and snow/weather panels compose these primitives. The foundation
does not introduce a generic card abstraction, force page sections into nested
cards, or replace existing feature ownership.

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

The application canvas uses one restrained horizontal/diagonal blend from
creamy alpenglow at the upper-left, through snow white in the content center,
to powder blue at the upper-right and lower edge. It replaces disconnected
solid side bands. White and ice content surfaces retain sufficient contrast;
the gradient never appears inside status badges, evidence cells, or charts.

Typography remains Sora for compact headings and Manrope for body and controls.
Use stable metric-cell widths and no viewport-scaled font sizes.

## API And Client Contract

Ranking endpoint:

- `POST /api/search` remains the Search V4 request and rerank boundary and does
  not invoke an LLM. After deterministic ranking it stores a typed, lightweight
  evaluated-baseline snapshot and returns its public baseline fingerprint.

Post-search refinement endpoint:

- `POST /api/search/refinements` accepts the canonical `applied_intent`, the
  brief, answered question IDs, and public baseline fingerprint after ranking
  has rendered;
- it loads the exact evaluated baseline stored by `POST /api/search` and accepts
  it only when the stored fingerprint and the SHA-256 digest recomputed from the
  request's canonical intent both match. Canonical serialization supplies the
  equality binding; no full intent is stored and no second typed-equality check
  occurs. The public fingerprint alone is not trusted;
- it never reruns deterministic search. A missing, expired, evicted, restarted,
  or mismatched baseline returns `temporarily_unavailable` without invoking
  Gemini;
- it returns `search_model_version`, `ranking_policy_version`,
  `refinement_presentation_policy_version`, `baseline_fingerprint`,
  `baseline_status`, `refinement_status`, orthogonal `fallback_used`, and a
  bounded `refinements` queue;
- the client cancels or ignores a stale request when the active applied intent
  changes and suppresses a response that does not belong to the visible
  ranking;
- `/api/search` temporarily accepts legacy refinement request fields but ignores
  them and returns `refinements: []` so current web/mobile clients remain
  compatible during migration.

Required response extension:

- each validated `RefinementOption` may include a deterministic preview;
- the preview is computed from server-side variant ranking simulation;
- preview construction reuses the stored candidate evaluations and variant
  simulation; it must not add another LLM call or repeat catalog/database
  acquisition;
- the dossier may request one typed, display-ready weather summary for the
  selected configuration's ski area and the current applied intent;
- the client never recomputes scores or eligibility;
- the refinement response includes `refinement_status` so an empty
  `refinements` array is not ambiguous.

Proposed client contract:

```text
RefinementOption.preview?:
  top_rank_changes:
    - ski_region_id
      previous_rank: integer or null
      preview_rank: integer or null
  eligible_candidate_count_delta: integer

SearchV4RefinementResponse.refinement_status:
  questions_available | not_needed | temporarily_unavailable
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
- the optional preview field does not break clients that ignore it;
- the ranked response remains usable while refinement is loading, fails, or is
  unavailable;
- the evaluated-baseline store is thread-safe and process-local, expires entries
  after 60 seconds, evicts the least-recently-used entry when insertion would
  exceed 64 entries, and retains only the canonical intent SHA-256 digest, not a
  full `SearchIntent`, origin text, full `CatalogSnapshot`,
  `CatalogTrustManifest`, brief, or provider secrets;
- the 60-second TTL is only the ranking-to-refinement server handoff. A delivered
  question remains answerable after expiry;
- applying a delivered answer reruns full search with the updated intent, stores
  a new baseline, and immediately requests the next refinement from that new
  snapshot; a deliberate ranking refresh also creates a new snapshot;
- `questions_available` requires at least one validated refinement;
- `not_needed` requires an empty refinement list and no material deterministic
  fallback;
- `temporarily_unavailable` requires an empty refinement list because the exact
  baseline handoff is unavailable/mismatched or provider/output failure has no
  material deterministic fallback;
- a deterministic fallback may emit at most one question, uses registered
  clarifiable factor topics and authoritative approved answer copy/actions, and
  must pass the existing option validation and material-impact simulation before
  serialization;
- the user-facing refinement request performs at most one provider attempt;
  snapshot lookup, provider work, and fallback validation share one five-second
  monotonic deadline from route ingress;
- missing, expired, evicted, restarted, or mismatched baseline requests invoke
  neither deterministic search nor a provider; zero-result baselines invoke no
  provider;
- application-local admission allows at most two concurrent requests and six
  requests per minute per client with burst two; a bounded `429` is returned
  before snapshot lookup, and client identity is never a telemetry label;
- the browser waits for a valid `Retry-After` of at most 15 seconds and retries
  one admission `429` once; a second `429` or other terminal discovery failure
  leaves results usable and does not render a persistent error card;
- malformed provider response JSON maps to a bounded provider failure and never
  escapes as an unhandled exception or appears in public error text.

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
- `SearchV4Configuration.evidence_profile` owns that three-value distinction
  in the backend. The client maps the typed profile to presentation copy and
  never infers it from generic factor warnings or provenance strings.
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
- approved refinement answer labels, descriptions, and typed intent actions;
- presentation safety fallback for unsuitable generated question copy;
- per-option rank preview simulation;
- impact-copy templates;
- weather-evidence mode selection, aggregation, interpretation templates, and
  limitation labels;
- evidence and estimate labels.

The LLM dynamically selects registered factor topics, writes a question from
the selected topics' approved vocabulary, and selects approved answer IDs rather
than emitting labels or raw patches. The server owns reason copy, resolves each
answer ID to authoritative presentation copy and typed intent actions, replaces
unsafe or ungrounded wording with deterministic fallback, and then runs the
existing legality, actionability, and materiality gates. Group-priority patches
remain part of Search V4 but are not generated as refinement questions in this
slice. The LLM does not generate recommendation explanations, metric values,
rank changes, dossier facts, reason/option copy, or executable patches.

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
- One bounded admission retry uses a compact `retrying` status while keeping the
  board interactive. Terminal optional discovery failure is announced through
  the polite status region and leaves no visible error/refinement card.
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
- Refinement is rate-limited separately from ranking, performs one provider
  attempt within a five-second hard budget, and records no brief, prompt,
  response, question text, question ID, token, or provider error body.
- The evaluated-baseline store retains only the canonical intent SHA-256 digest,
  not a full `SearchIntent`, origin text, full `CatalogSnapshot`,
  `CatalogTrustManifest`, brief, provider credential, prompt, token, response,
  or other provider secret. Fingerprints are identifiers, not authorization or
  proof of a matching canonical intent digest.
- The process-local store is valid for the current single-instance deployment
  only; horizontal deployment requires approved sticky routing, shared state,
  or a redesigned handoff.

## Observability And Operations

Useful aggregate events:

- homepage search submitted and bounded clarification shown;
- recommendation expanded/collapsed by rank;
- dossier opened by rank;
- dossier recommendation switched by source rank and destination rank;
- dossier navigator collapsed/expanded;
- weather evidence view changed between forecast and historical context;
- refinement preview selected, applied, cleared, failed;
- bounded evaluated-baseline outcome: `hit`, `miss`, `expired`,
  `intent_mismatch`, or `evicted`;
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
- A successful ranking stores a lightweight evaluated baseline for at most 60
  seconds in the process-local 64-entry LRU store without retaining the full
  intent or origin text, catalog/trust snapshot, brief, or provider secrets.
- Refinement uses only a stored baseline matching both the public fingerprint
  and the SHA-256 digest recomputed from canonical request intent. Miss,
  expiry, eviction, restart, or mismatch yields typed `temporarily_unavailable`,
  performs no deterministic search or Gemini call, and leaves the ranking
  usable.
- A delivered refinement remains answerable after snapshot expiry. Applying it
  reruns full search with the updated intent, stores a new baseline, and starts
  the next refinement request from that snapshot.
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
- Applying a changed refinement reranks in place and announces changed
  positions; applying a typed baseline option preserves the current ranking
  without a request.
- Search remains usable without refinement generation or preview metadata.
- Refinement presents a dynamic traveller-facing question as the heading, two
  to five keyboard-operable approved options, no internal factor/group/ranking
  vocabulary, and no persistent terminal discovery-failure card. Narrow
  tablet/mobile layouts keep the question visible, collapse the optional answer
  body by default, and preserve recommendation reachability.
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

- ranking stores the typed lightweight evaluated baseline after deterministic
  evaluation and excludes full catalog/trust snapshots, brief, and provider
  secrets;
- snapshot lookup requires a matching fingerprint plus the SHA-256 digest
  recomputed from canonical request intent; canonical serialization supplies the
  equality binding without a stored full intent or second typed-equality check;
- hit, miss, expiry, LRU eviction when inserting at the 64-entry capacity,
  process reset, and concurrent access preserve the typed store and endpoint
  invariants;
- miss, expiry, eviction, restart, and canonical-intent digest mismatch return
  `temporarily_unavailable` without deterministic search or Gemini;
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

- a delivered question remains applicable after the server snapshot TTL, and
  applying it reranks before immediately requesting the next refinement from
  the new baseline;
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
- Feature-review status: completed on 2026-07-16 and approved under the
  advisory gate (Blocker: 0, High: 0).
- Follow-up feature-review status: pending on the exact implementation head.
- Original outcome: implemented after owner review, exact-head remediation, and
  final verification recorded in the implementation plan.
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
- Feature-review findings resolved during implementation:
  - [Blocker] terrain evidence now preserves its owning pass, terrain-domain, or
    selected-ski-area scope and its field-level trust status rather than
    presenting an estimated ski-area value as unqualified pass terrain.
  - [High] the responsive post-search header retains `Current trip`; dossier
    routing preserves the displayed selected alternative; filter-drawer focus
    remains contained and stable through controlled edits; and dossier return
    restores a deliberate results focus target.
  - [Medium] mixed elevation and forecast-coverage wording, scoring-detail
    `Estimated` / `Needs source` labels, and the remaining focused review
    findings are resolved.
- Tracked feature-review residuals:
  - [Medium] add bounded weather-evidence outcome metrics and an OTLP smoke
    check so typed HTTP-200 unavailable responses are visible to operators;
  - [Medium] make `pass_terrain_value` wording scope-aware and assert pass,
    terrain-domain, and selected-ski-area numerators while retaining the trust
    qualifier.
- Known residual risks:
  - expanded cards can produce long pages when many results are opened;
  - practical metrics depend on uneven catalog and provider coverage;
  - exact refinement previews require a new structured response field;
  - browser-session return-state preservation needs careful history handling;
