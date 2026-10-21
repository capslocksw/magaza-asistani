"""Building blocks for the deterministic demo catalog generator (no LLM involved)."""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass, field

from magaza_core.contracts import ProductSpec

_TR_FOLD = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")


def fold(text: str) -> str:
    """ASCII-fold Turkish characters (ç->c, ğ->g, ı->i, ...)."""
    return text.translate(_TR_FOLD)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fold(text).lower()).strip("-")


def shelf_price(value: float) -> float:
    """Round a raw price to a storefront-looking one: 14,90 / 189,90 / 1.499,90."""
    if value < 20:
        return math.floor(value) + 0.90
    if value < 1000:
        return round(value / 10) * 10 - 0.10
    return round(value / 50) * 50 - 0.10


def spec(key: str, label: str, value: str | float | bool, unit: str | None = None) -> ProductSpec:
    return ProductSpec(key=key, label=label, value=value, unit=unit)


@dataclass
class Draft:
    """A product before SKU/URL/complement resolution."""

    code: str
    title: str
    brand: str
    category: str
    subcategory: str
    description: str
    base_price: float
    unit: str
    specs: list[ProductSpec]
    tags: list[str]
    icon: str
    badge: str
    doc_profile: str | None = None
    doc_priority: int | None = None
    popularity: float = 1.0
    sku: str = ""


@dataclass
class CategoryInfo:
    slug: str
    name: str
    code: str
    icon: str
    description: str
    subcategories: list[str] = field(default_factory=list)


class Builder:
    """Collects drafts for one tenant; SKUs are assigned in insertion order per family code."""

    def __init__(self, prefix: str, seed: int) -> None:
        self.prefix = prefix
        self.rng = random.Random(seed)
        self.drafts: list[Draft] = []
        self._counters: dict[str, int] = {}

    def add(self, draft: Draft) -> Draft:
        n = self._counters.get(draft.code, 0) + 1
        self._counters[draft.code] = n
        draft.sku = f"{self.prefix}-{draft.code}-{n:04d}"
        self.drafts.append(draft)
        return draft

    def pick(self, options: list[str]) -> str:
        return options[self.rng.randrange(len(options))]

    def jitter(self, value: float, pct: float = 0.08) -> float:
        return value * (1 + self.rng.uniform(-pct, pct))
