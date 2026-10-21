from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from magaza_core.contracts import Product, TenantConfig
from magaza_jobs.demo_data import build_tenant, write_tenant
from magaza_jobs.demo_data.docs import sheet_html
from magaza_jobs.demo_data.model import shelf_price
from magaza_jobs.demo_data.tenants import PERSONA_TEMPLATES, TENANT_SPECS
from magaza_jobs.feed_format import parse_feed, write_feed

BUNDLE = json.loads(
    (
        Path(__file__).resolve().parents[3] / "packages" / "contracts" / "generated" / "bundle.schema.json"
    ).read_text(encoding="utf-8")
)
MIN_PRODUCTS = {"yapi-market": 300, "ambalaj": 120}
DOC_COUNTS = {"yapi-market": 40, "ambalaj": 15}
# Real-world brands that must never appear in fictional demo data (CLAUDE.md rule).
REAL_BRANDS = [
    "bosch",
    "makita",
    "pattex",
    "akfix",
    "soudal",
    "dyo",
    "filli",
    "polisan",
    "marshall",
    "stanley",
    "dewalt",
    "fischer",
    "würth",
    "tesa",
    "3m",
    "karcher",
    "einhell",
    "black&decker",
    "henkel",
    "ceys",
]


@pytest.fixture(scope="module", params=list(TENANT_SPECS))
def dataset(request: pytest.FixtureRequest):  # type: ignore[no-untyped-def]
    return build_tenant(request.param)


def _validator(name: str) -> jsonschema.protocols.Validator:
    return jsonschema.Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": BUNDLE["$defs"]})


def test_minimum_catalog_size(dataset) -> None:  # type: ignore[no-untyped-def]
    assert len(dataset.products) >= MIN_PRODUCTS[dataset.tenant.tenant_id]


def test_products_conform_to_schema(dataset) -> None:  # type: ignore[no-untyped-def]
    validator = _validator("Product")
    for p in dataset.products:
        validator.validate(p.model_dump(mode="json", exclude_none=True))
        assert p.price > 0
        assert p.list_price is None or p.list_price > p.price
        assert p.sku.startswith(TENANT_SPECS[dataset.tenant.tenant_id].prefix + "-")
        assert p.specs, f"{p.sku} has no technical specs"


def test_sku_uniqueness_across_tenants() -> None:
    skus = [p.sku for tid in TENANT_SPECS for p in build_tenant(tid).products]
    assert len(skus) == len(set(skus))


def test_complement_references_are_valid(dataset) -> None:  # type: ignore[no-untyped-def]
    by_sku = {p.sku: p for p in dataset.products}
    with_complements = 0
    for p in dataset.products:
        assert len(p.complement_skus) <= 4
        assert len(set(p.complement_skus)) == len(p.complement_skus)
        for sku in p.complement_skus:
            assert sku in by_sku, f"{p.sku} -> unknown complement {sku}"
            assert sku != p.sku
            assert by_sku[sku].stock > 0
        with_complements += bool(p.complement_skus)
    assert with_complements >= len(dataset.products) // 2


def test_complement_rules_point_to_existing_categories(dataset) -> None:  # type: ignore[no-untyped-def]
    categories = {c.slug for c in dataset.categories}
    for rule in dataset.rules:
        assert rule.source_category in categories
        assert rule.target_category in categories
        targets = [
            p
            for p in dataset.products
            if p.category == rule.target_category
            and (not rule.target_tags or set(p.tags) & set(rule.target_tags))
        ]
        assert targets, f"rule {rule.rule_id} has no target products"


def test_data_sheets(dataset) -> None:  # type: ignore[no-untyped-def]
    tid = dataset.tenant.tenant_id
    assert len(dataset.sheets) == DOC_COUNTS[tid]
    with_doc = {p.sku for p in dataset.products if p.doc_id}
    assert with_doc == {s.sku for s in dataset.sheets}
    for sheet in dataset.sheets:
        assert "## Teknik Özellikler" in sheet.markdown
        assert sheet.doc_id == f"doc-{sheet.sku.lower()}"


