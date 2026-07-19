# Feature Spec: Product Language Audit Remediation

## Status

- Status: accepted
- Owner: solo-builder
- Related docs:
  - `docs/advisory-reviews/2026-07-19-content-language-domain-audit.md`
  - `docs/domain-language.md`
  - `docs/snow-evidence-model.md`
- Related plan:
  - `docs/superpowers/plans/2026-07-19-product-language-audit-remediation.md`
- Related ADRs:
  - `docs/architecture/adr/0017-use-stable-public-api-error-codes.md`

## User Outcome

Snowcast should explain trip choices in direct, natural American English that a
non-native English speaker can understand without knowing the ranking model.
Web and mobile users should see the same concepts, honest booking scope, useful
weather evidence, and safe recovery guidance instead of internal identifiers or
raw backend failures.

## Scope

In scope:

- Use `Trip option`, `Trip details`, and `Must-haves` as the public terms while
  leaving internal model and database identifiers unchanged.
- Rewrite Search V4 controls, result explanations, refinements, current-trip
  summaries, public destination pages, and the README product introduction in
  B2-level American English.
- Keep each refinement question about one decision and suppress repeated topics.
- Make the accommodation handoff state that the provider searches the broader
  destination; present the recommended stay base as planning guidance only.
- Return stable public error codes from customer-facing API failures and map
  them to platform-specific recovery copy in web and mobile.
- Bring Flutter screens to customer-facing language parity and prevent raw API,
  auth, transport, validation, or decoding details from rendering.
- Keep useful weather facts in the primary trip view: historical snow depth,
  forecast snowfall and temperature when available, number of historical
  seasons, freshness or confidence, and a readable data-backed chart.
- Label 30 cm as `30 cm snow-depth reference` and explain: `This reference helps
  compare modeled snow depth. It does not show snow coverage, open ski runs,
  comfort, or safety.`
- Show plain reasons for a recommendation first. Keep raw scoring weights,
  identifiers, points, caps, statistical methods, source rows, and calculation
  internals behind an advanced technical disclosure.
- Replace JSON errors on public HTML destination routes with a branded HTML 404.

Out of scope:

- Changing ranking weights, candidate selection, refinement semantics, or
  internal domain identifiers.
- Making the accommodation provider query stay-base-specific or adding hotel
  inventory.
- Adding weather facts to recommendation cards through new request fan-out or a
  larger search response.
- Localization beyond defining a language-neutral error-code boundary.
- Adding web-only features such as refinements, the detailed weather dossier,
  or accommodation handoff to Flutter. Mobile parity means language, error,
  and recovery parity on existing Flutter search and current-trip surfaces.
- Rebuilding the Flutter architecture beyond the smallest reusable copy and
  error-mapping seams needed for parity.

## Product Fit

- The language emphasizes Snowcast's differentiator: choosing a ski trip for a
  travel window using snow, mountain, stay, travel, and evidence quality.
- Estimated, missing, stale, limited, forecast-assisted, and archive-backed
  evidence remains explicit.
- Destination-level accommodation search is described honestly, avoiding a
  hotel-marketplace claim Snowcast cannot yet fulfill.
- Technical detail remains inspectable without dominating the planning flow.

## Domain Model

- Bounded contexts touched: Planning, Conditions and Weather Evidence,
  Companion, Booking Handoff, AI Orchestration and Assistance, and public API.
- Domain terms changed only at the public-language boundary:
  - public `Trip option` maps to internal `trip configuration`
  - public `Trip details` maps to the recommendation dossier/detail view
  - public `Must-haves` maps to hard constraints
- New contract concept: public API error code.
- Invariants:
  - public copy never changes ranking or typed refinement patches
  - raw exception text and internal IDs never render in a customer interface
  - error codes are stable, language-neutral, and safe to expose
  - every client has a safe fallback for an unknown code
  - weather charts use response values rather than decorative sample data
  - evidence availability is distinct from expected snow conditions
  - booking copy matches the provider query's destination-level scope
  - `evaluated_at` is request evaluation time and is never labelled data
    freshness
- `docs/domain-language.md` and `docs/snow-evidence-model.md` must stay aligned.

## Decision and Review Gate

- Classification: review-gated, full design flow
- High-risk domains touched: shared API contracts, evidence/trust wording,
  public booking claims, mobile companion behavior, and user-facing errors
- Developer Decision Checkpoints:
  - resolved: public vocabulary, American English, destination-level booking
    scope, mobile parity, weather-detail split, technical scoring disclosure,
    factual 30 cm explanation, stable error codes with client-owned messages,
    atomic client/server migration, and mobile session/partial-data recovery
  - accepted assumptions: internal identifiers and API success payloads remain
    stable; no recommendation-card weather response expansion
  - unresolved: none
