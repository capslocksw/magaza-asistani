"""The seven dashboards (+ conversation explorer), written once against the Dialect API."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from magaza_core.contracts import TenantConfig

from .repository import AnalyticsRepository

TitleResolver = Callable[[list[str]], Awaitable[dict[str, str]]]

FUNNEL_STAGES = [
    ("visit", "Ziyaret (widget yüklendi)"),
    ("widget_open", "Widget açıldı"),
    ("user_message", "Konuşma başladı"),
    ("product_shown", "Ürün önerildi"),
    ("add_to_cart", "Sepete eklendi"),
    ("order", "Sipariş (asistanlı)"),
]
GUARDRAIL_LABELS = {
    "grounding_redirect": "Grounding: yeniden yönlendirme",
    "grounding_stripped": "Grounding: SKU temizlendi",
    "rate_limited": "Hız sınırı",
    "quota_exceeded": "Kota aşıldı",
    "loop_limit": "Döngü sınırı",
}


@dataclass(frozen=True)
class Period:
    start: date
    end: date  # inclusive

    @property
    def params(self) -> dict[str, datetime]:
        return {
            "start": datetime.combine(self.start, time.min, tzinfo=UTC),
            "end": datetime.combine(self.end + timedelta(days=1), time.min, tzinfo=UTC),
        }

    def previous(self) -> Period:
        days = (self.end - self.start).days + 1
        return Period(self.start - timedelta(days=days), self.start - timedelta(days=1))


def _ratio(a: float | None, b: float | None) -> float | None:
    return round(float(a) / float(b), 4) if a is not None and b else None


class Dashboards:
    def __init__(self, repo: AnalyticsRepository, titles: TitleResolver) -> None:
        self.repo = repo
        self.d = repo.dialect
        self.titles = titles

    def _where(self, extra: str = "") -> str:
        d = self.d
        base = f"tenant_id = {d.p('tenant')} AND ts >= {d.p('start')} AND ts < {d.p('end')}"
        return f"{base} AND {extra}" if extra else base

    async def _rows(self, sql: str, tenant: str, period: Period, **extra: Any) -> list[dict[str, Any]]:
        return await self.repo.rows(sql, {"tenant": tenant, **period.params, **extra})

    # ------------------------------------------------------------------ 1. executive summary
    async def executive(self, cfg: TenantConfig, period: Period) -> dict[str, Any]:
        d = self.d
        ev = f"SELECT * FROM {d.table} WHERE {self._where()}"
        sql = f"""
        WITH ev AS ({ev}),
        visitors AS (
          SELECT visitor_id_hash AS v,
                 max(CASE WHEN event_type = 'visit' THEN {d.s("group")} END) AS grp,
                 {d.count_if("event_type = 'user_message'")} > 0 AS chatted
          FROM ev GROUP BY visitor_id_hash),
        orders AS (SELECT visitor_id_hash AS v, {d.n("total")} AS total, {d.b("assisted")} AS assisted FROM ev WHERE event_type = 'order')
        SELECT
          (SELECT count(*) FROM visitors) AS visitors,
          (SELECT {d.count_if("chatted")} FROM visitors) AS chatted_visitors,
          (SELECT count(*) FROM orders) AS orders,
          (SELECT {d.count_if("assisted")} FROM orders) AS assisted_orders,
          (SELECT coalesce(sum(total), 0) FROM orders) AS revenue,
          (SELECT {d.sum_if("total", "assisted")} FROM orders) AS assisted_revenue,
          (SELECT {d.count_if("grp = 'control'")} FROM visitors) AS control_visitors,
          (SELECT count(*) FROM orders o JOIN visitors x ON o.v = x.v WHERE x.grp = 'control') AS control_orders,
          (SELECT {d.count_if("grp = 'assistant'")} FROM visitors) AS assistant_visitors,
          (SELECT count(*) FROM orders o JOIN visitors x ON o.v = x.v WHERE x.grp = 'assistant') AS assistant_orders,
          (SELECT {d.count_if(f"event_type = 'product_shown' AND {d.arr_len(d.arr('skus'))} > 1")} FROM ev) AS bundles_shown,
          (SELECT {d.count_if(f"event_type = 'add_to_cart' AND {d.arr_len(d.arr('skus'))} > 1")} FROM ev) AS bundles_accepted,
          (SELECT {d.count_if(f"event_type = 'user_message' AND {d.n('turn')} = 1")} FROM ev) AS conversations
        """
        k = (await self._rows(sql, cfg.tenant_id, period))[0]
        unassisted_orders = (k["orders"] or 0) - (k["assisted_orders"] or 0)
        unassisted_visitors = (k["visitors"] or 0) - (k["chatted_visitors"] or 0)
        aov_a = _ratio(k["assisted_revenue"], k["assisted_orders"])
        aov_u = _ratio((k["revenue"] or 0) - (k["assisted_revenue"] or 0), unassisted_orders)
        conv_assistant_group = _ratio(k["assistant_orders"], k["assistant_visitors"])
        conv_control = _ratio(k["control_orders"], k["control_visitors"])
        trend = await self._rows(
            f"""
            SELECT {d.week()} AS week,
                   {d.sum_if(d.n("total"), f"event_type = 'order' AND {d.b('assisted')}")} AS assisted_revenue,
                   {d.sum_if(d.n("total"), "event_type = 'order'")} AS revenue,
                   {d.count_if(f"event_type = 'user_message' AND {d.n('turn')} = 1")} AS conversations
            FROM {d.table} WHERE {self._where()} GROUP BY 1 ORDER BY 1""",
            cfg.tenant_id,
            period,
        )
        return {
            "kpis": {
                "assisted_revenue": round(float(k["assisted_revenue"] or 0), 2),
                "revenue": round(float(k["revenue"] or 0), 2),
                "assisted_revenue_share": _ratio(k["assisted_revenue"], k["revenue"]),
                "conversion_assisted": _ratio(k["assisted_orders"], k["chatted_visitors"]),
                "conversion_unassisted": _ratio(unassisted_orders, unassisted_visitors),
                "aov_assisted": aov_a,
                "aov_unassisted": aov_u,
                "aov_diff_pct": round((aov_a / aov_u - 1) * 100, 1) if aov_a and aov_u else None,
                "cross_sell_acceptance": _ratio(k["bundles_accepted"], k["bundles_shown"]),
                "conversations": int(k["conversations"] or 0),
                "orders": int(k["orders"] or 0),
                "holdout_conversion_assistant_group": conv_assistant_group,
                "holdout_conversion_control_group": conv_control,
                "holdout_uplift_pct": round((conv_assistant_group / conv_control - 1) * 100, 1)
                if conv_assistant_group and conv_control
                else None,
            },
            "weekly": [
                {
                    "week": r["week"],
                    "assisted_revenue": round(float(r["assisted_revenue"] or 0), 2),
                    "revenue": round(float(r["revenue"] or 0), 2),
                    "conversations": int(r["conversations"] or 0),
                }
                for r in trend
            ],
        }

    # ------------------------------------------------------------------ 2. funnel
    async def funnel(self, cfg: TenantConfig, period: Period) -> dict[str, Any]:
        d = self.d
        cols = []
        for event, _ in FUNNEL_STAGES:
            cond = f"event_type = '{event}'" + (f" AND {d.b('assisted')}" if event == "order" else "")
            cols.append(f"{d.count_distinct_if('visitor_id_hash', cond)} AS {event}")
        row = (
            await self._rows(
                f"SELECT {', '.join(cols)} FROM {d.table} WHERE {self._where()}", cfg.tenant_id, period
            )
        )[0]
        stages, prev = [], None
        first = row[FUNNEL_STAGES[0][0]] or 0
        for event, label in FUNNEL_STAGES:
            count = int(row[event] or 0)
            stages.append(
                {
                    "stage": event,
                    "label": label,
                    "count": count,
                    "step_rate": _ratio(count, prev),
                    "overall_rate": _ratio(count, first),
                }
            )
            prev = count
        return {"stages": stages}

    # ------------------------------------------------------------------ 3. customer demand
    async def demand(self, cfg: TenantConfig, period: Period) -> dict[str, Any]:
        d = self.d
        labels = {t.topic_id: t.label for t in cfg.topic_taxonomy}
        sql = f"""SELECT {d.s("topic")} AS topic, count(*) AS count FROM {d.table}
                  WHERE {self._where(f"event_type = 'user_message' AND {d.s('topic')} IS NOT NULL")} GROUP BY 1 ORDER BY 2 DESC"""
        current = await self._rows(sql, cfg.tenant_id, period)
        previous = {
            r["topic"]: int(r["count"]) for r in await self._rows(sql, cfg.tenant_id, period.previous())
        }
        total = sum(int(r["count"]) for r in current) or 1
        topics = [
            {
                "topic": r["topic"],
                "label": labels.get(r["topic"], r["topic"]),
                "count": int(r["count"]),
                "share": round(int(r["count"]) / total, 4),
                "previous": previous.get(r["topic"], 0),
                "growth_pct": round((int(r["count"]) / previous[r["topic"]] - 1) * 100, 1)
                if previous.get(r["topic"])
                else None,
            }
            for r in current
        ]
        rising = sorted([t for t in topics if t["growth_pct"] is not None], key=lambda t: -t["growth_pct"])[
            :5
        ]
        samples = await self._rows(
            f"""SELECT session_id, ts, {d.s("text")} AS text, {d.s("topic")} AS topic FROM {d.table}
                WHERE {self._where("event_type = 'user_message'")} ORDER BY ts DESC LIMIT 12""",
            cfg.tenant_id,
            period,
        )
        return {
            "topics": topics,
            "rising": rising,
            "samples": [
                {**s, "ts": _iso(s["ts"]), "topic_label": labels.get(s["topic"] or "", "Diğer")}
                for s in samples
            ],
        }

    # ------------------------------------------------------------------ 4. unmet demand
    async def unmet(self, cfg: TenantConfig, period: Period) -> dict[str, Any]:
        d = self.d
        t = cfg.tenant_id
        not_in_catalog = await self._rows(
            f"""SELECT {d.s("unmet_query")} AS query, count(*) AS count FROM {d.table}
                WHERE {self._where(f"event_type = 'agent_message' AND {d.s('unmet_reason')} = 'not_in_catalog'")}
                GROUP BY 1 ORDER BY 2 DESC LIMIT 20""",
            t,
            period,
        )
        oos_answers = await self._rows(
            f"""SELECT {d.s("out_of_stock_sku")} AS sku, count(*) AS count FROM {d.table}
                WHERE {self._where(f"event_type = 'agent_message' AND {d.s('unmet_reason')} = 'out_of_stock'")} GROUP BY 1""",
            t,
            period,
        )
        oos_search = await self._rows(
            f"""SELECT sku, count(*) AS count FROM {d.table} {d.unnest(d.arr("out_of_stock_skus"), "sku")}
                WHERE {self._where(f"event_type = 'tool_call' AND {d.s('tool')} = 'search_products'")} GROUP BY 1""",
            t,
            period,
        )
        oos: dict[str, int] = {}
        for r in [*oos_answers, *oos_search]:
            if r["sku"]:
                oos[r["sku"]] = oos.get(r["sku"], 0) + int(r["count"])
        titles = await self.titles(list(oos))
        zero = await self._rows(
            f"""SELECT {d.s("query")} AS query, count(*) AS count FROM {d.table}
                WHERE {self._where(f"event_type = 'tool_call' AND {d.s('tool')} = 'search_products' AND {d.b('zero_result')}")}
                GROUP BY 1 ORDER BY 2 DESC LIMIT 20""",
            t,
            period,
        )
        totals = (
            await self._rows(
                f"""SELECT {d.count_if(f"event_type = 'agent_message' AND {d.b('unmet')}")} AS unmet,
                           {d.count_if("event_type = 'agent_message'")} AS answers FROM {d.table} WHERE {self._where()}""",
                t,
                period,
            )
        )[0]
        return {
            "kpis": {
                "unmet_answers": int(totals["unmet"] or 0),
                "unmet_rate": _ratio(totals["unmet"], totals["answers"]),
                "zero_result_searches": sum(int(r["count"]) for r in zero),
                "out_of_stock_requests": sum(oos.values()),
            },
            "not_in_catalog": [{"query": r["query"], "count": int(r["count"])} for r in not_in_catalog],
            "out_of_stock": sorted(
                [{"sku": s, "title": titles.get(s, s), "count": c} for s, c in oos.items()],
                key=lambda r: -int(str(r["count"])),
            )[:20],
            "zero_result": [{"query": r["query"], "count": int(r["count"])} for r in zero],
        }

    # ------------------------------------------------------------------ 5. products & bundles
    async def products(self, cfg: TenantConfig, period: Period) -> dict[str, Any]:
        d = self.d
        t = cfg.tenant_id
        rows = await self._rows(
            f"""
            WITH shown AS (SELECT sku, count(*) AS n FROM {d.table} {d.unnest(d.arr("skus"), "sku")}
                           WHERE {self._where("event_type = 'product_shown'")} GROUP BY 1),
                 added AS (SELECT sku, count(*) AS n FROM {d.table} {d.unnest(d.arr("skus"), "sku")}
                           WHERE {self._where("event_type = 'add_to_cart'")} GROUP BY 1),
                 ordered AS (SELECT sku, count(*) AS n FROM {d.table} {d.unnest(d.item_skus(), "sku")}
                           WHERE {self._where(f"event_type = 'order' AND {d.b('assisted')}")} GROUP BY 1)
            SELECT shown.sku AS sku, shown.n AS shown, coalesce(added.n, 0) AS added, coalesce(ordered.n, 0) AS ordered
            FROM shown LEFT JOIN added ON added.sku = shown.sku LEFT JOIN ordered ON ordered.sku = shown.sku
            ORDER BY shown.n DESC LIMIT 20""",
            t,
            period,
        )
        pairs = await self._rows(
            f"""
            WITH s AS (SELECT event_id, sku FROM {d.table} {d.unnest(d.arr("skus"), "sku")} WHERE {self._where("event_type = 'product_shown'")})
            SELECT a.sku AS sku_a, b.sku AS sku_b, count(*) AS count
            FROM s AS a JOIN s AS b ON a.event_id = b.event_id AND a.sku < b.sku
            GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15""",
            t,
            period,
        )
        titles = await self.titles(
            list({r["sku"] for r in rows} | {p["sku_a"] for p in pairs} | {p["sku_b"] for p in pairs})
        )
        return {
            "top": [
                {
                    "sku": r["sku"],
                    "title": titles.get(r["sku"], r["sku"]),
                    "shown": int(r["shown"]),
                    "added": int(r["added"]),
                    "ordered": int(r["ordered"]),
                    "shown_to_cart": _ratio(r["added"], r["shown"]),
                    "cart_to_order": _ratio(r["ordered"], r["added"]),
                }
                for r in rows
            ],
            "pairs": [
                {
                    **p,
                    "count": int(p["count"]),
                    "title_a": titles.get(p["sku_a"], p["sku_a"]),
                    "title_b": titles.get(p["sku_b"], p["sku_b"]),
                }
                for p in pairs
            ],
        }

    # ------------------------------------------------------------------ 6. conversation quality
    async def quality(self, cfg: TenantConfig, period: Period) -> dict[str, Any]:
        d = self.d
        t = cfg.tenant_id
        k = (
            await self._rows(
                f"""SELECT {d.count_if(f"event_type = 'feedback' AND {d.s('rating')} = 'up'")} AS up,
                           {d.count_if("event_type = 'feedback'")} AS feedback,
                           {d.count_if("event_type = 'agent_message'")} AS answers,
                           {d.count_if(f"event_type = 'agent_message' AND {d.b('dont_know')}")} AS dont_know,
                           {d.avg_if("latency_ms", "event_type = 'agent_message'")} AS latency_avg,
                           {d.p95_if("latency_ms", "event_type = 'agent_message'")} AS latency_p95
                    FROM {d.table} WHERE {self._where()}""",
                t,
                period,
            )
        )[0]
        sessions = (
            await self._rows(
                f"""WITH s AS (SELECT session_id, {d.count_if("event_type = 'user_message'")} AS msgs,
                                      {d.count_if("event_type IN ('add_to_cart', 'quote_request')")} AS converted
                               FROM {d.table} WHERE {self._where("session_id IS NOT NULL")} GROUP BY 1)
                    SELECT count(*) AS sessions, {d.count_if("msgs = 1 AND converted = 0")} AS abandoned FROM s WHERE msgs > 0""",
                t,
                period,
            )
        )[0]
        guardrails = await self._rows(
            f"""SELECT g AS guardrail, count(*) AS count FROM {d.table} {d.unnest(d.arr("guardrails"), "g")}
                WHERE {self._where("event_type = 'agent_message'")} GROUP BY 1 ORDER BY 2 DESC""",
            t,
            period,
        )
        weekly = await self._rows(
            f"""SELECT {d.week()} AS week, {d.count_if(f"event_type = 'feedback' AND {d.s('rating')} = 'up'")} AS up,
                       {d.count_if("event_type = 'feedback'")} AS feedback,
                       {d.count_if(f"event_type = 'agent_message' AND {d.b('dont_know')}")} AS dont_know,
                       {d.count_if("event_type = 'agent_message'")} AS answers
                FROM {d.table} WHERE {self._where()} GROUP BY 1 ORDER BY 1""",
            t,
            period,
        )
        return {
            "kpis": {
                "like_rate": _ratio(k["up"], k["feedback"]),
                "feedback_count": int(k["feedback"] or 0),
                "dont_know_rate": _ratio(k["dont_know"], k["answers"]),
                "abandonment_rate": _ratio(sessions["abandoned"], sessions["sessions"]),
                "guardrail_triggers": sum(int(g["count"]) for g in guardrails),
                "latency_avg_ms": round(float(k["latency_avg"])) if k["latency_avg"] is not None else None,
                "latency_p95_ms": round(float(k["latency_p95"])) if k["latency_p95"] is not None else None,
            },
            "guardrails": [
                {
                    "guardrail": g["guardrail"],
                    "label": GUARDRAIL_LABELS.get(g["guardrail"], g["guardrail"]),
                    "count": int(g["count"]),
                }
                for g in guardrails
            ],
            "weekly": [
                {
                    "week": w["week"],
                    "like_rate": _ratio(w["up"], w["feedback"]),
                    "dont_know_rate": _ratio(w["dont_know"], w["answers"]),
                }
                for w in weekly
            ],
        }

    # ------------------------------------------------------------------ 7. usage & cost (billing)
    async def usage(self, tenant_ids: list[str], period: Period) -> dict[str, Any]:
        d = self.d
        rows = await self.repo.rows(
            f"""SELECT tenant_id, {d.month()} AS month,
                       {d.count_if(f"event_type = 'user_message' AND {d.n('turn')} = 1")} AS conversations,
                       {d.count_if("event_type = 'user_message'")} AS messages,
                       {d.sum_if("tokens_in", "event_type = 'agent_message'")} AS tokens_in,
                       {d.sum_if("tokens_out", "event_type = 'agent_message'")} AS tokens_out,
                       coalesce(sum(cost_usd_est), 0) AS cost_usd
                FROM {d.table}
                WHERE {d.in_list("tenant_id", "tenants")} AND ts >= {d.p("start")} AND ts < {d.p("end")}
                GROUP BY 1, 2 ORDER BY 1, 2""",
            {"tenants": tenant_ids, **period.params},
        )
        out = [
            {
                "tenant_id": r["tenant_id"],
                "month": r["month"],
                "conversations": int(r["conversations"]),
                "messages": int(r["messages"]),
                "tokens_in": int(r["tokens_in"] or 0),
                "tokens_out": int(r["tokens_out"] or 0),
                "cost_usd": round(float(r["cost_usd"] or 0), 4),
            }
            for r in rows
        ]
        totals = {
            key: sum(r[key] for r in out) for key in ("conversations", "messages", "tokens_in", "tokens_out")
        }
        totals["cost_usd"] = round(sum(r["cost_usd"] for r in out), 4)
        return {"rows": out, "totals": totals}

    # ------------------------------------------------------------------ conversation explorer
    async def conversations(
        self, cfg: TenantConfig, period: Period, q: str = "", limit: int = 25, offset: int = 0
    ) -> dict[str, Any]:
        d = self.d
        labels = {t.topic_id: t.label for t in cfg.topic_taxonomy}
        filt = f"AND lower(f.text) LIKE {d.p('q')}" if q else ""
        rows = await self._rows(
            f"""
            WITH agg AS (
              SELECT session_id, min(ts) AS started, {d.count_if("event_type = 'user_message'")} AS turns,
                     {d.count_if("event_type = 'add_to_cart'")} AS adds,
                     {d.count_if(f"event_type = 'feedback' AND {d.s('rating')} = 'up'")} AS likes,
                     {d.count_if(f"event_type = 'feedback' AND {d.s('rating')} = 'down'")} AS dislikes,
                     {d.count_if(f"event_type = 'agent_message' AND {d.arr_len(d.arr('guardrails'))} > 0")} AS guardrails
              FROM {d.table} WHERE {self._where("session_id IS NOT NULL")} GROUP BY 1),
            f AS (SELECT session_id, {d.s("text")} AS text, {d.s("topic")} AS topic FROM {d.table}
                  WHERE {self._where(f"event_type = 'user_message' AND {d.n('turn')} = 1")})
            SELECT agg.session_id AS session_id, agg.started AS started, agg.turns AS turns, agg.adds AS adds, agg.likes AS likes,
                   agg.dislikes AS dislikes, agg.guardrails AS guardrails, f.text AS first_message, f.topic AS topic
            FROM agg JOIN f ON f.session_id = agg.session_id
            WHERE agg.turns > 0 {filt}
            ORDER BY agg.started DESC LIMIT {int(limit)} OFFSET {int(offset)}""",
            cfg.tenant_id,
            period,
            **({"q": f"%{q.lower()}%"} if q else {}),
        )
        return {
            "items": [
                {**r, "started": _iso(r["started"]), "topic_label": labels.get(r["topic"] or "", "Diğer")}
                for r in rows
            ],
            "limit": limit,
            "offset": offset,
        }

    async def conversation(self, cfg: TenantConfig, session_id: str) -> list[dict[str, Any]]:
        d = self.d
        rows = await self.repo.rows(
            f"""SELECT event_type, ts, model, latency_ms, payload FROM {d.table}
                WHERE tenant_id = {d.p("tenant")} AND session_id = {d.p("sid")} ORDER BY ts""",
            {"tenant": cfg.tenant_id, "sid": session_id},
        )
        return [{**r, "ts": _iso(r["ts"])} for r in rows]


def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
