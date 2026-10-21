import type { Product, TenantConfig } from "@magaza/contracts";

export type { Product, TenantConfig };

export interface Category {
  slug: string;
  name: string;
  icon: string;
  description: string;
  subcategories: string[];
  product_count: number;
}

/** Compact product shape used by listings, search and the cart. */
export type ProductSummary = Pick<
  Product,
  | "sku"
  | "title"
  | "brand"
  | "category"
  | "category_name"
  | "subcategory"
  | "tags"
  | "price"
  | "list_price"
  | "stock"
  | "image_url"
  | "url"
  | "rating"
  | "review_count"
  | "sales_rank"
  | "max_installments"
  | "free_shipping"
>;

export interface CartItem {
  sku: string;
  title: string;
  price: number;
  qty: number;
  image_url?: string | null;
  url?: string | null;
}
