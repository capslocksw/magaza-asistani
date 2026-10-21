"""Seeds a Firestore (emulator) with the demo tenants: configs, persona templates, rules, catalog, data sheets.

python -m magaza_jobs.seed --data data/demo
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from google.cloud.firestore import AsyncClient

from magaza_core.contracts import ComplementRule, PersonaTemplate, TenantConfig
from magaza_core.embedding import get_embedder
from magaza_core.repo import ComplementRuleRepo, PersonaTemplateRepo, TenantRegistry, get_db
from magaza_core.tenancy import TenantContext

from .doc_ingest import ingest_docs
from .feed_sync import sync_feed


async def seed(db: AsyncClient, data_dir: Path, tenants: list[str] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    for raw in json.loads((data_dir / "persona_templates.json").read_text(encoding="utf-8")):
        await PersonaTemplateRepo(db).upsert(PersonaTemplate.model_validate(raw))
    embedder = get_embedder()
    summary: dict[str, Any] = {}
    for tenant_dir in sorted(p for p in data_dir.iterdir() if (p / "tenant.json").exists()):
        config = TenantConfig.model_validate_json((tenant_dir / "tenant.json").read_text(encoding="utf-8"))
        if tenants and config.tenant_id not in tenants:
            continue
        config = await TenantRegistry(db).upsert(config)
        ctx = TenantContext.of(config)
        rules = [
            ComplementRule.model_validate(r)
            for r in json.loads((tenant_dir / "complement_rules.json").read_text(encoding="utf-8"))
        ]
        await ComplementRuleRepo(db, ctx).replace_all(rules)
        feed = await sync_feed(db, ctx, embedder, source=str(tenant_dir / "feed.xml"))
        docs = await ingest_docs(db, ctx, embedder, str(tenant_dir / "docs"))
        summary[config.tenant_id] = {
            "products": feed["products"],
            "doc_chunks": docs["chunks"],
            "docs": docs["docs"],
            "rules": len(rules),
        }
    summary["seconds"] = round(time.perf_counter() - started, 1)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Firestore with demo tenants")
    parser.add_argument("--data", default="data/demo", type=Path)
    parser.add_argument("--tenant", action="append", help="limit to tenant(s)")
    args = parser.parse_args()
    if not os.environ.get("FIRESTORE_EMULATOR_HOST") and os.environ.get("SEED_ALLOW_REAL_FIRESTORE") != "1":
        raise SystemExit(
            "Refusing to seed: FIRESTORE_EMULATOR_HOST is not set (set SEED_ALLOW_REAL_FIRESTORE=1 to override)."
        )
    print(json.dumps(asyncio.run(seed(get_db(), args.data, args.tenant)), ensure_ascii=False))


if __name__ == "__main__":
    main()
