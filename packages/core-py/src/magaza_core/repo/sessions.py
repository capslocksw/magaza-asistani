"""Storage for ADK sessions under ``tenants/{tid}/sessions/{session_id}`` (+ ``events`` sub-collection)."""

from __future__ import annotations

from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from .base import Collections, TenantScopedRepo


class SessionRepo(TenantScopedRepo):
    def _doc(self, session_id: str):  # type: ignore[no-untyped-def]
        return self.col(Collections.SESSIONS).document(session_id)

    async def create(self, session_id: str, data: dict[str, Any]) -> bool:
        """Creates the session document; returns False if it already exists."""
        from google.api_core.exceptions import AlreadyExists

        try:
            await self._doc(session_id).create(data)
            return True
        except AlreadyExists:
            return False

    async def get(self, session_id: str) -> dict[str, Any] | None:
        snap = await self._doc(session_id).get()
        return snap.to_dict() if snap.exists else None

    async def update(self, session_id: str, fields: dict[str, Any]) -> None:
        await self._doc(session_id).set(fields, merge=True)

    async def query(self, app_name: str, user_id: str | None = None) -> list[dict[str, Any]]:
        query = self.col(Collections.SESSIONS).where(filter=FieldFilter("app_name", "==", app_name))
        if user_id is not None:
            query = query.where(filter=FieldFilter("user_id", "==", user_id))
        return [{"id": d.id, **(d.to_dict() or {})} async for d in query.stream()]

    async def delete(self, session_id: str) -> None:
        doc = self._doc(session_id)
        await self._delete_collection(doc.collection(Collections.SESSION_EVENTS))
        await doc.delete()

    async def add_event(self, session_id: str, event_id: str, record: dict[str, Any]) -> None:
        await self._doc(session_id).collection(Collections.SESSION_EVENTS).document(event_id).set(record)

    async def list_events(self, session_id: str) -> list[dict[str, Any]]:
        col = self._doc(session_id).collection(Collections.SESSION_EVENTS)
        # written_ns preserves append order even when event timestamps tie.
        return [d.to_dict() or {} async for d in col.order_by("written_ns").stream()]

    async def get_scoped_state(self, key: str) -> dict[str, Any]:
        snap = await self.col(Collections.ADK_STATE).document(key).get()
        return (snap.to_dict() or {}).get("state", {}) if snap.exists else {}

    async def merge_scoped_state(self, key: str, delta: dict[str, Any]) -> None:
        if delta:
            await self.col(Collections.ADK_STATE).document(key).set({"state": delta}, merge=True)
