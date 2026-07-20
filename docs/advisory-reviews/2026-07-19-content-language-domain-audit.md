# Snowcast Content And Language Domain Audit

**Date:** 2026-07-19
**Mode:** `domain-audit`
**Branch:** `codex/content-language-refinement-clarity`
**Reviewed head:** `d276bc8de9bf65ab614a0352cf7d5fbe9c6c253e`
**Draft PR:** [#52](https://github.com/lampssy/ai-sports-travel-planner/pull/52)

This audit applies the `content-language` contract from
`docs/operating-model/advisory-reviewers.md`, with B2 English as the maximum
complexity. It covers the homepage, Search V4, refinements, recommendations,
dossier, weather evidence, accommodations, current trip, public pages, mobile
companion, backend errors, and product-facing README content.

The audit was source-backed and included relevant copy tests and rendered
component behavior. It records recommendations only and does not implement
them.

## Current Strengths

1. **The product now has a defined content-language standard.**
   The reviewer contract requires direct, natural language, standalone
   questions, meaningful options, visible uncertainty, and separation between
   user language and internal taxonomy
   (`docs/operating-model/advisory-reviewers.md:310-349`).

2. **Important trust terms are translated centrally in the web application.**
   `frontend/src/ui/snowcastCopy.ts:14-47` maps internal evidence states to
   understandable labels and preserves limitations instead of hiding them.

3. **The current refinement model asks one question at a time.**
   `frontend/src/search/RefinementCard.tsx:44-130` presents one decision, its
   options, and clear apply, skip, and reset actions. This is a major
   improvement over paired questions whose answers could not be chosen
   independently.

4. **Known internal phrases are covered by automated checks.**
   `frontend/src/search/contentLanguage.test.ts:100-203` prevents several
   previously identified technical phrases from returning to primary
   recommendation content.

5. **Evidence limitations are usually visible.**
   Snow, accommodation, and decision-evidence surfaces acknowledge missing
   data, estimates, and provider limitations rather than presenting them as
   confirmed facts:
   - `frontend/src/search/SnowEvidence.tsx:370-380`
   - `frontend/src/search/DecisionEvidenceLedger.tsx:42-78`
   - `frontend/src/search/AccommodationHandoff.tsx:29-59`

6. **Web service failures generally provide useful recovery guidance.**
   `frontend/src/api.ts:123-251` translates major availability failures into
   messages that explain what happened and what the user can do next.

7. **Public resort pages keep weather evidence tied to the correct ski area.**
   `app/public_pages.py:430-466` and `app/public_pages.py:572-619`
   distinguish current forecasts, historical evidence, and fallback content
   instead of blending them into one unsupported claim.

## Risks And Gaps

### High Severity

1. **The accommodation handoff promises a stay-base search that the backend
   does not perform.**

   **Type:** Decision accuracy and booking trust

   The UI says "Find a stay in {stay base}", "Continue with selected stay-base
   context", and "Opens a search using this stay base"
   (`frontend/src/search/AccommodationHandoff.tsx:29-59`).

   The backend validates the stay base but generates the external search from
   the destination name and country (`app/api/routes.py:514-545`,
   `app/domain/booking.py:4-13`).

   Users may expect accommodation results centred on the recommended base but
   receive broader destination results. Either the handoff must pass the actual
   stay base or the wording must describe a destination-level search honestly.

2. **The mobile application exposes developer terminology, technical controls,
   and raw errors.**

   **Type:** Task completion, trust, and error recovery

   Examples include:
   - "API base" and raw authentication errors (`mobile/lib/main.dart:142-192`)
   - "Parse brief", "Structured filters", numeric "Quality tier", and numeric
     month input (`mobile/lib/main.dart:426-566`)
   - "Unranked configuration", "fit / 100", and "Pass terrain unresolved"
     (`mobile/lib/main.dart:650-698`)
   - "Comparison basis", "Trip relevance", and "Mark checked"
     (`mobile/lib/main.dart:818-875`)
   - raw backend `detail` values (`mobile/lib/main.dart:1066-1073`)

   Backend details can contain phrases such as "unknown group ID" or "factor
   does not allow mode" (`app/domain/search_intent_policy.py:15-73`). The
   mobile app needs its own public copy and error-mapping layer, aligned with
   the web application.

3. **Primary Search V4 controls still require knowledge of the ranking model.**

   **Type:** User intent capture

   Problematic labels include:
   - "Exact controls", "Minimum stay tier", and "Hard drive limit"
   - "Value objective" and "Other active objectives"
   - "Trip priorities" and "Optimize ..."

   These appear in `frontend/src/search/SearchFiltersDrawer.tsx:203-489`.
   Supporting labels such as "Pass-accessible terrain", "Party skill fit",
   "Trip viability", and "Stay practicality" come from
   `frontend/src/search/searchPresentation.ts:31-70`.

   Important controls should be understandable without explanatory text.
   Suggested concepts include "Maximum drive time", "Required trip details",
   "Nice-to-have features", and "What matters most for value?"

### Medium Severity

4. **The search workflow uses implementation language as navigation language.**

   **Type:** Comprehension and product confidence

   "Ranking", "rerank", "refinement", "eligible configurations", and
   "unranked options" appear throughout:
   - `frontend/src/search/SearchContextRail.tsx:16-35`
   - `frontend/src/search/RefinementCard.tsx:40-130`
   - `frontend/src/search/RecommendationBoard.tsx:95-128`
   - `frontend/src/search/searchPresentation.ts:952-983`

   Prefer "One more question", "Update results", "Keep these results", "trip
   options", and "We are checking your new choices."

5. **Several refinement questions remain awkward or incomplete.**

   **Type:** Intent capture

   Examples in `app/config/search-refinement/presentation-v2.toml` include:
   - "Would you rather maximise terrain covered for the pass price?" without
     stating the alternative
   - "What kind of apres atmosphere would you like around the ski day?"
   - "Balanced" with a description that only says "Prefer balanced."
   - "Structural type of accommodation base."

   Generic reasons such as "Your answer can change which trip option fits you
   best" should be replaced with the concrete decision being made.

6. **Snow evidence uses statistical terms without enough plain-language
   context.**

   **Type:** Evidence interpretation

   Terms include "Average daily median depth", "likelihood above 30 cm",
   "climatology", "source rows", "Run", and "Computed":
   - `frontend/src/search/SnowEvidence.tsx:87-358`
   - `app/domain/search_weather_evidence.py:531-608`

   The chart labels a horizontal marker as "30 cm guide"
   (`frontend/src/search/SnowEvidenceChart.tsx:279-285`). The model
   documentation states that 30 cm is a planning heuristic, not a universal
   safety or skiability threshold (`docs/snow-evidence-model.md:106-108`),
   but the UI does not explain that distinction.

7. **"Snow window" labels can be mistaken for actual snow conditions.**

   **Type:** Decision interpretation

   Labels such as "Strong", "Good", "Mixed", and "Unknown" are generated in
   `frontend/src/search/searchPresentation.ts:930-937` and displayed by:
   - `frontend/src/search/RecommendationCard.tsx:74-86`
   - `frontend/src/search/DossierVerdict.tsx:53-62`

   "Unknown" may mean insufficient evidence rather than unknown conditions. Use
   "Snow fit for your dates" with labels such as "Strong fit", "Some concerns",
   and "Not enough evidence".

8. **Recommendation explanations remain generic and mechanically composed.**

   **Type:** Decision support

   Examples include "Terrain scale contributes positively to this comparison",
   "adds resilience", and generated phrases such as "A strong trip-window snow
   fit match" (`frontend/src/search/searchPresentation.ts:641-910`).

   The recommendation should use concrete facts wherever available: dates,
   historical depth, number of seasons, walking distance, terrain coverage, or
   travel time. "Supported strength" and "Watchout" in
   `frontend/src/search/DossierVerdict.tsx:74-95` should become "Why it fits"
   and "Main concern".

9. **Scoring details expose the internal calculation contract as ordinary
   product content.**

   **Type:** Transparency without comprehension

   `frontend/src/search/ScoringDetails.tsx:24-75` exposes policy codes, raw
   factor IDs, weights, points, decision groups, and evidence caps. The
   surrounding navigation calls this "How ranking works"
   (`frontend/src/search/RecommendationDossier.tsx:15-120`).

   The primary section should explain contributions in user terms. Raw IDs and
   calculation data, if retained, should sit inside a clearly marked
   "Technical calculation data" disclosure.

10. **Some 4xx and validation errors still pass internal backend details to
    users.**

    **Type:** Error recovery and trust

    `frontend/src/api.ts:57-79` passes string `detail` values through and
    can construct validation messages from raw field paths. Current-trip calls
    have similar behavior. Relevant backend messages originate in:
    - `app/api/routes.py:123-259`
    - `app/domain/search_intent_policy.py:15-73`

    Public errors should use stable error codes and a client-side copy table.
    Technical details should remain in logs.

11. **Refinement failure is hidden from sighted users.**

    **Type:** Workflow clarity

    `frontend/src/App.tsx:748-757` converts refinement failures into
    `temporarily_unavailable` while clearing the visible error.
    `frontend/src/search/SearchContextRail.tsx:16-35` contains an
    accessibility announcement, but no equivalent visible message.

    A short message should say: "We couldn't load another question. Your current
    results are still ready."

12. **Public resort pages contain internal catalog language and imply more
    booking agency than Snowcast provides.**

    **Type:** Product positioning

    Examples include "Trip market", "Where Snowcast can place you", "Rental
    display facts", "quality tier", "stable ski-area ID", and "Trust and
    provenance" (`app/public_pages.py:407-550`). The public error "Unknown
    stay_destination_id" can also reach users.

    Prefer "Where you can stay", "Equipment rental examples", "How we built this
    guide", and a normal destination-not-found page.

### Low Severity / Style Polish

13. **Current-trip copy feels operational rather than personal.**

    "Trip companion", "comparison baseline", "eligible", "suppressed", and
    "refresh has landed" appear across `frontend/src/ui/AppShell.tsx:88-137`
    and `app/domain/trip_companion.py:68-313`.

    Prefer "What changed since your last check", "No meaningful changes", and
    "Add your dates to receive relevant updates."

14. **The README product introduction mixes customer language with architecture
    language.**

    `README.md:3-29` includes "conditions-smart", "deterministic APIs", "thin
    supporting layers rather than ranking owners", "access edge", "provenance
    metadata", "demo", and "scaffold".

    The setup and engineering sections can remain technical. The opening
    product explanation should describe what Snowcast helps someone decide.

15. **Terminology and spelling are not fully consistent.**

    The product mixes concepts such as trip option/configuration,
    ranking/results, stay/base/accommodation, and UK/US spelling. This is
    mostly polish, but consistency would reduce translation and maintenance
    problems.

## Top Opportunities

1. Create one shared public-language glossary for web, mobile, backend errors,
   and generated recommendation copy.
2. Rename the Search V4 workflow around user decisions rather than ranking
   mechanics.
3. Make the accommodation handoff match its real provider query.
4. Reframe weather evidence around understandable findings, dates, sources, and
   explicit limits.
5. Replace generic recommendation templates with concrete evidence-backed
   sentences.
6. Separate plain scoring explanations from optional technical calculation
   data.
7. Add content contract tests for mobile, public pages, errors, refinements, and
   booking handoffs.

## Suggested Next Actions

1. **P0:** Correct the stay-base accommodation claim or change the provider
   query.
2. **P0:** Stop displaying raw backend and authentication errors in mobile and
   web clients.
3. **P0:** Replace Search V4 control labels that require internal ranking
   knowledge.
4. **P1:** Rewrite refinement questions and reasons using standalone,
   topic-specific language.
5. **P1:** Rename refinement and ranking actions throughout the search flow.
6. **P1:** Rewrite weather labels and explain that the 30 cm marker is a
   comparison aid, not a safety or piste-opening threshold.
7. **P1:** Make snow-fit labels distinguish evidence availability from expected
   conditions.
8. **P1:** Introduce evidence-specific recommendation templates.
9. **P2:** Simplify scoring disclosures, public resort pages, current-trip
   language, and the README introduction.
10. Add automated checks for forbidden internal terms, complete refinement
    questions, typed error mappings, booking-query claims, and
    primary-versus-technical disclosure copy.

## Deferred Pending Owner Review

1. Decide whether the main public term is **"trip option"** or **"trip
   configuration"**.
2. Decide whether **"dossier"** remains a product term or becomes **"trip
   details"**.
3. Choose **"Required trip details"** or **"Must-haves"** for hard constraints.
4. Decide whether the 30 cm chart marker should be relabelled, explained, or
   removed.
5. Decide how much statistical weather detail belongs in the main view versus
   a technical disclosure.
6. Decide whether raw scoring factors remain available behind an advanced
   disclosure.
7. Decide whether mobile must reach full public-language parity now or should be
   clearly labeled as an internal preview.
8. Decide whether accommodation search will become truly stay-base-specific or
   remain destination-level.
9. Select one English spelling convention. B2 complexity can remain the
   product-wide maximum in either case.

**Verification status:** Static, source-backed domain audit completed against
the stated branch and head. No audit recommendation was implemented.
