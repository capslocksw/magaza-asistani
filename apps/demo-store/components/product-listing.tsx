"use client";

import { SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { applyFilters, sortProducts, type Filters, type SortKey } from "@/lib/listing";
import type { ProductSummary } from "@/lib/types";
import { ProductCard } from "./product-card";
import { Button } from "./ui/button";
import { Select } from "./ui/input";

const PAGE_SIZE = 24;

const SORTS: { key: SortKey; label: string }[] = [
  { key: "recommended", label: "Önerilen" },
  { key: "bestseller", label: "En çok satan" },
  { key: "price-asc", label: "Fiyat (artan)" },
  { key: "price-desc", label: "Fiyat (azalan)" },
  { key: "rating", label: "En yüksek puan" },
];


function Checkbox({ label, checked, onChange, count }: { label: string; checked: boolean; onChange: () => void; count: number }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 py-1 text-sm">
      <input type="checkbox" checked={checked} onChange={onChange} className="size-4 accent-[var(--brand-strong)]" />
      <span className="flex-1">{label}</span>
      <span className="text-xs text-muted">{count}</span>
    </label>
  );
}

export function ProductListing({ products, title, emptyText }: { products: ProductSummary[]; title?: string; emptyText?: string }) {
  const [sort, setSort] = useState<SortKey>("recommended");
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>({ brands: [], subcategories: [], minPrice: null, maxPrice: null, inStockOnly: false });

  const brands = useMemo(() => countBy(products, (p) => p.brand), [products]);
  const subcategories = useMemo(() => countBy(products, (p) => p.subcategory ?? ""), [products]);
  const filtered = useMemo(() => sortProducts(applyFilters(products, filters), sort), [products, filters, sort]);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const visible = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

  const update = (patch: Partial<Filters>) => {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  };
  const toggle = (key: "brands" | "subcategories", value: string) =>
    update({ [key]: filters[key].includes(value) ? filters[key].filter((v) => v !== value) : [...filters[key], value] });

  const filterPanel = (
    <div className="space-y-5">
      {subcategories.length > 1 ? (
        <fieldset>
          <legend className="mb-1 text-sm font-bold">Alt kategori</legend>
          {subcategories.map(([name, count]) => (
            <Checkbox key={name} label={name} count={count} checked={filters.subcategories.includes(name)} onChange={() => toggle("subcategories", name)} />
          ))}
        </fieldset>
      ) : null}
      <fieldset>
        <legend className="mb-1 text-sm font-bold">Marka</legend>
        {brands.map(([name, count]) => (
          <Checkbox key={name} label={name} count={count} checked={filters.brands.includes(name)} onChange={() => toggle("brands", name)} />
        ))}
      </fieldset>
      <fieldset>
        <legend className="mb-2 text-sm font-bold">Fiyat aralığı (₺)</legend>
        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor="min-price">
            En düşük fiyat
          </label>
          <input
            id="min-price"
            type="number"
            inputMode="numeric"
            placeholder="En az"
            className="h-9 w-full rounded-md border border-line px-2 text-sm"
            onChange={(e) => update({ minPrice: e.target.value ? Number(e.target.value) : null })}
          />
          <span aria-hidden="true">–</span>
          <label className="sr-only" htmlFor="max-price">
            En yüksek fiyat
          </label>
          <input
            id="max-price"
            type="number"
            inputMode="numeric"
            placeholder="En çok"
            className="h-9 w-full rounded-md border border-line px-2 text-sm"
            onChange={(e) => update({ maxPrice: e.target.value ? Number(e.target.value) : null })}
          />
        </div>
      </fieldset>
      <label className="flex cursor-pointer items-center gap-2 text-sm font-medium">
        <input type="checkbox" checked={filters.inStockOnly} onChange={() => update({ inStockOnly: !filters.inStockOnly })} className="size-4 accent-[var(--brand-strong)]" />
        Yalnızca stoktakiler
      </label>
    </div>
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
      <aside className="hidden lg:block" aria-label="Filtreler">
        {filterPanel}
      </aside>
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <p className="text-sm text-muted" aria-live="polite">
            {title ? <strong className="text-ink">{title}</strong> : null} <span data-testid="result-count">{filtered.length}</span> ürün
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="lg:hidden" onClick={() => setShowFilters((s) => !s)} aria-expanded={showFilters}>
              <SlidersHorizontal aria-hidden="true" /> Filtrele
            </Button>
            <label htmlFor="sort" className="sr-only">
              Sırala
            </label>
            <Select id="sort" value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className="h-9 w-44">
              {SORTS.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.label}
                </option>
              ))}
            </Select>
          </div>
        </div>
        {showFilters ? <div className="border-b border-line py-4 lg:hidden">{filterPanel}</div> : null}
        <h2 className="sr-only">Ürünler</h2>
        {visible.length ? (
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
            {visible.map((p, i) => (
              <ProductCard key={p.sku} product={p} priority={i < 4} />
            ))}
          </div>
        ) : (
          <p className="py-16 text-center text-muted">{emptyText ?? "Filtrelere uygun ürün bulunamadı."}</p>
        )}
        {pages > 1 ? (
          <nav className="mt-8 flex justify-center gap-1" aria-label="Sayfalama">
            {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => {
                  setPage(n);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                aria-current={n === current ? "page" : undefined}
                className={`size-10 rounded-lg text-sm font-semibold ${n === current ? "bg-brand-strong text-white" : "border border-line hover:bg-surface"}`}
              >
                {n}
              </button>
            ))}
          </nav>
        ) : null}
      </div>
    </div>
  );
}

function countBy(products: ProductSummary[], key: (p: ProductSummary) => string): [string, number][] {
  const map = new Map<string, number>();
  for (const p of products) {
    const k = key(p);
    if (k) map.set(k, (map.get(k) ?? 0) + 1);
  }
  return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0], "tr"));
}
