"""Demo tenant configuration: persona templates, tenant configs and complement rule tables.

Everything sector specific (persona text, topic taxonomy, complement rules) lives here as *data*;
the agent code never branches on the tenant's sector.
"""

from __future__ import annotations

from dataclasses import dataclass

from magaza_core.contracts import (
    CatalogSource,
    ComplementRule,
    PersonaSettings,
    PersonaTemplate,
    TenantActions,
    TenantConfig,
    TenantQuotas,
    TenantTheme,
    TopicDefinition,
)

TEKNIK_USTA = PersonaTemplate(
    template_id="teknik-usta",
    name="Teknik Usta",
    description="Yapı market müşterisinin sorununu bir usta gibi anlayıp uygulanabilir çözüm paketi önerir.",
    version=1,
    instruction="""Sen {{store_name}} adlı yapı marketin dijital ustası "{{assistant_name}}"sın. Müşterinin anlattığı sorunu bir usta gibi anla ve katalogdaki ürünlerle uygulanabilir bir çözüm paketi öner.

Nasıl çalışırsın:
1. Sorunu anla. Kritik bir bilgi eksikse (yüzey tipi, yük/ağırlık, ölçü, iç/dış mekan, elindeki aletler) tek seferde en fazla iki kısa netleştirici soru sor. Bilgi yeterliyse soru sormadan öner.
2. Ürünleri yalnızca araçlarla bul: search_products ile ara, gerekirse get_product ile ayrıntıya bak, get_complements ile tamamlayıcıları al.
3. Teknik iddiaları (taşıma kapasitesi, kuruma süresi, yüzey uyumu, uygulama adımları) search_knowledge ile teknik föyden doğrula. Föyde olmayan bir değeri uydurma; "föyde bu bilgi yok" de.
4. Ana ürün + 1-3 tamamlayıcıdan oluşan paketi propose_bundle ile oluştur ve kısa gerekçesini yaz.
5. Kısa, uygulanabilir adımlar ver (en fazla 5 madde).

Kurallar:
- Yalnızca bu konuşmada araçların döndürdüğü ürünleri öner; her ürünün adından sonra SKU'sunu parantez içinde yaz. Araçlardan gelmeyen SKU yazma.
- Stokta olmayan ürünü önerme; benzerini ara.
- Fiyatları ₺1.234,90 biçiminde yaz.
- Elektrik, gaz, yüksekte çalışma ve taşıyıcı duvar gibi risklerde güvenlik uyarısı yap, gerekirse profesyonel destek öner.
- Katalogda karşılığı olmayan taleplerde bunu açıkça söyle.
{{actions}}
Ton: {{tone_notes}}
{{extra_instructions}}""",
)

AMBALAJ_DANISMANI = PersonaTemplate(
    template_id="ambalaj-danismani",
    name="Ambalaj Danışmanı",
    description="B2B müşterisine gönderilecek ürüne göre koli, koruma ve kapama malzemesi seçtirir; toplu alımda teklif önerir.",
    version=1,
    instruction="""Sen {{store_name}} firmasının B2B ambalaj danışmanı "{{assistant_name}}"sın. Müşterinin göndereceği ürüne göre doğru koliyi, koruma malzemesini ve kapama ürünlerini seçmesine yardım edersin.

Nasıl çalışırsın:
1. Ürünü anla: ağırlık, ölçü, kırılganlık, adet ve gönderim sıklığı. Kritik bilgi eksikse en fazla iki kısa soru sor.
2. search_products ile koli ve malzemeleri bul. Kolinin taşıma ağırlığı ürün ağırlığının en az iki katı olmalı; kırılacak ürünlerde çift oluklu koli ve sarma malzemesi öner.
3. Teknik değerleri (taşıma ağırlığı, dalga tipi, bant özellikleri) search_knowledge ile teknik föyden doğrula; föyde yoksa uydurma.
4. get_complements ile bant, balonlu naylon, dolgu ve uyarı etiketi gibi tamamlayıcıları ekle; propose_bundle ile paket oluştur ve adetleri gönderim miktarına göre öner.

Kurallar:
- Yalnızca bu konuşmada araçların döndürdüğü ürünleri öner; her ürünün adından sonra SKU'sunu parantez içinde yaz. Araçlardan gelmeyen SKU yazma.
- Stokta olmayan ürünü önerme; benzerini ara.
- Fiyatları ₺1.234,90 biçiminde yaz; paket fiyatı ile adet fiyatını karıştırma.
{{actions}}
Ton: {{tone_notes}}
{{extra_instructions}}""",
)

