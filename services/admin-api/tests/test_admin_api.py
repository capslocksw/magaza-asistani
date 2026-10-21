from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from admin_api.analytics import BigQueryDialect, Dashboards, DuckDbAnalyticsRepository, Period
from admin_api.auth import AdminUser, current_user
from admin_api.main import AdminDeps, create_app
from magaza_core.repo import get_db
from magaza_jobs.demo_data.tenants import tenant_config
from magaza_jobs.simulator import generate

TODAY = datetime.now(UTC).date()


@pytest.fixture(scope="module")
def fixture_db(tmp_path_factory: pytest.TempPathFactory) -> str:
    path = tmp_path_factory.mktemp("analytics") / "fixture.duckdb"
    generate(path, days=45, seed=3, end=TODAY)
    return str(path)


@contextmanager
def admin(project: str, fixture_db: str, user: AdminUser | None = None) -> Iterator[TestClient]:
    app = create_app(AdminDeps(db=get_db(project), analytics=DuckDbAnalyticsRepository(fixture_db)))
    app.dependency_overrides[current_user] = lambda: (
        user or AdminUser("dev", "dev@local", "superadmin", ["*"])
    )
    with TestClient(app) as client:
        yield client


async def _no_titles(skus: list[str]) -> dict[str, str]:
    return {}


async def test_dashboards_on_duckdb_fixture(fixture_db: str) -> None:
    dash = Dashboards(DuckDbAnalyticsRepository(fixture_db), _no_titles)
    cfg = tenant_config("yapi-market")
    period = Period(TODAY - timedelta(days=29), TODAY)
    ex = await dash.executive(cfg, period)
    k = ex["kpis"]
    assert k["assisted_revenue"] > 0 and k["conversion_assisted"] > k["conversion_unassisted"]
    assert (
        k["aov_diff_pct"] > 0 and 0 < k["cross_sell_acceptance"] < 1 and k["holdout_uplift_pct"] is not None
    )
    assert len(ex["weekly"]) >= 4
    stages = (await dash.funnel(cfg, period))["stages"]
    counts = [s["count"] for s in stages]
    assert counts == sorted(counts, reverse=True) and counts[-1] > 0
    demand = await dash.demand(cfg, period)
    assert demand["topics"][0]["label"] in {t.label for t in cfg.topic_taxonomy} and demand["samples"]
    unmet = await dash.unmet(cfg, period)
    assert unmet["not_in_catalog"] and unmet["zero_result"] and unmet["kpis"]["unmet_rate"] > 0
    products = await dash.products(cfg, period)
    assert products["top"][0]["shown"] >= products["top"][-1]["shown"] and products["pairs"]
    assert any(p["ordered"] > 0 for p in products["top"])
    quality = await dash.quality(cfg, period)
    assert 0.5 < quality["kpis"]["like_rate"] < 1 and quality["guardrails"]
    usage = await dash.usage(["yapi-market", "ambalaj"], period)
    assert {r["tenant_id"] for r in usage["rows"]} == {"yapi-market", "ambalaj"} and usage["totals"][
        "cost_usd"
    ] > 0
    conv = await dash.conversations(cfg, period, q="korniş", limit=5)
    assert conv["items"] and all("korniş" in i["first_message"].lower() for i in conv["items"])
    detail = await dash.conversation(cfg, conv["items"][0]["session_id"])
    assert detail[0]["event_type"] == "user_message"


def test_bigquery_dialect_renders_portable_sql() -> None:
    d = BigQueryDialect("`proj.ds.analytics_events`")
    assert d.p("tenant") == "@tenant" and "JSON_VALUE" in d.s("topic") and "COUNTIF" in d.count_if("x")
    assert "UNNEST" in d.unnest(d.arr("skus"), "sku") and "IN UNNEST(@tenants)" in d.in_list(
        "tenant_id", "tenants"
    )


