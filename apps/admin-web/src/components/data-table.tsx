import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useState } from "react";
import { cn } from "./ui";

export function DataTable<T>({
  data,
  columns,
  empty = "Bu aralıkta veri yok.",
  onRowClick,
  dense = false,
}: {
  data: T[];
  columns: ColumnDef<T, unknown>[];
  empty?: string;
  onRowClick?: (row: T) => void;
  dense?: boolean;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  if (!data.length) return <p className="px-4 py-8 text-center text-sm text-muted">{empty}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" data-testid="data-table">
        <thead className="bg-surface text-left text-xs uppercase tracking-wide text-muted">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th key={h.id} className="px-4 py-2 font-semibold">
                  {h.isPlaceholder ? null : (
                    <button type="button" className="inline-flex items-center gap-1" onClick={h.column.getToggleSortingHandler()}>
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getIsSorted() === "asc" ? <ArrowUp className="size-3" /> : null}
                      {h.column.getIsSorted() === "desc" ? <ArrowDown className="size-3" /> : null}
                    </button>
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-line">
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className={cn(onRowClick && "cursor-pointer hover:bg-surface")}
              onClick={onRowClick ? () => onRowClick(row.original) : undefined}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className={cn("px-4", dense ? "py-1.5" : "py-2.5")}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
