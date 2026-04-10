import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
  },
  webServer: {
    command:
      "cd .. && npm --prefix frontend run build && UV_CACHE_DIR=.uv-cache uv run --no-config uvicorn app.main:app --port 4173",
    url: "http://127.0.0.1:4173/api/healthz",
    reuseExistingServer: true,
    timeout: 120000,
  },
});
