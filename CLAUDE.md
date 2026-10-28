# Mağaza Asistanım — Proje Kuralları

Çok kiracılı (multi-tenant) B2B SaaS: e-ticaret sitelerine gömülen, sorunu anlayıp çözüm paketi öneren ve sepete ekleten yapay zeka asistanı. v1 = yalnızca "Dijital Paket" (web widget). Ayrıntılı görev tanımı: @docs/KICKOFF.md

## Mimari özeti
- `services/agent-api`: Google ADK (Python 3.12) + FastAPI, SSE ile sohbet. Tek servis tüm tenant'lara hizmet eder.
- `services/admin-api`: FastAPI; tenant yönetimi, dashboard sorguları, CSV/PDF export.
- `services/jobs`: feed-sync, doc-ingest, conversation-labeler, simulator (Cloud Run Jobs olarak çalışacak).
- `packages/core-py`: Pydantic modeller, tenant bağlamı, repo katmanı, olay şeması.
- `packages/contracts`: JSON Schema kaynakları → üretilen TS tipleri ve Pydantic modeller.
- `apps/widget` (Web Component), `apps/admin-web` (React+Vite), `apps/demo-store` (Next.js static export, iki tema).
- Veri: Firestore (yerelde emulator), BigQuery (yerelde DuckDB fixture), Cloud Storage. Bölge: europe-west1.

## Değişmez kurallar
- IMPORTANT: Firestore'a yalnızca `core-py` repo katmanı üzerinden erişilir. Her sorgu tenant yolu (`tenants/{tid}/...`) altında yapılır. `tenant_id` asla model çıktısından veya istemci girdisinden alınmaz; sunucunun doğruladığı bağlamdan gelir.
- Sektöre özel `if` dalı yazılmaz. Farklılık persona şablonuna veya tenant konfigürasyonuna gider.
- Yeni olay/mesaj tipi önce `packages/contracts`'a eklenir, sonra `make contracts` ile tipler üretilir.
- Agent cevabında yalnızca araçların o oturumda döndürdüğü SKU'lar geçebilir (grounding callback). Bu kuralı gevşeten değişiklik yapılmaz.
- Gemini model adları ve birim fiyatlar kodda sabit değil, konfigürasyondadır. Model ID'sini tahmin etme; Vertex AI dokümantasyonundan doğrula.
- IMPORTANT: Gerçek (ücretli) Gemini/Vertex çağrısı yapan komutları (`LLM_MODE=vertex`, `EMBEDDING_MODE=vertex`, gerçek-model eval/smoke) Claude kendi başına çalıştırmaz; komutu kullanıcıya verir, kullanıcı çalıştırıp çıktıyı paylaşır. `make check`/`make e2e` sahte modelde kalır. Toplam gerçek-model harcaması 5 $'ı geçmez: `config/llm.yaml → budget` ve harcama defteri (ADR 007) gevşetilmez, atlatılmaz; `make budget` durumu gösterir.
- Gerçek marka, logo, ürün fotoğrafı veya üretici adı kullanılmaz. Demo markaları kurgusaldır.
- Gizli bilgi (anahtar, token, service account JSON) repoya yazılmaz; `.env.local` git dışındadır.
- Kullanıcıya görünen metinler Türkçe, kod/değişken/commit mesajları İngilizce. Fiyat biçimi: `₺1.234,90`.

## Komutlar
- `make setup` — bağımlılıklar (uv, pnpm), Playwright tarayıcıları
- `make dev` — Firestore emulator + tüm servisler + uygulamalar
- `make check` — lint (ruff, eslint), tip kontrolü (mypy, tsc), birim testler (pytest, vitest)
- `make e2e` — Playwright uçtan uca testler; ekran görüntüleri `artifacts/screenshots/`
- `make eval` — `adk eval` altın setleri
- `make contracts` — JSON Schema'dan TS ve Pydantic üretimi

## Çalışma düzeni
- Depo: https://github.com/capslocksw/magaza-asistani (`origin`). Her iş `main`'den açılan kendi dalında (`feat/…`, `fix/…`, `docs/…`) yapılır; `main`'e doğrudan push yapılmaz.
- Her adım sonunda: `make check` geçer, `PROGRESS.md` güncellenir, git commit atılır (Conventional Commits), dal push edilip PR açılır. PR kullanıcı onayı olmadan birleştirilmez.
- İnsan kararı veya kimlik bilgisi gerektiren engelde: `docs/OPEN_QUESTIONS.md`'ye yaz, stub ile devam et, bekleme.
- Önemli mimari kararlar kısa ADR olarak `docs/adr/NNN-baslik.md`.
- Sıkıştırma (compaction) sırasında koru: tamamlanan kilometre taşları, değiştirilen dosyalar, test komutları, açık sorular.
