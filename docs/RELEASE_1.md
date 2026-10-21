# Release 1 — Mağaza Asistanım v1 (Dijital Paket) yerel iskeleti

- Sürüm: Release 1 (Gece 1 çıktısı, M0–M7)
- Tarih: 2026-10-22
- Kapsam: bulut kaynağı oluşturmadan, yerelde uçtan uca çalışan v1 — iki kurgusal demo vitrin, gömülü widget, ADK agent servisi, yönetim paneli ve analitik.
- İlgili belgeler: [README.md](../README.md) · [PROGRESS.md](../PROGRESS.md) · [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) · [MANUEL_TEST.md](MANUEL_TEST.md) · [adr/](adr/)

---

## Release 1 Kapsamı ve Yapılan Geliştirmeler

### Teslim edilen bileşenler

| Bileşen | Yol | Özet |
| --- | --- | --- |
| Sözleşmeler | `packages/contracts` | JSON Schema (Draft 2020-12) tek kaynak → `make contracts` ile TS tipleri + Pydantic v2 modeller (42 tip). SSE olayları (`token`, `products`, `bundle`, `action`, `source`, `done`, `error`), `AnalyticsEvent`, `TenantConfig`, `PersonaTemplate`, `Product`, `DocChunk`, tarayıcı olayları (`ma:add-to-cart`, `trackOrder`). |
| Core | `packages/core-py` | Tenant bağlamı, Firestore repo katmanı (tek erişim noktası), hashing/Vertex embedder, PII maskeleme, analitik yayıcı, HTML→PDF (WeasyPrint / Chromium yedeği), `config/llm.yaml` okuyucu. |
| Demo veri | `services/jobs/.../demo_data` | Seed'li, LLM'siz üretici: yapi-market 329 SKU / 40 föy, ambalaj 123 SKU / 15 föy (PDF), tamamlayıcı kural tabloları, SVG görseller, Google Merchant `feed.xml`. |
| Demo vitrin | `apps/demo-store` | Next.js 15 static export + Tailwind 4, iki marka/tema, kategori-arama-ürün-sepet-ödeme-onay akışı, Lighthouse erişilebilirlik 95–100. |
| Widget | `apps/widget` | Shadow DOM Web Component, SSE akışı, ürün/paket kartları, föy kaynağı, beğeni, teklif formu, mobilde tam ekran; **8,5 KB gzip**. Senaryolu `mock-agent`. |
| Agent servisi | `services/agent-api` | FastAPI + Google ADK 2.12 `LlmAgent`; tenant'a bağlı 6 araç + iç guardrail aracı; `FirestoreSessionService`; grounding, kota/rate limit, döngü sınırı callback'leri. |
| İşler | `services/jobs` | `feed_sync`, `doc_ingest`, `labeler` (conversation-labeler), `seed`, `simulator` (90 günlük sentetik analitik). |
| Yönetim | `services/admin-api`, `apps/admin-web` | Firebase Auth (yerelde bypass), tenant CRUD, persona şablonları, katalog senkronu, 7 pano, konuşma gezgini, CSV (BOM, `,`/`;`), aylık PDF rapor. |

### Kapanış incelemesinde yapılan 14 kritik düzeltme

Release öncesi, tüm diff bir alt ajan tarafından KICKOFF/CLAUDE.md kabul kriterlerine karşı incelendi; yalnızca doğruluk ve gereksinim açıkları düzeltildi. Her madde için regresyon testi eklendi veya mevcut test kapsamı doğrulandı.

1. **Sipariş tekilleştirme.** Sipariş onay sayfasında `MagazaAsistani.trackOrder` hem `ma:ready` dinleyicisi hem de yoklama döngüsü üzerinden tetiklenebiliyor, sayfa yenilemede tekrar gönderiliyordu → asistan destekli ciro, AOV ve dönüşüm şişiyordu.
   - Vitrin: tek seferlik koruma + `sessionStorage` bayrağı `ma-demo-tracked:{order_id}` (yenilemeye dayanıklı).
   - Widget: `order_id` bazlı `Set` ile ikinci savunma hattı (`apps/widget/src/main.ts`).
