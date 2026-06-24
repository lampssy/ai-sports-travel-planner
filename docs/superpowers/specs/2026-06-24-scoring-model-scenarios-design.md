# Scoring Model Scenario Design

## Summary

Define golden ranking scenarios for Snowcast's future scoring model. These
scenarios should describe the product behavior Snowcast should eventually
support, not only what current catalog fields can score today.

The key decision is that scenario design is aspirational. A scenario may include
factors that are implemented now, modeled but not scored yet, or not modeled at
all. The scoring architecture should make those future factors easy to add
without redesigning production ranking.

## Decision And Review Gate

- Classification: `review-gated`.
- High-risk domains: ranking correctness, AI-assisted search interpretation,
  user trust, source-backed catalog claims, and future production search
  behavior.
- Developer Decision Checkpoint status: resolved by owner discussion.
  - Golden scenarios must include future-relevant factors such as crowding,
    non-ski activities, ski-pass value, hotel amenities, ski school, childcare,
    and transfer simplicity.
  - AI-assisted search should be able to interpret a large pool of filters and
    preferences into deterministic scoring inputs.
  - The current implementation remains diagnostic-only until a later
    ranking-integration checkpoint.
- ADR status: not required for this scenario spec. A later ADR is appropriate
  when production ranking architecture, factor persistence, or the public search
  API changes.
- Advisory review status: run design review before production ranking
  integration. This spec is the review artifact for deciding scenario coverage
  and scoring-model shape.

## Research Inputs

The research pass suggests users choose ski trips through a constraint stack
rather than one universal "best resort" list.

- Snow reliability and altitude are top decision factors. Recent consumer
  reporting says snow reliability outranks value and ski-area size, and many
  skiers deliberately choose high-altitude resorts to reduce condition risk.
  Source: https://www.inthesnow.com/survey-finds-snow-reliability-tops-price-ski-area-size-in-ski-holiday-choice/
- Cost and conditions dominate booking behavior. Club Med's 2024 UK ski report
  frames booking behavior around value-for-money, early booking to secure price,
  and delaying booking to check snowfall.
  Source: https://corporate.clubmed/club-med-uk-ski-report-2024/
- Ski Club guidance frames resort choice around budget, accessibility, terrain
  variety, village character, and trip style.
  Source: https://www.skiclub.co.uk/discover-snowsports/planning-the-perfect-holiday/choosing-the-right-resort/
- Academic and service-quality research repeatedly highlights snow/slope
  conditions, slope variety, safety, services, accessibility, proximity, price,
  lift queues, weather, and open-slope share.
  Sources:
  - https://opensportssciencesjournal.com/VOLUME/9/PAGE/53/PDF/
  - https://www.researchgate.net/publication/240535320_Relative_Importance_of_Factors_Involved_in_Choosing_a_Regional_Ski_Destination_Influence_of_Consumption_Situation_and_Recreation_Specialization
- Beginner and family advice emphasizes easy slopes, lessons, ski school,
  rentals, lift proximity, non-skier activities, and low logistical friction.
  Sources:
  - https://www.vogue.com/article/first-ski-holiday-tips
  - https://www.snowheads.com/ski-forum/viewtopic.php?t=120454
  - https://www.skisolutions.com/blog/how-to-plan-a-family-ski-holiday
- Package and all-inclusive products are evidence that the "hassle factor" is
  itself important: lift pass, lessons, rentals, transfers, childcare, food, and
  equipment logistics can materially change perceived value.
  Sources:
  - https://www.skisolutions.com/ski-deals/ski-all-in
  - https://www.snowpak.com/
  - https://www.clubmed.us/l/all-inclusive-ski-vacations/lift-pass

## Design Principles

1. Score trips, not generic resorts.
   A ranked result represents a user intent matched to a destination, ski area
   or linked terrain domain, stay base, travel window, budget, and logistics.

2. Keep AI interpretation separate from deterministic scoring.
   AI-assisted search may interpret natural language into intents, preferences,
   avoidances, hard constraints, and weights. It must not invent catalog facts
   or become the final ranking authority.

3. Let scenarios lead implementation.
   A golden scenario can include factors that are not modeled yet. Missing
   factors should appear as explicit gaps in diagnostics rather than being
   ignored.

4. Add factors through a registry, not scoring rewrites.
   New filters and preferences should plug into a factor contract with stable
   metadata: factor id, scope, source requirements, lifecycle, trust behavior,
   default ranking role, supported user intents, and explanation policy.

5. Separate universal fit from preference-activated fit.
   Snow viability, season fit, budget, access, and skill mismatch often matter
   broadly. Apres, quietness, luxury, wellness, restaurants, childcare, and
   non-skier activities should usually matter only when user intent activates
   them.

