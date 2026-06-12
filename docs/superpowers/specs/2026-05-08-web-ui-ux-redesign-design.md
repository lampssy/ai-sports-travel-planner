# Snowcast Web UI/UX Redesign Design

## Summary

Redesign the React web app as Snowcast's premium planning and demo surface. The web experience should make the product immediately understandable, then turn into a serious ski-trip planning workspace after search.

The target posture is:

- demo-grade first impression
- workflow-grade search core
- evidence-backed recommendation cards
- selected-resort detail as a recommendation dossier
- current-trip view as a lightweight companion preview

This design does not change backend ranking, API semantics, data models, authentication, or booking-provider integration. It defines the target UI/UX and visual system for later implementation.

Updated review-aligned visualization references live in:

- `docs/ui-concepts/2026-05-30-review-guidelines/01-search-results-board.png`
- `docs/ui-concepts/2026-05-30-review-guidelines/02-selected-result-dossier.png`
- `docs/ui-concepts/2026-05-30-review-guidelines/03-current-trip.png`
- `docs/ui-concepts/2026-05-30-review-guidelines/04-public-resort-guide.png`

Updated accommodation-layer visualization references live in:

- `docs/ui-concepts/2026-06-10-accommodation-guidelines/01-search-results-grouped-accommodation-cues.png`
- `docs/ui-concepts/2026-06-10-accommodation-guidelines/02-selected-dossier-suggested-stays.png`
- `docs/ui-concepts/2026-06-10-accommodation-guidelines/03-suggested-stays-detail-panel.png`
- `docs/ui-concepts/2026-06-10-accommodation-guidelines/04-current-trip-accommodation-context.png`

Final main-page close-out visualization references live in:

- `docs/ui-concepts/2026-06-11-main-page-closeout/01-main-page-accepted-concept.png`
- `docs/ui-concepts/2026-06-11-main-page-closeout/02-main-page-rendered-desktop-1440x1000.png`
- `docs/ui-concepts/2026-06-11-main-page-closeout/03-main-page-rendered-mobile-390x844.png`

## Product Intent

Snowcast is a ski-trip planner for choosing the right resort, travel window, and stay base under snow/weather uncertainty. It is not a generic travel chatbot, hotel marketplace, or climate campaign.

The UI should emphasize practical planning around snow and weather:

- "April is risky below 1,800m."
- "Use archive snow evidence before you commit."
- "Best snow assurance, but very long drive."
- "Archive-backed vs forecast-assisted vs fallback-heavy."

Weather and snow planning are the core product story. Climate context can explain why the product matters in strategy, but the app UI should focus on the user's immediate decision.

## Chosen Visual Direction

Use the previous "C" direction:

- dark editorial command area
- strong snow/weather planning signal
- compact search command
- light workspace with ranked evidence cards
- premium consumer product feel, not internal dashboard

Chosen palette:

- midnight blue as the trust anchor
- clear alpine/sky blue for data and evidence
- creamy alpenglow pink as a brand accent
- snow white and very light blue/pink workspace surfaces
- controlled amber/orange for warnings and travel watchouts
- green/blue/amber status semantics where needed

Pink should be used for atmosphere, date/window emphasis, selected accents, and soft borders. It should not be the only signal for risk, trust, or snow status.

Semantic color rules after design review:

- pink/alpenglow: travel-window emphasis, selected date accents, brand atmosphere
- amber/orange: risk, warnings, watchouts, disruption
- green: positive status, strong fit, low disruption
- blue: evidence, data, archive/provenance cues

Avoid pink warning banners. If a date-window risk needs emphasis, pair a pink date accent with amber/orange warning iconography and text treatment.

Logo direction:

- Borrow the sharper mountain/snow mark direction from the third generated variant.
- Recreate it as a clean vector mark.
- Do not use the generated raster logo directly.

## Image Policy

Generated concept images are design references, not production assets.

Production image policy:

- AI-generated or abstract alpine imagery is acceptable for the command-bar atmosphere because it is brand mood, not factual evidence.
- Specific resort cards should prefer real, licensed, source-safe resort imagery.
- Do not use AI-generated "Cervinia" or "Cortina" images as if they show the real place.
- If real imagery is not available, resort cards must still work without thumbnails using typography, evidence chips, compact terrain motifs, or non-specific abstract mountain texture.
- Public resort pages can use real imagery later when rights and sourcing are clear.

## Search UX Model

Search has two states.

### Initial State

The first viewport is an editorial planning entry point:

- dark midnight-blue/alpenglow command band
- Snowcast brand and navigation
- one dominant trip brief input
- embedded or adjacent primary action
- compact planning signal, for example "April is risky below 1,800m"
- no large filter form
- no generic AI/chat panel

The initial state should sell the product in seconds, but it should not feel like a marketing landing page. The user can start planning immediately.

### Post-Search State

After search, the hero collapses into a compact command bar:

- Snowcast brand
- trip brief input with current text
- Search/Current trip navigation
- planning signal
- update/search action

The main space belongs to the recommendation board. The user is now comparing options, not reading the pitch.

Below the command bar:

- active trip-state chips
- `Refine` button
- optional compact clarification card when missing context materially affects ranking

The manual refine UI should be a drawer or side panel, not a permanently visible form.

## Trip State And Chips

Chips should make structured state visible and editable:

- location: `Italy`
- skill: `Intermediate`
- budget: `EUR 150-320 nightly`
- origin: `Warsaw origin`
- dates: `21-27 Apr 2027`
- quality: `Standard+ quality`
- travel preference when present

Avoid raw/internal labels in primary chips:

- Avoid `Budget flex 0.1`
- Avoid ambiguous `stars`
- Avoid unsupported accommodation preference chips

Each chip should have a clear removal affordance. Removing a chip should either update results immediately in the future or clearly require `Update`.

## Product Entity Hierarchy

Snowcast must consistently teach the relationship between destination, ski area, stay base, and trip option.

Use this hierarchy wherever a selected recommendation is described:

```text
Destination
Cervinia

Ski area
Ski Cervinia

Stay base
Breuil-Cervinia
```

Rules:

- Use `Destination` for the user-facing resort/trip destination.
- Use `Ski area` for the mountain/ski-domain component when it differs from the destination or materially affects the recommendation.
- Use `Stay base` for the village/base area where the user would stay.
- Use `Suggested stay` or `Accommodation` for a provider-backed hotel/apartment option under a stay base.
- Use `Trip option` when discussing the combined destination + ski area + stay base + travel window recommendation.
- Do not rely on small secondary text alone to explain these relationships.
- Do not mix `resort`, `area`, and `base` labels inconsistently across cards and detail pages.

## Accommodation Layer

Snowcast should support actual hotel/accommodation options as a layer inside trip options, not as the main search-result unit.

Recommended product model:

```text
Recommendation group
Destination + ski area

Trip option
Destination + ski area + stay base + optional suggested stay

Suggested stay
Provider-backed hotel, apartment, or lodging option under the selected stay base
```

UI rules:

- Main search results stay grouped by destination/ski-area. Do not create one global result card per hotel.
- A result card may mention `Suggested stays available` or `Provider-backed stays checked`, but it should not become a hotel card.
- Stay-base alternatives remain the first accommodation choice layer.
- Suggested hotels/apartments appear under the selected stay base in the detail page.
- Changing stay base should update suggested stays, stay cost, lift access, travel effort, total-trip estimate, and stay-fit explanation.
- Changing a suggested stay should update exact lodging price/availability, provider freshness, booking CTA, and lodging-specific tradeoffs.
- Hotel-level results must never hide mountain/snow fit. The product remains a ski-trip decision engine, not a generic hotel marketplace.

Suggested stay cards should show only facts the product can support:

- accommodation name
- type, e.g. hotel, apartment, aparthotel
- provider/source
- price or price range
- freshness, e.g. `Checked 2h ago`, `Stale`, or `Estimate only`
- distance/access cue when known
- one reason it fits this trip
- booking handoff action

