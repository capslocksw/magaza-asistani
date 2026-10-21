"""Kutu&Co Ambalaj (ambalaj) demo catalog: B2B packaging supplies. Brand names are fictional."""

from __future__ import annotations

from .model import Builder, CategoryInfo, Draft, spec

CATEGORIES: list[CategoryInfo] = [
    CategoryInfo(
        "koli-tek-oluklu",
        "Tek Oluklu Koli",
        "TOK",
        "box",
        "Hafif ürünler için ekonomik B dalga koliler",
        ["Standart koli", "Kilitli dipli koli"],
    ),
    CategoryInfo(
        "koli-cift-oluklu",
        "Çift Oluklu Koli",
        "COK",
        "box",
        "Kırılacak ve ağır ürünler için BC dalga koliler",
        ["Çift oluklu koli"],
    ),
    CategoryInfo(
        "koli-bandi",
        "Koli Bandı",
        "BNT",
        "tape",
        "Akrilik, hotmelt, sessiz ve baskılı bantlar",
        ["Koli bandı", "Bant tabancası"],
    ),
    CategoryInfo(
        "strec-film",
        "Streç Film",
        "STR",
        "film",
        "El ve makine streç filmleri",
        ["El streci", "Makine streci", "Aparat"],
    ),
    CategoryInfo(
        "balonlu-naylon",
        "Balonlu Naylon",
        "BAL",
        "bubble",
        "Rulo balonlu naylon, balonlu zarf ve poşet",
        ["Rulo", "Balonlu zarf", "Balonlu poşet"],
    ),
    CategoryInfo(
        "dolgu",
        "Dolgu ve Koruma",
        "DLG",
        "fill",
        "Kırpık kağıt, köpük cips, hava yastığı, köşe koruyucu, separatör",
        ["Dolgu", "Köşe koruyucu", "Separatör", "Levha"],
    ),
    CategoryInfo(
        "etiket", "Etiket", "ETK", "label", "Kargo ve uyarı etiketleri", ["Kargo etiketi", "Uyarı etiketi"]
    ),
    CategoryInfo(
        "zarf-poset",
        "Zarf ve Kargo Poşeti",
        "ZRF",
        "envelope",
        "Kargo poşetleri ve kraft zarflar",
        ["Kargo poşeti", "Zarf"],
    ),
]

_TOK_SIZES = [
    (15, 10, 10),
    (20, 15, 10),
    (20, 20, 20),
    (25, 20, 15),
    (30, 20, 15),
    (30, 30, 30),
    (35, 25, 20),
    (40, 30, 20),
    (40, 30, 30),
    (40, 40, 40),
    (50, 30, 30),
    (50, 40, 40),
    (60, 40, 40),
    (20, 10, 5),
    (25, 25, 10),
    (30, 22, 8),
]
_TOK_DOCS = {(30, 20, 15), (40, 30, 30), (25, 20, 15)}
_COK_SIZES = [
    (20, 20, 20),
    (25, 20, 20),
    (30, 20, 20),
    (30, 30, 20),
    (30, 30, 30),
    (40, 30, 30),
    (40, 40, 30),
    (40, 40, 40),
    (50, 40, 40),
    (60, 40, 40),
    (60, 50, 50),
    (80, 60, 60),
]
_COK_DOCS = {(30, 30, 30), (40, 30, 30), (20, 20, 20), (40, 40, 40), (30, 20, 20)}


def _dims(size: tuple[int, int, int]) -> str:
    return " x ".join(str(v) for v in size)


def _area_m2(size: tuple[int, int, int]) -> float:
    length, width, height = size
    return 2 * (length * width + length * height + width * height) / 10000 * 1.1


def build(b: Builder) -> None:
    _single_wall(b)
    _double_wall(b)
    _tapes(b)
    _stretch(b)
    _bubble(b)
    _fill(b)
    _labels(b)
    _envelopes(b)


