"""Tenant registry and global persona templates.

Resolving a public key to a tenant is inherently cross-tenant: it is how the server *establishes* the
tenant context, so it reads the root ``tenants`` collection. Nothing else in the codebase does that
(see docs/adr/004-tenant-isolation.md).
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import AsyncClient
from google.cloud.firestore_v1.base_query import FieldFilter

from magaza_core.contracts import PersonaTemplate, TenantConfig

from .base import Collections


class TenantRegistry:
    def __init__(self, db: AsyncClient) -> None:
        self.db = db
        self._col = db.collection(Collections.TENANTS)

    @staticmethod
    def _parse(data: dict[str, object]) -> TenantConfig:
        return TenantConfig.model_validate({k: v for k, v in data.items() if k in TenantConfig.model_fields})

    async def resolve_public_key(self, public_key: str) -> TenantConfig | None:
        async for snap in (
            self._col.where(filter=FieldFilter("public_key", "==", public_key)).limit(1).stream()
        ):
            config = self._parse(snap.to_dict() or {})
            return config if config.status == "active" else None
        return None

    async def get(self, tenant_id: str) -> TenantConfig | None:
        snap = await self._col.document(tenant_id).get()
        return self._parse(snap.to_dict() or {}) if snap.exists else None

    async def list(self) -> list[TenantConfig]:
        return sorted(
            [self._parse(d.to_dict() or {}) async for d in self._col.stream()], key=lambda t: t.tenant_id
        )

    async def upsert(self, config: TenantConfig) -> TenantConfig:
        now = datetime.now(UTC)
        existing = await self.get(config.tenant_id)
        config = config.model_copy(
            update={"created_at": existing.created_at if existing else now, "updated_at": now}
        )
        other = await self.resolve_public_key(config.public_key)
        if other and other.tenant_id != config.tenant_id:
            raise ValueError("public_key already used by another tenant")
        await self._col.document(config.tenant_id).set(config.model_dump(mode="json"), merge=True)
        return config

    async def delete(self, tenant_id: str) -> None:
        # Firestore does not cascade: delete the document and every nested sub-collection
        # (sessions/*/events hold raw conversation text).
        await self.db.recursive_delete(self._col.document(tenant_id))


class PersonaTemplateRepo:
    def __init__(self, db: AsyncClient) -> None:
        self._col = db.collection(Collections.PERSONA_TEMPLATES)

    async def get(self, template_id: str) -> PersonaTemplate | None:
        snap = await self._col.document(template_id).get()
        return PersonaTemplate.model_validate(snap.to_dict()) if snap.exists else None

    async def list(self) -> list[PersonaTemplate]:
        return sorted(
            [PersonaTemplate.model_validate(d.to_dict()) async for d in self._col.stream()],
            key=lambda t: t.template_id,
        )

    async def upsert(self, template: PersonaTemplate) -> PersonaTemplate:
        await self._col.document(template.template_id).set(template.model_dump(mode="json"))
        return template