PERSONA_TEMPLATES = [TEKNIK_USTA, AMBALAJ_DANISMANI]


@dataclass(frozen=True)
class TenantSpec:
    tenant_id: str
    prefix: str
    seed: int
    store_url: str
    doc_count: int


TENANT_SPECS: dict[str, TenantSpec] = {
    "yapi-market": TenantSpec("yapi-market", "YM", 20261021, "http://localhost:3101", 40),
    "ambalaj": TenantSpec("ambalaj", "KC", 20261022, "http://localhost:3102", 15),
}

_DEV_ORIGINS = ["http://localhost:5174", "http://127.0.0.1:5174"]


def tenant_config(tenant_id: str, data_dir: str = "data/demo") -> TenantConfig:
    spec = TENANT_SPECS[tenant_id]
    port = spec.store_url.rsplit(":", 1)[1]
    origins = [spec.store_url, f"http://127.0.0.1:{port}", *_DEV_ORIGINS]
    catalog = CatalogSource(
        type="merchant_feed",
        feed_url=f"{data_dir}/{tenant_id}/feed.xml",
        docs_url=f"{data_dir}/{tenant_id}/docs",
    )
    if tenant_id == "yapi-market":
        return TenantConfig(
            tenant_id="yapi-market",
            display_name="Yapıcı Market",
            status="active",
            public_key="pk_test_yapimarket",
            allowed_origins=origins,
            persona=PersonaSettings(
                template_id="teknik-usta",
                assistant_name="Usta",
                tone_notes="Samimi, pratik ve net; teknik terimleri gerektiğinde kısaca açıkla.",
                extra_instructions="",
                greeting="Merhaba, ben Usta! Ne tamir ediyoruz ya da yapıyoruz? Sorunu anlat, sana uygun malzemeleri birlikte seçelim.",
                suggested_questions=[
                    "Kornişim koptu, matkabım yok",
                    "Banyo derzleri karardı, nasıl yenilerim?",
                    "Salonu boyayacağım, neler lazım?",
                    "Damlatan musluğu nasıl tamir ederim?",
                ],
            ),
            theme=TenantTheme(
                primary_color="#E8590C",
                accent_color="#1F2937",
                text_on_primary="#FFFFFF",
                logo_url="/logo.svg",
                launcher_label="Ustaya sor",
                position="right",
            ),
            actions=TenantActions(add_to_cart=True, quote_request=False),
            catalog=catalog,
            quotas=TenantQuotas(
                monthly_messages=200_000, messages_per_session=40, requests_per_minute_per_visitor=12
            ),
            holdout_pct=10,
            sku_pattern=r"\bYM-[A-Z]{3}-[0-9]{4}\b",
            topic_taxonomy=[
                TopicDefinition(
                    topic_id="montaj_sabitleme",
                    label="Montaj ve sabitleme",
                    keywords=[
                        "korniş",
                        "kornis",
                        "raf",
                        "ayna",
                        "asmak",
                        "tablo",
                        "duvara",
                        "matkap",
                        "dübel",
                        "vida",
                        "montaj",
                    ],
                ),
                TopicDefinition(
                    topic_id="boya_badana",
                    label="Boya ve badana",
                    keywords=["boya", "badana", "astar", "rulo", "duvar rengi", "tavan", "fırça"],
                ),
                TopicDefinition(
                    topic_id="banyo_tesisat",
                    label="Banyo ve tesisat",
                    keywords=[
                        "derz",
                        "musluk",
                        "sifon",
                        "gider",
                        "kaçak",
                        "damlat",
                        "rezervuar",
                        "duş",
                        "küf",
                        "kireç",
                    ],
                ),
                TopicDefinition(
                    topic_id="yapistirma_onarim",
                    label="Yapıştırma ve onarım",
                    keywords=[
                        "yapıştır",
                        "kırıldı",
                        "kırık",
                        "çatlak",
                        "tamir",
                        "silikon",
                        "köpük",
                        "epoksi",
                    ],
                ),
                TopicDefinition(
                    topic_id="elektrikli_alet",
                    label="Elektrikli aletler",
                    keywords=[
                        "matkap",
                        "vidalama",
                        "şarjlı",
                        "akülü",
                        "taşlama",
                        "testere",
                        "zımpara makinesi",
                    ],
                ),
                TopicDefinition(
                    topic_id="hirdavat",
                    label="Hırdavat ve bağlantı",
                    keywords=["vida", "dübel", "çivi", "kanca", "menteşe", "kilit", "cıvata"],
                ),
            ],
        )
    return TenantConfig(
        tenant_id="ambalaj",
        display_name="Kutu&Co Ambalaj",
        status="active",
        public_key="pk_test_ambalaj",
        allowed_origins=origins,
        persona=PersonaSettings(
            template_id="ambalaj-danismani",
            assistant_name="Ambalaj Danışmanı",
            tone_notes="Profesyonel, çözüm odaklı ve kısa; B2B müşteriye sen yerine siz diye hitap et.",
            extra_instructions="Ücretsiz kargo eşiği 2.500 TL'dir; toplu alımlarda bunu hatırlat.",
            greeting="Merhaba, ne göndereceksiniz? Ürünün ağırlığını, ölçüsünü ve adedini söyleyin, doğru koli ve koruma malzemesini birlikte seçelim.",
            suggested_questions=[
                "2 kg seramik kupa göndereceğim, hangi koli?",
                "Paletimi nasıl sarmalıyım?",
                "Ayda 1000 koli gönderiyorum, teklif alabilir miyim?",
                "Tekstil ürünleri için en ekonomik ambalaj?",
            ],
        ),
        theme=TenantTheme(
            primary_color="#0F766E",
            accent_color="#B45309",
            text_on_primary="#FFFFFF",
            logo_url="/logo.svg",
            launcher_label="Danışmana sor",
            position="right",
        ),
        actions=TenantActions(add_to_cart=True, quote_request=True),
        catalog=catalog,
        quotas=TenantQuotas(
            monthly_messages=100_000, messages_per_session=60, requests_per_minute_per_visitor=12
        ),
        holdout_pct=10,
        sku_pattern=r"\bKC-[A-Z]{3}-[0-9]{4}\b",
        topic_taxonomy=[
            TopicDefinition(
                topic_id="kirilacak_urun",
                label="Kırılacak ürün gönderimi",
                keywords=["seramik", "cam", "kupa", "bardak", "porselen", "kırılacak", "şişe", "hassas"],
            ),
            TopicDefinition(
                topic_id="koli_secimi",
                label="Koli seçimi",
                keywords=["koli", "kutu", "ölçü", "boyut", "taşıma", "ağırlık"],
            ),
            TopicDefinition(
                topic_id="bantlama",
                label="Bantlama ve kapama",
                keywords=["bant", "koli bandı", "yapışmıyor", "tabanca"],
            ),
            TopicDefinition(
                topic_id="paletleme", label="Paletleme", keywords=["palet", "streç", "sarma", "köşe koruyucu"]
            ),
            TopicDefinition(
                topic_id="toplu_siparis",
                label="Toplu sipariş ve teklif",
                keywords=["teklif", "toplu", "adet", "fatura", "aylık", "düzenli", "kurumsal"],
            ),
            TopicDefinition(
                topic_id="kargo_poset_etiket",
                label="Kargo poşeti ve etiket",
                keywords=["poşet", "zarf", "etiket", "termal", "barkod", "tekstil"],
            ),
        ],
    )


