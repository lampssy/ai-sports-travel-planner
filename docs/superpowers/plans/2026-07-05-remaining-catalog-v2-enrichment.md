# Remaining Catalog V2 Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Historical campaign plan.** The commands and branch workflow below describe
> the original catalog-v2 campaign; they do not authorize current maintainer
> publication. PR #30 is accepted through its schema-v3 report, complete
> candidate/source inventories, exact prepare-base reconciliation, and fresh
> independent review. The maintainer cycle owns commits; the merged maintainer
> helper exclusively owns branch push and GitHub lifecycle publication.

**Goal:** Publish 13 independent, source-backed draft pull requests that enrich all 17 remaining canonical destinations with the approved catalog-v2 ski-area, stay-base, and aggregate-map facts.

**Architecture:** Each pull request starts from commit `455ed412bc081bf85c016dfe35fa27e85697b74e`, owns a non-overlapping destination/domain batch, and changes only the canonical catalog, trust manifest, and one typed report pair. Research is normalized through a local ignored campaign helper, while repository validators and exact reconciliation remain the acceptance authority.

**Tech Stack:** Python 3.11, Pydantic catalog models, JSON catalog/trust files, Snowcast typed curation reports, `uv`/pytest, Git worktrees, GitHub CLI, and official web sources.

---

## File Structure

Campaign-local ignored artifacts:

- `.superpowers/build_catalog_v2_enrichment.py`: applies one reviewed config,
  validates catalog/trust models, derives exact deltas, builds a narrow typed
  report, reconciles it, and renders Markdown.
- `.superpowers/v2_enrichment_remaining/`: one task-named JSON config containing
  reviewed values, evidence, normalization notes, trust-group changes, and
  unresolved notes for its batch.

Committed files per pull request:

- `app/data/catalog.json`: source-aware catalog facts for only that batch.
- `app/data/resort_trust_manifest.json`: matching group-specific trust status,
  source references, and curation notes.
- the exact task-specific JSON report path listed below: typed narrow report
  reconciled against the branch base;
- the matching `.md` path: rendered PR body.
- `tests/test_catalog_trust.py`: only if a populated canonical value exposes an
  assertion that incorrectly required all seed values to remain empty.

The approved design and this plan are committed only on the first Alta Badia
branch as campaign documentation.

## Common Cycle Contract

For every batch, the config must review these exact canonical paths when they
apply:

```text
ski_area:
  snowmaking.availability
  snowmaking.coverage_pct
  snowmaking.coverage_basis
  snowmaking.season_label
  glacier_terrain.availability
  snow_park.availability
  snow_park.park_count
  snow_park.season_label
  night_skiing.availability
  night_skiing.season_label
  marked_freeride_routes.availability
  marked_freeride_routes.route_count
  marked_freeride_routes.season_label
  official_trail_map.url
  official_trail_map.season_label
  ski_day_apres_profile.availability
  ski_day_apres_profile.intensity
  ski_day_apres_profile.season_label

stay_base:
  elevation_m
  base_type
  base_character.development_style
  base_character.local_pace
  local_apres_profile.availability
  local_apres_profile.intensity
  local_apres_profile.season_label

terrain_domain:
  official_trail_map.url
  official_trail_map.season_label
```

Every unresolved path receives an entity-specific note. `unknown` and null are
retained when official research does not support a stronger value.

The acceptance commands for each worktree are:

```bash
PYTHONPATH="$PWD" /Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv/bin/python \
  -m app.data.validate_catalog

PYTHONPATH="$PWD" /Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv/bin/python \
  -m app.data.validate_catalog_curation typed \
  "$REPORT_PATH"

PYTHONPATH="$PWD" /Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv/bin/python \
  -m app.data.validate_catalog_curation reconcile \
  "$REPORT_PATH" \
  --base-catalog-path /Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/data/catalog.json \
  --current-catalog-path app/data/catalog.json \
  --base-trust-manifest-path /Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/data/resort_trust_manifest.json \
  --current-trust-manifest-path app/data/resort_trust_manifest.json \
  --markdown-output "${REPORT_PATH%.json}.md"

git diff --check
```

