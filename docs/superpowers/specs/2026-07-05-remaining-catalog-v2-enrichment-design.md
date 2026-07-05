# Remaining Catalog V2 Enrichment Design

Date: 2026-07-05
Status: approved

## Objective

Research and populate the source-aware ski-area, stay-base, and aggregate-map
facts introduced by catalog schema version 2 for every canonical destination
not covered by the existing catalog-curation pull requests.

The work produces independently reviewable draft pull requests. It does not
merge branches, change destination boundaries, or broaden the catalog beyond
the 17 approved destinations.

## Scope

The enrichment reviews these fact groups:

- `SkiArea`: snowmaking, glacier terrain, snow park, night skiing, marked
  freeride routes, official trail map, and ski-day apres;
- `StayBase`: elevation, structural base type, development style, local pace,
  and local apres;
- `TerrainDomain`: official trail map when the document genuinely describes
  the connected aggregate; and
- `SkiAreaAccess`: only a concrete omission discovered while researching the
  approved entities. Existing access facts are otherwise outside this narrow
  enrichment.

Existing destination boundaries, weather identities, pass products, prices,
lodging estimates, terrain metrics, and unrelated trust groups remain outside
scope unless source research exposes a direct contradiction that prevents an
honest enrichment. Such a contradiction stops the affected cycle for review;
it is not silently repaired as incidental work.

## Pull Request Batches

Each branch starts independently from the same current `main` baseline and
targets `main` as a draft pull request.

| Branch suffix | Destinations | Connected terrain domain |
| --- | --- | --- |
| `alta-badia-v2` | Alta Badia | none |
| `auronzo-di-cadore-v2` | Auronzo di Cadore | none |
| `matterhorn-ski-paradise-v2` | Cervinia, Zermatt | Matterhorn Ski Paradise |
| `chamonix-mont-blanc-v2` | Chamonix Mont-Blanc | none |
| `cortina-dampezzo-v2` | Cortina d'Ampezzo | none |
| `campiglio-dolomiti-v2` | Folgarida-Marilleva, Madonna di Campiglio, Pinzolo | Campiglio Dolomiti di Brenta |
| `hintertux-v2` | Hintertux | none |
| `livigno-v2` | Livigno | none |
| `misurina-v2` | Misurina | none |
| `san-vito-di-cadore-v2` | San Vito di Cadore | none |
| `tignes-val-disere-v2` | Tignes, Val d'Isere | Tignes - Val d'Isere |
| `val-gardena-v2` | Val Gardena | none |
| `zell-am-see-kaprun-v2` | Zell am See-Kaprun | Kitzsteinhorn/Maiskogel - Kaprun |

The connected-domain batches prevent two pull requests from claiming or
editing the same aggregate document owner. Pass-only relationships and nearby
geography do not justify combining the remaining destinations.

## Source And Normalization Policy

Research uses official destination, operator, trail-map, and tourism sources
first. Authoritative structured open data may support settlement identity or
elevation. Specialist secondary sources are corroboration only.

- Website silence remains `unknown`.
- `unavailable` requires an explicit authoritative statement or a reviewed
  complete inventory for the exact owner and season.
- Snowmaking percentage is recorded only with its published denominator basis.
  Snow-machine counts establish availability, not percentage.
- Glacier language, terrain parks, night skiing, and marked freeride routes are
  not copied from an aggregate pass or neighboring ski area.
- Ski-touring routes and generic off-piste marketing are not marked freeride
  routes.
- A trail map belongs to a ski area unless it is explicitly an aggregate map
  for a modeled connected terrain domain.
- Stay-base character and apres values are independently normalized for each
  accommodation base. A ski-area venue does not establish a local-base profile.
- Qualitative mappings use `verified_with_adjustment` and state the
  normalization explicitly.

## Per-PR Artifacts

Every cycle updates only:

- `app/data/catalog.json`;
- `app/data/resort_trust_manifest.json`;
- one new typed JSON report under `docs/catalog-curation/`;
- its rendered Markdown report; and
- a focused test only if the first populated value exposes a contract assertion
  that encoded the previous empty seed state.

Each report declares narrow reviewed targets for all applicable version-2 fact
paths, records exact before/after values, includes direct evidence, classifies
unresolved fields with concrete notes, and includes every changed trust delta.

## Execution Flow

For each batch:

1. materialize an isolated branch from the approved `main` baseline;
2. map its stay bases, ski areas, access edges, domains, and pass references;
3. research every applicable source-aware field before editing;
4. update the catalog and matching trust groups together;
5. generate and render the typed curation report;
6. validate the catalog and reconcile the report against the branch baseline;
7. run diff hygiene and focused tests when code or test contracts change;
8. perform a local Snowcast catalog review;
9. commit and push the branch; and
10. create a draft pull request whose body is the rendered report.

Cycles are independent. An evidence ambiguity blocks only its affected fact or
batch; supported fields still land, unsupported fields stay unknown, and other
batches continue.

## Verification And Review

Every pull request must pass:

- normalized catalog and trust-manifest validation;
- typed curation report validation;
- exact base/current reconciliation;
- `git diff --check`;
- removal of generic migration placeholders from its report;
- local catalog review for owner scope, source scope, trust hygiene, and linked
  domain correctness; and
- GitHub CI after publication.

The campaign ends with a cross-PR audit confirming:

- all 17 destinations are covered exactly once;
- connected terrain domains are owned by only their designated batch;
- all branches are draft pull requests targeting `main`;
- every pull-request body contains the rendered source-aware report;
- no report retains the generic version-2 migration placeholder; and
- every published head has successful required checks, or any still-running
  check is reported explicitly rather than presented as complete.

## Decision And Review Gate

- Classification: review-gated.
- Developer Decision Checkpoints: resolved by owner approval of all 17
  destinations, 13 domain-aware batches, narrow enrichment scope, and
  independent pull requests targeting `main`.
- ADR: not required because the work applies the accepted normalized catalog
  and source-aware fact contracts without changing their ownership semantics.
- Advisory review: a Snowcast catalog review is required for every pull request.

## Merge Considerations

All branches edit shared JSON files even though their entity scopes do not
overlap. They may need mechanical rebasing as other catalog pull requests merge.
Reconciliation must be rerun after any rebase; a previously valid report is not
assumed valid against a new base.
