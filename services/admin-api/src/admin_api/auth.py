"""Firebase Auth verification. DEV_AUTH_BYPASS=1 is honoured only outside Cloud Run (local development)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AdminUser:
    uid: str
    email: str
    role: str  # "superadmin" | "tenant_admin"
    tenants: list[str] = field(default_factory=list)

    def can_access(self, tenant_id: str) -> bool:
        return self.role == "superadmin" or tenant_id in self.tenants

    def as_dict(self) -> dict[str, Any]:
        return {"uid": self.uid, "email": self.email, "role": self.role, "tenants": self.tenants}


def dev_bypass_enabled() -> bool:
    if os.environ.get("K_SERVICE"):  # running on Cloud Run: never bypass auth
        return False
    return os.environ.get("DEV_AUTH_BYPASS") == "1"


_firebase_ready = False


def _verify(token: str) -> dict[str, Any]:
    global _firebase_ready
    import firebase_admin
    from firebase_admin import auth

    if not _firebase_ready:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _firebase_ready = True
    claims: dict[str, Any] = auth.verify_id_token(token)
    return claims


async def current_user(request: Request) -> AdminUser:
    if dev_bypass_enabled():
        return AdminUser(uid="dev", email="gelistirici@localhost", role="superadmin", tenants=["*"])
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "Oturum açmanız gerekiyor.")
    try:
        claims = _verify(header.split(" ", 1)[1])
    except Exception as exc:
        raise HTTPException(401, "Geçersiz ya da süresi dolmuş oturum.") from exc
    return AdminUser(
        uid=str(claims.get("uid", claims.get("sub", ""))),
        email=str(claims.get("email", "")),
        role=str(claims.get("role", "tenant_admin")),
        tenants=list(claims.get("tenants", [])),
    )
