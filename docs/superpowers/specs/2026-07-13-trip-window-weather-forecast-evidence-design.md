# Feature Spec: Trip-Window Weather Forecast Evidence

## Status

- Status: implemented, including climatology reliability v2
- Owner: solo-builder
- Related docs:
  - `docs/search-ranking-model.md`
  - `docs/planning-model.md`
  - `docs/data-trust-model.md`
  - `docs/domain-language.md`
  - `docs/observability-plan.md`
  - `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`
- Related ADR:
  - `docs/architecture/adr/0013-versioned-forecast-runs-and-latest-run-serving.md`
- Related plan:
  - `docs/superpowers/plans/2026-07-15-search-v4-and-trip-window-forecast.md`

## User Outcome

For exact near-term ski dates, Snowcast should evaluate forecast conditions for
the requested days and ski-area elevations. A weak current outlook should be
able to outweigh historically favourable climatology when the trip is close,
without presenting uncertain long-range weather as fact.

Search must remain fast and available independently of weather providers. It
reads validated forecast evidence already stored in Snowcast, while a separate
background refresh owns provider calls and publication of the latest complete
run.

## Scope

In scope:

- ensemble forecast runs with provider/model provenance;
- daily forecast evidence for the representative mid-mountain elevation in the
  first implementation, with the elevation-band dimension retained for later
  expansion;
- immutable issue versions and atomic per-area latest-run heads;
- a rolling serving horizon of at most 30 days;
- one bulk indexed query for the candidate ski areas and requested dates;
- a per-ski-day forecast/climatology composition with lead-time uncertainty and
  valid-date coverage;
- a source-aware climatology reliability utility derived directly from stored
  historical snow-depth and deterioration statistics;
- typed snow-assessment and forecast-applicability states for deterministic
  user-facing presentation;
- sufficient sampled run history for later forecast-versus-observation
  calibration;
- freshness, partial-coverage, failure, and uncertainty semantics;
- observability and verification requirements.

Out of scope:

- provider credentials and commercial-provider evaluation;
- a replacement physical snowpack or energy-balance simulation;
- official or predicted open-lift counts, open-piste kilometres, or skiable
  area coverage;
- snow-quality, avalanche-safety, or route-safety claims;
- a Redis serving layer before Postgres latency is measured;
- forecasts beyond 30 days as an active Search V4 input.

## Current Limitation

The current Open-Meteo refresh requests one forecast day and writes the latest
normalized `resort_conditions` snapshot. Search may give that snapshot a
horizon-dependent planning weight, but the record is not aligned to the user's
requested dates.

`raw_weather_history` can label a row as forecast, but its current uniqueness
shape is designed around one source observation for a valid day/elevation. It
does not preserve issue versions, model runs, or ensemble quantiles cleanly.
Reusing it as the Search V4 serving model would either overwrite evidence or
make latest-run selection and calibration ambiguous.

## Domain Terms And Boundaries

- **Forecast run:** one immutable provider/model issue with a stable run ID,
  issue time, forecast kind, and completion state.
- **Valid date:** the ski day described by one daily forecast row.
- **Lead time:** duration from the run issue time to the valid date.
- **Forecast head:** the latest validated complete run selected for one ski area
  and forecast kind.
- **Trip-window snowpack outlook:** a deterministic Snowcast utility derived
  from forecast weather for exact requested dates and representative ski-area
  elevations.
- **Climatological snow reliability:** historical seasonal evidence for the
  recurring travel window, independent of the current forecast run.

Conditions And Weather Evidence owns acquisition, provenance, persistence,
freshness, and forecast confidence. Planning owns the deterministic composition
of forecast evidence with climatology and supplies the resulting factor
evaluation to Search. The search scorer does not know provider payload shapes.

Forecast evidence is never written to static catalog facts or historical
climatology. A prediction for a valid date is not an observation of that date.

## Decision And Review Gate

- Classification: `review-gated`; full design flow
- High-risk concerns: persistence, request-path latency, ranking semantics,
  scientific uncertainty, provider failures, and user trust
