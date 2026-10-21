# PROGRESS — Gece 1 (yerel v1 iskeleti)

Kaynak görev: [docs/KICKOFF.md](docs/KICKOFF.md). Açık sorular: [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md). ADR'ler: [docs/adr/](docs/adr/).

| Taş | Durum | Kanıt (özet) |
| --- | --- | --- |
| M0 Repo iskeleti | ✅ | `make setup` → exit 0; `make check` → ruff/eslint/mypy/tsc temiz, pytest 4 passed, vitest 4 dosya passed |
| M1 Sözleşmeler | ✅ | `make contracts` 42 tip üretir; vitest 26 + pytest 38 sözleşme testi; tsc + mypy temiz |
| M2 Demo veri | ✅ | `make data` → yapi-market 329 SKU/40 föy, ambalaj 123 SKU/15 föy (PDF); veri doğrulama testi 26 passed |
| M3 Demo vitrin | ⏳ | |
| M4 Widget | ⏳ | |
| M5 Agent servisi | ⏳ | |
| M6 Yönetim paneli | ⏳ | |
| M7 Kapanış | ⏳ | |

## M0 — Repo iskeleti ✅

- pnpm workspace: `apps/*`, `packages/contracts`; uv workspace: `packages/core-py`, `services/*` (Python 3.12, tek `.venv`).
- Araçlar: ruff (lint+format), mypy (pydantic eklentisi), eslint 9 flat config + typescript-eslint, tsc 5.9, vitest 3, pytest + pytest-asyncio.
- Firestore emulator: `firebase.json` (127.0.0.1:8085, proje `demo-magaza` — `demo-` önekli proje yalnızca yerel), `firestore.rules` (istemci erişimi kapalı), `firestore.indexes.json` (768 boyutlu vektör indeksleri).
- `scripts/with-emulator.sh`: çalışan emulator varsa onu kullanır, yoksa `firebase emulators:exec` ile geçici açar. `make test` pytest'i bu sarmalayıcıyla çalıştırır.
- Ortam notu: makinede `make` yoktu; MSYS2 resmi deposundan GNU Make 4.4.1 `~/bin/make.exe` olarak kuruldu (bkz. OPEN_QUESTIONS).

Kanıt:
```
$ make setup   → ... "setup ok", EXIT=0
$ make check   → ruff check/format OK, eslint OK, mypy "Success", tsc 4 paket Done,
                 pytest "4 passed", vitest contracts/widget/admin-web/demo-store "1 passed" (her biri)
```

## M1 — Sözleşmeler ✅

- Şemalar: `packages/contracts/schemas/{common,tenant,catalog,chat,analytics,browser}.schema.json`
  - `TenantConfig`, `PersonaTemplate` (+ `PersonaSettings`, `TenantTheme`, `TenantActions`, `TenantQuotas`, `TopicDefinition`, `WidgetPublicConfig`)
  - `Product`, `ProductCard`, `ProductSpec`, `ComplementRule`, `DocChunk`
  - `ChatRequest`, SSE olayları `token|products|bundle|action|source|done|error` (`SseEvent` birleşimi), `QuoteRequest`, `ClientEvent`
  - `AnalyticsEvent` (widget_open, user_message, agent_message, tool_call, product_shown, add_to_cart, quote_request, order, feedback + `visit`; alanlar: tenant_id, session_id, visitor_id_hash, ts, model, tokens_in, tokens_out, latency_ms, cost_usd_est, is_synthetic, payload)
  - Tarayıcı: `ma:add-to-cart` (`AddToCartDetail`), `MagazaAsistani.trackOrder(order)` (`Order`)
- Üretim: `make contracts` → `packages/contracts/src/generated/contracts.ts` + `packages/core-py/src/magaza_core/contracts/generated.py` (ADR 002).
- Ortak yardımcılar: `formatTRY` / `format_try` (`₺1.234,90`), SSE kodlayıcı/ayrıştırıcı (TS + Python).

Kanıt:
```
$ make contracts → "contracts: 42 types -> packages/contracts/src/generated/contracts.ts, .../magaza_core/contracts/generated.py"
$ make check     → EXIT=0; "All checks passed!", mypy "Success: no issues found in 8 source files",
                   pytest "41 passed", vitest packages/contracts "26 passed" (geçerli/geçersiz örnekler, bundle senkron, formatTRY, SSE)
```

## M2 — Demo veri ✅

- Üretici: `services/jobs/src/magaza_jobs/demo_data/` (seed'li `random.Random`, LLM yok). `make data` → `data/demo/` (git dışı, her kurulumda yeniden üretilir).
  - `yapi-market` (Yapıcı Market): 329 SKU, 9 kategori (boya, astar, boya malzemeleri, yapıştırıcı/silikon, hırdavat, el aletleri, elektrikli aletler, banyo/tesisat, temizlik/yüzey hazırlık).
  - `ambalaj` (Kutu&Co Ambalaj): 123 SKU, 8 kategori (tek/çift oluklu koli ölçüleri, koli bandı, streç film, balonlu naylon, dolgu, etiket, zarf/poşet).
  - Teknik özellikler: yapıştırıcıda taşıma kapasitesi / ilk tutunma / kuruma süresi / yüzey uyumu; kolide iç ölçü, dalga tipi, taşıma ağırlığı, gramaj.
  - Gerçekçi TL raf fiyatları (`₺189,90`, `₺1.499,90`), %30 indirimli liste fiyatı, ~%7 stok dışı, puan/yorum, taksit, kargo.
  - Tamamlayıcı kural tablosu (`tenants.py` → `COMPLEMENT_RULES`, veri olarak) + çözümleyici (`complements.py`): ör. montaj yapıştırıcısı → silikon tabancası + yüzey temizleyici + maskeleme bandı; çift oluklu koli → balonlu naylon + hotmelt bant + kupa separatörü + kırılacak etiketi.
  - Teknik föyler: yapi-market 40, ambalaj 15; Markdown → HTML → PDF (ADR 003: WeasyPrint, Windows'ta Chromium yedeği).
  - Görseller: kategori ikonlu, tutarlı stilde SVG yer tutucular (ürün başına), kategori ikonları ve kurgusal logolar.
  - Google Merchant `feed.xml` (RSS 2.0 `g:` + ek alanlar için `ma:` ad alanı); `feed_format.parse_feed` ile geri okunur.
  - Kiracı konfigürasyonları + persona şablonları (Teknik Usta, Ambalaj Danışmanı) ve konu taksonomileri veri olarak.
- Kanıt:
```
$ make data
yapi-market: 329 products, 9 categories, 40 data sheets, 40 PDFs
ambalaj: 123 products, 8 categories, 15 data sheets, 15 PDFs
$ uv run pytest -q services/jobs   → 26 passed
  (şemaya uygunluk [jsonschema + pydantic], SKU tekilliği, tamamlayıcı referans bütünlüğü, kural hedefleri,
   föy sayıları, determinizm, feed gidiş-dönüş, gerçek marka yok, KICKOFF senaryoları, PDF render)
```

## Kalan işler
(her taş tamamlandıkça güncellenir)
