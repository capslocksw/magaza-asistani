import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { EChart } from "@/components/chart";
import { DataTable } from "@/components/data-table";
import { PageHeader, Panel } from "@/components/panel";
import { ErrorNote, Spinner } from "@/components/ui";
import { int, pct } from "@/lib/format";
import { useDashboard } from "@/lib/hooks";
import type { FunnelData } from "@/lib/types";

type Stage = FunnelData["stages"][number];
const columns: ColumnDef<Stage, unknown>[] = [
  { header: "Aşama", accessorKey: "label" },
  { header: "Ziyaretçi", accessorKey: "count", cell: (c) => int(c.getValue() as number) },
  { header: "Önceki adıma", accessorKey: "step_rate", cell: (c) => pct(c.getValue() as number | null) },
  { header: "Toplam", accessorKey: "overall_rate", cell: (c) => pct(c.getValue() as number | null, 2) },
];

export function FunnelPage() {
  const { data, error, isLoading } = useDashboard<FunnelData>("funnel");
  const option = useMemo(
    () =>
      data && {
        tooltip: { trigger: "item", formatter: "{b}: {c}" },
        series: [
          {
            type: "funnel",
            left: "10%",
            width: "80%",
            sort: "none",
            minSize: "8%",
            label: { show: true, position: "inside", formatter: "{b}\n{c}", color: "#fff", fontWeight: 600 },
            data: data.stages.map((s) => ({ name: s.label, value: s.count })),
          },
        ],
      },
    [data],
  );
  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  return (
    <div className="space-y-5">
      <PageHeader title="Dönüşüm hunisi" description="Widget açıldı → konuşma → ürün önerildi → sepete eklendi → sipariş (tekil ziyaretçi)." />
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Huni" dataset="huni">
          {option ? <EChart option={option} height={360} label="Dönüşüm hunisi grafiği" /> : null}
        </Panel>
        <Panel title="Adım adım dönüşüm" dataset="huni">
          <DataTable data={data.stages} columns={columns} />
        </Panel>
      </div>
    </div>
  );
}
