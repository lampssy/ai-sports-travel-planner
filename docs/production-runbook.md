# Production Runbook

## Required secrets

- Fly:
  - `FLY_API_TOKEN` for GitHub Actions deploys
- Fly runtime:
  - `DATABASE_URL` pointing to the Neon production database
  - `GEMINI_API_KEY`
  - optional `GEMINI_MODEL`
- GitHub Actions:
  - `DATABASE_URL` for the scheduled/manual refresh workflow

## Local setup

1. Start Postgres:
```bash
docker compose up -d postgres
```
2. Create local env:
```bash
cp .env.example .env
```
3. Install dependencies:
```bash
UV_CACHE_DIR=.uv-cache uv sync --dev --no-config
cd frontend && npm install && cd ..
```
4. Run tests:
```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest
```
5. Run the built app:
```bash
cd frontend && npm run build && cd ..
./scripts/run-built-app.sh
```

## Bootstrap and refresh

- Fly runs schema creation and seed sync through the release command before new web machines serve traffic.
- Manual bootstrap:
```bash
uv run python -m app.data.bootstrap_database --database-url "$DATABASE_URL"
```
- Manual refresh:
```bash
uv run python -m app.data.refresh_conditions --database-url "$DATABASE_URL"
```
- Force refresh:
```bash
uv run python -m app.data.refresh_conditions --database-url "$DATABASE_URL" --force
```

## Deploy flow

- CI runs on push and pull request.
- Production deploy runs from `.github/workflows/deploy.yml` on push to `main`.
- Fly deploy command:
```bash
flyctl deploy --remote-only --app snowcast
```
- The deploy runs the Fly release command first:
  - `python -m app.data.bootstrap_database --database-url "$DATABASE_URL"`

## Refresh process

- Conditions refresh is scheduled by GitHub Actions, not by a resident Fly worker.
- Scheduled cadence: every 6 hours.
- Manual operator runs happen through `workflow_dispatch` with:
  - optional `force=true`
  - optional comma-separated `resort_targets`
- Manual refresh command shape remains:
```bash
uv run python -m app.data.refresh_conditions --database-url "$DATABASE_URL" --force --resort tignes
```

## Smoke checks

- App root: `/`
- Health: `/api/healthz`
- Ready: `/api/readyz`
- Representative search:
```bash
curl -s "https://snowcast.fly.dev/api/search?location=France&min_price=150&max_price=320&stars=1&skill_level=intermediate"
```

## Failure inspection

- Fly app logs:
```bash
fly logs --app snowcast
```
- Process-specific machine status:
```bash
fly status --app snowcast
```
- If readiness fails, validate:
  - `DATABASE_URL`
  - Neon connectivity / credentials
  - release-command bootstrap success
- If freshness lags, inspect:
  - `.github/workflows/refresh-conditions.yml` run history
  - GitHub Actions `DATABASE_URL` secret
  - provider failures from `refresh_conditions`
