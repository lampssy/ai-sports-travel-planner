# Implement Search V4 And Trip-Window Forecast Ranking

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to
date as work proceeds.

This document must be maintained in accordance with the ExecPlan requirements
and guidelines in the `execution-plan` skill. It deliberately contains the
decisions needed to execute the work without reopening the accepted product
model. The checked-in feature specs and ADRs remain useful deeper references,
but this plan explains the required behavior and implementation sequence.

## Purpose / Big Picture

After this change, Snowcast ranks concrete ski-trip configurations against a
traveller's actual priorities instead of a small fixed set of Search V3
components. A user can make terrain scale, party ability, access, pass value,
travel effort, village character, apres, night skiing, freeride, glacier
terrain, snow parks, or snowmaking resilience relevant without turning every
known catalog feature into an always-on bonus. For exact trip dates, the result
uses a stored forecast for those dates, blended with climatology according to
lead time, instead of treating today's conditions as the future.

The user can also receive up to three useful clarification questions. An LLM
chooses the topics and wording from the runtime-ready factor registry, but only
validated typed patches can change the deterministic ranking. The owner can
inspect `docs/search-ranking-model.md`, the active TOML policy, and a generated
inventory to see the exact equation, active factor count, group budgets,
weights, evidence modes, and activation rules.

The completed behavior is observable by submitting a typed `POST /api/search`
request, inspecting the factor and group breakdowns, selecting one returned
clarification option, and resubmitting its patches. A near-term request should
show target-date forecast provenance; a request beyond 30 days should show
climatology-only snow evidence. The old Search V3 GET contract and runtime
model switch will no longer exist.

## Decision Gate Before Execution

- Classification: `review-gated`, using the full design flow.
- High-risk domains touched: ranking and scoring semantics, source trust,
  persistence and indexed query shape, external weather acquisition, shared API
  and web/mobile-client contracts, LLM behavior, request-path performance,
  observability, and operational scheduling.
- Developer Decision Checkpoints: resolved. The owner approved the grouped
  score policy, evidence modes, factor readiness, direct V4 replacement,
  clarification ownership, forecast providers and lead-time shares, immutable
  forecast runs and serving heads, tiered retention, party-skill formula,
  estimate-aware lodging constraint, and conditional snowmaking composition.
- Accepted assumptions: none. Incidental names may be improved during
  implementation, but changing any accepted numeric policy or semantic
  boundary requires a new owner checkpoint and a Decision Log entry.
- Unresolved owner decisions: none.
- ADR status: accepted ADR 0012 owns the versioned factor registry and grouped
  scorer; accepted ADR 0013 owns immutable forecast runs and latest-run heads.
  No additional ADR is required unless implementation moves ranking into an
  LLM, changes the persistence/source-of-truth boundary, adds a request-path
  provider call or cache, or introduces a different migration strategy.
- Advisory design-review status: completed for the accepted Search V4 and
  weather specs and this final ExecPlan. The plan review found and resolved the
  mobile-client cutover and generated-inventory placement gaps; no Blocker or
  High finding remains.
- Advisory feature-review status: required before final handoff, after the
  implementation diff and product behavior exist.

## Progress

- [x] (2026-07-14 22:46Z) Accepted Search V4, evidence-readiness, party-skill,
  forecast, lodging-budget, and snowmaking-resilience decisions were recorded
  in the model docs, feature specs, domain language, engineering notes, and ADRs.
- [x] (2026-07-14 22:46Z) Current Search V3, API, frontend, Postgres bootstrap,
  Open-Meteo, climatology, parser, and test boundaries were inspected for this
  plan.
- [x] (2026-07-14 22:53Z) Focused advisory design review identified two plan
  gaps: the direct API cutover must migrate the existing mobile client, and the
  generated inventory should live in the canonical ranking document rather
  than a separate generated-doc tree. Both are incorporated below; no Blocker
  or High finding remains.
- [x] (2026-07-14 23:13Z) Milestone 1: added the versioned TOML policy, frozen
  typed loader and factor-evaluation contract, bidirectional registry
  validation, drift-checking CLI, canonical generated inventory block, and 11
  focused tests. Production search remains on V3 and the inventory honestly
  reports evaluator implementations as not registered until later milestones.
- [x] (2026-07-15 00:06Z) Milestone 2: added the generic grouped scorer,
  typed intent and constraints, static source-aware factor evaluators, catalog
  readiness audit, and golden scenarios covering every score group and the
  accepted travel/skill/unknown semantics.
- [x] (2026-07-15) Milestone 3: implemented immutable
  run/daily/head schema, repository and bulk read, ECMWF/GEFS source contracts,
  DST-safe local-day normalization, cycle-consistent partial-area publication,
  safe already-seen-cycle no-op, and tiered retention commands. The repository
  integration suite passes against local Postgres.
- [x] (2026-07-15 00:06Z) Milestone 4: added versioned physical curves,
  forecast/climatology composition, conditional snowmaking resilience, and
  source-routing/failure/fallback scenarios. Forecast freshness is an explicit
  preloaded run state rather than a provider call inside the evaluator.
- [x] (2026-07-15 00:06Z) Milestone 5: added typed manual preference patches,
  objective patches, deterministic actionability and hybrid-impact simulation,
  bounded LLM refinement proposals, one validation retry, prompt capability
  bounds, and no-question fallback.
- [x] (2026-07-15) Milestone 6: directly cut the API and web/mobile clients over
  to Search V4, activated the reviewed factors, added forecast refresh and
  retention schedules, and removed the Search V3 route, scorer, model switch,
  and V3-only tests.
- [x] (2026-07-15) Milestone 7: operator docs, generated policy checks, V4 canary/readiness,
  bounded search/refinement/forecast telemetry, Postgres integration tests,
  web build/tests, mobile analyze/tests, final full regression, advisory feature
  review, and the product-oriented local acceptance pass are complete.

## Surprises & Discoveries

- Observation: database-free tests could not exercise strict Pydantic mapping
  of a joined forecast run/daily query.
  Evidence: the first live Postgres repository run rejected daily columns as
  extras when `_run_from_row` received the whole joined row.
  Consequence: run and daily mappers now select only their declared column
  lists; the repository, API, and bootstrap integration set passes against
  local Postgres.

- Observation: a completed provider/model cycle is not a safe no-op unless it
  contains complete daily evidence for every ski area requested by that refresh.
  Evidence: a partially successful run could otherwise make failed areas skip
  every retry until the next model cycle.
  Consequence: complete-run lookup now requires requested-area coverage and has
  repository and refresh regressions.

