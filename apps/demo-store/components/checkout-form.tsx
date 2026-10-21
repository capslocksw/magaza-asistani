"use client";

import { formatTRY, type Order } from "@magaza/contracts";
import { Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { brandConfig } from "@/lib/brand";
import { useCart } from "./cart-provider";
import { Button } from "./ui/button";
import { Field, Input, Select } from "./ui/input";

export const LAST_ORDER_KEY = "ma-demo-last-order";
const CITIES = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Konya", "Kocaeli", "Gaziantep"];

export function CheckoutForm() {
  const { items, total, clear } = useCart();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const shipping = total >= brandConfig.freeShippingThreshold || total === 0 ? 0 : 89.9;
  const grandTotal = Math.round((total + shipping) * 100) / 100;

  if (!items.length) {
    return (
      <div className="rounded-2xl border border-line p-10 text-center">
        <p className="font-semibold">Sepetiniz boş.</p>
        <Button asChild className="mt-4">
          <Link href="/">Alışverişe başla</Link>
        </Button>
      </div>
    );
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    const order: Order = {
      order_id: `ORD-${Date.now().toString(36).toUpperCase()}`,
      items: items.map((i) => ({ sku: i.sku, qty: i.qty, price: i.price, title: i.title })) as Order["items"],
      total: grandTotal,
      currency: "TRY",
    };
    window.sessionStorage.setItem(LAST_ORDER_KEY, JSON.stringify(order));
    clear();
    router.push("/siparis-onay/");
  };

  return (
    <form onSubmit={onSubmit} className="grid gap-8 lg:grid-cols-[1fr_380px]" aria-label="Ödeme formu">
      <div className="space-y-6">
        <section className="space-y-4 rounded-2xl border border-line p-5">
          <h2 className="text-lg font-bold">Teslimat bilgileri</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Ad soyad" htmlFor="name">
              <Input id="name" name="name" required autoComplete="name" />
            </Field>
            <Field label="Telefon" htmlFor="phone">
              <Input id="phone" name="phone" type="tel" required autoComplete="tel" placeholder="05xx xxx xx xx" />
            </Field>
            <Field label="E-posta" htmlFor="email">
              <Input id="email" name="email" type="email" required autoComplete="email" />
            </Field>
            <Field label="İl" htmlFor="city">
              <Select id="city" name="city" required defaultValue="İstanbul">
                {CITIES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </Select>
            </Field>
            {brandConfig.b2b ? (
              <>
                <Field label="Firma adı" htmlFor="company">
                  <Input id="company" name="company" autoComplete="organization" />
                </Field>
                <Field label="Vergi dairesi / no" htmlFor="tax">
                  <Input id="tax" name="tax" />
                </Field>
              </>
            ) : null}
          </div>
          <Field label="Adres" htmlFor="address">
            <textarea
              id="address"
              name="address"
              required
              rows={3}
              autoComplete="street-address"
              className="w-full rounded-lg border border-line px-3 py-2 text-sm focus:border-brand-strong focus:outline-none focus:ring-2 focus:ring-brand-soft"
            />
          </Field>
        </section>
        <section className="space-y-3 rounded-2xl border border-line p-5">
          <h2 className="text-lg font-bold">Ödeme</h2>
          <fieldset className="space-y-2">
            <legend className="sr-only">Ödeme yöntemi</legend>
            {["Kredi / banka kartı (demo — kart bilgisi alınmaz)", "Havale / EFT (demo)"].map((label, i) => (
              <label key={label} className="flex cursor-pointer items-center gap-3 rounded-lg border border-line p-3 text-sm has-[:checked]:border-brand-strong has-[:checked]:bg-brand-soft">
                <input type="radio" name="payment" value={i} defaultChecked={i === 0} className="accent-[var(--brand-strong)]" />
                {label}
              </label>
            ))}
          </fieldset>
          <p className="flex items-center gap-2 text-xs text-muted">
            <Lock className="size-3.5" aria-hidden="true" /> Bu bir demo mağazadır; gerçek ödeme alınmaz.
          </p>
        </section>
      </div>
      <aside className="h-fit space-y-4 rounded-2xl border border-line bg-surface p-5 lg:sticky lg:top-40">
        <h2 className="text-lg font-bold">Sipariş özeti</h2>
        <ul className="space-y-2 text-sm">
          {items.map((i) => (
            <li key={i.sku} className="flex justify-between gap-3">
              <span className="line-clamp-2">
                {i.qty} × {i.title}
              </span>
              <span className="shrink-0 font-semibold">{formatTRY(i.price * i.qty)}</span>
            </li>
          ))}
        </ul>
        <dl className="space-y-1 border-t border-line pt-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted">Ara toplam</dt>
            <dd>{formatTRY(total)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Kargo</dt>
            <dd>{shipping ? formatTRY(shipping) : "Ücretsiz"}</dd>
          </div>
          <div className="flex justify-between pt-2 text-lg font-bold">
            <dt>Toplam</dt>
            <dd data-testid="checkout-total">{formatTRY(grandTotal)}</dd>
          </div>
        </dl>
        <Button type="submit" size="lg" className="w-full" disabled={submitting} data-testid="place-order">
          Siparişi tamamla
        </Button>
      </aside>
    </form>
  );
}
