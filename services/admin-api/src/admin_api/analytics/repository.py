"""AnalyticsRepository: executes dialect SQL. DuckDB (local fixture + live JSONL) and BigQuery (production)."""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from .dialect import BigQueryDialect, Dialect, DuckDbDialect

_COLUMNS = (
    "{'event_id': 'VARCHAR', 'event_type': 'VARCHAR', 'tenant_id': 'VARCHAR', 'session_id': 'VARCHAR', "
    "'visitor_id_hash': 'VARCHAR', 'ts': 'TIMESTAMP', 'model': 'VARCHAR', 'tokens_in': 'BIGINT', 'tokens_out': 'BIGINT', "
    "'latency_ms': 'BIGINT', 'cost_usd_est': 'DOUBLE', 'is_synthetic': 'BOOLEAN', 'payload': 'JSON'}"
)


class AnalyticsRepository(ABC):
    dialect: Dialect

    @abstractmethod
    async def rows(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...

    @staticmethod
    def _payload(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                return value
        return value


class DuckDbAnalyticsRepository(AnalyticsRepository):
    """Reads the synthetic fixture and, if present, live events the local agent-api appended as JSONL."""

    def __init__(self, path: str, live_jsonl: str | None = None) -> None:
        self.path = path
        self.live_jsonl = live_jsonl
        source = "analytics_events"
        if live_jsonl and Path(live_jsonl).exists() and Path(live_jsonl).stat().st_size > 0:
            live = Path(live_jsonl).as_posix()
            source = (
                f"(SELECT * FROM analytics_events UNION ALL SELECT * FROM "
                f"read_json('{live}', format='newline_delimited', columns={_COLUMNS}))"
            )
        self.dialect = DuckDbDialect(source)

    def _run(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        import duckdb

        con = duckdb.connect(self.path, read_only=True)
        try:
            cur = con.execute(sql, {k: v for k, v in params.items() if f"${k}" in sql})
            cols = [d[0] for d in cur.description or []]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
        finally:
            con.close()

    async def rows(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        out = await asyncio.to_thread(
            self._run,
            sql,
            {k: (v.replace(tzinfo=None) if isinstance(v, datetime) else v) for k, v in params.items()},
        )
        for row in out:
            if "payload" in row:
                row["payload"] = self._payload(row["payload"])
        return out


class BigQueryAnalyticsRepository(AnalyticsRepository):
    """Production: Cloud Logging sink -> BigQuery table with the AnalyticsEvent columns (payload JSON)."""

    def __init__(self, project: str, table: str) -> None:
        from google.cloud import bigquery

        self.client = bigquery.Client(project=project)
        self.dialect = BigQueryDialect(f"`{table}`")

    def _run(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        from google.cloud import bigquery

        def param(name: str, value: Any) -> Any:
            if isinstance(value, list):
                return bigquery.ArrayQueryParameter(name, "STRING", value)
            kind = (
                "TIMESTAMP"
                if isinstance(value, datetime)
                else "INT64"
                if isinstance(value, int)
                else "STRING"
            )
            return bigquery.ScalarQueryParameter(name, kind, value)

        config = bigquery.QueryJobConfig(
            query_parameters=[param(k, v) for k, v in params.items() if f"@{k}" in sql]
        )
        return [dict(r.items()) for r in self.client.query(sql, job_config=config).result()]

    async def rows(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        out = await asyncio.to_thread(self._run, sql, params)
        for row in out:
            if "payload" in row:
                row["payload"] = self._payload(row["payload"])
        return out