@pytest.mark.emulator
def test_http_dashboards_csv_and_pdf(seeded_project: str, fixture_db: str) -> None:
    with admin(seeded_project, fixture_db) as c:
        assert sorted(t["tenant_id"] for t in c.get("/api/tenants").json()) == ["ambalaj", "yapi-market"]
        for name in ("executive", "funnel", "demand", "unmet", "products", "quality", "usage"):
            res = c.get(f"/api/tenants/ambalaj/dashboards/{name}")
            assert res.status_code == 200, (name, res.text)
        top = c.get("/api/tenants/ambalaj/dashboards/products").json()["top"]
        assert top[0]["title"] != top[0]["sku"]  # titles resolved from the tenant's catalog

        csv = c.get("/api/tenants/ambalaj/export/urunler.csv", params={"sep": ";"})
        assert csv.status_code == 200 and csv.content.startswith(b"\xef\xbb\xbf")
        text = csv.content.decode("utf-8-sig")
        assert (
            text.splitlines()[0].startswith("SKU;Ürün;Önerildi")
            and "attachment" in csv.headers["content-disposition"]
        )
        assert "," in text.splitlines()[1].split(";")[5] or text.splitlines()[1].split(";")[5] in {"0", ""}
        assert c.get("/api/tenants/ambalaj/export/yok.csv").status_code == 404

        month = (TODAY.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        try:
            pdf = c.get("/api/tenants/ambalaj/reports/monthly.pdf", params={"month": month})
        except Exception as exc:  # pragma: no cover - no PDF backend
            pytest.skip(f"PDF backend unavailable: {exc}")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        assert (
            c.get("/api/tenants/ambalaj/reports/monthly.pdf", params={"month": "2026-13"}).status_code == 422
        )

        billing = c.get("/api/export/faturalama.csv", params={"sep": ","}).content.decode("utf-8-sig")
        assert (
            billing.splitlines()[0].startswith("Tenant,Ay,Konuşma")
            and "ambalaj" in billing
            and "yapi-market" in billing
        )


@pytest.mark.emulator
def test_tenant_access_control_and_updates(seeded_project: str, fixture_db: str) -> None:
    limited = AdminUser("u1", "u1@example.com", "tenant_admin", ["ambalaj"])
    with admin(seeded_project, fixture_db, limited) as c:
        assert [t["tenant_id"] for t in c.get("/api/tenants").json()] == ["ambalaj"]
        assert c.get("/api/tenants/yapi-market/dashboards/executive").status_code == 403
        assert c.get("/api/tenants/yapi-market").status_code == 403
        config = c.get("/api/tenants/ambalaj").json()
        config["holdout_pct"] = 15
        config["allowed_origins"] = [*config["allowed_origins"], "https://shop.example.com"]
        updated = c.put("/api/tenants/ambalaj", json=config)
        assert updated.status_code == 200 and updated.json()["holdout_pct"] == 15
        assert c.put("/api/tenants/ambalaj", json={**config, "tenant_id": "yapi-market"}).status_code in (
            403,
            422,
        )
        assert c.post("/api/tenants", json={**config, "tenant_id": "yeni-tenant"}).status_code == 403
        snippet = c.get("/api/tenants/ambalaj/widget-snippet").json()["snippet"]
        assert 'data-tenant="pk_test_ambalaj"' in snippet
        job = c.post("/api/tenants/ambalaj/catalog-sync").json()
        status = c.get(f"/api/tenants/ambalaj/sync-jobs/{job['job_id']}").json()
        assert status["status"] in {"queued", "running", "succeeded", "failed"}


def test_auth_required_without_bypass(monkeypatch: pytest.MonkeyPatch, fixture_db: str) -> None:
    monkeypatch.delenv("DEV_AUTH_BYPASS", raising=False)
    app = create_app(AdminDeps(db=get_db("demo-unused"), analytics=DuckDbAnalyticsRepository(fixture_db)))
    with TestClient(app) as c:
        assert c.get("/api/me").status_code == 401
        assert c.get("/api/me", headers={"authorization": "Bearer not-a-token"}).status_code == 401
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    monkeypatch.setenv("K_SERVICE", "admin-api")  # bypass must never work on Cloud Run
    with TestClient(app) as c:
        assert c.get("/api/me").status_code == 401


def test_period_previous() -> None:
    p = Period(date(2026, 10, 1), date(2026, 10, 30))
    assert p.previous() == Period(date(2026, 9, 1), date(2026, 9, 30))


def test_fixture_is_synthetic(fixture_db: str) -> None:
    import duckdb

    con = duckdb.connect(fixture_db, read_only=True)
    assert con.execute(
        "SELECT bool_and(is_synthetic), count(DISTINCT tenant_id) FROM analytics_events"
    ).fetchone() == (True, 2)
    assert Path(fixture_db).stat().st_size > 0
