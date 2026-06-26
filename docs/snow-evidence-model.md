# Snow Evidence Model

Snowcast uses an empirical ski-planning evidence model, not a physical
snowpack simulation. The goal is decision support for trip planning: explain
whether a requested ski window is historically reliable, whether near-term
forecast signals should alter that view, and how much evidence supports the
recommendation.

## Scientific Baseline

The long-horizon baseline follows the climatology pattern used by the World
Meteorological Organization: a 30-year normal is the default reference for
climate-sensitive decisions. WMO identifies standard climatological normals as
30-year periods such as 1991-2020, and recommends 1991-2020 as the current
global baseline reference.

References:

- [WMO climatological normals](https://community.wmo.int/site/knowledge-hub/programmes-and-initiatives/climate-services/wmo-climatological-normals)
- [WMO 1991-2020 baseline update](https://wmo.int/media/news/wmo-publishes-global-update-of-climate-datasets)

Snowcast adapts that idea to ski planning:

- `normal_30y`: primary baseline, using up to 30 archive seasons ending at the
  latest complete archive year.
- `recent_15y`: secondary adjustment baseline, used to nudge the 30-year normal
  toward recent climate behavior without replacing the more stable normal.

This is a pragmatic planning model. It does not claim official climatological
normal status for every ski area because the underlying weather archive is
gridded/model-backed rather than resort-operated station data.

## Data Layers

### Evidence Entity Ownership

Weather evidence is owned by modeled ski areas. A ski area is the smallest
durable skiable terrain unit Snowcast scores and refreshes, such as Tignes,
Val d'Isere, Grands Montets, or Brévent-Flégère.

Destination, terrain-group, and terrain-domain records can organize how options
are displayed and how accessible terrain is counted, but they do not own raw
weather history or derived climatology. When a recommendation card is displayed
at destination level, its weather explanation is still scoped to the selected
ski area that produced the top concrete trip option.

Normal catalog bootstrap must preserve ski-area evidence rows. If a ski area is
removed from the current seed catalog, it is retired from active catalog reads
rather than deleted from the database. Explicit database reset, targeted archive
rebuild, or reviewed ID migration is required before historical evidence is
deleted or moved.

Current forecast condition rows follow the same identity rule for runtime
lookup: they are keyed by `ski_area_id`. A stored ski-area name is display
metadata only, so renamed or replacement ski-area IDs do not collide on a reused
public label.

### Raw Archive

`raw_weather_history` stores daily archive weather observations per ski area and
elevation band. It remains the audit and rebuild source.

Important fields include:

- `observed_on`
- `elevation_band`
- `snow_depth_m`
- `snowfall_cm`
- `rain_sum_mm`
- `temperature_2m_min_c`
- `temperature_2m_max_c`
- `wind_gusts_10m_max_kmh`
- `record_type = 'archive'`

The archive may use provider model/reanalysis data. Reanalysis is appropriate
for this stage because it provides consistent historical time series; Copernicus
describes reanalyses as models plus observations used to reconstruct past
climate variables.

References:

- [Copernicus climate reanalysis overview](https://climate.copernicus.eu/climate-reanalysis)
- [ECMWF ERA5 overview](https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5)

### Derived Climatology

`ski_area_snow_climatology_daily` stores precomputed day-of-season statistics by
ski area, elevation band, baseline period, and source-model version.

It is a derived read model, not canonical truth. Rebuild it from raw archive
rows whenever the archive is rebuilt, weather-critical coordinates/elevations
change, or the empirical model version changes.

Stored outputs include:

- snow-depth percentiles: p25, p50, p75
- probability snow depth is at least 30 cm
- probability snow depth is at least 50 cm
- average daily snowfall
- rain-risk probability
- freeze-thaw probability
- average maximum temperature
- average wind gust
- average empirical snow-confidence and conditions scores

The 30 cm and 50 cm thresholds are planning heuristics, not universal ski-area
operability rules. They give users a legible way to compare marginal, low-base,
or late-season windows.

## Search-Time Evidence Order

For a requested travel window, planning uses evidence in this order:

1. Exact season-window check when known.
2. Derived snow climatology for the requested month/day window.
3. Raw archive rows for the requested month/day window.
4. Legacy monthly condition snapshots.
5. Season/elevation heuristic fallback.

The search request path should prefer climatology because it reads a small,
indexed derived table instead of constructing years of raw daily weather rows.
Raw archive remains the fallback and audit path.

## Forecast Assistance

Current forecast conditions should only affect planning when the trip is close
enough that forecast skill is meaningful.

Current policy:

- 0-14 days before exact trip start: forecast weight `0.35`
- 15-30 days before exact trip start: forecast weight `0.15`
- farther exact-date trips: forecast weight `0.0`
- month-only same-month planning: forecast weight `0.20`
- month-only next-month planning: forecast weight `0.08`

When forecast weight is non-zero and archive/climatology evidence exists, the
user-facing profile is `forecast_assisted`. Far-future planning should normally
be `archive_backed` or `fallback_heavy`.

## Physical Snowpack Models

Snowcast does not currently run physical snowpack models such as SNOWPACK,
Crocus, or SAFRAN-Crocus-MEPRA/S2M-style chains.

Those models simulate snowpack energy balance, layering, metamorphism, and
other detailed snow processes. They are scientifically stronger for operational
snowpack analysis, avalanche support, or climate-impact studies, but they need
more forcing data, calibration, compute, and validation than Snowcast currently
has.

References:

- [SNOWPACK model](https://snowpack.slf.ch/)
- [Crocus model summary](https://www.geo.utexas.edu/climate/Research/SNOWMIP/SUPERSNOW2/eric.martin.html)
- [Copernicus mountain tourism snow indicators](https://cds.climate.copernicus.eu/datasets/sis-tourism-snow-indicators)

Snowcast should reference these methods internally as future upgrade paths, but
should not expose their names to users unless the product actually implements
or consumes provider-backed outputs from those model families.

## User-Facing Language

Expose the evidence profile, not scientific model names:

- `Archive-backed`: derived from historical archive/climatology evidence.
- `Forecast-assisted`: historical evidence plus current forecast signal.
- `Fallback-heavy`: mostly season/elevation heuristics or weak legacy evidence.

Good user-facing copy:

- "High evidence - archive-backed, 30 seasons"
- "Medium evidence - forecast-assisted"
- "Limited evidence - fallback-heavy"

Avoid overclaiming:

- Do not say "guaranteed snow."
- Do not say "official snow report" for modeled weather evidence.
- Do not expose Crocus, SNOWPACK, S2M, or WMO labels as marketing badges unless
  the backend truly uses those methods or datasets directly.

## Rebuild Policy

Before a large backfill:

1. Lock weather-critical ski-area coordinates and elevation bands.
2. Rebuild `raw_weather_history`.
3. Run the climatology rebuild command.
4. Verify search uses `snow_climatology` rather than raw-history fallback.

Command:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.rebuild_snow_climatology
```

For one destination or ski area:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.rebuild_snow_climatology --target tignes
```

For a fixed latest archive year:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.rebuild_snow_climatology --baseline-end-year 2025
```

Backfill and climatology rebuild commands select active catalog ski areas by
default through `ResortRepository.list_resorts()`. Retired ski areas remain in
the database only to preserve existing evidence and are not refreshed unless a
future explicit maintenance path includes inactive entities by reviewed intent.
