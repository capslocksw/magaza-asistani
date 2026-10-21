"""Structured analytics events: every agent step is written as one JSON log line (Cloud Logging -> BigQuery sink
in production) and, locally, optionally appended to a JSONL file the admin DuckDB repository can read."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from magaza_core.contracts import AnalyticsEvent, AnalyticsEventType
from magaza_core.llm_config import LlmConfig, load_llm_config
from magaza_core.pii import mask_payload

log = logging.getLogger("magaza.analytics")


class AnalyticsEmitter:
    def __init__(self, jsonl_path: str | None = None, llm_config: LlmConfig | None = None) -> None:
        self.jsonl_path = Path(jsonl_path) if jsonl_path else None
        self.llm = llm_config or load_llm_config()
        self._lock = threading.Lock()
        self.events: list[AnalyticsEvent] = []  # last events, handy for tests
        if self.jsonl_path:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        event_type: AnalyticsEventType,
        *,
        tenant_id: str,
        visitor_id_hash: str,
        session_id: str | None = None,
        model: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int | None = None,
        payload: dict[str, Any] | None = None,
        ts: datetime | None = None,
        is_synthetic: bool = False,
    ) -> AnalyticsEvent:
        now = ts or datetime.now(UTC)
        event = AnalyticsEvent(
            event_id=uuid.uuid4().hex,
            event_type=event_type,
            tenant_id=tenant_id,
            session_id=session_id,
            visitor_id_hash=visitor_id_hash,
            ts=now,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_usd_est=self.llm.estimate_cost_usd(model, tokens_in, tokens_out, now) if model else 0.0,
            is_synthetic=is_synthetic,
            payload=mask_payload(payload or {}),
        )
        record = event.model_dump(mode="json")
        log.info(
            json.dumps(
                {"severity": "INFO", "message": "analytics_event", "analytics_event": record},
                ensure_ascii=False,
            )
        )
        with self._lock:
            self.events.append(event)
            del self.events[:-500]
            if self.jsonl_path:
                with self.jsonl_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return event
