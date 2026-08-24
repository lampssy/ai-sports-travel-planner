# ADR 0021: Gate Ski-Area Weather Sampling With Reviewed Geometry

Status: accepted
Date: 2026-08-19

Supersedes: N/A
Superseded by: N/A

Related ADRs:
- `docs/architecture/adr/0007-ski-area-weather-evidence-and-catalog-retirement.md`
- `docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md`

Related docs:
- `docs/domain-language.md`
- `docs/snow-evidence-model.md`
- `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`

## Context

Every active catalog ski area was previously eligible for current-weather
refresh, archive backfill, forecast refresh, historical-weather completion, and
climatology rebuild. A curation report could say that weather geometry was not
ready, but that prose did not prevent the scheduled jobs from using the ski
area's coordinates and elevation range.

Snowcast also lacked one stable interpretation of those fields. A village
centre, lift station, provider viewport, bounding-box centre, and terrain
representative point are not interchangeable weather coordinates. Likewise,
local base altitude, highest named peak, and lift-served ski-area bounds are
different elevation scopes. Allowing each curation pass to choose independently
made review non-convergent and could attach weather evidence to the wrong
terrain.

Catalog topology and weather readiness are separate concerns. A defensible ski
area can belong in the graph before a reproducible weather sampling point has
been established. Removing or withholding that entity would distort access,
pass, and terrain relationships, while sampling it prematurely would create
untrustworthy weather evidence.

## Decision

Every `SkiArea` has a typed `weather_sampling_status`:

- `active`: automated weather refresh, backfill, completion, and climatology
  jobs may select the ski area, and product reads may serve its weather
  evidence;
- `deferred`: the ski area remains in the catalog and product graph, but those
  jobs must skip it and product reads must use non-weather fallback evidence.
  An explicit command targeting the deferred ski area fails clearly rather
  than reporting a misleading no-op success.

Changing the status does not delete raw history, climatology, forecasts, or
conditions. Existing evidence remains attached to its durable `ski_area_id`,
but product reads do not serve it while the area is deferred.

The ski-area coordinate is a representative sampling point for the complete
modeled lift-served terrain. Use this hierarchy:

1. medoid of complete official terrain geometry (`verified`);
2. medoid of complete or sufficiently complete OSM terrain geometry,
   corroborated by the official map (`verified_with_adjustment`);
3. exact official central on-mountain hub or weather point, or an unambiguous
   official named hub/weather point matched to exact OSM feature geometry
   (`verified_with_adjustment`);
4. medoid of a complete structured lift inventory
   (`verified_with_adjustment`);
5. otherwise set `weather_sampling_status=deferred`.

Do not use an unverified map viewport, village centre, isolated lift endpoint,
bounding-box midpoint, or arithmetic average of conflicting coordinates.
Sufficient OSM geometry means every official named terrain sector is
represented, no known boundary-defining lift cluster is omitted, the reviewed
point lies within the skiable footprint, and discrepancies with the official
map are documented.

Deferral is an evidenced conclusion, not the absence of a coordinate in the
initial source packet. When no accepted coordinate is available, the typed
assessment records all four hierarchy tiers in order. Every attempt identifies
the method, its `rejected` or `unavailable` outcome, direct evidence references,
and a concise reason. When a fallback tier is selected while sampling remains
deferred for another geometry reason, every higher-priority tier is recorded and
the selected tier uses outcome `selected`.

`base_elevation_m` and `summit_elevation_m` are the area-wide lift-served
elevation bounds used both for user-facing terrain range and the base/mid/upper
weather request bands. Use this hierarchy:

1. official area-wide lift-served range (`verified`);
2. range derived from a complete official lift inventory (`verified`);
3. range from reviewed structured open data corroborated by the official map
   (`verified_with_adjustment`);
4. a specialist source such as Bergfex only as a same-scope conflict tie-break
   (`verified_with_adjustment`);
5. otherwise defer weather sampling.

Never average conflicting elevations. First determine whether values describe
the same terrain scope; keep legitimate differently scoped values on their own
entities.

Schema-v3 curation reports treat every new ski area and every retained ski area
whose coordinate, elevation bounds, or sampling status changes as a weather
geometry target. The typed assessment records before/after request geometry,
coordinate and elevation derivation methods, geometry completeness, derivation
status, coordinate-attempt evidence, and an activation prerequisite when
deferred. A new active ID records its scheduled historical-weather completion
handoff. A retained ID with changed coordinates or elevation bands records a
targeted forced-refetch and climatology-rebuild handoff; when sampling remains
deferred, that handoff occurs after activation.
Catalog reconciliation derives the required target set, including new IDs, so
report prose cannot waive the assessment.

Retained IDs with unchanged terrain boundaries may preserve an already
defensible sampling geometry. Catalog curation records the operational handoff
but does not run production weather jobs before the PR is prepared or merged.
A material geometry change requires the existing force-refetch and climatology
rebuild after merge when active, or after later activation when deferred.

## Consequences

- Catalog graph work can merge without manufacturing weather evidence.
- Scheduled weather jobs and data-quality coverage expectations share one
  typed eligibility decision.
- Existing catalog ski areas are explicitly migrated to `active`; future
  curation must review the field and geometry assessment for new IDs.
- Deferred areas can still appear in planning, but will use non-weather fallback
  evidence until activated and populated.
- Curation reports become more explicit, but the same metadata makes reviews
  reproducible and prevents repeated coordinate/elevation arguments.
- A reviewer can distinguish exhausted derivation options from incomplete
  research, and can see the required post-merge weather work directly in the
  rendered report.

## Alternatives Considered

- **Block creation of the ski area until geometry is ready.** Rejected because
  catalog topology, access, and pass coverage should not depend on weather-data
  readiness.
- **Maintain an operational exclusion list outside the catalog.** Rejected
  because it creates a second source of truth and is easy for new workflows to
  ignore.
- **Treat every catalog ski area as weather-active and rely on report prose.**
  Rejected because scheduled jobs cannot enforce prose.

## Revisit When

- weather sampling requires several horizontal points per ski area;
- provider-native station or grid-cell ownership becomes a separate durable
  entity;
- product serving needs a distinct status from sampling eligibility; or
- terrain geometry becomes a first-class stored polygon rather than reviewed
  derivation evidence.
