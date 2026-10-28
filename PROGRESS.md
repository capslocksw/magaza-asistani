# PROGRESS — Gece 1 (yerel v1 iskeleti)

Kaynak görev: [docs/KICKOFF.md](docs/KICKOFF.md). Açık sorular: [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md). ADR'ler: [docs/adr/](docs/adr/).

| Taş | Durum | Kanıt (özet) |
| --- | --- | --- |
| M0 Repo iskeleti | ✅ | `make setup` → exit 0; `make check` → ruff/eslint/mypy/tsc temiz, pytest 4 passed, vitest 4 dosya passed |
| M1 Sözleşmeler | ✅ | `make contracts` 42 tip üretir; vitest 26 + pytest 38 sözleşme testi; tsc + mypy temiz |
| M2 Demo veri | ✅ | `make data` → yapi-market 329 SKU/40 föy, ambalaj 123 SKU/15 föy (PDF); veri doğrulama testi 26 passed |
| M3 Demo vitrin | ✅ | Playwright 8 passed (2 marka × masaüstü/mobil); Lighthouse a11y 95–100; ekran görüntüleri `artifacts/screenshots/m3/` |
| M4 Widget | ✅ | widget.js 8,4 KB gzip (<60 KB); vitest 14 passed; Playwright widget 8 passed (iki vitrin × masaüstü/mobil) |
| M5 Agent servisi | ✅ | pytest 102 passed (emulator: çapraz-tenant sızıntı, grounding, oturum servisi, CORS/teklif); Playwright widget→gerçek agent 4 passed; `make eval` 2×30 vaka PASS |
| M6 Yönetim paneli | ✅ | 90 günlük sentetik fixture (147.722 olay); admin-api pytest 7 passed; Playwright admin 6 passed (9 sayfa + CSV + PDF indirme); ekran görüntüleri `artifacts/screenshots/m6/` |
| M7 Kapanış | ✅ | README, ADR 001–006, OPEN_QUESTIONS, manuel test rehberi; alt ajan incelemesi (14 bulgu düzeltildi); son tur `make check` ve `make e2e` 0 ile çıktı |

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

## M3 — Demo vitrin ✅

