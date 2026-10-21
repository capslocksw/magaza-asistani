"use client";

import { useEffect, useState } from "react";
import type { ProductSummary } from "@/lib/types";
import { searchProducts } from "@/lib/search";
import { AskAssistantButton } from "./ask-assistant-button";
import { ProductListing } from "./product-listing";

export function SearchResults() {
  const [query, setQuery] = useState<string | null>(null);
  const [results, setResults] = useState<ProductSummary[] | null>(null);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q") ?? "";
    setQuery(q);
    fetch("/search-index.json")
      .then((r) => r.json() as Promise<ProductSummary[]>)
      .then((index) => setResults(searchProducts(index, q)))
      .catch(() => setResults([]));
  }, []);

  if (query === null || results === null) return <p className="py-16 text-center text-muted">Aranıyor…</p>;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-extrabold">
        “{query}” için arama sonuçları
      </h1>
      {results.length ? (
        <ProductListing products={results} />
      ) : (
        <div className="rounded-2xl bg-brand-soft p-8 text-center">
          <p className="font-semibold text-brand-ink">Aramanızla eşleşen ürün bulamadık.</p>
          <p className="mt-1 text-sm text-brand-ink/90">Sorununuzu asistana anlatın, size uygun ürünleri bulsun.</p>
          <AskAssistantButton prompt={query} className="mt-4" variant="default" />
        </div>
      )}
    </div>
  );
}