def _box_specs(size: tuple[int, int, int], wave: str, load: float, gsm: int, pack: int) -> list:
    length, width, height = size
    return [
        spec("ic_olcu", "İç ölçü", f"{_dims(size)} cm"),
        spec("uzunluk_cm", "Uzunluk", length, "cm"),
        spec("genislik_cm", "Genişlik", width, "cm"),
        spec("yukseklik_cm", "Yükseklik", height, "cm"),
        spec("dalga_tipi", "Dalga tipi", wave),
        spec("tasima_agirligi", "Taşıma ağırlığı", load, "kg"),
        spec("gramaj", "Gramaj", gsm, "g/m²"),
        spec("paket_adedi", "Paket adedi", pack, "adet"),
        spec("kalite", "Kağıt kalitesi", "Kraft liner"),
    ]


def _single_wall(b: Builder) -> None:
    for size in _TOK_SIZES:
        volume_l = size[0] * size[1] * size[2] / 1000
        load = round(min(18.0, 4 + volume_l * 0.22))
        unit_price = _area_m2(size) * 26 + 1.8
        for pack, discount in ((25, 1.0), (100, 0.88)):
            b.add(
                Draft(
                    code="TOK",
                    title=f"Kutu&Co Tek Oluklu Koli {_dims(size)} cm ({pack}'li Paket)",
                    brand="Kutu&Co",
                    category="koli-tek-oluklu",
                    subcategory="Standart koli",
                    description=(
                        f"Tek oluklu (B dalga, 3 mm) kraft koli. Tekstil, kitap, kozmetik ve hafif e-ticaret ürünlerinin "
                        f"kargo gönderimi için ekonomik çözüm. İç ölçü {_dims(size)} cm, {load} kg'a kadar taşıma. "
                        f"Paket içinde {pack} adet, düz katlanmış teslim edilir."
                    ),
                    base_price=unit_price * pack * discount,
                    unit=f"paket ({pack} adet)",
                    specs=_box_specs(size, "B dalga (3 mm)", load, 420, pack),
                    tags=["koli", "tek-oluklu", "kargo"],
                    icon="box",
                    badge=f"{_dims(size)}",
                    doc_profile="box" if pack == 25 and size in _TOK_DOCS else None,
                    doc_priority=3 if pack == 25 and size in _TOK_DOCS else None,
                    popularity=2.0 if size in _TOK_DOCS else 1.0,
                )
            )
    for size in ((20, 15, 10), (30, 20, 15), (40, 30, 20), (40, 30, 30)):
        load = round(min(18.0, 5 + size[0] * size[1] * size[2] / 1000 * 0.22))
        b.add(
            Draft(
                code="TOK",
                title=f"Kutu&Co Kilitli Dipli Koli {_dims(size)} cm (50'li Paket)",
                brand="Kutu&Co",
                category="koli-tek-oluklu",
                subcategory="Kilitli dipli koli",
                description=(
                    f"Otomatik kilitli dipli tek oluklu koli; alt kısmı bant kullanmadan saniyeler içinde kurulur. "
                    f"Yoğun sipariş hazırlayan e-ticaret depoları için. İç ölçü {_dims(size)} cm, {load} kg'a kadar."
                ),
                base_price=(_area_m2(size) * 30 + 2.5) * 50,
                unit="paket (50 adet)",
                specs=_box_specs(size, "B dalga (3 mm)", load, 440, 50),
                tags=["koli", "tek-oluklu", "kilitli-dip", "kargo"],
                icon="box",
                badge=_dims(size),
                popularity=0.8,
            )
        )


