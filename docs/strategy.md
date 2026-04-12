# Product Strategy Research

Research and analysis conducted April 2026. Covers market opportunity, competitive landscape,
monetization model, and assessment of the current product direction.

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

## 4. What the Current Roadmap Gets Right

1. **Ski-only focus** — correct and critical. Generalising to multi-sport kills niche products. Data
   investment, audience clarity, and SEO positioning all depend on staying narrow.
2. **Conditions as the core differentiator** — correct. This is the emotional core of the product
   and the hardest thing for a generic platform to replicate.
3. **Stage ordering** — correct. Discovery → Booking handoff → Companion is the right sequence.
   You need stored trip context before the companion becomes genuinely useful, and affiliate
   revenue still depends on a booking action. But that trip context should not be defined too
   narrowly as an affiliate-booked reservation; it can come from outbound booking, manual
   "already booked" trip entry, or later provider imports.
4. **Mobile as the end state** — correct. Stage 3 features (push alerts, on-mountain chat) are
   fundamentally mobile experiences.
5. **Resort database as the moat** — correct. A manually curated, conditions-history-rich resort
   dataset is defensible and not easily replicated by an LLM or a generalist platform.

### Product Principle: Avoid Provider Lock-In

Booking.com is a strong first channel because it is broad, recognizable, and good enough for
learning conversion behavior early. But provider lock-in is strategically weak for this product.
The planner and companion layers should survive regardless of where the user ultimately books.

That means the medium-term model should be:
- affiliate booking handoff where useful
- provider-agnostic trip context in the product
- companion features that still work for users who booked elsewhere or already know where they are staying

---

## 5. Gaps in the Current Roadmap

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

## 6. Sprint Critique: Sprints 11–13 as Planned

The planned sprints (time-aware planning, comparative views, demo hardening) are good work and the
features are genuinely useful. However, they are sequenced for a product that will ship "later."

The product already has: resort data, real conditions signals, ranking, NL parsing, narrative
generation, and a demo frontend. What it does not have is a live URL, real users, or any revenue
signal.

Spending two more sprints deepening the planning engine — before anyone has used the product — risks
optimising the wrong things. Conditions-calendar and time-window planning are strong features, but
their value is much clearer once you have real user behaviour to validate against.

**Recommended resequencing:**

| Sprint | Focus | Why |
|---|---|---|
| **Sprint 11** | Public deployment | Real URL, forces production problem-solving, enables user feedback |
| **Sprint 12** | First affiliate booking link | First revenue signal, closes discovery→action loop |
| **Sprint 13** | Time-aware planning + conditions calendar | Now grounded in real usage data; SEO asset starts compounding |
