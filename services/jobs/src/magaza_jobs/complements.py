"""Resolve category-level complement rules into per-product complement SKUs."""

from __future__ import annotations

from collections import defaultdict

from magaza_core.contracts import ComplementRule, Product

MAX_COMPLEMENTS = 4


def _rank(product: Product) -> int:
    return product.sales_rank if product.sales_rank is not None else 10**9


def resolve_complements(products: list[Product], rules: list[ComplementRule]) -> dict[str, list[str]]:
    """For each product, apply matching rules in priority order and pick the best in-stock target.

    Preference: complements that do not cost more than twice the source product (a complement should
    not dwarf the main item), then same brand, then best sales rank, then SKU (deterministic).
    """
    by_category: dict[str, list[Product]] = defaultdict(list)
    for p in products:
        by_category[p.category].append(p)
    for candidates in by_category.values():
        candidates.sort(key=lambda p: (_rank(p), p.sku))

    result: dict[str, list[str]] = {}
    for product in products:
        tags = set(product.tags)
        chosen: list[str] = []
        matching = sorted(
            (
                r
                for r in rules
                if r.source_category == product.category and (not r.source_tags or tags & set(r.source_tags))
            ),
            key=lambda r: (r.priority, r.rule_id),
        )
        for rule in matching:
            targets = [
                c
                for c in by_category.get(rule.target_category, [])
                if c.sku != product.sku
                and c.stock > 0
                and c.sku not in chosen
                and (not rule.target_tags or set(c.tags) & set(rule.target_tags))
            ]
            if not targets:
                continue
            affordable = [c for c in targets if c.price <= 2 * product.price] or targets
            same_brand = [c for c in affordable if c.brand == product.brand]
            chosen.append((same_brand or affordable)[0].sku)
            if len(chosen) >= MAX_COMPLEMENTS:
                break
        result[product.sku] = chosen
    return result