- ADR status: required; ADR 0017 records the public-error contract
- Advisory design-review:
  - reviewers: content-language, UI/UX, mobile companion, backend/API,
    data-trust/source-integrity, accessibility
  - status: completed; all six lanes approved exact head `a5b5855` after the
    accommodation-boundary follow-up
- Advisory feature-review before final handoff:
  - reviewers: same scoped reviewers plus final whole-branch review
  - status: planned

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Product / Domain | Public planning vocabulary | Users should not need internal ranking vocabulary | Trip option/configuration; Trip details/dossier; Must-haves/hard constraints | `Trip option`, `Trip details`, `Must-haves` | Clear public language; retain precise internal names in code and technical disclosures | `docs/domain-language.md` |
| Mixed | Accommodation scope | Copy must match the external provider query | Stay-base claim or destination-level truth | Keep destination-level and explain the recommended base separately | Honest and low-risk; provider precision remains a future capability | this spec |
| Mixed | Evidence disclosure | Useful facts and trust limits must remain visible without overwhelming the primary flow | All detail primary, all detail hidden, or layered disclosure | Useful facts primary; methods and raw calculations advanced | Preserves Snowcast's evidence advantage while reducing cognitive load | `docs/snow-evidence-model.md` |
| Technical | Public error ownership | Two clients must not display raw server failures | Stable codes/client copy; status mapping; server-owned final messages | Stable backend codes with client-owned messages | Best long-term boundary; requires typed fallbacks and an atomic client/server release | ADR 0017 |
| Mixed | Mobile recovery | Authentication and secondary failures must not destroy useful state | Keep failure state local or replace the whole screen | Expired sessions return to sign-in; secondary failures preserve loaded trip data with an inline retry | Predictable and resilient; requires independent summary, event, and action states | this spec |
| Product / Domain | 30 cm chart marker | The data measures modeled point snow depth, not piste coverage | Ski-cover label, factual depth label, or removal | `30 cm snow-depth reference` with an explicit limitation | Preserves the comparison while avoiding unsupported skiability claims | `docs/snow-evidence-model.md` |

## Architecture Decisions

- Backend errors expose a stable, language-neutral code; web and mobile own
  customer-facing messages and recovery actions.
- A shared documented glossary defines concepts, while TypeScript and Dart keep
  platform-local typed copy maps. Runtime cross-language copy sharing and
  code-generation are intentionally avoided.
- Backend-authored current-trip prose remains limited to factual B2-level
  summaries and event descriptions shared by both clients. Clients own labels,
  actions, state names, and recovery guidance. Recommendation and weather
  interface explanations are derived from typed data in the web presentation
  layer.
- ADR needed: ADR 0017.
- Revisit error localization or generated client contracts when Snowcast ships
  another language or additional external clients.

## API and Client Contract

- Customer-facing failures use exactly `{"error":{"code":"<code>"}}`. The
  response contains no `detail`, message, validation path, or request ID.
- Backend, web, and Flutter change atomically. There are no deployed users and
  no legacy error-body compatibility requirements.
- Existing HTTP statuses remain unchanged. Each public code has exactly one
  status; several codes may share a status. Unsupported methods use
  `method_not_allowed` with HTTP 405 and retain headers such as `Allow`. ADR 0017
  owns the initial registry.
- A typed public exception plus application handlers cover explicit domain
  errors, dependency/auth failures, FastAPI request validation and malformed
  JSON, remaining HTTP exceptions, and unexpected failures for customer routes.
- The JSON contract covers every non-operational `/api/*` route except the
  accommodation browser-navigation boundary. Unknown routes return the bounded
  `not_found` envelope. Operational `/api/healthz`, `/api/readyz`, and
  `/api/search-readiness` retain their diagnostic contracts and are not consumed
  by customer clients.
- `/api/outbound/accommodation` and all descendant paths remain a direct
  browser-navigation boundary: valid requests return the existing provider
  redirect; missing or extra path segments, unsupported methods, and invalid or
  stale requests return a branded HTML recovery page while preserving the
  original status and headers. It never displays JSON to the browser.
- Web and Flutter parse only the code. Unknown, absent, malformed, non-JSON,
  transport, and decoding failures use an operation-specific safe fallback.
- Success response schemas and internal enum values remain unchanged.
- Public destination 404 responses remain HTTP 404 but return branded HTML with
  a document title, main heading, and return-to-search link.

### Operation Recovery Matrix

