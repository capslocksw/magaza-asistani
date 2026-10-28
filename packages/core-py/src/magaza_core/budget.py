"""Hard spending cap for paid model calls (Gemini chat + Vertex embeddings) — ADR 007.

Before a real request is sent, its worst-case cost is reserved in a SQLite ledger shared by every local process
(agent-api, admin-api, jobs, eval runner). The reservation is refused, and the request never reaches the API, when
spent + in flight + this request would exceed `budget.hard_cap_usd - budget.safety_margin_usd` (config/llm.yaml).
Afterwards the reservation is settled with the billed token counts from the response's usage metadata; when the
outcome is unknown (timeout, crash) the worst case stays on the books.

    python -m magaza_core.budget        # cap, spent, in flight, remaining
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from magaza_core.llm_config import LlmConfig, load_llm_config, repo_root


class BudgetExceeded(RuntimeError):
    """A paid request was refused before it was sent: it could push spending past the configured cap."""


@dataclass(frozen=True)
class Reservation:
    id: str
    model: str
    estimate_usd: float


@dataclass(frozen=True)
class SpendTotals:
    spent_usd: float
    in_flight_usd: float
    calls: int
    refused: int

    @property
    def committed_usd(self) -> float:
        return self.spent_usd + self.in_flight_usd


_SCHEMA = """
CREATE TABLE IF NOT EXISTS spend (
  id TEXT PRIMARY KEY,
  created_at REAL NOT NULL,
  model TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,  -- reserved | settled | released | refused
  estimate_usd REAL NOT NULL,
  cost_usd REAL,
  tokens_in INTEGER,
  tokens_out INTEGER,
  pid INTEGER NOT NULL
)
"""
_COMMITTED = (
    "SELECT COALESCE(SUM(CASE status WHEN 'reserved' THEN estimate_usd WHEN 'settled' THEN cost_usd ELSE 0 END), 0) "
    "FROM spend"
)


class SpendLedger:
    """SQLite ledger; BEGIN IMMEDIATE serialises check-and-reserve across processes on this machine."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._tx() as con:
            con.execute(_SCHEMA)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def reserve(self, model: str, kind: str, estimate_usd: float, limit_usd: float) -> Reservation:
        rid = uuid.uuid4().hex
        with self._tx() as con:
            committed = float(con.execute(_COMMITTED).fetchone()[0])
            allowed = committed + estimate_usd <= limit_usd
            con.execute(
                "INSERT INTO spend VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)",
                (
                    rid,
                    time.time(),
                    model,
                    kind,
                    "reserved" if allowed else "refused",
                    estimate_usd,
                    None if allowed else 0.0,
                    os.getpid(),
                ),
            )
        if not allowed:
            raise BudgetExceeded(
                f"LLM budget: {committed:.4f} USD committed + {estimate_usd:.4f} USD for this {kind} request "
                f"would exceed the {limit_usd:.2f} USD limit; the request was not sent"
            )
        return Reservation(rid, model, estimate_usd)

    def settle(
        self, reservation: Reservation, cost_usd: float, tokens_in: int | None, tokens_out: int | None
    ) -> None:
        with self._tx() as con:
            con.execute(
                "UPDATE spend SET status = 'settled', cost_usd = ?, tokens_in = ?, tokens_out = ? "
                "WHERE id = ? AND status = 'reserved'",
                (cost_usd, tokens_in, tokens_out, reservation.id),
            )

    def release(self, reservation: Reservation) -> None:
        with self._tx() as con:
            con.execute(
                "UPDATE spend SET status = 'released', cost_usd = 0 WHERE id = ? AND status = 'reserved'",
                (reservation.id,),
            )

    def totals(self) -> SpendTotals:
        with self._tx() as con:
            row = con.execute(
                "SELECT COALESCE(SUM(CASE WHEN status = 'settled' THEN cost_usd ELSE 0 END), 0), "
                "COALESCE(SUM(CASE WHEN status = 'reserved' THEN estimate_usd ELSE 0 END), 0), "
                "COUNT(*) FILTER (WHERE status IN ('settled', 'reserved')), "
                "COUNT(*) FILTER (WHERE status = 'refused') FROM spend"
            ).fetchone()
        return SpendTotals(float(row[0]), float(row[1]), int(row[2]), int(row[3]))

    def by_model(self) -> dict[str, dict[str, float]]:
        with self._tx() as con:
            rows = con.execute(
                "SELECT model, COUNT(*), COALESCE(SUM(cost_usd), 0), COALESCE(SUM(tokens_in), 0), "
                "COALESCE(SUM(tokens_out), 0) FROM spend WHERE status = 'settled' GROUP BY model ORDER BY model"
            ).fetchall()
        return {
            model: {"calls": calls, "cost_usd": round(cost, 6), "tokens_in": tin, "tokens_out": tout}
            for model, calls, cost, tin, tout in rows
        }