- Observation: sparse or source-needed numeric values can distort catalog-wide
  normalization even when the value itself later receives no ranking influence.
  Evidence: normalization originally read raw values before applying the trust
  manifest and pass-slice comparability policy.
  Consequence: numeric bounds use only positive-strength evidence, pass slices
  reject mixed currencies and ambiguous seasons, and terrain selection falls
  back to a trustworthy exact-scope source.

- Observation: readiness by distinct serving run hid missing ski-area/source
  pairs because one run can serve many heads and one fresh head says nothing
  about the rest of the catalog.
  Evidence: the first readiness implementation counted distinct run IDs.
  Consequence: readiness now compares fresh heads with every active ski area
  and configured source pair.

- Observation: unit-valid Pydantic structured output is not automatically a
  valid Gemini provider schema, and real trip intents include computed fields
  that must not be fed back into strict input validation.
  Evidence: the first live refinement request returned Gemini
  `INVALID_ARGUMENT`; after compacting the provider schema, live answer
  simulation exposed computed `TravelWindow` and lodging-budget fields as
  forbidden extras. A later invalid sibling also discarded a separately valid
  question through all-or-nothing validation.
  Consequence: Gemini receives a compact structural schema, Pydantic and policy
  validation remain authoritative, answer simulation excludes computed fields,
  and valid questions survive independently rejected siblings. Focused
  regressions and a real Gemini search now produce a UI-ready clarification.

- Observation: the verified Open-Meteo ensemble-mean routes use the exact model
  parameters `ecmwf_ifs025_ensemble_mean` and
  `ncep_gefs05_ensemble_mean`; ECMWF currently returns no usable freezing-level
  values while GEFS does.
  Evidence: official model metadata and bounded live contract requests made
  before implementing the gateway.
  Consequence: temperature, snowfall, rain, and snow depth define daily
  completeness for both routes; freezing level is a GEFS-only optional field,
  and all test fixtures use Unix timestamps so 23/24/25-hour local days remain
  distinguishable across daylight-saving transitions.

- Observation: the repository uses idempotent Postgres bootstrap SQL in
  `app/data/database.py`, not Alembic or another migration framework.
  Evidence: catalog, weather history, climatology, LLM cache, and user tables
  are all created through `CREATE TABLE IF NOT EXISTS` in `_create_schema`.
  Consequence: forecast tables and indexes use the same reviewed bootstrap
  boundary; this plan does not introduce a migration dependency incidentally.

- Observation: the current `GET /api/search` accepts required query fields and
  always calls Search V3 even though model-selection metadata still exists.
  Evidence: `app/api/routes.py::search` calls
  `app.domain.search_v3_service.search_trip_markets`, while
  `app/domain/search_models.py` accepts only `search_v3`.
  Consequence: the V4 cutover removes dead compatibility machinery instead of
  building a parallel runtime or comparison mode.

- Observation: current weather evidence is split between a latest conditions
  snapshot, raw history, and derived daily climatology; none preserves
  immutable model issue versions for arbitrary future dates.
  Evidence: `resort_conditions`, `raw_weather_history`, and
  `ski_area_snow_climatology_daily` exist in `app/data/database.py`.
  Consequence: V4 must add dedicated forecast-run tables and must not overload
  current conditions or climatology.

- Observation: the existing web client performs GET search and has a separate
  parse-query flow with typed clarification support for older trip-context
  questions.
  Evidence: `frontend/src/api.ts`, `frontend/src/types.ts`, and
  `app/ai/parser.py`.
  Consequence: reuse the proven structured-output and deterministic-fallback
  patterns, but replace their narrow filter model with Search V4 intent and
  factor patches rather than extending the old query string indefinitely.

- Observation: the Flutter companion also calls the GET search endpoint and
  parses Search V3 configurations.
  Evidence: `mobile/lib/main.dart::MobileApiClient.search` and
  `mobile/test/smoke_test.dart`.
  Consequence: deleting GET search without migrating mobile would break a
  checked-in first-party client. The direct cutover therefore updates mobile's
  transport and result parsing even though dynamic refinement UI remains
  web-first.

- Observation: `PROJECT.md` asks to keep generated artifacts out of version
  control, while the ranking design requires a generated, drift-checked policy
  inventory.
  Evidence: the product charter's documentation model and the accepted Search
  V4 policy-visibility requirement.
  Consequence: the generator maintains a bounded inventory block inside the
  canonical `docs/search-ranking-model.md`; it does not create a separate
  `docs/generated/` artifact tree.

## Decision Log

- Decision: replace Search V3 directly; do not implement shadow scoring,
  runtime rollback, compatibility endpoints, or V3 comparison reports.
  Rationale: the product has no users or external consumers, and the owner
  prefers one reviewed model over migration-only complexity.
  Date/Author: 2026-07-15, owner and Codex.

- Decision: migrate every checked-in first-party consumer of the search
  endpoint during the direct cutover; web exposes dynamic refinement first,
  while mobile may ignore optional proposals but must submit and parse V4.
  Rationale: direct replacement removes compatibility code but does not justify
  leaving the repository's Flutter client broken.
  Date/Author: 2026-07-15, Codex advisory review clarification of the accepted
  direct-cutover decision.

- Decision: make `app/config/search-ranking/search-v4.toml` the executable
  numeric and lifecycle policy, with typed Python evaluators owning derivation.
  Rationale: the owner needs one readable inventory and equation without an
  unsafe expression language or scattered literals.
  Date/Author: 2026-07-15, owner and Codex.

- Decision: keep constraints, group priorities, factor preferences, and factor
  importance as separate typed concepts.
  Rationale: a hard limit such as a 15-hour drive must filter before scoring,
  while `very_high` Travel Effort changes its share only up to the accepted 30%
  cap.
  Date/Author: 2026-07-15, owner and Codex.

- Decision: let the LLM choose clarification topics and wording only from the
  complete runtime-ready clarifiable registry; deterministic code validates
  typed patches and material ranking impact.
  Rationale: a fixed question-variant registry cannot anticipate future factor
  combinations, while LLM-owned filters or ranking would be unauditable.
  Date/Author: 2026-07-15, owner and Codex.

- Decision: use Open-Meteo as gateway to
  `ecmwf_ifs025_ensemble_mean` through lead day 15 and
  `ncep_gefs05_ensemble_mean` for days 16 through 30 and shorter-range gaps,
  selecting one source per ski-area/date.
  Rationale: this gives daily 30-day coverage while retaining explicit producer,
  model, grid, issue-time, and lead-time semantics.
  Date/Author: 2026-07-15, owner and Codex.