| Operation | Preserve | Message placement | Action | Accessibility behavior |
| --- | --- | --- | --- | --- |
| Initial or updated search | Keep the last successful results when present; keep the entered trip brief and filters | Results heading area | `Try again` | Visible alert; do not move focus away from the search control |
| Refinement discovery | Keep results, applied intent, answered topics, and unsubmitted drafts | Refinement rail/card | `Try again` and `Keep these results` | Announce one terminal status; keep focus on the triggering control |
| Apply refinement | Keep current results and the selected answer | Refinement card | `Update results` retry and `Keep these results` | Associate the error with the question; keep the selection perceivable |
| Weather evidence | Keep the trip details page and every other section | Snow and weather section | `Try again` | Inline alert labelled with the ski area; no route focus reset |
| Invalid accommodation handoff | Keep the browser on a Snowcast-branded recovery page | Recovery-page main region | `Return to trip details` | Descriptive document title, main heading, and keyboard-reachable return link |
| Sign-in attempt | Keep the sign-in screen | Sign-in form | `Try again` | Visible and announced once; sign-in remains reachable |
| Expired mobile session | Clear persisted session and protected current-trip state | Sign-in screen | `Sign in` | Announce the session-ended state, then focus the sign-in heading |
| Current-trip primary load | Keep any loaded summary; otherwise show a bounded empty/error state | Current-trip main region | `Try again` | Main-region alert without replacing global navigation |
| Current-trip events or mark-checked | Keep the loaded trip summary and prior events | Affected subsection/action | `Try again` | Inline live status; do not replace or refocus the whole screen |

Unknown codes follow the row for the operation that produced them.

## Public Language Contract

| Concept | Public wording |
| --- | --- |
| Ranked candidate | `Trip option` |
| Detail route | `Trip details` |
| Hard constraints | `Must-haves` |
| Soft factors | `Preferences` |
| Optional refinement | `One more question` |
| Apply a refinement | `Update results` |
| Stop refining | `Keep these results` |
| Date-specific snow assessment | `Snow fit for your dates` |
| Snow states | `Strong fit`, `Some concerns`, `Not enough evidence` |
| Positive/negative explanation | `Why it fits`, `Main concern` |
| Stay-base guidance | `Recommended place to stay` |
| Provider handoff | `Search stays in <destination>` |
| Saved planning state | `Current trip` |
| Companion events | `Trip updates` |
| Technical disclosure | `Technical calculation details` |

Internal-only primary-flow terms include `configuration`, `dossier`, `hard
constraint`, `ranking`, `rerank`, `eligible configurations`, factor/group IDs,
numeric quality tiers, `selected pass context`, `adjusted`, `evidence ledger`,
`comparison baseline`, `notification eligible`, and `suppressed`. Exact model
terms may appear only inside the advanced technical disclosure when necessary
to inspect a calculation.

Every refinement question stands alone and asks one decision. Its options
directly answer the question, are mutually exclusive and comparable, and
explain the consequence in B2 American English without changing registered IDs
or typed patches.

## Trip Details Information Hierarchy

`Trip details` uses one primary explanation and this order:

1. Overview: selected trip option, fit, snow fit, one concrete `Why it fits`,
   and one `Main concern` when present.
2. Snow and weather: always-visible summary plus charts and tables.
3. Trip option: destination, ski area, recommended place to stay, pass, access,
   cost estimates, and alternative options.
4. Accommodation: destination-level provider search with stay-base guidance.
5. Why this trip: one plain evidence list; this replaces the evidence-ledger
   presentation and does not repeat the overview verbatim.
6. `Technical calculation details`: one disclosure, collapsed by default,
   containing raw factor weights, points, caps, policy/version IDs, trust-state
   internals, statistical methods, and source-row detail.

On a collapsed 390 px result card, the destination/stay, fit, snow-fit/evidence
cue, and one plain rationale remain visible. Expansion reveals supporting facts,
alternatives, actions, and technical detail.

## Data Trust and Source Integrity

- Existing forecast, climatology, catalog, and provider sources remain
  unchanged.
- Primary weather copy identifies archive versus forecast evidence and keeps
  source type, currency, coverage, evidence strength, and expected conditions
  as separate concepts.
- `30 cm snow-depth reference` is a comparison aid for modeled point snow
  depth. The agreed limitation is visible text and is not only a chart line.
- Missing values render as plain limitations, not `Unknown` without context.

### Weather Presentation Matrix

