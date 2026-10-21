// Scripted mock agent (no LLM, no Firestore): node mock-agent/server.mjs [port]
// Implements the same HTTP + SSE contract as services/agent-api so the widget can be developed standalone.
import { createServer } from "node:http";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildScenario, loadTenants, widgetConfig } from "./scenarios.mjs";

const port = Number(process.argv[2] ?? process.env.MOCK_AGENT_PORT ?? 8787);
const dataDir = resolve(dirname(fileURLToPath(import.meta.url)), "../../../data/demo");
const tenants = loadTenants(dataDir);
const events = []; // received client events, exposed at GET /__events for tests

function cors(req, res) {
  res.setHeader("access-control-allow-origin", req.headers.origin ?? "*");
  res.setHeader("access-control-allow-methods", "GET, POST, OPTIONS");
  res.setHeader("access-control-allow-headers", "content-type, accept");
  res.setHeader("vary", "Origin");
}

function json(res, status, body) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body));
}

async function readBody(req) {
  let raw = "";
  for await (const chunk of req) raw += chunk;
  try {
    return JSON.parse(raw || "{}");
  } catch {
    return null;
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

createServer(async (req, res) => {
  cors(req, res);
  const url = new URL(req.url ?? "/", `http://${req.headers.host}`);
  if (req.method === "OPTIONS") return res.writeHead(204).end();
  if (url.pathname === "/healthz") return json(res, 200, { ok: true, tenants: tenants.size });
  if (url.pathname === "/__events") return json(res, 200, events);

  const match = /^\/v1\/t\/([^/]+)\/(config|chat|events|quotes)$/.exec(url.pathname);
  const tenant = match ? tenants.get(decodeURIComponent(match[1])) : undefined;
  if (!match) return json(res, 404, { error: "not_found" });
  if (!tenant) return json(res, 404, { type: "error", code: "unknown_tenant", message: "Bilinmeyen anahtar" });

  switch (match[2]) {
    case "config":
      return json(res, 200, widgetConfig(tenant, url.searchParams.get("visitor_id") ?? "anon"));
    case "events": {
      const body = await readBody(req);
      if (body) events.push({ ...body, tenant_id: tenant.config.tenant_id, received_at: new Date().toISOString() });
      return json(res, 202, { ok: true });
    }
    case "quotes": {
      const body = await readBody(req);
      if (!body?.items?.length || !body.email) return json(res, 422, { error: "invalid_request" });
      return json(res, 200, { quote_id: `Q-MOCK-${Date.now().toString(36).toUpperCase()}`, status: "received" });
    }
    case "chat": {
      const body = await readBody(req);
      if (!body?.message) return json(res, 422, { type: "error", code: "invalid_request", message: "message gerekli" });
      res.writeHead(200, { "content-type": "text/event-stream; charset=utf-8", "cache-control": "no-cache", connection: "keep-alive" });
      for (const event of buildScenario(tenant, body.message, body.session_id)) {
        res.write(`event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`);
        await sleep(event.type === "token" ? 12 : 40);
      }
      return res.end();
    }
  }
}).listen(port, () => console.log(`mock-agent listening on http://localhost:${port} (${tenants.size} tenants)`));
