import { useMemo } from "react";
import { EChart } from "@/components/chart";
import { Kpi, PageHeader, Panel } from "@/components/panel";
import { ErrorNote, Spinner } from "@/components/ui";
import { delta, formatTRY, int, pct, shortDate } from "@/lib/format";
import { useDashboard } from "@/lib/hooks";
import type { ExecutiveData } from "@/lib/types";

export function ExecutivePage() {
  const { data, error, isLoading } = useDashboard<ExecutiveData>("executive");
  const option = useMemo(
    () =>
      data && {
        tooltip: { trigger: "axis" },
        legend: { top: 0 },
        grid: { left: 70, right: 50, top: 36, bottom: 30 },
        xAxis: { type: "category", data: data.weekly.map((w) => shortDate(w.week)) },
        yAxis: [
          { type: "value", name: "TL", axisLabel: { formatter: (v: number) => `${Math.round(v / 1000)}K` } },
          { type: "value", name: "Konuşma", splitLine: { show: false } },
        ],
        series: [
          { name: "Asistan destekli ciro", type: "bar", data: data.weekly.map((w) => w.assisted_revenue), barMaxWidth: 26 },
          { name: "Konuşma", type: "line", yAxisIndex: 1, smooth: true, data: data.weekly.map((w) => w.conversations) },
        ],
      },
    [data],
  );
  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  const k = data.kpis;
  return (
    <div className="space-y-5">
      <PageHeader title="Yönetici özeti" description="Asistanın satışa etkisi: destekli ciro, dönüşüm, sepet ortalaması ve çapraz satış." />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Asistan destekli ciro" value={formatTRY(k.assisted_revenue)} hint={`Toplam cironun ${pct(k.assisted_revenue_share)}'i`} />
        <Kpi
          label="Dönüşüm: asistanlı / asistansız"
          value={`${pct(k.conversion_assisted)} / ${pct(k.conversion_unassisted)}`}
          hint="Sohbet eden vs. etmeyen ziyaretçiler"
          tone="good"
        />
        <Kpi
          label="Sepet ortalaması farkı"
          value={delta(k.aov_diff_pct)}
          hint={`${k.aov_assisted ? formatTRY(k.aov_assisted) : "—"} vs ${k.aov_unassisted ? formatTRY(k.aov_unassisted) : "—"}`}
          tone={(k.aov_diff_pct ?? 0) >= 0 ? "good" : "bad"}
        />
        <Kpi label="Çapraz satış kabul oranı" value={pct(k.cross_sell_acceptance)} hint="Önerilen paketlerden tamamlayıcısı sepete eklenen" />
        <Kpi label="Konuşma" value={int(k.conversations)} />
        <Kpi label="Sipariş" value={int(k.orders)} />
        <Kpi
          label="Holdout'a göre dönüşüm artışı"
          value={delta(k.holdout_uplift_pct)}
          hint={`Asistan grubu ${pct(k.holdout_conversion_assistant_group, 2)} · kontrol ${pct(k.holdout_conversion_control_group, 2)}`}
          tone={(k.holdout_uplift_pct ?? 0) >= 0 ? "good" : "bad"}
        />
        <Kpi label="Toplam ciro" value={formatTRY(k.revenue)} />
      </div>
      <Panel title="Haftalık trend" subtitle="Asistan destekli ciro ve konuşma sayısı" dataset="yonetici-ozeti">
        {option ? <EChart option={option} label="Haftalık asistan destekli ciro grafiği" /> : null}
      </Panel>
    </div>
  );
}
