"""Server-sent event encoding for the chat stream contract."""

from __future__ import annotations

from pydantic import BaseModel


def encode_sse(event: BaseModel) -> bytes:
    """Encode one contract event as ``event: <type>`` + ``data: <json>``."""
    event_type = getattr(event, "type", "message")
    payload = event.model_dump_json(exclude_none=True)
    return f"event: {event_type}\ndata: {payload}\n\n".encode()
