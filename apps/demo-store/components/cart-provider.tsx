"use client";

import { ADD_TO_CART_EVENT, type AddToCartDetail } from "@magaza/contracts";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { BRAND } from "@/lib/brand";
import type { CartItem } from "@/lib/types";

interface CartContextValue {
  items: CartItem[];
  count: number;
  total: number;
  open: boolean;
  toast: string | null;
  setOpen: (open: boolean) => void;
  add: (items: CartItem[], options?: { openSheet?: boolean; source?: string }) => void;
  setQty: (sku: string, qty: number) => void;
  remove: (sku: string) => void;
  clear: () => void;
}

const CartContext = createContext<CartContextValue | null>(null);
const STORAGE_KEY = `ma-demo-cart-${BRAND}`;

function merge(current: CartItem[], incoming: CartItem[]): CartItem[] {
  const next = current.map((item) => ({ ...item }));
  for (const item of incoming) {
    const existing = next.find((i) => i.sku === item.sku);
    if (existing) existing.qty += item.qty;
    else next.push({ ...item });
  }
  return next;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setItems(JSON.parse(raw) as CartItem[]);
    } catch {
      // Storage unavailable (private mode): start with an empty cart.
    }
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (!loaded) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      // Ignore persistence failures.
    }
  }, [items, loaded]);

  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(id);
  }, [toast]);

  const add = useCallback<CartContextValue["add"]>((incoming, options) => {
    setItems((current) => merge(current, incoming));
    const units = incoming.reduce((sum, i) => sum + i.qty, 0);
    setToast(options?.source === "assistant" ? `Asistan ${units} ürünü sepetinize ekledi` : "Ürün sepete eklendi");
    if (options?.openSheet) setOpen(true);
  }, []);

  // The assistant widget dispatches `ma:add-to-cart` on window; the storefront owns the cart.
  useEffect(() => {
    const onAdd = (event: Event) => {
      const detail = (event as CustomEvent<AddToCartDetail>).detail;
      if (!detail?.items?.length) return;
      add(
        detail.items.map((i) => ({ sku: i.sku, title: i.title, price: i.price, qty: i.qty, image_url: i.image_url, url: i.url })),
        { source: "assistant" },
      );
    };
    window.addEventListener(ADD_TO_CART_EVENT, onAdd);
    return () => window.removeEventListener(ADD_TO_CART_EVENT, onAdd);
  }, [add]);

  const value = useMemo<CartContextValue>(
    () => ({
      items,
      count: items.reduce((sum, i) => sum + i.qty, 0),
      total: Math.round(items.reduce((sum, i) => sum + i.qty * i.price, 0) * 100) / 100,
      open,
      toast,
      setOpen,
      add,
      setQty: (sku, qty) => setItems((cur) => cur.map((i) => (i.sku === sku ? { ...i, qty: Math.max(1, qty) } : i))),
      remove: (sku) => setItems((cur) => cur.filter((i) => i.sku !== sku)),
      clear: () => setItems([]),
    }),
    [items, open, toast, add],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used inside <CartProvider>");
  return ctx;
}
