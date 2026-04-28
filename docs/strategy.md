# Product Strategy

Durable product strategy for the ski travel planner. This document covers market
positioning, client strategy, AI UX direction, monetization, acquisition, and
longer-term product sequencing. Sprint status belongs in `PROJECT.md`; technical
implementation notes belong in `docs/engineering-notes.md`.

---

## 1. Market Opportunity

### Size and Shape

The ski tourism market is substantial and high-value:
- Alps alone generate ~€25–30B in annual tourism revenue
- North America adds ~$10B
- Active recreational skiers: ~60–70M globally (Europe ~25M, North America ~20M)
- Addressable segment (intermediate/advanced, 30–55, research before booking): ~20–25M in Europe + North America
- Average spend per ski holiday in Western Europe: €1,500–3,000 per person including travel, accommodation, lift passes, and equipment

This is a niche market, not mass consumer scale — but it is a high-income, high-intent niche with a genuine unsolved planning problem.

### Climate Change as a Tailwind

Climate change is actively reshaping skier behaviour right now, not as a background factor. Lower-altitude
Alpine resorts (below ~1,500m) are losing 3–5 weeks of natural snow season per decade. Skiers who
previously trusted "just go to Courchevel in January" are now anxious about booking months in advance.

This creates genuine new demand for conditions-intelligence products that did not exist 10 years ago.
The trust problem — "will there actually be snow when I arrive?" — is the most emotionally charged pain
point in the target audience. The current product is well-positioned to address this.

That means the product should compete on trusted decision support, not on generic AI chat. The more
it helps users understand uncertainty clearly — through timestamps, source visibility, and explicit
distinctions between forecast, reported, and estimated signals — the stronger the positioning becomes.

---

## 2. Competitive Landscape

### Existing Players and Their Gaps

| Player | What They Do | What They Miss |
|---|---|---|
| **OnTheSnow** (Mountain News LLC, owned by Vail Resorts) | Snow reports, resort conditions, mountain cams | No planning, no personalization, no booking; resort-operator perspective |
| **Powder Alert / Snow-Forecast.com** | Snowfall forecasts, powder alerts | No trip planning, no personalization; push-and-forget |
| **Skiline / PisteMap** | Trail tracking, trail maps | On-mountain only, no planning |
| **Liftopia** | Lift pass discounts | Near-defunct; absorbed into Ikon/Epic pass ecosystems |
| **PowderBeds / Ski Boutique** | Ski accommodation booking | Pure booking, no conditions, no discovery |
| **Roam Around / Layla AI** | Generic AI itinerary generation | Zero sport-specific depth, no conditions data, mass market |
| **Google Travel / Booking.com** | Hotels and flights | No ski-specific intelligence, no conditions, no on-mountain utility |

### The Structural Advantage Over Closed Ecosystems

The closest near-term threat is not a startup — it is **Vail Resorts** (Epic Pass) and **Alterra Mountain**
(Ikon Pass). Together they control ~60–70 resorts across North America and Europe and are building
digital ecosystems. However, they are fundamentally closed: they optimise for their own resorts, not
independent discovery.

This is a structural advantage for an independent product. An independent tool can tell a skier
"Courchevel is better for your February window than Verbier this year." Vail and Alterra never will,
because they own both.

### Competitive Window

No well-funded startup has cracked the combination of discovery + conditions + booking + trip companion
in a coherent flow. The gap is real.

The 18–24 month window stated in PROJECT.md is roughly correct but the risk profile differs from what
is assumed:
- **Less risk from incumbents** than expected. Google has been "about to" add sport-specific travel
  features for years and has not. The technical complexity of conditions modelling is non-trivial.
- **More risk from well-funded peers.** A $2–3M seed-funded niche team in Chamonix or Boulder could
  move fast on the same gap.

**Realistic window: 2–3 years. Main competitive risk is a well-capitalised niche startup, not Google.**

---

## 3. Monetization

### Affiliate Revenue (Stage 2)

Booking.com pays affiliates 25–35% of their commission margin, translating to roughly **€15–40 per
completed accommodation booking** in the ski segment (ski hotels are higher AOV than average).

Ski rental affiliate programs (Ski-Set, Ridestore, Snow+Rock) pay 5–8% of booking value — on a
€200–400 rental order, that is **€10–30 per conversion**.

Lift pass affiliate programs are sparse and inconsistent. Ikon and Epic do not run affiliate programs.
Some operators (Ski Solutions UK, Iglu Ski) offer **£20–50 referral fees**.

