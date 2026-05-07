# Sprint 33 Design: Grouped Trip Options And Stay-Base Alternatives

## Summary

Sprint 33 evolves search results from "one resort card with one selected stay base" into grouped ski-trip recommendations. The ranking engine should evaluate full trip options internally, but the UI should group those options into clear destination or ski-area recommendations so users are not overwhelmed by repeated cards for the same resort.

The goal is to make stay-base choice visible and meaningful without turning Snowcast into a generic accommodation marketplace. To support that, Sprint 33 also adds a scoped stay-base acquisition/enrichment flow for source-backed coordinates, lift access, and qualitative base profiles.

## Product Boundary

Snowcast should answer:

- Which ski trip option should I consider?
- Which stay base makes that option fit my budget, access, travel effort, and skill needs?
- What tradeoff do I make if I choose a different base?

Snowcast should not yet answer:

- Which exact hotel should I book?
- Which room type, cancellation policy, or live accommodation inventory is best?
- Which neighborhood is best for generic travel reasons unrelated to skiing?

Hotel-level recommendations can be added later under the selected stay base, but Sprint 33 keeps the primary product surface at destination, ski-area, and stay-base level.

## Current State

The backend already evaluates combinations of destination, ski area, stay base, and rental. It then returns only the best combination per resort.

The frontend displays a resort card with one selected stay base and a detail page for that selected combination.

This is a useful foundation, but it hides alternatives:

- a resort may have one premium near-lift base and one cheaper farther base
- a lower-ranked resort may become competitive if the user prioritizes price or travel effort
- future hotel availability could change the best stay option without changing the mountain fit

## Goals

- Make the internal ranking unit explicit as a trip option.
- Group multiple trip options into one user-facing recommendation where appropriate.
- Show the best stay base for the current search on the main result card.
- Show credible alternative stay bases inside the result details.
- Explain how switching stay base changes price, lift access, travel effort, and total-trip fit.
- Keep the main search result list compact and ski-focused.
- Prepare the data contract for later hotel/provider options without adding hotel inventory in this sprint.
- Add a stay-base acquisition scope to the existing catalog acquisition model so current stay bases can be enriched with source-backed facts and evidence.
- Add an AI-assisted qualitative profile proposal step for stay-base character labels, constrained by source policy, fixed enums, and reviewable evidence.

## Non-Goals

- No live hotel inventory.
- No hotel-level ranking.
- No booking-provider search UI.
- No broad accommodation marketplace behavior.
- No generic destination neighborhood guide.
- No requirement to fully curate every possible stay base before release.
- No blind broad-web scraping or unbounded source crawling for qualitative stay-base profiles.
- No automatic approval of interpretive stay-base profile tags in the first release.

## Core Model

Sprint 33 should separate the ranking unit from the display unit.

### Trip Option

A `TripOption` is the internal ranked entity:

- destination
- ski area
- stay base
- rental or rental estimate
- optional future lodging option
- component scores:
  - mountain fit
  - snow or planning fit
  - stay fit
  - travel effort fit
  - price fit
  - evidence confidence
- total score
- explanation and caveats

This preserves scoring correctness because accommodation choice really can affect the overall recommendation.

### Recommendation Group

A `RecommendationGroup` is the user-facing result:

- destination id and name
- selected ski area
- top trip option
- alternative trip options
- group-level score and confidence
- compact explanation of why this resort/ski-area group appears in the results

The main result list should usually show one group per destination or ski-area context, not one card per stay base.

## Grouping Policy

Default behavior:

- Rank all eligible trip options.
- Group them by destination and selected ski area.
- Pick the highest-scoring option as the group's recommended stay base.
- Include a small set of alternative stay-base options when they are credible and meaningfully different.
- Sort groups by the top trip option score.

Alternative trip options should be included only when they add useful choice:

- cheaper stay base
- closer lift access
- easier travel access
- better fit for beginners or families
- better fit for premium/convenience preference

Avoid showing alternatives that differ only trivially.

## Duplicate Resort Policy

The same destination should not appear multiple times by default. Repeated resort cards make the product feel noisy and hotel-marketplace-like.

Allow a second card for the same destination only when the options represent materially different user intents that cannot be explained well inside one group.

Examples:

- "Tignes: best snow and premium near-lift base"
- "Tignes: lower-cost family base"

This should be rare and policy-driven, not the normal output shape.

## UX

### Main Result Card

The result card should keep the resort/ski-area as the main object, with the selected stay base clearly visible.

Example structure:

```text
Tignes
Best base for this search: Val Claret

Mountain fit: strong
Stay fit: premium, near lifts
Travel effort: moderate
Estimated trip cost: high

Other viable bases: Le Lac, Tignes 1800
```

The card should not look like a hotel card. It should still feel like a ski-trip recommendation.

### Detail View

The details page should add a stay-base comparison surface.

Suggested layout:

- destination and ski-area summary at the top
- selected stay-base panel
- alternative stay-base tabs or compact comparison rows
- tradeoff explanation for each alternative

Changing the stay base should update:

- stay price range
- lift-distance/access label
- travel effort if stay-base coordinates are known
- total-trip estimate when available
- explanation highlights and risks

### Agentic Clarification

If two stay bases are close in score and the missing preference changes the recommendation, the app can ask a bounded clarification question.

Examples:

- "For Tignes, should we prioritize lower stay cost or closest lift access?"
- "Do you prefer a quieter base or a livelier center?"
- "Is ski-in/ski-out important for this trip?"

These should reuse the Sprint 31 clarification pattern: concrete choices, deterministic triggers, and no open-ended chat requirement.

## Data And API Shape

Preferred direction:

- Add backend models for trip options and grouped recommendations.
- Keep the existing search endpoint backward compatible during transition.
- Add new response fields rather than removing current `SearchResult` fields immediately.
- Continue returning the top selected stay base for simple clients.
- Add an alternatives collection for richer clients.

Candidate response shape:

```json
{
  "resort_id": "tignes",
  "resort_name": "Tignes",
  "selected_ski_area_id": "tignes-val-disere",
  "top_option": {
    "stay_base_name": "Val Claret",
    "score": 0.82,
    "price_range": "EUR ...",
    "lift_distance": "near"
  },
  "alternative_options": [
    {
      "stay_base_name": "Le Lac",
      "score": 0.77,
      "tradeoff_summary": "Balanced base with slightly lower convenience."
    }
  ]
}
```

The implementation plan should decide whether to introduce a new public response model immediately or add compatibility fields first.

## Stay-Base Data Requirements

Sprint 33 can work with existing stay-base fields:

- name
- price range
- quality
- lift-distance bucket
- supported skill levels

It becomes more useful as these fields are added later:

- stable stay-base id
- stay-base coordinates
- village/town type
- nearest lift or gondola reference
- computed lift/station distance
- access mode: walk, ski bus, car recommended, unknown
- family friendliness
- nightlife/quietness
- ski-bus dependency
- ski-in/ski-out flag
- provider-backed or reviewed accommodation price evidence

Do not expose filters for weakly supported attributes until data quality is good enough.

## Stay-Base Acquisition Pipeline

Sprint 33 should extend the existing catalog acquisition model rather than create a separate unrelated system.

The acquisition runner should support a stay-base scope, for example:

```text
catalog acquisition
  --scope resort-static
  --scope stay-bases
  --scope full-catalog
```

This keeps the proposal, evidence, source registry, fetch-log, and patch-review patterns consistent with Sprint 29/30 while allowing stay-base enrichment to run separately after resort and ski-area anchors are stable.

Recommended operating order:

```text
1. Freeze resort/ski-area identity, coordinates, elevations, and official URLs.
2. Run or preserve weather-history rebuilds based on weather-critical ski-area fields.
3. Run stay-base acquisition against the frozen catalog.
4. Review grouped stay-base proposals.
```

Stay-base acquisition should not affect historical weather rebuilds unless a later product decision makes stay-base coordinates weather-critical. Weather should remain ski-area and elevation-band based.

### Deterministic Enrichment

For current catalog stay bases, deterministic extraction should prioritize:

- OSM place nodes/relations for stay-base identity and coordinates
- Wikidata or GeoNames as secondary identity/coordinate evidence
- OSM lift, gondola, aerialway, and station geometry for nearest-lift distance
- computed lift-distance bucket from coordinates and nearest relevant lift/station
- official resort/tourism pages for explicit access notes such as ski bus, pedestrian lift access, or named village services

LLM output should not determine coordinates, nearest lift distance, or other measurable facts.

### Qualitative Profile Enrichment

For non-deterministic character fields, Sprint 33 should add an AI-assisted research/profile proposal step.

The profile agent receives minimal structured input:

- stay-base id
- stay-base name
- parent resort and ski-area context
- country/region
- coordinates when known
- official resort or tourism domains when known

It can then discover and inspect a small number of source-policy-approved pages. Manual source URLs should not be required for every stay base.

Allowed source tiers:

- official resort/tourism pages
- local tourism pages
- reputable ski guide pages
- Wikivoyage/Wikipedia-style reference pages where useful

Avoid or downrank:

- random SEO travel blogs
- broad review scraping
- Booking/TripAdvisor-style review platforms as primary evidence
- pages with unclear resort/base identity

The qualitative classifier must emit constrained enum values only. Candidate fields:

- `base_type`: `resort_center`, `satellite_village`, `quiet_village`, `family_base`, `premium_base`, `budget_base`, `nightlife_base`
- `access_profile`: `ski_in_ski_out`, `walk_to_lifts`, `ski_bus_needed`, `car_recommended`, `unknown`
- `atmosphere_tags`: `quiet`, `lively`, `family_friendly`, `premium`, `budget_friendly`, `beginner_friendly`