2. **AGENT_URL entegrasyonu.** `.env.example`'daki `AGENT_URL` hiçbir yere bağlı değildi. Vitrin build'inde `NEXT_PUBLIC_AGENT_URL`'e (`next.config.mjs`), widget build'inde `import.meta.env.VITE_AGENT_URL`'e (`vite.config.ts`) eşlendi; boşsa senaryolu mock-agent (`:8787`).
3. **`config/llm.yaml` ile dinamik model ID yönetimi.** Simülatörde model adı kodda sabitti (CLAUDE.md ihlali). Artık `load_llm_config().chat.default_model`; kodda hiçbir Gemini ID'si veya birim fiyatı yok. `gemini-3.8-flash` ID'si ve fiyatları Google Cloud dokümanından doğrulanıp yalnızca konfigürasyonda tutuluyor.
4. **Tenant bazlı sepet kuralları.** Widget, tenant'ın `actions.add_to_cart` ayarını yok sayıyordu. Ayar kapalıysa "Sepete ekle" ve "Paketi sepete ekle" butonları üretilmiyor (teklif aksiyonu zaten tenant'a bağlıydı).
5. **Çapraz satış metriği düzeltmesi.** Kabul oranı paydası "1'den fazla SKU içeren her `product_shown`" idi; gerçek agent paket olmayan yanıtlarda da çoklu SKU gösterdiği için oran yanlış düşüyordu. Pay ve payda artık yalnızca `payload.bundle_id IS NOT NULL` olaylar (DuckDB ve BigQuery lehçelerinde ortak SQL).
6. **Grounding / kod doğrulama.** Guardrail yalnızca tenant'ın `sku_pattern`'ini tarıyordu; küçük harfli veya farklı biçimli uydurma kodlar kaçabiliyordu. Ek olarak her biçimde SKU benzeri kodları yakalayan büyük-küçük harf duyarsız tarama (`SKU_LIKE`) eklendi; satır temizleme harf duyarsız; `propose_bundle` başlık/gerekçe metnindeki doğrulanmamış kodları siliyor. Test: `test_sku_in_other_shape_is_also_guarded`.
7. **Oturum kotasında çıkmaz.** `messages_per_session` dolunca widget aynı oturumla takılı kalıyordu. `quota_exceeded` olayında oturum kimliği temizleniyor ve sunucunun Türkçe mesajı gösteriliyor; sonraki mesaj yeni oturum açar.
8. **Persona şablonu önbelleği.** Agent tarafındaki şablon önbelleği süresizdi; admin'den yapılan düzenlemeler yeniden başlatmaya kadar uygulanmıyordu. Tenant önbelleğiyle aynı TTL (30 sn).
9. **Canlı analitik kaynağı.** admin-api, yerel canlı olay JSONL dosyasının varlığını yalnızca açılışta kontrol ediyordu; `make dev` sonrası yapılan sohbetler panolarda görünmüyordu. Kaynak artık her sorguda belirleniyor.
10. **Faturalama CSV'si.** "Faturalama: tenant / ay" tablosu tüm erişilen tenant'ları gösterirken CSV'si tek tenant veriyordu. Yeni uç: `GET /api/export/faturalama.csv` (kullanıcının erişebildiği tüm tenant'lar).
11. **Conversation-labeler servisi.** CLAUDE.md'de listelenen iş eksikti. `magaza_jobs.labeler`: kullanıcı mesajlarını her tenant'ın kendi konu taksonomisiyle (tenant verisi, sektör mantığı kodda değil) yeniden etiketler; JSONL üzerinde çalışır, prod'da BigQuery tablosu üzerinde koşacak şekilde tasarlandı.
12. **Admin panel yerelleştirmesi.** Senkron iş durumları (`queued/running/succeeded/failed`) ve konuşma gezginindeki ham olay adları Türkçe etiketlere çevrildi (CLAUDE.md: kullanıcıya görünen metinler Türkçe).
13. **Tenant silme temizliği.** Silme işlemi yalnızca bir seviye alt koleksiyonu siliyordu; `tenants/{tid}/sessions/*/events` (ham konuşma metni) yetim kalıyordu. Artık `AsyncClient.recursive_delete` ile tüm ağaç siliniyor (KVKK açısından önemli).
14. **422 hata yönetimi.** Aylık PDF raporunda geçersiz ay (ör. `2026-13`) 500 dönüyordu; artık `422 Geçersiz ay (YYYY-AA)`.

Ek düzeltmeler (manuel doğrulama sırasında): Windows'ta takılan uvicorn `--reload` `make dev`'den kaldırıldı; `make e2e` hedefinde build/veri sırası düzeltildi; oturum olayları yazım sırasına (`written_ns`) göre sıralanıyor (eşit zaman damgalarında sıralama bozuluyordu).

