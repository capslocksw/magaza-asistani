import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { EChart } from "@/components/chart";
import { DataTable } from "@/components/data-table";
import { Kpi, PageHeader, Panel } from "@/components/panel";
import { ErrorNote, Spinner } from "@/components/ui";
import { apiGet, qs } from "@/lib/api";
import { int, usd } from "@/lib/format";
import { useDashboard } from "@/lib/hooks";
import { useFilters } from "@/lib/state";
import type { UsageData, UsageRow } from "@/lib/types";

const columns: ColumnDef<UsageRow, unknown>[] = [
  { header: "Tenant", accessorKey: "tenant_id" },
  { header: "Ay", accessorKey: "month" },
  { header: "Konuşma", accessorKey: "conversations", cell: (c) => int(c.getValue() as number) },
  { header: "Mesaj", accessorKey: "messages", cell: (c) => int(c.getValue() as number) },
  { header: "Girdi token", accessorKey: "tokens_in", cell: (c) => int(c.getValue() as number) },
  { header: "Çıktı token", accessorKey: "tokens_out", cell: (c) => int(c.getValue() as number) },
  { header: "Tahmini maliyet", accessorKey: "cost_usd", cell: (c) => usd(c.getValue() as number) },
];

export function UsagePage() {
  const { data, error, isLoading } = useDashboard<UsageData>("usage");
  const { range } = useFilters();
  const billing = useQuery({
    queryKey: ["billing", range.start, range.end],
    queryFn: () => apiGet<UsageData>(`/api/billing${qs({ start: range.start, end: range.end })}`),
  });
  const option = useMemo(
    () =>
      data && {
        tooltip: { trigger: "axis" },
        legend: { top: 0 },
        grid: { left: 60, right: 60, top: 34, bottom: 30 },
        xAxis: { type: "category", data: data.rows.map((r) => r.month) },
        yAxis: [
          { type: "value", name: "Mesaj" },
          { type: "value", name: "USD", splitLine: { show: false } },
        ],
        series: [
          { name: "Mesaj", type: "bar", data: data.rows.map((r) => r.messages), barMaxWidth: 36 },
          { name: "Tahmini maliyet (USD)", type: "line", yAxisIndex: 1, data: data.rows.map((r) => r.cost_usd) },
        ],
      },
    [data],
  );
  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  const t = data.totals;
  return (
    <div className="space-y-5">
      <PageHeader title="Kullanım ve maliyet" description="Konuşma, mesaj, token ve tahmini model maliyeti (birim fiyatlar config/llm.yaml) — faturalama raporu." />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Konuşma" value={int(t.conversations)} />
        <Kpi label="Mesaj" value={int(t.messages)} />
        <Kpi label="Token (girdi / çıktı)" value={`${int(t.tokens_in / 1000)}K / ${int(t.tokens_out / 1000)}K`} />
        <Kpi label="Tahmini maliyet" value={usd(t.cost_usd)} hint="USD, model fiyatlarına göre" />
      </div>
      <Panel title="Aylık kullanım" dataset="kullanim">
        {option ? <EChart option={option} label="Aylık kullanım ve maliyet grafiği" /> : null}
      </Panel>
      <Panel title="Faturalama: tenant / ay" subtitle="Erişiminiz olan tüm tenant'lar" dataset="faturalama" csvPath="/api/export/faturalama.csv">
        {billing.data ? <DataTable data={billing.data.rows} columns={columns} dense /> : <Spinner />}
      </Panel>
    </div>
  );
}
