"""Cross-tenant leak tests: nothing from tenant A may ever be returned in a tenant B conversation."""

from __future__ import annotations

import pytest
from agent_test_helpers import chat, client, of_type, tenant_ctx
from google.adk.tools import ToolContext

from agent_api.agent import APP_NAME
from agent_api.session_service import FirestoreSessionService
from agent_api.tools import ToolBox
from agent_api.turn import TurnContext
from magaza_core.analytics import AnalyticsEmitter
from magaza_core.embedding import HashingEmbedder
from magaza_core.repo import (
    ComplementRuleRepo,
    KnowledgeRepo,
    ProductRepo,
    QuoteRepo,
    SessionRepo,
    TenantRegistry,
    get_db,
)
from magaza_core.tenancy import TenantContext

pytestmark = pytest.mark.emulator


async def _toolbox(project: str, tenant_id: str) -> ToolBox:
    db = get_db(project)
    config = await TenantRegistry(db).get(tenant_id)
    assert config is not None
    ctx = TenantContext.of(config)
    turn = TurnContext(tenant=ctx, visitor_hash="0" * 32, session_id="s_isolation_test", message="")
    return ToolBox(
        turn,
        products=ProductRepo(db, ctx),
        knowledge=KnowledgeRepo(db, ctx),
        rules=ComplementRuleRepo(db, ctx),
        quotes=QuoteRepo(db, ctx),
        embedder=HashingEmbedder(),
        analytics=AnalyticsEmitter(None),
    )


def _tool(box: ToolBox, name: str):  # type: ignore[no-untyped-def]
    return next(t for t in box.tools() if t.__name__ == name)


async def test_tools_never_return_other_tenant_products(seeded_project: str) -> None:
    box = await _toolbox(seeded_project, "ambalaj")
    ctx: ToolContext = None  # type: ignore[assignment]
    result = await _tool(box, "search_products")(
        "montaj yapıştırıcısı korniş silikon matkap", tool_context=ctx
    )
    assert result["products"], "ambalaj catalog should still return its own nearest products"
    assert all(p["sku"].startswith("KC-") for p in result["products"])
    assert "error" in await _tool(box, "get_product")("YM-YAP-0001", tool_context=ctx)
    assert "error" in await _tool(box, "get_complements")("YM-YAP-0001", tool_context=ctx)
    bundle = await _tool(box, "propose_bundle")(["YM-YAP-0001"], [1], "x", "y", tool_context=ctx)
    assert "error" in bundle and box.turn.bundle is None
    knowledge = await _tool(box, "search_knowledge")(
        "montaj yapıştırıcısı taşıma kapasitesi", tool_context=ctx
    )
    assert all(p["doc_id"].startswith("doc-kc-") for p in knowledge["passages"])


async def test_session_of_tenant_a_is_invisible_to_tenant_b(seeded_project: str) -> None:
    db = get_db(seeded_project)
    a = await tenant_ctx(seeded_project, "yapi-market")
    b = await tenant_ctx(seeded_project, "ambalaj")
    session = await FirestoreSessionService(SessionRepo(db, a)).create_session(
        app_name=APP_NAME, user_id="u1", state={"x": 1}
    )
    assert (
        await FirestoreSessionService(SessionRepo(db, b)).get_session(
            app_name=APP_NAME, user_id="u1", session_id=session.id
        )
        is None
    )
    assert (
        await FirestoreSessionService(SessionRepo(db, a)).get_session(
            app_name=APP_NAME, user_id="u1", session_id=session.id
        )
    ) is not None


def test_http_session_id_from_other_tenant_starts_a_new_session(seeded_project: str) -> None:
    with client(seeded_project) as (c, _):
        first = chat(c, "pk_test_yapimarket", "Kornişim koptu, matkabım yok", visitor="v_cross_tenant_1")
        sid_a = first[-1]["session_id"]
        second = chat(
            c, "pk_test_ambalaj", "Kornişim koptu, matkabım yok", visitor="v_cross_tenant_1", session_id=sid_a
        )
        assert second[-1]["session_id"] != sid_a
        for event in of_type(second, "products"):
            assert all(p["sku"].startswith("KC-") for p in event["products"])
        for event in of_type(second, "bundle"):
            assert all(i["sku"].startswith("KC-") for i in event["bundle"]["items"])
        assert "YM-" not in "".join(e.get("text", "") for e in second)


def test_client_cannot_choose_tenant(seeded_project: str) -> None:
    with client(seeded_project) as (c, _):
        res = c.post(
            "/v1/t/pk_test_yapimarket/chat",
            json={"message": "koli", "visitor_id": "v_cross_tenant_2", "tenant_id": "ambalaj"},
            headers={"origin": "http://localhost:3101"},
        )
        assert res.status_code == 422
        # An origin allowed for tenant B cannot use tenant A's key.
        res = c.post(
            "/v1/t/pk_test_yapimarket/chat",
            json={"message": "koli", "visitor_id": "v_cross_tenant_2"},
            headers={"origin": "http://localhost:3102"},
        )
        assert res.status_code == 403
