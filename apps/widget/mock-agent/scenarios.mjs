// Scripted, contract-conformant agent used when no real AGENT_URL is configured.
// Uses the real demo catalogs (data/demo/<tenant>/catalog.json) so SKUs, prices and images are genuine.
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const FOLD = { ç: "c", ğ: "g", ı: "i", İ: "i", ö: "o", ş: "s", ü: "u" };
export const fold = (text) => text.toLocaleLowerCase("tr-TR").replace(/[çğıİöşü]/g, (c) => FOLD[c] ?? c);

/** Loads every tenant under data/demo, keyed by public key. */
export function loadTenants(dataDir) {
  const tenants = new Map();
  for (const id of ["yapi-market", "ambalaj"]) {
    const dir = join(dataDir, id);
    if (!existsSync(join(dir, "tenant.json"))) continue;
    const config = JSON.parse(readFileSync(join(dir, "tenant.json"), "utf8"));
    const catalog = JSON.parse(readFileSync(join(dir, "catalog.json"), "utf8"));
    tenants.set(config.public_key, { config, catalog, bySku: new Map(catalog.map((p) => [p.sku, p])) });
  }
  return tenants;
}

/** Deterministic holdout assignment; identical to magaza_core.tenancy.assign_group. */
export function assignGroup(tenantId, visitorId, holdoutPct) {
  const bucket = parseInt(createHash("sha256").update(`${tenantId}:${visitorId}`).digest("hex").slice(0, 8), 16) % 100;
  return bucket < holdoutPct ? "control" : "assistant";
}

export function widgetConfig(tenant, visitorId) {
  const c = tenant.config;
  return {
    display_name: c.display_name,
    assistant_name: c.persona.assistant_name,
    greeting: c.persona.greeting,
    suggested_questions: c.persona.suggested_questions,
    theme: c.theme,
    actions: c.actions,
    group: assignGroup(c.tenant_id, visitorId, c.holdout_pct),
  };
}

const card = (p, reason) => ({
  sku: p.sku,
  title: p.title,
  brand: p.brand,
  price: p.price,
  list_price: p.list_price ?? null,
  currency: "TRY",
  image_url: p.image_url,
  url: p.url,
  in_stock: p.stock > 0,
  reason: reason ?? null,
});

const RULES = {
  "yapi-market": [
    { match: /kornis|ayna|raf|matkab|matkap|duvara/, tag: "montaj-yapistiricisi", intro: "Matkap kullanmadan sabitlemek için montaj yapıştırıcısı en pratik çözüm.", title: "Matkapsız montaj paketi" },
    { match: /boya|badana|duvar|salon/, tag: "ic-cephe", intro: "Duvarları yenilemek için astar + boya + uygulama malzemeleri gerekir.", title: "Duvar boyama paketi" },
    { match: /derz|kuf|banyo/, tag: "derz", intro: "Kararmış derzleri önce temizleyip sonra yenilemek gerekir.", title: "Derz yenileme paketi" },
    { match: /musluk|damlat|sizdir/, tag: "musluk", intro: "Damlatan musluklarda genellikle conta değişimi yeterlidir.", title: "Musluk tamir paketi" },
  ],
  ambalaj: [
    { match: /teklif|toplu|aylik|adet|kurumsal/, tag: "cift-oluklu", intro: "Düzenli ve toplu gönderimler için size özel teklif hazırlayabiliriz.", title: "Toplu gönderim paketi", quote: true },
    { match: /kupa|seramik|cam|kirilacak|bardak|porselen/, tag: "cift-oluklu", intro: "Kırılacak ürünlerde çift oluklu (BC dalga) koli ve sarma malzemesi önerilir.", title: "Kırılacak ürün gönderim paketi" },
    { match: /palet|strec/, tag: "el-strec", intro: "Palet sarmak için el streç filmi ve aparatı yeterlidir.", title: "Palet sarma paketi" },
    { match: /koli|kutu|tekstil|kargo/, tag: "tek-oluklu", intro: "Hafif ürünler için tek oluklu koli ekonomik bir seçimdir.", title: "Kargo gönderim paketi" },
  ],
};

let counter = 0;
const nextId = (prefix) => `${prefix}_mock_${Date.now().toString(36)}${(counter++).toString(36)}`;

/** Returns the full ordered list of SSE events for one user message. */
export function buildScenario(tenant, message, sessionId) {
  const tenantId = tenant.config.tenant_id;
  const text = fold(message);
  const rule = (RULES[tenantId] ?? []).find((r) => r.match.test(text));
  const session = sessionId || nextId("s");
  const events = [];
  const say = (reply) => {
    for (const piece of reply.match(/\S+\s*/g) ?? []) events.push({ type: "token", text: piece });
  };

  if (!rule) {
    say(
      tenantId === "ambalaj"
        ? "Size doğru ambalajı önerebilmem için göndereceğiniz ürünün ağırlığını, yaklaşık ölçüsünü ve adedini yazar mısınız?"
        : "Size doğru malzemeyi önerebilmem için biraz daha ayrıntı verir misiniz? Hangi yüzeyde (beton, alçıpan, ahşap) ve ne tür bir iş yapacaksınız?",
    );
  } else {
    const main = tenant.catalog
      .filter((p) => p.tags.includes(rule.tag) && p.stock > 0)
      .sort((a, b) => Number(Boolean(b.doc_url)) - Number(Boolean(a.doc_url)) || (a.sales_rank ?? 1e9) - (b.sales_rank ?? 1e9))[0];
    const complements = (main?.complement_skus ?? []).map((sku) => tenant.bySku.get(sku)).filter((p) => p && p.stock > 0).slice(0, 3);
    if (!main) {
      say("Bu talep için katalogda uygun ürün bulamadım.");
    } else {
      const lines = [
        rule.intro,
        "",
        `**Önerim:**`,
        `- ${main.title} (${main.sku}) — ana ürün`,
        ...complements.map((c) => `- ${c.title} (${c.sku}) — tamamlayıcı`),
        "",
        "Paketi aşağıdan tek tıkla sepetinize ekleyebilirsiniz.",
      ];
      say(lines.join("\n"));
      if (main.doc_url) {
        events.push({ type: "source", sources: [{ doc_id: main.doc_id, title: `${main.title} — Teknik Föy`, url: main.doc_url, section: "Teknik Özellikler", snippet: null }] });
      }
      events.push({ type: "products", products: [card(main, "Ana ürün"), ...complements.map((c) => card(c, "Tamamlayıcı"))] });
      const items = [
        { sku: main.sku, title: main.title, price: main.price, qty: 1, role: "main", image_url: main.image_url, url: main.url, reason: null },
        ...complements.map((c) => ({ sku: c.sku, title: c.title, price: c.price, qty: 1, role: "complement", image_url: c.image_url, url: c.url, reason: null })),
      ];
      const total = Math.round(items.reduce((s, i) => s + i.price * i.qty, 0) * 100) / 100;
      events.push({ type: "bundle", bundle: { bundle_id: nextId("b"), title: rule.title, rationale: rule.intro, items, total, currency: "TRY" } });
      if (rule.quote && tenant.config.actions.quote_request) {
        events.push({ type: "action", action: "suggest_quote", label: "Teklif talebi oluştur", payload: {} });
      }
    }
  }
  events.push({
    type: "done",
    session_id: session,
    message_id: nextId("m"),
    usage: { model: "mock-agent", tokens_in: 0, tokens_out: 0, latency_ms: 0 },
  });
  return events;
}