Before running the shared commands, set `REPORT_PATH` to the exact report path
listed in the active task's **Files** section.

### Task 1: Build The Campaign Report Helper

**Files:**
- Create locally, not committed: `.superpowers/build_catalog_v2_enrichment.py`
- Create locally, not committed: `.superpowers/v2_enrichment_remaining/`
- Reference: `app/data/catalog_curation.py`
- Reference: `app/data/catalog_curation_reconciliation.py`

- [ ] **Step 1: Extend the existing local enrichment helper contract**

  Make the helper accept `--config`, `--report`, `--base-catalog`,
  `--base-trust`, `--catalog`, and `--trust`. When `--report` does not exist,
  construct `CatalogCurationReport` from the config's `reviewed_paths`, exact
  `_derive_deltas(...)`, field evidence, unresolved notes, validation commands,
  and changed trust entries.

- [ ] **Step 2: Validate the helper with a no-write fixture in `/tmp`**

  Copy the canonical catalog and trust manifest to `/tmp`, apply a single
  reversible Alta Badia field fixture, and require model validation plus exact
  reconciliation to succeed. Delete the temporary fixture after the check.

- [ ] **Step 3: Keep campaign tooling out of Git**

  Run `git status --short` in the repository root and confirm `.superpowers/`
  does not appear.

### Task 2: Alta Badia

**Files:**
- Modify: `app/data/catalog.json` (`alta-badia-ski-area`, `alta-badia-corvara`)
- Modify: `app/data/resort_trust_manifest.json` (matching ski-area/base entries)
- Create: `docs/catalog-curation/2026-07-05-alta-badia-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-alta-badia-v2-enrichment.md`

- [ ] Research official Alta Badia ski-area and Corvara sources for every common-cycle path.
- [ ] Apply reviewed facts with `.superpowers/v2_enrichment_remaining/alta-badia.json`.
- [ ] Run catalog validation, typed validation, reconciliation, and `git diff --check` using the exact Alta Badia report path.
- [ ] Run the Snowcast catalog-review checklist and fix any defensible finding.
- [ ] Commit with `data: enrich Alta Badia catalog v2 facts`.
- [ ] Push `codex/catalog-curation-alta-badia-v2` and create a draft PR titled `Enrich Alta Badia catalog v2 facts` using the rendered report body.

### Task 3: Auronzo di Cadore

