# Feature Spec: Search V4 Factor Registry And Dynamic Refinement

## Status

- Status: accepted
- Owner: solo-builder
- Active search contract: `search-v4`
- Active ranking policy: `search-v4-policy-1`
- Active refinement presentation policy: `search-refinement-presentation-1`
- Related docs:
  - `docs/search-ranking-model.md`
  - `docs/planning-model.md`
  - `docs/data-trust-model.md`
  - `docs/domain-language.md`
  - `docs/superpowers/specs/2026-05-07-trip-context-clarifying-search-design.md`
  - `docs/superpowers/specs/2026-06-20-resort-fit-data-model-design.md`
  - `docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md`
  - `docs/superpowers/specs/2026-07-13-trip-window-weather-forecast-evidence-design.md`
- Related plan:
  - `docs/superpowers/plans/2026-07-15-search-v4-and-trip-window-forecast.md`
- Related ADRs:
  - `docs/architecture/adr/0012-versioned-search-factor-registry-and-ranking-policy.md`
  - `docs/architecture/adr/0013-versioned-forecast-runs-and-latest-run-serving.md`
  - `docs/architecture/adr/0015-load-search-refinements-after-ranking.md`
  - `docs/architecture/adr/0016-use-ai-as-a-cross-product-orchestration-layer.md`

## User Outcome

Snowcast should rank concrete ski-trip configurations according to the user's
actual priorities rather than one universal definition of the best resort. A
user should be able to optimize for concerns such as snow reliability, usable
terrain, pass value, skill fit, access, freeride, night skiing, ski-day apres,
quiet accommodation, or village character.

When the initial brief leaves an important preference ambiguous, Snowcast may
ask a small number of useful follow-up questions. The LLM may decide which
registered concrete factor or objective topics are worth clarifying and
dynamically compose a selected-topic-grounded question from approved
vocabulary. It selects approved answer IDs; server-owned reason and answer copy
plus validated typed intent actions are the only refinement output that may
affect the deterministic search and ranking model.

The active ranking model must remain easy for the owner to inspect. One
high-level document and one versioned policy file must show the active factors,
their groups, weights, activation rules, trust behavior, and exact score
equation.

## Scope

In scope:

- a Search V4 intent model separating constraints, objectives, preferences,
  avoidances, and assumptions;
- a typed factor registry with stable factor IDs and evaluator contracts;
- a declarative, versioned ranking policy with group and factor weights;
- the accepted initial group budgets and bounded importance multipliers;
- an exact, bounded, grouped scoring equation;
- explicit trust, missing-data, lifecycle, and correlation policy;
- factor roles for hard filtering, ranking, clarification, explanation, and
  diagnostic measurement;
- LLM-selected registered concrete factor or objective topics and approved
  answer IDs, with constrained dynamic question copy and server-owned reason,
  option copy, and typed actions;
- deterministic validation and impact simulation before a question is shown;
- automatic reranking after the user selects an answer;
- support for static catalog, derived catalog, planning-evidence, weather, and
  future operational-prediction factors;
- a request-path contract for bulk-loading target-date forecast evidence from
  versioned latest-run heads without provider calls;
- factor-level ranking explanations and model-version visibility;
- representative golden scenarios that define intended Search V4 behavior;
- direct replacement of the unused Search V3 API, scorer, and first-party web
  and mobile client flows;
- a generated human-readable active-factor inventory.

Out of scope for the Search V4 design slice:

- activating poorly covered catalog facts merely because the registry exists;
- implementing forecast acquisition and persistence, which is owned by the
  companion trip-window forecast evidence spec and ADR 0013;
- defining or implementing a provider for predicted open pistes, open lifts,
  skiable snow coverage, or open terrain;
- treating prediction as official operational status;
- open-ended chat, autonomous itinerary construction, or LLM-owned ranking;
- detailed accommodation inventory or package-price ranking;
- implementation task decomposition.

## Product Fit

- The design makes Snowcast more ski-specific by exposing terrain, pass,
  conditions, access, and ski-experience tradeoffs.
- It keeps the conditions-smart core: trip viability remains an explicit group
  rather than one optional marketplace filter among many.
- It avoids a large static filter wall by asking bounded questions only when the
  answer can materially improve the current result set.
- It keeps uncertainty visible. Unknown catalog evidence and low-confidence
  predictions cannot silently become verified absence or full-strength score.
- It avoids generic chat: the LLM interprets user meaning and proposes typed
  refinements, while registered deterministic logic owns candidate eligibility
  and ranking.

## Current Baseline And Motivation

Search V3 filters candidates by country, lodging-budget estimate, quality tier,
skill label, access tolerance, dates, and optional travel constraints. It ranks
lodging quality, terrain scale, skill fit, stay-base access, snow evidence,
conditions, budget, and travel effort. Pass selection is separate and does not
affect global ranking.

Recent catalog curation introduced typed facts for snowmaking, glacier terrain,
snow parks, night skiing, marked freeride routes, official trail maps, ski-day
apres, base elevation, base type, development style, local pace, and local
apres. These facts are stored and source-aware but are not yet search inputs.

Search V4 is required instead of incrementally adding constants to Search V3
because the current model also needs these corrections:

- terrain influence must distinguish ski-area potential, connected-domain
  potential, selected-pass terrain, and pass-accessible terrain;
- skill scoring must evaluate the requested skill rather than the strongest
  label present on the area;
- runtime factor trust must use the catalog trust contract;
- estimated data must not become an unexplained hard exclusion;
- score output must be bounded and must not be presented as a probability;
- operational disruption policy must either affect score or remain only an
  explicit eligibility state;
- brief fields omitted by the user must not silently act like intentional
  preferences merely because the client has demo defaults.

## Domain Model

Bounded contexts touched:

- Planning owns constraints, factor evaluation, ranking policy, impact
  simulation, result explanations, and deterministic reranking.
- AI Assistance owns optional interpretation of user text and dynamic proposal
  of schema-valid refinements.
- Catalog And Data Trust owns slow-changing source facts and their trust state.
- Conditions And Weather Evidence owns refreshed observations, forecasts, and
  future prediction evidence supplied to factor evaluators.

Durable terms:

- `SearchConstraint`: a rule that determines candidate eligibility and does not
  receive a ranking weight.
- `RankingFactor`: a registered dimension of fit with a stable factor ID.
- `FactorDefinition`: declarative metadata, roles, allowed values, lifecycle,
  group, and policy references for one factor.
- `FactorEvaluation`: one candidate's value, normalized utility, trust,
  availability, scope, source trust, prediction confidence, freshness, effective
  evidence cap, and explanation inputs for one factor.
- `RankingPolicy`: the versioned group weights, factor weights, activation,
  missing-data, trust, and correlation rules used by the generic scorer.
- `GroupPriority`: a typed registered group ID plus controlled importance label
  that changes the group's effective budget.
- `SearchPreference`: a typed `prefer`, `avoid`, or `ignore` instruction for a
  registered factor; a `require` instruction is evaluated as a constraint.
