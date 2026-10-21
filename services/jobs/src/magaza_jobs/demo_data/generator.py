"""Deterministic demo dataset generator: catalog, complements, data sheets, images and feed per tenant."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from magaza_core.contracts import ComplementRule, PersonaTemplate, Product, TenantConfig

from ..complements import resolve_complements
from ..feed_format import write_feed
from . import catalog_ambalaj, catalog_yapi
from .docs import DocSheet, build_sheet, sheet_html
from .images import category_svg, logo_svg, product_svg
from .model import Builder, CategoryInfo, shelf_price
from .tenants import COMPLEMENT_RULES, PERSONA_TEMPLATES, TENANT_SPECS, tenant_config

log = logging.getLogger(__name__)

GENERATOR_VERSION = "1"
_MODULES: dict[str, ModuleType] = {"yapi-market": catalog_yapi, "ambalaj": catalog_ambalaj}


@dataclass
class TenantDataset:
    tenant: TenantConfig
    categories: list[CategoryInfo]
    products: list[Product]
    rules: list[ComplementRule]
    sheets: list[DocSheet]
    icons: dict[str, str]
    badges: dict[str, str]
    store_url: str


def build_tenant(tenant_id: str, data_dir: str = "data/demo") -> TenantDataset:
    spec = TENANT_SPECS[tenant_id]
    module = _MODULES[tenant_id]
    builder = Builder(spec.prefix, spec.seed)
    module.build(builder)
    drafts = builder.drafts
    rng = random.Random(spec.seed + 1)

    scores = sorted(((d.popularity * rng.uniform(0.6, 1.4), i) for i, d in enumerate(drafts)), reverse=True)
    sales_rank = {i: rank for rank, (_, i) in enumerate(scores, start=1)}
    doc_candidates = sorted((d.doc_priority, i) for i, d in enumerate(drafts) if d.doc_priority is not None)
    with_doc = {i for _, i in doc_candidates[: spec.doc_count]}
    categories = {c.slug: c for c in module.CATEGORIES}

    products: list[Product] = []
    for i, d in enumerate(drafts):
        price = round(shelf_price(d.base_price), 2)
        list_price = round(shelf_price(price * rng.uniform(1.12, 1.35)), 2) if rng.random() < 0.3 else None
        stock = 0 if rng.random() < 0.07 else rng.randint(3, 400)
        has_doc = i in with_doc
        products.append(
            Product(
                sku=d.sku,
                title=d.title,
                brand=d.brand,
                category=d.category,
                category_name=categories[d.category].name,
                subcategory=d.subcategory,
                description=d.description,
                price=price,
                list_price=list_price,
                currency="TRY",
                stock=stock,
                unit=d.unit,
                image_url=f"/images/{d.sku}.svg",
                url=f"/urun/{d.sku}/",
                specs=d.specs,
                tags=d.tags,
                complement_skus=[],
                doc_id=f"doc-{d.sku.lower()}" if has_doc else None,
                doc_url=f"/docs/{d.sku}.pdf" if has_doc else None,
                rating=round(rng.uniform(3.6, 4.9), 1),
                review_count=rng.randint(0, 640),
                sales_rank=sales_rank[i],
                max_installments=12 if price >= 2500 else 9 if price >= 1000 else 6 if price >= 300 else 3,
                free_shipping=price >= 500,
                gtin=None,
            )
        )

    rules = COMPLEMENT_RULES[tenant_id]
    complements = resolve_complements(products, rules)
    products = [p.model_copy(update={"complement_skus": complements[p.sku]}) for p in products]
    tenant = tenant_config(tenant_id, data_dir)
    sheets = [
        build_sheet(p, drafts[i].doc_profile or "adhesive", tenant.display_name)
        for i, p in enumerate(products)
        if i in with_doc
    ]
    return TenantDataset(
        tenant=tenant,
        categories=list(module.CATEGORIES),
        products=products,
        rules=rules,
        sheets=sheets,
        icons={d.sku: d.icon for d in drafts},
        badges={d.sku: d.badge for d in drafts},
        store_url=spec.store_url,
    )


def _dump(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_tenant(ds: TenantDataset, out_dir: Path, *, pdf: bool = True) -> dict[str, int]:
    tid = ds.tenant.tenant_id
    root = out_dir / tid
    _dump(root / "tenant.json", ds.tenant.model_dump(mode="json"))
    _dump(root / "catalog.json", [p.model_dump(mode="json") for p in ds.products])
    _dump(root / "complement_rules.json", [r.model_dump(mode="json") for r in ds.rules])
    _dump(
        root / "categories.json",
        [
            {
                "slug": c.slug,
                "name": c.name,
                "icon": c.icon,
                "description": c.description,
                "subcategories": c.subcategories,
                "product_count": sum(1 for p in ds.products if p.category == c.slug),
            }
            for c in ds.categories
        ],
    )
    (root / "feed.xml").write_text(
        write_feed(ds.products, store_name=ds.tenant.display_name, store_url=ds.store_url), encoding="utf-8"
    )
    images = root / "images"
    images.mkdir(parents=True, exist_ok=True)
    for p in ds.products:
        (images / f"{p.sku}.svg").write_text(
            product_svg(
                sku=p.sku,
                title=p.title,
                brand=p.brand,
                icon=ds.icons[p.sku],
                badge=ds.badges[p.sku],
                category=p.category,
            ),
            encoding="utf-8",
        )
    for c in ds.categories:
        (images / f"cat-{c.slug}.svg").write_text(
            category_svg(tenant_prefix=ds.products[0].sku[:2], slug=c.slug, icon=c.icon), encoding="utf-8"
        )
    theme = ds.tenant.theme
    (root / "logo.svg").write_text(
        logo_svg(
            name=ds.tenant.display_name,
            primary=theme.primary_color,
            accent=theme.accent_color,
            icon="hammer" if tid == "yapi-market" else "box",
        ),
        encoding="utf-8",
    )
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for sheet in ds.sheets:
        (docs / f"{sheet.sku}.md").write_text(sheet.markdown, encoding="utf-8")
    pdf_count = 0
    if pdf:
        from magaza_core.pdf import pdf_renderer

        with pdf_renderer() as renderer:
            for sheet in ds.sheets:
                html = sheet_html(sheet, ds.tenant.display_name, theme.primary_color)
                (docs / f"{sheet.sku}.pdf").write_bytes(renderer.render(html))
                pdf_count += 1
    return {
        "products": len(ds.products),
        "docs": len(ds.sheets),
        "pdfs": pdf_count,
        "categories": len(ds.categories),
    }


def write_all(out_dir: Path, *, pdf: bool = True, data_dir: str = "data/demo") -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for tenant_id in TENANT_SPECS:
        summary[tenant_id] = write_tenant(build_tenant(tenant_id, data_dir), out_dir, pdf=pdf)
    templates: list[PersonaTemplate] = PERSONA_TEMPLATES
    _dump(out_dir / "persona_templates.json", [t.model_dump(mode="json") for t in templates])
    _dump(out_dir / "manifest.json", {"generator_version": GENERATOR_VERSION, "tenants": summary})
    return summary