- Decision: store immutable forecast issues and advance source-keyed serving
  heads only after area-level validation.
  Rationale: search gets one bounded indexed read, failed refreshes keep the
  previous complete evidence, and retained runs enable later calibration.
  Date/Author: 2026-07-15, owner and Codex.

- Decision: keep `lodging_budget_fit` measured with weight zero, while an
  explicit budget becomes an estimate-aware constraint using at least 10%
  flexibility or a larger user-provided `budget_flex`.
  Rationale: current lodging ranges are estimates and can exclude clear
  non-overlap, but cannot defensibly reward one destination as cheaper.
  Date/Author: 2026-07-15, owner and Codex.

- Decision: treat verified snowmaking availability as an explicitly requested
  conditional resilience input to `trip_window_snow_fit`, never as a separate
  additive factor.
  Rationale: snowmaking matters when natural snow evidence is weak, but its
  availability does not prove coverage, operation, or open terrain.
  Date/Author: 2026-07-15, owner and Codex.

## Outcomes & Retrospective

Search V4 now directly serves the web and Flutter clients through typed
`POST /api/search`. Its versioned TOML policy, registered evaluators, exact
grouped equation, trust-aware normalization, hard constraints, dynamic typed
refinements, factor/group explanations, forecast blending, and unscored
fallback are executable and documented. Search V3 and its compatibility
switches are removed.

Versioned ECMWF/GEFS forecast runs, per-area/source heads, scheduled refresh,
tiered retention, and degraded climatology fallback are operationally wired.
The final exact-head verification passed 1,376 backend tests, six web tests and
production build, five Flutter tests plus static analysis, Ruff, generated
policy consistency, readiness audit, and diff hygiene. The local product canary
passed health, service readiness, degraded search readiness with no forecast
heads yet, and a ranked four-region representative search in 4.34 seconds.

The final feature review found no remaining Blocker or High issue. Release-gate
findings fixed during review covered partial-cycle refresh retries, calendar-day
climatology coverage, source-aware and currency/season-safe normalization,
public input/output bounds, complete forecast-head readiness, removable intent
controls, truthful unranked presentation, overlapping refinement requests, and
the live Gemini structured-output/answer-simulation boundary.
Deliberate residuals are the expert-authored rather than learned initial weights,
sparse catalog evidence limiting some refinements, pass-price/value objectives
remaining request-slice inactive until they meet the declared readiness gate,
and forecast-head coverage remaining degraded until scheduled acquisition runs.

## Context and Orientation

The repository root is
`/Users/awownysz/repos/personal_projects/ai-sports-travel-planner`. Backend code
is Python 3.11 with FastAPI, Pydantic, psycopg, and Postgres. The web client is
React and TypeScript under `frontend/`. Python commands use `uv`; frontend
commands use npm.

Before this plan, search used the removed Search V3 candidate, evidence, and
scoring modules. It now enters through `app/api/routes.py::search`, validates a
typed `SearchIntent`, and delegates deterministic candidate generation,
constraint evaluation, factor evaluation, ranking, and optional refinement to
`app/domain/search_v4_service.py`.
`app/domain/resort_fit.py`, `app/domain/ranking.py`, and
`app/domain/pass_selection.py` contain useful existing derivations, but V4 must
move accepted scoring policy into the new typed evaluator and policy boundaries
rather than wrapping the V3 score dictionary.

A candidate is one concrete trip configuration: ski region, stay destination,
stay base, focus ski area, access edge, and selected pass. A constraint decides
whether that candidate is eligible. A factor produces a normalized utility in
`[0,1]` plus its evidence state. A factor group owns a fixed budget such as Ski
Experience or Character. A clarification patch is a schema-validated request to
change one group priority or one factor preference; it is not free-form code.

The accepted grouped equation is:

    u_i = b_i + t_i * (r_i - b_i)

    G_g = sum(e_i * u_i) / sum(e_i)

    raw_group_budget_g = W_g * M_g
    P(q) = capped_normalize(raw_group_budgets, max_effective_share)

    ScoreV4(c, q) = 100 * sum(P_g(q) * G_g)

Here `r_i` is the direction-adjusted raw utility, `t_i` is the effective
evidence cap, `b_i` is the declared neutral or fallback utility, `e_i` is the
factor's base weight after its controlled importance and correlation policy,
`W_g` is the default group budget, `M_g` is the controlled group-importance
multiplier, and `P_g` is the final capped group share. The score is fit, not
probability or confidence. If no feasible active-group allocation exists,
return eligible candidates in stable unranked order with
`ranking_status="unscored"`; never invent a numeric fit score.

The default group budgets are Trip Viability 30, Ski Experience 30, Stay
Practicality 15, Value 10, Character 10, and Travel Effort 5. Group importance
maps `ignore/secondary/normal/important/primary/very_high` to
`0/0.5/1/2/4/8`. Factor importance maps `low/normal/high` to `0.5/1/2`.
Travel Effort has a maximum effective share of 30%; other initial groups do not
have a lower cap.

The initial core or context-core factors are `accessible_terrain_scale` with
Ski Experience weight 3, `party_skill_coverage` with weight 2 when party
ability is known, `stay_base_access` with weight 1, `travel_effort` with weight
1 when an origin is known, and `trip_window_snow_fit` with Trip Viability weight
1 when a usable travel window exists. One selected `pass_price_per_day` or
`pass_terrain_value` objective has Value weight 2. Explicit or clarified
preferences may activate `terrain_potential_scale`, `lift_network_scale`,
`glacier_terrain`, `snow_park`, `night_skiing`, `marked_freeride_routes`,
`snowmaking_availability`, `ski_day_apres`, `local_apres`, `local_pace`,
`development_style`, and `base_type`. `lodging_budget_fit` is measured with
zero weight. Expected open-piste, open-lift, snow-coverage, pass-accessible-open-
kilometre, and lift-accessible-off-piste factors remain diagnostic or planned.

Comparative factors require 90% resolved coverage and average evidence strength
0.70 when always on, or 75% and 0.50 in the applicable request slice when
requested. `party_skill_coverage` is a reviewed exception that remains active
with neutral shrink while difficulty-profile gaps are curated. Positive-
presence features require at least three verified positives and activate only
from explicit or clarified intent; verified available maps to raw utility 1,
unknown to neutral 0.5, and verified unavailable to 0, followed by evidence
shrink. Categorical matches use 1 for a known match, 0 for a known mismatch,
and 0.5 for unknown. Pass objectives require comparable audience, duration,
currency, season, and terrain scope. Predictions retain separate provenance,
time coverage, freshness, and uncertainty policy.