- `RefinementProposal`: a constrained LLM-generated question plus server-owned
  reason, answer options, and typed factor-preference or objective actions
  awaiting deterministic validation.
- `RefinementPresentationPolicy`: a separately versioned registry of
  traveller-facing factor topics, approved answer IDs, authoritative option
  reason and option copy, typed intent actions, safe question fallback, and deterministic
  fallback order. Presentation wording does not change score semantics.

Invariants:

- Constraints are evaluated before ranking and are never hidden negative
  weights.
- The LLM cannot create factor IDs, allowed values, weights, utilities, trust,
  candidate scores, or catalog facts.
- Unknown is not equivalent to unavailable.
- A planned, diagnostic, or measured-not-ranked factor contributes zero to
  production ranking.
- A newly activated factor shares a stable group contribution budget; adding a
  factor cannot increase the maximum overall score.
- Static terrain potential, selected-pass coverage, and expected open terrain
  remain distinct values.
- Current or predicted operational evidence is time-scoped and never stored as
  slow-changing catalog truth.
- Party ability does not imply a terrain preference such as freeride.
- A hard travel or season requirement is decided before scoring and cannot be
  weakened by a low default group budget.
- Forecast evidence is aligned to each requested ski day. The latest current
  conditions snapshot is not treated as a requested-date forecast.
- The score is a policy-defined fit score, not a success probability.

## Decision And Review Gate

- Classification: `review-gated`
- High-risk domains touched: ranking correctness, user trust, catalog trust,
  public model wording, API contracts, LLM boundaries, request-path latency,
  and future prediction semantics.
- Developer Decision Checkpoints:
  - resolved:
    - use a declarative versioned policy plus typed factor evaluators;
    - use stable factor groups with bounded contribution budgets;
    - keep constraints separate from ranking factors;
    - let the refinement LLM choose registered concrete factor or objective
      topics, select approved answer IDs, and dynamically compose a constrained
      selected-topic-grounded question;
    - keep deterministic validation, impact simulation, filtering, and ranking;
    - publish one easy-to-find exact equation and generated factor inventory;
    - accommodate future dynamic prediction factors through the same registry
      without treating them as catalog facts;
    - replace Search V3 directly through `POST /api/search`, with no compatibility
      endpoint, runtime model switch, shadow comparison, or V3 rollback path;
    - choose initial weights from reviewed golden scenarios rather than preserve
      Search V3 ordering;
    - expose the bounded numeric value as a `Fit score` rather than probability
      or confidence;
    - make every runtime-ready `clarifiable` factor eligible for LLM refinement,
      including preference factors inactive in the initial search.
    - use the hybrid deterministic refinement gate: eligibility, winner, or
      top-three membership changes are material; a top-three reorder requires a
      `2.0` point pairwise-margin change; a stable-order option requires a
      `5.0` point top-five candidate difference;
    - use default group budgets `30/30/15/10/10/5` for Trip Viability, Ski
      Experience, Stay Practicality, Value, Character, and Travel Effort;
    - apply controlled group multipliers `0/0.5/1/2/4/8` and factor
      multipliers `0.5/1/2` through hierarchical normalization;
    - cap Travel Effort at 30% effective share after normalization and
      redistribute any excess to the other active groups;
    - let group importance change the overall group budget while factor
      importance only reallocates the existing budget inside that group;
    - treat maximum travel duration and known out-of-season dates as
      constraints rather than weighted penalties;
    - replace the supported-skill label bonus with party skill coverage based
      on compatible piste inventory, without inferring freeride preference;
    - activate party skill coverage with neutral-shrunk fallback evidence while
      a focused catalog initiative fills missing difficulty profiles;
    - use factor-shaped evidence readiness instead of one universal catalog-
      coverage gate: comparative factors require broad coverage, sparse
      positive-presence and categorical factors keep unknown neutral and may
      reward trusted explicit matches, and objective factors require a
      comparable request slice;
    - make glacier terrain, snow parks, night skiing, marked freeride routes,
      snowmaking availability, ski-day apres, and local apres runtime-ready
      positive-presence preferences after their reviewed positive-evidence
      threshold, without treating catalog silence as absence;
    - keep snowmaking availability separate from snowmaking coverage percentage
      and use it only as an explicitly preferred conditional resilience input:
      no uplift at natural snow utility `0.75` or above, full need at `0.30` or
      below, and a maximum `0.25` headroom-scaled uplift;
    - keep `lodging_budget_fit` measured with zero ranking weight while all
      current lodging-price evidence is estimated;
    - retain an explicitly supplied lodging budget as an estimate-aware
      constraint with at least `10%` uncertainty flexibility, no ranking bonus,
      and visible estimate provenance;
    - keep kilometre and run-count difficulty profiles distinct, weighting
      source-backed kilometre, run-count, qualitative, and unknown evidence at
      `1.00`, `0.50`, `0.25`, and `0` respectively;
    - compute effective skill fit by shrinking the evidence-unadjusted
      `base_skill_fit` toward neutral `0.50`, rather than multiplying uncertain
      candidates toward zero;
    - use balanced full-utility thresholds of `30%/10 km` for beginners,
      `70%/30 km` for intermediates, and `100%/50 km` for advanced skiers, with
      linear saturation and minimum aggregation across mixed-skill parties;
    - compose climatology and target-date forecast into one trip-window snow
      factor using the accepted per-day horizon caps;
    - derive target-date snowpack outlook from a depth-led physical-driver
      model, with snowfall as a secondary benefit, correlated rain/thaw
      evidence as one deterioration risk, and wind/spread excluded from the
      initial utility;
    - use the reviewed physical-driver response curves and composition defined
      in the canonical ranking model, including the `0.15` fresh-snow modifier,
      `0.25` deterioration limit, and maximum-composed rain/thaw risk;
    - persist immutable forecast runs behind atomic per-area latest-run heads,
      with no request-path provider call and no Redis dependency initially.
    - retain every complete forecast run for 45 days, one canonical daily run
      per source through two years, and one canonical weekly run through five
      years, without purging a current head;
    - use daily Open-Meteo ensemble-mean evidence with ECMWF IFS 0.25 degree
      preferred through lead day 15 and NOAA GEFS 0.5 degree through day 30 and
      as shorter-range gap fallback;
    - acquire and evaluate the representative mid-mountain elevation initially
      while retaining elevation band for later extension;
    - activate `trip_window_snow_fit` with the completed forecast pipeline,
      using the accepted lead-time blend without a separate diagnostic-only
      production phase or mandatory meteorological validation gate.
  - accepted assumptions: none
  - unresolved before implementation activation: none
  - deferred without blocking initial activation:
    - correlation and weights for future operational-prediction factors;
    - named fit bands; initial Search V4 exposes only the numeric `Fit score`.
- ADR status: ADR 0012 accepted for the registry, policy, scorer, and LLM
  ownership boundaries; ADR 0013 accepted for forecast persistence and serving.
  Numeric values remain versioned policy even though the initial values are now
  owner-approved.