def test_generation_is_deterministic() -> None:
    for tid in TENANT_SPECS:
        a = [p.model_dump(mode="json") for p in build_tenant(tid).products]
        b = [p.model_dump(mode="json") for p in build_tenant(tid).products]
        assert a == b


def test_feed_round_trip(dataset) -> None:  # type: ignore[no-untyped-def]
    xml = write_feed(dataset.products, store_name=dataset.tenant.display_name, store_url=dataset.store_url)
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert 'xmlns:g="http://base.google.com/ns/1.0"' in xml
    assert parse_feed(xml) == dataset.products


def test_tenant_config_and_personas(dataset) -> None:  # type: ignore[no-untyped-def]
    _validator("TenantConfig").validate(dataset.tenant.model_dump(mode="json", exclude_none=True))
    TenantConfig.model_validate(dataset.tenant.model_dump())
    assert dataset.tenant.persona.template_id in {t.template_id for t in PERSONA_TEMPLATES}
    assert all(not o.endswith("/") for o in dataset.tenant.allowed_origins)


def test_no_real_brands(dataset) -> None:  # type: ignore[no-untyped-def]
    text = json.dumps([p.model_dump(mode="json") for p in dataset.products], ensure_ascii=False).lower()
    for brand in REAL_BRANDS:
        assert f'"{brand}' not in text and f" {brand} " not in text, brand


def test_kickoff_scenarios_have_expected_complements() -> None:
    ym = {p.sku: p for p in build_tenant("yapi-market").products}
    montaj = next(
        p
        for p in ym.values()
        if p.title.endswith("Montaj Yapıştırıcısı 290 ml") and "montaj-yapistiricisi" in p.tags
    )
    tags = {t for sku in montaj.complement_skus for t in ym[sku].tags}
    assert {"silikon-tabancasi", "yuzey-temizleyici"} <= tags

    kc = {p.sku: p for p in build_tenant("ambalaj").products}
    koli = next(p for p in kc.values() if "cift-oluklu" in p.tags)
    tags = {t for sku in koli.complement_skus for t in kc[sku].tags}
    assert {"balonlu", "koli-bandi"} <= tags


def test_write_tenant_without_pdf(tmp_path: Path) -> None:
    ds = build_tenant("ambalaj")
    counts = write_tenant(ds, tmp_path, pdf=False)
    root = tmp_path / "ambalaj"
    assert counts["products"] == len(ds.products)
    catalog = [
        Product.model_validate(p) for p in json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    ]
    assert catalog == ds.products
    assert parse_feed((root / "feed.xml").read_text(encoding="utf-8")) == ds.products
    for p in ds.products:
        svg = (root / "images" / f"{p.sku}.svg").read_text(encoding="utf-8")
        assert svg.startswith("<svg") and 'role="img"' in svg
    assert len(list((root / "docs").glob("*.md"))) == DOC_COUNTS["ambalaj"]


def test_sheet_renders_to_pdf() -> None:
    pytest.importorskip("playwright")
    from magaza_core.pdf import html_to_pdf

    ds = build_tenant("ambalaj")
    try:
        pdf = html_to_pdf(sheet_html(ds.sheets[0], ds.tenant.display_name, ds.tenant.theme.primary_color))
    except Exception as exc:  # pragma: no cover - browser not installed
        pytest.skip(f"no PDF backend available: {exc}")
    assert pdf.startswith(b"%PDF")


@pytest.mark.parametrize(
    ("raw", "expected"), [(14.3, 14.9), (187.0, 189.9), (1493.0, 1499.9), (2731.0, 2749.9)]
)
def test_shelf_price(raw: float, expected: float) -> None:
    assert shelf_price(raw) == pytest.approx(expected)
