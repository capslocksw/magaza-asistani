"""Tenant context: established only by the server (public key + Origin, or admin auth), never by clients or models."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from magaza_core.contracts import TenantConfig


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    config: TenantConfig

    @classmethod
    def of(cls, config: TenantConfig) -> TenantContext:
        return cls(tenant_id=config.tenant_id, config=config)


def assign_group(tenant_id: str, visitor_id: str, holdout_pct: float) -> str:
    """Deterministic holdout bucket; must match apps/widget/mock-agent/scenarios.mjs#assignGroup."""
    bucket = int(hashlib.sha256(f"{tenant_id}:{visitor_id}".encode()).hexdigest()[:8], 16) % 100
    return "control" if bucket < holdout_pct else "assistant"


def hash_visitor(tenant_id: str, visitor_id: str) -> str:
    """Pseudonymous visitor id stored in analytics (salted, tenant-bound)."""
    salt = os.environ.get("VISITOR_HASH_SALT", "local-dev-salt")
    return hashlib.sha256(f"{salt}:{tenant_id}:{visitor_id}".encode()).hexdigest()[:32]


def origin_allowed(config: TenantConfig, origin: str | None) -> bool:
    """Browsers always send Origin on cross-origin requests; requests without it are non-browser clients."""
    if origin is None:
        return True
    return origin.rstrip("/") in {o.rstrip("/") for o in config.allowed_origins}