- Advisory design-review:
  - reviewers: product-strategy, backend-api, data-trust-source-integrity,
    ui-ux, ai-llm-reliability, security-privacy, observability-ops, performance
  - status: completed
- Advisory feature-review before final handoff:
  - reviewers: product-strategy, backend-api, data-trust-source-integrity,
    ui-ux, ai-llm-reliability, security-privacy, observability-ops, performance
  - status: planned

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Product / Domain | Numeric group and factor weights | They define Snowcast's opinion about ski-trip quality and can change every ranking | Calibrate from representative scenarios; start with expert policy; or collect preference/outcome data later | Resolved: initial expert policy in `docs/search-ranking-model.md`; snowmaking uses a conditional composition rather than an independent weight | Preserve the accepted hierarchy in which group importance changes the group budget and factor importance only reallocates inside it; validate with golden scenarios and do not imply statistical calibration | `docs/search-ranking-model.md` and Search V4 policy |
| Product / Domain | Hard requirement handling | A low baseline group budget must not let an explicitly unacceptable result survive | Model maximums and must-haves as constraints; or use very large score penalties | Resolved: typed pre-score constraints | A request such as at most 15 hours by car excludes candidates before Travel Effort scoring | `docs/search-ranking-model.md` |
| Mixed | Target-date forecast influence | Near-term weather can outweigh historical normal, while long-range predictions are uncertain | One current snapshot; independent additive factors; or a per-day confidence-capped composition | Resolved: per-day climatology/forecast composition with `80/60/40/15/0` lead-time caps | Keeps near-term forecasts influential without double-counting them or claiming exact long-range certainty | Forecast evidence spec and `docs/planning-model.md` |
| Mixed | Forecast sources and resolution | Exact requested-date lookup needs a daily product across the 30-day horizon without overstating long-range precision | ECMWF plus EC46 weekly periods; one coarse daily model throughout; or preferred short-range ECMWF plus extended daily GEFS | Resolved: Open-Meteo ECMWF ensemble mean through lead day 15, daily GEFS ensemble mean through day 30 and as gap fallback, one selected source per date | Keeps daily storage and deterministic lookup while the 15% long-range cap limits the coarse GEFS contribution | Forecast evidence spec and ADR 0013 |
| Product / Domain | Forecast elevation scope | Three elevation bands add provider volume and apparent terrain precision before Snowcast predicts open terrain | Base/mid/upper immediately; or representative mid only with a future-compatible band column | Resolved: mid elevation only initially | Matches existing climatology defaults and preserves later expansion without claiming terrain-wide snow coverage | Forecast evidence spec |
| Technical | Forecast persistence and serving | Search latency and later calibration depend on retaining issue versions without scanning all runs | Overwrite latest rows; query latest by aggregate; Redis-only; or immutable runs plus latest heads | Resolved: immutable runs and atomic per-area heads in Postgres | Supports one bulk indexed request-path query and later forecast-vs-observed calibration | ADR 0013 |
| Mixed | Initial factor activation | Sparse fields can bias results toward heavily curated destinations | One universal coverage gate; factor-shaped readiness with positive-presence and categorical unknown-neutral semantics; or infer missing facts as absence | Resolved: factor-shaped readiness, with only estimated lodging-budget fit excluded from initial ranking | Comparative factors retain coverage gates; sparse source-backed features may reward explicit intent but unknown stays neutral and no feature is universally rewarded merely because it is populated | Search V4 implementation plan and canonical ranking model |
| Product / Domain | Snowmaking preference influence | Snowmaking is useful positive evidence but simple availability should not silently overwhelm the physical trip-window snow factor | Independent factor weight; dynamic weight; or conditional resilience composition | Resolved: preference-activated conditional resilience with need `1` at/below `0.30`, need `0` at/above `0.75`, and maximum headroom-scaled coefficient `0.25` | Unknown and unavailable produce no uplift, availability does not claim coverage or operations, and no independent factor-importance multiplier applies | Search V4 policy and golden scenarios |
| Product / Domain | Estimated lodging-budget constraint | Removing the estimated ranking factor does not decide whether an explicit budget may still exclude candidates | Keep an estimate-aware hard constraint with visible warning/flexibility; make it soft/non-excluding; or disable it until stronger data exists | Resolved: explicit budgets remain estimate-aware eligibility constraints with at least `10%` uncertainty flexibility; no lodging ranking factor | Only clearly non-overlapping candidates are excluded and the response must expose estimated provenance | Search V4 request contract and UI acceptance |
| Technical | API replacement | A richer intent, breakdown, and clarification contract is awkward in the current GET query | Directly replace it with `POST /api/search`; no compatibility endpoint or runtime model switch | Resolved | Appropriate because there are no users or external consumers; remove V3 after the new flow passes its own acceptance tests | Search V4 implementation plan and API docs |
| Product / Domain | Public score presentation | A bounded utility score is interpretable but is not a probability | Show numeric `Fit score` and breakdown; add named bands only after separate threshold review | Resolved for numeric score; bands deferred | Keep evidence confidence separate from ranking fit | `docs/search-ranking-model.md` and UI spec |

## Architecture

### Components

```text
user brief and explicit controls
  -> LLM-assisted typed intent parsing
  -> SearchIntent constraints and known preferences
  -> candidate generation
  -> factor evaluator registry
       catalog facts
       catalog trust
       climatology and historical planning evidence
       bulk latest-run target-date forecast evidence
       future operational predictions
  -> versioned deterministic ranking policy
  -> ranked configurations and factor breakdowns
  -> result-difference and factor-coverage summary
  -> LLM RefinementProposal
  -> deterministic schema, relevance, and impact validation
  -> user answer as typed preference patches
  -> deterministic reranking
```

Planned executable boundaries:

```text
app/config/search-ranking/search-v4.toml
app/domain/search_factors/registry.py
app/domain/search_factors/<factor-family>.py
app/domain/search_ranking.py
app/domain/search_refinement.py
app/tools/explain_search_policy.py
```

Forecast acquisition is a background/provider boundary rather than a factor
evaluator responsibility:

```text
forecast refresh trigger
  -> provider client
  -> immutable forecast run and daily rows
  -> validation
  -> atomic per-area latest-run heads
  -> one bulk repository read for candidate ski areas and requested dates
  -> pure trip-window snow evaluator
```

Static constraints narrow candidate area IDs before the forecast preload. The
search request never calls a weather provider, queries one area at a time, or
finds the latest run through a per-request `MAX(issued_at)` scan.

The paths are design targets and may be refined by the implementation plan
without changing the ownership boundaries.

### Declarative Search Policy

The versioned policy is the source of truth for:

- model ID and score range;
- constraint and factor inventories;
- factor group weights and within-group weights;
- lifecycle and activation modes;
- filter, rank, clarification, explanation, and diagnostic roles;
- allowed preference operations and controlled values;
- unknown utility and trust behavior;
- correlation groups and combined-contribution caps;
- user-importance multipliers;
- material-impact thresholds used to validate proposed clarifications.