6. Treat value as utility per trip, not only low price.
   Price should be understood against snow reliability, accessible terrain,
   included lift pass, lesson/rental needs, travel effort, and friction. A cheap
   result with poor access or bad snow can be bad value.

7. Use trust caps and missing-factor visibility.
   Weak or missing data must not create strong positive boosts. Diagnostics
   should show whether an expected factor was active, proxy-only, known missing,
   or future-only.

## Factor Availability States For Scenarios

These states describe scenario design and diagnostics. They do not need to be
identical to runtime factor lifecycle values.

- `active_now`: current implementation can score this factor directly.
- `near_term`: modeled or sourceable soon, but not yet production scored.
- `proxy_only`: current implementation uses a weaker proxy.
- `known_missing`: important to the scenario, but current catalog lacks a
  reliable signal.
- `future_candidate`: valuable later, likely requiring new data sources,
  provider feeds, hotel inventory, or user feedback.

## Candidate Factor Families

### Trip Viability

- snow reliability
- season window fit
- current conditions and disruption risk
- open lifts and open pistes
- snow depth and recent snowfall
- freeze-thaw, wind, rain, visibility, storm risk
- source freshness and confidence

### Ski Experience Fit

- selected ski-area terrain scale
- accessible terrain through default or selected lift pass
- piste difficulty mix
- beginner terrain quality and learning zones
- advanced terrain, off-piste indicators, guide requirement
- lift network strength and uplift convenience
- terrain variety, grooming, trees, glacier, altitude
- lift queues and crowding

### Stay-Base And Logistics Fit

- walking distance to lifts
- nearest lift, rental, ski school, and lesson meeting point
- ski bus quality and frequency
- car-free viability
- airport or train transfer simplicity
- short-break suitability
- luggage and equipment friction
- ski-in/ski-out or ski-to-door access

### Budget And Value

- lodging nightly budget fit
- lift-pass product price
- lift-pass price per accessible piste kilometer
- lesson and rental package availability
- total trip cost estimate
- included products such as pass, lessons, rentals, transfers, meals, childcare
- price confidence and hidden-cost risk

### Group And Skill Context

- beginner-first-trip fit
- mixed-skill group fit
- family fit
- child ski school and childcare
- solo traveler fit
- non-skier partner fit
- group nightlife or quietness preferences

### Resort Character And Non-Ski Fit

- quiet village
- apres/nightlife
- restaurants and food quality
- scenic village
- wellness/spa
- shopping
- non-ski activities
- culture or day-trip access
- sustainability preferences

### Accommodation And Hotel-Level Fit

- hotel distance to lift or shuttle
- hotel amenities: spa, sauna, pool, hot tub, half-board, restaurant
- family rooms
- ski room or boot room
- package operator support
- cancellation flexibility
- user reviews and quality signals

## Scoring Architecture Target

The eventual production scorer should be layered:

1. Intent interpretation
   AI converts user language into normalized intents, hard constraints,
   preference weights, avoidances, and explanation hints.

2. Eligibility and viability
   Remove or heavily cap options that fail season, budget, availability, or
   hard user constraints. Poor snow viability should be able to dominate.

3. Core utility scoring
   Score snow, terrain, skill fit, access, budget, travel effort, and source
   confidence.

4. Preference scoring
   Apply user-activated factors such as quietness, apres, family, luxury,
   wellness, non-ski activities, ski-in/ski-out, or restaurants.

5. Value normalization
   Compare cost against accessible terrain, snow reliability, logistics, and
   included products.

6. Result grouping
   Collapse or nest options so a shared terrain domain or multi-ski-area
   destination does not occupy repeated top-level slots unless the difference is
   materially useful to the user.

7. Explanation and uncertainty
   Explain dominant positive and negative factors, show missing-factor caveats,
   and avoid implying that future-only factors were evaluated.

## Golden Scenario Format

Each golden scenario should define:

- `scenario_id`
- user query or user intent
- travel timing and origin constraints
- hard constraints
- preference weights
- expected top result group behavior
- acceptable alternatives
- results that should be penalized or grouped
- dominant factors that should explain the ranking
- factor availability states
- data gaps that should appear in diagnostics
- target behavior later when future factors become available

## Initial Golden Scenarios

### 1. Snow-Sure Late-Season Intermediate

User intent: "I want a March or April trip with the best chance of good snow,
intermediate skiing, and reasonable value."

Expected behavior:
- High-altitude, glacier, or historically reliable resorts should beat cheaper
  low-altitude options with weak spring snow.
- Budget still matters, but not enough to overcome poor snow viability.
- Accessible terrain matters after snow reliability and skill fit are sane.

Dominant factors:
- `active_now`: snow confidence, season fit, terrain scale, skill fit, budget.
- `near_term`: exact season windows, shared terrain domains.
- `future_candidate`: open piste share, recent snowfall, snow depth, grooming.

