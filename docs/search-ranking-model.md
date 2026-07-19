# Search Ranking Model

This is the easy-to-find human-readable reference for Snowcast search filtering,
ranking, factor policy, and adaptive refinement.

## Status

- Active search contract: `search-v4`
- Active ranking policy: `search-v4-policy-1`
- Active refinement presentation policy: `search-refinement-presentation-2`
- Search V4 architecture: ADR 0012
- Forecast evidence architecture: ADR 0013
- Search V4 feature design:
  `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`
- Trip-window forecast evidence design:
  `docs/superpowers/specs/2026-07-13-trip-window-weather-forecast-evidence-design.md`
- Planning and forecast evidence details: `docs/planning-model.md`
- Executable policy: `app/config/search-ranking/search-v4.toml`
- Executable refinement presentation registry:
  `app/config/search-refinement/presentation-v1.toml`
- Policy inspection: `uv run python -m app.data.explain_search_policy --check`

This document and its generated inventory describe the active behavior. The
TOML policy is authoritative for numeric policy and inventory; typed evaluator
code is authoritative for derivation.

## How To Read The Model

Snowcast distinguishes:

- **constraints**, which decide whether a candidate is eligible;
- **ranking factors**, which compare eligible candidates;
- **objectives**, which choose an optimization direction such as maximum
  terrain, lowest pass price, or terrain value;
- **preferences**, which activate or emphasize factors for this search;
- **avoidances**, which reverse supported preference utility;
- **assumptions**, which are visible defaults rather than claimed user intent;
- **diagnostic factors**, which are measured but cannot influence production
  ranking.

One capability may have several roles. For example, night skiing may be a hard
requirement, a soft preference, a clarification topic, and an explanation fact.
Country is only a constraint. Snow reliability is normally an always-on ranking
factor.

Clarification eligibility is independent from initial score activation. The LLM
receives all runtime-ready factors with `clarifiable = true`, including
`when_requested` and `objective_selected` factors that contributed nothing to
the initial ranking. A validated answer activates them. Planned, diagnostic, or
measured-only factors are not offered until their answer can change real search
behavior.

## Active Search V4 Model

### Executable Sources

The active implementation is split across:

```text
app/config/search-ranking/search-v4.toml
  declarative constraints, groups, factors, roles, weights, lifecycle,
  trust, missing-data, importance, correlation, and impact policy

app/domain/search_factors/
  typed factor evaluators registered by stable factor ID

app/domain/search_ranking.py
  generic deterministic grouped scorer

app/domain/search_refinement.py
  refinement context, proposal validation, and impact simulation

app/config/search-refinement/presentation-v1.toml
  traveller-facing refinement topics, approved answers, authoritative option
  copy, typed intent actions, and deterministic fallback order

app/domain/search_refinement_presentation.py
  presentation-registry validation, answer-ID resolution, safe-copy fallback,
  and registry-backed deterministic fallback
```

The TOML policy is authoritative for numeric policy and active inventory. Typed
code is authoritative for factor derivation. This document explains both and
contains the generated inventory below.

### Factor Lifecycle

Every factor has one lifecycle state:

- `planned`: defined as future work and not evaluated;
- `diagnostic`: evaluated for investigation but not compared as production
  policy;
- `measured`: emitted in reports or result diagnostics but contributes zero;
- `active`: allowed to influence production ranking when activation rules match;
- `retired`: retained only for migration or historical model explanation.

Every factor also declares roles from:

- `constraint`;
- `ranking`;
- `clarification`;
- `explanation`;
- `diagnostic`.

Lifecycle and role are separate. A factor may support a future ranking role but
remain measured until coverage and policy review are complete.

Activation is also separate from clarification:

- `always`: contributes whenever its required context exists;
- `when_requested`: contributes after a parsed or selected preference;
- `objective_selected`: contributes after the user selects its optimization
  objective;
- `clarifiable = true`: can be proposed by the LLM even when inactive in the
  initial score.

### Preference Operations

- `prefer`: use the normal factor-utility direction;
- `avoid`: invert utility when avoidance is supported;
- `ignore`: do not activate the factor for the search;
- `require`: evaluate a typed constraint before scoring.

The LLM cannot assign an arbitrary numeric importance. It may map explicit user
language or a selected clarification answer to the controlled importance labels
defined below. An omitted priority uses normal group importance and the
factor's configured default activation; it is not silently upgraded merely
because the LLM considers the topic useful.

Search intent represents group priority separately from factor preference:

```text
GroupPriorityPatch(group_id, importance)
FactorPreferencePatch(factor_id, mode, values, importance)
```

Both patch types use registered IDs and controlled labels. A group-priority
patch changes the effective group budget. A factor-preference patch activates,
directs, or reallocates influence only inside that group.

### Exact Search V4 Equation

For candidate `c`, intent `q`, and factor `i`:

- `r_i(c, q)` is normalized utility in `[0, 1]` after preference-direction
  transformation;
- `t_i(c)` is the factor-policy-derived effective evidence cap in `[0, 1]`;
- `b_i` is documented neutral or fallback utility;
- `m_i(q)` is the configured importance multiplier;
- `w_i` is weight inside the factor group;
- `e_i(c, q)` is effective factor weight after importance and any declared
  correlation cap, with `e_i = w_i * m_i` when no cap applies;
- `W_g` is the factor-group weight.
- `M_g(q)` is the bounded policy-defined multiplier for the user's declared
  importance of the group, with `M_g = 1` at normal importance.
- `P_g(q)` is the final normalized group share after applying any
  policy-defined maximum effective share.

Trust-adjusted factor utility:

```text
u_i = b_i + t_i * (r_i - b_i)
```

Group score over factors active for the search:

```text
G_g = sum(e_i * u_i) / sum(e_i)
```

Group allocation over active groups:

```text
raw_group_budget_g = W_g * M_g
P(q) = capped_normalize(raw_group_budgets, max_effective_share)
```

`capped_normalize` first normalizes raw active budgets. If a group exceeds its
declared maximum, the excess is redistributed proportionally among the other
active groups, repeating until the shares sum to `1` and all caps are met.

Overall score:

```text
ScoreV4(c, q) = 100 * sum(P_g(q) * G_g)
```

Only active groups appear in the denominator. Within an active group, only
active factors appear in its denominator. Hard constraints run before this
equation and never consume or change a score budget. Policy validation requires
a feasible active allocation: at least one group and active-group maximum
shares summing to at least `1`. If none is available, search returns
constraint-qualified results without a fabricated fit score and may propose a
clarification.

Consequences:

- the score is bounded in `[0, 100]`;
- group weights, not factor count, control maximum influence;
- adding a factor redistributes its group's budget;
- trust zero moves the evaluation to its documented neutral/fallback value;
- inactive groups and factors do not contribute and are handled through the
  explicit normalization policy;