The policy must not contain executable business expressions, provider calls, or
arbitrary Python import paths. Code maps stable evaluator IDs to typed
implementations.

Every factor definition must expose at least:

| Field | Purpose |
| --- | --- |
| `factor_id`, `label`, `description` | Stable identity and human meaning |
| `group_id`, `scope`, `source_kind` | Ownership and contribution category |
| `evaluator_id`, `value_type` | Typed code boundary and normalized value shape |
| `lifecycle`, `activation`, `roles` | Whether and when the factor can act |
| `allowed_modes`, `allowed_values` | Valid constraints and preference patches |
| `weight`, `importance_policy` | Versioned influence when active |
| `evidence_mode`, `readiness_policy` | Comparative coverage, sparse positive-presence, categorical-match, request-slice objective, or composed-prediction readiness |
| `composition_target`, `composition_policy` | Optional typed factor/component relationship such as snowmaking resilience modifying `trip_window_snow_fit` |
| `unknown_utility`, `evidence_cap_policy` | Missing, trust, confidence, and freshness behavior |
| `correlation_group` | Double-counting protection |
| `clarifiable`, `llm_description` | Bounded capability supplied to refinement generation |
| `explanation_policy` | User-facing factor and uncertainty wording inputs |

Constraints that are not ranking factors use a parallel typed inventory with a
stable ID, value type, validation, trust requirement where applicable, and
client/LLM exposure roles, but no group or ranking weight.

Each group definition exposes its stable ID, label, description, default
budget, allowed importance labels, optional maximum effective share,
clarification role, and LLM-safe description. The LLM can refer only to these
registered group IDs.

Factor activation and clarification are orthogonal:

- `activation = always` contributes whenever its required context exists;
- `activation = when_requested` contributes only after a parsed or selected
  preference activates it;
- `activation = objective_selected` contributes when its optimization objective
  is selected;
- `clarifiable = true` allows the LLM to propose activating or prioritizing the
  factor even when it contributed nothing to the initial search.

Only runtime-ready factors may be clarified. Planned, diagnostic, or
measured-only factors are not shown as questions until an answer can produce
real filtering, ranking, or explanation behavior.

### Generic Scorer

For candidate `c`, search intent `q`, and factor `i`:

- `r_i(c, q)` is the evaluator's normalized utility in `[0, 1]` after applying
  `prefer` or `avoid` semantics;
- `t_i(c)` is the factor-policy-derived effective evidence cap in `[0, 1]`;
- `b_i` is the factor's documented neutral or fallback utility;
- `m_i(q)` is the configured user-importance multiplier;
- `w_i` is the factor weight inside its group;
- `e_i(c, q)` is the deterministic effective weight after importance and any
  declared correlation cap, with `e_i = w_i * m_i` when no cap applies;
- `W_g` is the group weight.
- `M_g(q)` is the bounded policy-defined multiplier for how important the user
  says the group is, with `M_g = 1` at normal importance.
- `P_g(q)` is the final normalized group share after any group-specific maximum
  effective share.

Trust-adjusted utility:

```text
u_i = b_i + t_i * (r_i - b_i)
```

Group score over the factors active for this search:

```text
G_g = sum(e_i * u_i) / sum(e_i)
```

Group allocation and overall fit score:

```text
raw_group_budget_g = W_g * M_g
P(q) = capped_normalize(raw_group_budgets, max_effective_share)
Score(c, q) = 100 * sum(P_g(q) * G_g)
```

`capped_normalize` redistributes any excess from a capped group proportionally
across the other active groups until the shares sum to `1`. Policy validation
requires at least one active ranking group and active-group caps summing to at
least `1`. With no feasible allocation, search may return constraint-qualified
unscored results and propose clarification but must not fabricate a fit score.

The generic scorer must remain bounded in `[0, 100]`. A correlation cap may
reduce the combined effective weights of factors representing overlapping
evidence. Its exact algorithm and resulting effective weights must be visible in
the policy, per-result breakdown, and generated model explanation.

Attribution for one factor is therefore inspectable as:

```text
factor_contribution_i =
  100 * P_g(q)
      * (e_i / sum(e_i in group g))
      * u_i
```

The displayed breakdown must state whether a contribution is the
default-policy maximum or the actual contribution for the current intent.

`M_g` is necessary because changing factor weight only inside Character, Value,
or Ski Experience cannot express that the whole category is a major user
priority. The brief parser may emit only a controlled importance label; the
policy maps that label to `M_g`. It cannot emit the multiplier itself.

Group-priority patches and factor-preference patches are different typed
contracts. A group patch contains a registered `group_id` and importance. A
factor patch contains a registered `factor_id`, preference operation,
controlled values where applicable, and factor importance. The brief parser may
produce either contract but never collapse them into one ambiguous weight. In
this refinement slice, the refinement LLM emits neither patch contract: it
selects registered concrete factor or objective topics and approved answer IDs,
and the server resolves them to typed factor-preference or objective patches.
Group-priority questions are not generated.

An evaluator must preserve source trust, prediction confidence, calibration,
and freshness as distinct inputs. A factor-specific evidence-cap policy derives
`t_i`; the result breakdown must expose both the effective cap and the component
evidence state instead of presenting prediction confidence as catalog trust.

### Preference And Constraint Semantics

- `prefer`: use the factor's normal utility direction.
- `avoid`: invert the factor utility where the factor supports avoidance.
- `ignore`: do not activate the factor for this search.
- `require`: convert the typed requirement into a pre-score eligibility check.
- importance affects the configured multiplier, not an arbitrary LLM-provided
  number.

An explicit requirement must declare its minimum acceptable trust. Unknown
normally does not satisfy a verified must-have. For a soft preference, unknown
uses the documented neutral utility and must not be treated as verified absence.

An explicit lodging budget is a typed, estimate-aware constraint rather than a
ranking factor. Catalog lodging ranges receive at least `10%` uncertainty
flexibility, or a larger user-provided `budget_flex`; only clear non-overlap
excludes an option. The response exposes the estimate and applied flexibility.
No explicit lodging budget means that lodging estimates have no search effect,
and a cheaper estimate never receives a ranking bonus.

### Group Budgets And Correlated Evidence

Initial group names should cover:

- trip viability: `30`;
- ski experience: `30`;
- stay practicality: `15`;
- value: `10`;
- character: `10`;
- travel effort: `5`.

Travel Effort additionally has `max_effective_share=0.30`. Other initial groups
have no lower policy cap. If inactive groups would otherwise push Travel Effort
above 30%, its excess is redistributed among the remaining active groups.

Weights are normalized inside each group, and group weights are normalized in
the overall score. Adding a factor therefore redistributes an existing group
budget rather than increasing the possible score.

Controlled group importance is:

