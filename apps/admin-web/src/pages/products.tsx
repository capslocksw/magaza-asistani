import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";
import { EChart } from "@/components/chart";
import { DataTable } from "@/components/data-table";
import { PageHeader, Panel } from "@/components/panel";
import { ErrorNote, Spinner } from "@/components/ui";
import { int, pct } from "@/lib/format";
import { useDashboard } from "@/lib/hooks";
import type { ProductsData } from "@/lib/types";

const topCols: ColumnDef<ProductsData["top"][number], unknown>[] = [
  { header: "Ürün", accessorKey: "title", cell: (c) => <span title={c.row.original.sku}>{c.getValue() as string}</span> },
  { header: "Önerildi", accessorKey: "shown", cell: (c) => int(c.getValue() as number) },
  { header: "Sepete", accessorKey: "added", cell: (c) => int(c.getValue() as number) },
  { header: "Satış", accessorKey: "ordered", cell: (c) => int(c.getValue() as number) },
  { header: "Öneri→sepet", accessorKey: "shown_to_cart", cell: (c) => pct(c.getValue() as number | null) },
  { header: "Sepet→satış", accessorKey: "cart_to_order", cell: (c) => pct(c.getValue() as number | null) },
];
const pairCols: ColumnDef<ProductsData["pairs"][number], unknown>[] = [
  { header: "Ürün A", accessorKey: "title_a" },
  { header: "Ürün B", accessorKey: "title_b" },
  { header: "Birlikte önerilme", accessorKey: "count", cell: (c) => int(c.getValue() as number) },
];

export function ProductsPage() {
  const { data, error, isLoading } = useDashboard<ProductsData>("products");
  const option = useMemo(() => {
    if (!data) return null;
    const top = data.top.slice(0, 10);
    return {
      tooltip: { trigger: "axis" },
      legend: { top: 0 },
      grid: { left: 200, right: 20, top: 30, bottom: 20 },
      xAxis: { type: "value" },
      yAxis: { type: "category", inverse: true, data: top.map((t) => (t.title.length > 28 ? `${t.title.slice(0, 27)}…` : t.title)) },
      series: [
        { name: "Önerildi", type: "bar", data: top.map((t) => t.shown) },
        { name: "Sepete eklendi", type: "bar", data: top.map((t) => t.added) },
        { name: "Satıldı", type: "bar", data: top.map((t) => t.ordered) },
      ],
    };
  }, [data]);
  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  return (
    <div className="space-y-5">
      <PageHeader title="Ürün ve paket performansı" description="En çok önerilen ürünler, öneri→sepet→satış dönüşümü ve birlikte önerilen ikililer." />
      <Panel title="En çok önerilen 10 ürün" dataset="urunler">
        {option ? <EChart option={option} height={380} label="En çok önerilen ürünler grafiği" /> : null}
      </Panel>
      <Panel title="Ürün bazında öneri → sepet → satış" dataset="urunler">
        <DataTable data={data.top} columns={topCols} dense />
      </Panel>
      <Panel title="Birlikte önerilen ikililer" dataset="birlikte-onerilen">
        <DataTable data={data.pairs} columns={pairCols} dense />
      </Panel>
    </div>
  );
}
