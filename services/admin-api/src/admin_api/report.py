"""Monthly PDF report (tenant branded). HTML via Jinja2 -> PDF via WeasyPrint (Chromium fallback locally, ADR 003)."""

from __future__ import annotations

import asyncio
import base64
import calendar
import os
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, select_autoescape

from magaza_core.contracts import TenantConfig
from magaza_core.money import format_try
from magaza_core.pdf import html_to_pdf

from .analytics import Dashboards, Period

MONTHS_TR = [
    "",
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
]

TEMPLATE = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>{{ cfg.display_name }} — {{ month_label }} raporu</title>
<style>
  @page { size: A4; margin: 16mm 14mm; }
  body { font-family: "Segoe UI", "DejaVu Sans", Arial, sans-serif; color: #111827; font-size: 10.5pt; }
  header { display: flex; align-items: center; gap: 14px; border-bottom: 3px solid {{ primary }}; padding-bottom: 10px; }
  header img { width: 48px; height: 48px; }
  header h1 { margin: 0; font-size: 18pt; } header p { margin: 2px 0 0; color: #6b7280; }
  h2 { font-size: 12.5pt; color: {{ primary }}; margin: 18px 0 6px; }
  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .kpi { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px 10px; }
  .kpi .v { font-size: 14pt; font-weight: 700; } .kpi .l { color: #6b7280; font-size: 8.5pt; }
  table { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
  th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid #e5e7eb; }
  th { background: #f3f4f6; }
  .bar { height: 8px; background: {{ primary }}; border-radius: 4px; }
  footer { margin-top: 18px; color: #9ca3af; font-size: 8pt; }
</style></head><body>
<header><img src="{{ logo }}" alt=""><div><h1>{{ cfg.display_name }}</h1><p>Mağaza Asistanım aylık raporu · {{ month_label }}</p></div></header>
<h2>Yönetici özeti</h2>
<div class="kpis">
  <div class="kpi"><div class="v">{{ money(ex.kpis.assisted_revenue) }}</div><div class="l">Asistan destekli ciro</div></div>
  <div class="kpi"><div class="v">{{ pct(ex.kpis.conversion_assisted) }} / {{ pct(ex.kpis.conversion_unassisted) }}</div><div class="l">Dönüşüm: asistanlı / asistansız</div></div>
  <div class="kpi"><div class="v">{{ pctn(ex.kpis.aov_diff_pct) }}</div><div class="l">Sepet ortalaması farkı</div></div>
  <div class="kpi"><div class="v">{{ pct(ex.kpis.cross_sell_acceptance) }}</div><div class="l">Çapraz satış kabul oranı</div></div>
  <div class="kpi"><div class="v">{{ ex.kpis.conversations }}</div><div class="l">Konuşma</div></div>
  <div class="kpi"><div class="v">{{ ex.kpis.orders }}</div><div class="l">Sipariş</div></div>
  <div class="kpi"><div class="v">{{ pctn(ex.kpis.holdout_uplift_pct) }}</div><div class="l">Holdout'a göre dönüşüm artışı</div></div>
  <div class="kpi"><div class="v">{{ pct(q.kpis.like_rate) }}</div><div class="l">Beğeni oranı</div></div>
</div>
<h2>Dönüşüm hunisi</h2>
<table><tr><th>Aşama</th><th>Ziyaretçi</th><th style="width:45%"></th></tr>
{% for s in funnel.stages %}<tr><td>{{ s.label }}</td><td>{{ s.count }}</td><td><div class="bar" style="width: {{ (s.overall_rate or 0) * 100 }}%"></div></td></tr>{% endfor %}
</table>
<h2>Müşteri talepleri</h2>
<table><tr><th>Kategori</th><th>Mesaj</th><th>Pay</th><th>Değişim</th></tr>
{% for t in demand.topics[:8] %}<tr><td>{{ t.label }}</td><td>{{ t.count }}</td><td>{{ pct(t.share) }}</td><td>{{ pctn(t.growth_pct) }}</td></tr>{% endfor %}
</table>
<h2>En çok önerilen ürünler</h2>
<table><tr><th>Ürün</th><th>Önerildi</th><th>Sepete</th><th>Satış</th></tr>
{% for p in products.top[:8] %}<tr><td>{{ p.title }}</td><td>{{ p.shown }}</td><td>{{ p.added }}</td><td>{{ p.ordered }}</td></tr>{% endfor %}
</table>
<h2>Kullanım ve maliyet</h2>
<table><tr><th>Ay</th><th>Konuşma</th><th>Mesaj</th><th>Token (girdi/çıktı)</th><th>Tahmini maliyet</th></tr>
{% for u in usage.rows %}<tr><td>{{ u.month }}</td><td>{{ u.conversations }}</td><td>{{ u.messages }}</td><td>{{ u.tokens_in }} / {{ u.tokens_out }}</td><td>${{ "%.2f"|format(u.cost_usd) }}</td></tr>{% endfor %}
</table>
<footer>Oluşturma: {{ today }} · Tutarlar KDV dahil sipariş toplamlarıdır; maliyet tahmini birim fiyatlar config/llm.yaml'dan hesaplanır.</footer>
</body></html>"""


def _logo(cfg: TenantConfig) -> str:
    logo_dir = Path(os.environ.get("TENANT_LOGO_DIR", "data/demo"))
    candidate = logo_dir / cfg.tenant_id / "logo.svg"
    if candidate.exists():
        return "data:image/svg+xml;base64," + base64.b64encode(candidate.read_bytes()).decode()
    if cfg.theme.logo_url and cfg.theme.logo_url.startswith("http"):
        return cfg.theme.logo_url
    initials = "".join(w[0] for w in cfg.display_name.split()[:2]).upper()
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{cfg.theme.primary_color}"/>'
        f'<text x="32" y="41" font-size="24" font-family="Arial" font-weight="700" fill="#fff" text-anchor="middle">{initials}</text></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def month_period(month: str) -> Period:
    year, mon = (int(x) for x in month.split("-"))
    return Period(date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1]))


async def build_report(dash: Dashboards, cfg: TenantConfig, month: str) -> bytes:
    period = month_period(month)
    data: dict[str, Any] = {
        "ex": await dash.executive(cfg, period),
        "funnel": await dash.funnel(cfg, period),
        "demand": await dash.demand(cfg, period),
        "products": await dash.products(cfg, period),
        "q": await dash.quality(cfg, period),
        "usage": await dash.usage([cfg.tenant_id], period),
    }
    env = Environment(autoescape=select_autoescape(default=True))
    html = env.from_string(TEMPLATE).render(
        cfg=cfg,
        primary=cfg.theme.primary_color,
        logo=_logo(cfg),
        month_label=f"{MONTHS_TR[period.start.month]} {period.start.year}",
        today=date.today().isoformat(),
        money=lambda v: format_try(v or 0),
        pct=lambda v: "—" if v is None else f"%{v * 100:.1f}".replace(".", ","),
        pctn=lambda v: "—" if v is None else f"%{v:.1f}".replace(".", ","),
        **data,
    )
    return await asyncio.to_thread(html_to_pdf, html)
