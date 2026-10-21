from __future__ import annotations

import os
from typing import Any

from google.cloud.firestore import AsyncClient, AsyncCollectionReference, AsyncDocumentReference

from magaza_core.tenancy import TenantContext


class Collections:
    TENANTS = "tenants"
    PERSONA_TEMPLATES = "persona_templates"
    PRODUCTS = "products"
    DOC_CHUNKS = "doc_chunks"
    COMPLEMENT_RULES = "complement_rules"
    SESSIONS = "sessions"
    SESSION_EVENTS = "events"
    ADK_STATE = "adk_state"
    QUOTES = "quotes"
    USAGE = "usage"
    SYNC_JOBS = "sync_jobs"


def get_db(project: str | None = None) -> AsyncClient:
    """Async Firestore client. Honours FIRESTORE_EMULATOR_HOST automatically (local dev and tests)."""
    project = (
        project
        or os.environ.get("FIRESTORE_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or "demo-magaza"
    )
    return AsyncClient(project=project)


class TenantScopedRepo:
    """Base for repositories of tenant-owned data."""

    def __init__(self, db: AsyncClient, ctx: TenantContext) -> None:
        if not ctx.tenant_id:
            raise ValueError("TenantContext without tenant_id")
        self.db = db
        self.ctx = ctx

    @property
    def tenant_doc(self) -> AsyncDocumentReference:
        return self.db.collection(Collections.TENANTS).document(self.ctx.tenant_id)

    def col(self, name: str) -> AsyncCollectionReference:
        return self.tenant_doc.collection(name)

    async def _delete_collection(self, col: AsyncCollectionReference, batch_size: int = 400) -> int:
        deleted = 0
        while True:
            docs = [d async for d in col.limit(batch_size).stream()]
            if not docs:
                return deleted
            batch = self.db.batch()
            for d in docs:
                batch.delete(d.reference)
            await batch.commit()
            deleted += len(docs)


def strip_internal(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k not in keys and not k.startswith("_")}
