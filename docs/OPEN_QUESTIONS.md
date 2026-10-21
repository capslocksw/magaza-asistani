# Açık sorular ve engeller

Her madde: durum (bekliyor / çözüldü / bilgi), bağlam, şimdilik ne yapıldı.

## 1. Gerçek Gemini (Vertex AI) çağrıları — **bekliyor**
- `GOOGLE_CLOUD_PROJECT` ortam değişkeni tanımlı değil. Makinede ADC dosyası var ancak aktif gcloud projesi bu ürünle ilgisiz bir proje; ona maliyet yazmamak için kullanılmadı.
- Şimdilik: tüm agent testleri, eval ve uçtan uca senaryolar deterministik `FakeLlm` ile çalışıyor (`LLM_MODE=fake`).
- Gerekli insan kararı: hangi GCP projesi (europe-west1) kullanılacak; `GOOGLE_CLOUD_PROJECT` + ADC ile `LLM_MODE=vertex make eval` çalıştırılmalı.

## 2. Yerel araç: GNU Make — **bilgi**
- Windows makinesinde `make` yoktu (winget/choco/scoop da yok). `make` hedefleri kabul kriteri olduğu için MSYS2 resmi deposundan `make-4.4.1-3` paketi indirilip `C:\Users\ASUS\bin\make.exe` olarak kopyalandı (Git Bash PATH'inde). Kaldırmak için dosyayı silmek yeterli.

## 3. `adk eval` CLI ve tenant'a bağlı agent — **bilgi / karar bekliyor**
- `adk eval` modül düzeyinde statik bir `root_agent` bekliyor. Bizim agent'ımız güvenlik gereği her istekte doğrulanmış tenant bağlamıyla (tenant'a bağlı araç kapanışları, oturum servisi) kuruluyor.
- Şimdilik: altın setler ADK `EvalSet` JSON formatında (`services/agent-api/evals/*.evalset.json`, 30+30 vaka); `make eval` bu dosyaları üretim hattından (`run_turn`) geçiren ince bir koşucu ile çalışıyor (araç yörüngesi + referans yanıt örtüşmesi; eşikler `test_config.json`).
- Karar: Vertex AI Gen AI Evaluation Service / `adk eval` ile tam uyum için her tenant'a özel bir "eval agent" modülü üretilsin mi?

## 4. Vertex embedding benzerlik eşiği — **bekliyor**
- `config/llm.yaml` → `embedding.min_similarity: 0.0` (kapalı). Gerçek `gemini-embedding-001` vektörleriyle "katalogda yok" (karşılanmayan talep) ayrımı için eşik gerçek trafikte ayarlanmalı. Yerel hashing embedder'da alakasız sorgular da 0,1–0,2 benzerlik aldığından eşik uygulanmıyor.

## 5. Üretimde PDF — **bilgi**
- Aylık rapor ve föy PDF'leri üretimde WeasyPrint ile basılacak (Linux imajında Pango/GTK paketleri gerekir). Windows geliştirme makinesinde WeasyPrint yerel kütüphaneleri olmadığından headless Chromium yedeği kullanılıyor (ADR 003).

## 6. Yönetim paneli girişi (Firebase Auth) — **bekliyor**
- admin-api üretimde Firebase ID token doğrular (rol ve tenant listesi custom claim'lerden: `role`, `tenants`). admin-web'de e-posta/şifre formu yer tutucu; Firebase Web SDK yapılandırması (apiKey, authDomain, proje) ve claim atama süreci insan kararı gerektiriyor.
- Şimdilik: yerelde `DEV_AUTH_BYPASS=1` ile "Geliştirici olarak giriş" (Cloud Run'da `K_SERVICE` varken bypass kapalı).

## 7. BigQuery analitik tablosu — **bekliyor**
- Prod'da Cloud Logging → BigQuery sink'i ve `BIGQUERY_EVENTS_TABLE` (proje.dataset.analytics_events) kurulmalı; BigQuery lehçesi yalnızca SQL üretimi düzeyinde test edildi (ADR 006).