Realistic affiliate revenue at moderate scale (5,000 MAU actively planning):
- Accommodation conversion rate 3–5% → 150–250 bookings/month
- At €25 average affiliate payout: **€3,750–6,250/month**
- Rental add-on: ~€1,000–2,000/month
- **Year 1–2 ceiling without scale: ~€50–100K/year**

This is proof-of-concept revenue, not a standalone business. Meaningful affiliate income requires
50,000+ engaged MAU, which in turn requires either strong SEO, paid acquisition, or a viral loop.

Booking.com should be treated as the first practical accommodation partner, not as the product's
identity. The right long-term shape is provider-agnostic trip context with affiliate monetization
layered on top of it. That keeps the planner valuable for users who book through Booking.com, book
elsewhere, or already have accommodation arranged.

### Premium Subscription (Stage 3)

Benchmark pricing from comparable outdoor/sports apps:
- AllTrails Pro: ~$36/year
- Komoot: €30–60/year
- Strava: ~€55/year

A ski product with genuinely differentiated utility (trip companion, push alerts, daily conditions chat)
can defensibly charge **€5–10/month or €25–45/season**.

Revenue projections:
- 2,000 paying subscribers at €35/season: **€70K/year**
- 10,000 paying subscribers: **€350K/year**

The subscription model has better unit economics than affiliate at small scale, but requires Stage 3
companion features to justify the price.

### B2B Licensing (Stage 4+)

Ski tour operators (Crystal Ski, Inghams, Ski Solutions, Neilson, Club Med) spend on technology.
A white-label conditions + planning layer could command **€500–2,000/month per operator** at SaaS
pricing. Sales cycles are 6–18 months and require production-grade reliability. Do not prioritise
before the consumer product is proven.

---

## 4. Product Strategy

### Core Product Principles

- **Ski-only focus is critical.** Generalising to multi-sport travel would dilute data quality,
  audience clarity, and positioning.
- **Conditions are the core differentiator.** The product should compete on trusted
  decision support under snow and weather uncertainty, not generic itinerary generation.
- **The product sequence remains discovery -> booking handoff -> companion.** Stored trip
  context is the bridge from planning to daily trip utility.
- **Provider-agnostic trip context matters.** The companion should work whether the user
  booked through the product, booked elsewhere, or already had accommodation.
- **Mobile is the long-term companion surface.** Push alerts, daily conditions, and
  on-mountain guidance are fundamentally mobile behaviors.
- **The resort and conditions dataset is the moat.** Manually curated resort data plus
  conditions history are more defensible than an LLM wrapper.

### Product Principle: Avoid Provider Lock-In

Booking.com is a strong first channel because it is broad, recognizable, and good enough for
learning conversion behavior early. But provider lock-in is strategically weak for this product.
The planner and companion layers should survive regardless of where the user ultimately books.

That means the medium-term model should be:
- affiliate booking handoff where useful
- provider-agnostic trip context in the product
- companion features that still work for users who booked elsewhere or already know where they are staying

---

## 5. Client Strategy

### Web

The React web app should remain the public planning and demo surface in the near term. It is
the easiest way to show the product in a browser, portfolio, or live conversation. Web should
prioritize discovery, planning confidence, evidence visibility, and booking handoff.

Web auth should remain optional and deferred until authenticated trip continuity is valuable
enough to justify the added friction. Anonymous planning should remain available.

### Mobile

The Flutter app should remain the authenticated companion surface. Its role is to prove and
eventually own:
- Google sign-in and backend-owned session identity
- saved current trip context
- current-trip summary and companion events
- future push notifications and trip-specific assistant behavior

Mobile UI polish should focus on companion-specific screens rather than rebuilding the entire
planning experience before the companion value is proven.

### Backend

FastAPI remains the shared product foundation. Search, ranking, current-trip state, auth,
companion events, and future assistant tools should stay backend-owned so web and mobile can
consume the same product model.

---

## 6. AI UX Strategy

### Planning Should Be Intent-First and State-Visible

Planning should not become a generic chat-first experience. Ski planning is a comparison and
refinement task: users need to see constraints, tradeoffs, evidence, and ranked options.

The preferred planning UX is:
- trip brief as the primary input
- inferred constraints shown as editable/removable filter chips
- ranked results with evidence and provenance
- a secondary `Refine filters` panel for manual control

This makes the experience feel AI-native without hiding the state that drives recommendations.
The AI transforms messy intent into structured trip state; the UI keeps that state visible and
controllable.

### Companion Is The Stronger Fit For Chat

