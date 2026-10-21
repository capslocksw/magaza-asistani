// Serves the built widget (dist/widget.js) plus a bare test page: node scripts/serve-dist.mjs [port]
import { createReadStream, existsSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const port = Number(process.argv[2] ?? 5174);

const page = (key, api) => `<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Widget test sayfası</title></head>
<body style="font-family: system-ui; padding: 24px">
<h1>Mağaza Asistanım — widget test sayfası</h1>
<p>Sepet sayacı: <strong id="count">0</strong></p>
<script>
  window.addEventListener("ma:add-to-cart", (e) => {
    const el = document.getElementById("count");
    el.textContent = String(Number(el.textContent) + e.detail.items.reduce((s, i) => s + i.qty, 0));
  });
</script>
<script src="/widget.js" data-tenant="${key}" data-api="${api}" async></script>
</body></html>`;

createServer((req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host}`);
  if (url.pathname === "/widget.js") {
    const file = join(root, "dist", "widget.js");
    if (!existsSync(file)) return res.writeHead(404).end("run `pnpm --filter @magaza/widget build` first");
    res.writeHead(200, { "content-type": "text/javascript; charset=utf-8", "access-control-allow-origin": "*", "cache-control": "no-cache" });
    return createReadStream(file).pipe(res);
  }
  if (url.pathname === "/") {
    const key = (url.searchParams.get("key") ?? "pk_test_yapimarket").replace(/[^a-z0-9_]/gi, "");
    const api = (url.searchParams.get("api") ?? "http://localhost:8787").replace(/[^a-z0-9:/._-]/gi, "");
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    return res.end(page(key, api));
  }
  res.writeHead(404).end();
}).listen(port, () => console.log(`widget served on http://localhost:${port}/widget.js`));