Party skill is based primarily on classified piste inventory. Beginner uses
easy terrain, intermediate uses easy plus intermediate terrain, and advanced
uses the complete classified network. Its evidence-unadjusted value is:

    base_skill_fit = 0.65 * compatible_share_utility
                   + 0.35 * compatible_amount_utility

    effective_skill_fit = 0.5
                        + evidence_strength * (base_skill_fit - 0.5)

Full share/full amount are 30%/10 km for beginner, 70%/30 km for intermediate,
and 100%/50 km for advanced. Kilometre breakdown has strength 1, source-backed
run-count breakdown 0.5, positive qualitative support 0.25, and unknown 0.
For mixed parties take the minimum fit across represented levels. Never infer
freeride or another terrain preference from advanced ability.

Postgres schema creation is centralized in `app/data/database.py` and invoked
by `app/data/bootstrap_database.py` and catalog sync. Current weather access is
implemented in `app/integrations/open_meteo.py`, with raw/history/climatology
repositories in `app/data/repositories.py`. V4 adds forecast-specific tables
and a focused repository rather than encoding forecast issues into
`raw_weather_history`. Current conditions remain for current-state display and
companion behavior; they do not rank future dates.

The initial target-date forecast uses one normalized local-day mid-elevation
row. ECMWF is preferred through lead day 15; GEFS serves days 16 through 30 and
can fill shorter gaps. The weather outlook is:

    outlook_d = clamp(
        depth_adequacy_d
      + 0.15 * fresh_snow_benefit_d
      - 0.25 * max(rain_risk_d, thaw_risk_d),
      0, 1
    )

Piecewise-linear anchors are depth centimetres
`0/10/20/30/60/100 -> 0/0.15/0.40/0.60/0.90/1`, snowfall centimetres
`0/5/15/30 -> 0/0.25/0.70/1`, rain millimetres
`0/5/15/30 -> 0/0.25/0.75/1`, and positive degree-hours
`0/12/36/72 -> 0/0.20/0.60/1`. Forecast shares by local calendar lead day are
80% for 0-5, 60% for 6-10, 40% for 11-16, 15% for 17-30, and zero later. Missing
or invalid date coverage is zero, returning that share to climatology.

If and only if the user prefers snowmaking resilience, calculate:

    need_d = clamp((0.75 - natural_snow_utility_d) / 0.45, 0, 1)
    uplift_d = 0.25 * need_d * (1 - natural_snow_utility_d)
               * snowmaking_support
    managed_snow_utility_d = clamp(natural_snow_utility_d + uplift_d, 0, 1)

`snowmaking_support` is the effective source-evidence cap only for verified
available snowmaking and otherwise zero. This component has no independent
weight or importance multiplier and proves neither coverage nor operation.

The existing parser in `app/ai/parser.py` demonstrates structured JSON-schema
output, retry, caching, observability, and deterministic fallback. Search V4's
refinement generator belongs in a separate AI module because the LLM must not
fetch evidence or rank. The web API belongs in `app/api/routes.py`; frontend
request/response types belong in `frontend/src/types.ts`, transport in
`frontend/src/api.ts`, and interaction state in `frontend/src/App.tsx` or small
components extracted from it.

## Plan of Work

### Milestone 1: Versioned Policy And Typed Registry Foundation

Create `app/config/search-ranking/search-v4.toml`. It must declare
`search_model_version="search-v4"`, a separately incrementable policy version,
the six group budgets and Travel Effort cap, controlled importance maps,
constraint inventory, factor inventory, lifecycle, roles, activation, weight,
neutral value, evidence mode, readiness policy, supported operations and
values, correlation group, composition target/policy, and clarification-impact
thresholds. It contains data only; do not add Python expressions or provider
calls.

Create `app/domain/search_policy.py` with frozen, extra-forbidden Pydantic
models and a loader using Python 3.11 `tomllib`, so no dependency is required.
Policy validation must reject duplicate IDs, missing groups, illegal weights,
unknown roles or activation modes, infeasible group caps, ranking-active
factors with zero/absent evaluators, unsupported composition targets, and
numeric multipliers outside the accepted controlled maps.

Create `app/domain/search_factors/__init__.py`, `models.py`, and `registry.py`.
The registry maps stable IDs to typed evaluators. The minimum shared result is
a `FactorEvaluation` containing factor ID, scope and entity IDs, raw value,
normalized utility, neutral value, effective evidence cap, distinct evidence-
cap components, lifecycle/activation state, warning codes, provenance summary,
and explanation inputs. Define an evaluator protocol whose `evaluate` method is
pure over a `FactorEvaluationContext` and one candidate. Define registry
validation in both directions: every runtime evaluator has policy and every
active/measured policy factor has an evaluator unless it is explicitly a
non-additive component handled by a named typed composition evaluator.

Create `app/data/explain_search_policy.py` and a marker-delimited generated
inventory block inside `docs/search-ranking-model.md`. Running the command
without `--check` rewrites only that block deterministically; `--check` exits
non-zero when the block differs. The report shows model and policy versions,
equation reference, active/measured/diagnostic counts, group budgets and caps,
all factor weights and maximum default contributions, activation, evidence
mode, roles, evaluator status, and composition relationships.

Use test-first development in `tests/test_search_policy.py` and
`tests/test_search_factor_registry.py`. End this milestone with a validated
policy and generated inventory but no production ranking change.

### Milestone 2: Deterministic Scorer, Constraints, And Static Evaluators

Create `app/domain/search_ranking.py` for the generic equation and
`app/domain/search_constraints.py` for eligibility. Create
`app/domain/search_v4_models.py` for `SearchIntent`, typed constraints,
objectives, group-priority patches, factor-preference patches, party and travel
context, ranking breakdowns, warnings, and the typed unscored state. Keep all
models frozen and extra-forbidden where they cross deterministic boundaries.

Implement capped group normalization as a small, independently tested function.
It repeatedly caps an over-budget group and proportionally redistributes the
excess until shares sum to one, or returns the typed unscored condition if the
active caps cannot form a complete allocation. Implement preference direction,
trust shrink, correlation-adjusted effective weights, group scores, factor
contributions, and the final `[0,100]` score without factor-specific branches in
the scorer.

