import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { EChart } from "@/components/chart";
import { DataTable } from "@/components/data-table";
import { PageHeader, Panel } from "@/components/panel";
import { Badge, ErrorNote, Spinner } from "@/components/ui";
import { dateTime, delta, int, pct } from "@/lib/format";
import { useDashboard } from "@/lib/hooks";
import type { DemandData } from "@/lib/types";

type Topic = DemandData["topics"][number];
const columns: ColumnDef<Topic, unknown>[] = [
  { header: "Kategori", accessorKey: "label" },
  { header: "Mesaj", accessorKey: "count", cell: (c) => int(c.getValue() as number) },
  { header: "Pay", accessorKey: "share", cell: (c) => pct(c.getValue() as number) },
  { header: "Önceki dönem", accessorKey: "previous", cell: (c) => int(c.getValue() as number) },
  {
    header: "Değişim",
    accessorKey: "growth_pct",
    cell: (c) => {
      const v = c.getValue() as number | null;
      return <Badge tone={v == null ? "neutral" : v >= 0 ? "good" : "bad"}>{delta(v)}</Badge>;
    },
  },
];

export function DemandPage() {
  const { data, error, isLoading } = useDashboard<DemandData>("demand");
  const option = useMemo(
    () =>
      data && {
        tooltip: { trigger: "axis" },
        grid: { left: 170, right: 30, top: 10, bottom: 20 },
        xAxis: { type: "value" },
        yAxis: { type: "category", inverse: true, data: data.topics.map((t) => t.label) },
        series: [{ type: "bar", data: data.topics.map((t) => t.count), barMaxWidth: 22, label: { show: true, position: "right" } }],
      },
    [data],
  );
  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  return (
    <div className="space-y-5">
      <PageHeader title="Müşteri talepleri" description="Müşterilerin hangi sorunlarla geldiği, yükselen konular ve örnek konuşmalar." />
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Sorun kategorileri" dataset="talepler">
          {option ? <EChart option={option} label="Sorun kategorileri grafiği" /> : null}
        </Panel>
        <Panel title="Yükselen konular" subtitle="Önceki eşit uzunluktaki döneme göre" dataset="talepler">
          <DataTable data={data.rising.length ? data.rising : data.topics} columns={columns} dense />
        </Panel>
      </div>
      <Panel title="Tüm kategoriler" dataset="talepler">
        <DataTable data={data.topics} columns={columns} />
      </Panel>
      <Panel title="Örnek konuşmalar" subtitle="En son kullanıcı mesajları (kişisel veriler maskelenmiştir)" dataset="konusmalar">
        <ul className="divide-y divide-line">
          {data.samples.map((s) => (
            <li key={`${s.session_id}-${s.ts}`} className="flex items-start gap-3 px-4 py-2.5 text-sm">
              <span className="w-24 shrink-0 text-xs text-muted">{dateTime(s.ts)}</span>
              <span className="flex-1">“{s.text}”</span>
              <Badge tone="primary">{s.topic_label}</Badge>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