```text
ignore=0, secondary=0.5, normal=1, important=2, primary=4, very_high=8
```

Controlled factor importance is:

```text
low=0.5, normal=1, high=2
```

Group importance multiplies the default group budget before normalization.
Factor importance only changes the factor's share inside the already effective
group budget. With all groups active, `very_high` Travel Effort therefore has
`40 / 135 = 29.63%`, while `very_high` Ski Experience has
`240 / 310 = 77.42%`. The labels are relative to policy priors, not target
absolute shares.

Initial core factor weights are:

- Trip Viability: composed `trip_window_snow_fit=1`;
- Ski Experience: `accessible_terrain_scale=3`,
  `party_skill_coverage=2`, and each explicitly activated terrain preference
  `=2`;
- Stay Practicality: `stay_base_access=1`;
- Value: one selected pass-price or pass-terrain objective `=2`;
- Character: each requested character factor `=1`;
- Travel Effort: `travel_effort=1` when an origin exists.

Unlisted factors have no implicit weight. They stay non-active until their
weight, coverage, trust, and correlation behavior are reviewed.

`lodging_budget_fit` is initially measured with zero ranking weight because all
current stay-base price ranges are estimated. Snowmaking availability has no
independent Trip Viability weight. When explicitly preferred, it supplies the
canonical per-day conditional resilience input to `trip_window_snow_fit`; the
composition is visible in the factor breakdown.

Closely related factors must declare a correlation group or composition rule.
For example, snow reliability, predicted snow coverage, predicted open-piste
ratio, and predicted open-lift ratio may share evidence. Search V4 must prevent
these signals from being added as four independent full-strength reasons.

Climatological snow reliability and target-date snowpack outlook use an exact
composition rather than a correlation cap. For each ski day, effective
forecast share is its lead-time cap multiplied by valid-date coverage. Missing,
stale, or incomplete rows have zero coverage. The initial model adds no second
provider-confidence or calibration multiplier because the lead-time blend is
the accepted uncertainty policy. The maximum forecast caps for `0–5`, `6–10`,
`11–16`, `17–30`, and more than `30` days are respectively `0.80`, `0.60`,
`0.40`, `0.15`, and `0`.

## Factor Inventory Direction

The initial implementation plan should classify each candidate as active,
measured, diagnostic, or planned based on actual coverage and trust.

### Always-On Or Context-Core Candidates

- season viability as an eligibility constraint, not a ranking factor;
- `trip_window_snow_fit`, composed per ski day from climatological snow
  reliability and target-date snowpack outlook;
- party skill coverage based on compatible piste inventory;
- accessible terrain scale with explicit source and pass scope;
- stay-base access practicality;
- travel effort when origin is available.

Party skill coverage uses easier terrain for beginners, easier plus
intermediate terrain for intermediates, and the complete classified network for
advanced skiers. It combines compatible kilometres and difficulty share with a
reviewed saturation curve. Ability never activates freeride or another terrain
preference.

### Preference-Activated Candidates

- maximum terrain potential;
- lift-network scale or strength when its derivation is source-backed and
  comparable;
- lowest pass price or pass price per ski day;
- pass-accessible terrain value;
- marked freeride routes;
- future lift-accessible off-piste terrain;
- snow park;
- night skiing;
- glacier terrain;
- snowmaking availability;
- ski-day apres;
- local apres;
- local pace;
- development style;
- base type.

Official trail-map URLs remain evidence/display links rather than ranking
factors. Stay-base elevation and piste difficulty may feed explicit derived
factors, but must not become hidden duplicate contributions. Snowmaking
coverage percentage remains planned until comparable source-backed coverage is
available; snowmaking availability may be preference-activated earlier.

### Evidence-Mode Readiness

The initial policy does not apply one catalog-completeness threshold to every
factor. A concrete non-unknown input counts as resolved coverage, while its
trust status independently supplies evidence strength; `needs_source` has zero
strength.

Always-on comparative factors require `90%` resolved coverage and average
evidence strength `0.70`. Requested comparative factors require `75%` and
`0.50` in their applicable catalog or request slice. Party skill is the
reviewed exception and uses neutral shrink while its data gap is filled.

Positive-presence factors become runtime-ready when their evaluator and source
policy are reviewed and at least three catalog entities have verified positive
evidence. Verified availability maps to raw utility `1`, verified
unavailability to `0`, and unknown to neutral `0.5`; evidence strength shrinks
the result toward `0.5`. The policy applies this mode to glacier terrain, snow
parks, night skiing, marked freeride routes, ski-day apres, and local apres. It
does not require broad negative-evidence coverage and does not activate these
factors without explicit or clarified preference.

Snowmaking availability uses the same minimum verified-positive readiness rule
but has specialized composition semantics. When preferred, verified
availability supplies a source-strength-capped, headroom-scaled uplift to the
natural per-day snow utility. Need is zero at natural utility `0.75` or above,
linear to full need at `0.30`, and the maximum coefficient is `0.25`. Unknown or
unavailable produces no uplift, while the states remain distinct for
explanation and a verified requirement. Snowmaking has no independent weight
or factor-importance multiplier and does not claim coverage, operation, or open
terrain.
Generic apres preference evaluates availability; an intensity-specific apres
preference evaluates the controlled intensity as a categorical qualifier, so
available-but-unclassified apres remains neutral for a request such as lively
or quiet rather than receiving a false full match.

Categorical-match factors use trusted match `1`, trusted mismatch `0`, and
unknown `0.5`, subject to evidence shrink. Base type, development style, and
local pace, plus intensity-qualified apres, may therefore reward known matches
even with sparse global coverage. Request-slice objective comparisons retain
their `75%` coverage and `0.50` strength gate and require comparable duration,
audience, currency, season, and terrain scope as applicable. Prediction factors
retain their own date-coverage, freshness, and confidence policy.

### Future Dynamic Candidates

- expected open piste kilometres and ratio;
- expected open lift count and ratio;
- expected snow-coverage ratio;
- expected pass-accessible open terrain;
- operational-outlook confidence.

Dynamic values must include target window, issue time, forecast horizon,
provenance, confidence, and exact ski-area, terrain-domain, or pass scope. They
belong to planning or conditions evidence, not the static catalog.

Forecast snow depth is a modelled point/elevation value and must not be named or
interpreted as ski-area snow-cover percentage, open-piste ratio, or expected
open kilometres. The latter require separate operational evidence or prediction
models.

## Dynamic Search Refinement

### LLM Ownership

The LLM dynamically selects registered concrete factor or objective topics,
writes a question using only their approved vocabulary plus bounded generic
question words, and selects approved answer IDs rather than emitting labels or
raw patches. The server owns reason copy, resolves every answer ID to
authoritative presentation copy and typed factor-preference or objective
patches, and replaces unsafe, sensitive, unsupported, or ungrounded questions
with deterministic fallback before the existing legality, actionability, and
materiality gates run. Group-priority patches remain part of Search V4 and the
parser's typed-patch capabilities, but group-priority refinement questions are
not generated in this slice.

