import { defineConfig, devices } from "@playwright/test";

// Local end-to-end setup. `make e2e` builds everything first and runs this under the Firestore emulator.
// E2E_SUITES (comma separated: store,widget,agent,admin) limits which servers start; default = all.
const suites = new Set((process.env.E2E_SUITES ?? "store,widget,agent,admin").split(","));
const PY = "uv run --no-sync";

type Server = NonNullable<Parameters<typeof defineConfig>[0]["webServer"]>;
const servers: Extract<Server, unknown[]> = [];

if (suites.has("store") || suites.has("widget") || suites.has("agent")) {
  servers.push(
    { command: "node apps/demo-store/scripts/serve.mjs apps/demo-store/dist/yapi-market 3101", url: "http://localhost:3101/", reuseExistingServer: true },
    { command: "node apps/demo-store/scripts/serve.mjs apps/demo-store/dist/ambalaj 3102", url: "http://localhost:3102/", reuseExistingServer: true },
  );
}
if (suites.has("widget") || suites.has("agent")) {
  servers.push(
    { command: "node apps/widget/scripts/serve-dist.mjs 5174", url: "http://localhost:5174/widget.js", reuseExistingServer: true },
    { command: "node apps/widget/mock-agent/server.mjs", url: "http://localhost:8787/healthz", reuseExistingServer: true },
  );
}
if (suites.has("agent")) {
  servers.push({
    command: `${PY} uvicorn agent_api.main:app --port 8080`,
    url: "http://localhost:8080/healthz",
    reuseExistingServer: true,
    env: { LLM_MODE: "fake", ANALYTICS_JSONL_PATH: ".local/analytics/e2e-events.jsonl" },
    timeout: 120_000,
  });
}
if (suites.has("admin")) {
  servers.push(
    {
      command: `${PY} uvicorn admin_api.main:app --port 8090`,
      url: "http://localhost:8090/healthz",
      reuseExistingServer: true,
      env: { DEV_AUTH_BYPASS: "1", ANALYTICS_BACKEND: "duckdb", ANALYTICS_DUCKDB_PATH: "data/analytics/fixture.duckdb" },
      timeout: 120_000,
    },
    { command: "pnpm --filter @magaza/admin-web exec vite preview --port 5175 --strictPort", url: "http://localhost:5175/", reuseExistingServer: true },
  );
}

export default defineConfig({
  testDir: "e2e",
  outputDir: "test-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: { locale: "tr-TR", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: servers,
});