Implement constraints before scoring: explicit trip market, travel dates or
month, season viability, maximum travel time, factor-backed verified must-have,
pass-price ceiling, and lodging budget. For lodging, use the catalog estimated
range only when a budget is explicit. The effective flexibility is the greater
of 10% and the user-provided `budget_flex`; exclude only a clearly non-
overlapping range, preserve missing estimates as eligible with an uncertainty
warning, expose the range/flexibility/provenance, and never add a cheaper-is-
better contribution.

Move or adapt candidate generation and useful derivations from V3 into neutral
module names, but do not call the V3 scorer. Implement typed static evaluators
under `app/domain/search_factors/` for terrain scale, party skill, base access,
travel effort, pass price/day, pass terrain value, terrain potential, lift
network scale, the approved positive-presence features, categorical character
matches, and the measured lodging estimate. Consume exact source-group trust
from the catalog trust manifest. Keep scope explicit for ski area, terrain
domain, pass product, stay base, or trip configuration.

Create `app/data/audit_search_factor_readiness.py`. It reports global and
request-slice-ready statistics without changing catalog truth: resolved
coverage, average evidence strength, verified-positive count, distinct trusted
categorical utilities, comparable pass slices, and evaluator/policy status.
Use it to identify missing difficulty profiles. Fill readily sourceable gaps
through the existing catalog curation workflow, permitting source-backed run
counts as strength-0.5 evaluator evidence but never storing run counts as piste
kilometres. Do not block the engine on perfect global coverage; preserve the
accepted party-skill neutral shrink exception.

Add reviewed golden scenarios in `tests/fixtures/search_v4_golden/` and
`tests/test_search_v4_golden.py`. Each fixture states the typed intent, minimal
candidate evidence, expected eligibility/order, and important contribution
ranges. Include all group multipliers, `very_high` Ski Experience, `very_high`
Travel Effort and its 30% cap, inactive groups, mixed party skill, advanced
without freeride, unknown versus unavailable, sparse positive presence,
intensity-qualified apres, objective comparability, estimate-aware lodging,
and unscored allocation. The golden tests define intentional V4 behavior; do
not compare it with V3.

### Milestone 3: Versioned Forecast Persistence And Acquisition

Add forecast schema to `app/data/database.py` using the repository's existing
idempotent bootstrap convention. Create `weather_forecast_runs` for one
immutable source/model issue, `ski_area_weather_forecast_daily` for one
normalized ski-area/local-date/elevation row, and `ski_area_forecast_heads` for
the current complete run per `(ski_area_id, forecast_source_key)`. Add foreign
keys and checks for run status and elevation band. Add an indexed daily lookup
on run, ski area, valid date, and band, and a head index that supports joining
candidate IDs and eligible source keys. Never point a head to a building,
failed, or rejected run.

Create typed forecast domain records in `app/domain/weather_forecast.py` and a
focused `app/data/weather_forecast_repository.py`. Required operations are:

    create_building_run(...)
    insert_daily_rows(run_id, rows)
    reject_or_fail_run(run_id, reason)
    complete_run_and_advance_heads(run_id, publishable_ski_area_ids)
    list_latest_daily_rows(ski_area_ids, start_date, end_date, source_keys)
    apply_retention(now)

Completion and head advancement must be transactional per publishable area or
bounded group. The bulk read must issue one query for all candidate IDs and
requested dates and return rows grouped in memory. Tests must prove that an
incomplete new area keeps the previous head and that current heads never refer
to purged runs.

Create `app/integrations/open_meteo_forecast.py`. Keep HTTP fetching and provider
normalization out of ranking code. Declare required and optional hourly fields
per source key. Read Open-Meteo model-update metadata before fetching, wait
until the issue is at least ten minutes past provider availability, fetch
bounded coordinate batches at each ski area's representative mid elevation,
then re-read metadata. Reject the building run if initialization changed during
the batch. Normalize by provider-returned local timezone, require all 23, 24,
or 25 expected hourly timestamps, store 12:00-local snow depth and spread, sum
snowfall and rain, derive positive degree-hours, store temperature extrema and
supported wind/freezing/spread fields, and omit partial boundary dates. Do not
substitute adjacent dates.

Create `app/data/refresh_weather_forecasts.py` with injectable client,
repository, clock, and sleeper, plus `app/data/retain_weather_forecasts.py`.
Refresh creates immutable runs, validates each area independently, and advances
only successful heads. Retention keeps every complete issue for 45 days, one
canonical daily issue per source from day 46 through two years, one canonical
weekly issue through five years, failed/rejected metadata for 90 days, and any
head-referenced run regardless of age. Prefer 00Z, otherwise earliest complete,
for canonical samples. Add workflows only in Milestone 6; until then these
commands are manual and non-serving.

Use fake HTTP responses and a test clock for unit/integration tests. Do not make
network calls in the test suite. End this milestone by demonstrating schema,
immutable issue publication, source-keyed heads, one bulk serving query, model-
cycle consistency rejection, DST-safe daily normalization, and retention.

### Milestone 4: Active Trip-Window Snow Composition

Implement piecewise-linear interpolation and the weather outlook in a pure
factor module. Select one source per ski area/date: complete eligible ECMWF
through lead 15, otherwise complete eligible GEFS; use GEFS for 16-30; use no
forecast after 30. Compute `lead_days` from the model initialization timestamp
converted to the stored local timezone and then to local calendar date, not
from ingestion time.

Load climatology and latest forecast rows once for all constrained candidates.
For each requested ski day calculate forecast share as the lead-time cap times
valid-date coverage, then blend outlook and climatology. Month-only searches
are climatology-only. Exact dates with missing, stale, incomplete, or
ineligible forecast evidence return that share to climatology. Store and expose
source key, producer/model, run, initialization, local valid date, elevation,
coverage, freshness, spread, and policy version without collapsing them into a
single trust label.

Apply the approved snowmaking uplift only after natural composition and only
when the typed preference is active. Unknown and unavailable both produce zero
uplift but different explanation states. A verified `require` constraint may
filter on availability; generic preference does not imply coverage. Keep wind
as operational-disruption explanation and ensemble spread as uncertainty
explanation; neither modifies the initial utility.

Tests must cover every physical curve anchor and interpolation interval, every
lead-time boundary, partial trip coverage, ECMWF-to-GEFS selection, shorter-
range GEFS fallback, model-cycle timezone boundaries, month-only and over-30-
day searches, stale/incomplete/headless evidence, weak/good natural-snow
snowmaking examples, unknown/unavailable distinction, and proof that the
request path makes no provider call and one forecast repository read.

### Milestone 5: Typed Refinement And Bounded LLM Questions

