import { describe, expect, it } from "vitest";
import { applyFilters, sortProducts } from "../lib/listing";
import { searchProducts } from "../lib/search";
import type { ProductSummary } from "../lib/types";
import { discountPercent, installmentText, normalizeTr } from "../lib/utils";

const p = (over: Partial<ProductSummary>): ProductSummary => ({
  sku: "YM-YAP-0001",
  title: "Tutkan Montaj Yapıştırıcısı 290 ml",
  brand: "Tutkan",
  category: "yapistirici-silikon",
  category_name: "Yapıştırıcı ve Silikon",
  subcategory: "Montaj yapıştırıcısı",
  tags: ["montaj-yapistiricisi", "kornis"],
  price: 199.9,
  list_price: null,
  stock: 10,
  image_url: "/images/YM-YAP-0001.svg",
  url: "/urun/YM-YAP-0001/",
  rating: 4.5,
  review_count: 10,
  sales_rank: 5,
  max_installments: 3,
  free_shipping: false,
  ...over,
});

const catalog = [
  p({}),
  p({ sku: "YM-YAP-0043", title: "Ustakit Silikon Tabancası Standart Metal", brand: "Ustakit", price: 119.9, sales_rank: 2, tags: ["silikon-tabancasi"], subcategory: "Tabanca" }),
  p({ sku: "YM-BOY-0001", title: "Renkpark Silikonlu İç Cephe Boyası Kar Beyazı 2,5 L", brand: "Renkpark", category: "boya", price: 639.9, sales_rank: 1, stock: 0, tags: ["ic-cephe"] }),
];

describe("normalizeTr", () => {
  it("folds Turkish characters and case", () => {
    expect(normalizeTr("KORNİŞ Şeffaf Çiçek")).toBe("kornis seffaf cicek");
  });
});

describe("search", () => {
  it("matches Turkish words without diacritics and stems inflections", () => {
    expect(searchProducts(catalog, "kornişim").map((x) => x.sku)).toEqual(["YM-YAP-0001"]);
    expect(searchProducts(catalog, "silikon tabancasi")[0]!.sku).toBe("YM-YAP-0043");
    expect(searchProducts(catalog, "")).toEqual([]);
  });
});

describe("listing", () => {
  it("sorts by price and sales rank", () => {
    expect(sortProducts(catalog, "price-asc").map((x) => x.price)).toEqual([119.9, 199.9, 639.9]);
    expect(sortProducts(catalog, "bestseller")[0]!.sku).toBe("YM-BOY-0001");
    expect(sortProducts(catalog, "recommended").at(-1)!.stock).toBe(0);
  });

  it("filters by brand, price and stock", () => {
    const base = { brands: [], subcategories: [], minPrice: null, maxPrice: null, inStockOnly: false };
    expect(applyFilters(catalog, { ...base, brands: ["Ustakit"] })).toHaveLength(1);
    expect(applyFilters(catalog, { ...base, minPrice: 150, maxPrice: 300 })).toHaveLength(1);
    expect(applyFilters(catalog, { ...base, inStockOnly: true })).toHaveLength(2);
  });
});

describe("price helpers", () => {
  it("computes discount and installment text", () => {
    expect(discountPercent(80, 100)).toBe(20);
    expect(discountPercent(100, null)).toBeNull();
    expect(installmentText(9)).toBe("9 aya varan taksit");
    expect(installmentText(1)).toBeNull();
  });
});
