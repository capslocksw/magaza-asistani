# PROGRESS — Gece 1 (yerel v1 iskeleti)

Kaynak görev: [docs/KICKOFF.md](docs/KICKOFF.md). Açık sorular: [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md). ADR'ler: [docs/adr/](docs/adr/).

| Taş | Durum | Kanıt (özet) |
| --- | --- | --- |
| M0 Repo iskeleti | ✅ | `make setup` → exit 0; `make check` → ruff/eslint/mypy/tsc temiz, pytest 4 passed, vitest 4 dosya passed |
| M1 Sözleşmeler | ✅ | `make contracts` 42 tip üretir; vitest 26 + pytest 38 sözleşme testi; tsc + mypy temiz |
| M2 Demo veri | ⏳ | |
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

## Kalan işler
(her taş tamamlandıkça güncellenir)