Create `app/domain/search_refinement.py` for deterministic context building,
patch validation, repetition checks, readiness checks, and impact simulation.
Manual typed preference and priority patches must work without any LLM. Reuse
the baseline candidate evaluations and rerank each complete answer variant;
never refetch weather, travel, catalog, or planning evidence per option.

The material-impact gate accepts a proposal only when two valid answer variants
change candidate eligibility, the winner, top-three membership, top-three order
with at least a 2.0-point pairwise-margin change, or a candidate in the union of
either top five by at least 5.0 points. Positive-presence clarification also
requires a trustworthy non-neutral outcome and at least two effective
utilities; categorical match requires trusted variation; comparative and pass
objectives retain their request-slice readiness gates.

Create `app/ai/search_refinement.py` using the existing `LLMClient`, structured
JSON-schema output, retry helper, and sanitized observability conventions. Its
bounded input contains typed intent, unresolved priorities, runtime-ready
clarifiable groups/factors and allowed values, compact top-result differences,
coverage summaries, and already answered question IDs. Its output contains at
most three questions, bounded answer options, display text, and only typed group
or factor patches. It cannot emit numbers for weights, utilities, scores, or
trust. Treat the brief as untrusted text; embedded instructions cannot alter
the registry or schema.

Apply one bounded retry at most and a short independent timeout. On timeout,
provider error, invalid output, repeated question, immaterial variants, or no
useful topic, return no questions and preserve deterministic results. Cache only
if the key can be built from normalized typed context and policy version
without retaining raw sensitive text. Test schemas, bounds, prompt-injection
attempts, unsupported IDs/values, numeric-weight injection, duplicate questions,
impact thresholds, initially inactive factor activation, no-question fallback,
and result invariance when the LLM fails. Mock LLM output; do not test exact
wording.

### Milestone 6: Direct API And First-Party Client Cutover

Add frozen Search V4 request/response models. `POST /api/search` receives a
`SearchIntent`, optional untrusted brief for refinement relevance, applied
typed patches, and a flag controlling optional refinement generation. The
intent separates constraints, objectives, group priorities, factor preferences,
party context, travel context, and assumptions. Do not accept LLM-provided raw
weights.

The response exposes `search_model_version`, `ranking_policy_version`,
`ranking_status`, optional typed `unscored_reason`, applied intent and
constraints, recommendation groups, per-result fit score when ranked, group
and factor breakdowns, source/trust/freshness warnings, zero to three validated
refinement proposals, and all typed patches needed for a stateless resubmission.
The optional LLM call may time out independently; an empty proposal list is a
successful search response. Preserve the region -> destination/base -> area ->
pass configuration hierarchy.

Update `frontend/src/types.ts` and `frontend/src/api.ts` to POST JSON. Update the
form and result state in `frontend/src/App.tsx`, extracting components when that
keeps the file comprehensible. Show applied constraints and preferences as
removable structured state. Label the score as fit, not probability. Show
unknown separately from unavailable, estimated lodging range and applied
budget flexibility, forecast versus climatology dates, factor contribution and
scope, and unranked state. Keep results visible and usable even when no
clarification is returned. Selecting an answer applies its typed patches and
immediately resubmits search; users can remove or change them.

Update `mobile/lib/main.dart::MobileApiClient.search` and its typed response
models to submit the same Search V4 POST intent and parse the V4 recommendation
hierarchy. Preserve the mobile companion's current ability to choose and save a
trip configuration. Mobile does not need the new dynamic-question interaction
in this milestone, but it must safely ignore optional refinement proposals and
must not depend on deleted V3-only score or weather-summary fields. Update
`mobile/test/smoke_test.dart` to assert POST method/body, exact-date precedence,
V4 response parsing, rendering, and save-current-trip identities.

Once POST API, service, frontend unit tests, and end-to-end flow pass, remove the
GET search route, query-model override, `SNOWCAST_SEARCH_MODEL` and override
environment behavior, V3 scorer/service/model-selection modules, V3-only tests,
and V3-specific UI fields that have no V4 meaning. Move still-valid candidate,
pass, travel, and explanation behavior to neutral modules before deletion. Do
not retain a hidden fallback to V3.

Add `.github/workflows/refresh-weather-forecasts.yml` on a six-hour schedule and
manual dispatch, with a model-metadata check making already-seen issues a safe
no-op. Add a daily or weekly retention workflow with manual dispatch. Follow
the current conditions workflow's scoped `DATABASE_URL`, uv setup, timeout,
concurrency, and job-telemetry conventions. Do not place provider responses,
raw briefs, prompts, or run IDs in metric labels.

Use this release order: merge and deploy additive schema, policy, forecast
acquisition, and V4 code with climatology fallback; verify bootstrap and a
manual forecast refresh; then enable the forecast schedule. The API cutover can
serve without forecast heads because climatology fallback is valid, but the GET
route is removed only after backend, web, and mobile V4 tests pass on the same
head. A failed forecast job never requires an application rollback.

### Milestone 7: Operations, Documentation, And Final Review

Update `README.md` and `docs/production-runbook.md` with the POST example,
policy inspection command, forecast refresh and retention commands, schedule,
failure/retry behavior, latest-head inspection, and local UI acceptance path.
Update `docs/observability-plan.md` and existing observability code with bounded
metrics/traces for policy version, ranking status, factor-evaluation and ranking
latency, refinement outcome/latency, questions shown/selected, forecast refresh
status, incomplete areas, head age, date coverage, and bulk preload latency.
Factor IDs may be span attributes in bounded debug detail if reviewed, but must
not become unbounded metric labels. Never log raw briefs, prompts, responses,
origin text, budgets, exact dates, exact factor values, run IDs, or provider
payloads by default.

Update search and parse canaries to use POST V4 and assert model/policy versions,
ranked or typed-unscored status, a valid factor breakdown, and search success
when refinements are absent. Add readiness checks for policy load/registry
integrity and forecast head freshness as a degraded signal; missing forecast
heads must not make the API unready because climatology fallback is valid.

Run the full reviewer set appropriate to the completed surfaces:
product-strategy, backend-api, data-trust-source-integrity, ui-ux,
ai-llm-reliability, security-privacy, observability-ops, performance,
accessibility, mobile-companion, and release-change-management. Fix every
Blocker and High finding, rerun focused reviewers on
the exact final diff, and record Medium/Low follow-ups in
`docs/product-backlog.md` only when they are real deferred work.

## Concrete Steps

Work from:

    cd /Users/awownysz/repos/personal_projects/ai-sports-travel-planner