Freshness and evidence language is mandatory:

- `Provider-backed · checked 2h ago`
- `Provider-backed · stale`
- `Stay-base estimate, not live hotel inventory`

Do not show property-level claims such as amenities, cancellation, exact availability, ratings, or room details unless the backend has provider-backed data with freshness metadata for those fields.

## Clarification UX

Clarifications are bounded decision cards, not chat.

Use them when missing or ambiguous context changes recommendation quality:

- budget mode: nightly lodging vs total trip
- duration or party size for total-trip budget
- origin when the user mentions drive distance or travel effort
- stay-base preference when alternatives are close in score

Clarification cards should be compact and contextual:

- appear above rankings when the ambiguity materially affects the ranking
- appear near chips or in the decision rail only when the ambiguity is low impact
- use two to four concrete choices
- explain why the answer matters in one short sentence
- never block search unless the current input cannot be interpreted safely

The search state area should distinguish:

- parsed confidently, e.g. `Italy`, `Warsaw`, `21-27 Apr 2027`
- assumed, e.g. `Intermediate`
- clarification needed, e.g. `Budget per night or total trip?`

If results are shown with an assumption, say so plainly: `Results shown using nightly lodging budget until you clarify.`

## Recommendation Board

The result list should feel like a decision board, not a hotel listing grid.

Each result card should answer:

- why does this result lead?
- what option is this?
- what is the main tradeoff?
- what evidence backs it?
- which stay base is recommended?
- what is the secondary trip-fit score?

Card anatomy:

- rank and role: `#1 Best late-April snow reliability`, `#2 Easier travel`, `#3 Balanced stay fit`
- leading verdict, e.g. `Best late-April snow reliability`
- destination name and region
- explicit destination / ski area / stay base labels
- one-line verdict
- evidence quality badge, e.g. `Archive-backed · 6 seasons`
- snow label: use `Snow reliability` for archive/history and `Snow outlook` for current/forecast
- travel watchout or travel advantage
- stay base
- stay-base alternatives count only when the API/data supports it
- suggested-stays availability cue only when provider-backed accommodation data exists
- mid-mountain snow metric when available
- `Trip fit` or `Match score` percentage and progress indicator as a secondary metric
- `View details` action

Do not make cards look like hotel inventory. Accommodation details are part of the recommendation, not the product identity.

Do not use `Confidence` as the primary visible label on result cards. A bare percentage invites "92% of what?". Use `Trip fit` or `Match score`, and keep the explanation/evidence hierarchy more prominent than the score.

Evidence quality framework:

- `Archive-backed`: high trust; enough historical seasons or records support this window.
- `Forecast-assisted`: medium trust; current forecast meaningfully supports the recommendation.
- `Fallback-heavy`: lower trust; seasonal traits or sparse data are carrying more of the answer.

Use one of these labels consistently instead of scattering `evidence`, `confidence`, `signal`, `provenance`, and `freshness` as separate unexplained concepts.

## Decision Rail

The right rail in post-search should be decision support, not a form.

Recommended sections:

- `Why Cervinia leads`
- `Clarify`
- `Evidence mode`
- optional compact `Tradeoffs` summary

The rail should explain the selected result and expose ambiguity. It should not duplicate every filter control. The card itself should still carry a short `why this leads` verdict, so the rail deepens rather than introduces the reasoning.

## Refine Drawer

The refine drawer owns manual control.

Group fields by user mental model:

- Trip: location, skill, quality
- Snow window: any time, month, exact dates
- Stay budget: nightly budget, budget mode, party/duration only when supported
- Travel effort: origin, max drive, tolerance

The drawer should keep current values visible, use segmented controls where appropriate, and avoid advanced/internal fields unless the product can explain them clearly.

## Selected Resort Detail

The selected-resort page should become a recommendation dossier.

Hierarchy:

