"""Agent API: one service for all tenants. Tenant = verified public key + allowed Origin."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from magaza_core.contracts import (
    ChatRequest,
    ClientEvent,
    ErrorEvent,
    QuoteRequest,
    QuoteResponse,
    WidgetPublicConfig,
)
from magaza_core.pii import PiiMaskingFilter
from magaza_core.repo import ProductRepo, QuoteRepo
from magaza_core.sse import encode_sse
from magaza_core.tenancy import TenantContext, assign_group, hash_visitor, origin_allowed

from .chat import run_turn
from .deps import Deps

_TENANT_PATH = re.compile(r"^/v1/t/([^/]+)/")


def _configure_logging() -> None:
    root = logging.getLogger()
    if not any(isinstance(f, PiiMaskingFilter) for h in root.handlers for f in h.filters):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.addFilter(PiiMaskingFilter())
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(ErrorEvent(type="error", code=code, message=message).model_dump(), status_code=status)


def create_app(deps: Deps | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _configure_logging()
        app.state.deps = deps or Deps.from_env()
        yield

    app = FastAPI(title="Mağaza Asistanım — agent-api", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def tenant_cors(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Per-tenant CORS: the Origin must be in the tenant's allow-list (resolved from the public key in the path)."""
        match = _TENANT_PATH.match(request.url.path)
        if not match:
            return await call_next(request)
        current: Deps = request.app.state.deps
        tenant = await current.resolve_tenant(match.group(1))
        origin = request.headers.get("origin")
        if tenant is None:
            return _error(404, "unknown_tenant", "Bilinmeyen ya da pasif anahtar.")
        if not origin_allowed(tenant.config, origin):
            return _error(403, "origin_not_allowed", "Bu alan adı için asistan etkin değil.")
        request.state.tenant = tenant
        if request.method == "OPTIONS":
            response: Response = Response(status_code=204)
        else:
            response = await call_next(request)
        if origin:
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-methods"] = "GET, POST, OPTIONS"
            response.headers["access-control-allow-headers"] = "content-type, accept"
            response.headers["access-control-max-age"] = "600"
            response.headers["vary"] = "Origin"
        return response

    def tenant_of(request: Request) -> TenantContext:
        return request.state.tenant

    @app.get("/healthz")
    async def healthz(request: Request) -> dict[str, object]:
        current: Deps = request.app.state.deps
        return {"ok": True, "llm_mode": current.settings.llm_mode, "model": current.model_name}

    @app.get("/v1/t/{public_key}/config", response_model=WidgetPublicConfig)
    async def widget_config(
        public_key: str, request: Request, visitor_id: str = "anonymous"
    ) -> WidgetPublicConfig:
        cfg = tenant_of(request).config
        return WidgetPublicConfig(
            display_name=cfg.display_name,
            assistant_name=cfg.persona.assistant_name,
            greeting=cfg.persona.greeting,
            suggested_questions=cfg.persona.suggested_questions,
            theme=cfg.theme,
            actions=cfg.actions,
            group=assign_group(cfg.tenant_id, visitor_id, cfg.holdout_pct),
        )

    @app.post("/v1/t/{public_key}/chat")
    async def chat(public_key: str, request: Request) -> Response:
        try:
            req = ChatRequest.model_validate_json(await request.body())
        except ValidationError:
            return _error(422, "invalid_request", "Geçersiz istek.")
        current: Deps = request.app.state.deps
        tenant = tenant_of(request)

        async def stream() -> AsyncIterator[bytes]:
            async for event in run_turn(current, tenant, req):
                yield encode_sse(event)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
        )

    @app.post("/v1/t/{public_key}/events", status_code=202)
    async def client_event(public_key: str, request: Request) -> Response:
        try:
            event = ClientEvent.model_validate_json(await request.body())
        except ValidationError:
            return _error(422, "invalid_request", "Geçersiz olay.")
        current: Deps = request.app.state.deps
        tenant = tenant_of(request)
        current.analytics.emit(
            event.event_type,
            tenant_id=tenant.tenant_id,  # from the verified key, never from the body
            visitor_id_hash=hash_visitor(tenant.tenant_id, event.visitor_id),
            session_id=event.session_id,
            payload=dict(event.payload or {}),
        )
        return JSONResponse({"ok": True}, status_code=202)

    @app.post("/v1/t/{public_key}/quotes", response_model=QuoteResponse)
    async def quote(public_key: str, request: Request) -> Response:
        tenant = tenant_of(request)
        if not tenant.config.actions.quote_request:
            return _error(404, "invalid_request", "Bu mağazada teklif talebi kapalı.")
        try:
            req = QuoteRequest.model_validate_json(await request.body())
        except ValidationError:
            return _error(422, "invalid_request", "Teklif formu eksik ya da hatalı.")
        current: Deps = request.app.state.deps
        products = {
            p.sku: p for p in await ProductRepo(current.db, tenant).get_many([i.sku for i in req.items])
        }
        unknown = [i.sku for i in req.items if i.sku not in products]
        if unknown:
            return _error(422, "invalid_request", f"Katalogda olmayan ürün: {', '.join(unknown)}")
        visitor_hash = hash_visitor(tenant.tenant_id, req.visitor_id)
        lines = [{"sku": i.sku, "qty": i.qty, "unit_price": products[i.sku].price} for i in req.items]
        quote_id = await QuoteRepo(current.db, tenant).create(
            req, visitor_id_hash=visitor_hash, source="widget_form", lines=lines
        )
        current.analytics.emit(
            "quote_request",
            tenant_id=tenant.tenant_id,
            visitor_id_hash=visitor_hash,
            session_id=req.session_id,
            payload={
                "quote_id": quote_id,
                "source": "widget_form",
                "skus": [i.sku for i in req.items],
                "email": req.email,
            },
        )
        return JSONResponse(QuoteResponse(quote_id=quote_id, status="received").model_dump())

    return app


app = create_app()
