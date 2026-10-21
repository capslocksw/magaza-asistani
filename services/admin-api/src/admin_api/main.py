"""Admin API: tenant management, persona templates, catalog sync, dashboards, CSV and PDF exports."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from google.cloud.firestore import AsyncClient

from magaza_core.contracts import PersonaTemplate, TenantConfig
from magaza_core.embedding import get_embedder
from magaza_core.repo import PersonaTemplateRepo, ProductRepo, SyncJobRepo, TenantRegistry, get_db
from magaza_core.tenancy import TenantContext
from magaza_jobs.feed_sync import sync_feed

from .analytics import (
    AnalyticsRepository,
    BigQueryAnalyticsRepository,
    Dashboards,
    DuckDbAnalyticsRepository,
    Period,
)
from .auth import AdminUser, current_user
from .exports import DATASETS, to_csv
from .report import build_report

DASHBOARDS = ("executive", "funnel", "demand", "unmet", "products", "quality", "usage")


@dataclass
class AdminDeps:
    db: AsyncClient
    analytics: AnalyticsRepository

    @classmethod
    def from_env(cls) -> AdminDeps:
        if os.environ.get("ANALYTICS_BACKEND", "duckdb") == "bigquery":
            analytics: AnalyticsRepository = BigQueryAnalyticsRepository(
                os.environ["GOOGLE_CLOUD_PROJECT"], os.environ["BIGQUERY_EVENTS_TABLE"]
            )
        else:
            analytics = DuckDbAnalyticsRepository(
                os.environ.get("ANALYTICS_DUCKDB_PATH", "data/analytics/fixture.duckdb"),
                os.environ.get("ANALYTICS_LIVE_JSONL"),
            )
        return cls(db=get_db(), analytics=analytics)


User = Annotated[AdminUser, Depends(current_user)]


def get_deps(request: Request) -> AdminDeps:
    deps: AdminDeps = request.app.state.deps
    return deps


Deps_ = Annotated[AdminDeps, Depends(get_deps)]


async def tenant(tenant_id: str, user: User, d: Deps_) -> TenantContext:
    """Tenant id from the URL is only trusted after checking the authenticated user's access."""
    if not user.can_access(tenant_id):
        raise HTTPException(403, "Bu tenant'a erişim yetkiniz yok.")
    config = await TenantRegistry(d.db).get(tenant_id)
    if config is None:
        raise HTTPException(404, "Tenant bulunamadı.")
    return TenantContext.of(config)


Tenant = Annotated[TenantContext, Depends(tenant)]


