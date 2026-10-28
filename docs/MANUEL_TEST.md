# Manuel test rehberi (yerel)

## 1. Kurulum (ilk sefer)

Önkoşullar: Node 22+, pnpm 10, uv, Java 21, GNU Make, **Git Bash** (Windows'ta komutları Git Bash'te çalıştırın).

```bash
cd /c/dev/kolaptech/magaza-asistani
make setup      # uv + pnpm bağımlılıkları, Playwright tarayıcıları, Firestore emulator, demo veri + analitik fixture (~3-5 dk)
make check      # isteğe bağlı: lint + tip + birim testler (beklenen: exit 0)
```

## 2. Çalıştırma

```bash
make dev        # ilk seferde vitrinleri/widget'ı build eder (~2 dk), sonra her şeyi başlatır
```

Hazır olduğunda konsolda adres listesi görünür. Durdurmak için `Ctrl+C`. Python kodunu değiştirirseniz `make dev`'i yeniden başlatın.

| Ne | Adres |
| --- | --- |
| Yapıcı Market (mock-agent ile) | http://localhost:3101 |
| Yapıcı Market (gerçek agent-api ile) | http://localhost:3101/?ma_api=http://localhost:8080 |
| Kutu&Co Ambalaj (gerçek agent-api ile) | http://localhost:3102/?ma_api=http://localhost:8080 |
| Yönetim paneli | http://localhost:5175 |
| Sağlık kontrolü | http://localhost:8080/healthz · http://localhost:8090/healthz |

`?ma_api=...` sekme boyunca hatırlanır; mock-agent'a dönmek için yeni sekme açın.

## 3. Test senaryoları

| # | Adımlar | Beklenen |
| --- | --- | --- |
| TC-01 Vitrin alışverişi | 3101 → menüden **Yapıştırıcı ve Silikon** → bir ürün → **Sepete ekle** → sağdan açılan sepette **Sepeti onayla** → formu doldurup **Siparişi tamamla** | "Siparişiniz alındı!", `ORD-…` numarası, sepet sayacı 0 |
| TC-02 Widget + gerçek agent | `3101/?ma_api=http://localhost:8080` → sağ alttaki **Ustaya sor** → "Kornişim koptu, matkabım yok" yazıp gönderin | Yanıtta SKU'lu liste ve "Teknik föye göre…", "📄 föye göre" etiketi, 4 ürün kartı, paket kartı: Tutkan Montaj Yapıştırıcısı + Silikon Tabancası + Yüzey Temizleyici + Maskeleme Bandı, toplam **₺449,60** |
| TC-03 Paketi sepete ekle | TC-02'den sonra **Paketi sepete ekle** | Buton "Sepete eklendi ✓", vitrin üstündeki sepet sayacı **4**, "Asistan 4 ürünü sepetinize ekledi" bildirimi |
| TC-04 Asistanlı sipariş | TC-03'ten sonra sepet → ödeme → sipariş | Sipariş onayı; yönetim panelinde sipariş "asistanlı" sayılır |
| TC-05 B2B ambalaj + teklif | `3102/?ma_api=http://localhost:8080` → **Danışmana sor** → "Ayda 1000 koli gönderiyorum, teklif alabilir miyim?" → **Teklif talebi oluştur** → firma, ad soyad, e-posta → **Teklif iste** | "Teklif talebiniz alındı (no: Q-…)". Not: 3101'de (Yapıcı Market) "Teklif iste" butonu **yoktur** |
| TC-06 Kırılacak ürün | 3102 widget → "2 kg seramik kupa göndereceğim, hangi koli?" | Paket: Çift Oluklu Koli + Balonlu Naylon + Hotmelt Koli Bandı + Kupa Ayırıcı Separatör |
| TC-07 Yönetim paneli | 5175 → **Geliştirici olarak giriş** → tenant **Yapıcı Market** → **Konuşmalar** | TC-02'deki sohbet en üstte ("Montaj ve sabitleme"); satıra tıklayınca mesajlar ve olaylar |
| TC-08 Panolar ve dışa aktarma | 7 panoyu gezin; bir panelde **CSV indir**; üstte ay seçip **Aylık raporu PDF indir** | Grafik/tablolar dolu; CSV Excel'de Türkçe karakterlerle açılır; PDF'te tenant logosu |
| TC-09 Holdout (kontrol grubu) | 3101'de tarayıcı konsolunda `localStorage.setItem("ma_vid","v_e2e_control_0014")` → sayfayı yenile | Widget görünmez (ziyaret yine sayılır) |
| TC-10 Origin güvenliği | Git Bash: `curl -s -X POST http://localhost:8080/v1/t/pk_test_yapimarket/chat -H "content-type: application/json" -H "origin: https://evil.example" -d '{"message":"merhaba","visitor_id":"v_test_00001"}'` | `403` ve `"code":"origin_not_allowed"` |

İpuçları: PowerShell'de `curl` yerine `curl.exe` kullanın; Türkçe karakterli JSON'u curl yerine tarayıcıdan/widget'tan deneyin
(Windows konsolu UTF-8 göndermeyebilir).

## 4. Otomatik testler

```bash
make check   # ruff, eslint, mypy, tsc, pytest (emulator), vitest
make e2e     # build + seed + 26 Playwright testi (vitrin, widget, gerçek agent, yönetim paneli; masaüstü + mobil)
make eval    # 2 × 30 altın set vaka (FakeLlm)
```

Ekran görüntüleri: `artifacts/screenshots/m3..m6/`. `make e2e` çalışan `make dev` sunucularını yeniden kullanır.

## 5. Gerçek Gemini ile (isteğe bağlı)

Kurulum ve ilk deneme: [GEMINI_KURULUM.md](GEMINI_KURULUM.md). Çağrılar faturalandırılır; toplam harcama
`config/llm.yaml → budget` ile 5 $'la sınırlıdır (4,50 $'da durur), durum: `make budget`.
