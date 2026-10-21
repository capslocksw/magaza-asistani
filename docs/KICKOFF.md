# Gece 1 Görev Tanımı — Yerel, uçtan uca çalışan v1 iskeleti

Bu dosya kendi başına yeterlidir. Amaç: sabaha kadar, **bulut kaynağı oluşturmadan**, yerelde uçtan uca çalışan bir v1 iskeleti: iki demo vitrin, gömülü widget, ADK agent servisi, yönetim paneli ve analitik. Her kilometre taşı (M0–M7) sırayla yapılır, kabul kriterleri kanıtıyla `PROGRESS.md`'ye işlenir.

## Ürün bağlamı
- Ürün: e-ticaret sitelerine tek `<script>` satırıyla gömülen danışman satış asistanı. Müşteri sorununu anlatır; asistan netleştirici soru sorar, katalog ve teknik föylere dayanarak çözüm paketi (ana ürün + tamamlayıcılar) önerir, tek tıkla sepete ekletir.
- Multi-tenant: tek kod tabanı, tenant başına konfigürasyon (persona şablonu, katalog kaynağı, açık aksiyonlar, tema, kotalar).
- İki kurgusal demo tenant:
  - `yapi-market` — "Yapıcı Market" (çalışma adı). Persona: Teknik Usta. Aksiyon: sepete ekle. Örnek: "Kornişim koptu, matkabım yok" → montaj yapıştırıcısı + silikon tabancası + yüzey temizleyici.
  - `ambalaj` — "Kutu&Co Ambalaj" (çalışma adı, B2B). Persona: Ambalaj Danışmanı. Aksiyonlar: sepete ekle + teklif talebi. Örnek: "2 kg seramik kupa göndereceğim, hangi koli?" → çift oluklu koli + balonlu naylon + koli bandı.

## Bu gece kapsam dışı
Terraform apply, herhangi bir deploy, GCP kaynağı oluşturma, `git push`, gerçek ödeme, Imagen ile görsel üretimi, rapor aboneliği gönderimi.

## Gemini kullanımı
- `GOOGLE_CLOUD_PROJECT` ve Application Default Credentials varsa gerçek Vertex AI çağrılabilir. Toplam bütçe bu gece için: en fazla ~300 model çağrısı (agent smoke testleri + küçük eval). Katalog üretimi LLM kullanmaz.
- Yoksa: agent testleri `FakeLlm`/kayıtlı yanıtlarla çalışır, gerçek model testleri `docs/OPEN_QUESTIONS.md`'ye "bekliyor" olarak yazılır.
- Varsayılan model Gemini 3.8 Flash; tam Vertex model ID'sini dokümantasyondan doğrula, konfigürasyona yaz. Embedding: Gemini embedding, 768 boyut. Testlerde deterministik sahte embedder.

