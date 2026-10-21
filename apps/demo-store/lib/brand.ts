// Storefront presentation per demo brand (storefront content, not assistant logic).
export type BrandId = "yapi-market" | "ambalaj";

export const BRAND: BrandId = process.env.NEXT_PUBLIC_BRAND === "ambalaj" ? "ambalaj" : "yapi-market";

export interface BrandConfig {
  name: string;
  shortName: string;
  tagline: string;
  publicKey: string;
  supportPhone: string;
  freeShippingThreshold: number;
  b2b: boolean;
  topBar: string;
  hero: { eyebrow: string; title: string; subtitle: string; cta: string; secondary: string; secondaryHref: string };
  campaigns: { title: string; text: string; href: string; tone: "brand" | "dark" | "soft" }[];
  trust: string[];
  assistantName: string;
  askLabel: string;
  assistantPrompt: string;
}

export const BRANDS: Record<BrandId, BrandConfig> = {
  "yapi-market": {
    name: "Yapıcı Market",
    shortName: "Yapıcı",
    tagline: "Usta işi malzeme, kapında.",
    publicKey: "pk_test_yapimarket",
    supportPhone: "0850 000 12 34",
    freeShippingThreshold: 500,
    b2b: false,
    topBar: "500 TL ve üzeri siparişlerde kargo bedava · 15:00'e kadar verilen siparişler aynı gün kargoda",
    hero: {
      eyebrow: "Yeni: Ustaya sor",
      title: "Evdeki her tamir için doğru malzeme",
      subtitle:
        "Boyadan hırdavata 300'den fazla ürün. Ne alacağını bilmiyorsan Usta'ya sorununu anlat; ihtiyacın olan paketi saniyeler içinde hazırlasın.",
      cta: "Ustaya sorununu anlat",
      secondary: "Boya ürünlerini incele",
      secondaryHref: "/kategori/boya/",
    },
    campaigns: [
      { title: "Boyada %25'e varan indirim", text: "İç cephe boyaları ve astarlar", href: "/kategori/boya/", tone: "brand" },
      { title: "Matkapsız montaj", text: "Korniş, ayna ve raf için yapıştırıcılar", href: "/kategori/yapistirici-silikon/", tone: "dark" },
      { title: "12 aya varan taksit", text: "Akülü vidalama ve matkaplarda", href: "/kategori/elektrikli-aletler/", tone: "soft" },
    ],
    trust: ["500 TL üzeri ücretsiz kargo", "Aynı gün kargo", "12 aya varan taksit", "14 gün koşulsuz iade"],
    assistantName: "Usta",
    askLabel: "Usta'ya sor",
    assistantPrompt: "Kornişim koptu, matkabım yok",
  },
  ambalaj: {
    name: "Kutu&Co Ambalaj",
    shortName: "Kutu&Co",
    tagline: "İşletmenizin ambalaj tedarikçisi",
    publicKey: "pk_test_ambalaj",
    supportPhone: "0850 000 56 78",
    freeShippingThreshold: 2500,
    b2b: true,
    topBar: "Kurumsal fatura · 2.500 TL üzeri ücretsiz sevkiyat · Toplu alımlarda özel teklif",
    hero: {
      eyebrow: "B2B ambalaj danışmanı",
      title: "Ürününüz güvenle, ambalajınız doğru ölçüde",
      subtitle:
        "Koli, bant, streç ve koruma malzemelerinde 120'den fazla ürün. Ne göndereceğinizi anlatın; danışmanımız koli ölçüsünden dolguya kadar paketi önersin.",
      cta: "Danışmana ne göndereceğinizi yazın",
      secondary: "Çift oluklu koliler",
      secondaryHref: "/kategori/koli-cift-oluklu/",
    },
    campaigns: [
      { title: "Çift oluklu kolilerde 50'li paket avantajı", text: "Kırılacak ürünler için BC dalga", href: "/kategori/koli-cift-oluklu/", tone: "brand" },
      { title: "Koli bandı koli fiyatına", text: "36'lı kolilerde birim fiyat düşer", href: "/kategori/koli-bandi/", tone: "dark" },
      { title: "Toplu alımda teklif", text: "Aylık düzenli siparişlere özel fiyat", href: "/kategori/koli-tek-oluklu/", tone: "soft" },
    ],
    trust: ["Kurumsal fatura", "2.500 TL üzeri ücretsiz sevkiyat", "Aynı gün sevkiyat", "Toplu alımda teklif"],
    assistantName: "Ambalaj Danışmanı",
    askLabel: "Danışmana sor",
    assistantPrompt: "2 kg seramik kupa göndereceğim, hangi koli?",
  },
};

export const brandConfig: BrandConfig = BRANDS[BRAND];

export const WIDGET_URL = process.env.NEXT_PUBLIC_WIDGET_URL || "http://localhost:5174/widget.js";
export const AGENT_URL = process.env.NEXT_PUBLIC_AGENT_URL || "http://localhost:8787";
