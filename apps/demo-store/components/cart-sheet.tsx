"use client";

import { formatTRY } from "@magaza/contracts";
import { CheckCircle2, Minus, Plus, ShoppingBag, Trash2, Truck } from "lucide-react";
import Link from "next/link";
import { brandConfig } from "@/lib/brand";
import { useCart } from "./cart-provider";
import { Button } from "./ui/button";
import { Sheet, SheetContent } from "./ui/sheet";

export function CartSheet() {
  const { items, total, open, setOpen, setQty, remove } = useCart();
  const remaining = Math.max(0, brandConfig.freeShippingThreshold - total);
  const progress = Math.min(100, (total / brandConfig.freeShippingThreshold) * 100);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent title={`Sepetim (${items.length})`} description="Sepetinizdeki ürünler">
        {items.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center text-muted">
            <ShoppingBag className="size-12 text-gray-300" aria-hidden="true" />
            <p>Sepetiniz boş.</p>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Alışverişe devam et
            </Button>
          </div>
        ) : (
          <>
            <div className="border-b border-line bg-brand-soft/60 px-5 py-3 text-sm">
              {remaining > 0 ? (
                <p className="flex items-center gap-2 text-brand-ink">
                  <Truck className="size-4" aria-hidden="true" /> Ücretsiz kargo için <strong>{formatTRY(remaining)}</strong> daha ekleyin.
                </p>
              ) : (
                <p className="flex items-center gap-2 text-ok">
                  <CheckCircle2 className="size-4" aria-hidden="true" /> Kargo bedava!
                </p>
              )}
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white">
                <div className="h-full rounded-full bg-brand-strong" style={{ width: `${progress}%` }} />
              </div>
            </div>
            <ul className="flex-1 divide-y divide-line overflow-y-auto px-5" data-testid="cart-items">
              {items.map((item) => (
                <li key={item.sku} className="flex gap-3 py-4" data-testid="cart-item" data-sku={item.sku}>
                  <img src={item.image_url ?? ""} alt="" className="size-20 shrink-0 rounded-lg border border-line object-cover" />
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <Link href={item.url ?? "#"} className="line-clamp-2 text-sm font-medium hover:underline" onClick={() => setOpen(false)}>
                      {item.title}
                    </Link>
                    <p className="text-xs text-muted">{item.sku}</p>
                    <div className="mt-auto flex items-center justify-between">
                      <div className="flex items-center rounded-md border border-line">
                        <button className="grid size-8 place-items-center" onClick={() => setQty(item.sku, item.qty - 1)} aria-label="Azalt">
                          <Minus className="size-3.5" />
                        </button>
                        <span className="w-7 text-center text-sm font-semibold">{item.qty}</span>
                        <button className="grid size-8 place-items-center" onClick={() => setQty(item.sku, item.qty + 1)} aria-label="Artır">
                          <Plus className="size-3.5" />
                        </button>
                      </div>
                      <span className="font-bold">{formatTRY(item.price * item.qty)}</span>
                    </div>
                  </div>
                  <button className="self-start rounded p-1 text-muted hover:text-deal" onClick={() => remove(item.sku)} aria-label={`${item.title} sil`}>
                    <Trash2 className="size-4" />
                  </button>
                </li>
              ))}
            </ul>
            <div className="space-y-3 border-t border-line p-5">
              <div className="flex items-center justify-between text-base">
                <span className="text-muted">Toplam</span>
                <span className="text-xl font-bold" data-testid="cart-total">
                  {formatTRY(total)}
                </span>
              </div>
              <Button asChild size="lg" className="w-full">
                <Link href="/odeme/" onClick={() => setOpen(false)} data-testid="checkout-link">
                  Sepeti onayla
                </Link>
              </Button>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