A dedicated assistant/chat surface makes more sense after a trip is saved. Companion mode has
the context needed for useful conversation:
- saved resort, ski area, stay base, and travel dates
- current and historical conditions
- companion events and notification history
- user skill level and trip preferences

That assistant should answer grounded trip questions such as:
- "Is today worth skiing?"
- "What changed since yesterday?"
- "Which area should we start with?"
- "Should we adjust plans because of wind or visibility?"

Do not add a generic chat panel only to look modern. Add chat when it can take grounded actions
or explain saved-trip context better than static UI.

---

## 7. Search And Filter Strategy

### Travel Window

The user-facing model should be one `Travel window`, not separate fixed controls for travel
month and exact dates.

The internal states should be:
- no time constraint
- month-level planning
- exact date range planning

Month-only input should remain month-level. Do not convert "March" into March 1-31 because
that implies a full-month trip and would distort companion logic. Exact dates should override
month when present.

### Dynamic Filter Surface

The long-term filter model will likely include many dimensions: spa, food, ski bus, apartment
type, board type, wellness, ski-in/ski-out, family needs, parking, and similar preferences.
Showing all filters upfront would make the app feel like a generic travel search form.

The preferred UX is:
- show only inferred/applied filters as chips by default
- keep manual control in a `Refine filters` panel
- add richer filters only after the underlying data and ranking model can support them credibly

This is a data and ranking problem before it is a UI problem. A filter that cannot be backed by
trustworthy resort or stay-base data should not be exposed.

---

## 8. AI Framework Strategy

The current direct Gemini integration behind a local LLM boundary is enough for parser and
grounded narrative work. Do not introduce an agent framework just because the product has AI.

Framework triggers:
- **Pydantic AI:** consider when backend AI behavior grows into typed tools, dependency-injected
  context, validated structured outputs, and observable agent runs.
- **CopilotKit:** consider when the React app needs a real assistant panel that can read and
  update UI state, render tool-driven components, or support human-in-the-loop confirmations.
- **LangGraph:** consider only for persistent, multi-step, stateful companion workflows such as
  daily trip guidance, plan-B assistance, or notification investigation flows.

Keep deterministic ranking, conditions scoring, and simple parsing outside heavyweight agent
orchestration.

---

## 9. Growth And Launch Strategy

### SEO / Content Strategy is Missing

The conditions calendar idea (PROJECT.md section 7) is potentially the biggest organic growth lever,
but it is buried as a data feature. If built as publicly accessible, indexed content — e.g.
"Best time to ski Tignes: historical snowfall by month" — this becomes a powerful acquisition engine.
Niche travel sites like The Ski Guru built their audiences exactly this way.

This should be a first-class strategic initiative, not an afterthought in the data strategy section.

### Geography is Uncommitted

The roadmap implies Europe-first (Alps focus) but does not commit. This matters for:
- Resort data coverage priorities
- Language, currency, and UX decisions
- Affiliate partner selection
- Launch marketing channels

A European-first approach with Alpine resorts is probably right for a solo builder, but it should be
explicit. North America has more English-speaking digital-native skiers and stronger app-first culture.
Europe has more anxious independent ski travellers (fewer pass ecosystems, more variety in resort choice).

### User Acquisition Path is Absent

There is no section on how the first 1,000 users arrive. This is the most critical gap. The product
can be excellent and fail for lack of acquisition. Options worth evaluating:
- SEO via conditions-calendar content pages
- Ski community seeding (Reddit r/skiing, r/alpineskiing, Facebook ski groups, ski club newsletters)
- Product Hunt / Hacker News launch
- Ski influencer outreach

One of these needs to be in the plan before or alongside Stage 2.

### Seasonality is Unaccounted For

~70% of ski travel happens November–March. Skiers plan 4–12 weeks in advance. A product launched
in May finds few active users until October. Sprint planning should account for the seasonal cycle.

**Target window: deploy by October, before the planning season starts.**

### Conditions History Cold-Start

The conditions calendar feature requires multi-year historical data per resort. Open-Meteo provides
historical weather data going back years — this can be backfilled now. Waiting to start collecting it
creates an unnecessary bottleneck.

---

## 10. Near-Term Strategic Priorities

The next strategy work should focus on turning the working product into something easier to
understand, demo, and validate:

- Move web planning toward the intent-first, chip-based search model before adding more filters.
- Extend parsing to understand travel-window precision, including exact date ranges.
- Keep building companion foundations on authenticated trip context, but avoid broad mobile UI polish
  until the companion value is clearer.
- Treat public resort landing pages and conditions-calendar content as the main organic growth path.
- Add web auth only when it clearly improves cross-surface trip continuity.