Every proposed tag must have source-backed claims and a short evidence summary. The agent should classify explicit claims; it should not infer hidden truth from generic marketing language.

### Review-Limiting Policy

The review packet should group evidence by resort and stay base, not by isolated atomic facts.

Example:

```text
Tignes / Tignes 1800
Recommended:
- coordinates: OSM place node, no conflict
- nearest lift: Boisses gondola, computed distance 220m
- access profile: walk_to_lifts, review required
- profile tags: quiet, family_friendly, satellite_village, review required
```

To keep review manageable:

- enrich only current catalog stay bases first; do not auto-discover every nearby village
- limit each destination to a small, product-relevant set of stay bases unless manually expanded
- suppress boring confirmations when source-backed values match current catalog values within tolerance
- auto-patch only low-risk new deterministic fields when the implementation plan explicitly allows it
- keep qualitative profile tags review-required initially
- on refresh runs, show only new values, changed values, conflicts, source loss, or low-confidence cases

### Proposal Shape

Stay-base acquisition proposals should use the same proposal model style as resort acquisition, with target metadata:

```json
{
  "resort_id": "tignes",
  "target": {
    "entity_type": "stay_base",
    "entity_id": "tignes-1800-les-boisses"
  },
  "field_path": "profile_tags",
  "proposed_value": ["family_friendly", "quiet", "satellite_village"],
  "status": "review_required",
  "confidence": 0.72,
  "extraction_method": "stay_base_profile_agent",
  "evidence_summary": "Sources consistently describe Tignes 1800 / Les Boisses as a quieter, family-oriented village below Le Lac with access to other Tignes bases by shuttle.",
  "source_claims": [
    {
      "url": "https://www.tignes.net/...",
      "claim": "Official tourism content describes village location and access."
    }
  ]
}
```

Qualitative profile confidence should reflect source agreement:

- high: multiple independent sources agree with specific evidence
- medium: one strong source or two weaker aligned sources
- low: vague marketing language only
- below threshold: no proposal

## Hotel Future

Hotel options should fit under the same model later:

```text
RecommendationGroup
  -> TripOption
    -> StayBase
      -> LodgingOption
```

The main search should still rank ski-trip options, not individual hotel listings. Hotels can appear in the selected result details as examples, booking handoff candidates, or provider-backed options.

This keeps the product differentiated from generic accommodation search while still allowing monetization and booking handoff.

## Ranking

Sprint 33 should make component scoring more legible.

Suggested components:

- mountain fit: ski area, skill fit, terrain, snow/planning signal
- stay fit: stay-base quality, lift access, supported skill levels
- travel fit: Sprint 32 travel effort when known
- price fit: nightly or total-trip budget semantics from Sprint 31
- confidence: evidence quality and missing-data caveats

The grouped result score should usually be the top trip option score, with optional group-level boosts or caveats only if they are easy to explain.

Avoid averaging all stay bases inside a resort. A resort with one excellent stay option should not be dragged down by weaker irrelevant bases.

## Error Handling

- If a destination has only one stay base, return one group with no alternatives.
- If stay-base data is incomplete, keep the current top-option behavior and add caveats rather than blocking search.
- If travel effort is unavailable for stay bases, use destination-level travel effort and mark it clearly.
- If alternatives cannot be scored reliably, omit them instead of showing noisy choices.

## Testing

Backend tests:

- trip-option generation across destination, ski area, stay base, and rental combinations
- grouping by destination/ski area
- top-option selection
- alternative selection and deduplication
- duplicate-resort suppression
- rare duplicate-resort allowance for materially different intents if implemented
- compatibility with existing search clients
- stay-base acquisition target resolution for existing catalog stay bases
- deterministic OSM/Wikidata coordinate and lift-distance proposal generation with mocked sources
- qualitative profile classifier validation with enum-only mocked LLM output
- review packet grouping by resort and stay base
- refresh behavior suppresses unchanged confirmations and surfaces conflicts

Frontend tests:

- main result card shows selected stay base and alternative count/names
- detail view shows stay-base alternatives
- selecting an alternative updates visible price, access, and explanation fields
- no alternatives state renders cleanly
- clarification card appears when stay-base preference would change recommendation

## Acceptance Criteria

- Search internally ranks full trip options, not only destination-level records.
- Main results remain compact and avoid repeated resort spam.
- Each result clearly names the recommended stay base.
- Users can inspect credible alternative stay bases for the same resort/ski area.
- Switching or comparing stay bases makes tradeoffs visible.
- Current catalog stay bases can be enriched through the catalog acquisition flow with source-backed coordinates, lift access, and qualitative profile proposals.
- Qualitative profile proposals are constrained, evidence-backed, and review-required.
- Review artifacts group stay-base evidence in a way that avoids field-by-field review overload.
- Existing search behavior remains compatible for simple clients.
- The model can later accept hotel/provider options without redesigning search from scratch.
