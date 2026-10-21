# Mağaza Asistanım

E-ticaret sitelerine tek `<script>` satırıyla gömülen, müşterinin sorununu anlayıp katalog ve teknik föylere dayanarak
**çözüm paketi** (ana ürün + tamamlayıcılar) öneren ve tek tıkla sepete ekleten çok kiracılı (multi-tenant) yapay zeka asistanı.

Bu repo, bulut kaynağı oluşturmadan yerelde uçtan uca çalışan v1 iskeletidir: iki kurgusal demo vitrin, gömülü widget,
Google ADK tabanlı agent servisi, yönetim paneli ve analitik. İlerleme ve kanıtlar: [PROGRESS.md](PROGRESS.md) ·
açık sorular: [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) · mimari kararlar: [docs/adr/](docs/adr/).

## Hızlı başlangıç

Önkoşullar: Node 22+, pnpm 10, [uv](https://docs.astral.sh/uv/), Java 21 (Firestore emulator), GNU Make, Git Bash (Windows).

```bash
make setup   # uv + pnpm bağımlılıkları, Playwright tarayıcıları, Firestore emulator, demo veri + analitik fixture
make dev     # emulator + seed + tüm servisler ve uygulamalar
```

| Uygulama | Adres |
| --- | --- |
| Yapıcı Market vitrini (yapı market) | http://localhost:3101 |
| Kutu&Co Ambalaj vitrini (B2B ambalaj) | http://localhost:3102 |
| Yönetim paneli (geliştirici girişi) | http://localhost:5175 |
| agent-api (ADK + FastAPI, SSE) | http://localhost:8080 |
| admin-api | http://localhost:8090 |
| mock-agent (senaryolu, `AGENT_URL` yokken) | http://localhost:8787 |
| widget.js | http://localhost:5174/widget.js |
| Firestore emulator | 127.0.0.1:8085 |

Vitrinler varsayılan olarak mock-agent'a bağlanır; gerçek agent-api için adrese `?ma_api=http://localhost:8080` ekleyin
(sekme boyunca hatırlanır). Örnek sorular: “Kornişim koptu, matkabım yok”, “2 kg seramik kupa göndereceğim, hangi koli?”.
Adım adım manuel test senaryoları: [docs/MANUEL_TEST.md](docs/MANUEL_TEST.md).

## Komutlar

| Komut | Ne yapar |
| --- | --- |
| `make setup` | bağımlılıklar (uv, pnpm), Playwright tarayıcıları, emulator jar, `make data fixture` |
| `make dev` | Firestore emulator + seed + tüm servisler + uygulamalar (`scripts/dev.mjs`) |
| `make check` | ruff (lint+format), eslint, mypy, tsc, pytest (emulator altında), vitest |
| `make e2e` | build + seed + Playwright (vitrin, widget, gerçek agent, yönetim paneli); ekran görüntüleri `artifacts/screenshots/` |
| `make eval` | altın setler (`services/agent-api/evals/*.evalset.json`, ADK EvalSet formatı) |
| `make contracts` | JSON Schema → TS tipleri + Pydantic modeller |
| `make data` / `make fixture` / `make seed` | demo katalog+föy+feed / 90 günlük analitik fixture / emulator'e yükleme |

`LLM_MODE=fake` (varsayılan) deterministik `FakeLlm` kullanır. Gerçek Gemini için `LLM_MODE=vertex`, `GOOGLE_CLOUD_PROJECT`
ve Application Default Credentials gerekir; model ID'si ve birim fiyatlar `config/llm.yaml`'dadır (kodda sabit değil).

## Mimari

```
apps/
  demo-store/   Next.js static export, BRAND=yapi-market|ambalaj → iki tema/iki build
  widget/       Web Component + Shadow DOM (8 KB gzip), SSE akışı; mock-agent/
  admin-web/    React + Vite + TanStack Query/Table + ECharts, 7 pano
packages/
  contracts/    JSON Schema kaynakları → TS tipleri + Pydantic (make contracts)
  core-py/      Pydantic sözleşmeler, TenantContext, Firestore repo katmanı, embedder, PII maskeleme, analitik, PDF
services/
  agent-api/    FastAPI + Google ADK LlmAgent; tenant'a bağlı araçlar, FirestoreSessionService, callback'ler
  admin-api/    tenant yönetimi, panolar (DuckDB yerel / BigQuery prod), CSV + PDF
  jobs/         demo_data, feed_sync, doc_ingest, labeler (conversation-labeler), seed, simulator (Cloud Run Jobs)
config/llm.yaml model ID'leri, embedding boyutu, birim fiyatlar
```

Akış: widget `POST /v1/t/{public_key}/chat` → agent-api tenant'ı **public key + Origin** ile doğrular → ADK agent'ı o
tenant'a bağlı araçlarla (`search_products`, `get_product`, `search_knowledge`, `get_complements`, `propose_bundle`,
`create_quote_request`) çalıştırır → **grounding** guardrail'inden geçen yanıt SSE ile akar (`token`, `products`,
`bundle`, `action`, `source`, `done`, `error`) → widget `ma:add-to-cart` olayıyla vitrin sepetine ekler. Her adım
`AnalyticsEvent` olarak yapılandırılmış log'a yazılır (prod: Cloud Logging → BigQuery; yerel: JSONL + DuckDB fixture).

Değişmez kurallar (CLAUDE.md): Firestore'a yalnızca `magaza_core.repo` ile ve `tenants/{tid}/...` altında erişilir;
`tenant_id` istemciden ya da modelden alınmaz (ADR 004); cevapta yalnızca araçların döndürdüğü SKU'lar geçer (ADR 005);
sektöre özel kod dalı yok — persona şablonu, konu taksonomisi ve tamamlayıcı kurallar tenant verisidir.

## Testler

- `make check`: 108 pytest (emulator dahil: çapraz-tenant sızıntı, grounding, oturum servisi, API/CORS, panolar, veri
  doğrulama), vitest (sözleşmeler, widget, vitrin, admin).
- `make e2e`: vitrin akışı (gez → sepet → ödeme → onay), widget (mock-agent ve gerçek agent), yönetim paneli
  (her pano, CSV ve PDF indirme), masaüstü + mobil.

Demo markalar, ürünler, fiyatlar ve föyler kurgusaldır; gerçek ödeme alınmaz.