1. Verdict header: destination, ski area, stay base, main tradeoff, and secondary `Trip fit`.
2. Why this result leads: decision explanation before raw metrics.
3. Planning signal: travel window fit and evidence basis.
4. Selected trip option: stay base, lift access, rental, budget, travel effort.
5. Stay-base comparison when alternatives are available; otherwise show the selected stay base clearly without inventing alternatives.
6. Suggested stays/accommodations under the selected stay base when provider-backed data exists.
7. Evidence ledger: evidence quality, current conditions, archive-backed metrics, coverage, lodging-source freshness, and freshness in user language.
8. Highlights and risks.
9. Booking handoff and save-current-trip actions.

The page should reduce repeated cards and use fewer, stronger sections. It should not feel like a widened side panel.

Move `Why this result` above detailed weather rows. Users need to understand why they should trust/book the recommendation before reading wind, freshness, or raw provenance details.

Evidence ledger organization should expose conclusions, not implementation internals:

- `Evidence quality`: Archive-backed / Forecast-assisted / Fallback-heavy
- `Coverage`: number of archive seasons or records
- `Freshness`: fresh / stale / historical in plain language
- `Snow reliability` or `Snow outlook`
- `Known limitation`, when data is sparse
- `Lodging evidence`, when suggested stays are present: provider, checked time, live vs estimate status

Hide raw weather-model terminology, confidence calculations, provider implementation details, and debug-like provenance unless the user opens a deeper evidence view later.

## Accommodation Clarifications

When stay-base or lodging choice materially changes ranking, ask bounded preference questions instead of exposing many filters upfront:

- `What matters more for Tignes?`
- `Lower total price`
- `Closest to lifts`
- `Quieter base`
- `Family-friendly stay`

Clarifications can influence stay-base selection and suggested stays, but they should remain ski-trip preference questions. Avoid generic hotel-filter dialogs unless the user explicitly asks for hotel shopping.

## Current Trip

The web current-trip view is a preview of the mobile companion product.

Target structure:

- trip identity and dates
- selected stay base and optional selected accommodation context
- today's/current conditions status
- `Planning update` instead of `What changed since last check`
- companion/event history
- next useful action

Accommodation context remains secondary here. If a provider-backed suggested stay is known, show the name, source/freshness, price label, access cue, and booking handoff. If not, show `Stay-base estimate, not live hotel inventory` and keep the focus on trip identity, conditions, and planning updates. Keep this simpler than search. The long-term companion belongs primarily on mobile.

## Public Resort Pages

Public resort pages can use a more editorial content layout than the app search flow.

Target structure:

- resort identity
- current snow outlook
- best months/conditions calendar
- historical evidence
- planning caveats
- call back into Snowcast planning

Do not make public pages look like the private app result detail. They are SEO/content surfaces, not routeable search-context pages.

## Component And Visual Rules

- Prefer fewer, stronger surfaces over nested cards.
- Use border radius around 14-18px for most UI components.
- Do not put cards inside cards unless the inner element is a true repeated metric tile.
- Use code-native text and controls for UI, not screenshots of UI.
- Keep typography deliberate for buttons, chips, labels, controls, and result metrics.
- Use icons sparingly and consistently.
- Use image areas only when assets are real or clearly non-specific.
- Preserve responsive behavior: mobile should stack command, chips, recommendation cards, and decision rail without overflow.

## Accessibility And Trust

- Maintain high contrast in dark command areas.
- Do not encode risk/status with color alone.
- Use readable chip labels and button text.
- Keep provenance wording visible but not debug-heavy.
- Distinguish forecast, archive, and fallback evidence in user language.

## Implementation Boundaries

This redesign should not introduce:

- new backend ranking behavior
- new semantic filters unsupported by data
- web auth
- hotel-level marketplace UI
- generic AI chat
- unsupported provider-backed accommodation claims
- fake resort imagery
- push notification delivery

Future implementation may refactor the large `App.tsx` file into smaller route and component modules as part of the UI work, but that should be scoped to supporting the redesign.

## Concept Pack To Produce

Generate and review concepts for:

- search initial state
- search post-search state
- refine drawer
- selected resort detail
- suggested stays under selected stay base
- current trip view
- public resort page direction

The accepted concepts become the implementation spec for visual fidelity.