def _double_wall(b: Builder) -> None:
    for i, size in enumerate(_COK_SIZES):
        volume_l = size[0] * size[1] * size[2] / 1000
        load = round(min(40.0, 12 + volume_l * 0.3))
        unit_price = _area_m2(size) * 52 + 3
        brand = "Kutu&Co" if i % 3 else "Oluklum"
        for pack, discount in ((10, 1.0), (50, 0.9)):
            b.add(
                Draft(
                    code="COK",
                    title=f"{brand} Çift Oluklu Koli {_dims(size)} cm ({pack}'lu Paket)",
                    brand=brand,
                    category="koli-cift-oluklu",
                    subcategory="Çift oluklu koli",
                    description=(
                        f"Çift oluklu (BC dalga, 7 mm) dayanıklı kraft koli. Seramik kupa, tabak, cam şişe ve kırılacak "
                        f"ürünlerin kargo gönderiminde yüksek darbe ve ezilme dayanımı sağlar; ağır ürünlerde güvenle "
                        f"kullanılır. İç ölçü {_dims(size)} cm, {load} kg'a kadar taşıma. Paket içinde {pack} adet."
                    ),
                    base_price=unit_price * pack * discount,
                    unit=f"paket ({pack} adet)",
                    specs=_box_specs(size, "BC dalga (7 mm)", load, 690, pack),
                    tags=["koli", "cift-oluklu", "kirilacak", "kargo"],
                    icon="box",
                    badge=_dims(size),
                    doc_profile="box" if pack == 10 and size in _COK_DOCS else None,
                    doc_priority=1 if pack == 10 and size in _COK_DOCS else None,
                    popularity=2.4 if size in _COK_DOCS else 1.1,
                )
            )


def _tapes(b: Builder) -> None:
    rows = [
        (
            "Şeffaf Akrilik Koli Bandı 45 mm x 100 m",
            "Genel amaçlı, sararmayan akrilik koli bandı; -10 °C'ye kadar yapışma.",
            44.0,
            ["koli-bandi", "akrilik"],
            True,
        ),
        (
            "Kahverengi Akrilik Koli Bandı 45 mm x 100 m",
            "Kraft kolilerle uyumlu kahverengi akrilik bant.",
            44.0,
            ["koli-bandi", "akrilik"],
            False,
        ),
        (
            "Sessiz Koli Bandı 48 mm x 66 m",
            "Açılırken ses çıkarmayan bant; ofis ve gece vardiyası paketleme için.",
            69.0,
            ["koli-bandi", "sessiz"],
            False,
        ),
        (
            "Hotmelt Şeffaf Koli Bandı 48 mm x 100 m",
            "Yüksek ilk yapışmalı hotmelt bant; ağır ve çift oluklu kolilerde güçlü kapama.",
            54.0,
            ["koli-bandi", "hotmelt"],
            True,
        ),
        (
            "Geniş Koli Bandı 72 mm x 100 m",
            "Büyük koliler ve palet ambalajı için geniş bant.",
            79.0,
            ["koli-bandi", "genis"],
            False,
        ),
        (
            "Kırılacak Eşya Baskılı Koli Bandı 45 mm x 100 m",
            "Kırmızı 'KIRILACAK EŞYA' baskılı uyarı bandı; seramik ve cam gönderileri için.",
            64.0,
            ["koli-bandi", "kirilacak", "baskili"],
            True,
        ),
        (
            "Kraft Kağıt Bant 50 mm x 50 m",
            "Plastiksiz, geri dönüştürülebilir kraft kağıt bant.",
            74.0,
            ["koli-bandi", "kraft"],
            False,
        ),
    ]
    for title, desc, base, tags, doc in rows:
        for pack, mult, unit in ((6, 6 * 0.95, "paket (6 rulo)"), (36, 36 * 0.82, "koli (36 rulo)")):
            b.add(
                Draft(
                    code="BNT",
                    title=f"Bantoloji {title} ({pack}'lı)",
                    brand="Bantoloji",
                    category="koli-bandi",
                    subcategory="Koli bandı",
                    description=f"{desc} {pack} rulo.",
                    base_price=base * mult,
                    unit=unit,
                    specs=[
                        spec(
                            "olcu",
                            "Ölçü",
                            title.split(" Bandı ")[-1] if " Bandı " in title else title.split(" Bant ")[-1],
                        ),
                        spec("yapiskan", "Yapışkan tipi", "Hotmelt" if "hotmelt" in tags else "Akrilik"),
                        spec("rulo_adedi", "Rulo adedi", pack, "adet"),
                    ],
                    tags=tags,
                    icon="tape",
                    badge=f"{pack} rulo",
                    doc_profile="tape" if doc and pack == 6 else None,
                    doc_priority=4 if doc and pack == 6 else None,
                    popularity=1.8 if "Şeffaf" in title else 1.0,
                )
            )
    for width, base in ((50, 189.0), (75, 289.0)):
        b.add(
            Draft(
                code="BNT",
                title=f"Bantoloji Bant Tabancası {width} mm",
                brand="Bantoloji",
                category="koli-bandi",
                subcategory="Bant tabancası",
                description=f"Fren ayarlı, tırtıklı bıçaklı koli bandı kesme tabancası ({width} mm'ye kadar bantlar). Paketlemeyi hızlandırır.",
                base_price=base,
                unit="adet",
                specs=[spec("genislik", "Bant genişliği", width, "mm")],
                tags=["bant-tabancasi"],
                icon="gun",
                badge=f"{width} mm",
                popularity=1.2,
            )
        )