- the result is a policy-defined fit score, not a probability or confidence.

Correlation policy may reduce the effective weights of factors that represent
overlapping evidence. Any cap or composition rule is part of the exact policy
and must appear in the generated inventory and result breakdown.

The attributable contribution from one factor is:

```text
factor_contribution_i =
  100 * P_g(q)
      * (e_i / sum(e_i in group g))
      * u_i
```

The policy report should show both the default-policy maximum contribution and
the actual per-search contribution when importance or correlation changes the
effective weight.

Factor importance `m_i` changes influence inside one group. Group importance
`M_g` lets a user say that a whole concern such as Character or Value is a main
priority. User-facing labels map to bounded policy values; neither the parser
nor refinement LLM supplies numeric multipliers.

Source trust, prediction confidence, calibration, and freshness remain separate
factor-evaluation fields. The factor's evidence-cap policy derives `t_i` from
the applicable fields. Result explanations expose the effective cap and its
components rather than relabeling prediction confidence as catalog trust.

### Active Initial Numerical Policy

Default group budgets are policy priors, not permanently fixed result shares:

| Group | Default budget | Maximum effective share |
| --- | ---: | ---: |
| Trip viability | `30` | `1.00` |
| Ski experience | `30` | `1.00` |
| Stay practicality | `15` | `1.00` |
| Value | `10` | `1.00` |
| Character | `10` | `1.00` |
| Travel effort | `5` | `0.30` |

The budgets sum to `100` when all groups are active at normal importance. A
group without any active factor drops out. The remaining groups are normalized
back to `100`.

Group importance changes the effective group budget before normalization:

| Group importance | Multiplier |
| --- | ---: |
| `ignore` | `0` |
| `secondary` | `0.5` |
| `normal` | `1` |
| `important` | `2` |
| `primary` | `4` |
| `very_high` | `8` |

Factor importance changes only the allocation inside its group:

| Factor importance | Multiplier |
| --- | ---: |
| `low` | `0.5` |
| `normal` | `1` |
| `high` | `2` |

Consequently, `very_high` is relative to a group's baseline. With every group
active and all others normal, `very_high` Ski Experience receives
`240 / 310 = 77.42%`, while `very_high` Travel Effort receives
`40 / 135 = 29.63%`. This is intentional: the smallest baseline concern may
grow to at most thirty percent without silently becoming the sole objective.
If other groups are inactive and raw normalization would push Travel Effort
above `30%`, the cap holds it at `30%` and redistributes the excess among the
other active groups.
If the user literally asks for the nearest result regardless of other fit, that
is a primary-sort objective rather than an even larger multiplier.

Initial within-group base weights are:

| Group | Factor | Base weight | Activation |
| --- | --- | ---: | --- |
| Trip viability | `trip_window_snow_fit` | `1` | Always when a usable travel window exists |
| Ski experience | `accessible_terrain_scale` | `3` | Core |
| Ski experience | `party_skill_coverage` | `2` | Core when party ability is known |
| Ski experience | Each explicit terrain preference | `2` | Requested or clarified only |
| Stay practicality | `stay_base_access` | `1` | Core |
| Value | Selected pass-price or pass-terrain objective | `2` | Objective-selected only |
| Character | Each requested character factor | `1` | Requested or clarified only |
| Travel effort | `travel_effort` | `1` | Active when an origin exists |

Only one pass-value objective is active by default; explicitly comparing
several requires a reviewed correlation/composition rule. Unlisted or future
factors do not inherit a weight: they remain planned, diagnostic, or measured
until their activation and base weight are reviewed.

Within Ski Experience, the core split is therefore `60/40` when only terrain
scale and party skill coverage are active. One normal optional terrain
preference changes the split to approximately `43/29/29`; making that optional
factor high changes it to approximately `33/22/44`. Activating an additional
factor redistributes the Ski Experience budget and does not enlarge it.

### Hard Requirements Versus Weighted Priorities

User requirements are eligibility constraints. Examples include:

- driving time at or below 15 hours;
- dates inside a source-backed operating season;
- a pass-price ceiling with comparable price context; and
- a sufficiently trusted must-have feature such as night skiing.

A candidate failing a hard requirement is excluded before ranking. Travel
Effort's maximum weighted share therefore has no bearing on a 15-hour limit.
Unknown evidence normally does not satisfy a verified must-have, while unknown
season evidence remains eligible with an explicit uncertainty warning unless
the user requires verified operation.

Season viability follows this constraint policy rather than receiving a
weighted factor budget. A candidate known to be outside its operating season is
excluded. A candidate inside the known window is eligible. Missing or
approximate season evidence is retained cautiously and never receives a false
positive season claim.

### Skill Ability And Terrain Preferences

`party_skill_coverage` replaces the Search V3 supported-level bonus. It should
be derived primarily from source-backed classified piste inventory:

- beginner coverage uses easier classified pistes;
- intermediate coverage uses easier plus intermediate classified pistes;
- advanced coverage uses the complete classified piste network because
  advanced skiers can use the whole mountain.

The evaluator combines compatible piste amount with the relevant difficulty
share and applies the balanced saturation policy. Kilometres and published run
counts are distinct catalog facts: a count profile must never be written into a
field that claims measured piste kilometres.

The evidence-unadjusted value is named `base_skill_fit`, not raw skill utility:

```text
base_skill_fit = 0.65 * compatible_share_utility
               + 0.35 * compatible_amount_utility

effective_skill_fit = 0.5
                    + evidence_strength * (base_skill_fit - 0.5)
```

Both component utilities interpolate linearly from zero to their saturation
point and clamp to `[0, 1]`:

| Party level | Compatible terrain | Full share utility | Full amount utility |
| --- | --- | ---: | ---: |
| beginner | beginner/easy pistes | `30%` | `10 km` |
| intermediate | beginner plus intermediate pistes | `70%` | `30 km` |
| advanced | complete classified network | `100%` | `50 km` |

For a source-backed run-count profile, compatible share uses run counts. When
source-backed `total_piste_km` is also available, the evaluator may calculate a
temporary compatible-amount proxy as total kilometres multiplied by the run
share. That proxy never becomes a catalog kilometre fact and remains subject to
the run-count evidence strength. Without total kilometres, amount utility is
neutral `0.50` rather than zero.

The share-dominant composition prevents the skill factor from duplicating
`accessible_terrain_scale`; overall terrain size remains the scale factor's
responsibility. Evidence strengths are:

| Evidence basis | Strength |
| --- | ---: |
| source-backed kilometre breakdown | `1.00` |
| source-backed run-count breakdown | `0.50` |
| positive qualitative `supported_skill_levels` label | `0.25` |
| unknown | `0`, producing neutral `0.50` |

