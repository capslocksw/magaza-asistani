"""Per-request state shared by the tools, callbacks and the SSE layer of one chat turn."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from magaza_core.contracts import Bundle, ErrorEvent, Product
from magaza_core.repo import ScoredChunk
from magaza_core.tenancy import TenantContext


@dataclass
class TurnContext:
    tenant: TenantContext
    visitor_hash: str
    session_id: str
    message: str
    session_messages: int = 0
    grounded: set[str] = field(default_factory=set)  # SKUs returned by tools in this session
    products: dict[str, Product] = field(default_factory=dict)  # products returned by tools in this turn
    knowledge: list[ScoredChunk] = field(default_factory=list)
    bundle: Bundle | None = None
    quote_id: str | None = None
    zero_result_queries: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    blocked: ErrorEvent | None = None
    model_calls: int = 0
    grounding_retries: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    started: float = field(default_factory=time.perf_counter)

    @property
    def tenant_id(self) -> str:
        return self.tenant.tenant_id

    def remember(self, products: list[Product]) -> None:
        for p in products:
            self.products[p.sku] = p
            self.grounded.add(p.sku)

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)
