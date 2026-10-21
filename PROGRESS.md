# PROGRESS — Gece 1 (yerel v1 iskeleti)

Kaynak görev: [docs/KICKOFF.md](docs/KICKOFF.md). Açık sorular: [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md). ADR'ler: [docs/adr/](docs/adr/).

| Taş | Durum | Kanıt (özet) |
| --- | --- | --- |
| M0 Repo iskeleti | ✅ | `make setup` → exit 0; `make check` → ruff/eslint/mypy/tsc temiz, pytest 4 passed, vitest 4 dosya passed |
| M1 Sözleşmeler | ⏳ | |
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

## Kalan işler
(her taş tamamlandıkça güncellenir)
