// Server-only catalog access for static generation. Reads data/demo/<BRAND>/ produced by `make data`.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Category, Product, ProductSummary, TenantConfig } from "./types";
import { BRAND } from "./brand";

const dataDir = join(process.cwd(), "..", "..", "data", "demo", BRAND);

function readJson<T>(name: string): T {
  return JSON.parse(readFileSync(join(dataDir, name), "utf8")) as T;
}

let cache: { products: Product[]; categories: Category[]; tenant: TenantConfig } | null = null;

function load() {
  cache ??= {
    products: readJson<Product[]>("catalog.json"),
    categories: readJson<Category[]>("categories.json"),
    tenant: readJson<TenantConfig>("tenant.json"),
  };
  return cache;
}

export function toSummary(p: Product): ProductSummary {
  return {
    sku: p.sku,
    title: p.title,
    brand: p.brand,
    category: p.category,
    category_name: p.category_name,
    subcategory: p.subcategory,
    tags: p.tags,
    price: p.price,
    list_price: p.list_price,
    stock: p.stock,
    image_url: p.image_url,
    url: p.url,
    rating: p.rating,
    review_count: p.review_count,
    sales_rank: p.sales_rank,
    max_installments: p.max_installments,
    free_shipping: p.free_shipping,
  };
}

export const getProducts = (): Product[] => load().products;
export const getCategories = (): Category[] => load().categories;
export const getTenant = (): TenantConfig => load().tenant;

export function getProduct(sku: string): Product | undefined {
  return load().products.find((p) => p.sku === sku);
}

export function getCategory(slug: string): Category | undefined {
  return load().categories.find((c) => c.slug === slug);
}

export function getCategoryProducts(slug: string): ProductSummary[] {
  return load()
    .products.filter((p) => p.category === slug)
    .map(toSummary);
}

export function getBestSellers(limit: number): ProductSummary[] {
  return [...load().products]
    .filter((p) => p.stock > 0)
    .sort((a, b) => (a.sales_rank ?? 1e9) - (b.sales_rank ?? 1e9))
    .slice(0, limit)
    .map(toSummary);
}

export function getDeals(limit: number): ProductSummary[] {
  return load()
    .products.filter((p) => p.list_price && p.stock > 0)
    .sort((a, b) => (b.list_price! - b.price) / b.list_price! - (a.list_price! - a.price) / a.list_price!)
    .slice(0, limit)
    .map(toSummary);
}

export function getComplements(product: Product): ProductSummary[] {
  const bySku = new Map(load().products.map((p) => [p.sku, p]));
  return product.complement_skus.flatMap((sku) => {
    const p = bySku.get(sku);
    return p ? [toSummary(p)] : [];
  });
}

export function getRelated(product: Product, limit: number): ProductSummary[] {
  const exclude = new Set([product.sku, ...product.complement_skus]);
  return load()
    .products.filter((p) => p.category === product.category && !exclude.has(p.sku))
    .sort((a, b) => Number(b.subcategory === product.subcategory) - Number(a.subcategory === product.subcategory) || (a.sales_rank ?? 1e9) - (b.sales_rank ?? 1e9))
    .slice(0, limit)
    .map(toSummary);
}