def _stretch(b: Builder) -> None:
    rows = [
        (
            "El Streç Filmi 17 Mikron 50 cm 2,5 kg",
            "Palet ve koli gruplarını sabitlemek için şeffaf el streç filmi.",
            279.0,
            ["el-strec"],
            True,
            17,
        ),
        (
            "El Streç Filmi 23 Mikron 50 cm 3 kg",
            "Yüksek yırtılma dayanımlı, ağır yükler için el streç filmi.",
            339.0,
            ["el-strec"],
            True,
            23,
        ),
        (
            "Siyah El Streç Filmi 23 Mikron 50 cm 3 kg",
            "İçeriği gizleyen siyah streç film; değerli gönderiler için.",
            379.0,
            ["el-strec"],
            False,
            23,
        ),
    ]
    for title, desc, base, tags, doc, micron in rows:
        for pack, mult, unit in ((1, 1.0, "rulo"), (6, 6 * 0.9, "koli (6 rulo)")):
            b.add(
                Draft(
                    code="STR",
                    title=f"Gergin {title}" + (f" ({pack}'lı Koli)" if pack > 1 else ""),
                    brand="Gergin",
                    category="strec-film",
                    subcategory="El streci",
                    description=desc,
                    base_price=base * mult,
                    unit=unit,
                    specs=[
                        spec("kalinlik", "Kalınlık", micron, "mikron"),
                        spec("genislik", "Genişlik", 50, "cm"),
                        spec("rulo_adedi", "Rulo adedi", pack, "adet"),
                    ],
                    tags=["strec", *tags],
                    icon="film",
                    badge=f"{micron} µm",
                    doc_profile="stretch" if doc and pack == 1 else None,
                    doc_priority=6 if doc and pack == 1 else None,
                    popularity=1.2,
                )
            )
    for title, desc, base, tags, badge in (
        (
            "Makine Streç Filmi 23 Mikron 50 cm 16 kg",
            "Palet sarma makineleri için %150 ön gerdirmeli film.",
            1390.0,
            ["makine-strec"],
            "16 kg",
        ),
        (
            "Mini Streç Film 10 cm x 150 m",
            "Küçük paketler ve kablo demetleri için dar streç.",
            89.0,
            ["el-strec"],
            "10 cm",
        ),
        (
            "Streç Film Aparatı (El Tutacağı)",
            "Fren ayarlı el aparatı; eli yormadan hızlı palet sarma.",
            249.0,
            ["strec-aparati"],
            "Aparat",
        ),
    ):
        b.add(
            Draft(
                code="STR",
                title=f"Gergin {title}",
                brand="Gergin",
                category="strec-film",
                subcategory="Aparat"
                if "Aparat" in title
                else "Makine streci"
                if "Makine" in title
                else "El streci",
                description=desc,
                base_price=base,
                unit="adet",
                specs=[spec("ozellik", "Özellik", badge)],
                tags=["strec", *tags],
                icon="film",
                badge=badge,
                popularity=0.8,
            )
        )


