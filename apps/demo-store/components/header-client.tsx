"use client";

import { ChevronRight, Menu, Search, ShoppingCart } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { brandConfig } from "@/lib/brand";
import type { Category } from "@/lib/types";
import { useCart } from "./cart-provider";
import { Sheet, SheetContent } from "./ui/sheet";

export function SearchBox() {
  const [value, setValue] = useState("");
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q && window.location.pathname.startsWith("/ara")) setValue(q);
  }, []);
  return (
    <form action="/ara/" method="get" role="search" className="relative">
      <label htmlFor="site-search" className="sr-only">
        Ürün ara
      </label>
      <input
        id="site-search"
        name="q"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={brandConfig.b2b ? "Koli ölçüsü, bant, streç film ara…" : "Ürün, marka veya kategori ara (ör. silikon, korniş)"}
        className="h-11 w-full rounded-lg border-2 border-brand-strong/80 bg-white pl-4 pr-12 text-sm placeholder:text-gray-500 focus:border-brand-strong focus:outline-none"
        autoComplete="off"
      />
      <button
        type="submit"
        className="absolute right-1 top-1 grid h-9 w-10 place-items-center rounded-md bg-brand-strong text-white"
        aria-label="Ara"
      >
        <Search className="size-4" />
      </button>
    </form>
  );
}

export function CartButton() {
  const { count, setOpen, toast } = useCart();
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="relative flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold hover:bg-surface"
        aria-label={`Sepetim, ${count} ürün`}
        data-testid="cart-button"
      >
        <span className="relative">
          <ShoppingCart className="size-5" aria-hidden="true" />
          <span
            className="absolute -right-2.5 -top-2.5 grid min-w-5 place-items-center rounded-full bg-brand-strong px-1 text-[11px] font-bold leading-5 text-white ring-2 ring-white"
            data-testid="cart-count"
          >
            {count}
          </span>
        </span>
        <span className="hidden sm:inline">Sepetim</span>
      </button>
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 top-20 z-[60] flex justify-center px-4">
        {toast ? (
          <p className="rounded-full bg-chrome px-4 py-2 text-sm font-medium text-white shadow-lg" data-testid="cart-toast">
            {toast}
          </p>
        ) : null}
      </div>
    </>
  );
}

export function MobileMenu({ categories }: { categories: Category[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <button type="button" className="rounded-md p-2 hover:bg-surface md:hidden" aria-label="Menüyü aç" onClick={() => setOpen(true)}>
        <Menu className="size-6" />
      </button>
      <SheetContent title="Kategoriler" className="left-0 right-auto">
        <ul className="divide-y divide-line overflow-y-auto">
          {categories.map((c) => (
            <li key={c.slug}>
              <Link
                href={`/kategori/${c.slug}/`}
                onClick={() => setOpen(false)}
                className="flex items-center justify-between px-5 py-3.5 font-medium"
              >
                <span className="flex items-center gap-3">
                  <img src={`/images/cat-${c.slug}.svg`} alt="" className="size-8" />
                  {c.name}
                </span>
                <ChevronRight className="size-4 text-muted" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      </SheetContent>
    </Sheet>
  );
}
