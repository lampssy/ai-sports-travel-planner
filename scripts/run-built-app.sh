#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to build the frontend." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required to run the backend." >&2
  exit 1
fi

cd "$ROOT_DIR/frontend"
npm run build

cd "$ROOT_DIR"
uv run --no-config python -m app.data.bootstrap_database
exec uv run --no-config uvicorn app.main:app "$@"