**Files:**
- Modify: `app/data/catalog.json` (`auronzo-monte-agudo`, `auronzo-di-cadore-auronzo-di-cadore`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-auronzo-di-cadore-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-auronzo-di-cadore-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-auronzo-di-cadore-v2` from commit `455ed412bc081bf85c016dfe35fa27e85697b74e` in an ignored worktree.
- [ ] Research official Monte Agudo and Auronzo sources for every common-cycle path without copying Cortina pass context.
- [ ] Apply `.superpowers/v2_enrichment_remaining/auronzo-di-cadore.json` and run the four acceptance commands with the exact Auronzo report path.
- [ ] Run local catalog review, commit `data: enrich Auronzo catalog v2 facts`, push, and open draft PR `Enrich Auronzo catalog v2 facts`.

### Task 4: Matterhorn Ski Paradise

**Files:**
- Modify: `app/data/catalog.json` (`cervinia-ski-area`, `zermatt-ski-area`, three owned stay bases, `matterhorn-ski-paradise`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-matterhorn-ski-paradise-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-matterhorn-ski-paradise-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-matterhorn-ski-paradise-v2` from the approved base commit.
- [ ] Research child-scoped Cervinia and Zermatt facts, both Cervinia stay bases, Zermatt stay base, and a genuinely aggregate domain map.
- [ ] Do not copy international-domain glacier or facility claims to a child area without child-scoped evidence.
- [ ] Apply `.superpowers/v2_enrichment_remaining/matterhorn-ski-paradise.json` and run exact validation/reconciliation for the Matterhorn report.
- [ ] Review, commit `data: enrich Matterhorn catalog v2 facts`, push, and open draft PR `Enrich Matterhorn Ski Paradise catalog v2 facts`.

### Task 5: Chamonix Mont-Blanc

**Files:**
- Modify: `app/data/catalog.json` (four Chamonix ski areas and three stay bases)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-chamonix-mont-blanc-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-chamonix-mont-blanc-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-chamonix-mont-blanc-v2` from the approved base commit.
- [ ] Research Balme, Brevent-Flegere, Grands Montets, and Les Houches independently; do not treat Mont-Blanc Unlimited as one connected domain.
- [ ] Research Argentiere, Chamonix, and Les Houches stay-base facts independently.
- [ ] Apply `.superpowers/v2_enrichment_remaining/chamonix-mont-blanc.json`, validate/reconcile, review, and commit `data: enrich Chamonix catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Chamonix Mont-Blanc catalog v2 facts`.

### Task 6: Cortina d'Ampezzo

**Files:**
- Modify: `app/data/catalog.json` (`cortina-dampezzo-ski-area`, `cortina-dampezzo-cortina-dampezzo`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-cortina-dampezzo-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-cortina-dampezzo-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-cortina-dampezzo-v2` from the approved base commit.
- [ ] Research Cortina child-area and town facts without copying Valle Skipass satellite-area features.
- [ ] Apply `.superpowers/v2_enrichment_remaining/cortina-dampezzo.json`, validate/reconcile, review, and commit `data: enrich Cortina catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Cortina d'Ampezzo catalog v2 facts`.

### Task 7: Campiglio Dolomiti di Brenta

**Files:**
- Modify: `app/data/catalog.json` (Folgarida-Marilleva, Madonna di Campiglio, and Pinzolo ski areas; six stay bases; `campiglio-dolomiti-di-brenta`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-campiglio-dolomiti-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-campiglio-dolomiti-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-campiglio-dolomiti-v2` from the approved base commit.
- [ ] Research each child ski area and stay base independently, plus the aggregate domain map.
- [ ] Keep domain totals and domain-wide facilities off child ski areas unless an exact child source supports them.
- [ ] Apply `.superpowers/v2_enrichment_remaining/campiglio-dolomiti.json`, validate/reconcile, review, and commit `data: enrich Campiglio catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Campiglio Dolomiti catalog v2 facts`.

### Task 8: Hintertux

**Files:**
- Modify: `app/data/catalog.json` (`hintertux-glacier`, `hintertux-hintertux`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-hintertux-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-hintertux-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-hintertux-v2` from the approved base commit.
- [ ] Research exact glacier-area and Hintertux village facts without copying Zillertal pass-wide facilities.
- [ ] Apply `.superpowers/v2_enrichment_remaining/hintertux.json`, validate/reconcile, review, and commit `data: enrich Hintertux catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Hintertux catalog v2 facts`.

### Task 9: Livigno

**Files:**
- Modify: `app/data/catalog.json` (`livigno-ski-area`, `livigno-livigno`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-livigno-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-livigno-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-livigno-v2` from the approved base commit.
- [ ] Research official Livigno area and town sources for every common-cycle path.
- [ ] Apply `.superpowers/v2_enrichment_remaining/livigno.json`, validate/reconcile, review, and commit `data: enrich Livigno catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Livigno catalog v2 facts`.

### Task 10: Misurina

**Files:**
- Modify: `app/data/catalog.json` (`misurina-passo-tre-croci`, `misurina-misurina`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-misurina-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-misurina-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-misurina-v2` from the approved base commit.
- [ ] Research Misurina child-area and settlement facts without copying Cortina regional-pass features.
- [ ] Apply `.superpowers/v2_enrichment_remaining/misurina.json`, validate/reconcile, review, and commit `data: enrich Misurina catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Misurina catalog v2 facts`.

### Task 11: San Vito di Cadore

**Files:**
- Modify: `app/data/catalog.json` (`san-vito-di-cadore-ski-area`, `san-vito-di-cadore-san-vito-di-cadore`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-san-vito-di-cadore-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-san-vito-di-cadore-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-san-vito-di-cadore-v2` from the approved base commit.
- [ ] Research San Vito child-area and village facts without copying Cortina regional-pass features.
- [ ] Apply `.superpowers/v2_enrichment_remaining/san-vito-di-cadore.json`, validate/reconcile, review, and commit `data: enrich San Vito catalog v2 facts`.
- [ ] Push and open draft PR `Enrich San Vito di Cadore catalog v2 facts`.

### Task 12: Tignes - Val d'Isere

**Files:**
- Modify: `app/data/catalog.json` (`tignes-ski-area`, `val-disere-ski-area`, eight stay bases, `tignes-val-disere`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-tignes-val-disere-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-tignes-val-disere-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-tignes-val-disere-v2` from the approved base commit.
- [ ] Research both child ski areas and all eight stay bases independently, plus the aggregate domain map.
- [ ] Apply `.superpowers/v2_enrichment_remaining/tignes-val-disere.json`, validate/reconcile, review, and commit `data: enrich Tignes Val d'Isere catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Tignes - Val d'Isere catalog v2 facts`.

### Task 13: Val Gardena

**Files:**
- Modify: `app/data/catalog.json` (`val-gardena-ski-area`, `val-gardena-ortisei`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-val-gardena-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-val-gardena-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-val-gardena-v2` from the approved base commit.
- [ ] Research Val Gardena and Ortisei facts at child scope; do not infer a new connected-domain owner during this narrow pass.
- [ ] Apply `.superpowers/v2_enrichment_remaining/val-gardena.json`, validate/reconcile, review, and commit `data: enrich Val Gardena catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Val Gardena catalog v2 facts`.

### Task 14: Zell am See-Kaprun

**Files:**
- Modify: `app/data/catalog.json` (`kitzsteinhorn`, `maiskogel`, `schmittenhoehe`, two stay bases, `kitzsteinhorn-maiskogel`)
- Modify: `app/data/resort_trust_manifest.json` (matching entries)
- Create: `docs/catalog-curation/2026-07-05-zell-am-see-kaprun-v2-enrichment.json`
- Create: `docs/catalog-curation/2026-07-05-zell-am-see-kaprun-v2-enrichment.md`

- [ ] Create `codex/catalog-curation-zell-am-see-kaprun-v2` from the approved base commit.
- [ ] Research the three ski areas, Kaprun and Zell am See bases, and the two-area aggregate map independently.
- [ ] Apply `.superpowers/v2_enrichment_remaining/zell-am-see-kaprun.json`, validate/reconcile, review, and commit `data: enrich Zell am See-Kaprun catalog v2 facts`.
- [ ] Push and open draft PR `Enrich Zell am See-Kaprun catalog v2 facts`.

### Task 15: Cross-PR Verification

**Files:**
- Inspect only: all 13 GitHub pull requests and their rendered reports

- [ ] Query all 13 PRs and assert they are drafts targeting `main` with distinct approved branch names.
- [ ] Assert the union of report-reviewed stay destinations equals the approved 17 IDs exactly once.
- [ ] Assert only the Matterhorn, Campiglio, Tignes-Val d'Isere, and Zell batches modify terrain-domain map facts.
- [ ] Assert every PR body contains source-aware field coverage and no generic version-2 migration boilerplate.
- [ ] Wait for every required CI check to reach a terminal state and report any non-success without claiming completion.
- [ ] Confirm the main worktree and pre-existing unrelated worktrees remain clean and unchanged.