### 2. Beginner First Trip, Low Hassle

User intent: "First ski trip, nervous beginner, I want it to be easy and not
too expensive."

Expected behavior:
- Beginner-friendly terrain, ski school, rental convenience, and walkable lift
  access should beat huge expert terrain.
- A smaller resort can beat a famous mega resort if it reduces confusion and
  cost.
- Terrain size should not be a universal boost for beginners.

Dominant factors:
- `active_now`: skill fit, stay-base access, budget, travel effort.
- `proxy_only`: beginner piste share where available.
- `known_missing`: ski school quality, rental distance, lesson package price.
- `future_candidate`: beginner package availability and review quality.

### 3. Family With Children And Mixed Confidence

User intent: "Family ski week with children, some beginners, parents are
intermediate."

Expected behavior:
- Ski school, childcare, easy morning logistics, safe beginner terrain, and
  family-friendly stay base should matter strongly.
- Nightlife should not boost by default.
- A result with easy lift/rental/school access should beat a stronger mountain
  with high friction.

Dominant factors:
- `active_now`: skill fit, stay-base access, budget.
- `near_term`: pass products and accessible terrain.
- `known_missing`: childcare, lesson meeting point, family rooms.
- `future_candidate`: hotel-level family amenities and package support.

### 4. Advanced Big-Terrain Trip

User intent: "Advanced skier, I want serious terrain and enough variety for a
week."

Expected behavior:
- Accessible terrain through a linked domain or regional pass should matter
  more than local child ski-area terrain alone.
- Advanced difficulty mix, altitude, and terrain variety should boost.
- Beginner convenience should be secondary unless requested.

Dominant factors:
- `active_now`: terrain scale, skill fit, snow confidence.
- `near_term`: terrain domains, terrain groups, lift-pass scope.
- `known_missing`: advanced piste quality, off-piste/guide requirement.
- `future_candidate`: open lift network, lift queues, expert terrain reviews.

### 5. Short Break, No Car

User intent: "Two ski days, no car, coming by flight or train, I want minimal
wasted time."

Expected behavior:
- Transfer simplicity, car-free stay base, walkable lifts, and compact terrain
  should beat a famous resort with spread-out access.
- Huge accessible terrain matters less than quick arrival-to-ski time.

Dominant factors:
- `active_now`: stay-base access, travel effort when origin is supplied.
- `near_term`: car-free viability, station/airport transfer time.
- `known_missing`: bus frequency, transfer reliability.
- `future_candidate`: live transfer disruption and luggage friction.

### 6. Value Optimizer

User intent: "Best skiing value for money, not just cheapest lodging."

Expected behavior:
- Ranking should consider pass price, lodging cost, terrain access, snow
  reliability, and included products.
- A cheap stay with poor snow or expensive pass should not automatically win.
- Price per accessible piste kilometer can be a useful supporting factor, but
  should not reward huge terrain that does not fit the user.

Dominant factors:
- `active_now`: lodging budget fit, terrain scale, snow confidence.
- `near_term`: lift-pass products and prices.
- `known_missing`: total trip cost and food/transfer cost.
- `future_candidate`: package inclusions and dynamic pricing.

### 7. Crowd-Averse Quiet Slopes

User intent: "I want reliable snow but hate crowds and lift queues."

Expected behavior:
- Snow reliability remains necessary.
- Resorts known for smaller crowds or better lift capacity should beat equally
  snowy but congested destinations.
- Apres/nightlife should not boost and may penalize if user asks for quiet.

Dominant factors:
- `active_now`: snow confidence, terrain scale.
- `proxy_only`: less-famous destination or larger terrain as weak crowd proxy.
- `known_missing`: lift queue time, crowding, holiday peak effects.
- `future_candidate`: occupancy, lift wait feeds, review-derived crowd signal.

### 8. Non-Skier Partner

User intent: "One skier, one non-skier partner; needs a nice town and things to
do."

Expected behavior:
- Non-ski activities, restaurants, scenic town, wellness, and transit access
  should matter when requested.
- Pure-skiing terrain should not dominate if the non-skier experience is poor.

Dominant factors:
- `active_now`: budget, stay-base quality proxy.
- `proxy_only`: destination/stay-base atmosphere tags if curated.
- `known_missing`: non-ski activity inventory, restaurants, wellness.
- `future_candidate`: hotel spa, dining, cultural/day-trip access.

### 9. Luxury Wellness Hotel Trip

User intent: "Premium ski trip with spa, sauna, good food, easy access, and
solid snow."

Expected behavior:
- Hotel-level amenities and lodging quality should strongly matter once hotel
  data exists.
- Snow and access still guard against attractive hotels in poor ski conditions.
- Budget is a preference, not necessarily a hard low-cost constraint.

