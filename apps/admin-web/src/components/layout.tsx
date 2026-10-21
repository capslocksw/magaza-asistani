import {
  BadgeDollarSign,
  ChartNoAxesCombined,
  FileDown,
  Filter,
  Gauge,
  LogOut,
  MessagesSquare,
  PackageSearch,
  SearchX,
  Settings,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { download, setToken } from "@/lib/api";
import { useTenants } from "@/lib/hooks";
import { presetRange, useFilters } from "@/lib/state";
import { Button, cn, Input, Select, Spinner } from "./ui";

export const NAV = [
  { to: "/", label: "Yönetici özeti", icon: ChartNoAxesCombined },
  { to: "/huni", label: "Dönüşüm hunisi", icon: Filter },
  { to: "/talepler", label: "Müşteri talepleri", icon: Sparkles },
  { to: "/karsilanmayan", label: "Karşılanmayan talep", icon: SearchX },
  { to: "/urunler", label: "Ürün ve paket", icon: PackageSearch },
  { to: "/kalite", label: "Konuşma kalitesi", icon: ShieldCheck },
  { to: "/kullanim", label: "Kullanım ve maliyet", icon: BadgeDollarSign },
  { to: "/konusmalar", label: "Konuşmalar", icon: MessagesSquare },
  { to: "/ayarlar", label: "Ayarlar", icon: Settings },
];

function lastMonths(count: number): string[] {
  const now = new Date();
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - i, 1));
    return d.toISOString().slice(0, 7);
  });
}

function MonthlyReport() {
  const { tenantId } = useFilters();
  const months = lastMonths(4);
  const [month, setMonth] = useState(months[1]!);
  const [busy, setBusy] = useState(false);
  return (
    <div className="flex items-center gap-1.5">
      <label htmlFor="report-month" className="sr-only">
        Rapor ayı
      </label>
      <Select id="report-month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-32">
        {months.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </Select>
      <Button
        variant="outline"
        disabled={!tenantId || busy}
        data-testid="pdf-report"
        onClick={async () => {
          setBusy(true);
          try {
            await download(`/api/tenants/${tenantId}/reports/monthly.pdf?month=${month}`, `rapor-${month}.pdf`);
          } finally {
            setBusy(false);
          }
        }}
      >
        <FileDown aria-hidden="true" /> {busy ? "Hazırlanıyor…" : "Aylık raporu PDF indir"}
      </Button>
    </div>
  );
}

function RangePicker() {
  const { range, setRange } = useFilters();
  return (
    <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Tarih aralığı">
      {([7, 30, 90] as const).map((days) => (
        <Button key={days} size="sm" variant={range.preset === days ? "default" : "outline"} onClick={() => setRange(presetRange(days))}>
          Son {days} gün
        </Button>
      ))}
      <label htmlFor="range-start" className="sr-only">
        Başlangıç
      </label>
      <Input id="range-start" type="date" value={range.start} max={range.end} className="h-8 w-36" onChange={(e) => setRange({ ...range, start: e.target.value, preset: "custom" })} />
      <span aria-hidden="true">–</span>
      <label htmlFor="range-end" className="sr-only">
        Bitiş
      </label>
      <Input id="range-end" type="date" value={range.end} min={range.start} className="h-8 w-36" onChange={(e) => setRange({ ...range, end: e.target.value, preset: "custom" })} />
    </div>
  );
}

export function Layout() {
  const tenants = useTenants();
  const { tenantId, setTenantId } = useFilters();
  const navigate = useNavigate();

  useEffect(() => {
    const list = tenants.data ?? [];
    if (list.length && (!tenantId || !list.some((t) => t.tenant_id === tenantId))) setTenantId(list[0]!.tenant_id);
  }, [tenants.data, tenantId, setTenantId]);

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-white md:flex">
        <div className="flex items-center gap-2 px-5 py-5">
          <Gauge className="size-6 text-primary" aria-hidden="true" />
          <div className="leading-tight">
            <p className="font-bold">Mağaza Asistanım</p>
            <p className="text-xs text-muted">Yönetim paneli</p>
          </div>
        </div>
        <nav aria-label="Panolar" className="flex-1 space-y-0.5 px-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn("flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium", isActive ? "bg-primary-soft text-primary" : "text-ink hover:bg-surface")
              }
            >
              <Icon className="size-4" aria-hidden="true" /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3">
          <Button
            variant="ghost"
            className="w-full justify-start"
            onClick={() => {
              setToken(null);
              navigate("/giris");
            }}
          >
            <LogOut aria-hidden="true" /> Çıkış yap
          </Button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-10 flex flex-wrap items-center gap-3 border-b border-line bg-white/95 px-6 py-3 backdrop-blur">
          <label htmlFor="tenant" className="text-sm font-medium">
            Tenant
          </label>
          <Select id="tenant" value={tenantId ?? ""} onChange={(e) => setTenantId(e.target.value)} className="w-52" data-testid="tenant-select">
            {(tenants.data ?? []).map((t) => (
              <option key={t.tenant_id} value={t.tenant_id}>
                {t.display_name}
              </option>
            ))}
          </Select>
          <RangePicker />
          <div className="ml-auto">
            <MonthlyReport />
          </div>
        </header>
        <nav aria-label="Panolar (mobil)" className="flex gap-1 overflow-x-auto border-b border-line bg-white px-3 py-2 md:hidden">
          {NAV.map(({ to, label }) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => cn("shrink-0 rounded-md px-2.5 py-1 text-xs font-medium", isActive ? "bg-primary-soft text-primary" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="p-6">{tenants.isLoading ? <Spinner /> : <Outlet />}</main>
      </div>
    </div>
  );
}