The factor registry describes scoring capabilities and clarification legality.
The separate `search-refinement-presentation-1` registry owns traveller-facing
factor topics, approved answers, option labels and descriptions, typed actions,
and deterministic fallback copy/order. Changing its wording does not change the
score equation, active factor inventory, or ranking-policy weights.

The LLM may:

- interpret ambiguity or missing priorities in the user's wording;
- decide which one or more registered concrete factor or objective topics would
  be useful to contrast;
- dynamically write only a selected-topic-grounded question from the supplied
  approved vocabulary;
- select two to five options using only approved answer IDs;

One option may combine approved answer IDs from several selected topics, with at
most one answer for each factor. The server compiles those IDs into authoritative
labels, descriptions, and typed factor-preference or objective actions.

The LLM may not:

- invent a factor ID, operation, controlled value, or constraint;
- invent an answer label, description, patch, fact, numeric claim, or ID;
- provide numeric weights, normalized utilities, trust, or candidate scores;
- filter or reorder candidates directly;
- promote user text into catalog or planning evidence.

### Refinement Input

The model should receive a bounded summary containing:

- the parsed brief and known typed preferences;
- assumptions and unresolved intent;
- the top result set's factor differences, without unsupported prose;
- factor coverage and unknown rates within the candidate set;
- registered presentation topics and approved answer IDs for every runtime-ready
  clarifiable factor, including `when_requested` and `objective_selected`
  factors inactive in the initial score;
- already asked or answered refinements;
- a strict structured-output schema.

Raw internal source documents, arbitrary catalog payloads, provider secrets, and
unbounded candidate lists must not enter the prompt.

The trip brief is untrusted text. Prompt instructions must treat it only as
planning content, and structured-output validation must prevent embedded
instructions from expanding capabilities or bypassing the registry.

### Deterministic Validation And Impact Gate

Each proposal must be rejected unless:

- every factor, operation, and value exists in the runtime-ready registry and
  every selected answer ID belongs to a selected topic;
- every target factor allows a clarification role;
- patches are type-valid and do not contain model-defined weights;
- options are distinct and do not merely repeat a known preference;
- enough candidates have trustworthy data for the question to be useful;
- evidence-mode-specific actionability holds: positive-presence needs at least
  one trustworthy non-neutral outcome and two distinct effective utilities,
  categorical matching needs trusted utility variation, and comparative or
  objective factors meet their request-slice coverage gate;
- the patches can be evaluated without mutating production state;
- simulation activates currently inactive requested/objective factors exactly
  as the answer would;
- simulating the answers passes the hybrid material-impact gate defined in the
  canonical ranking model; explanation-only changes are insufficient.

The LLM chooses what may be worth asking; the deterministic impact gate decides
whether the proposal is safe and useful enough to show. If validation fails,
the system may offer one material registry-backed factor question or show no
question. Search must remain usable through explicit controls without the LLM.

### Interaction

- Initial results should not be blocked by optional preference questions.
- Show at most one to three refinements, prioritizing conversational relevance
  and deterministic impact.
- Render each dynamic traveller-facing question as the heading with two to five
  keyboard-operable server-owned options and no internal policy vocabulary.
- If admission returns a bounded `429`, show a compact `retrying` state, wait for
  a valid `Retry-After` of at most 15 seconds, and retry once while results remain
  usable.
- A terminal optional discovery failure is announced politely and leaves no
  persistent visible error or refinement card.
- Selecting an answer applies visible preference chips and reruns search
  immediately.
- The user can remove or edit any inferred or selected preference.
- Results explain the relevant factor matches, misses, and unknowns rather than
  exposing internal debug terminology.

## API And Client Contract

The Search V4 contract should represent:

```text
SearchIntent
  constraints
  objectives
  group priorities
  preferences
  avoidances
  assumptions
  travel context
```

Search responses should include:

- separate search-model and ranking-policy versions, so an API or algorithm
  contract remains distinguishable from a reviewed weight or activation change;
- a separate refinement-presentation-policy version on refinement responses, so
  traveller wording and answer presentation can evolve without implying a
  scoring-policy change;
- normalized results and recommendation groups;
- applied constraints, group priorities, and factor preferences;
- per-result factor values, trust, contribution, and scope;
- score and group breakdown;
- coverage or unknown warnings relevant to requested preferences;
- zero to three validated refinement proposals;
- enough typed state to apply an answer and rerun deterministically.

`fit_score` is numeric for every feasible active-group allocation. The response
also exposes `ranking_status = ranked|unscored` and an optional typed
`unscored_reason`. The exceptional case where all groups are inactive or their
caps cannot form a complete allocation returns constraint-qualified candidates
in stable non-recommendation order, no fabricated numeric score, and a
clarification opportunity. Clients must not present that order as ranked fit.

Search V4 directly replaces the existing unused contract as `POST /api/search`.
The implementation updates the web client and tests in the same cutover and
then removes the Search V3 GET route, hardcoded scorer, model-selection flags,
and V3-only tests. The response still exposes separate search-model and
ranking-policy versions for reproducibility, not compatibility.

## Data Trust And Source Integrity

- Catalog-backed evaluations must consume the trust-manifest status of their
  exact source group.
- `verified` and `verified_with_adjustment` may receive full source-backed
  influence subject to factor policy.
- `estimated` receives a reduced cap and must remain visibly estimated.
- `needs_source` cannot receive positive source-backed influence.
- Explicit `unavailable` with trustworthy evidence differs from `unknown`.
- Scope must remain explicit: ski area, terrain domain, pass product, stay base,
  or one concrete trip configuration.
- Pass value must compare equivalent durations, currencies, audiences, and
  applicable seasons. A curated default pass must not define intrinsic
  destination value.
- Numeric comparison bounds must exclude evidence with zero source strength.
  Mixed currencies are not normalized together, and differing season-specific
  prices remain unresolved when the request does not select a season.
- Marked freeride routes must remain distinct from generic lift-accessible
  off-piste terrain and classified pistes.
- Predicted values require time-scope and uncertainty policy separate from
  static catalog trust. The initial weather factor expresses uncertainty with
  reviewed lead-time/climatology shares; future operational predictions may
  require different confidence and calibration policy.
- A provider's raw confidence label is never automatically an evidence cap.
- Forecast evaluations retain provider/model/run, issue time, valid date, lead
  time, elevation, date coverage, ensemble basis, spread, freshness, and policy
  version as separate fields.
- Forecast issue rows never enter archive climatology, and modelled snow depth
  is never relabelled as ski-area snow coverage or operational availability.

## AI / LLM Use

Deterministic logic that must not use an LLM:

- candidate generation and eligibility;
- factor evaluation and trust adjustment;
- score calculation and result ordering;
- pass-price arithmetic and terrain-scope selection;
- refinement-schema validation and impact simulation;
- fallback search behavior.

Allowed LLM use:

- parse the brief into typed context and preferences;
- identify useful concrete factor or objective clarification topics from the
  bounded registered set;
