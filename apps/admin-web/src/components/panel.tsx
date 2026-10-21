import { Download } from "lucide-react";
import { useState, type ReactNode } from "react";
import { download, qs } from "@/lib/api";
import { useFilters } from "@/lib/state";
import { Button, Card, cn } from "./ui";

export function CsvButton({ dataset }: { dataset: string }) {
  const { tenantId, range } = useFilters();
  const [busy, setBusy] = useState(false);
  const [sep, setSep] = useState<"," | ";">(";");
  return (
    <div className="flex items-center gap-1">
      <label className="sr-only" htmlFor={`sep-${dataset}`}>
        Ayraç
      </label>
      <select
        id={`sep-${dataset}`}
        value={sep}
        onChange={(e) => setSep(e.target.value as "," | ";")}
        className="h-8 rounded-md border border-line bg-white px-1 text-xs"
        title="CSV ayracı"
      >
        <option value=";">;</option>
        <option value=",">,</option>
      </select>
      <Button
        variant="outline"
        size="sm"
        disabled={busy || !tenantId}
        data-testid={`csv-${dataset}`}
        onClick={async () => {
          setBusy(true);
          try {
            await download(`/api/tenants/${tenantId}/export/${dataset}.csv${qs({ start: range.start, end: range.end, sep })}`, `${dataset}.csv`);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Download aria-hidden="true" /> CSV indir
      </Button>
    </div>
  );
}

export function Panel({
  title,
  subtitle,
  dataset,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  dataset?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line px-4 py-3">
        <div>
          <h2 className="text-sm font-bold">{title}</h2>
          {subtitle ? <p className="text-xs text-muted">{subtitle}</p> : null}
        </div>
        {dataset ? <CsvButton dataset={dataset} /> : null}
      </div>
      <div>{children}</div>
    </Card>
  );
}

export function Kpi({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "good" | "bad" }) {
  return (
    <Card className="p-4" data-testid="kpi">
      <p className="text-xs font-medium text-muted">{label}</p>
      <p className={cn("mt-1 text-2xl font-bold tracking-tight", tone === "good" && "text-good", tone === "bad" && "text-bad")}>{value}</p>
      {hint ? <p className="mt-0.5 text-xs text-muted">{hint}</p> : null}
    </Card>
  );
}

export function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-5">
      <h1 className="text-xl font-bold tracking-tight">{title}</h1>
      <p className="text-sm text-muted">{description}</p>
    </div>
  );
}
