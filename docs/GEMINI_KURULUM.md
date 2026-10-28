# Gerçek Gemini kurulumu (GCP hesabını bağlama)

Bu adımları **sen** uygularsın. Claude gerçek modelle (ücretli) hiçbir test, eval ya da deneme çalıştırmaz; bu
rehberdeki komutları sen çalıştırıp çıktıyı paylaşırsın.

## Koruma özeti (ADR 007)

- Toplam harcama sınırı **5 $** (`config/llm.yaml → budget.hard_cap_usd`). 0,50 $ güvenlik payı nedeniyle istekler
  **4,50 $**'da durur.
- Her ücretli istek (sohbet + embedding) gönderilmeden önce en kötü durum maliyetini `.local/llm-spend.sqlite`
  defterine ayırır; sınırı aşacak istek **API'ye hiç gitmez**. Yanıttan sonra gerçek token sayılarıyla kapatılır.
- Durumu her an görmek için:

```bash
make budget
```

Çıktıda `spent_usd` (harcanan), `in_flight_usd` (süren istekler), `remaining_usd` (kalan) ve model bazında çağrı/token
sayıları yer alır. `.local/llm-spend.sqlite` dosyasını **silme**: sayaç sıfırlanır.

- `make check` ve `make e2e` her zaman sahte modelle çalışır; kabuğunda `LLM_MODE=vertex` tanımlı olsa bile harcamaz.

## 1. GCP projesi

1. Google Cloud Console'da faturalandırma hesabı bağlı bir proje seç ya da oluştur; **proje ID**'sini not et
   (aşağıda `PROJE_ID`).
2. Vertex AI API'yi etkinleştir:

```bash
gcloud services enable aiplatform.googleapis.com --project PROJE_ID
```

## 2. İkinci savunma hattı: GCP bütçe uyarısı (önerilir)

Uygulama içi defter asıl sert sınırdır. GCP tarafında ayrıca bir bütçe uyarısı kur:

- Console → **Billing → Budgets & alerts → Create budget**: kapsam = bu proje, tutar = **5 USD**, eşikler %50, %90,
  %100 (gerçekleşen) ve %100 (tahmini), e-posta bildirimi açık.
- Not: GCP bütçesi harcamayı **durdurmaz**, yalnızca uyarır; fatura verisi saatlerce gecikebilir.
- İsteğe bağlı hız sınırı: **IAM & Admin → Quotas** altında `gemini-3.8-flash` (europe-west1) için dakikalık istek
  kotasını düşür (ör. 10/dk). Bu toplam harcamayı değil hızı sınırlar.

## 3. Kimlik bilgileri (Application Default Credentials)

```bash
gcloud auth application-default login
```

```bash
gcloud auth application-default set-quota-project PROJE_ID
```

Service account JSON dosyası kullanma ve asla repoya koyma (`.env.local` git dışındadır).

## 4. İlk deneme: tek soru (elle)

Önce sayacın sıfır olduğunu gör:

```bash
make budget
```

Sistemi gerçek sohbet modeliyle başlat (embedding yerel kalır, ücretsiz):

```bash
LLM_MODE=vertex GOOGLE_CLOUD_PROJECT=PROJE_ID make dev
```

`make dev` açılışta harcama durumunu yazdırır. Ardından tarayıcıda
`http://localhost:3101/?ma_api=http://localhost:8080` adresini aç, asistana **tek** soru sor
(ör. “Kornişim koptu, matkabım yok”), sonra yeni bir terminalde:

```bash
make budget
```

Beklenen: `calls` 2–5 arası (araç döngüsü), soru başına tahmini **0,01–0,05 $**. Gerçek değer `spent_usd`'dedir.

## 5. Küçük eval (isteğe bağlı)

Gerçek modelle eval, `--confirm-spend` olmadan çalışmaz ve koşu başına ayrıca 0,50 $ ile sınırlıdır
(`--run-cap-usd` ile düşürülebilir). Önce az vakayla başla (`make dev` kapalıyken):

```bash
LLM_MODE=vertex GOOGLE_CLOUD_PROJECT=PROJE_ID make eval EVAL_ARGS="--confirm-spend --limit 3"
```

3 vaka × 2 tenant = 6 soru. Çıktı, defteri koşudan önce ve sonra yazdırır.

## 6. Gerçek embedding (sonraki adım, isteğe bağlı)

`EMBEDDING_MODE=vertex` ürün ve föyleri `gemini-embedding-001` ile embed eder. Tohumlama her `make dev`
başlangıcında tüm kataloğu yeniden embed eder (~840 istek, tahmini 0,02–0,04 $). Sohbet ve arama aynı modda olmalı;
ikisini birlikte aç:

```bash
LLM_MODE=vertex EMBEDDING_MODE=vertex GOOGLE_CLOUD_PROJECT=PROJE_ID make dev
```

## 7. Bütçe dolarsa

- İstek gönderilmez; widget “Asistan şu anda yanıt veremiyor” der, SSE `error` olayının kodu `budget_exceeded` olur,
  agent-api log'unda `refused by the spend guard` görünür.
- Sınırı değiştirmek bilinçli bir karardır: `config/llm.yaml → budget.hard_cap_usd` ve 5 $ üst sınırını doğrulayan
  `packages/core-py/tests/test_budget.py` birlikte değiştirilmelidir.
