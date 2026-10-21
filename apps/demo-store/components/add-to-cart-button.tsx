"use client";

import { Minus, Plus, ShoppingCart } from "lucide-react";
import { useState } from "react";
import type { ProductSummary } from "@/lib/types";
import { useCart } from "./cart-provider";
import { Button } from "./ui/button";

export function AddToCartButton({ product, compact = false }: { product: ProductSummary; compact?: boolean }) {
  const { add } = useCart();
  const [qty, setQty] = useState(1);
  const onAdd = () =>
    add([{ sku: product.sku, title: product.title, price: product.price, qty, image_url: product.image_url, url: product.url }], {
      openSheet: !compact,
    });

  if (compact) {
    return (
      <Button className="w-full" size="sm" onClick={onAdd} aria-label={`${product.title} sepete ekle`} data-testid="add-to-cart">
        <ShoppingCart aria-hidden="true" /> Sepete ekle
      </Button>
    );
  }
  return (
    <div className="flex gap-3">
      <div className="flex h-12 items-center rounded-lg border border-line" role="group" aria-label="Adet">
        <button
          type="button"
          className="grid size-12 place-items-center text-muted hover:text-ink"
          onClick={() => setQty((q) => Math.max(1, q - 1))}
          aria-label="Adedi azalt"
        >
          <Minus className="size-4" />
        </button>
        <span className="w-8 text-center font-semibold" aria-live="polite" data-testid="qty">
          {qty}
        </span>
        <button
          type="button"
          className="grid size-12 place-items-center text-muted hover:text-ink"
          onClick={() => setQty((q) => Math.min(99, q + 1))}
          aria-label="Adedi artır"
        >
          <Plus className="size-4" />
        </button>
      </div>
      <Button size="lg" className="flex-1" onClick={onAdd} data-testid="add-to-cart-main">
        <ShoppingCart aria-hidden="true" /> Sepete ekle
      </Button>
    </div>
  );
}