Neutral shrink applies symmetrically: weak evidence cannot create either a
confident positive or confident negative result. A qualitative level label is
positive-only fallback evidence; an omitted label is unknown unless separate
reviewed evidence explicitly establishes that the terrain is unsuitable.
Source-backed run counts may estimate compatible share and amount for the
evaluator but do not become catalog kilometres.

When a party contains more than one represented ability level, party skill
coverage is the minimum effective fit across those levels. This avoids an
average hiding that one party member has little suitable terrain. An unknown
level contributes neutral `0.50`, not a fabricated negative result.

Ability and preference are independent. Advanced ability does not imply
freeride, black-piste emphasis, snow parks, night skiing, glacier terrain, or
any other terrain preference. Those factors activate only from explicit user
language or a validated clarification answer.

### Trip-Window Snow Composition

`trip_window_snow_fit` is one composed Trip Viability factor, not separate
full-strength climatology and forecast bonuses. For each requested ski day `d`:

```text
forecast_share_d = lead_time_cap_d
                 * requested_date_coverage_d

natural_snow_utility_d = forecast_share_d * trip_window_snowpack_outlook_d
                       + (1 - forecast_share_d)
                         * climatological_snow_reliability_d

trip_window_snow_fit = mean(natural_snow_utility_d over requested ski days)
```

The lead-time caps are:

| Lead time for one ski day | Maximum forecast share | Remaining climatology share |
| --- | ---: | ---: |
| `0–5` days | `0.80` | `0.20` |
| `6–10` days | `0.60` | `0.40` |
| `11–16` days | `0.40` | `0.60` |
| `17–30` days | `0.15` | `0.85` |
| More than `30` days | `0` | `1.00` |

These are maximum shares. Missing, stale, or incomplete forecast dates have
zero coverage and return that share to climatology. The first version does not
apply a second provider-confidence or calibration multiplier: the lead-time
blend itself expresses the accepted uncertainty policy. Ensemble spread is
retained for explanation and later policy refinement. The blend is computed per
ski day rather than only from trip start date. Month-only searches use
climatology and do not borrow the latest current conditions snapshot. Their
climatology evidence cap is the fraction of calendar days in that month with
resolved archive evidence; a single resolved day cannot represent a complete
month.

The initial outlook uses a daily ensemble-mean row at the representative
mid-mountain elevation. Open-Meteo supplies ECMWF IFS 0.25 degree ensemble mean
as the preferred source through lead day 15 and NOAA GEFS 0.5 degree ensemble
mean for days 16 through 30 and as a shorter-range gap fallback. One source is
selected per date; the models are not averaged together. The row may contain
modelled 12:00-local snow depth and spread, daily snowfall and rain,
temperature, optional freezing level, and wind. Lead day is derived from the
model initialization timestamp supplied by provider metadata rather than
retrieval time. Forecast snow depth is a modelled point/elevation value; it is not
ski-area snow-cover percentage, open-piste ratio, or expected open kilometres.
Those operational predictions remain distinct future factors. GEFS daily
resolution at a coarse 0.5 degree grid does not imply high daily confidence;
the `17–30` cap holds its maximum influence to 15%.

The outlook itself is a transparent depth-led physical-driver utility:

```text
trip_window_snowpack_outlook_d = clamp(
    depth_adequacy_d
  + 0.15 * fresh_snow_benefit_d
  - 0.25 * rain_thaw_risk_d,
  0,
  1
)
```

Depth adequacy is primary. Fresh snowfall is a smaller benefit. Rain,
temperature, and freezing level are composed into one deterioration risk to
avoid independently scoring correlated thaw signals. Wind and gusts remain
operational-disruption evidence, while ensemble spread remains explanatory
evidence; neither changes the initial snowpack utility.

The version-one policy uses piecewise-linear curves:

| Component | Physical value to normalized value |
| --- | --- |
| Depth adequacy | snow depth `0/10/20/30/60/100 cm` to `0/0.15/0.40/0.60/0.90/1` |
| Fresh-snow benefit | local-day snowfall `0/5/15/30 cm` to `0/0.25/0.70/1` |
| Rain risk | local-day rain `0/5/15/30 mm` to `0/0.25/0.75/1` |
| Thaw risk | positive degree-hours `0/12/36/72 °C h` to `0/0.20/0.60/1` |

`rain_thaw_risk_d` is the maximum of rain risk and thaw risk, preventing two
correlated full penalties. Positive degree-hours sum hourly temperature above
`0 °C` over the complete local day. Freezing level remains optional
explanatory evidence because both initial source routes do not expose it
consistently. Curves and weights are owned by versioned factor policy.

When and only when an explicit or validated clarified snowmaking preference is
active, verified snowmaking availability supplies a bounded resilience uplift
on days with weak natural snow evidence. It is a composition input to
`trip_window_snow_fit`, not an independently weighted Trip Viability factor:

```text
snowmaking_need_d = clamp(
    (0.75 - natural_snow_utility_d) / (0.75 - 0.30),
    0,
    1
)

snowmaking_support = effective source-evidence cap
                     when availability is verified available
snowmaking_support = 0 when availability is unavailable or unknown

snowmaking_resilience_uplift_d = 0.25
                               * snowmaking_need_d
                               * (1 - natural_snow_utility_d)
                               * snowmaking_support

managed_snow_utility_d = clamp(
    natural_snow_utility_d + snowmaking_resilience_uplift_d,
    0,
    1
)

trip_window_snow_fit = mean(managed_snow_utility_d over requested ski days)
```

Without that preference, `managed_snow_utility_d` equals
`natural_snow_utility_d`. Natural snow utility at or above `0.75` receives no
uplift; the uplift reaches its maximum response only at or below `0.30` and is
absolutely capped by the `0.25` coefficient and remaining headroom. Unknown
and verified unavailable both receive no resilience uplift, but remain
semantically distinct for explanations and hard requirements. Verified
availability does not prove snowmaking coverage, operation, open pistes, or
ski-area snow cover. This component supports `prefer`, `ignore`, and verified
`require`; it does not accept an independent factor-importance multiplier.

This is a ranking-policy transformation rather than a new physical snowpack
model. Operational systems such as SNOW-17 and Crocus/Crocus-Resort support the
importance of snow state, snowfall, temperature, and rain-on-snow, but they
simulate coupled mass and energy processes and require local calibration or
managed-piste inputs. Snowcast consumes the provider's modelled snow-depth
state and uses the other variables only as bounded surface-condition modifiers;
it does not re-run a degree-day melt calculation or claim that policy weights
are scientific constants. The scientific boundary and source references are
recorded in the trip-window forecast evidence design.

The existing latest one-day `resort_conditions` snapshot is not
requested-date forecast evidence. It remains useful for current-conditions
display and companion experiences but cannot enter Search V4 ranking
merely because a trip begins within 30 days.

### Missing And Trust Semantics

For soft preferences:

- verified availability may contribute at full configured strength;
- verified unavailability may produce low utility;
- estimated or partial evidence receives reduced influence;
- unknown returns the documented neutral utility and is not treated as false;
- source-needed data receives no source-backed positive boost.

For requirements:

- the constraint declares a minimum acceptable trust;
- unknown normally does not satisfy a verified must-have;
- the UI states that only results with sufficient evidence qualify.

Prediction confidence is time-scoped and distinct from static catalog trust.
Raw provider confidence is not automatically ranking confidence; dynamic
factors require a calibrated or conservatively capped evidence policy.

The initial source-evidence defaults are:

| Evidence state | Maximum source-evidence cap |
| --- | ---: |
| Source-backed `verified` or `verified_with_adjustment` | `1.0` |
| Partially supported deterministic derivation | `0.7` |
| Manual or catalog `estimated` value | `0.25` |
| `needs_source` | `0` |

The default neutral utility for an unknown soft-preference value is `0.5`.
Individual factors may define a different reviewed neutral value when their
utility is not symmetric. Prediction confidence, date coverage, freshness, and
calibration may only lower the applicable cap; they cannot promote weak source
evidence into full-strength evidence.

Numeric comparison bounds are derived only from candidates with positive
source-evidence strength. A `needs_source` value cannot widen the normalization
range or suppress otherwise trustworthy differences merely because its raw
number is present.

### Evidence Modes And Initial Promotion Policy

A single catalog-completeness threshold is not appropriate for every factor.
The policy therefore declares an `evidence_mode` and a corresponding readiness
rule. A concrete non-unknown value counts as resolved coverage, while its trust
status independently determines evidence strength. `needs_source` contributes
zero strength and cannot influence a source-backed score.

`comparative` factors need broad enough data for fair comparison. An always-on
comparative factor requires at least `90%` resolved coverage and average
evidence strength of at least `0.70`. A requested comparative factor requires
at least `75%` resolved coverage and average strength of at least `0.50` in its
applicable catalog or request slice. `accessible_terrain_scale` and
`stay_base_access` qualify as initial core factors. `lift_network_scale`
qualifies as requested-only. `party_skill_coverage` is an explicit reviewed
exception: it remains active with neutral shrink while the catalog difficulty-
profile gap-filling initiative improves its evidence.

`positive_presence` factors represent features for which trustworthy positive
evidence is useful even though authoritative absence is rarely published. They
become runtime-ready after their evaluator and source policy are reviewed and
at least three catalog entities have verified positive evidence. They do not
need broad verified-negative coverage. For a positive preference:

```text
verified available   -> raw utility 1.0
unknown              -> neutral utility 0.5
verified unavailable -> raw utility 0.0
effective utility    = 0.5 + evidence_strength * (raw utility - 0.5)
```

These factors activate only from explicit intent or a validated clarification;
they receive no universal feature-count bonus. The initial positive-presence
set is `glacier_terrain`, `snow_park`, `night_skiing`,
`marked_freeride_routes`, `ski_day_apres`, and `local_apres`.
`snowmaking_availability` uses the same verified-positive readiness threshold
but applies through the conditional resilience composition above rather than
the generic presence utility. A generic apres preference uses availability. A
preference for a particular apres intensity uses the requested controlled
intensity as a categorical qualifier: known matching intensity is positive,
known mismatch is negative, and missing intensity remains neutral rather than
inheriting full utility merely from `availability=available`. Snowmaking
availability is distinct from `snowmaking_coverage_pct`: the availability fact
is usable under this policy, while the percentage remains non-ranking until
comparable denominator-scoped coverage exists. It cannot modify physical
snowpack outlook; it supplies only the explicitly requested resilience
composition documented above.

`categorical_match` factors compare a requested controlled value. A trusted
match has raw utility `1`, a trusted mismatch has raw utility `0`, and unknown
is neutral `0.5`, with the same evidence shrink. `base_type`,
`development_style`, `local_pace`, and intensity-qualified apres preferences
use this mode. Sparse global coverage does not prevent an explicit preference
from rewarding a known match, but an LLM clarification still requires distinct
trusted utilities and material simulated impact in the current candidate set.

`objective_comparison` factors require comparable values in the relevant
request slice. Pass price needs equivalent duration, audience, currency, and
season; pass-terrain value additionally needs truthful applicable terrain
scope. They use the requested-comparative `75%` coverage and `0.50` average-
strength gate for the applicable candidate slice. A factor may therefore be
usable for one duration or market and neutral for another. Mixed currencies
disable shared price/value normalization until an explicit conversion policy
exists. When no season is requested, differing season-specific prices are
ambiguous and remain neutral; identical duplicate price slices may still be
used.

`composed_prediction` factors use their own reviewed date coverage, freshness,
and confidence policy. `trip_window_snow_fit` is the initial example. Future
open-piste, open-lift, and snow-coverage predictions remain diagnostic until
their separate evidence policies are approved.

`lodging_budget_fit` is initially `measured` with zero ranking weight because
all current stay-base price ranges are estimates. This does not silently remove
the separately declared lodging-budget constraint; its estimate-aware filter
behavior remains explicit in the request contract. Provider-backed or more
strongly sourced lodging evidence is required before the ranking factor can be
promoted.

### Factor Definition Contract

Each group declares a stable ID, label, description, default budget, allowed
importance labels, optional maximum effective share, clarification role, and
LLM-safe description.

The declarative inventory must make these fields inspectable:

| Field | Meaning |
| --- | --- |
| Factor ID, label, description | Stable code identity and owner-readable meaning |
| Group, scope, evidence kind | Contribution category and data ownership |
| Evaluator ID, value type | Typed derivation boundary |
| Lifecycle, activation, roles | Whether and when the factor can affect behavior |
| Allowed modes and values | Valid requirements, preferences, and LLM patches |
| Weight and importance policy | Numeric influence when active |
| Evidence mode and readiness policy | Comparative coverage, positive-presence, categorical matching, request-slice objective, or composed-prediction behavior |
| Unknown utility and evidence-cap policy | Missing, trust, confidence, and freshness behavior |
| Correlation group | Double-counting protection |
| Clarifiable and LLM description | Capability supplied to dynamic refinement generation |
| Explanation policy | Inputs for user-facing match and uncertainty wording |

Pure constraints use a parallel inventory with stable identity, value type,
validation, trust requirement where applicable, and client/LLM roles, but no
ranking group or weight.

<!-- search-v4-policy-inventory:start -->
#### Generated Search V4 Policy Inventory

- Search model: `search-v4`
- Ranking policy: `search-v4-policy-1`
- Active factors: `21`
- Measured or diagnostic factors: `1`
- Planned factors: `5`

##### Groups

