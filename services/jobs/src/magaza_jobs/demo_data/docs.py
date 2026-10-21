"""Technical data sheets ("teknik föy") generated from product data as Markdown, rendered to PDF."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

import markdown

from magaza_core.contracts import Product


@dataclass(frozen=True)
class DocSheet:
    doc_id: str
    sku: str
    title: str
    markdown: str


_PROFILES: dict[str, dict[str, list[str]]] = {
    "adhesive": {
        "areas": [
            "Korniş, ayna, raf ve süpürgelik montajı (matkapsız)",
            "Dekoratif profil, panel ve pervaz yapıştırma",
            "Beton, tuğla, ahşap, alçıpan, seramik ve metal yüzeyler",
        ],
        "steps": [
            "Yüzeyi tozdan, yağdan ve eski boya kalıntılarından arındırın; gerekirse yüzey temizleyici kullanın.",
            "Kartuş ambalajda ucu kesip nozulu takın ve silikon tabancasına yerleştirin; tüp ambalajda doğrudan sıkın.",
            "Yapıştırıcıyı parçaya noktasal veya şerit halinde, kenarlardan 2 cm içeride uygulayın.",
            "Parçayı yerine bastırın; ilk 10 dakika içinde konumunu düzeltebilirsiniz.",
            "Ağır parçaları kuruma süresince maskeleme bandı veya destekle sabitleyin; tam kuruma süresi dolmadan yük bindirmeyin.",
        ],
        "safety": [
            "Çocukların ulaşamayacağı yerde saklayın.",
            "Uygulama sırasında ortamı havalandırın.",
            "Gözle temasında bol suyla yıkayın, tahriş devam ederse doktora başvurun.",
        ],
        "faq": [
            "Korniş taşır mı? Taşıma kapasitesi değerinin yarısını aşmayan yüklerde, tam kuruma sonrası evet.",
            "Islak yüzeye uygulanır mı? Hayır; yüzey kuru ve temiz olmalıdır.",
        ],
        "storage": ["+5 / +25 °C arasında, kuru ortamda, açılmamış ambalajda 12 ay."],
    },
    "silicone": {
        "areas": [
            "Küvet, lavabo, duşakabin ve tezgah birleşimleri",
            "Cam, alüminyum ve PVC doğrama derzleri",
            "Seramik ve fayans köşe derzleri",
        ],
        "steps": [
            "Eski silikonu silikon sökücü ile yumuşatıp sıyırın; yüzeyi kurulayın.",
            "Derzin iki kenarına maskeleme bandı yapıştırın.",
            "Kartuşu silikon tabancasına takıp derz boyunca kesintisiz uygulayın.",
            "Silikon sıyırıcı ile hattı düzeltin ve bantları kabuk bağlamadan sökün.",
            "24 saat boyunca suyla temas ettirmeyin.",
        ],
        "safety": [
            "Kürlenme sırasında asetik koku oluşabilir; ortamı havalandırın.",
            "Cilde bulaşırsa kurumadan silin.",
        ],
        "faq": [
            "Boyanabilir mi? Hayır, silikon boyanmaz; boyanacak derzlerde akrilik mastik kullanın.",
            "Kaç saatte kurur? Kabuk bağlama ve tam kuruma süreleri teknik özellikler tablosundadır.",
        ],
        "storage": ["+5 / +25 °C arasında 18 ay."],
    },
    "foam": {
        "areas": [
            "Kapı ve pencere kasası boşlukları",
            "Boru ve kablo geçişleri",
            "Isı ve ses yalıtımı amaçlı boşluk doldurma",
        ],
        "steps": [
            "Kutuyu en az 20 kez çalkalayın.",
            "Yüzeyi su spreyi ile hafifçe nemlendirin.",
            "Boşluğun yaklaşık yarısını doldurun; köpük genleşerek tamamlar.",
            "Bir saat sonra fazlasını maket bıçağı ile kesin.",
            "UV ışığına maruz kalan yüzeyleri boya veya mastikle kapatın.",
        ],
        "safety": [
            "Eldiven ve koruyucu gözlük kullanın.",
            "Basınçlı kap: 50 °C üzerinde bırakmayın, delmeyin.",
        ],
        "faq": [
            "Taze köpük nasıl temizlenir? Köpük temizleyici sprey ile; kürlenmiş köpük yalnızca mekanik olarak alınır."
        ],
        "storage": ["Dik konumda, +5 / +25 °C arasında 12 ay."],
    },
    "paint": {
        "areas": ["Sıva, alçı ve alçıpan duvarlar", "Daha önce boyanmış yüzeylerin yenilenmesi"],
        "steps": [
            "Yüzeydeki çatlakları macunla kapatın, zımparalayın ve tozunu alın.",
            "Yeni veya emici yüzeylere bir kat astar uygulayın.",
            "Zemini örtü ile, kenarları maskeleme bandı ile koruyun.",
            "Boyayı iyice karıştırın; ilk katı %10 su ile inceltip rulo ile uygulayın.",
            "Kat arası bekleme süresinden sonra ikinci katı inceltmeden uygulayın.",
        ],
        "safety": [
            "Uygulama sırasında ortamı havalandırın.",
            "Ambalajı +5 °C altında bırakmayın; dondurmayın.",
        ],
        "faq": [
            "Kaç kat gerekir? Renk değişiminde iki kat önerilir.",
            "Ne kadar boya lazım? Duvar alanı (m²) × kat sayısı ÷ örtücülük.",
        ],
        "storage": ["Ağzı kapalı ambalajda, +5 / +35 °C arasında 24 ay."],
    },
    "primer": {
        "areas": [
            "Yeni sıva ve alçı yüzeyler",
            "Tozuyan veya emiciliği yüksek yüzeyler",
            "Renk değişimi öncesi",
        ],
        "steps": [
            "Yüzeyi tozdan arındırın.",
            "Astarı karıştırın ve gerekirse %10-20 suyla inceltin.",
            "Rulo veya fırça ile tek kat uygulayın.",
            "Boyaya hazır olma süresini bekleyip son kata geçin.",
        ],
        "safety": ["Çocukların ulaşamayacağı yerde saklayın.", "Gözle temasından kaçının."],
        "faq": [
            "Astar şart mı? Yeni sıva, alçı ve renk değişimlerinde boyanın tutunması ve örtücülüğü için önerilir."
        ],
        "storage": ["Dondurmayın; +5 / +35 °C arasında 24 ay."],
    },
    "power_tool": {
        "areas": ["Mobilya montajı ve vidalama", "Ahşap, metal ve (darbe modunda) beton delme"],
        "steps": [
            "Malzemeye uygun ucu seçin: beton için karbür uçlu beton ucu ve darbe modu, metal için HSS uç.",
            "Ucu mandrene tam oturtun ve sıkın.",
            "Delik yerini işaretleyin; ilk delmeyi düşük devirde başlatın.",
            "Dübel deliğinde uç çapını dübel çapıyla aynı seçin.",
            "Kullanım sonrası aküyü serin yerde, yarı dolu saklayın.",
        ],
        "safety": [
            "Koruyucu gözlük kullanın; beton delerken toz maskesi takın.",
            "Duvar içinde elektrik ve su hattı olabilecek noktaları önceden kontrol edin.",
            "Uç değiştirirken aküyü çıkarın veya fişi çekin.",
        ],
        "faq": [
            "Akülü vidalama betonu deler mi? Darbe fonksiyonu yoksa betonda yetersiz kalır; darbeli matkap tercih edin."
        ],
        "storage": ["Kuru ortamda, çantasında saklayın."],
    },
    "grout": {
        "areas": ["Banyo ve mutfak fayans aralıkları", "Islak hacimlerde derz yenileme"],
        "steps": [
            "Eski derzi derz kazıma aleti ile 2-3 mm kazıyın, tozunu alın.",
            "Derz temizleyici ile küf ve kiri giderin, kurulayın.",
            "Tozu suyla topaksız kıvama gelene kadar karıştırın, 5 dakika dinlendirin.",
            "Lastik mala ile çapraz hareketlerle derzlere doldurun.",
            "15-20 dakika sonra nemli süngerle yüzeyi temizleyin.",
        ],
        "safety": ["Çimento esaslıdır; eldiven kullanın.", "Gözle temasında bol suyla yıkayın."],
        "faq": ["Ne zaman suyla temas edebilir? Kullanıma açılma süresinden sonra."],
        "storage": ["Kuru ortamda 12 ay."],
    },
    "box": {
        "areas": ["E-ticaret ve kargo gönderimleri", "Depolama ve taşımacılık"],
        "steps": [
            "Ürün ağırlığının kolinin taşıma ağırlığının yarısını geçmemesine dikkat edin.",
            "Kırılacak ürünlerde her parçayı balonlu naylonla en az iki kat sarın.",
            "Ürün ile koli duvarı arasında her yönde en az 5 cm boşluk bırakıp dolgu malzemesiyle doldurun.",
            "Koliyi alt ve üstten H-bantlama yöntemiyle kapatın.",
            "Kırılacak ürünlerde 'Kırılacak Eşya' etiketi veya baskılı bant kullanın.",
        ],
        "safety": [
            "Nemli ortamda bekletmeyin; karton nemle dayanımını kaybeder.",
            "İstiflerken ağır kolileri alta koyun.",
        ],
        "faq": [
            "Tek oluklu mu çift oluklu mu? Kırılacak veya 10 kg üzeri ürünlerde çift oluklu (BC dalga) koli önerilir.",
            "Taşıma ağırlığı nedir? Kolinin içerik dahil güvenle taşıyabileceği en yüksek ağırlıktır.",
        ],
        "storage": ["Kuru, düz zeminde ve güneş görmeyen yerde istifleyin."],
    },
    "tape": {
        "areas": ["Koli kapama", "Kargo ve depo paketleme"],
        "steps": [
            "Koli yüzeyinin tozsuz ve kuru olmasını sağlayın.",
            "Bant tabancası ile koli ek yeri boyunca bantlayın.",
            "Kenarlardan 5-7 cm taşırarak H-bantlama yapın.",
            "Bandı elle bastırarak yapışmayı tamamlayın.",
        ],
        "safety": ["Bant tabancası bıçağına dikkat edin."],
        "faq": [
            "Hotmelt mi akrilik mi? Ağır ve geri dönüşümlü kolilerde hotmelt daha yüksek ilk yapışma sağlar; akrilik sararmaz ve soğukta iyi çalışır."
        ],
        "storage": ["+10 / +30 °C arasında, rulolar dik konumda."],
    },
    "stretch": {
        "areas": ["Palet sarma ve sabitleme", "Koli gruplarını bir arada tutma"],
        "steps": [
            "Filmin ucunu paletin alt köşesine sıkıştırın.",
            "Paletin alt kısmına 3 tur sarın.",
            "Her turda filmin %50'si önceki tura binecek şekilde yukarı çıkın.",
            "Üst kısımda 2 tur atıp filmi kesin ve ucunu bastırarak yapıştırın.",
        ],
        "safety": ["Keskin köşelerde köşe koruyucu kullanın; film yırtılabilir."],
        "faq": [
            "Kaç mikron seçmeliyim? Hafif yüklerde 17 mikron, ağır ve keskin köşeli yüklerde 23 mikron önerilir."
        ],
        "storage": ["Güneş görmeyen serin yerde saklayın."],
    },
    "bubble": {
        "areas": ["Seramik, cam, porselen ve elektronik ürün koruması", "Mobilya köşe ve yüzey koruması"],
        "steps": [
            "Kabarcıklı yüzey ürüne bakacak şekilde sarın.",
            "Kırılacak ürünleri en az iki kat sarın.",
            "Sarılan ürünü bantla sabitleyin.",
            "Kolide kalan boşlukları dolgu malzemesiyle doldurun.",
        ],
        "safety": ["Plastik ambalajı çocuklardan uzak tutun."],
        "faq": [
            "Küçük mü büyük kabarcık mı? Hafif ve küçük ürünlerde 10 mm, ağır ürünlerde 30 mm kabarcık daha iyi darbe emer."
        ],
        "storage": ["Isı kaynaklarından uzak tutun."],
    },
}


def _spec_value(value: str | float | bool, unit: str | None) -> str:
    if isinstance(value, bool):
        text = "Evet" if value else "Hayır"
    elif isinstance(value, float):
        text = f"{value:g}".replace(".", ",")
    else:
        text = str(value)
    return f"{text} {unit}" if unit else text


def build_sheet(product: Product, profile: str, store_name: str) -> DocSheet:
    p = _PROFILES[profile]
    lines = [
        f"# {product.title} — Teknik Föy",
        "",
        f"**Ürün kodu:** {product.sku} · **Marka:** {product.brand} · **Kategori:** {product.category_name}",
        "",
        "## Ürün Tanımı",
        "",
        product.description,
        "",
        "## Kullanım Alanları",
        "",
        *[f"- {a}" for a in p["areas"]],
        "",
        "## Teknik Özellikler",
        "",
        "| Özellik | Değer |",
        "| --- | --- |",
        *[f"| {s.label} | {_spec_value(s.value, s.unit)} |" for s in product.specs],
        "",
        "## Uygulama",
        "",
        *[f"{i}. {step}" for i, step in enumerate(p["steps"], start=1)],
        "",
        "## Sık Sorulan Sorular",
        "",
        *[f"- {q}" for q in p["faq"]],
        "",
        "## Güvenlik",
        "",
        *[f"- {s}" for s in p["safety"]],
        "",
        "## Saklama",
        "",
        *[f"- {s}" for s in p["storage"]],
        "",
        f"_Bu föy {store_name} demo kataloğu için üretilmiş kurgusal bir belgedir._",
        "",
    ]
    return DocSheet(
        doc_id=f"doc-{product.sku.lower()}",
        sku=product.sku,
        title=f"{product.title} — Teknik Föy",
        markdown="\n".join(lines),
    )


def sheet_html(sheet: DocSheet, store_name: str, primary_color: str) -> str:
    body = markdown.markdown(sheet.markdown, extensions=["tables"])
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>{escape(sheet.title)}</title>
<style>
  body {{ font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: #1f2937; font-size: 11pt; line-height: 1.45; }}
  header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid {primary_color};
           padding-bottom: 6pt; margin-bottom: 12pt; }}
  header .store {{ font-weight: 700; color: {primary_color}; font-size: 13pt; }}
  header .kind {{ color: #6b7280; font-size: 9pt; text-transform: uppercase; letter-spacing: .08em; }}
  h1 {{ font-size: 17pt; margin: 0 0 6pt; }}
  h2 {{ font-size: 12.5pt; color: {primary_color}; margin: 14pt 0 4pt; border-bottom: 1px solid #e5e7eb; padding-bottom: 2pt; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 10pt; }}
  th, td {{ border: 1px solid #e5e7eb; padding: 4pt 6pt; text-align: left; }}
  th {{ background: #f3f4f6; }}
  em {{ color: #6b7280; font-size: 9pt; }}
</style></head>
<body><header><span class="store">{escape(store_name)}</span><span class="kind">Teknik Föy · {escape(sheet.sku)}</span></header>
{body}
</body></html>"""
