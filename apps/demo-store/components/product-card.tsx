import Link from "next/link";
import { Truck } from "lucide-react";
import type { ProductSummary } from "@/lib/types";
import { discountPercent, installmentText } from "@/lib/utils";
import { AddToCartButton } from "./add-to-cart-button";
import { Price, Rating } from "./price";
import { Badge } from "./ui/badge";

export function ProductCard({ product, priority = false }: { product: ProductSummary; priority?: boolean }) {
  const pct = discountPercent(product.price, product.list_price);
  const inStock = product.stock > 0;
  return (
    <article
      className="group relative flex flex-col overflow-hidden rounded-xl border border-line bg-white transition-shadow hover:shadow-lg"
      data-testid="product-card"
      data-sku={product.sku}
    >
      <Link href={product.url} className="relative block aspect-square overflow-hidden bg-surface">
        <img
          src={product.image_url}
          alt={product.title}
          loading={priority ? "eager" : "lazy"}
          className="size-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
        />
        <div className="absolute left-2 top-2 flex flex-col items-start gap-1">
          {pct ? <Badge variant="deal">%{pct} indirim</Badge> : null}
          {product.free_shipping ? (
            <Badge variant="ok">
              <Truck className="size-3" aria-hidden="true" /> Kargo bedava
            </Badge>
          ) : null}
        </div>
      </Link>
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        <p className="text-[11px] font-bold uppercase tracking-wide text-brand-strong">{product.brand}</p>
        <h3 className="line-clamp-2 min-h-10 text-sm font-medium leading-5 text-ink">
          <Link href={product.url} className="after:absolute after:inset-0 after:content-['']">
            {product.title}
          </Link>
        </h3>
        <Rating rating={product.rating} count={product.review_count} />
        <div className="mt-auto pt-1">
          <Price price={product.price} listPrice={product.list_price} size="sm" />
          <p className="min-h-4 text-[11px] text-muted">{installmentText(product.max_installments) ?? " "}</p>
        </div>
        <div className="relative z-10 pt-1">
          {inStock ? (
            <AddToCartButton product={product} compact />
          ) : (
            <p className="rounded-lg bg-surface py-2 text-center text-xs font-semibold text-muted">Stokta yok</p>
          )}
        </div>
      </div>
    </article>
  );
}

export function ProductGrid({ products, className }: { products: ProductSummary[]; className?: string }) {
  return (
    <div className={className ?? "grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"}>
      {products.map((p, i) => (
        <ProductCard key={p.sku} product={p} priority={i < 4} />
      ))}
    </div>
  );
}