- `apps/demo-store`: Next.js 15 static export + Tailwind 4 + shadcn tarzı bileşenler (Button/Badge/Sheet/Input, Radix Dialog). `BRAND=yapi-market|ambalaj` → iki ayrı build: `pnpm --filter @magaza/demo-store build:all` → `dist/yapi-market`, `dist/ambalaj`.
- Sayfalar: ana sayfa (hero, kampanya bantları, güven rozetleri, kategori vitrini, çok satanlar, fırsatlar), kategori listesi (alt kategori/marka/fiyat/stok filtresi, 5 sıralama, 24'lük sayfalama), arama (Türkçe karakter katlamalı istemci araması, sıfır sonuçta "asistana sor"), ürün detay (galeri, taksit/kargo/stok rozetleri, teknik özellik tablosu, föy PDF bağlantısı, "Birlikte iyi gider" tamamlayıcıları, benzer ürünler), sağdan açılan sepet (ücretsiz kargo ilerleme çubuğu), sahte ödeme (kart bilgisi alınmaz) + sipariş onayı (`MagazaAsistani.trackOrder(order)` çağırır), `feed.xml`.
- Tema: marka başına CSS değişkenleri (`--brand-strong` beyaz metinle AA kontrast), `₺1.234,90` biçimi `@magaza/contracts.formatTRY`.
- Widget gömme: tek `<script data-tenant="pk_..." data-api=...>`; vitrin `ma:add-to-cart` olayını dinleyip kendi sepetine ekler.
- Tasarım gözden geçirme sonrası düzeltmeler: ürün kartında görsel/başlık bağlantı çakışması, ambalaj için kahverengi yerine koyu petrol üst bar/altbilgi (`--chrome`), sepet rozetinin "Sepetim" yazısına binmesi, alt bilgi ve kampanya metni kontrastı, kategori sayfasında başlık sırası.
- Kanıt:
```
$ E2E_SUITES=store pnpm exec playwright test e2e/store.spec.ts → 8 passed (16.7s)
  [desktop|mobile] × [yapi-market|ambalaj]: gez → kategori/sırala → ara → ürün → sepete ekle → ödeme → onay
  + föy PDF bağlantısı (application/pdf) ve feed.xml (g: ad alanı)
Ekran görüntüleri: artifacts/screenshots/m3/{yapi-market,ambalaj}-0{1..7}-*-{desktop,mobile}.png
Lighthouse erişilebilirlik (lighthouse 12.8.2, Playwright Chromium): yapi-market / 96, /kategori/boya/ 98,
  /urun/YM-YAP-0001/ 100, /odeme/ 100; ambalaj / 96, /kategori/koli-cift-oluklu/ 95, /urun/KC-COK-0009/ 97
  (kalan kontrast/başlık uyarıları sonradan düzeltildi; JSON: artifacts/lighthouse/)
vitest apps/demo-store → 5 passed (arama, sıralama, filtre, fiyat yardımcıları)
```

## M4 — Widget ✅

- `apps/widget`: framework'süz Web Component `<magaza-asistani>` + Shadow DOM, Vite IIFE build → `dist/widget.js`. Gömme: `<script src=".../widget.js" data-tenant="pk_..." data-api="..." async>`.
- Başlatıcı buton, sohbet paneli (masaüstünde yan panel, ≤640px tam ekran), fetch+ReadableStream ile SSE akışlı yazım (`@magaza/contracts` `SseParser`), güvenli zengin metin (önce HTML kaçışı; kalın, liste, SKU çipi), ürün kartları ("Sepete ekle"), paket kartı ("Paketi sepete ekle"), "📄 föye göre" kaynak etiketleri, beğen/beğenme, teklif formu (yalnızca `actions.quote_request` açık tenant'ta; ambalaj), tenant temasından renk/logo/karşılama/önerilen sorular; tenant rengi beyaz metinle AA kontrastı tutmuyorsa otomatik koyulaştırılır.
- Vitrin entegrasyonu: `window` üzerinde `ma:add-to-cart` (`AddToCartDetail`) yayar, `ma:ready/ma:open/ma:close`; `window.MagazaAsistani.{open, close, trackOrder}`. Analitik istemci olayları: visit, widget_open, add_to_cart, feedback, order (`assisted`, `group` ile).
- Holdout: sunucu ziyaretçiyi deterministik olarak (`sha256(tenant:visitor) % 100 < holdout_pct`) kontrol grubuna atar; kontrol grubunda widget görünmez ama `visit` ve `order` izlenir.
- `mock-agent` (`apps/widget/mock-agent/server.mjs`): `AGENT_URL` yokken kullanılan, gerçek demo kataloğunu okuyan senaryolu ajan; agent-api ile aynı uçlar (`/v1/t/{pk}/config|chat|events|quotes`), sözleşmeye uygun SSE (ajv ile test edildi).
- Kanıt:
```
$ pnpm --filter @magaza/widget build → "widget.js: 23.8 KB raw, 8.4 KB gzip (limit 60 KB)"
$ vitest apps/widget → 14 passed (zengin metin/XSS kaçışı, kontrast, happy-dom'da tam tur: kartlar + paket → ma:add-to-cart,
  feedback, trackOrder assisted=true, kontrol grubunda gizli, hata mesajı; mock-agent olayları SseEvent şemasına uygun)
$ E2E_SUITES=widget pnpm exec playwright test e2e/widget.spec.ts → 8 passed
  iki vitrin × masaüstü/mobil: widget aç → mesaj → kartlar → paketi sepete ekle → vitrin sepet sayacı = paket kalemi sayısı
  → ödeme → sipariş mock-agent'a assisted=true ile ulaşır; ambalaj teklif formu; holdout ziyaretçide widget yok
Ekran görüntüleri: artifacts/screenshots/m4/
```

## M5 — Agent servisi ve işler ✅

- `services/agent-api` (FastAPI + Google ADK 2.12 `LlmAgent` + `Runner`):
  - Tenant çözümleme: public key (`/v1/t/{pk}/...`) + Origin izin listesi (preflight dahil); tenant bağlamı yalnızca sunucuda (ADR 004).
  - Persona talimatı `InstructionProvider` ile tenant konfigürasyonu + Firestore'daki persona şablonundan.
  - Araçlar (tenant'a bağlı kapanışlar): `search_products(query, category, brand, max_price, in_stock_only)` (Firestore `find_nearest` vektör araması + kategori ön filtresi + sözcüksel yeniden sıralama), `get_product`, `search_knowledge`, `get_complements` (kural gerekçeleriyle), `propose_bundle`, `create_quote_request` (yalnızca teklif açık tenant'ta), iç guardrail aracı `report_grounding_issue`.
  - `FirestoreSessionService` (`BaseSessionService`; `tenants/{tid}/sessions/{sid}/events`, app/user state).
  - Callback'ler: grounding (oturumda araçlardan dönmemiş SKU → bir kez yeniden yönlendirme, ikinci kez satır temizleme; ADR 005), kota/rate limit (ziyaretçi/dk, oturum mesajı, aylık mesaj sayacı) + döngü sınırı, PII maskeleme (telefon, e-posta, TC kimlik [checksum], kart [Luhn]) log/analitik öncesi.
  - Her adım `AnalyticsEvent` olarak yapılandırılmış JSON log (+ yerelde isteğe bağlı JSONL): user_message (konu etiketi), tool_call, agent_message (model, token, gecikme, tahmini maliyet, guardrail, "bilmiyorum", karşılanmayan talep), product_shown, quote_request; widget olayları (visit, widget_open, add_to_cart, order, feedback) `/events` ile.
  - `LLM_MODE=fake` → deterministik `FakeLlm` (aynı araç döngüsünü sürer); `LLM_MODE=vertex` → `gemini-3.8-flash` (ID ve fiyatlar `config/llm.yaml`, Google Cloud dokümanından doğrulandı).
- `services/jobs`: `feed_sync` (Merchant feed → Firestore + embedding, iş kaydı, `last_synced_at`), `doc_ingest` (PDF → pypdf → bölüm-farkında parçalar → embedding), `seed` (emulator'e iki tenant).
- Altın setler: `services/agent-api/evals/{yapi-market,ambalaj}.evalset.json` — ADK `EvalSet` formatında 30'ar vaka (paket / netleştirme / katalog dışı); `make eval` (bkz. OPEN_QUESTIONS #3).
- Kanıt:
```
$ make seed → {"ambalaj": {"products": 123, "doc_chunks": 92, "docs": 15, "rules": 14},
               "yapi-market": {"products": 329, "doc_chunks": 289, "docs": 40, "rules": 39}, "seconds": 6.2}
$ uv run pytest -q (emulator) → 102 passed
  services/agent-api/tests/test_tenant_isolation.py  çapraz-tenant: araçlar/oturum/HTTP; B'de A ürünü dönmez
  services/agent-api/tests/test_grounding.py         bilinmeyen SKU → report_grounding_issue → düzeltilmiş yanıt; 2. ihlal temizlenir
  services/agent-api/tests/test_chat_flow.py         KICKOFF örnekleri (montaj+tabanca+yüzey temizleyici; çift oluklu koli+balonlu+bant)
$ E2E_SUITES=agent pnpm exec playwright test e2e/agent.spec.ts → 4 passed (widget → gerçek agent-api, FakeLlm; ekran: artifacts/screenshots/m5/)
$ make eval (LLM_MODE=fake) → ambalaj-golden traj 1.0 / resp 0.611 PASS; yapi-market-golden traj 1.0 / resp 0.581 PASS
Gerçek Gemini ile uçtan uca test: bekliyor (OPEN_QUESTIONS #1).
```

## M6 — Yönetim paneli ✅

- `services/jobs/.../simulator.py` (`make fixture`): iki tenant için 90 günlük gerçekçi sentetik ziyaretçi yolculuğu (`is_synthetic=true`) → `data/analytics/fixture.duckdb` (`analytics_events`, AnalyticsEvent kolonları + JSON payload): holdout grubu, widget açma, çok turlu konuşmalar (yükselen konu), araç çağrıları, sıfır sonuç, katalog dışı/stok dışı talep, guardrail, paket önerisi, sepete ekleme, beğeni, teklif, asistanlı/asistansız sipariş.
- `services/admin-api`:
  - Firebase Auth ID token doğrulaması; `DEV_AUTH_BYPASS=1` yalnızca yerelde (Cloud Run'da `K_SERVICE` varken reddedilir). Tenant erişimi kullanıcının yetkili tenant'larıyla doğrulanır.
  - Tenant CRUD, persona şablonları, katalog senkron tetikleme (arka plan iş + durum), widget kodu, konuşma listesi/detayı.
  - `AnalyticsRepository`: `DuckDbAnalyticsRepository` (fixture + yerel canlı JSONL) ve `BigQueryAnalyticsRepository`; panolar tek bir SQL üreticisiyle iki lehçede (DuckDB/BigQuery) yazıldı.
  - 7 pano ucu (`/dashboards/{executive|funnel|demand|unmet|products|quality|usage}`), `/billing` (tenant/ay), 12 CSV veri seti (UTF-8 BOM, `,` veya `;` — `;` seçilince ondalık virgül), aylık PDF raporu (tenant logolu; WeasyPrint/Chromium, ADR 003).
- `apps/admin-web` (React 19 + Vite + Tailwind 4 + shadcn tarzı bileşenler + TanStack Query/Table + ECharts): giriş, tenant seçici, tarih aralığı (7/30/90 gün + özel), 7 pano, konuşma gezgini (detay çekmecesi), ayarlar (persona editörü, izinli domain'ler, widget kodu kopyalama, holdout % kaydırıcı, aksiyonlar, katalog senkronu), her tablo/grafikte "CSV indir", üst barda "Aylık raporu PDF indir".
- Kanıt:
```
$ make fixture → {"events": 147722, "by_tenant": {"ambalaj": 39466, "yapi-market": 108256}, "days": 90, "seconds": 2.4}
$ uv run pytest -q services/admin-api → 7 passed (7 pano DuckDB'de, BigQuery SQL lehçesi, HTTP + CSV BOM/`;` + PDF,
  erişim kontrolü [tenant_admin başka tenant'a 403], auth bypass Cloud Run'da kapalı)
$ E2E_SUITES=admin pnpm exec playwright test e2e/admin.spec.ts → 6 passed
  [desktop|mobile]: 9 sayfa açılır + ambalaj'a geçiş; CSV indir (BOM + başlık doğrulandı); aylık PDF indir (%PDF-); konuşma detayı
Ekran görüntüleri: artifacts/screenshots/m6/01..11-*-{desktop,mobile}.png (gözden geçirildi; rapor ayı seçicisi genişletildi)
```

## M7 — Kapanış ✅

- Belgeler: [README.md](README.md) (kurulum, `make dev`, mimari), [docs/MANUEL_TEST.md](docs/MANUEL_TEST.md) (10 manuel test senaryosu),
  ADR'ler `docs/adr/001..006`, [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md). `make dev` (`scripts/dev.mjs`) uçtan uca doğrulandı
  (tüm servisler ayakta, iki KICKOFF örneği doğru paketi döndürür, canlı sohbet yönetim panelinde görünür).
- Alt ajan, tüm diff'i KICKOFF/CLAUDE.md kabul kriterlerine göre gözden geçirdi; düzeltilen doğruluk/gereksinim açıkları:
  1. Sipariş onayında `trackOrder` iki kez sayılabiliyordu → tek seferlik koruma (vitrin + widget `order_id` tekilleştirme).
  2. `AGENT_URL` hiçbir yere bağlı değildi → vitrin (`NEXT_PUBLIC_AGENT_URL`) ve widget (`VITE_AGENT_URL`) build'ine eşlendi.
  3. Simülatörde model ID'si koddaydı → `config/llm.yaml`'dan okunuyor.
  4. Widget, tenant'ın `actions.add_to_cart` ayarını yok sayıyordu → kapalıysa sepet butonları gösterilmez.
  5. Çapraz satış kabul oranı paket olmayan önerileri de sayıyordu → yalnızca `bundle_id`'li olaylar.
  6. Grounding yalnızca tenant SKU desenini tarıyordu → her biçimdeki SKU benzeri kodlar da denetleniyor; paket başlığı/gerekçesi temizleniyor.
  7. Oturum mesaj kotasında widget çıkmaza giriyordu → oturum sıfırlanır, sunucu mesajı gösterilir.
  8. Persona şablonu önbelleği süresizdi → 30 sn TTL.
  9. Canlı JSONL olayları admin-api açıldıktan sonra oluşursa görünmüyordu → kaynak sorgu anında belirleniyor.
  10. Faturalama tablosunun CSV'si tek tenant veriyordu → `/api/export/faturalama.csv` (erişilen tüm tenant'lar).
  11. CLAUDE.md'deki `conversation-labeler` işi yoktu → `magaza_jobs.labeler` (+ test).
  12. Yönetim panelinde İngilizce durum/olay adları → Türkçe etiketler.
  13. Tenant silme alt koleksiyonları (oturum olayları) bırakıyordu → `recursive_delete`.
  14. Geçersiz ayda PDF 500 veriyordu → 422.
  Ayrıca `make dev`'de Windows'ta takılan uvicorn `--reload` kaldırıldı.
- Kanıt (son tur, tüm değişikliklerden sonra):
```
$ make check   → EXIT=0
  ruff: "All checks passed!" · eslint: temiz · mypy: "Success: no issues found in 55 source files" · tsc: 4 paket + e2e temiz
  pytest: "110 passed" (emulator dahil) · vitest: contracts 26, demo-store 5, admin-web 2, widget 16 passed
$ make e2e     → EXIT=0
  build: "widget.js: 24.1 KB raw, 8.5 KB gzip (limit 60 KB)", dist/yapi-market, dist/ambalaj, admin-web
  seed: {"ambalaj": {"products": 123, "doc_chunks": 105, ...}, "yapi-market": {"products": 329, "doc_chunks": 280, ...}}
  Playwright: "26 passed (1.4m)" — admin 6, agent 4, store 8, widget 8 (masaüstü + mobil)
```
- Kapsam dışı kaldı ve yapılmadı: deploy, Terraform, GCP kaynağı oluşturma, `git push`, gerçek ödeme, Imagen, rapor aboneliği gönderimi.

## Release 1 ✅

- Sürüm dokümanı: [docs/RELEASE_1.md](docs/RELEASE_1.md) (kapsam, 14 kapanış düzeltmesi, mimari/uyumluluk, test durumu, Release 2 yol haritası, riskler).
- Manuel test senaryoları TC-01 – TC-10 ([docs/MANUEL_TEST.md](docs/MANUEL_TEST.md)) kullanıcı tarafından yerelde yürütüldü ve başarılı raporlandı.
- Release 1 doğrulaması (commit `38489fe`): `make check` exit 0 (pytest 110/110, vitest 49/49), `make e2e` exit 0 (Playwright 26/26).

## Release 2 — Adım 1: Gerçek Gemini için harcama koruması ✅

Dal `feat/gemini-cost-guard` (PR ile `main`'e). Karar: gerçek Gemini ile ilerlenecek, toplam harcama 5 $'ı geçmeyecek,
gerçek-model testlerini yalnızca kullanıcı çalıştıracak. Bu adımda **hiçbir gerçek model çağrısı yapılmadı**.

- Sert sınır (ADR 007): `config/llm.yaml → budget` (`hard_cap_usd: 5.00`, `safety_margin_usd: 0.50`,
  `max_output_tokens: 4096`). `magaza_core.budget`: süreçler arası paylaşılan SQLite defteri
  (`.local/llm-spend.sqlite`), istek öncesi en kötü durum rezervasyonu, sınırı aşacak istek gönderilmez, yanıt sonrası
  `usage_metadata` ile kapanış; 4xx serbest bırakılır, belirsiz sonuç en kötü durumla kalır; fiyatı tanımsız model
  reddedilir; Cloud Run'da (paylaşılan defter yokken) başlamaz.
- Tek giriş noktaları: sohbet `agent_api.paid_llm.BudgetedGemini` (ADK `Gemini` alt sınıfı), embedding
  `VertexEmbedder`. `gemini-embedding-001` fiyatı yapılandırmaya eklendi (resmî fiyat sayfası, 2026-10-28).
- Açık onay: ücretli embedding artık yalnızca `EMBEDDING_MODE=vertex` ile (LLM_MODE açmaz); gerçek-model eval
  `--confirm-spend` + koşu sınırı `--run-cap-usd` (0,50 $) + `--limit N`; `make budget` durum gösterir; `make dev`
  ücretli modda açılışta harcamayı yazdırır.
- Testler asla harcamaz: `make check`/`make e2e` modları `fake`'e zorlar, pytest gerçek `google-genai` istemcisini
  engeller ve geçici defter kullanır, e2e yeniden kullandığı agent-api `fake` değilse durur.
- Sözleşme: SSE `error.code` için `budget_exceeded` (widget Türkçe mesaj gösterir).
- Belgeler: [docs/GEMINI_KURULUM.md](docs/GEMINI_KURULUM.md) (GCP bağlama, 5 $ GCP bütçe uyarısı, ilk tek-soru denemesi),
  [docs/adr/007-llm-spend-guard.md](docs/adr/007-llm-spend-guard.md), OPEN_QUESTIONS #1 güncellendi, #8 eklendi.
- Kanıt:
```
$ make check   → EXIT=0
  ruff: "All checks passed!" · mypy: "Success: no issues found in 57 source files" · eslint/tsc temiz
  pytest: "123 passed" (13 yeni: defter, eşzamanlı rezervasyon, koşu sınırı, Cloud Run reddi, embedder, BudgetedGemini,
          sohbette budget_exceeded) · vitest: contracts 26, demo-store 5, admin-web 2, widget 16 passed
$ make e2e     → EXIT=0
  "LLM_MODE=fake EMBEDDING_MODE=fake bash scripts/with-emulator.sh ..." · widget.js 8.5 KB gzip · Playwright "26 passed (1.2m)"
```

## Kalan işler
- Gerçek Gemini ile ilk tek-soru denemesi ve küçük eval — **kullanıcı çalıştırır** ([docs/GEMINI_KURULUM.md](docs/GEMINI_KURULUM.md), OPEN_QUESTIONS #1).
- Prod için paylaşılan harcama defteri ve tenant maliyet kotası (OPEN_QUESTIONS #8).
- Vertex embedding ile yeniden indeksleme ve "katalogda yok" benzerlik eşiğinin ayarı (OPEN_QUESTIONS #4).
- Yönetim paneli için Firebase Auth web yapılandırması ve rol/tenant claim süreci (OPEN_QUESTIONS #6).
- Prod analitik: Cloud Logging → BigQuery sink ve `BigQueryAnalyticsRepository`'nin gerçek tabloda doğrulanması (OPEN_QUESTIONS #7).
- Prod imajı: WeasyPrint için Pango/GTK paketleri (OPEN_QUESTIONS #5); Cloud Run servis/iş tanımları ve Terraform (bu gece kapsam dışı).
- `adk eval` CLI ile tam uyum için tenant'a özel eval agent modülü (OPEN_QUESTIONS #3).