- select approved refinement topic IDs and answer IDs and compose only the
  constrained dynamic question;
- generate explanations only from supplied typed factor evaluations.

Prompt and output boundaries:

- structured output only;
- stable factor IDs and controlled values supplied by the application;
- no raw model response trusted without validation;
- no raw brief or prompt logged by default;
- bounded candidate summary and factor count;
- one provider attempt within the endpoint deadline;
- one browser admission retry at most after a bounded `429` and valid
  `Retry-After`, with results remaining usable;
- one material registry-backed factor fallback at most, otherwise no question;
- cache only when privacy-safe and keyed without retaining raw sensitive text.

The provider-facing structured-output schema contains only topic IDs, answer
IDs, and bounded question text. Full Pydantic bounds, selected-topic vocabulary
and sensitive-copy gates, presentation-registry resolution, safe-copy fallback,
and deterministic policy validation remain application-owned. Approved reasons,
labels, descriptions, and typed actions never come from the provider. Validate
proposed questions independently so one invalid sibling cannot discard another
question that passed every gate.

## Security, Privacy, And Abuse

- User briefs may contain origin, budget, party, or accessibility details and
  must be treated as user-provided planning context.
- Raw briefs, prompts, and responses must stay out of logs, metrics, and traces.
- Observability should record only low-cardinality model version, outcome,
  latency, validation failure category, and aggregate token/cost data.
- Structured patches must be size-limited and schema-validated.
- Public identifiers, display text, free-form briefs, travel-window spans, and
  request collections must have explicit schema bounds. Refinement questions,
  answer options, and patches use tighter policy limits inside those hard
  schema bounds.
- Free-form question text is display-only and must not become executable input.
- Rate and timeout controls must keep refinement failure from blocking core
  search.

## Background Work

Search factor evaluation, reranking, and clarification validation remain
request-path functions over preloaded evidence. Target-date forecast evidence
is produced by the separate Worker / Function / Trigger design in
`2026-07-13-trip-window-weather-forecast-evidence-design.md`: a scheduled
refresh function fetches provider data, persists a versioned run, validates it,
and atomically advances per-area latest-run heads. Search is only a consumer.

Future operational predictions need their own acquisition and calibration
design before activation. They do not overload the weather forecast worker or
the static catalog.

## Performance And Operations

- Factor evaluators should be pure and side-effect-free over already loaded
  catalog, planning, and prediction evidence.
- Static constraints should narrow candidate ski-area IDs before one indexed
  bulk query joins those IDs and requested dates through forecast heads to
  daily forecast rows.
- Search must not call forecast providers, issue per-candidate forecast queries,
  or calculate the latest run through a request-path aggregate scan.
- Postgres is the initial forecast serving source. Add a cache only after
  measured request-path latency demonstrates a need.
- Impact simulation should reuse candidate evaluations and rerank typed patches;
  it must not repeat provider fetches or planning queries for every answer.
- The LLM refinement call should run after initial deterministic results exist
  and may be independently timed out.
- Search results remain usable when the refinement call fails or is skipped.
- Policy-defined caps must bound candidate summaries, clarifiable factors,
  proposed questions, answer options, and simulated reranks. Simulation reuses
  factor evaluations and performs no provider or LLM call per option.
- Metrics should cover factor-evaluation latency, ranking latency, refinement
  latency, proposal validation outcomes, questions shown, answers selected, and
  reranking completion without high-cardinality factor-value labels.
- Forecast metrics should cover refresh completion/failure, head age, valid-date
  coverage, incomplete runs, and bulk preload latency without resort, exact-date,
  or run-ID metric labels.

## Documentation And Policy Visibility

`docs/search-ranking-model.md` is the easy-to-find human-readable model. It must
show the active production version, exact equation, group weights, factor
inventory, activation modes, trust/missing semantics, and current limitations.

The Search V4 implementation should add a command conceptually equivalent to:

```bash
uv run python -m app.data.explain_search_policy
```

The command should render:

- active and non-active factor counts;
- group weights;
- group importance multipliers, maximum effective shares, and redistribution
  policy;
- factor weights and maximum overall contributions;
- constraints and factor roles;
- lifecycle, trust, unknown, and correlation policies;
- evaluator registration status.

CI must validate that the generated inventory in the model document matches the
versioned policy.

## Rollout

1. Introduce the typed registry, declarative policy parser, generic scorer,
   policy-explanation command, and generated model inventory.
2. Implement corrected core evaluators using the accepted initial policy and
   validate it against reviewed golden scenarios.
3. Activate reviewed source-aware positive-presence and categorical catalog
   factors when requested; keep request slices that fail comparative pass/value
   gates neutral rather than fabricating coverage.
4. Add source-keyed versioned ECMWF/GEFS acquisition, daily mid-elevation rows,
   and the bulk latest-run consumer without changing the production search
   contract yet.
5. Implement and verify the active `trip_window_snow_fit` evaluator, including
   its conditional snowmaking composition and climatology fallback. There is no
   diagnostic-only production or historical meteorological validation gate.
6. Implement manual typed preference patches and deterministic impact
   simulation, then add bounded dynamic LLM proposals over the complete
   runtime-ready clarifiable registry.
7. Replace the search API and first-party web and mobile clients with the one
   complete Search V4 model, enable forecast refresh after manual verification,
   and remove Search V3 code, configuration, compatibility logic, and tests.
8. Run API, UI, mobile, golden, performance, security/privacy, operations, and
   advisory feature reviews on the final search model.
9. Add future operational-prediction factors first as diagnostic inputs and
   activate them only after calibration and source semantics are reviewed.

## Acceptance Criteria

- The active ranking equation and every active factor are visible from one
  high-level document.
- A versioned policy is the executable source for groups, weights, lifecycle,
  roles, trust, missing-data, and correlation behavior.
- Every configured factor has a typed evaluator and every evaluator has a
  configured factor definition.
- Constraints and ranking factors remain separate.
- Search scores are bounded and reproducible for identical inputs and evidence.
- Adding a factor cannot silently increase a group's total score budget.
- Unknown and unavailable produce different behavior.
- Positive-presence features may reward verified availability after explicit or
  clarified intent without broad proof of absence, and they never create an
  always-on feature-count bonus.
- Snowmaking availability is distinct from percentage coverage and modifies
  `trip_window_snow_fit` only through the explicitly requested, capped
  conditional-resilience composition.
- `lodging_budget_fit` remains measured with zero ranking weight while its
  source evidence is entirely estimated.
- An explicit lodging budget applies only the estimate-aware eligibility rule
  and never contributes a cheaper-is-better ranking bonus.
- Party skill coverage uses compatible piste inventory and never infers a
  freeride or other terrain preference from ability.
- Default group budgets, group multipliers, factor multipliers, and actual
  per-search normalized shares are visible and reproduce the documented
  examples.
- A maximum journey duration is enforced before scoring and is unaffected by
  Travel Effort's group budget.