| Group | Default budget | Maximum effective share | Clarifiable |
| --- | ---: | ---: | --- |
| `trip_viability` | 30 | 1.00 | yes |
| `ski_experience` | 30 | 1.00 | yes |
| `stay_practicality` | 15 | 1.00 | yes |
| `value` | 10 | 1.00 | yes |
| `character` | 10 | 1.00 | yes |
| `travel_effort` | 5 | 0.30 | yes |

##### Correlation Groups

| Correlation group | Mode | Maximum combined effective weight |
| --- | --- | ---: |
| `terrain_scale` | `informational` | — |
| `terrain_fit` | `informational` | — |
| `pass_value` | `informational` | — |

##### Constraints

| Constraint | Value type | Inputs | Clarifiable |
| --- | --- | --- | --- |
| `location_scope` | `location_scope` | client, llm | yes |
| `travel_window` | `travel_window` | client, llm | yes |
| `lodging_budget` | `lodging_budget` | client, llm | yes |
| `season_viability` | `season_window_eligibility` | system | no |
| `travel_limit` | `travel_limit` | client, llm | yes |
| `minimum_stay_quality` | `minimum_stay_quality` | client, llm | yes |
| `factor_requirement` | `factor_requirement` | client, llm | yes |
| `pass_price_ceiling` | `pass_price_ceiling` | client, llm | yes |

##### Factors

| Factor | Lifecycle | Group | Weight | All-eligible default max | Activation | Evidence mode | Neutral | Readiness | Cap policy | Correlation | Clarifiable |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | --- | --- | --- | --- |
| `trip_window_snow_fit` | `active` | `trip_viability` | 1 | 30.00 points | `always` | `composed_prediction` | 0.5 | `trip_window_prediction_v1` | `forecast_coverage_and_climatology_v1` | — | yes |
| `climatological_snow_reliability` | `active` | — | 0 | — | `always` | `composed_prediction` | 0.5 | `climatology_component_v1` | `climatology_coverage_v1`; composition `forecast_climatology_blend_v1` -> `trip_window_snow_fit` | — | no |
| `trip_window_snowpack_outlook` | `active` | — | 0 | — | `always` | `composed_prediction` | 0.5 | `forecast_component_v1` | `forecast_date_coverage_v1`; composition `forecast_climatology_blend_v1` -> `trip_window_snow_fit` | — | no |
| `expected_open_piste_ratio` | `planned` | `trip_viability` | 0 | — | `never` | `planned` | 0.5 | `planned_v1` | `planned_unavailable_v1` | — | no |
| `expected_open_lift_ratio` | `planned` | `trip_viability` | 0 | — | `never` | `planned` | 0.5 | `planned_v1` | `planned_unavailable_v1` | — | no |
| `expected_snow_coverage_ratio` | `planned` | `trip_viability` | 0 | — | `never` | `planned` | 0.5 | `planned_v1` | `planned_unavailable_v1` | — | no |
| `party_skill_coverage` | `active` | `ski_experience` | 2 | 3.53 points | `always` | `comparative` | 0.5 | `party_skill_exception_v1` | `difficulty_profile_strength_v1` | `terrain_fit` | no |
| `accessible_terrain_scale` | `active` | `ski_experience` | 3 | 5.29 points | `always` | `comparative` | 0.5 | `comparative_core_v1` | `catalog_source_strength_v1` | `terrain_scale` | yes |
| `terrain_potential_scale` | `active` | `ski_experience` | 2 | 3.53 points | `when_requested` | `comparative` | 0.5 | `comparative_requested_v1` | `catalog_source_strength_v1` | `terrain_scale` | yes |
| `lift_network_scale` | `active` | `ski_experience` | 2 | 3.53 points | `when_requested` | `comparative` | 0.5 | `comparative_requested_v1` | `catalog_source_strength_v1` | `terrain_scale` | yes |
| `expected_pass_accessible_open_km` | `planned` | `ski_experience` | 0 | — | `never` | `planned` | 0.5 | `planned_v1` | `planned_unavailable_v1` | — | no |
| `marked_freeride_routes` | `active` | `ski_experience` | 2 | 3.53 points | `when_requested` | `positive_presence` | 0.5 | `positive_presence_v1` | `catalog_source_strength_v1` | — | yes |
| `lift_accessible_off_piste` | `planned` | `ski_experience` | 0 | — | `never` | `planned` | 0.5 | `planned_v1` | `planned_unavailable_v1` | — | no |
| `snow_park` | `active` | `ski_experience` | 2 | 3.53 points | `when_requested` | `positive_presence` | 0.5 | `positive_presence_v1` | `catalog_source_strength_v1` | — | yes |
| `night_skiing` | `active` | `ski_experience` | 2 | 3.53 points | `when_requested` | `positive_presence` | 0.5 | `positive_presence_v1` | `catalog_source_strength_v1` | — | yes |
| `glacier_terrain` | `active` | `ski_experience` | 2 | 3.53 points | `when_requested` | `positive_presence` | 0.5 | `positive_presence_v1` | `catalog_source_strength_v1` | — | yes |
| `snowmaking_availability` | `active` | `trip_viability` | 0 | — | `when_requested` | `positive_presence` | 0.5 | `positive_presence_v1` | `catalog_source_strength_v1`; composition `conditional_snowmaking_resilience_v1` -> `trip_window_snow_fit` | — | yes |
| `stay_base_access` | `active` | `stay_practicality` | 1 | 15.00 points | `always` | `comparative` | 0.5 | `comparative_core_v1` | `catalog_source_strength_v1` | — | yes |
| `lodging_budget_fit` | `measured` | `value` | 0 | — | `never` | `measured_only` | 0.5 | `measured_only_v1` | `estimated_lodging_range_v1` | — | no |
| `pass_price_per_day` | `active` | `value` | 2 | 5.00 points | `objective_selected` | `objective_comparison` | 0.5 | `objective_comparison_v1` | `comparable_pass_price_v1` | `pass_value` | yes |
| `pass_terrain_value` | `active` | `value` | 2 | 5.00 points | `objective_selected` | `objective_comparison` | 0.5 | `objective_comparison_v1` | `comparable_pass_terrain_value_v1` | `pass_value` | yes |
| `ski_day_apres` | `active` | `character` | 1 | 2.00 points | `when_requested` | `positive_presence` | 0.5 | `positive_presence_v1` | `catalog_source_strength_v1` | — | yes |
| `local_apres` | `active` | `character` | 1 | 2.00 points | `when_requested` | `positive_presence` | 0.5 | `positive_presence_v1` | `catalog_source_strength_v1` | — | yes |
| `local_pace` | `active` | `character` | 1 | 2.00 points | `when_requested` | `categorical_match` | 0.5 | `categorical_match_v1` | `catalog_source_strength_v1` | — | yes |
| `development_style` | `active` | `character` | 1 | 2.00 points | `when_requested` | `categorical_match` | 0.5 | `categorical_match_v1` | `catalog_source_strength_v1` | — | yes |
| `base_type` | `active` | `character` | 1 | 2.00 points | `when_requested` | `categorical_match` | 0.5 | `categorical_match_v1` | `catalog_source_strength_v1` | — | yes |
| `travel_effort` | `active` | `travel_effort` | 1 | 5.00 points | `context_available` | `comparative` | 0.5 | `comparative_requested_v1` | `route_evidence_strength_v1` | — | yes |

