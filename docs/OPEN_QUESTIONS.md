# Açık sorular ve engeller

Her madde: durum (bekliyor / çözüldü / bilgi), bağlam, şimdilik ne yapıldı.

## 1. Gerçek Gemini (Vertex AI) çağrıları — **bekliyor**
- `GOOGLE_CLOUD_PROJECT` ortam değişkeni tanımlı değil. Makinede ADC dosyası var ancak aktif gcloud projesi bu ürünle ilgisiz bir proje; ona maliyet yazmamak için kullanılmadı.
- Şimdilik: tüm agent testleri, eval ve uçtan uca senaryolar deterministik `FakeLlm` ile çalışıyor (`LLM_MODE=fake`).
- Gerekli insan kararı: hangi GCP projesi (europe-west1) kullanılacak; `GOOGLE_CLOUD_PROJECT` + ADC ile `LLM_MODE=vertex make eval` çalıştırılmalı.

## 2. Yerel araç: GNU Make — **bilgi**
- Windows makinesinde `make` yoktu (winget/choco/scoop da yok). `make` hedefleri kabul kriteri olduğu için MSYS2 resmi deposundan `make-4.4.1-3` paketi indirilip `C:\Users\ASUS\bin\make.exe` olarak kopyalandı (Git Bash PATH'inde). Kaldırmak için dosyayı silmek yeterli.