Dominant factors:
- `active_now`: snow confidence, stay-base quality proxy, access.
- `known_missing`: hotel amenities, half-board, restaurant quality.
- `future_candidate`: provider-backed hotel inventory and amenity matching.

### 10. Late-Booking Conditions Chaser

User intent: "I can book last minute and want the best conditions next week."

Expected behavior:
- Current conditions, recent snowfall, open lifts/pistes, wind, and weather
  disruption should dominate historical averages.
- Static resort quality should matter less than live operational status.

Dominant factors:
- `active_now`: current forecast conditions and weather-derived disruption.
- `near_term`: operational status source URLs.
- `known_missing`: open lift/open piste counts.
- `future_candidate`: provider feeds, official status refresh, alerting.

### 11. Mixed-Skill Group

User intent: "Group with beginners, intermediates, and advanced skiers."

Expected behavior:
- A resort should need enough beginner-safe terrain and enough intermediate or
  advanced variety.
- Extreme advanced terrain alone should not win if beginners are stranded.
- Linked domains can help if access logistics are not painful.

Dominant factors:
- `active_now`: supported skill fit, terrain scale.
- `near_term`: difficulty mix and pass scope.
- `known_missing`: ski school, learning zones, terrain connectivity.
- `future_candidate`: group itinerary compatibility.

### 12. Shared-Domain And Multi-Ski-Area Grouping

User intent: "Show me the best option in a linked area, but do not fill the
whole list with the same ski domain."

Expected behavior:
- Tignes and Val d'Isere can share one linked-domain result group when the
  dominant value is the shared pass/domain.
- Chamonix can show separate ski-area alternatives when the areas create
  materially different trip choices, but should avoid repeated top-level slots
  when the user cares about the destination as a whole.

Dominant factors:
- `active_now`: option-level ranking diagnostics and result-group keys.
- `near_term`: terrain domains, terrain groups, lift-pass scope.
- `known_missing`: user-facing grouping policy.
- `future_candidate`: nested recommendations with best option and alternatives.

## Scenario Acceptance Rules

- A scenario can pass today even when future factors are missing, but the report
  must make the missing factors explicit.
- A factor marked `future_candidate` cannot affect score until it has a source
  and deterministic derivation.
- A factor marked `proxy_only` must be named as a proxy in diagnostics or test
  notes.
- A result should not win primarily because of a low-trust positive factor.
- A hard user constraint should gate or strongly cap incompatible results.
- Shared terrain domains and multi-ski-area destinations should expose grouping
  behavior separately from raw option score.
- Preference-activated factors should not change default ranking unless user
  intent activates them.

## AI-Assisted Search Interpretation

AI search should produce structured intent, not direct rankings.

Target interpretation shape:

```text
intent:
  trip_type: beginner_first_trip
  hard_constraints:
    max_budget_per_night_eur: 250
    no_car: true
  weighted_preferences:
    snow_reliability: high
    beginner_friendliness: high
    low_hassle: high
    terrain_size: low
  avoidances:
    party_heavy: medium
  explanation_hints:
    - "prioritize easy logistics over famous terrain"
```

The deterministic scorer should consume normalized factor preferences. The AI
interpreter may map user language to factor weights, but scoring should remain
auditable and testable.

## Verification Strategy

1. Scenario fixtures
   Create compact fixtures for each golden scenario. Fixtures can be synthetic
   when real catalog data is missing, as long as factor states are explicit.

2. Query interpretation tests
   Mock AI output and test that natural-language intents map to normalized
   factor preferences. Do not test exact LLM prose.

3. Deterministic scoring tests
   Assert expected winners, acceptable alternatives, gated results, and
   grouping behavior.

4. Diagnostics review
   Ranking comparison reports should include factor availability states, top
   positive/negative components, group counts, and missing-factor caveats.

5. Regression suite
   Keep scenario tests as golden tests before changing production search.

## Implementation Boundaries

This spec does not require immediate production scoring changes.

Near-term implementation should focus on:

- encoding golden scenarios;
- extending diagnostics to track factor availability and missing future factors;
- expanding the factor registry shape;
- tuning candidate scoring in diagnostics;
- reviewing output before production ranking integration.

Production `/api/search` should change only after the scenario suite and
diagnostic output make the ranking behavior defensible.

## Open Decisions

- Whether AI interpretation returns a generic set of weighted factors or one of
  several trip-profile templates plus overrides.
- How to represent factor availability states in diagnostic output.
- Which future factors become first-class before the production switch.
- Whether value scoring should use total trip cost, normalized per-day cost, or
  multiple separate cost factors first.
- Whether hotel-level amenities belong in the same factor registry as
  destination/stay-base factors or in a separate accommodation layer.
- How much user-facing explanation should expose missing factors versus keeping
  them as internal confidence caveats.
