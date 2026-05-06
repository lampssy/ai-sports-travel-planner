# Catalog Acquisition Patch PR Design

## Summary

Add a Sprint 30 follow-up that turns catalog acquisition evidence into reviewable catalog edits without making acquisition itself canonical. The pipeline keeps producing `proposals.json`, `fetch-log.json`, and `evidence.md`; a separate patch command applies only conservative `new` proposals into `resorts.json` and `sources.json`; GitHub Actions can optionally create a draft PR with those edits and the evidence packet.

## Goals

- Add app-facing catalog fields for acquisition facts that are already being extracted:
  - `ski_areas[].total_piste_km`
  - `ski_areas[].total_lift_count`
  - `ski_areas[].piste_km_by_difficulty`
  - `lift_pass_prices`
- Keep terrain facts ski-area scoped because OpenDataHub, Bergfex, and official ski-area pages describe terrain entities, not travel destinations.
- Keep lift-pass price examples destination scoped because they are user-facing planning facts attached to the trip destination.
- Add a local patch generator that applies only safe, missing values and writes a review summary.
- Add an opt-in GitHub Actions draft PR path after acquisition, patching, validation, and focused tests.
- Preserve artifact-only behavior by default.

## Non-Goals

- No automatic merge or auto-approval.
- No database canonical catalog model.
- No dynamic operating status ingestion.
- No automatic conflict resolution between sources.
- No full pricing product model beyond reviewed adult/default examples.

## Data Model

`SkiArea` gains optional terrain metadata:

- `total_piste_km: float | None`
- `total_lift_count: int | None`
- `piste_km_by_difficulty: { beginner, intermediate, advanced } | None`

`Destination` gains:

- `lift_pass_prices: list[LiftPassPrice]`

`LiftPassPrice` stores only reviewed catalog values:

- `duration_days`
- `audience`
- `amount` or `amount_min`/`amount_max`
- `currency`
- `price_kind`
- optional `season_label`
- optional `source_url`

LLM extraction evidence remains in artifacts and is not stored in the catalog price object.

## Proposal Targeting

- OpenDataHub/Bergfex/official-page terrain facts target `ski_area` when catalog context identifies a single ski area.
- If no ski-area target can be resolved, the proposal may remain destination-scoped for evidence, but the patch generator will not auto-apply terrain facts to destination fields.
- URL and regional ID proposals remain destination-scoped and patch into `sources.json`.
- Existing coordinate/elevation/season behavior is unchanged.

## Patch Generator

Add:

```bash
python -m app.data.resort_acquisition.generate_catalog_patch \
  --artifacts-dir artifacts/catalog-acquisition
```

Inputs:

- `artifacts/catalog-acquisition/proposals.json`
- `app/data/resorts.json`
- `app/data/resort_acquisition/sources.json`

Outputs:

- Patched `resorts.json` and/or `sources.json`
- `artifacts/catalog-acquisition/patch-review.md`

Auto-applied proposals:

- only `status == "new"`
- only accepted extraction methods/source types already represented in proposals
- only missing catalog/source-registry fields
- `season_windows` append when that exact window is absent
- ski-area terrain fields when target is a known `ski_area`
- destination `lift_pass_prices` for official adult/default price examples with supported durations
- source registry official URLs and regional IDs when missing

Skipped proposals:

- `changed`, `conflict`, `warning`, `rejected`, and `same`
- unsupported field paths
- missing target entities
- terrain facts targeting `destination`
- duplicate price/window entries

## GitHub Actions

The catalog acquisition workflow gains `create_pr` input defaulting to `false`.

Default behavior:

- run acquisition
- upload artifacts
- fail on acquisition errors
- do not write catalog files
- do not create a PR

When `create_pr=true` and acquisition succeeds:

- run patch generator
- validate the patched catalog
- run focused tests
- create a draft PR only when `git diff` has changes
- include `patch-review.md` and evidence guidance in the PR body

## Validation

- Unit tests for model loading and patch generator behavior.
- Existing acquisition tests for proposal targeting and evidence output.
- Workflow static test proving default artifact-only behavior remains opt-in and PR mode includes validation gates.
- Focused verification:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_loader.py tests/test_resort_acquisition.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/resort_acquisition app/domain tests/test_loader.py tests/test_resort_acquisition.py
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```