def _rule(
    rule_id: str, src: str, src_tags: list[str], dst: str, dst_tags: list[str], reason: str, priority: int
) -> ComplementRule:
    return ComplementRule(
        rule_id=rule_id,
        source_category=src,
        source_tags=src_tags,
        target_category=dst,
        target_tags=dst_tags,
        reason=reason,
        priority=priority,
    )


COMPLEMENT_RULES: dict[str, list[ComplementRule]] = {
    "yapi-market": [
        _rule(
            "boya-astar-ic",
            "boya",
            ["ic-cephe"],
            "astar",
            ["su-bazli"],
            "Boyanın tutunması ve örtücülüğü için önce astar",
            1,
        ),
        _rule(
            "boya-astar-dis",
            "boya",
            ["dis-cephe"],
            "astar",
            ["dis-cephe"],
            "Dış cephede boya ömrünü uzatan astar",
            1,
        ),
        _rule(
            "boya-rulo-ic",
            "boya",
            ["ic-cephe", "tavan"],
            "boya-malzemeleri",
            ["rulo-ic-cephe"],
            "Geniş yüzeyde eşit uygulama",
            2,
        ),
        _rule(
            "boya-rulo-dis",
            "boya",
            ["dis-cephe"],
            "boya-malzemeleri",
            ["rulo-dis-cephe"],
            "Pürüzlü dış cephede eşit uygulama",
            2,
        ),
        _rule(
            "boya-bant",
            "boya",
            ["ic-cephe", "dis-cephe", "tavan"],
            "boya-malzemeleri",
            ["maskeleme-bandi"],
            "Temiz kenar ve köşeler",
            3,
        ),
        _rule(
            "boya-ortu",
            "boya",
            ["ic-cephe", "tavan"],
            "boya-malzemeleri",
            ["ortu"],
            "Zemini ve eşyaları korur",
            4,
        ),
        _rule(
            "yagli-firca",
            "boya",
            ["yagli-boya", "ahsap"],
            "boya-malzemeleri",
            ["firca"],
            "Detay ve kenar boyama",
            1,
        ),
        _rule("yagli-astar", "boya", ["yagli-boya"], "astar", ["metal"], "Metalde pas önleyici astar", 2),
        _rule("astar-rulo", "astar", [], "boya-malzemeleri", ["rulo"], "Astarı eşit dağıtır", 1),
        _rule("astar-boya", "astar", ["ic-cephe"], "boya", ["ic-cephe"], "Astar sonrası son kat boya", 2),
        _rule(
            "montaj-tabanca",
            "yapistirici-silikon",
            ["montaj-yapistiricisi"],
            "yapistirici-silikon",
            ["silikon-tabancasi"],
            "Kartuşu uygulamak için tabanca gerekir",
            1,
        ),
        _rule(
            "montaj-temizleyici",
            "yapistirici-silikon",
            ["montaj-yapistiricisi", "montaj-bandi"],
            "temizlik-yuzey",
            ["yuzey-temizleyici"],
            "Yapıştırma öncesi toz ve yağı alır, tutunmayı artırır",
            2,
        ),
        _rule(
            "montaj-bant",
            "yapistirici-silikon",
            ["montaj-yapistiricisi"],
            "boya-malzemeleri",
            ["maskeleme-bandi"],
            "Kuruma süresince parçayı sabitler",
            3,
        ),
        _rule(
            "silikon-tabanca",
            "yapistirici-silikon",
            ["silikon", "mastik"],
            "yapistirici-silikon",
            ["silikon-tabancasi"],
            "Kartuşu uygulamak için tabanca gerekir",
            1,
        ),
        _rule(
            "silikon-bant",
            "yapistirici-silikon",
            ["silikon"],
            "boya-malzemeleri",
            ["maskeleme-bandi"],
            "Düzgün silikon hattı",
            2,
        ),
        _rule(
            "silikon-siyirici",
            "yapistirici-silikon",
            ["silikon"],
            "el-aletleri",
            ["silikon-siyirici"],
            "Silikonu düzeltir, fazlasını alır",
            3,
        ),
        _rule(
            "silikon-sokucu",
            "yapistirici-silikon",
            ["silikon"],
            "temizlik-yuzey",
            ["silikon-sokucu"],
            "Eski silikonu söker",
            4,
        ),
        _rule(
            "kopuk-tabanca",
            "yapistirici-silikon",
            ["tabancali"],
            "yapistirici-silikon",
            ["kopuk-tabancasi"],
            "Tabancalı köpük için tabanca",
            1,
        ),
        _rule(
            "kopuk-eldiven",
            "yapistirici-silikon",
            ["poliuretan-kopuk"],
            "temizlik-yuzey",
            ["eldiven"],
            "Köpük cilde yapışır; eldiven kullanın",
            2,
        ),
        _rule(
            "kopuk-temizleyici",
            "yapistirici-silikon",
            ["poliuretan-kopuk"],
            "temizlik-yuzey",
            ["kopuk-temizleyici"],
            "Taze köpük artıklarını temizler",
            3,
        ),
        _rule(
            "onarim-temizleyici",
            "yapistirici-silikon",
            ["onarim", "tutkal"],
            "temizlik-yuzey",
            ["yuzey-temizleyici"],
            "Yapıştırılacak yüzeyi hazırlar",
            1,
        ),
        _rule(
            "matkap-uc",
            "elektrikli-aletler",
            ["matkap"],
            "elektrikli-aletler",
            ["matkap-ucu"],
            "Malzemeye uygun uç seti",
            1,
        ),
        _rule(
            "matkap-dubel",
            "elektrikli-aletler",
            ["matkap"],
            "hirdavat",
            ["dubel"],
            "Duvara montaj için dübel",
            2,
        ),
        _rule(
            "matkap-gozluk",
            "elektrikli-aletler",
            ["matkap", "taslama", "kirici"],
            "temizlik-yuzey",
            ["gozluk"],
            "Göz koruması",
            3,
        ),
        _rule(
            "kornis-dubel",
            "hirdavat",
            ["kornis", "raf"],
            "hirdavat",
            ["dubel"],
            "Braketi duvara sabitlemek için dübel",
            1,
        ),
        _rule(
            "kornis-uc",
            "hirdavat",
            ["kornis", "raf"],
            "elektrikli-aletler",
            ["matkap-ucu"],
            "Dübel deliği için beton ucu",
            2,
        ),
        _rule(
            "raf-terazi",
            "hirdavat",
            ["raf", "kornis"],
            "el-aletleri",
            ["su-terazisi"],
            "Düz montaj için su terazisi",
            3,
        ),
        _rule(
            "vida-tornavida",
            "hirdavat",
            ["vida"],
            "el-aletleri",
            ["tornavida"],
            "Vidalar için uygun tornavida",
            1,
        ),
        _rule("vida-dubel", "hirdavat", ["vida"], "hirdavat", ["dubel"], "Beton duvarda vida için dübel", 2),
        _rule(
            "kanca-temizleyici",
            "hirdavat",
            ["matkapsiz"],
            "temizlik-yuzey",
            ["yuzey-temizleyici"],
            "Yapışkanın tutunması için yüzey temizliği",
            1,
        ),
        _rule("cekic-civi", "el-aletleri", ["cekic"], "hirdavat", ["civi"], "Çakma işleri için çivi", 1),
        _rule(
            "derz-temizleyici",
            "banyo-tesisat",
            ["derz", "derz-yenileme"],
            "banyo-tesisat",
            ["derz-temizleyici"],
            "Yenilemeden önce derzdeki küf ve kiri çözer",
            1,
        ),
        _rule(
            "derz-kazima",
            "banyo-tesisat",
            ["derz"],
            "el-aletleri",
            ["derz-kazima"],
            "Eski derzi kazımak için",
            2,
        ),
        _rule(
            "derz-silikon",
            "banyo-tesisat",
            ["derz"],
            "yapistirici-silikon",
            ["banyo"],
            "Küvet ve lavabo birleşimlerinde silikon",
            3,
        ),
        _rule(
            "musluk-teflon",
            "banyo-tesisat",
            ["musluk", "batarya", "flex"],
            "banyo-tesisat",
            ["teflon"],
            "Dişli bağlantıda sızdırmazlık",
            1,
        ),
        _rule(
            "musluk-anahtar",
            "banyo-tesisat",
            ["musluk", "batarya", "sifon"],
            "el-aletleri",
            ["tesisat"],
            "Somunları sıkmak için ayarlı anahtar",
            2,
        ),
        _rule(
            "kuf-silikon",
            "banyo-tesisat",
            ["kuf"],
            "yapistirici-silikon",
            ["banyo"],
            "Küflenmiş silikonu yenilemek için",
            1,
        ),
        _rule(
            "rulo-tekne",
            "boya-malzemeleri",
            ["rulo"],
            "boya-malzemeleri",
            ["tekne"],
            "Rulo için sıyırma ızgaralı tekne",
            1,
        ),
        _rule(
            "rulo-sap",
            "boya-malzemeleri",
            ["rulo"],
            "boya-malzemeleri",
            ["rulo-sapi"],
            "Tavan ve yüksek duvarlar için uzatma sapı",
            2,
        ),
    ],
    "ambalaj": [
        _rule(
            "tok-bant", "koli-tek-oluklu", [], "koli-bandi", ["akrilik"], "Koliyi kapatmak için koli bandı", 1
        ),
        _rule("tok-dolgu", "koli-tek-oluklu", [], "dolgu", ["kagit"], "Koli içindeki boşluğu doldurur", 2),
        _rule("tok-etiket", "koli-tek-oluklu", [], "etiket", ["kargo"], "Kargo etiketi", 3),
        _rule(
            "cok-balonlu",
            "koli-cift-oluklu",
            [],
            "balonlu-naylon",
            ["rulo"],
            "Kırılacak ürünü tek tek sarar",
            1,
        ),
        _rule(
            "cok-bant", "koli-cift-oluklu", [], "koli-bandi", ["hotmelt"], "Ağır kolilerde güçlü kapama", 2
        ),
        _rule(
            "cok-ayirici",
            "koli-cift-oluklu",
            [],
            "dolgu",
            ["ayirici"],
            "Kupa ve bardakları ayrı gözlere yerleştirir",
            3,
        ),
        _rule("cok-etiket", "koli-cift-oluklu", [], "etiket", ["kirilacak"], "Kargo personelini uyarır", 4),
        _rule(
            "bant-tabanca",
            "koli-bandi",
            ["koli-bandi"],
            "koli-bandi",
            ["bant-tabancasi"],
            "Hızlı ve düzgün bantlama",
            1,
        ),
        _rule(
            "strec-aparat",
            "strec-film",
            ["el-strec"],
            "strec-film",
            ["strec-aparati"],
            "Eli yormadan sarma",
            1,
        ),
        _rule("strec-kose", "strec-film", [], "dolgu", ["kose"], "Palet köşelerini korur", 2),
        _rule(
            "balonlu-bant", "balonlu-naylon", ["rulo"], "koli-bandi", ["akrilik"], "Sarılan ürünü sabitler", 1
        ),
        _rule(
            "balonlu-koli",
            "balonlu-naylon",
            ["rulo", "poset"],
            "koli-cift-oluklu",
            [],
            "Sarılan kırılacak ürün için dayanıklı koli",
            2,
        ),
        _rule("zarf-etiket", "zarf-poset", [], "etiket", ["kargo"], "Kargo etiketi", 1),
        _rule(
            "ayirici-koli",
            "dolgu",
            ["ayirici"],
            "koli-cift-oluklu",
            [],
            "Separatör çift oluklu koliyle kullanılır",
            1,
        ),
    ],
}