class BudgetGuard:
    """Prices, reserves and settles paid requests against the hard cap (and an optional per-run cap)."""

    def __init__(self, config: LlmConfig, ledger: SpendLedger, run_cap_usd: float | None = None) -> None:
        self.config = config
        self.ledger = ledger
        self.run_cap_usd = run_cap_usd
        self._run_committed = 0.0

    @property
    def limit_usd(self) -> float:
        budget = self.config.budget
        return budget.hard_cap_usd - budget.safety_margin_usd

    def estimate_tokens(self, chars: int) -> int:
        return math.ceil(chars / self.config.budget.chars_per_token)

    def cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        if self.config.price(model) is None:
            raise BudgetExceeded(
                f"no price configured for {model!r} in config/llm.yaml; paid requests are refused"
            )
        return self.config.estimate_cost_usd(model, tokens_in, tokens_out)

    def reserve(self, model: str, kind: str, tokens_in: int, tokens_out: int) -> Reservation:
        estimate = self.cost(model, tokens_in, tokens_out)
        if self.run_cap_usd is not None and self._run_committed + estimate > self.run_cap_usd:
            raise BudgetExceeded(
                f"run cap {self.run_cap_usd:.2f} USD reached ({self._run_committed:.4f} USD used by this run); "
                "the request was not sent"
            )
        reservation = self.ledger.reserve(model, kind, estimate, self.limit_usd)
        self._run_committed += estimate
        return reservation

    def settle(self, reservation: Reservation, tokens_in: int, tokens_out: int) -> float:
        cost = self.cost(reservation.model, tokens_in, tokens_out)
        self.ledger.settle(reservation, cost, tokens_in, tokens_out)
        self._run_committed += cost - reservation.estimate_usd
        return cost

    def settle_estimate(self, reservation: Reservation) -> None:
        """Outcome unknown (timeout, server error, cancelled stream): keep the worst case on the books."""
        self.ledger.settle(reservation, reservation.estimate_usd, None, None)

    def release(self, reservation: Reservation) -> None:
        """The API rejected the request (4xx): nothing was billed."""
        self.ledger.release(reservation)
        self._run_committed -= reservation.estimate_usd

    def status(self) -> dict[str, object]:
        totals = self.ledger.totals()
        budget = self.config.budget
        return {
            "hard_cap_usd": budget.hard_cap_usd,
            "limit_usd": round(self.limit_usd, 2),
            "spent_usd": round(totals.spent_usd, 6),
            "in_flight_usd": round(totals.in_flight_usd, 6),
            "remaining_usd": round(max(0.0, self.limit_usd - totals.committed_usd), 6),
            "calls": totals.calls,
            "refused": totals.refused,
            "by_model": self.ledger.by_model(),
            "ledger": str(self.ledger.path),
        }


def ledger_path() -> Path:
    return Path(os.environ.get("LLM_SPEND_LEDGER") or repo_root() / ".local" / "llm-spend.sqlite")


def get_budget_guard(run_cap_usd: float | None = None) -> BudgetGuard:
    if os.environ.get("K_SERVICE"):
        # A file ledger is per instance: N Cloud Run instances would each allow the full cap.
        raise RuntimeError(
            "paid model calls on Cloud Run need a shared spend ledger (docs/OPEN_QUESTIONS.md #8); refusing to start"
        )
    return BudgetGuard(load_llm_config(), SpendLedger(ledger_path()), run_cap_usd)


if __name__ == "__main__":
    print(json.dumps(get_budget_guard().status(), indent=2, ensure_ascii=False))