def create_app(deps: AdminDeps | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.deps = deps or AdminDeps.from_env()
        yield

    app = FastAPI(title="Mağaza Asistanım — admin-api", version="0.1.0", lifespan=lifespan)
    origins = os.environ.get("ADMIN_WEB_ORIGINS", "http://localhost:5175,http://127.0.0.1:5175").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["authorization", "content-type"],
        expose_headers=["content-disposition"],
    )

    def dashboards(d: AdminDeps, ctx: TenantContext) -> Dashboards:
        async def titles(skus: list[str]) -> dict[str, str]:
            try:
                return {p.sku: p.title for p in await ProductRepo(d.db, ctx).get_many(skus)}
            except Exception:
                return {}

        return Dashboards(d.analytics, titles)

    def period(start: date | None, end: date | None) -> Period:
        end = end or datetime.now(UTC).date()
        start = start or end - timedelta(days=29)
        if start > end:
            raise HTTPException(422, "Başlangıç tarihi bitişten sonra olamaz.")
        return Period(start, end)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True}

    @app.get("/api/me")
    async def me(user: User) -> dict[str, Any]:
        return user.as_dict()

    # ------------------------------------------------------------------ tenants
    @app.get("/api/tenants")
    async def list_tenants(user: User, d: Deps_) -> list[dict[str, Any]]:
        return [
            t.model_dump(mode="json")
            for t in await TenantRegistry(d.db).list()
            if user.can_access(t.tenant_id)
        ]

    @app.post("/api/tenants", status_code=201)
    async def create_tenant(config: TenantConfig, user: User, d: Deps_) -> dict[str, Any]:
        if user.role != "superadmin":
            raise HTTPException(403, "Yalnızca süper yönetici tenant oluşturabilir.")
        registry = TenantRegistry(d.db)
        if await registry.get(config.tenant_id):
            raise HTTPException(409, "Bu tenant zaten var.")
        try:
            return (await registry.upsert(config)).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/tenants/{tenant_id}")
    async def get_tenant(ctx: Tenant) -> dict[str, Any]:
        return ctx.config.model_dump(mode="json")

    @app.put("/api/tenants/{tenant_id}")
    async def update_tenant(tenant_id: str, config: TenantConfig, ctx: Tenant, d: Deps_) -> dict[str, Any]:
        if config.tenant_id != ctx.tenant_id:
            raise HTTPException(422, "tenant_id değiştirilemez.")
        try:
            return (await TenantRegistry(d.db).upsert(config)).model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.delete("/api/tenants/{tenant_id}", status_code=204)
    async def delete_tenant(ctx: Tenant, user: User, d: Deps_) -> Response:
        if user.role != "superadmin":
            raise HTTPException(403, "Yalnızca süper yönetici tenant silebilir.")
        await TenantRegistry(d.db).delete(ctx.tenant_id)
        return Response(status_code=204)

    @app.get("/api/tenants/{tenant_id}/widget-snippet")
    async def widget_snippet(ctx: Tenant) -> dict[str, str]:
        widget_url = os.environ.get("WIDGET_PUBLIC_URL", "http://localhost:5174/widget.js")
        agent_url = os.environ.get("AGENT_PUBLIC_URL", "http://localhost:8080")
        snippet = f'<script src="{widget_url}" data-tenant="{ctx.config.public_key}" data-api="{agent_url}" async></script>'
        return {"snippet": snippet}

    # ------------------------------------------------------------------ persona templates
    @app.get("/api/persona-templates")
    async def list_templates(user: User, d: Deps_) -> list[dict[str, Any]]:
        return [t.model_dump(mode="json") for t in await PersonaTemplateRepo(d.db).list()]

    @app.put("/api/persona-templates/{template_id}")
    async def update_template(
        template_id: str, template: PersonaTemplate, user: User, d: Deps_
    ) -> dict[str, Any]:
        if user.role != "superadmin":
            raise HTTPException(403, "Yalnızca süper yönetici şablon düzenleyebilir.")
        if template.template_id != template_id:
            raise HTTPException(422, "template_id uyuşmuyor.")
        return (await PersonaTemplateRepo(d.db).upsert(template)).model_dump(mode="json")

    # ------------------------------------------------------------------ catalog sync
    @app.post("/api/tenants/{tenant_id}/catalog-sync", status_code=202)
    async def catalog_sync(ctx: Tenant, d: Deps_, background: BackgroundTasks) -> dict[str, str]:
        job_id = f"feed-{uuid.uuid4().hex[:10]}"
        await SyncJobRepo(d.db, ctx).record(
            job_id, {"kind": "feed_sync", "status": "queued", "queued_at": datetime.now(UTC).isoformat()}
        )
        background.add_task(sync_feed, d.db, ctx, get_embedder(), job_id=job_id)
        return {"job_id": job_id, "status": "queued"}

    @app.get("/api/tenants/{tenant_id}/sync-jobs/{job_id}")
    async def sync_job(job_id: str, ctx: Tenant, d: Deps_) -> dict[str, Any]:
        job = await SyncJobRepo(d.db, ctx).get(job_id)
        if job is None:
            raise HTTPException(404, "İş bulunamadı.")
        return {"job_id": job_id, **job}

    # ------------------------------------------------------------------ dashboards
    @app.get("/api/tenants/{tenant_id}/dashboards/{name}")
    async def dashboard(
        name: str, ctx: Tenant, d: Deps_, start: date | None = None, end: date | None = None
    ) -> dict[str, Any]:
        if name not in DASHBOARDS:
            raise HTTPException(404, "Bilinmeyen pano.")
        dash = dashboards(d, ctx)
        p = period(start, end)
        data: dict[str, Any] = await (
            dash.usage([ctx.tenant_id], p) if name == "usage" else getattr(dash, name)(ctx.config, p)
        )
        return {"tenant_id": ctx.tenant_id, "start": p.start.isoformat(), "end": p.end.isoformat(), **data}

    @app.get("/api/billing")
    async def billing(
        user: User, d: Deps_, start: date | None = None, end: date | None = None
    ) -> dict[str, Any]:
        tenants = [t.tenant_id for t in await TenantRegistry(d.db).list() if user.can_access(t.tenant_id)]
        p = period(start, end)
        return await Dashboards(d.analytics, _no_titles).usage(tenants, p)

    @app.get("/api/tenants/{tenant_id}/conversations")
    async def conversations(
        ctx: Tenant,
        d: Deps_,
        start: date | None = None,
        end: date | None = None,
        q: str = "",
        limit: Annotated[int, Query(ge=1, le=200)] = 25,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return await dashboards(d, ctx).conversations(
            ctx.config, period(start, end), q=q, limit=limit, offset=offset
        )

    @app.get("/api/tenants/{tenant_id}/conversations/{session_id}")
    async def conversation(session_id: str, ctx: Tenant, d: Deps_) -> dict[str, Any]:
        events = await dashboards(d, ctx).conversation(ctx.config, session_id)
        if not events:
            raise HTTPException(404, "Konuşma bulunamadı.")
        return {"session_id": session_id, "events": events}

    # ------------------------------------------------------------------ exports
    @app.get("/api/tenants/{tenant_id}/export/{dataset}.csv")
    async def export_csv(
        dataset: str,
        ctx: Tenant,
        d: Deps_,
        start: date | None = None,
        end: date | None = None,
        sep: Annotated[str, Query(pattern="^[,;]$")] = ",",
    ) -> Response:
        if dataset not in DATASETS:
            raise HTTPException(404, "Bilinmeyen veri seti.")
        p = period(start, end)
        rows = await DATASETS[dataset].load(dashboards(d, ctx), ctx.config, p)
        filename = f"{ctx.tenant_id}-{dataset}-{p.start}-{p.end}.csv"
        return Response(
            to_csv(DATASETS[dataset], rows, sep),
            media_type="text/csv; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/tenants/{tenant_id}/reports/monthly.pdf")
    async def monthly_report(
        ctx: Tenant, d: Deps_, month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")]
    ) -> Response:
        pdf = await build_report(dashboards(d, ctx), ctx.config, month)
        return Response(
            pdf,
            media_type="application/pdf",
            headers={"content-disposition": f'attachment; filename="{ctx.tenant_id}-rapor-{month}.pdf"'},
        )

    return app


async def _no_titles(skus: list[str]) -> dict[str, str]:
    return {}


app = create_app()