Before each milestone, inspect `git status --short` and preserve unrelated
changes. Use test-first loops: add one focused failing test, run it to confirm
the missing behavior, implement the smallest policy/domain slice, rerun the
focused test, then run the milestone regression set.

Milestone 1 commands:

    UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
      tests/test_search_policy.py tests/test_search_factor_registry.py -q
    UV_CACHE_DIR=.uv-cache uv run --no-config python \
      -m app.data.explain_search_policy
    UV_CACHE_DIR=.uv-cache uv run --no-config python \
      -m app.data.explain_search_policy --check

Expected final signal: both test files pass and `--check` exits zero without
changing the generated inventory.

Milestone 2 commands:

    UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
      tests/test_search_v4_models.py \
      tests/test_search_v4_scoring.py \
      tests/test_search_v4_constraints.py \
      tests/test_search_v4_factors.py \
      tests/test_search_v4_golden.py -q
    UV_CACHE_DIR=.uv-cache uv run --no-config python \
      -m app.data.audit_search_factor_readiness

Expected final signal: golden ordering and contribution ranges pass without a
V3 comparison, the readiness report names every configured factor, and
measured/diagnostic factors contribute zero.

Milestone 3 commands require local Postgres for repository integration:

    docker compose up -d postgres
    UV_CACHE_DIR=.uv-cache uv run --no-config python \
      -m app.data.bootstrap_database
    UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
      tests/test_weather_forecast_repository.py \
      tests/test_open_meteo_forecast.py \
      tests/test_refresh_weather_forecasts.py \
      tests/test_weather_forecast_retention.py -q

Expected final signal: idempotent bootstrap creates all three tables and
indexes, publication advances only valid heads, the bulk-read test records one
repository query, fake model-cycle changes reject a mixed run, and retention
never deletes a head-referenced run.

Milestone 4 and 5 commands:

    UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
      tests/test_trip_window_snow_factor.py \
      tests/test_search_v4_service.py \
      tests/test_search_refinement.py \
      tests/test_search_refinement_ai.py -q

Expected final signal: exact-date scenarios use the accepted per-day source and
blend, month/far-future scenarios use climatology, weak natural snow receives a
bounded requested snowmaking uplift, and LLM failure leaves result ordering
unchanged.

Milestone 6 and 7 commands:

    UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
      tests/test_api.py \
      tests/test_search_v4_service.py \
      tests/test_observability_search.py \
      tests/test_product_canary.py -q
    cd frontend
    npm test
    npm run build
    npm run test:e2e
    cd ..
    cd mobile
    flutter test
    flutter analyze
    cd ..
    UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests ops
    UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q
    git diff --check

Do not guess an exact total pass count in advance; record it in `Progress` and
`Artifacts and Notes` after execution. All commands must exit zero. If the full
suite reveals unrelated pre-existing failures, record the exact command and
failure, prove the focused change set passes, and do not hide or overwrite the
unrelated state.

For a local product acceptance pass:

    docker compose up -d postgres
    UV_CACHE_DIR=.uv-cache uv run --no-config python \
      -m app.data.bootstrap_database
    UV_CACHE_DIR=.uv-cache uv run --no-config python \
      -m app.data.refresh_weather_forecasts --ski-area tignes-ski-area
    UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.main

In another terminal:

    cd /Users/awownysz/repos/personal_projects/ai-sports-travel-planner/frontend
    npm run dev

Use the UI or POST a request equivalent to:

    curl -sS -X POST http://127.0.0.1:8000/api/search \
      -H 'Content-Type: application/json' \
      -d '{
        "intent": {
          "constraints": {
            "location": {"country": "France"},
            "travel_window": {
              "start_date": "2027-01-16",
              "end_date": "2027-01-20"
            },
            "lodging_budget": {
              "currency": "EUR",
              "maximum_nightly": 250,
              "budget_flex": 0.10
            }
          },
          "party": {"skill_levels": ["intermediate"]},
          "travel_context": {"origin_text": "Berlin"},
          "objectives": [
            {"factor_id": "pass_terrain_value", "importance": "normal"}
          ],
          "group_priorities": [],
          "factor_preferences": [
            {"factor_id": "night_skiing", "mode": "prefer",
             "values": [], "importance": "normal"}
          ],
          "assumptions": []
        },
        "generate_refinements": true
      }'

Choose dates within 30 days of the actual test day when verifying forecast
provenance; the fixed example above is schema documentation and may be outside
the forecast horizon later. A successful response has model and policy
versions, `ranking_status`, recommendation groups, factor/group breakdowns,
source warnings, and zero to three validated questions. Copy one option's typed
patches into the next request and observe a deterministic eligibility/order/
contribution change that satisfies the impact gate. Remove the patch and
observe the baseline return.

## Validation and Acceptance

The implementation is accepted only when all of the following are observable:

1. `docs/search-ranking-model.md`, the TOML policy, and the generated inventory
   agree on versions, equation, group budgets, active factor count, weights,
   lifecycle, evidence modes, and composition. The `--check` command catches a
   deliberate local drift.
2. Identical request, catalog, forecast heads, climatology, travel evidence,
   and policy version produce identical eligibility, score, order, and
   breakdown. Scores remain within `[0,100]` and are labelled fit.
3. A hard 15-hour drive limit filters before scoring; Travel Effort importance
   cannot admit the excluded option. `very_high` Travel Effort remains at or
   below 30% of effective group budget.
4. An explicit lodging ceiling uses at least 10% estimate flexibility, exposes
   that estimate and margin, excludes only clear non-overlap, and creates no
   cheaper-is-better contribution. Without a lodging constraint the estimates
   have no ranking effect.
5. Party skill uses the accepted difficulty and saturation formula, takes the
   minimum across a mixed party, and never activates freeride or other terrain
   preferences from advanced ability.
6. Unknown, unavailable, estimated, weakly trusted, and verified evidence are
   distinct in utility and explanation. Sparse positive-presence factors can
   reward verified availability only when explicitly requested or clarified.
7. Forecast publication never exposes a partial building run. Search reads
   source-keyed current heads and target dates in one bulk repository operation
   and makes no Open-Meteo call.
8. Exact dates use ECMWF/GEFS and the accepted per-day lead-time blend; missing
   coverage returns to climatology. Month-only and over-30-day requests do not
   borrow current conditions.
9. Snowmaking changes snow fit only when requested, only when verified
   available, and primarily under weak natural snow. It has no separate factor
   contribution or importance multiplier.