- The latest current-conditions snapshot does not stand in for a target-date
  forecast.
- Exact-date snow fit applies the documented per-day forecast caps, selects the
  configured eligible source, and falls back to climatology when valid evidence
  is missing.
- Month-only searches use climatology without current-snapshot assistance.
- Terrain explanations identify ski-area, domain, or pass scope.
- Future predicted availability factors can use the registry without becoming
  catalog facts.
- The LLM can dynamically select any registered concrete factor or objective
  topic for a clarifiable runtime-ready factor, including factors inactive in
  the initial search, and write its constrained question without emitting
  reason/option copy or raw patches.
- Invalid, unsupported, non-actionable under their evidence mode, repetitive,
  or immaterial proposals are discarded deterministically.
- Selecting a refinement answer applies visible typed preferences and reruns
  deterministic search.
- Search succeeds without an LLM refinement response.
- Search V3 is removed after the Search V4 endpoint, web/mobile clients, and
  golden scenarios pass their own acceptance tests.

## Verification

Unit tests:

- policy parsing and validation;
- factor-registry completeness;
- factor evaluator normalization and trust adjustment;
- effective evidence-cap composition while preserving source trust, prediction
  confidence, calibration, and freshness separately;
- exact score equation, bounds, group normalization, and correlation caps;
- group-versus-factor importance hierarchy, including `very_high` Ski
  Experience and Travel Effort examples;
- constraints versus preference semantics;
- hard maximum travel duration before scoring;
- party-skill coverage for beginner, intermediate, and advanced parties without
  automatic terrain-preference activation;
- unknown, unavailable, estimated, and conflicting-evidence behavior;
- refinement proposal validation and impact simulation;
- prompt-injection attempts, output-size bounds, proposal/option caps, timeout,
  and deterministic fallback;
- predicted-evidence time and confidence handling.
- per-day forecast/climatology composition at every horizon boundary, partial
  date coverage, stale/incomplete runs, and no-forecast fallback.

API and integration tests:

- direct `POST /api/search` request and response schema;
- deterministic results with and without the refinement service;
- removal of the old GET contract and model-selection behavior;
- web and mobile clients submit the typed POST contract and parse the V4 result
  hierarchy;
- factor breakdown and model-version exposure;
- one bounded bulk forecast preload with no provider call or per-candidate
  repository query;
- distinct search-model and ranking-policy version exposure;
- answer-patch application and reranking.
- typed unscored response when no feasible active-group allocation exists.

UI and manual checks:

- initial results remain available before optional clarification;
- dynamic questions are understandable and relevant;
- applied preferences are visible, editable, and removable;
- answers rerun search immediately;
- unknown evidence is not presented as absence;
- score labels do not imply probability;
- an exceptional unscored response is labelled as unranked and its stable order
  is not presented as recommendation strength;
- desktop and mobile-web-viewport refinement flows remain usable; the Flutter
  companion may ignore optional refinement proposals in the initial cutover.

Policy and regression checks:

- generated model docs match policy;
- golden cases cover inactive groups and Travel Effort's 30% effective-share
  cap;
- golden scenarios protect intentional ranking behavior;
- golden scenario reports expose intended ordering and factor contributions;
- no measured, diagnostic, or planned factor influences production ranking;
- focused benchmarks enforce policy-defined factor-evaluation, reranking,
  refinement, and total-search latency budgets.

## Advisory Review

- Design reviewers: product-strategy, backend-api,
  data-trust-source-integrity, ui-ux, ai-llm-reliability, security-privacy,
  observability-ops, performance.
- Feature reviewers: the same reviewers plus accessibility, mobile-companion,
  and release-change-management, narrowed to implemented surfaces.
- Design-review result: no Blocker or High findings. Medium clarity findings on
  policy-version identity, correlation-adjusted attribution, evidence-cap
  composition, prompt-injection boundaries, and bounded simulation were folded
  into this accepted design.
- Numerical-policy and forecast-extension re-review completed on 2026-07-13
  with product-strategy, backend-api, data-trust-source-integrity, ui-ux,
  security-privacy, observability-ops, ai-llm-reliability, and performance
  lenses. No Blocker or High findings remained. Group/factor patch separation,
  Travel Effort's absolute 30% cap, exceptional unscored response semantics,
  forecast lead-time timezone handling, and forecast-serving telemetry were
  folded into the design.
- Focused forecast-provider follow-up completed on 2026-07-14 with no Blocker
  or High finding. Source-keyed ECMWF/GEFS routing, model-cycle metadata,
  local-day aggregation, mid-elevation scope, and exact-date fallback were
  aligned with the forecast evidence spec and ADR 0013.
- Focused factor-readiness follow-up completed on 2026-07-14 with no Blocker or
  High finding. Product, backend/API, data-trust, UI/UX, AI/LLM reliability,
  security/privacy, observability/ops, and performance lenses confirmed the
  factor-shaped readiness boundary. The review clarified that intensity-
  specific apres must not inherit a full match from availability alone. On
  2026-07-15 the owner resolved the remaining gates by choosing conditional
  snowmaking resilience and an estimate-aware, non-ranking lodging constraint.
- Final ExecPlan design review completed on 2026-07-15. A High first-party-
  client cutover gap was fixed by including the checked-in Flutter search
  client before deleting GET search. A Medium documentation-hygiene finding was
  fixed by generating the policy inventory inside the canonical ranking model
  instead of a separate generated-doc tree. No Blocker or High finding remains.
- Final feature review completed on 2026-07-15 across product strategy,
  backend/API, data trust, UI/UX, AI reliability, security/privacy,
  observability/operations, performance, accessibility, mobile companion, and
  release management. Blocker/High release-gate findings were fixed for partial
  forecast-cycle retries, calendar-day climatology coverage, source-aware and
  currency/season-safe comparison bounds, public schema bounds, per-area/source
  readiness, removable intent controls, truthful unranked presentation, and
  overlapping refinement requests. Exact-head verification and local canary
  acceptance leave no Blocker or High finding open.
- Focused live-provider feature follow-up completed on 2026-07-15 after a real
  Gemini request exposed three release-gating integration faults that mocked
  output tests could not detect: provider rejection of the full Pydantic schema,
  computed intent fields re-entering strict validation, and one invalid question
  discarding a valid sibling. The provider now receives a compact structural
  schema, application validation remains authoritative, computed fields are
  excluded from answer simulation, and questions validate independently. A real
  Austria search returned a material UI-ready clarification, all 1,376 backend
  tests pass, and no Blocker or High finding remains.
- Known residual risks:
  - initial weights are owner-approved expert policy backed by golden scenarios,
    not learned calibration;
  - sparse facts can limit useful refinement choices;
  - LLM question relevance requires bounded evaluation without exact-wording
    tests;
  - the active party-skill policy still requires golden-scenario coverage and
    the focused catalog difficulty-profile gap-filling initiative;
  - operational predictions need a separate provider and calibration design.