## M0 — Repo iskeleti
- pnpm workspace (`apps/*`, `packages/contracts`) + uv workspace (`services/*`, `packages/core-py`), Makefile hedefleri (CLAUDE.md'deki komutlar), ruff/mypy/eslint/tsc/vitest/pytest yapılandırması, `.gitignore`, `.env.example`, Firestore emulator yapılandırması.
- Kabul: `make setup && make check` 0 ile çıkar.

## M1 — Sözleşmeler (contracts)
JSON Schema → TS + Pydantic: `TenantConfig`, `PersonaTemplate`, `Product`, `DocChunk`, `ChatRequest`, SSE olayları (`token`, `products`, `bundle`, `action`, `source`, `done`, `error`), `AnalyticsEvent` (`widget_open`, `user_message`, `agent_message`, `tool_call`, `product_shown`, `add_to_cart`, `quote_request`, `order`, `feedback`; alanlar: tenant_id, session_id, visitor_id_hash, ts, model, tokens_in, tokens_out, latency_ms, cost_usd_est, is_synthetic, payload), vitrin↔widget tarayıcı olayları (`ma:add-to-cart`, `MagazaAsistani.trackOrder(order)`).
- Kabul: `make contracts` üretir; üretilen tipler iki tarafta derlenir; şema testleri geçer.

## M2 — Demo veri
- Seed'li, deterministik üretici (LLM yok): `yapi-market` ≥ 300 SKU (boya, astar, yapıştırıcı/silikon, hırdavat, el aletleri, elektrikli aletler, banyo/tesisat), `ambalaj` ≥ 120 SKU (tek/çift oluklu koli ölçüleri, koli bandı, streç film, balonlu naylon, dolgu, etiket). Gerçekçi TL fiyatları, teknik özellikler (yapıştırıcı için taşıma kapasitesi, kuruma süresi, yüzey uyumu; koli için ölçü, dalga tipi, taşıma ağırlığı), stok, kategori, marka adları kurgusal.
- Tamamlayıcı ürün kuralları tablosu (ör. boya → astar, rulo, maskeleme bandı).
- Teknik föyler: `yapi-market` için ~40, `ambalaj` için ~15 ürün föyü; Markdown'dan PDF üret.
- Ürün görselleri: tutarlı stilde, kategori ikonlu SVG yer tutucular.
- Her tenant için Google Merchant formatında `feed.xml`.
- Kabul: veri doğrulama testi (şemaya uygunluk, SKU tekilliği, tamamlayıcı referansları geçerli).

## M3 — Demo vitrin (`apps/demo-store`)
- Next.js static export + Tailwind + shadcn/ui; `BRAND=yapi-market|ambalaj` ile iki tema ve iki ayrı build.
- Sayfalar: ana sayfa (hero, kampanya bantları, kategori vitrini, çok satanlar), kategori listesi (filtre, sıralama, sayfalama), arama sonuçları, ürün detay (galeri, teknik özellik tablosu, föy PDF bağlantısı, ilgili ürünler), sağdan açılan sepet, sahte ödeme + sipariş onayı (`trackOrder` çağırır), `feed.xml`.
- Kalite çıtası: Türkiye'nin önde gelen e-ticaret sitelerinin alışılmış kalıbı (yoğun kategori menüsü, belirgin arama, taksit/kargo rozetleri, `₺1.234,90`), ama özgün tasarım; gerçek marka öğesi yok. Mobil uyumlu. Lighthouse erişilebilirlik ≥ 90.
- Kabul: her iki marka için Playwright: gez → sepete ekle → ödeme → onay. Masaüstü ve mobil ekran görüntüleri `artifacts/screenshots/` altında; görüntülere bakıp tasarım kusurlarını düzelt.

## M4 — Widget (`apps/widget`)
- Web Component + Shadow DOM, Vite, `<script src=".../widget.js" data-tenant="pk_...">`. Başlatıcı buton, sohbet paneli, SSE akışlı yazım, ürün kartları ("Sepete ekle", "Paketi sepete ekle"), kaynak etiketi ("föye göre"), teklif talebi formu (yalnızca açık tenant'ta), tenant temasından renk/logo/karşılama/önerilen sorular, mobilde tam ekran, beğen/beğenme.
- `ma:add-to-cart` olayı yayar; vitrin dinleyip kendi sepetine ekler.
- `AGENT_URL` yoksa senaryolu yanıtlar veren `mock-agent` (sözleşmeye uygun SSE) ile çalışır.
- Kabul: gzip boyutu < 60 KB; Playwright: iki vitrinde widget aç → mesaj → kartlar → paketi sepete ekle → vitrin sepet sayacı artar.

## M5 — Agent servisi (`services/agent-api`) ve işler
- FastAPI + ADK `LlmAgent`; tenant çözümleme (public key + Origin izin listesi), persona talimatı `InstructionProvider` ile tenant konfigürasyonundan.
- Araçlar: `search_products(query, filters)` (Firestore vektör araması + ön filtre), `get_product(sku)`, `search_knowledge(query)`, `get_complements(sku)`, `propose_bundle(items, rationale)`, `create_quote_request(...)`.
- ADK `BaseSessionService` üzerine `FirestoreSessionService`.
- Callback'ler: grounding (cevaptaki her SKU oturumda araçlardan dönmüş olmalı; değilse bir kez yeniden yönlendir), kota/rate limit, kişisel veri maskeleme (telefon, e-posta, TC kimlik, kart no) log'a yazmadan önce.
- Her adımda `AnalyticsEvent` yapılandırılmış log olarak yazılır.
- İşler: `feed-sync` (feed.xml → Firestore + embedding), `doc-ingest` (PDF → parçalar → embedding).
- Altın setler: `services/agent-api/evals/` altında her tenant için 30 soru, ADK eval formatında.
- Kabul: emulator ile birim/entegrasyon testleri; **çapraz-tenant sızıntı testi** (A oturumundan B ürünü dönmez); grounding callback testi; widget gerçek agent'a bağlıyken bir uçtan uca senaryo (gerçek Gemini varsa) veya FakeLlm ile.

## M6 — Yönetim paneli (`apps/admin-web`, `services/admin-api`)
- admin-api: Firebase Auth doğrulaması (yalnızca yerelde `DEV_AUTH_BYPASS=1`), tenant CRUD, persona şablonları, katalog senkron tetikleme, konuşma listesi/detayı, dashboard uçları, CSV export (UTF-8 BOM; `,` veya `;`), aylık PDF rapor (WeasyPrint, tenant logolu).
- `AnalyticsRepository` arayüzü: BigQuery (prod) ve DuckDB fixture (yerel). Fixture: iki tenant için 90 günlük gerçekçi sentetik veri (`is_synthetic=true`).
- admin-web (React + Vite + shadcn/ui + TanStack Query/Table + ECharts): giriş, tenant seçici, tarih aralığı, şu 7 dashboard:
  1. Yönetici özeti: asistan destekli ciro, asistanlı vs. asistansız dönüşüm, AOV farkı, çapraz satış kabul oranı, haftalık trend
  2. Dönüşüm hunisi: widget açıldı → konuşma → ürün önerildi → sepete eklendi → sipariş
  3. Müşteri talepleri: sorun kategorileri, yükselen konular, örnek konuşmalar
  4. Karşılanmayan talep: katalogda olmayan istekler, stok dışı kayıp talep, sıfır sonuçlu aramalar
  5. Ürün ve paket performansı: en çok önerilenler, öneri→sepet→satış, birlikte önerilen ikililer
  6. Konuşma kalitesi: beğeni oranı, "bilmiyorum" oranı, terk, guardrail tetiklenmesi, konuşma gezgini
  7. Kullanım ve maliyet: konuşma, mesaj, token, tahmini maliyet (tenant/ay) — faturalama raporu
- Ayrıca: tenant ayarları (persona editörü, izinli domain'ler, widget kodu kopyalama), kontrol grubu (holdout %) ayarı, her tablo/grafikte "CSV indir", "Aylık raporu PDF indir".
- Kabul: Playwright her dashboard'u açar, bir CSV ve bir PDF indirir; ekran görüntüleri alınır ve gözden geçirilip düzeltilir.

## M7 — Kapanış
- `README.md` (kurulum, `make dev`, mimari özet), `PROGRESS.md` (kilometre taşı, kanıt, kalan işler), `docs/adr/` kayıtları, `docs/OPEN_QUESTIONS.md`.
- Bir subagent ile tüm diff'i bu dosyadaki kabul kriterlerine göre gözden geçir; yalnızca doğruluk ve gereksinim açıklarını düzelt.
- Kabul: `make check` ve `make e2e` 0 ile çıkar; çıktı özetleri transcript'e yazdırılır.

## Çalışma kuralları
- Sıra M0 → M7. Bir taşta takılırsan engeli `docs/OPEN_QUESTIONS.md`'ye yaz, stub ile geç, sonraki taşa devam et.
- Her taş sonunda: `make check`, `PROGRESS.md` güncelle, yerel commit. Push yok.
- Başarıyı iddia etme, kanıt göster: komut ve çıktı özeti, ekran görüntüsü yolu.
- Bağlam dolarsa sıkıştırmada PROGRESS.md ve bu dosyanın yolunu koru; devam ederken önce PROGRESS.md'yi oku.
