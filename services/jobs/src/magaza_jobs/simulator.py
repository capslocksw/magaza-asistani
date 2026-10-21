"""Synthetic analytics generator (is_synthetic=true): 90 days of realistic visitor journeys for both demo tenants.

    python -m magaza_jobs.simulator --out data/analytics/fixture.duckdb [--days 90] [--seed 7]

Writes the `analytics_events` table (same columns as the AnalyticsEvent contract; payload as JSON) used by the
admin dashboards locally (DuckDB) and mirrors the BigQuery table layout used in production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb

from magaza_core.contracts import Product
from magaza_core.llm_config import load_llm_config

from .demo_data import build_tenant

COLUMNS = (
    "event_id VARCHAR, event_type VARCHAR, tenant_id VARCHAR, session_id VARCHAR, visitor_id_hash VARCHAR, "
    "ts TIMESTAMP, model VARCHAR, tokens_in BIGINT, tokens_out BIGINT, latency_ms BIGINT, cost_usd_est DOUBLE, "
    "is_synthetic BOOLEAN, payload JSON"
)


@dataclass(frozen=True)
class Profile:
    visits_per_day: int
    weekend_factor: float
    open_rate: float
    chat_rate: float
    base_conversion: float
    assisted_conversion: float
    aov_base: float
    aov_assisted: float
    quote_rate: float
    topics: dict[str, tuple[float, list[str]]]  # topic -> (weight, sample messages)
    rising: str
    unmet: list[str]


PROFILES: dict[str, Profile] = {
    "yapi-market": Profile(
        visits_per_day=520,
        weekend_factor=1.35,
        open_rate=0.16,
        chat_rate=0.78,
        base_conversion=0.028,
        assisted_conversion=0.085,
        aov_base=540,
        aov_assisted=760,
        quote_rate=0.0,
        topics={
            "montaj_sabitleme": (
                0.30,
                [
                    "Kornişim koptu, matkabım yok",
                    "Aynayı duvara nasıl asarım?",
                    "Beton duvara raf asacağım",
                    "Tablo asmak için ne lazım?",
                ],
            ),
            "boya_badana": (
                0.24,
                [
                    "Salonu boyayacağım, neler lazım?",
                    "Tavan sararmış, hangi boya?",
                    "Dış cepheyi yenileyeceğim",
                    "Kaç kova boya gerekir?",
                ],
            ),
            "banyo_tesisat": (
                0.20,
                [
                    "Banyo derzleri karardı",
                    "Musluk damlatıyor",
                    "Silikon küflenmiş",
                    "Rezervuar su kaçırıyor",
                ],
            ),
            "yapistirma_onarim": (
                0.13,
                ["Kırılan kupayı yapıştırmak istiyorum", "Sandalyem sallanıyor", "Kapı kasasında boşluk var"],
            ),
            "elektrikli_alet": (0.08, ["Hangi akülü vidalamayı alayım?", "Betona delik için matkap"]),
            "hirdavat": (0.05, ["Mobilya için vida seti", "Menteşe değiştireceğim"]),
        },
        rising="banyo_tesisat",
        unmet=[
            "buzdolabı tamiri",
            "klima montajı",
            "parke cilası",
            "çim biçme makinesi",
            "mutfak dolabı kapağı",
            "fayans kesme makinesi",
        ],
    ),
    "ambalaj": Profile(
        visits_per_day=190,
        weekend_factor=0.55,
        open_rate=0.23,
        chat_rate=0.82,
        base_conversion=0.046,
        assisted_conversion=0.118,
        aov_base=2450,
        aov_assisted=3380,
        quote_rate=0.07,
        topics={
            "kirilacak_urun": (
                0.32,
                [
                    "2 kg seramik kupa göndereceğim, hangi koli?",
                    "Cam şişe nasıl paketlenir?",
                    "Porselen tabak takımı göndereceğim",
                ],
            ),
            "koli_secimi": (
                0.24,
                ["40x30x30 koli lazım", "15 kg ürün için hangi koli?", "Kitap göndermek için koli"],
            ),
            "toplu_siparis": (
                0.16,
                ["Ayda 1000 koli gönderiyorum, teklif alabilir miyim?", "Kurumsal fatura ile toplu alım"],
            ),
            "paletleme": (0.12, ["Paletimi nasıl sarmalıyım?", "Palet köşeleri eziliyor"]),
            "bantlama": (0.09, ["Ağır koliler için bant", "Bant tabancası önerir misiniz?"]),
            "kargo_poset_etiket": (0.07, ["Tekstil için kargo poşeti", "Termal etiket lazım"]),
        },
        rising="toplu_siparis",
        unmet=[
            "forklift kiralama",
            "ahşap palet",
            "vakumlu poşet makinesi",
            "özel baskılı koli",
            "soğuk zincir kutusu",
        ],
    ),
}


def _hash(*parts: str) -> str:
    return hashlib.sha256(":".join(parts).encode()).hexdigest()[:32]


class Writer:
    def __init__(self, fh: Any, cost: Any) -> None:
        self.fh = fh
        self.cost = cost
        self.count = 0

    def emit(
        self,
        event_type: str,
        tenant: str,
        session: str | None,
        visitor: str,
        ts: datetime,
        payload: dict[str, Any],
        **kw: Any,
    ) -> None:
        model = kw.get("model")
        tin, tout = kw.get("tokens_in", 0), kw.get("tokens_out", 0)
        row = {
            "event_id": uuid.UUID(int=random.getrandbits(128)).hex,
            "event_type": event_type,
            "tenant_id": tenant,
            "session_id": session,
            "visitor_id_hash": visitor,
            "ts": ts.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "model": model,
            "tokens_in": tin,
            "tokens_out": tout,
            "latency_ms": kw.get("latency_ms"),
            "cost_usd_est": self.cost(model, tin, tout, ts) if model else 0.0,
            "is_synthetic": True,
            "payload": payload,
        }
        self.fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.count += 1


def _pick_topic(rng: random.Random, profile: Profile, progress: float) -> str:
    topics = list(profile.topics)
    weights = [w * (1 + 1.6 * progress if t == profile.rising else 1) for t, (w, _) in profile.topics.items()]
    return rng.choices(topics, weights=weights)[0]


def simulate_tenant(
    w: Writer, tenant_id: str, products: list[Product], days: int, end: date, rng: random.Random, model: str
) -> None:
    p = PROFILES[tenant_id]
    in_stock = [x for x in products if x.stock > 0]
    out_of_stock = [x for x in products if x.stock == 0]
    by_sku = {x.sku: x for x in products}
    keyword_index: dict[str, list[Product]] = {}
    for topic, (_, samples) in p.topics.items():
        words = {w.lower()[:5] for s in samples for w in s.split() if len(w) > 3}
        keyword_index[topic] = [
            x for x in in_stock if any(wd in x.title.lower() or wd in " ".join(x.tags) for wd in words)
        ] or in_stock
    for day_index in range(days):
        day = end - timedelta(days=days - 1 - day_index)
        progress = day_index / max(1, days - 1)
        weekday = day.weekday()
        volume = p.visits_per_day * (p.weekend_factor if weekday >= 5 else 1.0) * (0.85 + 0.3 * progress)
        volume *= 1 + 0.08 * math.sin(day_index / 6.0)
        for _ in range(int(rng.gauss(volume, volume * 0.05))):
            visitor = _hash(tenant_id, str(rng.getrandbits(64)))
            group = "control" if rng.random() < 0.10 else "assistant"
            ts = datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(
                seconds=rng.randint(7 * 3600, 23 * 3600)
            )
            w.emit("visit", tenant_id, None, visitor, ts, {"group": group})
            assisted = False
            cart_skus: list[str] = []
            if group == "assistant" and rng.random() < p.open_rate:
                ts += timedelta(seconds=rng.randint(5, 120))
                w.emit("widget_open", tenant_id, None, visitor, ts, {})
                if rng.random() < p.chat_rate:
                    assisted = True
                    session = f"s_{uuid.UUID(int=rng.getrandbits(128)).hex[:24]}"
                    turns = rng.choices([1, 2, 3, 4], weights=[0.45, 0.3, 0.17, 0.08])[0]
                    topic = _pick_topic(rng, p, progress)
                    for turn in range(1, turns + 1):
                        ts += timedelta(seconds=rng.randint(10, 90))
                        unmet = rng.random() < 0.07
                        text = rng.choice(p.unmet) + " var mı?" if unmet else rng.choice(p.topics[topic][1])
                        w.emit(
                            "user_message",
                            tenant_id,
                            session,
                            visitor,
                            ts,
                            {"text": text, "topic": None if unmet else topic, "turn": turn},
                        )
                        results = (
                            []
                            if unmet
                            else rng.sample(keyword_index[topic], min(6, len(keyword_index[topic])))
                        )
                        w.emit(
                            "tool_call",
                            tenant_id,
                            session,
                            visitor,
                            ts,
                            {
                                "tool": "search_products",
                                "query": text,
                                "result_count": len(results),
                                "skus": [x.sku for x in results],
                                "zero_result": not results,
                            },
                            latency_ms=rng.randint(40, 180),
                        )
                        oos = rng.random() < 0.05 and bool(out_of_stock)
                        shown: list[str] = []
                        bundle_id = None
                        if results:
                            main = results[0]
                            comps = [s for s in main.complement_skus if s in by_sku][: rng.randint(1, 3)]
                            shown = [main.sku, *comps]
                            bundle_id = f"b_{uuid.UUID(int=rng.getrandbits(128)).hex[:12]}"
                            w.emit(
                                "tool_call",
                                tenant_id,
                                session,
                                visitor,
                                ts,
                                {"tool": "propose_bundle", "ok": True, "bundle_id": bundle_id, "skus": shown},
                                latency_ms=rng.randint(5, 40),
                            )
                        latency = int(rng.lognormvariate(7.3, 0.35))
                        tin, tout = rng.randint(2800, 9500), rng.randint(140, 520)
                        dont_know = rng.random() < (0.03 + (0.6 if unmet else 0))
                        guardrails = ["grounding_redirect"] if rng.random() < 0.025 else []
                        if rng.random() < 0.004:
                            guardrails.append("rate_limited")
                        oos_sku = rng.choice(out_of_stock).sku if oos else None
                        ts += timedelta(milliseconds=latency)
                        w.emit(
                            "agent_message",
                            tenant_id,
                            session,
                            visitor,
                            ts,
                            {
                                "message_id": f"m_{rng.getrandbits(48):x}",
                                "text": "Önerilen paket ve kullanım adımları…"
                                if shown
                                else "Bu ürünü katalogda bulamadım.",
                                "skus": shown,
                                "bundle_id": bundle_id,
                                "bundle_skus": shown,
                                "dont_know": dont_know,
                                "guardrails": guardrails,
                                "unmet": unmet or oos,
                                "unmet_reason": "not_in_catalog"
                                if unmet
                                else ("out_of_stock" if oos else None),
                                "unmet_query": text if unmet else None,
                                "out_of_stock_sku": oos_sku,
                                "topic": None if unmet else topic,
                            },
                            model=model,
                            tokens_in=tin,
                            tokens_out=tout,
                            latency_ms=latency,
                        )
                        if shown:
                            w.emit(
                                "product_shown",
                                tenant_id,
                                session,
                                visitor,
                                ts,
                                {"skus": shown, "bundle_id": bundle_id},
                            )
                            if rng.random() < 0.36:
                                added = shown if rng.random() < 0.55 else shown[: rng.randint(1, len(shown))]
                                ts += timedelta(seconds=rng.randint(3, 40))
                                value = round(sum(by_sku[s].price for s in added), 2)
                                w.emit(
                                    "add_to_cart",
                                    tenant_id,
                                    session,
                                    visitor,
                                    ts,
                                    {
                                        "bundle_id": bundle_id,
                                        "skus": added,
                                        "value": value,
                                        "items": [
                                            {"sku": s, "qty": 1, "price": by_sku[s].price} for s in added
                                        ],
                                    },
                                )
                                cart_skus += added
                        if rng.random() < 0.16:
                            w.emit(
                                "feedback",
                                tenant_id,
                                session,
                                visitor,
                                ts,
                                {"rating": "up" if rng.random() < (0.55 if dont_know else 0.83) else "down"},
                            )
                        if p.quote_rate and topic == "toplu_siparis" and rng.random() < p.quote_rate * 4:
                            w.emit(
                                "quote_request",
                                tenant_id,
                                session,
                                visitor,
                                ts,
                                {
                                    "quote_id": f"Q-{rng.getrandbits(24):06X}",
                                    "source": "widget_form",
                                    "skus": shown,
                                    "email": "[e-posta]",
                                },
                            )
                        if rng.random() < 0.35:
                            break  # abandoned the conversation
            rate = p.assisted_conversion * (1.5 if cart_skus else 0.7) if assisted else p.base_conversion
            if rng.random() < rate:
                ts += timedelta(minutes=rng.randint(2, 50))
                aov = rng.lognormvariate(math.log(p.aov_assisted if assisted else p.aov_base), 0.45)
                extra = rng.sample(in_stock, rng.randint(1, 3))
                items: list[dict[str, Any]] = [
                    {"sku": s, "qty": 1, "price": by_sku[s].price} for s in cart_skus
                ] + [{"sku": x.sku, "qty": max(1, round(aov / 3 / x.price)), "price": x.price} for x in extra]
                total = round(sum(i["price"] * i["qty"] for i in items), 2)
                w.emit(
                    "order",
                    tenant_id,
                    None,
                    visitor,
                    ts,
                    {
                        "order_id": f"ORD-{rng.getrandbits(40):X}",
                        "total": total,
                        "currency": "TRY",
                        "items": items,
                        "assisted": assisted,
                        "group": group,
                    },
                )


def generate(out: Path, days: int = 90, seed: int = 7, end: date | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    rng = random.Random(seed)
    random.seed(seed)
    end = end or datetime.now(UTC).date()
    cfg = load_llm_config()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        jsonl = Path(tmp) / "events.jsonl"
        with jsonl.open("w", encoding="utf-8") as fh:
            writer = Writer(fh, cfg.estimate_cost_usd)
            for tenant_id in PROFILES:
                simulate_tenant(
                    writer,
                    tenant_id,
                    build_tenant(tenant_id).products,
                    days,
                    end,
                    rng,
                    cfg.chat.default_model,
                )
        if out.exists():
            out.unlink()
        con = duckdb.connect(str(out))
        con.execute(f"CREATE TABLE analytics_events ({COLUMNS})")
        con.execute(
            f"INSERT INTO analytics_events SELECT * FROM read_json('{jsonl.as_posix()}', format='newline_delimited', columns={{{_columns_struct()}}})"
        )
        con.execute("CREATE INDEX idx_tenant_ts ON analytics_events (tenant_id, ts)")
        counts = dict(
            con.execute("SELECT tenant_id, count(*) FROM analytics_events GROUP BY 1 ORDER BY 1").fetchall()
        )
        con.close()
    return {
        "events": writer.count,
        "by_tenant": counts,
        "days": days,
        "end": end.isoformat(),
        "seconds": round(time.perf_counter() - started, 1),
    }


def _columns_struct() -> str:
    pairs = [c.strip().split(" ", 1) for c in COLUMNS.split(", ")]
    return ", ".join(f"'{name}': '{kind}'" for name, kind in pairs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic analytics fixture")
    parser.add_argument("--out", default="data/analytics/fixture.duckdb", type=Path)
    parser.add_argument("--days", default=90, type=int)
    parser.add_argument("--seed", default=7, type=int)
    args = parser.parse_args()
    print(json.dumps(generate(args.out, args.days, args.seed), ensure_ascii=False))


if __name__ == "__main__":
    main()