##### Roles, Values, And Evaluators

| Factor | Roles | Allowed modes / values | Qualifier | Evaluator |
| --- | --- | --- | --- | --- |
| `trip_window_snow_fit` | ranking, clarification, explanation | prefer, ignore | — | registered |
| `climatological_snow_reliability` | explanation, diagnostic | — | — | registered |
| `trip_window_snowpack_outlook` | explanation, diagnostic | — | — | registered |
| `expected_open_piste_ratio` | diagnostic | — | — | not required |
| `expected_open_lift_ratio` | diagnostic | — | — | not required |
| `expected_snow_coverage_ratio` | diagnostic | — | — | not required |
| `party_skill_coverage` | ranking, explanation | ignore | — | registered |
| `accessible_terrain_scale` | ranking, clarification, explanation | prefer, ignore | — | registered |
| `terrain_potential_scale` | ranking, clarification, explanation | prefer, ignore | — | registered |
| `lift_network_scale` | ranking, clarification, explanation | prefer, ignore | — | registered |
| `expected_pass_accessible_open_km` | diagnostic | — | — | not required |
| `marked_freeride_routes` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require | — | registered |
| `lift_accessible_off_piste` | diagnostic | — | — | not required |
| `snow_park` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require | — | registered |
| `night_skiing` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require | — | registered |
| `glacier_terrain` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require | — | registered |
| `snowmaking_availability` | constraint, ranking, clarification, explanation | prefer, ignore, require | — | registered |
| `stay_base_access` | ranking, clarification, explanation | prefer, ignore | — | registered |
| `lodging_budget_fit` | explanation, diagnostic | — | — | registered |
| `pass_price_per_day` | ranking, clarification, explanation | prefer, ignore | — | registered |
| `pass_terrain_value` | ranking, clarification, explanation | prefer, ignore | — | registered |
| `ski_day_apres` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require; low_key, moderate, lively, destination_defining | `availability_or_categorical_intensity_v1` | registered |
| `local_apres` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require; low_key, moderate, lively, destination_defining | `availability_or_categorical_intensity_v1` | registered |
| `local_pace` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require; quiet, balanced, lively | — | registered |
| `development_style` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require; traditional, mixed, planned_resort | — | registered |
| `base_type` | constraint, ranking, clarification, explanation | prefer, avoid, ignore, require; town, village, hamlet, resort_station, neighbourhood, resort_sector | — | registered |
| `travel_effort` | ranking, clarification, explanation | prefer, ignore | — | registered |

Group importance: `ignore=0`, `secondary=0.5`, `normal=1`, `important=2`, `primary=4`, `very_high=8`.

Factor importance: `low=0.5`, `normal=1`, `high=2`.

Clarification impact: eligibility, winner, or top-three-membership change; top-three order requires a `2`-point margin change; a top-five candidate difference requires `5` points.
<!-- search-v4-policy-inventory:end -->

The inventory intentionally keeps these concepts separate:

- total terrain potential versus terrain accessible on the selected pass;
- classified pistes versus marked routes versus generic off-piste terrain;
- ski-day apres versus local evening atmosphere;
- static capacity versus expected open capacity;
- catalog trust versus time-scoped prediction confidence.

Some curated fields are useful inputs or explanations without becoming direct
ranking factors. `official_trail_map` is an evidence/display link. Stay-base
elevation may inform explanation or a later explicitly reviewed factor, but it
must not silently duplicate ski-area altitude or snow reliability. Published
piste difficulty is an input to party skill coverage. Snowmaking coverage
percentage remains unusable until source-backed coverage is populated broadly
enough for comparison; current availability can still be preference-activated.

## Pass And Terrain Value

Pass value must not use a curated default pass as intrinsic destination value.
Comparison requires:

- terrain actually accessible on the applicable pass;
- comparable audience, duration, currency, and season;
- price per ski day when duration is exact;
- explicit local-pass versus wider-domain scope;
- neutral handling when comparable price or terrain coverage is unresolved.

Source-needed price or terrain facts do not participate in numeric comparison
bounds. If multiple otherwise applicable seasons disagree and the request does
not identify one, no arbitrary season is selected.

Scoring and result summaries share one accessible-terrain source policy. It
selects the first trust-usable source in this order: pass aggregate, exactly
one matching terrain-domain aggregate, then selected ski-area terrain only for
a pass without terrain-domain ownership. A numeric source with a zero trust cap
is skipped, so scoring values, summary scope, entity, field group, and trust
always describe the same evidence owner.

Search may support separate objectives for maximum accessible terrain, lowest
pass price, and best terrain value. A raw piste-kilometres-per-price ratio must
not become a universal always-on definition of value.

## Dynamic Refinement Questions

The LLM may select one registered factor topic, use one approved
traveller-facing phrase in one constrained question grammar, and select
approved answer IDs rather than emitting labels or raw patches. A question
contains exactly one topic, and each option contains exactly one answer for
that topic. The server owns reason copy, answer copy, and typed intent actions.
Unsafe or unregistered compositions use deterministic registry-backed
fallback copy before the existing legality, actionability, and materiality
gates run. Group-priority patches remain part of Search V4 but are not generated
as refinement questions in this slice.

After initial ranking, Snowcast supplies the LLM with a bounded summary of known
intent, unresolved priorities, unresolved registered factor topics, approved
answer IDs, top-result differences, coverage, and already answered questions.
This includes preference and objective factors that were inactive in the
initial score.
Question wording remains dynamic; answer labels, descriptions, and typed intent
actions are owned by the versioned presentation registry.

Example shape:

```json
{
  "topic_id": "development_style",
  "question": "What kind of place would you prefer to stay in?",
  "options": [
    {
      "answer_id": "development_style.traditional"
    },
    {
      "answer_id": "development_style.mixed"
    },
    {
      "answer_id": "development_style.planned_resort"
    },
    {
      "answer_id": "development_style.ignore"
    }
  ]
}
```

The provider never supplies the labels or patches implied by those IDs. For
example, the registry resolves the four selections above to `Traditional
mountain village`, `A mix of old and new`, `Purpose-built ski resort`, and `It
doesn't matter`, plus their typed `development_style` actions. A provider
response may contain no question or one question only. The next question is
requested from the fresh baseline after an answer or skip.

Deterministic code then validates:

- topic and answer IDs, factor operations, controlled values, and objectives;
- clarification role and applicable scope;
- evidence-mode-specific readiness, trust, and actionability within the
  candidate set;
