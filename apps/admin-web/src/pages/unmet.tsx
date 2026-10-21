import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/data-table";
import { Kpi, PageHeader, Panel } from "@/components/panel";
import { ErrorNote, Spinner } from "@/components/ui";
import { int, pct } from "@/lib/format";
import { useDashboard } from "@/lib/hooks";
import type { UnmetData } from "@/lib/types";

const queryCols: ColumnDef<{ query: string; count: number }, unknown>[] = [
  { header: "İstek / arama", accessorKey: "query" },
  { header: "Adet", accessorKey: "count", cell: (c) => int(c.getValue() as number) },
];
const stockCols: ColumnDef<UnmetData["out_of_stock"][number], unknown>[] = [
  { header: "SKU", accessorKey: "sku" },
  { header: "Ürün", accessorKey: "title" },
  { header: "Kayıp talep", accessorKey: "count", cell: (c) => int(c.getValue() as number) },
];

export function UnmetPage() {
  const { data, error, isLoading } = useDashboard<UnmetData>("unmet");
  if (isLoading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  const k = data.kpis;
  return (
    <div className="space-y-5">
      <PageHeader title="Karşılanmayan talep" description="Katalogda olmayan istekler, stok dışı kayıp talep ve sıfır sonuçlu aramalar — ürün gamı fırsatları." />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Karşılanmayan yanıt" value={int(k.unmet_answers)} hint={`Tüm yanıtların ${pct(k.unmet_rate)}'i`} />
        <Kpi label="Sıfır sonuçlu arama" value={int(k.zero_result_searches)} />
        <Kpi label="Stok dışı kayıp talep" value={int(k.out_of_stock_requests)} />
        <Kpi label="Karşılanma oranı" value={pct(k.unmet_rate == null ? null : 1 - k.unmet_rate)} tone="good" />
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Katalogda olmayan istekler" dataset="karsilanmayan-katalog">
          <DataTable data={data.not_in_catalog} columns={queryCols} dense />
        </Panel>
        <Panel title="Sıfır sonuçlu aramalar" dataset="sifir-sonuc">
          <DataTable data={data.zero_result} columns={queryCols} dense />
        </Panel>
      </div>
      <Panel title="Stok dışı kayıp talep" subtitle="Müşterinin istediği ama stokta olmayan ürünler" dataset="karsilanmayan-stok">
        <DataTable data={data.out_of_stock} columns={stockCols} dense />
      </Panel>
    </div>
  );
}
