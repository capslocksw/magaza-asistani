import { useMemo } from "react";
import { Link } from "react-router-dom";
import { EChart } from "@/components/chart";
import { Kpi, PageHeader, Panel } from "@/components/panel";
import { Button, ErrorNote, Spinner } from "@/components/ui";
import { int, pct, shortDate } from "@/lib/format";
import { useDashboard } from "@/lib/hooks";
import type { QualityData } from "@/lib/types";
import { ConversationList } from "./conversations";

export function QualityPage() {
  const { data, error, isLoading } = useDashboard<QualityData>("quality");
  const trend = useMemo(
    () =>
      data && {
        tooltip: { trigger: "axis", valueFormatter: (v: number) => pct(v) },
        legend: { top: 0 },
        grid: { left: 50, right: 20, top: 34, bottom: 30 },
        xAxis: { type: "category", data: data.weekly.map((w) => shortDate(w.week)) },
        yAxis: { type: "value", max: 1, axisLabel: { formatter: (v: number) => pct(v, 0) } },
        series: [
          { name: "Beğeni oranı", type: "line", smooth: true, data: data.weekly.map((w) => w.like_rate) },
          { name: "'Bilmiyorum' oranı", type: "line", smooth: true, data: data.weekly.map((w) => w.dont_know_rate) },
        ],
      },
    [data],
  );
  const guardrails = useMemo(
    () =>
      data && {
        tooltip: { trigger: "axis" },
        grid: { left: 190, right: 30, top: 10, bottom: 20 },
        xAxis: { type: "value" },
        yAxis: { type: "category", data: data.guardrails.map((g) => g.label) },
        series: [{ type: "bar", data: data.guardrails.map((g) => g.count), barMaxWidth: 22, label: { show: true, position: "right" } }],
      },
    [data],
  );
  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  const k = data.kpis;
  return (
    <div className="space-y-5">
      <PageHeader title="Konuşma kalitesi" description="Beğeni, 'bilmiyorum' ve terk oranları, guardrail tetiklenmeleri ve konuşma gezgini." />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Beğeni oranı" value={pct(k.like_rate)} hint={`${int(k.feedback_count)} değerlendirme`} tone="good" />
        <Kpi label="'Bilmiyorum' oranı" value={pct(k.dont_know_rate)} />
        <Kpi label="Terk oranı" value={pct(k.abandonment_rate)} hint="Tek mesajda kalan, sepete eklemeyen sohbetler" />
        <Kpi label="Guardrail tetiklenmesi" value={int(k.guardrail_triggers)} hint={`Yanıt süresi ort. ${int(k.latency_avg_ms)} ms · p95 ${int(k.latency_p95_ms)} ms`} />
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Haftalık kalite" dataset="kalite-haftalik">
          {trend ? <EChart option={trend} label="Haftalık beğeni ve bilmiyorum oranı grafiği" /> : null}
        </Panel>
        <Panel title="Guardrail tetiklenmeleri" dataset="kalite-guardrail">
          {guardrails ? <EChart option={guardrails} label="Guardrail tetiklenme grafiği" /> : null}
        </Panel>
      </div>
      <Panel title="Konuşma gezgini" subtitle="Son konuşmalar — ayrıntı için satıra tıklayın" dataset="konusmalar">
        <ConversationList limit={10} />
        <div className="border-t border-line p-3 text-right">
          <Button asChild variant="outline" size="sm">
            <Link to="/konusmalar">Tüm konuşmalar</Link>
          </Button>
        </div>
      </Panel>
    </div>
  );
}
