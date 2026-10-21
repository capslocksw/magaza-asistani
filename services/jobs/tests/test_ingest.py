from __future__ import annotations

from pathlib import Path

import pytest

from magaza_core.embedding import HashingEmbedder
from magaza_core.repo import KnowledgeRepo, ProductRepo, TenantRegistry, get_db
from magaza_core.tenancy import TenantContext
from magaza_jobs.doc_ingest import chunk_pages, extract
from magaza_jobs.feed_sync import sync_feed

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_chunk_pages_splits_by_section_headings() -> None:
    page = "\n".join(
        [
            "Yapıcı Market TEKNİK FÖY · YM-YAP-0001",
            "Tutkan Montaj Yapıştırıcısı 290 ml — Teknik Föy",
            "Ürün kodu: YM-YAP-0001 · Marka: Tutkan",
            "Ürün Tanımı",
            "Matkap ve vida kullanmadan montaj sağlar.",
            "Teknik Özellikler",
            "Taşıma kapasitesi 40 kg/m²",
            "Uygulama",
            "1. Yüzeyi temizleyin.",
        ]
    )
    chunks = chunk_pages(
        [page], doc_id="doc-ym-yap-0001", sku="YM-YAP-0001", source_url="/docs/YM-YAP-0001.pdf"
    )
    assert [c.section for c in chunks] == ["Ürün Tanımı", "Teknik Özellikler", "Uygulama"]
    assert chunks[1].text.startswith("Teknik Özellikler: Taşıma kapasitesi 40")
    assert all(c.sku == "YM-YAP-0001" and c.page == 1 for c in chunks)
    assert "Montaj Yapıştırıcısı" in chunks[0].title


@pytest.mark.skipif(
    not (REPO_ROOT / "data/demo/ambalaj/docs/KC-COK-0009.pdf").exists(), reason="run `make data` first"
)
def test_extract_real_pdf_data_sheet() -> None:
    pdf = REPO_ROOT / "data/demo/ambalaj/docs/KC-COK-0009.pdf"
    chunks = chunk_pages(
        extract(pdf), doc_id="doc-kc-cok-0009", sku="KC-COK-0009", source_url="/docs/KC-COK-0009.pdf"
    )
    sections = {c.section for c in chunks}
    assert {"Ürün Tanımı", "Teknik Özellikler", "Uygulama"} <= sections
    assert any("BC dalga" in c.text for c in chunks)


@pytest.mark.emulator
async def test_seeded_catalog_and_knowledge(seeded_project: str, demo_data_dir: Path) -> None:
    db = get_db(seeded_project)
    config = await TenantRegistry(db).get("yapi-market")
    assert config is not None and config.catalog.last_synced_at is not None
    ctx = TenantContext.of(config)
    products = ProductRepo(db, ctx)
    assert await products.count() >= 300
    assert await KnowledgeRepo(db, ctx).count() > 40

    hits = await products.vector_search(HashingEmbedder().embed_one("çift oluklu koli"), limit=3)
    assert all(h.product.sku.startswith("YM-") for h in hits)  # tenant-scoped even for another sector's query

    summary = await sync_feed(
        db, ctx, HashingEmbedder(), source=str(demo_data_dir / "yapi-market" / "feed.xml")
    )
    assert summary["removed"] == 0 and summary["products"] == await products.count()
    sample = await products.get("YM-YAP-0001")
    assert sample is not None and sample.complement_skus and sample.doc_url == "/docs/YM-YAP-0001.pdf"