- Developer Decision Checkpoints resolved:
  - use target-date forecasts rather than the latest current snapshot;
  - allow at most 80% forecast influence for days zero through five and reduce
    influence with lead time;
  - use climatology only beyond 30 days;
  - preserve immutable versioned runs and expose atomic latest-run heads;
  - use Postgres as source of truth and initial serving surface;
  - make provider acquisition background work, never a search dependency;
  - retain enough sampled historical runs to support later calibration;
  - acquire daily ensemble-mean evidence through Open-Meteo, preferring ECMWF
    IFS 0.25 degree through lead day 15 and using NOAA GEFS 0.5 degree through
    lead day 30 and as the short-range gap fallback;
  - evaluate the representative mid-mountain elevation initially while keeping
    elevation band explicit in storage;
  - derive the initial snowpack outlook from a transparent depth-led physical
    driver model: current modelled snow depth is primary, new snowfall is a
    secondary benefit, and rain/thaw conditions form one deterioration risk;
    wind and ensemble spread remain separate explanatory evidence initially;
  - use the reviewed version-one physical response curves and composition:
    depth adequacy plus at most `0.15` fresh-snow benefit minus at most `0.25`
    combined rain/thaw risk;
  - retain every complete issue run for 45 days, one canonical daily run per
    source through two years, and one canonical weekly run through five years;
  - use the documented lead-time/climatology blend as the initial uncertainty
    policy, without an additional provider calibration multiplier or mandatory
    forecast-versus-observation study before activation;
  - activate the factor with the completed forecast implementation rather than
    shipping a diagnostic-only production phase.
  - replace the legacy averaged snow-confidence score in Search V4 with a
    policy-owned climatology reliability equation using median snow depth,
    probabilities of reaching 30 cm and 50 cm, and the maximum of historical
    rain and freeze-thaw probability;
  - keep historical average daily snowfall and average maximum temperature as
    explanation evidence rather than independent climatology-utility terms;
  - reserve a separate future powder-likelihood factor for source-backed fresh
    snowfall probabilities rather than overloading snow reliability;
  - distinguish forecast evidence that is not yet applicable from unexpectedly
    missing in-horizon evidence, and never turn expected long-range absence into
    a customer-facing concern;
  - make the backend own the canonical snow-assessment state instead of having
    the frontend infer it independently from warnings and a duplicated score
    threshold;
  - defer unifying the legacy public-page planning calculation and UI to the
    product backlog.
- Developer Decision Checkpoints still required before activation: none.
- ADR status: ADR 0013 accepted
- ADR status for climatology reliability v2: no new ADR required because the
  existing evidence ownership, persistence, request-path composition, and
  forecast-run architecture remain unchanged.
- Advisory design review: completed on 2026-07-13; no Blocker or High findings
  remained after clarifying daily lead-time timezone semantics, partial-area
  head publication, request-path query shape, trust boundaries, and telemetry
  cardinality. Focused provider-policy follow-up completed on 2026-07-14 with
  no blocking finding; model-cycle metadata, local-noon snow depth,
  source-specific optional variables, and exact-date fallback semantics were
  folded into the design.

## Forecast Influence Policy

For every requested ski day `d`:

```text
forecast_share_d = lead_time_cap_d
                 * requested_date_coverage_d

snow_utility_d = forecast_share_d * trip_window_snowpack_outlook_d
               + (1 - forecast_share_d) * climatological_snow_reliability_d

trip_window_snow_fit = mean(snow_utility_d over requested ski days)
```

| Lead time | Maximum forecast share | Remaining climatology share |
| --- | ---: | ---: |
| `0–5` days | `0.80` | `0.20` |
| `6–10` days | `0.60` | `0.40` |
| `11–16` days | `0.40` | `0.60` |
| `17–30` days | `0.15` | `0.85` |
| More than `30` days | `0` | `1.00` |

The caps are not guaranteed shares. Missing, stale, or incomplete valid-date
evidence makes coverage zero and returns that share to climatology rather than
becoming a score penalty. The first version does not multiply the share by an
additional provider-confidence or calibration cap: lead-time blending already
limits forecast influence to 80%, 60%, 40%, or 15%. Ensemble spread remains
stored and explainable evidence that can support a later reviewed policy.

The calculation is per ski day. A trip spanning two lead-time bands uses the
appropriate cap for each date before daily utilities are aggregated. Month-only
searches have no exact valid dates, so they use climatology and do not borrow
the latest current snapshot. Month-level climatology evidence strength is
capped by resolved calendar-day coverage for that month, including leap-year
day counts; partial archive coverage cannot masquerade as complete evidence.

A `17–30` day contribution is possible only when an eligible long-range or
ensemble source covers the exact date. If no such evidence exists, date
coverage is zero and the day is fully climatological.

