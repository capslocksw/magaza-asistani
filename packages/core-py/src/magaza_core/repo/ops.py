from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from google.cloud import firestore

from magaza_core.contracts import QuoteRequest

from .base import Collections, TenantScopedRepo


class QuoteRepo(TenantScopedRepo):
    async def create(
        self, request: QuoteRequest, *, visitor_id_hash: str, source: str, lines: list[dict[str, Any]]
    ) -> str:
        quote_id = f"Q-{datetime.now(UTC):%y%m%d}-{uuid.uuid4().hex[:6].upper()}"
        data = request.model_dump(mode="json", exclude={"visitor_id"})
        data.update(
            {
                "quote_id": quote_id,
                "visitor_id_hash": visitor_id_hash,
                "source": source,
                "lines": lines,
                "status": "received",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        await self.col(Collections.QUOTES).document(quote_id).set(data)
        return quote_id

    async def list(self, limit: int = 100) -> list[dict[str, Any]]:
        query = (
            self.col(Collections.QUOTES)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        return [d.to_dict() or {} async for d in query.stream()]


class UsageRepo(TenantScopedRepo):
    """Monthly usage counters (quota enforcement): tenants/{tid}/usage/{YYYY-MM}."""

    async def increment(self, month: str, *, messages: int = 0, sessions: int = 0) -> None:
        await (
            self.col(Collections.USAGE)
            .document(month)
            .set(
                {
                    "messages": firestore.Increment(messages),
                    "sessions": firestore.Increment(sessions),
                    "month": month,
                },
                merge=True,
            )
        )

    async def get(self, month: str) -> dict[str, int]:
        snap = await self.col(Collections.USAGE).document(month).get()
        data = snap.to_dict() or {}
        return {"messages": int(data.get("messages", 0)), "sessions": int(data.get("sessions", 0))}


class SyncJobRepo(TenantScopedRepo):
    async def record(self, job_id: str, data: dict[str, Any]) -> None:
        await self.col(Collections.SYNC_JOBS).document(job_id).set(data, merge=True)

    async def get(self, job_id: str) -> dict[str, Any] | None:
        snap = await self.col(Collections.SYNC_JOBS).document(job_id).get()
        return snap.to_dict() if snap.exists else None
