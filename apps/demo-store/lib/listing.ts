import type { ProductSummary } from "./types";

export type SortKey = "recommended" | "bestseller" | "price-asc" | "price-desc" | "rating";


export function sortProducts(products: ProductSummary[], sort: SortKey): ProductSummary[] {
  const list = [...products];
  switch (sort) {
    case "bestseller":
      return list.sort((a, b) => (a.sales_rank ?? 1e9) - (b.sales_rank ?? 1e9));
    case "price-asc":
      return list.sort((a, b) => a.price - b.price);
    case "price-desc":
      return list.sort((a, b) => b.price - a.price);
    case "rating":
      return list.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
    default:
      return list.sort((a, b) => Number(b.stock > 0) - Number(a.stock > 0));
  }
}

export interface Filters {
  brands: string[];
  subcategories: string[];
  minPrice: number | null;
  maxPrice: number | null;
  inStockOnly: boolean;
}

export function applyFilters(products: ProductSummary[], f: Filters): ProductSummary[] {
  return products.filter(
    (p) =>
      (!f.brands.length || f.brands.includes(p.brand)) &&
      (!f.subcategories.length || (p.subcategory && f.subcategories.includes(p.subcategory))) &&
      (f.minPrice == null || p.price >= f.minPrice) &&
      (f.maxPrice == null || p.price <= f.maxPrice) &&
      (!f.inStockOnly || p.stock > 0),
  );
}