## Climatology Reliability Policy

Search V4 computes one normalized climatology utility for each recurring local
ski date from the selected mid-mountain normal row. The version-two policy uses
statistics already stored in `ski_area_snow_climatology_daily`:

```text
typical_depth_d = depth_curve(snow_depth_cm_p50_d)

depth_reliability_d =
    0.60 * probability(snow depth >= 30 cm)_d
  + 0.40 * probability(snow depth >= 50 cm)_d

historical_deterioration_d = max(
    probability(rain)_d,
    probability(freeze-thaw)_d
)

climatology_reliability_d = clamp(
    0.50 * typical_depth_d
  + 0.50 * depth_reliability_d
  - 0.25 * historical_deterioration_d,
  0,
  1
)
```

The shared depth curve keeps forecast and climatology utilities on a comparable
physical scale. The forecast outlook describes one modelled future snowpack
state; climatology reliability describes the historical distribution for the
recurring date. They are not interchangeable inputs and remain separate pure
evaluators before the documented lead-time blend.

The p25-p75 snow-depth range, average daily snowfall, average maximum
temperature, evidence-season count, and archive provenance remain visible
explanation and evidence-quality inputs. Historical snowfall does not add a
ranking bonus because established depth already reflects accumulated snowfall
and a daily mean cannot distinguish frequent refreshes from rare large storms.
Average maximum temperature likewise does not add a separate penalty because
depth, rain probability, and freeze-thaw probability already capture the
decision-relevant historical effect more directly.

The normal 30-year row is the scoring baseline when it exists. The recent
15-year row is used only as a fallback when the normal is absent; it does not
silently adjust the displayed normal. Missing median snow depth cannot be
converted into a positive snow claim. Date coverage and evidence caps continue
to express whether enough recurring dates were resolved.

## Forecast Applicability And Public Assessment

For exact dates, forecast availability has one typed state:

- `not_yet_available`: every requested date is beyond the maximum active
  forecast horizon;
- `available`: every forecast-applicable requested date has usable evidence;
- `partial`: some forecast-applicable requested dates have usable evidence;
- `unexpectedly_unavailable`: no forecast-applicable requested date has usable
  evidence;
- `not_applicable`: the request is month-only and intentionally climatology-only.

The backend exposes this status consistently on the ranked search configuration
and detailed weather-evidence response.

The backend also owns the canonical public snow assessment: `not_assessed` when
no travel window exists, otherwise `strong_fit`, `some_concerns`, or
`not_enough_evidence`. A snow-quality claim requires resolved evidence for every
requested exact date or every calendar day represented by a month search; lower
coverage still scales ranking influence but is presented as
`not_enough_evidence`. The strong-fit and minimum-coverage thresholds remain
versioned weather policy and are not duplicated in React. Expected forecast
absence beyond 30 days is neutral context and cannot create a main concern.
Partial or unexpectedly unavailable in-horizon evidence remains a visible
limitation, while its missing forecast share returns to climatology rather than
becoming a fabricated negative score.

For `some_concerns`, the backend returns a typed primary reason derived from the
same depth, consistency, deterioration, and forecast inputs used by the score.
The detailed evidence response exposes the averaged historical deterioration
risk so a rain/freeze-thaw penalty is not hidden from the user. Exact windows
entirely before the request reference date are rejected rather than overloading
the month-only `not_applicable` status.

When accepted forecast evidence exists without historical context, the detailed
response uses `forecast_only`, keeps historical evidence null, and presents the
forecast that actually influenced ranking instead of returning a contradictory
historical-evidence error.

## Initial Provider And Model Policy

The first acquisition gateway is Open-Meteo's Ensemble Mean API. Model
producers and the API gateway remain distinct provenance fields.

- `ecmwf_ifs025_ensemble_mean` is preferred for complete local daily evidence
  through `lead_days <= 15`.
- `ncep_gefs05_ensemble_mean` is selected for `16 <= lead_days <= 30` and may
  fill a shorter-range date when the preferred ECMWF row is missing, stale, or
  incomplete.
- Snowcast selects one eligible source for a ski-area/date evaluation. It does
  not average the two model products together.
- If neither source has a valid row, forecast coverage is zero and the date is
  fully climatological.

Both routes are ensemble-mean products with spread fields. GEFS supplies daily
coverage to day 30 but uses a coarse 0.5 degree, approximately 50 km global
grid. Its daily resolution must not be described as daily precision; the
`17–30` lead-time cap limits its maximum contribution to 15%.

