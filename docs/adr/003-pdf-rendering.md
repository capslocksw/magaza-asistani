# ADR 003 — PDF üretimi (teknik föyler ve aylık rapor)

- Durum: kabul edildi (Gece 1)
- Bağlam: KICKOFF aylık raporu WeasyPrint ile istiyor; teknik föyler Markdown'dan PDF'e dönüşmeli. WeasyPrint Pango/GObject
  yerel kütüphanelerine ihtiyaç duyar; geliştirme makinesi (Windows) bunlara sahip değil.
- Karar: `magaza_core.pdf` tek bir HTML→PDF arayüzü sunar.
  - Üretimde (Linux konteyner) **WeasyPrint** kullanılır.
  - WeasyPrint yüklenemezse (veya Windows'ta `WEASYPRINT_DLL_DIRECTORIES` yoksa) **headless Chromium** (Playwright) yedeğine düşer;
    Playwright zaten `make setup` ile kuruluyor. `PDF_RENDERER=weasyprint|chromium` ile zorlanabilir.
  - Her iki yol da aynı HTML/CSS şablonunu kullanır; Türkçe karakterler sistem fontlarıyla gömülür (pypdf ile metin çıkarımı test edildi).
- Sonuç: Yerelde sıfır ek kurulum; prod imajında GTK/Pango paketleri + WeasyPrint gerekir (Dockerfile notu, deploy kapsam dışı).
