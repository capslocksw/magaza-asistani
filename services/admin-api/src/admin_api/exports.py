"""CSV exports for every dashboard table/chart (UTF-8 with BOM so Excel opens Turkish text correctly)."""

from __future__ import annotations

import csv
import io
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from magaza_core.contracts import TenantConfig

from .analytics import Dashboards, Period


@dataclass(frozen=True)
class Dataset:
    title: str
    columns: list[tuple[str, str]]  # (key, header)
    load: Callable[[Dashboards, TenantConfig, Period], Awaitable[list[dict[str, Any]]]]


async def _get(
    dash: Dashboards, cfg: TenantConfig, period: Period, name: str, key: str
) -> list[dict[str, Any]]:
    data = await getattr(dash, name)(cfg, period)
    rows: list[dict[str, Any]] = data[key]
    return rows


DATASETS: dict[str, Dataset] = {
    "yonetici-ozeti": Dataset(
        "Haftalık asistan destekli ciro",
        [
            ("week", "Hafta"),
            ("assisted_revenue", "Asistan destekli ciro (TL)"),
            ("revenue", "Toplam ciro (TL)"),
            ("conversations", "Konuşma"),
        ],
        lambda d, c, p: _get(d, c, p, "executive", "weekly"),
    ),
    "huni": Dataset(
        "Dönüşüm hunisi",
        [
            ("label", "Aşama"),
            ("count", "Ziyaretçi"),
            ("step_rate", "Önceki adıma oran"),
            ("overall_rate", "Toplam oran"),
        ],
        lambda d, c, p: _get(d, c, p, "funnel", "stages"),
    ),
    "talepler": Dataset(
        "Sorun kategorileri",
        [
            ("label", "Kategori"),
            ("count", "Mesaj"),
            ("share", "Pay"),
            ("previous", "Önceki dönem"),
            ("growth_pct", "Değişim (%)"),
        ],
        lambda d, c, p: _get(d, c, p, "demand", "topics"),
    ),
    "karsilanmayan-katalog": Dataset(
        "Katalogda olmayan istekler",
        [("query", "İstek"), ("count", "Adet")],
        lambda d, c, p: _get(d, c, p, "unmet", "not_in_catalog"),
    ),
    "karsilanmayan-stok": Dataset(
        "Stok dışı kayıp talep",
        [("sku", "SKU"), ("title", "Ürün"), ("count", "Talep")],
        lambda d, c, p: _get(d, c, p, "unmet", "out_of_stock"),
    ),
    "sifir-sonuc": Dataset(
        "Sıfır sonuçlu aramalar",
        [("query", "Arama"), ("count", "Adet")],
        lambda d, c, p: _get(d, c, p, "unmet", "zero_result"),
    ),
    "urunler": Dataset(
        "En çok önerilen ürünler",
        [
            ("sku", "SKU"),
            ("title", "Ürün"),
            ("shown", "Önerildi"),
            ("added", "Sepete eklendi"),
            ("ordered", "Satıldı"),
            ("shown_to_cart", "Öneri→sepet"),
            ("cart_to_order", "Sepet→satış"),
        ],
        lambda d, c, p: _get(d, c, p, "products", "top"),
    ),
    "birlikte-onerilen": Dataset(
        "Birlikte önerilen ikililer",
        [
            ("sku_a", "SKU A"),
            ("title_a", "Ürün A"),
            ("sku_b", "SKU B"),
            ("title_b", "Ürün B"),
            ("count", "Birlikte önerilme"),
        ],
        lambda d, c, p: _get(d, c, p, "products", "pairs"),
    ),
    "kalite-guardrail": Dataset(
        "Guardrail tetiklenmeleri",
        [("label", "Guardrail"), ("count", "Adet")],
        lambda d, c, p: _get(d, c, p, "quality", "guardrails"),
    ),
    "kalite-haftalik": Dataset(
        "Haftalık konuşma kalitesi",
        [("week", "Hafta"), ("like_rate", "Beğeni oranı"), ("dont_know_rate", "'Bilmiyorum' oranı")],
        lambda d, c, p: _get(d, c, p, "quality", "weekly"),
    ),
    "kullanim": Dataset(
        "Kullanım ve maliyet",
        [
            ("tenant_id", "Tenant"),
            ("month", "Ay"),
            ("conversations", "Konuşma"),
            ("messages", "Mesaj"),
            ("tokens_in", "Girdi token"),
            ("tokens_out", "Çıktı token"),
            ("cost_usd", "Tahmini maliyet (USD)"),
        ],
        lambda d, c, p: _usage(d, c, p),
    ),
    "konusmalar": Dataset(
        "Konuşmalar",
        [
            ("session_id", "Oturum"),
            ("started", "Başlangıç"),
            ("topic_label", "Konu"),
            ("first_message", "İlk mesaj"),
            ("turns", "Mesaj"),
            ("adds", "Sepete ekleme"),
            ("likes", "Beğeni"),
            ("dislikes", "Beğenmeme"),
        ],
        lambda d, c, p: _conversations(d, c, p),
    ),
}


async def _usage(d: Dashboards, c: TenantConfig, p: Period) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = (await d.usage([c.tenant_id], p))["rows"]
    return rows


async def _conversations(d: Dashboards, c: TenantConfig, p: Period) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await d.conversations(c, p, limit=1000))["items"]
    return items


def _fmt(value: Any, sep: str) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text.replace(".", ",") if sep == ";" else text
    return str(value)


def to_csv(dataset: Dataset, rows: list[dict[str, Any]], sep: str = ",") -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=sep, lineterminator="\r\n")
    writer.writerow([header for _, header in dataset.columns])
    for row in rows:
        writer.writerow([_fmt(row.get(key), sep) for key, _ in dataset.columns])
    return ("﻿" + buffer.getvalue()).encode("utf-8")
