"""The only way to reach Firestore. Every tenant-data repository is constructed with a server-verified
``TenantContext`` and builds its paths under ``tenants/{tenant_id}/...``; no method accepts a tenant id."""

from .base import Collections, TenantScopedRepo, get_db
from .catalog import ComplementRuleRepo, KnowledgeRepo, ProductRepo, ScoredChunk, ScoredProduct
from .ops import QuoteRepo, SyncJobRepo, UsageRepo
from .registry import PersonaTemplateRepo, TenantRegistry
from .sessions import SessionRepo

__all__ = [
    "Collections",
    "ComplementRuleRepo",
    "KnowledgeRepo",
    "PersonaTemplateRepo",
    "ProductRepo",
    "QuoteRepo",
    "ScoredChunk",
    "ScoredProduct",
    "SessionRepo",
    "SyncJobRepo",
    "TenantRegistry",
    "TenantScopedRepo",
    "UsageRepo",
    "get_db",
]