def _bubble(b: Builder) -> None:
    for width in (50, 100, 120):
        for bubble, mm, mult in (("Küçük Kabarcık", 10, 1.0), ("Büyük Kabarcık", 30, 1.25)):
            b.add(
                Draft(
                    code="BAL",
                    title=f"Kabarcıkla Balonlu Naylon {width} cm x 50 m {bubble}",
                    brand="Kabarcıkla",
                    category="balonlu-naylon",
                    subcategory="Rulo",
                    description=(
                        f"{mm} mm kabarcıklı rulo balonlu naylon. Seramik, cam, porselen ve elektronik gibi kırılacak "
                        f"ürünleri sararak darbelere karşı korur. {width} cm x 50 m."
                    ),
                    base_price=width * 50 / 100 * 11 * mult,
                    unit="rulo",
                    specs=[
                        spec("genislik", "Genişlik", width, "cm"),
                        spec("uzunluk", "Uzunluk", 50, "m"),
                        spec("kabarcik", "Kabarcık çapı", mm, "mm"),
                        spec("kat", "Kat", "2 katlı"),
                    ],
                    tags=["balonlu", "rulo", "kirilacak"],
                    icon="bubble",
                    badge=f"{width} cm",
                    doc_profile="bubble" if width == 100 else None,
                    doc_priority=2 if width == 100 else None,
                    popularity=2.2 if width == 100 and mm == 10 else 1.2,
                )
            )
    b.add(
        Draft(
            code="BAL",
            title="Kabarcıkla 3 Katlı Balonlu Naylon 100 cm x 50 m",
            brand="Kabarcıkla",
            category="balonlu-naylon",
            subcategory="Rulo",
            description="Kabarcıkları patlamayan 3 katlı (ekstra dayanımlı) balonlu naylon; ağır ve hassas ürünler için.",
            base_price=749.0,
            unit="rulo",
            specs=[spec("genislik", "Genişlik", 100, "cm"), spec("kat", "Kat", "3 katlı")],
            tags=["balonlu", "rulo", "kirilacak"],
            icon="bubble",
            badge="3 kat",
            popularity=0.9,
        )
    )
    for size, base in (("15 x 21 cm", 229.0), ("22 x 28 cm", 299.0), ("30 x 40 cm", 449.0)):
        b.add(
            Draft(
                code="BAL",
                title=f"Kabarcıkla Balonlu Zarf {size} (100'lü)",
                brand="Kabarcıkla",
                category="balonlu-naylon",
                subcategory="Balonlu zarf",
                description=f"İçi balonlu kraft zarf {size}; takı, aksesuar ve küçük elektronik gönderileri.",
                base_price=base,
                unit="paket (100 adet)",
                specs=[spec("olcu", "Ölçü", size), spec("adet", "Adet", 100)],
                tags=["balonlu", "zarf"],
                icon="envelope",
                badge=size,
                popularity=1.0,
            )
        )
    for size, base in (("20 x 30 cm", 189.0), ("30 x 40 cm", 259.0)):
        b.add(
            Draft(
                code="BAL",
                title=f"Kabarcıkla Balonlu Poşet {size} (100'lü)",
                brand="Kabarcıkla",
                category="balonlu-naylon",
                subcategory="Balonlu poşet",
                description=f"Hazır balonlu poşet {size}; kupa, bardak ve şişeleri tek tek sarmadan korur.",
                base_price=base,
                unit="paket (100 adet)",
                specs=[spec("olcu", "Ölçü", size)],
                tags=["balonlu", "poset", "kirilacak"],
                icon="bubble",
                badge=size,
                popularity=0.9,
            )
        )


