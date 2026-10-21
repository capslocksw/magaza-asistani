from __future__ import annotations

import pytest
from agent_test_helpers import client, tenant_ctx

from magaza_core.repo import QuoteRepo, get_db
from magaza_core.tenancy import assign_group

pytestmark = pytest.mark.emulator


def test_widget_config_and_deterministic_holdout(seeded_project: str) -> None:
    with client(seeded_project) as (c, _):
        res = c.get(
            "/v1/t/pk_test_yapimarket/config",
            params={"visitor_id": "v_e2e_assistant_0001"},
            headers={"origin": "http://localhost:3101"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["assistant_name"] == "Usta" and body["actions"]["quote_request"] is False
        assert body["group"] == "assistant"
        control = c.get("/v1/t/pk_test_yapimarket/config", params={"visitor_id": "v_e2e_control_0014"}).json()
        assert control["group"] == "control"  # same bucket as the widget's mock-agent (JS) implementation
        assert assign_group("yapi-market", "v_e2e_control_0014", 10) == "control"


def test_cors_preflight_and_unknown_key(seeded_project: str) -> None:
    with client(seeded_project) as (c, _):
        ok = c.options(
            "/v1/t/pk_test_ambalaj/chat",
            headers={"origin": "http://localhost:3102", "access-control-request-method": "POST"},
        )
        assert ok.status_code == 204 and ok.headers["access-control-allow-origin"] == "http://localhost:3102"
        denied = c.options(
            "/v1/t/pk_test_ambalaj/chat",
            headers={"origin": "https://evil.example", "access-control-request-method": "POST"},
        )
        assert denied.status_code == 403
        assert c.get("/v1/t/pk_unknown_key/config").status_code == 404


def test_client_events_use_verified_tenant(seeded_project: str) -> None:
    with client(seeded_project) as (c, deps):
        res = c.post(
            "/v1/t/pk_test_ambalaj/events",
            json={
                "event_type": "order",
                "visitor_id": "v_events_test_1",
                "payload": {"order_id": "ORD-1", "total": 10, "tenant_id": "yapi-market"},
            },
            headers={"origin": "http://localhost:3102"},
        )
        assert res.status_code == 202
        event = deps.analytics.events[-1]
        assert event.event_type == "order" and event.tenant_id == "ambalaj"
        assert len(event.visitor_id_hash) == 32 and "v_events_test_1" not in event.visitor_id_hash


async def test_quote_form_only_for_enabled_tenant(seeded_project: str) -> None:
    quote = {
        "visitor_id": "v_quote_test_01",
        "company_name": "Kupa Atölyesi",
        "contact_name": "Deniz Kaya",
        "email": "deniz@example.com",
        "items": [{"sku": "KC-COK-0009", "qty": 500}],
    }
    with client(seeded_project) as (c, deps):
        res = c.post("/v1/t/pk_test_ambalaj/quotes", json=quote, headers={"origin": "http://localhost:3102"})
        assert res.status_code == 200, res.text
        quote_id = res.json()["quote_id"]
        assert deps.analytics.events[-1].payload["email"] == "[e-posta]"
        bad = c.post(
            "/v1/t/pk_test_ambalaj/quotes", json={**quote, "items": [{"sku": "YM-YAP-0001", "qty": 1}]}
        )
        assert bad.status_code == 422
        assert c.post("/v1/t/pk_test_yapimarket/quotes", json=quote).status_code == 404
    db = get_db(seeded_project)
    ctx = await tenant_ctx(seeded_project, "ambalaj")
    stored = await QuoteRepo(db, ctx).list()
    assert any(q["quote_id"] == quote_id and q["lines"][0]["unit_price"] > 0 for q in stored)
