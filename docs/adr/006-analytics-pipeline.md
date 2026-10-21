# ADR 006 — Analitik hattı ve panolar

- Durum: kabul edildi (Gece 1)
- Bağlam: Agent ve widget her adımda `AnalyticsEvent` üretiyor; yönetim paneli 7 pano, CSV ve aylık PDF istiyor. Prod'da BigQuery, yerelde bulutsuz çalışmalı.
- Karar:
  - **Üretim:** agent-api her olayı tek satır yapılandırılmış JSON log olarak yazar (`analytics_event` alanı). Cloud Logging → BigQuery log sink'i ile `analytics_events` tablosuna akar (kolonlar sözleşmeyle aynı, `payload` JSON). PII, log'a yazılmadan önce maskelenir.
  - **Yerel:** aynı olaylar isteğe bağlı JSONL'e de eklenir (`ANALYTICS_JSONL_PATH`); `simulator` 90 günlük sentetik (`is_synthetic=true`) DuckDB fixture'ı üretir. `DuckDbAnalyticsRepository` fixture + canlı JSONL'i birlikte okur.
  - **Tek SQL, iki lehçe:** panolar bir kez, küçük bir `Dialect` API'si üzerinden yazılır (JSON alan erişimi, koşullu toplama, unnest, hafta/ay, parametre sözdizimi); `DuckDbDialect` ve `BigQueryDialect` bunu çevirir.
  - Huni tekil ziyaretçi (`visitor_id_hash`) üzerinden; "asistanlı" = sohbet eden ziyaretçi; holdout karşılaştırması `visit.payload.group` ile.
  - CSV: UTF-8 BOM, `,` veya `;` (noktalı virgülde ondalık virgül). PDF: Jinja2 HTML → WeasyPrint (ADR 003).
- Sonuç: BigQuery yolu yalnızca SQL üretimi düzeyinde test edildi (birim test); gerçek tabloya karşı doğrulama deploy aşamasında yapılmalı.