def _fill(b: Builder) -> None:
    rows = [
        (
            "Dolgu",
            "Kırpık Kağıt Dolgu 1 kg",
            "Koli içindeki boşlukları dolduran geri dönüştürülebilir kırpık kağıt.",
            129.0,
            ["dolgu", "kagit"],
            "1 kg",
        ),
        (
            "Dolgu",
            "Kırpık Kağıt Dolgu 5 kg",
            "Depo kullanımına uygun ekonomik kırpık kağıt.",
            499.0,
            ["dolgu", "kagit"],
            "5 kg",
        ),
        (
            "Dolgu",
            "Köpük Cips Dolgu 50 L",
            "Hafif, ürünü sarmalayan köpük cips (loose fill).",
            149.0,
            ["dolgu", "kopuk"],
            "50 L",
        ),
        (
            "Dolgu",
            "Köpük Cips Dolgu 150 L",
            "Büyük hacimli gönderiler için köpük cips.",
            349.0,
            ["dolgu", "kopuk"],
            "150 L",
        ),
        (
            "Dolgu",
            "Hava Yastığı Dolgu 20 x 10 cm (200'lü)",
            "Boşluk dolgusu için şişirilmiş hava yastıkları.",
            179.0,
            ["dolgu", "hava-yastigi"],
            "200'lü",
        ),
        (
            "Dolgu",
            "Kraft Dolgu Kağıdı 50 cm x 300 m",
            "Sarma ve boşluk doldurma için kraft kağıt rulo.",
            449.0,
            ["dolgu", "kagit"],
            "300 m",
        ),
        (
            "Köşe koruyucu",
            "Karton Köşe Koruyucu 35 x 35 x 1000 mm (50'li)",
            "Palet ve koli köşelerini ezilmeye karşı korur.",
            389.0,
            ["kose", "dolgu"],
            "50'li",
        ),
        (
            "Separatör",
            "Kupa ve Bardak Ayırıcı Separatör 6 Gözlü (25 set)",
            "Kupa, bardak ve şişeleri koli içinde ayrı gözlere yerleştiren karton separatör.",
            299.0,
            ["ayirici", "dolgu", "kirilacak"],
            "6 göz",
        ),
        (
            "Separatör",
            "Kupa ve Bardak Ayırıcı Separatör 12 Gözlü (25 set)",
            "12 gözlü karton separatör; toplu seramik gönderimi.",
            449.0,
            ["ayirici", "dolgu", "kirilacak"],
            "12 göz",
        ),
        (
            "Levha",
            "Köpük Levha 2 mm x 100 cm x 50 m",
            "Mobilya ve yüzey koruma için ince köpük levha.",
            329.0,
            ["dolgu", "kopuk"],
            "2 mm",
        ),
        (
            "Dolgu",
            "Petek Kağıt 50 cm x 100 m",
            "Plastiksiz, esnek petek kağıt sarma malzemesi.",
            549.0,
            ["dolgu", "kagit"],
            "100 m",
        ),
        (
            "Levha",
            "Ambalaj Kartonu Levha 100 x 70 cm (10'lu)",
            "Ara katman ve kutu içi bölme için oluklu levha.",
            199.0,
            ["levha"],
            "10'lu",
        ),
        (
            "Levha",
            "Ambalaj Kartonu Levha 100 x 70 cm (50'li)",
            "Depo için ekonomik oluklu levha paketi.",
            849.0,
            ["levha"],
            "50'li",
        ),
    ]
    for sub, title, desc, base, tags, badge in rows:
        b.add(
            Draft(
                code="DLG",
                title=f"Dolgu+ {title}",
                brand="Dolgu+",
                category="dolgu",
                subcategory=sub,
                description=desc,
                base_price=base,
                unit="paket",
                specs=[spec("icerik", "İçerik", badge)],
                tags=tags,
                icon="fill",
                badge=badge,
                popularity=1.3 if "ayirici" in tags else 0.9,
            )
        )


