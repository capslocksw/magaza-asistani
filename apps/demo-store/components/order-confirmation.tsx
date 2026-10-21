"use client";

import { formatTRY, type Order } from "@magaza/contracts";
import { CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { LAST_ORDER_KEY } from "./checkout-form";
import { Button } from "./ui/button";

export function OrderConfirmation() {
  const [order, setOrder] = useState<Order | null>(null);
  const [tracked, setTracked] = useState(false);

  useEffect(() => {
    const raw = window.sessionStorage.getItem(LAST_ORDER_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as Order;
    setOrder(parsed);
    // Conversion attribution: hand the order to the widget exactly once, also across refreshes.
    const trackedKey = `ma-demo-tracked:${parsed.order_id}`;
    if (window.sessionStorage.getItem(trackedKey)) {
      setTracked(true);
      return;
    }
    let done = false;
    const tryTrack = () => {
      if (done || !window.MagazaAsistani) return done;
      done = true;
      window.MagazaAsistani.trackOrder(parsed);
      window.sessionStorage.setItem(trackedKey, "1");
      setTracked(true);
      return true;
    };
    if (tryTrack()) return;
    let attempts = 0;
    const id = window.setInterval(() => {
      attempts += 1;
      if (tryTrack() || attempts > 40) window.clearInterval(id);
    }, 250);
    return () => window.clearInterval(id);
  }, []);

  if (!order) {
    return <p className="py-16 text-center text-muted">Görüntülenecek sipariş bulunamadı.</p>;
  }

  return (
    <div className="mx-auto max-w-2xl rounded-2xl border border-line p-8 text-center" data-testid="order-confirmation" data-tracked={tracked}>
      <CheckCircle2 className="mx-auto size-14 text-ok" aria-hidden="true" />
      <h1 className="mt-4 text-2xl font-extrabold">Siparişiniz alındı!</h1>
      <p className="mt-2 text-muted">
        Sipariş numaranız <strong className="text-ink" data-testid="order-id">{order.order_id}</strong>. Onay e-postası (demo) gönderildi.
      </p>
      <ul className="mt-6 divide-y divide-line rounded-xl border border-line text-left text-sm">
        {order.items.map((i) => (
          <li key={i.sku} className="flex justify-between gap-3 px-4 py-2.5">
            <span>
              {i.qty} × {i.title ?? i.sku}
            </span>
            <span className="font-semibold">{formatTRY(i.price * i.qty)}</span>
          </li>
        ))}
        <li className="flex justify-between px-4 py-3 text-base font-bold">
          <span>Toplam</span>
          <span>{formatTRY(order.total)}</span>
        </li>
      </ul>
      <Button asChild className="mt-6">
        <Link href="/">Alışverişe devam et</Link>
      </Button>
    </div>
  );
}