---

## Mimari ve Uyumluluk Standartları

### CLAUDE.md prensiplerine uyum

| Kural | Uygulama | Kanıt |
| --- | --- | --- |
| Firestore'a yalnızca core-py repo katmanı | `magaza_core.repo`; servisler yalnızca istemci nesnesini repolara geçirir | İnceleme raporu; `repo/__init__.py` |
| Her sorgu `tenants/{tid}/...` altında | `TenantScopedRepo` yolları kendisi üretir; hiçbir metot `tenant_id` parametresi almaz | ADR 004 |
| `tenant_id` model/istemci girdisinden alınmaz | Public key + Origin → `TenantContext`; tüm istek modelleri `extra="forbid"`, `ChatRequest`'te `tenant_id` yok (gönderilirse 422) | `test_client_cannot_choose_tenant` |
| Sektöre özel `if` yok | Persona şablonu, konu taksonomisi, tamamlayıcı kurallar, SKU deseni, aksiyonlar tenant verisidir | `services/agent-api` incelemesi |
| Yeni olay önce contracts | `visit` olay tipi önce şemaya eklendi, sonra üretildi | ADR 002 |
| Cevapta yalnızca araçların döndürdüğü SKU | Grounding callback (bir kez yönlendirme + temizleme) | ADR 005, `test_grounding.py` |
| Model ID ve fiyat konfigürasyonda | `config/llm.yaml` (kaynak bağlantılarıyla) | `test_llm_config_prices_and_ids` |
| Gerçek marka yok | Kurgusal markalar; gerçek marka kara listesi testi | `test_no_real_brands` |
| Gizli bilgi repoda yok | `.env.local`, servis hesabı JSON'ları git dışı | `.gitignore`, push öncesi tarama |
| Türkçe arayüz, `₺1.234,90` | `formatTRY` / `format_try` (ICU'dan bağımsız) | Sözleşme testleri |

### Deterministik AI davranışı

- `LLM_MODE=fake` (varsayılan): `FakeLlm`, gerçek ADK araç döngüsünü sürer (arama → tamamlayıcılar → paket → topraklanmış yanıt); ağ erişimi yok, sonuçlar tekrarlanabilir. Tüm birim/E2E testleri ve `make eval` bu modla deterministiktir.
- Embedding: yerelde 768 boyutlu deterministik hashing embedder (kelime + gövde + karakter 4-gram, işaretli özellik hash'leme); prod'da `gemini-embedding-001` (`output_dimensionality=768`).
- Demo veri ve analitik fixture seed'lidir; aynı komut aynı veriyi üretir (`test_generation_is_deterministic`).
- `LLM_MODE=vertex`: `gemini-3.8-flash`, `thinking_level: LOW` (model rehberi `temperature` yerine `thinking_level` öneriyor).

### Grounding mekanizması (ADR 005)

1. Araçlar döndürdükleri SKU'ları oturum durumuna (`grounded_skus`) yazar.
2. `after_model_callback` nihai yanıttaki kodları hem tenant `sku_pattern`'i hem genel `SKU_LIKE` ile bulur.
3. İlk ihlal: yanıt, `report_grounding_issue` iç araç çağrısına dönüştürülür; model izinli liste ile yanıtı yeniden yazar.
4. İkinci ihlal: bilinmeyen kod içeren satırlar çıkarılır; hiçbir şey kalmazsa güvenli geri dönüş metni.
5. `propose_bundle` / `create_quote_request` yalnızca topraklanmış ve stoktaki SKU'ları kabul eder.
6. Akış guardrail'den **sonra** başlar (`StreamingMode.NONE` + nihai metnin SSE `token` parçaları); doğrulanmamış ürün istemciye kısa süreliğine bile ulaşmaz.

### Tenant izolasyonu (ADR 004)

- Agent ve araçları her istekte, doğrulanmış bağlamla kurulmuş repolar üzerine yeniden oluşturulur (kapanışlar); model hangi argümanı üretirse üretsin başka tenant'ın yoluna erişemez.
- `FirestoreSessionService` tek tenant'a bağlıdır; başka tenant'ın oturum kimliği "yok" sayılır. Oturum ayrıca ziyaretçi hash'ine bağlıdır.
- CORS: tenant'ın `allowed_origins` listesi (preflight dahil); izinsiz origin → `403 origin_not_allowed`.
- Admin API: URL'deki tenant, kimliği doğrulanmış kullanıcının yetkili tenant listesiyle kontrol edilir; `DEV_AUTH_BYPASS` Cloud Run'da (`K_SERVICE`) devre dışıdır.
- Bilinçli istisnalar: public key çözümleme (bağlamı kuran işlem) ve tenant verisi içermeyen `persona_templates`.

### API kontratları

- Widget ↔ agent: `GET /v1/t/{pk}/config`, `POST /v1/t/{pk}/chat` (SSE), `POST /v1/t/{pk}/events`, `POST /v1/t/{pk}/quotes`. mock-agent aynı sözleşmeyi uygular (ajv ile doğrulanır).
- Vitrin ↔ widget: `window` üzerinde `ma:add-to-cart` (`AddToCartDetail`), `ma:ready/ma:open/ma:close`; `window.MagazaAsistani.{open, close, trackOrder}`.
- Analitik: `AnalyticsEvent` (tenant_id, session_id, visitor_id_hash, ts, model, tokens_in, tokens_out, latency_ms, cost_usd_est, is_synthetic, payload); PII log'a yazılmadan maskelenir.
- Admin: `/api/tenants/{tid}/dashboards/{executive|funnel|demand|unmet|products|quality|usage}`, `/conversations`, `/export/{dataset}.csv`, `/api/export/faturalama.csv`, `/reports/monthly.pdf`, `/catalog-sync`, `/widget-snippet`.
- Sözleşme senkronu: vitest, commit'li `bundle.schema.json`'un şemalardan yeniden üretilenle aynı olduğunu doğrular.

---

## Test ve Doğrulama Durumu

Son tur (tüm düzeltmelerden sonra, commit `38489fe` üzerinde):

### Statik analiz — `make check` (exit 0)

| Araç | Sonuç |
| --- | --- |
| ruff (lint + format) | `All checks passed!` |
| eslint (flat config, `--max-warnings=0`) | temiz |
| mypy (pydantic eklentisi) | `Success: no issues found in 55 source files` |
| tsc | contracts, widget, demo-store, admin-web, e2e — temiz |

### Birim ve entegrasyon testleri

| Paket | Sonuç | Öne çıkan kapsam |
| --- | --- | --- |
| pytest (Firestore emulator dahil) | **110 / 110** | çapraz-tenant sızıntı, grounding (yönlendirme, temizleme, farklı biçimli kod), FirestoreSessionService, CORS/teklif/olay API'si, kota ve rate limit, PII, 7 pano (DuckDB), BigQuery SQL lehçesi, CSV/PDF, erişim kontrolü, veri doğrulama, feed gidiş-dönüş, PDF bölümleme, labeler |
| vitest | **49 / 49** | contracts 26, widget 16, demo-store 5, admin-web 2 |

### Playwright E2E — `make e2e` (exit 0)

**26 / 26 passed (1,4 dk)**, masaüstü (1440×900) + mobil (Pixel 7):

| Suite | Test | Senaryo |
| --- | --- | --- |
| store | 8 | iki marka: gez → kategori/sırala → ara → ürün → sepet → ödeme → onay; föy PDF + `feed.xml` |
| widget (mock-agent) | 8 | aç → sor → kartlar → paketi sepete ekle → vitrin sayacı → sipariş `assisted=true`; ambalaj teklif formu; holdout ziyaretçide widget yok |
| agent (gerçek agent-api) | 4 | widget → ADK agent (FakeLlm + emulator) → topraklanmış paket → vitrin sepeti |
| admin | 6 | 9 sayfa + tenant değişimi; CSV (BOM) ve aylık PDF indirme; konuşma detayı |

Ek kanıtlar: Lighthouse erişilebilirlik 95–100 (vitrin), widget gzip 8,5 KB (< 60 KB), `make eval` 2 × 30 vaka PASS (FakeLlm), ekran görüntüleri `artifacts/screenshots/m3..m6/`.

### Manuel test senaryoları (TC-01 – TC-10)

Senaryolar [MANUEL_TEST.md](MANUEL_TEST.md)'de. Kullanıcı tarafından yerelde yürütüldü ve başarılı olarak raporlandı; her senaryonun otomatik karşılığı da yeşil:

| TC | Senaryo | Otomatik karşılık |
| --- | --- | --- |
| TC-01 | Vitrin alışverişi | `e2e/store.spec.ts` |
| TC-02 | Widget + gerçek agent (montaj paketi, ₺449,60) | `e2e/agent.spec.ts`, `test_chat_flow.py`, `make dev` API doğrulaması |
| TC-03 | Paketi sepete ekle (sayaç 4) | `e2e/agent.spec.ts` |
| TC-04 | Asistanlı sipariş | `e2e/widget.spec.ts` (`assisted=true`) |
| TC-05 | B2B teklif (yalnızca ambalaj) | `e2e/widget.spec.ts`, `test_api.py` |
| TC-06 | Kırılacak ürün paketi | `test_chat_flow.py`, `e2e/agent.spec.ts` |
| TC-07 | Konuşmanın yönetim panelinde görünmesi | `e2e/admin.spec.ts`, `make dev` canlı JSONL doğrulaması |
| TC-08 | Panolar, CSV, PDF | `e2e/admin.spec.ts`, `test_admin_api.py` |
| TC-09 | Holdout (kontrol grubu) | `e2e/widget.spec.ts`, `test_api.py` |
| TC-10 | İzinsiz origin → 403 | `test_api.py`, `test_tenant_isolation.py` |

### Bilinen doğrulama boşlukları

- Gerçek Gemini (`LLM_MODE=vertex`) ile hiçbir test koşmadı (GCP projesi kararı bekliyor; OPEN_QUESTIONS #1).
- BigQuery lehçesi yalnızca SQL üretimi düzeyinde test edildi.
- WeasyPrint yolu Windows'ta denenmedi (Chromium yedeği kullanıldı).

---

## Release 2 Yol Haritası (Planned Features)

Planlanan işlerdir; öncelik ve kapsam ürün kararıyla netleşecektir.

### Gerçek model ve kalite
- Vertex AI üzerinde `gemini-3.8-flash` ile agent smoke testleri, altın setlerin gerçek modelle koşulması ve eşiklerin kalibrasyonu.
- `gemini-embedding-001` ile katalog ve föylerin yeniden indekslenmesi; "katalogda yok" için benzerlik eşiğinin gerçek trafikle ayarlanması.
- `adk eval` / Vertex AI Gen AI Evaluation Service ile tam uyum için tenant'a özel eval agent modülleri; LLM-as-judge rubrikleri.
- Artımlı grounding ile kısmi token akışı (ilk token gecikmesini düşürmek, doğrulamayı cümle bazında yapmak).

### Altyapı ve dağıtım
- Terraform ile GCP kaynakları (europe-west1): Cloud Run servisleri (agent-api, admin-api), Cloud Run Jobs (feed-sync, doc-ingest, labeler), Firestore vektör indeksleri, Cloud Storage, Secret Manager.
- Cloud Logging → BigQuery log sink'i ve `BigQueryAnalyticsRepository`'nin gerçek tabloda doğrulanması; labeler'ın BigQuery etiket tablosuna yazması.
- WeasyPrint'li (Pango/GTK) prod imajı; CI (GitHub Actions) ile `make check` + `make e2e`.
- Widget'ın CDN üzerinden sürümlü dağıtımı (cache-busting, SRI).

### Kimlik, güvenlik ve uyum
- Firebase Auth web entegrasyonu, rol/tenant custom claim yönetimi, admin RBAC ve denetim kaydı.
- Firestore oturum verileri için saklama süresi (TTL) ve KVKK uyumlu silme/dışa aktarma; prod'da `VISITOR_HASH_SALT` Secret Manager'dan.
- Dağıtık rate limit (instance başına değil, merkezi), parçalı (sharded) kullanım sayaçları.

### Ürün ve ölçeklenebilirlik
- Platform eklentileri (ör. yaygın e-ticaret altyapıları için tek tık kurulum) ve sepet/stok için gerçek vitrin API entegrasyonları.
- Holdout deneyleri için istatistiksel anlamlılık hesabı ve deney yönetimi.
- Rapor aboneliği (aylık PDF'in e-postayla gönderimi), Imagen ile ürün görseli üretimi (Release 1'de kapsam dışıydı).
- Çok sayıda tenant için katalog senkronunda artımlı güncelleme ve iş kuyruğu.

---

## Dikkat Edilmesi Gerekenler ve Riskler (Gotchas)

### Production'a geçiş
- **Embedder değişimi:** Yerel veri hashing embedder ile indekslidir. Prod'da Vertex embedder'a geçmeden önce tüm ürün ve föyler yeniden embed edilmeli; iki embedder'ın vektörleri karıştırılırsa arama anlamsızlaşır.
- **Vektör indeksleri:** `firestore.indexes.json`'daki 768 boyutlu vektör indeksleri (kategori ön filtreli bileşik indeks dahil) prod'a dağıtılmadan `find_nearest` sorguları hata verir.
- **Ziyaretçi hash tuzu:** `VISITOR_HASH_SALT` ayarlanmazsa varsayılan `local-dev-salt` kullanılır; prod'da mutlaka gizli bir değer verilmeli (aksi halde ziyaretçi hash'leri tahmin edilebilir).
- **Auth bypass:** `DEV_AUTH_BYPASS=1` yalnızca yerelde çalışır (Cloud Run'da `K_SERVICE` varken yok sayılır); yine de prod ortam değişkenlerinde bulunmamalı.
- **CORS:** `allowed_origins` birebir eşleşir; `www` ve çıplak alan adı, `http`/`https`, port ayrı ayrı eklenmeli.
- **PDF:** WeasyPrint için imajda Pango/GTK paketleri gerekir; yoksa Chromium yedeğine düşer (prod'da Chromium imaj boyutunu büyütür).

### Emulator ve yerel ortam bağımlılıkları
- `make check` ve `make e2e` Firestore emulator ister (Java 21). Çalışan emulator (`127.0.0.1:8085`) varsa yeniden kullanılır, yoksa `firebase emulators:exec` ile geçici açılır.
- `seed`, `FIRESTORE_EMULATOR_HOST` yoksa gerçek Firestore'a yazmayı reddeder (`SEED_ALLOW_REAL_FIRESTORE=1` ile bilinçli olarak açılmalı).
- Testler `demo-test-*` gibi `demo-` önekli proje kimlikleri kullanır; bunlar buluta bağlanmaz.
- Windows: uvicorn `--reload` takıldığı için `make dev` yeniden yüklemesiz çalışır (Python değişikliğinde yeniden başlatın); Git Bash'te curl Türkçe karakterli gövdeyi UTF-8 göndermeyebilir.
- `make e2e`, çalışan `make dev` sunucularını yeniden kullanır (`reuseExistingServer`); eski build'lere karşı test etmemek için gerekirse `make dev`'i durdurun.

### Token limitleri ve maliyet
- `gemini-3.8-flash`: 1.048.576 token bağlam, 65.536 token azami çıktı (Google Cloud dokümanı). Bizim tarafta tur başına model çağrısı `max_llm_calls_per_turn: 10` ile sınırlı.
- Oturum geçmişi her turda bağlama girer; uzun sohbetlerde girdi token'ı (ve maliyet) büyür. Release 2'de geçmiş özetleme / `num_recent_events` sınırı değerlendirilmeli.
- Fiyatlar: tanıtım fiyatı 2026-12-31'e kadar ($0,825 / $4,125 per 1M token, bölgesel); 2027-01-01'den itibaren standart fiyat (`config/llm.yaml`'da iki dönem de tanımlı). `cost_usd_est` tahmindir; faturalama için GCP faturası esas alınmalı.

### Rate limit ve kota senaryoları
- Ziyaretçi başına dakika sınırı **instance içi** (bellek) tutulur; Cloud Run'da birden fazla instance varsa etkin sınır instance sayısıyla çarpılır. Merkezi bir sınırlayıcı Release 2 işidir.
- Aylık mesaj sayacı tenant başına tek Firestore dokümanında `Increment` ile tutulur; Firestore'un tek doküman için sürdürülebilir yazma hızı sınırlıdır (~1 yazma/sn). Yüksek trafikte sayaç parçalanmalı (sharded counter).
- `messages_per_session` dolduğunda widget oturumu sıfırlar ve sunucu mesajını gösterir; `rate_limited` durumunda kullanıcı birkaç saniye beklemelidir.
- Holdout yüzdesi değiştirildiğinde ziyaretçilerin bir kısmı gruplar arasında yer değiştirir (atama deterministik ama eşik değişir); deney süresince sabit tutulmalı.

### Veri ve gizlilik
- Firestore oturum olaylarında ham konuşma metni tutulur (teklif için e-posta/telefon gerekebileceğinden); log ve analitikte PII maskelenir. Prod öncesi saklama süresi (TTL) ve silme süreçleri tanımlanmalı.
- Analitik fixture tamamen sentetiktir (`is_synthetic=true`); prod panolarında sentetik verinin karışmaması için filtre korunmalı.
