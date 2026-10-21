"""feed-sync: Google Merchant feed -> Firestore products (+ embeddings). Cloud Run Job in production.

python -m magaza_jobs.feed_sync --tenant yapi-market
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.cloud.firestore import AsyncClient

from magaza_core.embedding import Embedder, get_embedder
from magaza_core.repo import ComplementRuleRepo, ProductRepo, SyncJobRepo, TenantRegistry, get_db
from magaza_core.repo.catalog import product_search_text
from magaza_core.tenancy import TenantContext

from .complements import resolve_complements
from .feed_format import parse_feed

log = logging.getLogger(__name__)


def read_feed(source: str) -> str:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=60) as resp:
            return str(resp.read().decode("utf-8"))
    return Path(source).read_text(encoding="utf-8")


async def sync_feed(
    db: AsyncClient,
    ctx: TenantContext,
    embedder: Embedder,
    *,
    source: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    job_id = job_id or f"feed-{uuid.uuid4().hex[:10]}"
    jobs = SyncJobRepo(db, ctx)
    await jobs.record(
        job_id, {"kind": "feed_sync", "status": "running", "started_at": datetime.now(UTC).isoformat()}
    )
    try:
        products = parse_feed(read_feed(source or ctx.config.catalog.feed_url))
        if not any(p.complement_skus for p in products):
            rules = await ComplementRuleRepo(db, ctx).list()
            if rules:
                resolved = resolve_complements(products, rules)
                products = [p.model_copy(update={"complement_skus": resolved[p.sku]}) for p in products]
        embeddings: list[list[float]] = []
        for i in range(0, len(products), 64):
            embeddings += await embedder.embed(
                [product_search_text(p) for p in products[i : i + 64]], "document"
            )
        repo = ProductRepo(db, ctx)
        synced_at = datetime.now(UTC).isoformat()
        written = await repo.upsert_many(products, embeddings, synced_at=synced_at)
        removed = await repo.delete_missing({p.sku for p in products})
        summary = {
            "job_id": job_id,
            "products": written,
            "removed": removed,
            "embedder": embedder.name,
            "seconds": round(time.perf_counter() - started, 2),
        }
        await jobs.record(job_id, {"status": "succeeded", "finished_at": synced_at, **summary})
        registry = TenantRegistry(db)
        config = await registry.get(ctx.tenant_id)
        if config:
            config.catalog.last_synced_at = datetime.now(UTC)
            await registry.upsert(config)
        return summary
    except Exception as exc:
        await jobs.record(job_id, {"status": "failed", "error": str(exc)[:500]})
        raise


async def _main(tenant_id: str, source: str | None) -> None:
    db = get_db()
    config = await TenantRegistry(db).get(tenant_id)
    if config is None:
        raise SystemExit(f"unknown tenant {tenant_id}")
    print(await sync_feed(db, TenantContext.of(config), get_embedder(), source=source))


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync a tenant's Merchant feed into Firestore")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--source", help="override feed URL/path")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main(args.tenant, args.source))


if __name__ == "__main__":
    main()
