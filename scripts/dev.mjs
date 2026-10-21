// `make dev`: Firestore emulator + seed + agent-api + admin-api + mock-agent + widget + both storefronts + admin-web.
// Every child process is prefixed in the console; Ctrl+C stops everything.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { connect } from "node:net";

const LIVE_EVENTS = ".local/analytics/live-events.jsonl";
const env = {
  ...process.env,
  PYTHONUTF8: "1",
  FIRESTORE_EMULATOR_HOST: process.env.FIRESTORE_EMULATOR_HOST ?? "127.0.0.1:8085",
  FIRESTORE_PROJECT_ID: process.env.FIRESTORE_PROJECT_ID ?? "demo-magaza",
  LLM_MODE: process.env.LLM_MODE ?? "fake",
  DEV_AUTH_BYPASS: process.env.DEV_AUTH_BYPASS ?? "1",
  ANALYTICS_JSONL_PATH: LIVE_EVENTS,
  ANALYTICS_LIVE_JSONL: LIVE_EVENTS,
};
const children = [];
const COLORS = [31, 32, 33, 34, 35, 36, 91, 92, 93, 94];

function run(name, command, args, opts = {}) {
  const color = COLORS[children.length % COLORS.length];
  const child = spawn(command, args, { env, shell: process.platform === "win32", ...opts });
  const tag = `\x1b[${color}m[${name}]\x1b[0m `;
  for (const stream of [child.stdout, child.stderr]) {
    stream?.on("data", (buf) => {
      for (const line of buf.toString().split(/\r?\n/)) if (line.trim()) process.stdout.write(tag + line + "\n");
    });
  }
  child.on("exit", (code) => process.stdout.write(`${tag}exited (${code})\n`));
  children.push(child);
  return child;
}

function portOpen(port) {
  return new Promise((resolve) => {
    const socket = connect(port, "127.0.0.1");
    socket.once("connect", () => (socket.end(), resolve(true)));
    socket.once("error", () => resolve(false));
  });
}

async function waitFor(port, seconds = 90) {
  for (let i = 0; i < seconds; i++) {
    if (await portOpen(port)) return;
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`port ${port} did not open`);
}

function step(cmd, args) {
  const result = spawnSync(cmd, args, { env, stdio: "inherit", shell: process.platform === "win32" });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

process.on("SIGINT", () => {
  for (const child of children) child.kill();
  process.exit(0);
});

mkdirSync(".local/analytics", { recursive: true });
if (!existsSync("data/demo/manifest.json")) step("make", ["data"]);
if (!existsSync("data/analytics/fixture.duckdb")) step("make", ["fixture"]);
if (!existsSync("apps/demo-store/dist/ambalaj/index.html") || !existsSync("apps/widget/dist/widget.js")) step("make", ["build"]);

if (!(await portOpen(8085))) {
  run("emulator", "pnpm", ["exec", "firebase", "emulators:start", "--only", "firestore", "--project", env.FIRESTORE_PROJECT_ID]);
  await waitFor(8085);
}
step("uv", ["run", "--no-sync", "python", "-m", "magaza_jobs.seed", "--data", "data/demo"]);

// No --reload: uvicorn's reloader hangs on Windows; restart `make dev` after Python changes.
run("agent-api", "uv", ["run", "--no-sync", "uvicorn", "agent_api.main:app", "--port", "8080"]);
run("admin-api", "uv", ["run", "--no-sync", "uvicorn", "admin_api.main:app", "--port", "8090"]);
run("mock-agent", "node", ["apps/widget/mock-agent/server.mjs"]);
run("widget", "pnpm", ["--filter", "@magaza/widget", "exec", "vite", "build", "--watch"]);
run("widget-cdn", "node", ["apps/widget/scripts/serve-dist.mjs", "5174"]);
run("store-yapi", "node", ["apps/demo-store/scripts/serve.mjs", "apps/demo-store/dist/yapi-market", "3101"]);
run("store-ambalaj", "node", ["apps/demo-store/scripts/serve.mjs", "apps/demo-store/dist/ambalaj", "3102"]);
run("admin-web", "pnpm", ["--filter", "@magaza/admin-web", "exec", "vite", "--port", "5175", "--strictPort"]);

setTimeout(() => {
  console.log(`
  Yapıcı Market vitrini   http://localhost:3101        (gerçek agent: http://localhost:3101/?ma_api=http://localhost:8080)
  Kutu&Co Ambalaj vitrini http://localhost:3102        (gerçek agent: http://localhost:3102/?ma_api=http://localhost:8080)
  Yönetim paneli          http://localhost:5175        (geliştirici girişi)
  agent-api / admin-api   http://localhost:8080/healthz · http://localhost:8090/healthz
  mock-agent              http://localhost:8787/healthz
`);
}, 4000);