| Concept | Archive / climatology | Forecast-assisted |
| --- | --- | --- |
| Source type | `Historical pattern` | `Forecast and historical pattern` |
| Currency | Latest archive year and baseline years when available; never `evaluated_at` | Forecast issue time plus latest archive year; never `evaluated_at` |
| Coverage | Historical seasons and requested-date profile coverage | Usable forecast dates out of requested dates, plus historical seasons |
| Expected conditions | Historical median depth, typical snowfall, and temperature for the requested window | Forecast snowfall/temperature for covered dates, with historical depth context |
| Main limitation | Limited seasons, mixed source/elevation, or unavailable metric | Partial dates, mixed sources/elevation, or forecast unavailable for some dates |
| Chart | Historical depth profile with accessible values table and the 30 cm reference | Forecast daily snowfall/temperature plus historical depth context; metric switch is keyboard operable |

Forecast `issued_at` and archive `latest_archive_year`/baseline fields own
currency. `evaluated_at` and `cache_valid_until` are request/cache metadata and
never appear as source freshness.

### Recommendation Claim Eligibility

- `verified`: may support a direct factual claim with its source scope.
- `verified_with_adjustment`: state the resulting fact and explain the
  adjustment only in technical details; do not label the public fact
  `adjusted`.
- `estimated`: use `estimated`, `about`, or a range in the visible claim.
- `needs_source`: do not use as a positive reason; show a plain limitation when
  material.
- Mixed evidence: make only the narrow claim supported by all contributing
  sources and disclose mixed provenance in technical details.
- Missing evidence: omit the claim and state that the fact is unavailable when
  the omission affects the decision.
- Do not infer that glacier terrain or snowmaking `adds resilience` unless typed
  ranking evidence explicitly supports that claim for the requested window.

## AI / LLM Use

- No new LLM use.
- Refinement wording remains registry-owned and deterministically validated.
- Question and answer IDs plus typed patches remain unchanged while visible copy
  is rewritten.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| N/A | N/A | N/A | No new asynchronous work |

## Security, Privacy, and Abuse

- Raw auth-provider failures, validation internals, policy IDs, and exception
  text must not cross the customer-facing error boundary.
- Request identifiers are omitted from response bodies in this migration.
- Authentication and rate-limit policy remain unchanged. Flutter now clears an
  unknown or expired stored session after `session_expired` and returns to the
  sign-in screen.

## Observability and Operations

- Server logs retain the internal failure class and safe request correlation;
  public code is logged as a bounded field.
- No user-entered trip brief or raw provider response becomes a metric label.
- Client fallback handling must work for network, decoding, validation, auth,
  not-found, rate-limit, and server failures.

## Acceptance Criteria

- A customer can understand search controls, refinements, recommendations,
  weather evidence, accommodation scope, and current-trip state without knowing
  internal Snowcast terminology.
- No audited public web, mobile, or destination-page surface displays the banned
  internal terms or raw backend details identified by the domain audit.
- Every refinement question stands alone, asks one decision, and does not repeat
  an answered topic.
- Web and mobile map stable error codes to safe recovery copy and handle unknown
  codes without exposing `detail`.
- Main weather evidence shows real response data and the agreed 30 cm caveat;
  technical methods and raw scoring remain reachable through an advanced
  disclosure.
- Accommodation handoff promises only a destination-level provider search.
- Desktop and 390 px mobile views have no overlap, clipped actions, or
  inaccessible disclosure controls.
- Errors are visible without color, announced once by web and Flutter semantics,
  and paired with labelled recovery actions without unexpected focus movement.
- Drawer Escape/focus return, tab/disclosure keyboard operation, refinement
  replacement, route-heading focus, and public-404 navigation remain intact.
- Weather charts retain a programmatic summary, equivalent values table,
  keyboard-operable metric switching, and visible text for the 30 cm limitation.
- Flutter screens reflow at enlarged text scale, use platform-standard touch
  targets, and expose semantic control names and states.

## Verification

- Unit tests: complete backend error registry/status/OpenAPI coverage,
  refinement registry, weather wording and policy, public-page HTML, TypeScript
  presentation/copy, Dart copy/error map, and Flutter state/semantics.
- API/integration tests: every registered 401/404/422/429/500/503 pairing,
  malformed JSON, booking redirect contract, search/refinement behavior, and
  current-trip failures.
- UI/manual checks: search, one and multiple refinements, all result cards,
  trip-detail disclosures, booking handoff, current trip, mobile errors, public
  404, full keyboard path, chart alternatives, and enlarged mobile text.
- Operational checks: backend suite, Ruff, frontend Vitest/build/Playwright,
  Flutter analyze/test/build smoke where environment permits.

## Advisory Review

- Design reviewers: content-language, UI/UX, mobile companion, backend/API,
  data-trust/source-integrity, accessibility
- Feature reviewers: same scoped reviewers plus whole-branch review
- Known residual risks: platform-local copy can drift; contract and forbidden-
  term tests plus the shared glossary are the chosen controls.
