# ADR 007 — Gerçek model harcaması için sert bütçe sınırı

- Durum: kabul edildi (Release 2, adım 1)
- Bağlam: Gerçek Gemini (Vertex AI) ile ilerlenecek; toplam harcama **5 $'ı geçmemeli** ve beklenmeyen API maliyeti
  oluşmamalı. GCP bütçe uyarıları gecikmeli gelir ve harcamayı kendiliğinden durdurmaz; koruma, istek API'ye çıkmadan
  önce uygulama içinde yapılmalı.
- Karar:
  - **Rezervasyon defteri:** Her ücretli istek (sohbet ve embedding) gönderilmeden önce en kötü durum maliyetini
    `.local/llm-spend.sqlite` defterine ayırır. Defter tüm yerel süreçlerce paylaşılır (agent-api, admin-api, işler,
    eval); `BEGIN IMMEDIATE` ile kontrol + ayırma tek işlemde yapılır, eşzamanlı istekler sınırı birlikte aşamaz.
  - **Sınır:** `config/llm.yaml → budget`: `hard_cap_usd: 5.00`, `safety_margin_usd: 0.50`. Harcanan + uçuştaki + bu
    istek > 4,50 $ ise istek **gönderilmez** (`BudgetExceeded`), defterde `refused` olarak kaydedilir. Bir test,
    yapılandırmadaki sınırın 5 $'ı aşmadığını doğrular.
  - **En kötü durum tahmini:** girdi = istek JSON uzunluğu / 2,5 karakter (Türkçe gerçekte ~3,5–4 karakter/token,
    yani bilinçli olarak fazla); çıktı = `max_output_tokens` (4096, her sohbet isteğine zorla uygulanır). Fiyatlar
    `pricing_usd_per_1m_tokens`'tan; fiyatı tanımsız model **reddedilir**.
  - **Kapanış:** yanıt sonrası `usage_metadata` ile gerçek maliyet yazılır (girdi = prompt + tool-use prompt; çıktı =
    aday + düşünme token'ları). 4xx (429 dahil) faturalanmadığı için serbest bırakılır; zaman aşımı/sunucu hatası
    gibi belirsiz sonuçlarda en kötü durum defterde kalır.
  - **Tek giriş noktaları:** sohbet için `BudgetedGemini` (ADK `Gemini` alt sınıfı), embedding için `VertexEmbedder`.
    Başka bir ücretli istemci eklenirse aynı korumadan geçmek zorundadır.
  - **Açık onay:** `LLM_MODE=vertex` yalnızca sohbet modelini açar; ücretli embedding ayrıca `EMBEDDING_MODE=vertex`
    ister (aksi halde her `make dev` tohumlaması tüm kataloğu sessizce yeniden embed ederdi). Gerçek modelle eval
    `--confirm-spend` olmadan çalışmaz ve koşu başına ayrıca `--run-cap-usd` (varsayılan 0,50 $) ile sınırlıdır.
  - **Testler asla harcamaz:** `make check`/`make e2e` modları `fake`'e zorlar; pytest gerçek `google-genai`
    istemcisi kurulmasını engeller ve geçici bir defter kullanır; e2e, yeniden kullandığı agent-api `fake` değilse
    durur.
  - **Cloud Run:** dosya defteri örnek başınadır (N örnek = N × sınır). `K_SERVICE` varken koruma başlamayı reddeder;
    paylaşılan defter gelene kadar prod'da ücretli çağrı yoktur (OPEN_QUESTIONS #8).
- Sonuç: Sınır, istek başına en fazla birkaç sentlik tahmin hatasıyla (uçuştaki isteklerin gerçek maliyeti tahmini
  aşarsa) korunur; güvenlik payı bunu karşılar. GCP tarafında 5 $'lık bütçe uyarısı ikinci savunma hattıdır
  ([docs/GEMINI_KURULUM.md](../GEMINI_KURULUM.md)). Defter dosyası silinirse sayaç sıfırlanır; bu yüzden dosya
  `.local/` altında, git dışında tutulur ve silinmemelidir.
