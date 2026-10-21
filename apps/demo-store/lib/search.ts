import type { ProductSummary } from "./types";
import { normalizeTr } from "./utils";

/** Scores products by how many query tokens appear (prefix match) in title/brand/category/tags. */
export function searchProducts(index: ProductSummary[], query: string): ProductSummary[] {
  const tokens = normalizeTr(query).split(" ").filter((t) => t.length > 1);
  if (!tokens.length) return [];
  const scored = index.flatMap((p) => {
    const haystack = normalizeTr(`${p.title} ${p.brand} ${p.category_name} ${p.subcategory ?? ""} ${p.tags.join(" ")}`).split(" ");
    let score = 0;
    for (const token of tokens) {
      const stem = token.length > 5 ? token.slice(0, token.length - 2) : token;
      if (haystack.some((w) => w.startsWith(stem))) score += 1;
    }
    return score ? [{ p, score }] : [];
  });
  return scored.sort((a, b) => b.score - a.score || (a.p.sales_rank ?? 1e9) - (b.p.sales_rank ?? 1e9)).map((s) => s.p);
}
