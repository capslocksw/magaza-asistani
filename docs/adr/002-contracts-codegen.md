# ADR 002 — Sözleşmeler: JSON Schema tek kaynak

- Durum: kabul edildi (Gece 1)
- Bağlam: Widget (TS), vitrin (TS), admin-web (TS) ve Python servisleri aynı olay/mesaj tiplerini konuşuyor.
- Karar:
  - Kaynak: `packages/contracts/schemas/*.schema.json` (Draft 2020-12, her tip `$defs` içinde, `title` = tip adı).
  - `make contracts`: şemalar tek bir `generated/bundle.schema.json` içinde birleştirilir; buradan
    `json-schema-to-typescript` → `packages/contracts/src/generated/contracts.ts`,
    `datamodel-code-generator` → `packages/core-py/src/magaza_core/contracts/generated.py` (Pydantic v2, `extra="forbid"`).
  - JSON Schema'nın adlandırılmış Python tipine dönüşmeyen iki şey (`SseEvent` ayrımlı birleşimi, olay tipi `Literal`'i) `magaza_core/contracts/__init__.py` içinde elle tanımlıdır; test şemadaki enum ile eşitliği doğrular.
  - Dizi elemanlarında `pattern` kullanılmaz (üretici RootModel üretir); SKU referans bütünlüğü veri testlerinde kontrol edilir.
  - `ChatRequest` `tenant_id` taşımaz ve `additionalProperties: false`'tur: tenant yalnızca doğrulanmış public key + Origin'den gelir.
  - `AnalyticsEvent` tiplerine `visit` eklendi: asistanlı/asistansız dönüşüm paydası için gerekli.
- Sonuç: Üretilen dosyalar commit'lenir; vitest, commit'li bundle'ın şemalardan yeniden üretilenle aynı olduğunu doğrular.