10. The LLM can propose any runtime-ready clarifiable factor without a
    predefined question variant, but invalid, repeated, unsupported, or
    immaterial proposals never reach the client. Search remains successful with
    no LLM result.
11. The web UI shows applied structured intent, editable/removable preferences,
    uncertainty and scope, ranked versus unranked state, and reranks after a
    selected typed answer on desktop and mobile web viewports. The Flutter
    client submits and parses V4, renders and saves a recommendation, and
    ignores optional proposals safely.
12. `GET /api/search`, Search V3 runtime selection, V3 scorer/service, and V3-
    only tests are absent. Web and Flutter use the POST contract and there is
    one production ranking path.
13. Scheduled refresh failure, stale heads, incomplete area coverage, and
    refinement failure are visible through low-cardinality telemetry and the
    runbook without exposing raw user text or provider payloads.

## Idempotence and Recovery

Policy generation, schema bootstrap, source issue detection, forecast upserts,
head publication, and retention must be safe to repeat. Forecast rows are
immutable by run identity; retry a failed refresh by creating a new run or
resuming only when the repository contract explicitly proves the building run
is consistent. Never mutate a complete historical run to make a retry appear
successful.

If acquisition fails before publication, mark the run failed or rejected and
leave existing heads unchanged. If publication fails within a transaction,
retry the transaction; a head must never point to a non-complete run. If one
ski area is incomplete, publish valid areas and keep that area's prior head.
If all heads are absent or stale, search falls back to climatology and emits a
warning rather than failing.

Retention first identifies the complete canonical daily/weekly replacements,
then deletes non-retained rows, and never deletes a head-referenced run. Test
retention against a temporary database before enabling its schedule. A rerun at
the same timestamp should produce no additional deletions.

During API cutover, keep V3 files only until V4 backend and frontend tests pass
in the same branch. Then remove V3 in one explicit deletion step and rerun the
full suite. Because there is no compatibility requirement, recovery is by
fixing or reverting the unmerged change, not by retaining a production model
switch. Never use destructive git commands or overwrite unrelated user changes.

Provider/API integration tests always use fixtures or fake clients. The one
manual refresh command is optional when credentials/network/provider
availability prevent it; in that case validate the stored fixture path and
record the unverified live-provider caveat before scheduling production.

## Artifacts and Notes

Design sources already accepted and to remain aligned:

- `docs/search-ranking-model.md`
- `docs/planning-model.md`
- `docs/data-trust-model.md`
- `docs/domain-language.md`
- `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`
- `docs/superpowers/specs/2026-07-13-trip-window-weather-forecast-evidence-design.md`
- `docs/architecture/adr/0012-versioned-search-factor-registry-and-ranking-policy.md`
- `docs/architecture/adr/0013-versioned-forecast-runs-and-latest-run-serving.md`

Expected proof snippets to record during implementation include the generated
policy summary, one golden scenario report, one forecast publication/head
transcript, one bulk-query count, one weak-snow snowmaking calculation, one
validated clarification rerank, final focused/full test counts, and advisory
feature-review outcome. Keep these concise and never paste raw provider or LLM
payloads containing user data.

Milestone 1 proof:

    search policy inventory is current: model=search-v4 policy=search-v4-policy-1
    11 passed in 0.14s
    All checks passed!

## Interfaces and Dependencies

Use existing dependencies only: Python 3.11 `tomllib`, Pydantic, FastAPI,
psycopg, httpx, existing OpenTelemetry helpers, React, TypeScript, Vitest, and
Playwright. Installing another package requires owner approval and a plan
update.

At the end of Milestone 1, expose stable interfaces equivalent to:

    class SearchPolicy(BaseModel):
        search_model_version: str
        policy_version: str
        groups: tuple[GroupPolicy, ...]
        constraints: tuple[ConstraintPolicy, ...]
        factors: tuple[FactorPolicy, ...]
        refinement: RefinementImpactPolicy

    def load_search_policy(path: Path | None = None) -> SearchPolicy: ...

    class FactorEvaluator(Protocol):
        factor_id: str
        def evaluate(
            self,
            context: FactorEvaluationContext,
            candidate: SearchCandidate,
        ) -> FactorEvaluation: ...

At the end of Milestone 2, expose deterministic boundaries equivalent to:

    def evaluate_constraints(
        intent: SearchIntent,
        candidate: SearchCandidate,
        context: SearchEvaluationContext,
    ) -> ConstraintEvaluation: ...

    def score_candidate(
        intent: SearchIntent,
        evaluations: tuple[FactorEvaluation, ...],
        policy: SearchPolicy,
    ) -> RankedScore | UnscoredAllocation: ...

    def search_v4(
        request: SearchV4Request,
        dependencies: SearchV4Dependencies,
    ) -> SearchV4Response: ...

At the end of Milestone 3, expose forecast boundaries equivalent to:

    class WeatherForecastRepository(Protocol):
        def create_building_run(...) -> WeatherForecastRun: ...
        def insert_daily_rows(...) -> int: ...
        def complete_run_and_advance_heads(...) -> None: ...
        def list_latest_daily_rows(...) -> ForecastRowsByAreaDateSource: ...
        def apply_retention(...) -> ForecastRetentionResult: ...

    class ForecastProvider(Protocol):
        def get_model_metadata(source_key: str) -> ForecastModelMetadata: ...
        def fetch_hourly_batch(...) -> tuple[ProviderForecastSeries, ...]: ...

At the end of Milestone 5, expose:

    def validate_and_simulate_proposals(
        proposals: tuple[UntrustedRefinementProposal, ...],
        baseline: EvaluatedSearch,
        policy: SearchPolicy,
    ) -> tuple[ValidatedRefinementProposal, ...]: ...

    class RefinementGenerator(Protocol):
        def propose(
            self,
            context: BoundedRefinementContext,
        ) -> tuple[UntrustedRefinementProposal, ...]: ...

The LLM module depends only on bounded refinement context and returns untrusted
proposals. It must not import repositories, provider clients, or the scorer's
internal arithmetic. Evaluators depend on preloaded evidence and must not call
integrations. The API composes services; it does not contain ranking logic.

Plan revision note (2026-07-14 23:13Z): Milestone 1 implementation and focused
verification were recorded. The policy inventory deliberately reports pending
evaluator registration until the corresponding typed evaluators are added.

Plan revision note (2026-07-14 22:46Z): initial self-contained ExecPlan created
after the owner approved the final conditional snowmaking and estimate-aware
lodging-budget policies. The sequence deliberately builds Search V4 policy and
static scoring first, forecast infrastructure second, and activates one final
model only at the direct API/client cutover.