def _labels(b: Builder) -> None:
    rows = [
        (
            "Kargo etiketi",
            "Termal Kargo Etiketi 100 x 100 mm (500'lü)",
            "Termal yazıcılar için kargo barkod etiketi.",
            189.0,
            ["kargo", "termal"],
        ),
        (
            "Kargo etiketi",
            "Termal Kargo Etiketi 100 x 150 mm (500'lü)",
            "Pazaryeri kargo şablonlarına uygun termal etiket.",
            229.0,
            ["kargo", "termal"],
        ),
        (
            "Kargo etiketi",
            "A4 Adres Etiketi 2'li (100 Sayfa)",
            "Lazer ve mürekkep yazıcı için adres etiketi.",
            249.0,
            ["kargo", "a4"],
        ),
        (
            "Kargo etiketi",
            "A4 Adres Etiketi 8'li (100 Sayfa)",
            "Küçük paketler için 8'li adres etiketi.",
            249.0,
            ["kargo", "a4"],
        ),
        (
            "Uyarı etiketi",
            "Kırılacak Eşya Uyarı Etiketi (500'lü Rulo)",
            "Kırmızı 'KIRILACAK' uyarı etiketi; seramik ve cam koliler için.",
            149.0,
            ["kirilacak", "uyari"],
        ),
        (
            "Uyarı etiketi",
            "Bu Taraf Yukarı Etiketi (500'lü Rulo)",
            "Ok işaretli yön etiketi.",
            139.0,
            ["uyari"],
        ),
        (
            "Uyarı etiketi",
            "Dikkat Cam Etiketi (500'lü Rulo)",
            "Cam ve şişe gönderileri için uyarı etiketi.",
            139.0,
            ["kirilacak", "uyari"],
        ),
    ]
    for sub, title, desc, base, tags in rows:
        b.add(
            Draft(
                code="ETK",
                title=f"Etiketoz {title}",
                brand="Etiketoz",
                category="etiket",
                subcategory=sub,
                description=desc,
                base_price=base,
                unit="paket",
                specs=[spec("adet", "İçerik", title.split("(")[-1].rstrip(")"))],
                tags=["etiket", *tags],
                icon="label",
                badge="Etiket",
                popularity=1.0 if "kirilacak" in tags else 0.7,
            )
        )


def _envelopes(b: Builder) -> None:
    rows = [
        (
            "Kargo poşeti",
            "Kargo Poşeti 25 x 35 cm (100'lü)",
            "Yapışkan bantlı, darbe dayanımlı LDPE kargo poşeti.",
            149.0,
        ),
        ("Kargo poşeti", "Kargo Poşeti 35 x 45 cm (100'lü)", "Tekstil gönderileri için kargo poşeti.", 199.0),
        (
            "Kargo poşeti",
            "Kargo Poşeti 45 x 55 cm (100'lü)",
            "Büyük tekstil ürünleri için kargo poşeti.",
            269.0,
        ),
        (
            "Kargo poşeti",
            "Fatura Cepli Kargo Poşeti 30 x 40 cm (100'lü)",
            "Şeffaf fatura cepli kargo poşeti.",
            219.0,
        ),
        ("Zarf", "Kraft Zarf C4 (50'li)", "A4 evrak ve katalog gönderimi için kraft zarf.", 179.0),
        ("Zarf", "Kraft Zarf C5 (100'lü)", "A5 evrak için kraft zarf.", 159.0),
    ]
    for sub, title, desc, base in rows:
        b.add(
            Draft(
                code="ZRF",
                title=f"Kutu&Co {title}",
                brand="Kutu&Co",
                category="zarf-poset",
                subcategory=sub,
                description=desc,
                base_price=base,
                unit="paket",
                specs=[spec("olcu", "Ölçü", title.split(" (")[0].split(" ", 2)[-1])],
                tags=["poset" if sub == "Kargo poşeti" else "zarf", "kargo"],
                icon="envelope",
                badge="100'lü" if "100" in title else "50'li",
                popularity=0.9,
            )
        )