- distinctness and non-repetition;
- absence of LLM-provided weights or scores;
- correct activation of requested/objective factors that were initially
  inactive;
- material impact after simulating each option.

A proposal passes the initial hybrid material-impact gate only when at least
one pair of its valid answer variants produces one of these effects against the
same candidate baseline:

- a different eligible-candidate set;
- a different top-ranked candidate;
- different top-three membership;
- a different top-three order with at least a `2.0` Fit-score-point change in
  the affected pairwise margin; or
- at least a `5.0` point Fit-score difference for a candidate appearing in the
  union of either variant's top five.

A tiny near-tie reorder, explanation-only wording change, or contribution
change below these limits is not material. The LLM does not see or alter these
numeric thresholds. Deterministic code evaluates complete typed answer patches,
including activation of an initially inactive preference factor, before a
question is shown.

Only validated proposals are shown. Selecting an answer applies visible typed
preferences and reruns deterministic search immediately. Search remains fully
usable if question generation fails or no proposal has material impact.
The provider-facing response schema deliberately contains only the compact
topic/answer-ID structure and bounded question text supported by Gemini.
Pydantic size and shape validation plus presentation-registry and deterministic
policy validation remain authoritative. The server accepts provider question
wording only when it uses an approved traveller-preference or priority form,
anchored as one complete question with no appended clause or comma, semicolon,
or colon; its extracted semantic body is an exact registered single-topic
phrase; and it follows the minimal
allowed Unicode letter, mark, whitespace, and punctuation policy. Factual `is`,
`are`, or `does` claims cannot be rescued by an incidental preference word or a
conjoined preference clause. Otherwise the server uses registry-backed
traveller copy, which is config-validated rather than passed through the
generated-copy grammar, and always supplies the configured single-topic or
topic reason. A
bounded brief containing a configured sensitive, credential, payment, or
contact marker forces that fallback for the request; candidate IDs, external
actions, unsupported claims, internal policy terms, numeric claims, malformed
questions, and overlong copy are also never shown. Approved reasons, option
labels, descriptions, and typed actions never come from the provider.
The provider question is validated independently of deterministic fallback.
The refinement provider receives one attempt only; no retry can extend the
request budget.

Before actionability and materiality validation, every answer variant reruns
the registered static and weather evaluators from the exact captured baseline
inputs under that variant intent. For `positive_presence`, a clarification
needs at least one trustworthy
non-neutral candidate outcome, at least two distinct effective utilities, and
the normal hybrid impact result; broad verified-negative coverage is not
required. For `categorical_match`, it needs trusted variation that creates at
least two utilities. Comparative and objective factors continue to enforce
their applicable coverage gate. Each selected non-ignore factor must pass this
gate from its replayed outcomes; a material sibling topic cannot rescue a
meaningless factor. Explicit user preferences may activate a runtime-ready
factor even when the LLM would not independently choose to ask about it.

The LLM owns registered-topic selection and constrained question composition.
Deterministic Planning owns public-copy safety, reasons, validity, usefulness,
candidate eligibility, and ranking.

A validated question may retain one option that reproduces the current intent
when another option has material impact. The response marks each option with a
typed intent-change flag. Applying an unchanged baseline option records the
question as answered and preserves the current ranking without a search
request or changed-ranking announcement.

The brief is untrusted planning text, not an instruction source. Embedded
instructions cannot expand the supplied factor registry, allowed values, or
structured output contract.

The public contract bounds identifiers to 128 characters, descriptive intent
and refinement text to 500 characters, and the untrusted brief to 2,000
characters. Exact travel windows are capped at 366 days, request collections
are size-limited, and every refinement question has bounded options and typed
patches. Invalid or oversized refinement output produces no question and never
changes deterministic search results.

Each returned `SearchV4Configuration` carries a backend-owned
`evidence_profile`: `forecast_assisted` when selected trip-window evidence
uses usable forecast coverage, `archive_backed` when complete requested-window
climatology coverage supports the snow factor, and `fallback_heavy` otherwise.
The frontend presents this typed source profile and does not reconstruct it
from generic score-factor internals.

## Post-Search Refinement Contract

`POST /api/search` is ranking-only. It never constructs or calls Gemini and
returns an immediately usable ranking with an empty `refinements` list during
the client migration. The legacy `brief`, `generate_refinements`, and answered
question-ID fields remain accepted on that endpoint only for mobile/web
compatibility; they are ignored.

`POST /api/search/refinements` accepts the canonical intent, a bounded brief,
unique bounded answered question IDs, resolved topic IDs, and the ranking
response's `baseline_fingerprint`. Question IDs preserve compatibility and
block an exact question from repeating. Topic IDs block the same decision from
returning with different wording or answer combinations. Ranking stores compact
baseline scores plus the exact static and weather evaluator inputs needed by
refinement in a thread-safe process-local LRU/TTL store. Refinement accepts only
the exact stored fingerprint plus canonical intent digest. It replays the same
registered evaluators under every variant intent without catalog, weather,
routing, repository, provider, or network acquisition. The whole endpoint has
a five-second monotonic deadline: snapshot lookup and validation consume from
that budget, the provider receives only the remaining timeout, and
deterministic fallback is skipped once the deadline is exhausted.

The refinement response has exactly one public status:

- `questions_available`: one validated question is available;
- `not_needed`: no material question is needed, including a zero-result
  baseline or a captured policy with `max_questions = 0`;
- `temporarily_unavailable`: provider/output failure, an exhausted deadline,
  or a missing, expired, evicted, restarted, or intent-mismatched baseline left
  no valid queue.

Admission rejection is an HTTP `429`, not a refinement response. Its generic
error body is `{"detail": "Refinement is temporarily unavailable."}` and a
`Retry-After` header supplies the bounded retry delay. The browser waits for a
valid delay of at most 15 seconds and retries that admitted request once. It
shows a compact `retrying` lifecycle message while the ranked results remain
usable; a second `429` or any other terminal discovery failure ends the cycle.
Terminal optional failure is announced politely to assistive technology and
does not leave a visible error or refinement card in the results rail.

`fallback_used` is orthogonal to status. When the provider has no usable
proposal or is unavailable, Snowcast may return one fallback question only if
the existing typed proposal validator confirms materiality. It tries unresolved
registered factor topics in configured fallback order, resolves their approved
answer IDs to the same authoritative option copy and typed actions as
provider-selected questions, derives a semantic question ID from the
presentation-policy version, and suppresses both already answered question IDs
and resolved topic IDs. It never creates a group-priority question or duplicates
ranking or materiality logic.

