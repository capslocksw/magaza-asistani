# ADR 001 — Monorepo araçları

- Durum: kabul edildi (Gece 1)
- Bağlam: Python (ADK/FastAPI) servisleri ile TypeScript uygulamaları aynı repoda, tek komutla kurulup kontrol edilmeli.
- Karar:
  - Python: uv workspace, tek kök `.venv`, Python 3.12, `uv_build` backend. Paketler: `magaza-core` (packages/core-py), `magaza-agent-api`, `magaza-admin-api`, `magaza-jobs`.
  - JS: pnpm workspace (`apps/*`, `packages/contracts`). Bilinen kararlı majörler sabitlendi (TypeScript 5.9, Vite 6, ESLint 9, Vitest 3, Next 15, Tailwind 4) — daha yeni majörler (TS 7, Vite 8, ESLint 10) bu gece için risk.
  - Firestore emulator `firebase-tools` devDependency olarak; `demo-magaza` proje kimliği (demo- önekli projeler buluta bağlanmaz).
  - pytest, emulator gerektiren testleri `@pytest.mark.emulator` ile işaretler; `make test` bunları emulator altında çalıştırır.
- Sonuç: `make setup && make check` tek makinede sıfırdan çalışır; Java 21 ve Node 22 önkoşul.