Provider capability references:

- [Open-Meteo Ensemble API](https://open-meteo.com/en/docs/ensemble-api)
- [Open-Meteo Ensemble Mean API](https://open-meteo.com/en/docs/ensemble-mean-api)
- [Open-Meteo model-update metadata](https://open-meteo.com/en/docs/model-updates)

The ensemble response does not carry the model initialization timestamp. Before
fetching an acquisition batch, the job reads the selected model's metadata and
stores `last_run_initialisation_time` and `last_run_availability_time`. It waits
until at least ten minutes after the reported availability time, as recommended
for Open-Meteo's eventually consistent servers. After fetching all bounded
coordinate batches, it reads the metadata again. If the initialization time
changed, the building run is rejected and retried so one published run cannot
mix two model cycles.

### Daily Normalization

The gateway returns hourly ensemble-mean and spread values. Normalization groups
timestamps by the provider-returned local timezone and records the aggregation
policy version on the run. The initial daily row stores, when supported by the
configured source:

- snow depth and snow-depth spread at 12:00 local time, representing the ski
  day's central daylight period rather than summing or averaging an
  instantaneous state variable;
- summed snowfall and rain;
- positive degree-hours derived from complete hourly temperature evidence;
- minimum and maximum two-metre temperature;
- optional mean and maximum freezing-level height;
- maximum wind speed and gust.

Each source key declares required and optional variables because supported
spread and freezing-level fields differ by model. A local day is publishable
only when every required variable has the expected 23, 24, or 25 local-hour
timestamps for that calendar date. Missing optional fields remain null and
visible in completeness metadata. A partial boundary date is omitted rather
than presented as complete; source selection may then use the eligible GEFS
fallback or return to climatology. It never substitutes an adjacent valid
date. The model initialization time, provider availability time, provider
timezone, local valid date, and original units remain explicit so
daylight-saving and model-horizon boundaries are reproducible.

## Forecast Evidence Inputs

The first forecast evaluator consumes one normalized local-day row at the ski
area's representative `mid` elevation. The row may contain:

- ensemble-mean snow depth and its spread;
- forecast snowfall and rain;
- minimum and maximum temperature;
- freezing level or an equivalent derived rain/snow boundary;
- wind speed and gust risk;
- ensemble member count and other supported spread fields.

Base and upper rows are not acquired or scored initially. The schema keeps
`elevation_band` and `representative_elevation_m` so a later evidence model can
add them without changing row identity or confusing them with predicted open
terrain.

The model should stay tied to physical weather-model output. Marketing snow
claims and LLM interpretations are not forecast evidence. The LLM does not
derive, weight, or calibrate weather variables.

Forecast snow depth is a modelled point/elevation value. It does not establish:

- percentage of the ski area with snow cover;
- percentage or kilometres of pistes expected to open;
- lift availability;
- official avalanche or route safety.

Those are separately named future evidence and factor families.

## Initial Physical-Driver Composition

The initial `trip_window_snowpack_outlook_d` is deterministic and
depth-led:

```text
trip_window_snowpack_outlook_d = clamp(
    depth_adequacy_d
  + 0.15 * fresh_snow_benefit_d
  - 0.25 * rain_thaw_risk_d,
  0,
  1
)
```

`depth_adequacy_d` is the primary component and expresses whether the modelled
mid-mountain snow depth is adequate for skiing. `fresh_snow_benefit_d` is a
smaller positive component derived from forecast snowfall for the local day.
`rain_thaw_risk_d` combines rain and positive-temperature exposure into one
deterioration component so correlated physical signals are not charged as
independent penalties.

Each normalized component uses piecewise-linear interpolation between these
ordered points and clamps outside the stated range:

| Component | Physical value to normalized value |
| --- | --- |
| `depth_adequacy_d` | snow depth `0/10/20/30/60/100 cm` to `0/0.15/0.40/0.60/0.90/1` |
| `fresh_snow_benefit_d` | local-day snowfall `0/5/15/30 cm` to `0/0.25/0.70/1` |
| `rain_surface_risk_d` | local-day rain `0/5/15/30 mm` to `0/0.25/0.75/1` |
| `thaw_surface_risk_d` | positive degree-hours `0/12/36/72 °C h` to `0/0.20/0.60/1` |

`positive_degree_hours_d` is the sum of `max(hourly_temperature_c, 0)` over
the complete local day. The combined risk is:

```text
rain_thaw_risk_d = max(rain_surface_risk_d, thaw_surface_risk_d)
```

Using the maximum prevents liquid rain and above-freezing temperature from
becoming two full correlated penalties. Freezing level remains optional
supporting and explanatory evidence because it is not available consistently
from both initial model routes.

Wind speed and gusts describe operational disruption rather than snowpack
adequacy and do not enter this utility initially. Ensemble spread remains
stored and visible in explanations but does not become a second confidence
multiplier. These response curves and weights are versioned ranking policy and
must not be embedded in provider or acquisition code.

### Scientific Interpretation And Limits

This utility is a decision policy over forecast-model output, not a new
snowpack simulator. Operational models provide useful structure but do not
publish a universal ski-ranking equation:

- NOAA's [SNOW-17](https://training.weather.gov/nwstc/Hydrology/HYDRO/RFS/RFS303d.html)
  represents one snow column with temperature-indexed energy exchange and
  distinct rain-on-snow and non-rain melt treatment.
- [Crocus-Resort](https://doi.org/10.1016/j.coldregions.2016.01.002) uses a
  detailed mass and energy balance plus grooming and snowmaking because managed
  piste snow responds non-linearly and differs materially from natural snow.
- French-Alps ski-reliability research uses approximately 20 cm of dense
  groomed snow as a daily skiable-area threshold and models 30 cm base-building
  and 60 cm maintenance targets, while older natural-snow studies commonly use
  30 cm as a coarse reliability threshold. These are useful curve anchors, not
  universal statements about an individual ski day.
- A Northern-Hemisphere evaluation of temperature-index models found that melt
  factors vary by climate, terrain, and scale and recommends full energy-balance
  modelling where feasible. Snowcast therefore does not apply a homemade
  degree-day melt model on top of the provider's modelled snow depth.

The provider's snow-depth state remains the primary evidence. Fresh snowfall
and rain/thaw are bounded surface-condition modifiers; they must not be
described as independently reconstructing snow accumulation or melt already
represented by the forecast model. Their exact response curves are Snowcast
policy, validated with named scenarios and kept distinct from scientific
constants. Later official open-piste and open-lift predictions remain more
direct operational evidence and must not be inferred from this utility.

References for the ski-specific thresholds and modelling boundary include the
[French-Alps reliability study](https://www.nature.com/articles/s41598-019-44068-8),
the [100-day-rule review](https://tc.copernicus.org/articles/13/1325/2019/),
and the [temperature-index parameter evaluation](https://hess.copernicus.org/articles/30/2613/2026/).

## Persistence Model

The implementation should introduce three dedicated concepts.

### `weather_forecast_runs`

One immutable provider issue:

- `forecast_run_id`;
- stable `forecast_source_key` identifying the configured acquisition route;
- provider and provider model identifier;
- forecast kind such as deterministic or ensemble;
- model initialization time, provider availability time, and ingestion time;
- first and last valid date;
- run status such as building, complete, rejected, or failed;
- schema/parser version and bounded provider metadata;
- daily aggregation policy version.

### `ski_area_weather_forecast_daily`

One normalized daily/elevation evaluation input:

- forecast run ID;
- ski area ID;
- valid local date, ski-area/provider timezone, and elevation band;
- representative elevation and request coordinates;
- normalized physical forecast variables;
- ensemble member count and supported spread fields;
- row-level completeness and quality metadata.

The natural lookup path is run, ski area, valid date, and elevation band. Daily
rows are immutable after their run is published and retain provider, model,
model initialization time, valid date, and derived lead time through their run
relationship.

For daily forecast policy, `lead_days` is the difference between the valid local
date and the model initialization timestamp converted to the stored
ski-area/provider timezone and truncated to its local date. This calendar-day
definition makes the
`0–5`, `6–10`, and later boundaries deterministic across UTC refresh times and
daylight-saving changes. Hourly evidence may preserve exact UTC valid times in
a future extension, but it must not silently change the daily lead-time rule.

### `ski_area_forecast_heads`

The serving pointer:

- ski area ID and forecast kind;
- forecast source key;
- current complete forecast run ID;
- head update time.

The head identity is `(ski_area_id, forecast_source_key)`, not only ski area and
generic ensemble kind. This allows the current ECMWF and GEFS runs to coexist
and lets deterministic planning policy select the eligible source by lead day.

Heads advance only after the run and all publishable rows for the area pass
validation. The previous complete run remains queryable. A failed partial run
never becomes current.

## Acquisition And Publication Lifecycle

```text
scheduled refresh trigger
  -> create building run
  -> fetch provider data in bounded batches
  -> normalize and insert immutable daily rows
  -> validate dates, bands, values, completeness, and provenance
  -> mark run complete
  -> atomically advance heads for successfully covered ski areas
  -> emit refresh and freshness telemetry
```

An area may keep its previous head when the new run is incomplete for that
area. Publication must not require every catalog ski area to succeed as one
global transaction, but a head can never point at a building, rejected, or
failed run.

Refresh cadence is an implementation policy based on provider issue cadence and
cost. Search does not trigger refreshes.

## Request-Path Serving

Search first applies static constraints and identifies candidate ski-area IDs.
The forecast repository then performs one bounded indexed query using:

- candidate ski-area IDs;
- requested start and end dates;
- eligible forecast source keys;
- current head run IDs.

The result is grouped in memory by ski area, date, elevation band, and forecast
source key for pure factor evaluation. The request path must not:

- call a weather provider;
- query separately for each candidate;
- select latest runs using `MAX(issued_at)` over daily rows;
- scan retained historical runs;
- require Redis for correctness.

At current catalog scale, a 30-day horizon across two source keys and one
initial elevation band remains small enough for Postgres serving. Add caching
only after tracing shows that the bulk indexed query or decoding is materially
affecting search latency. Any later cache must remain an optimization over the
Postgres head contract, not a second source of truth.

## Confidence, Calibration, And Trust

Every evaluator retains these fields independently:

- source provenance;
- provider/model/run identity;
- issue and valid time;
- lead time and the timezone used to derive daily `lead_days`;
- date and elevation coverage;
- freshness;
- deterministic versus ensemble basis;
- ensemble agreement or spread;
- configured lead-time policy version.

Provider output availability is not a claim of certainty. The initial policy
expresses decreasing long-range confidence through the documented
forecast/climatology shares and rejects missing, stale, or incomplete rows. It
does not add an uncalibrated provider multiplier on top of those shares.

The run store enables later forecast-versus-observation evaluation. Retention
is tiered by model initialization time:

- retain every complete issue run and its normalized daily rows for 45 days;
- from day 46 through two years, retain one canonical complete run per
  `forecast_source_key` and UTC initialization date, preferring the `00Z` run
  and otherwise the earliest complete run for that date;
- after two years through five years, retain one canonical complete run per
  source and ISO week, again preferring a retained `00Z` run;
- remove normalized forecast rows after five years, while keeping compact
  aggregate calibration reports and their policy/model versions;
- retain failed or rejected run metadata for 90 days, but never publish or use
  their partial rows for calibration;
- never purge a run referenced by a current serving head.

The retention job runs outside the request path and deletes rows only after the
replacement sample for the relevant day or week is known to be complete. This
keeps dense recent evidence for incident diagnosis, daily samples for regular
lead-time analysis, and multi-season weekly samples for detecting durable
model or policy behavior. Latest-only overwriting is not acceptable because it
would remove the old predictions needed for comparison with eventual evidence.
Calibration is not a prerequisite for initial activation.

## Failure And Fallback Policy

- Provider failure leaves existing heads unchanged.
- Partial area failure leaves that area's previous head unchanged.
- A stale head remains usable only through the policy-defined freshness cap and
  visible uncertainty.
- Missing dates or bands reduce date coverage rather than being imputed as good
  conditions.
- No trustworthy forecast yields zero forecast share and full climatology.
- Missing climatology and forecast evidence produces the factor's documented
  cautious neutral/fallback behavior, not a fabricated snow claim.
- Forecast refresh failure never makes `/api/search` unavailable.

## Observability

Low-cardinality metrics and spans should cover:

- run attempts, completion, rejection, and failure by provider/forecast kind;
- run duration and provider request duration;
- age of the oldest and typical current head;
- aggregate ski-area and valid-date coverage;
- bulk forecast preload duration and returned row count;
- searches using forecast, climatology-only fallback, partial coverage, or
  stale evidence.

Do not put ski-area IDs, run IDs, exact valid dates, coordinates, URLs, or raw
provider errors in metric labels. Use traces and sanitized structured logs for
run-specific investigation.

## Security And Privacy

- Provider credentials stay in runtime configuration and never enter run
  metadata, logs, or search responses.
- Forecast rows contain public environmental data, not user data.
- Candidate ski-area IDs and travel dates must not be copied into
  high-cardinality telemetry.
- Provider payloads and errors are bounded and sanitized before logging.

## Acceptance Criteria

- Search can retrieve the latest complete forecast evidence for all candidate
  ski areas and requested dates in one repository call.
- A failed or partial refresh cannot advance an invalid head.
- Previous run versions remain available for audit and calibration.
- Exact-date ranking uses the documented per-day lead-time caps.
- Zero coverage or confidence returns the forecast share to climatology.
- Month-only and more-than-30-day searches do not use a current snapshot as a
  target-date forecast.
- Search performs no request-path provider call and remains usable during
  provider failure.
- Forecast snow depth is never labelled as ski-area snow coverage or expected
  open terrain.
- Forecast evidence never enters archive climatology.

## Verification

Persistence and repository tests:

- immutable run insertion and valid state transitions;
- unique daily row identity and referential integrity;
- atomic head publication and rollback on validation failure;
- previous-head preservation for partial area failure;
- one bulk latest-head query across areas, dates, kinds, and elevation bands;
- query-plan/index verification at representative catalog and horizon size.

Model tests:

- exact boundary dates for every lead-time cap and the ECMWF-to-GEFS routing
  boundary;
- issue times around local midnight and daylight-saving transitions;
- a trip spanning multiple lead-time bands;
- partial requested-date and elevation coverage;
- stale, incomplete, preferred-source, fallback-source, and absent evidence;
- zero-forecast fallback to climatology;
- month-only and over-30-day climatology-only behavior;
- no confusion between snow depth and operational coverage.

Job and failure tests:

- ECMWF and GEFS source-contract fixtures, including unsupported optional
  freezing-level fields;
- metadata initialization/availability parsing and a model-cycle change during
  a multi-batch fetch;
- local-noon snow-depth selection, complete 23/24/25-hour aggregation, and
  incomplete boundary-date omission;
- provider timeout, rate limit, malformed payload, and partial batch;
- rejected run never becoming a head;
- refresh retry without duplicate publication;
- search availability while refresh is running or failing;
- bounded telemetry without sensitive or high-cardinality labels.

## Rollout Direction

1. Add persistence schema, repository contracts, and head publication tests.
2. Add the ECMWF and GEFS ensemble-mean acquisition routes and normalized daily
   `mid`-elevation rows.
3. Implement source selection, forecast utility, and the documented
   forecast/climatology composition.
4. Activate `trip_window_snow_fit` when golden scenarios, failure tests,
   performance checks, and advisory feature review pass. Do not add a separate
   diagnostic-only production phase.
5. Retain bounded issue history for a later calibration refinement without
   making historical forecast validation an initial activation gate.

There is no Search V3 comparison or rollback requirement. Correctness is
defined by this policy, the Search V4 model, and reviewed golden scenarios.

## Advisory Review

- Design reviewers: backend-api, data-trust-source-integrity,
  observability-ops, performance, product-strategy.
- Feature reviewers: the same set, narrowed to the implemented provider,
  persistence, serving, and evaluator surfaces.
- Climatology reliability v2 design review: product-strategy, backend-api,
  data-trust-source-integrity, and content-language reviewed the accepted
  formula, forecast-applicability states, backend-owned public assessment, and
  deferred public-page migration on 2026-07-20. No Blocker or High finding
  remained after adding `not_assessed`, requiring typed forecast status on both
  search and weather-evidence responses, and keeping the strong-fit boundary in
  versioned backend policy.
- Required design focus: scientific claim boundaries, confidence semantics,
  run publication atomicity, query shape, failure isolation, and telemetry
  cardinality.
- Design-review result: no Blocker or High findings. The focused provider
  follow-up covered the accepted ECMWF/GEFS routing, daily-only storage,
  mid-elevation scope, model-cycle identity, daily aggregation, exact-date
  fallback, and removal of an initial calibration gate. Exact utility policy
  and retained-run sampling remain explicit implementation concerns rather
  than hidden provider assumptions.
- Final combined ExecPlan review completed on 2026-07-15 with no additional
  forecast-specific Blocker or High finding. It added an explicit additive-
  schema/manual-refresh/schedule-enablement release order and kept missing
  forecast heads as a valid climatology fallback rather than a readiness
  failure.
