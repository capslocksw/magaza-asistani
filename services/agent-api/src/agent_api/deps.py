"""Process-wide dependencies of the agent API (created once at startup)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from google.adk.models import BaseLlm
from google.cloud.firestore import AsyncClient

from magaza_core.analytics import AnalyticsEmitter
from magaza_core.budget import BudgetGuard, get_budget_guard
from magaza_core.contracts import PersonaTemplate
from magaza_core.embedding import Embedder, get_embedder
from magaza_core.repo import PersonaTemplateRepo, TenantRegistry, get_db
from magaza_core.tenancy import TenantContext

from .callbacks import RateLimiter
from .fake_llm import FakeLlm
from .paid_llm import BudgetedGemini
from .settings import Settings


@dataclass
class Deps:
    settings: Settings
    db: AsyncClient
    embedder: Embedder
    analytics: AnalyticsEmitter
    limiter: RateLimiter = field(default_factory=RateLimiter)
    llm_override: BaseLlm | None = None  # tests inject scripted models here
    budget: BudgetGuard | None = None  # LLM_MODE=vertex: created on first use unless injected (eval run cap)
    _paid_model: BaseLlm | None = None
    _tenant_cache: dict[str, tuple[float, TenantContext | None]] = field(default_factory=dict)
    _templates: dict[str, tuple[float, PersonaTemplate]] = field(default_factory=dict)

    @classmethod
    def from_env(cls, settings: Settings | None = None) -> Deps:
        settings = settings or Settings()
        settings.configure_vertex_env()
        return cls(
            settings=settings,
            db=get_db(),
            embedder=get_embedder(),
            analytics=AnalyticsEmitter(settings.analytics_jsonl_path, settings.llm),
        )

    @property
    def registry(self) -> TenantRegistry:
        return TenantRegistry(self.db)

    async def resolve_tenant(self, public_key: str) -> TenantContext | None:
        """public key -> TenantContext (cached briefly). The only way a request gets a tenant."""
        cached = self._tenant_cache.get(public_key)
        if cached and time.monotonic() - cached[0] < self.settings.tenant_cache_ttl_s:
            return cached[1]
        config = await self.registry.resolve_public_key(public_key)
        ctx = TenantContext.of(config) if config else None
        self._tenant_cache[public_key] = (time.monotonic(), ctx)
        return ctx

    async def persona_template(self, template_id: str) -> PersonaTemplate:
        cached = self._templates.get(template_id)
        if cached and time.monotonic() - cached[0] < self.settings.tenant_cache_ttl_s:
            return cached[1]  # short TTL so admin edits reach running instances
        template = await PersonaTemplateRepo(self.db).get(template_id)
        if template is None:
            raise LookupError(f"persona template {template_id!r} not found")
        self._templates[template_id] = (time.monotonic(), template)
        return template

    def model(self) -> BaseLlm:
        if self.llm_override is not None:
            return self.llm_override
        if self.settings.llm_mode == "fake":
            return FakeLlm()
        if self._paid_model is None:
            self.budget = self.budget or get_budget_guard()
            self._paid_model = BudgetedGemini(model=self.settings.llm.chat.default_model, guard=self.budget)
        return self._paid_model

    @property
    def model_name(self) -> str:
        return self.model().model