`search-refinement-presentation-2` versions presentation ownership separately
from `search-v4` and `search-v4-policy-1`. Copy-only changes under a new
presentation-policy version may change what travellers read, but they do not
change factor weights, score equations, candidate eligibility, or ranking
semantics. Every configured fallback question and reason, plus every approved
answer label and description, passes deterministic public-copy validation when
the registry loads; unsafe copy cannot become either provider-resolved or
fallback output.

The fingerprint remains a public SHA-256 integrity digest. Its canonical inputs
include the applied intent, complete catalog snapshot, trust manifest, ordered
evaluated candidate states and ranking allocations, Search V4 and
ranking-policy versions, and the weather-selection policy revision. Ranking
uses it as the key for a separate bounded snapshot containing the policy,
compact candidate/constraint/scoring state, and exact evaluator inputs required
by refinement for every initially eligible configuration, subject to capacity.
It retains immutable candidate catalog entities, normalized weather rows,
frozen candidate-scoped trust evidence, and intent-free evaluator context
templates, but not a full trust manifest, `SearchIntent`, origin text, trip
brief, provider prompts, responses, or credentials. Ordinary contexts
containing a variant intent exist only for the duration of an evaluator replay.
The caller's canonical intent digest must also match; the public fingerprint is
never trusted alone.

Replay is narrow-only. A proposal is rejected if any option could relax an
existing synthesized factor `require`; explicit constraint requirements remain
authoritative, while a new requirement may narrow the retained cohort. For each
accepted variant, eligibility is resolved before numeric normalization. The
numeric bounds are then derived exactly once across the variant-eligible cohort
and shared by every replayed registered evaluator.

The snapshot is actively reclaimed 60 seconds after ranking. The process-local
LRU store holds at most 64 entries, 2,048 candidate replay states, and 8,192
unique climatology/forecast rows. A snapshot that cannot fit by itself is not
retained; this affects optional refinement only, never the ranking. A miss,
expiry, eviction, capacity rejection, restart, intent mismatch, or candidate
missing its required replay state returns
`temporarily_unavailable` without deterministic search, Gemini, or fallback
generation. This TTL covers only generation of the next question. Once a
question reaches the browser, its typed answer remains usable after expiry.
Applying a material answer performs a full rerank, stores a new baseline and
fingerprint, records that topic as resolved only after the rerank succeeds, and
requests the next unresolved topic from that fresh baseline. Skipping records
the topic as resolved and requests the next question from the unchanged
baseline. A materially new trip brief or hard-constraint context clears all
resolved topics; manually changing the preference owned by one topic clears
only that topic.
Active cleanup retains only bounded, data-free expired-fingerprint tombstones,
at most the entry limit, so a later handoff lookup still reports `expired`
rather than `miss`. Cleanup emits the expiry outcome once and the later lookup
does not double-count it.

Refinement requests are protected before snapshot lookup by app-local admission
control: at most two concurrent requests and a per-client token bucket of six
requests per minute with a burst of two. The route uses `Fly-Client-IP` only
when it is a syntactically valid fixed Fly header; otherwise it uses the direct
request peer. Client identities are retained only in the bounded in-memory
guard and are never emitted in metrics or logs. Rejected requests receive a
generic `429` with `Retry-After`.

The two-worker executor is guarded by a fail-fast circuit. An outer deadline
releases endpoint admission immediately; if its worker is still unresolved,
new refinement work is rejected without entering an executor queue until all
timed-out workers finish. The Gemini transport itself uses the remaining
deadline, while the circuit covers unexpected non-returning application or
transport behavior without creating replacement threads.

Endpoint metrics record only bounded final outcomes and `fallback_used`; the
AI layer records provider-call health separately and does not emit public
refinement status before fallback handling. Snapshot metrics record only
bounded lookup, eviction, and capacity-rejection outcomes.
The store is intentionally valid only for the current single-process
deployment; multiple web processes require sticky routing, shared state, or a
redesigned handoff.

## Factor Policy Visibility

Inspect or regenerate the active policy inventory with:

```bash
uv run python -m app.data.explain_search_policy
```

It reports at least:

```text
Search V4
Active ranking factors: <count>
Measured or diagnostic factors: <count>
Planned factors: <count>

<group>: <overall weight>
  <factor>  <within-group weight>  <maximum overall contribution>
```

The generated inventory block in this document must also show lifecycle,
activation, roles, trust,
unknown utility, group maximum effective share, importance policy, correlation
group, evaluator status, and whether a factor is clarifiable. A per-search
breakdown shows raw group budgets, cap/redistribution adjustments, and final
normalized group shares.

Search results and policy reports must expose two separate identifiers:

- `search_model_version`, covering the request/response and evaluation
  algorithm contract;
- `ranking_policy_version`, covering the active inventory, weights,
  activation, neutral utilities, and correlation policy.

A weight-only change increments the ranking-policy version even when the Search
V4 API and generic scorer do not change.

## Changing The Model

To add a factor safely:

1. Define a stable factor ID, scope, evidence kind, controlled values, missing
   semantics, trust semantics, and roles.
2. Add a typed evaluator with unit tests.
3. Register it as planned, diagnostic, or measured without ranking influence.
4. Assign its evidence mode and audit the matching readiness rule, catalog or
   request-slice coverage, and trust.
5. Add representative golden scenarios.
6. Resolve owner decisions for activation, group, weight, neutral utility, and
   correlation handling.
7. Promote it in a new versioned policy and regenerate this model inventory.
8. Run advisory review for ranking, trust, UI explanation, and any LLM boundary
   affected by the change.

Changing only a weight is still a ranking-policy change. It requires a versioned
diff, regenerated inventory, and golden-scenario evidence even when no Python
code changes.

## Search V4 Cutover

Search V4 directly replaced the unused Search V3 implementation through
`POST /api/search`. The old GET contract, hardcoded V3 scorer, model-selection
flags, and V3-only ranking tests were deleted. There is no parallel endpoint,
shadow comparison, or runtime V3 rollback path. The narrow Search V4 request
field compatibility noted above is temporary and does not preserve V3 behavior.

Golden scenarios define correct V4 behavior; preserving V3 ordering is not an
acceptance criterion.

## Resolved Initial Activation Boundaries

- Snowmaking availability has no independent factor weight. When preferred, it
  supplies the documented conditional resilience uplift only while natural
  snow utility is below `0.75`, reaching full need at `0.30` with maximum
  coefficient `0.25`.
- `lodging_budget_fit` remains measured with zero ranking weight. An explicitly
  supplied budget remains an estimate-aware constraint: catalog price ranges
  are compared with the requested range using at least a `10%` evidence-
  uncertainty margin or a larger explicit `budget_flex`, only clearly
  non-overlapping candidates are excluded, and the response identifies the
  estimate-based decision.

Initial Search V4 uses the numeric `Fit score` without named fit bands. Exact
correlation caps and weights for future operational-prediction factors are
deferred until those factors have their own source and calibration design; they
do not block the initial model.
