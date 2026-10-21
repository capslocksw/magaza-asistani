import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { isoDate } from "./format";

export interface Range {
  start: string;
  end: string;
  preset: 7 | 30 | 90 | "custom";
}

interface Filters {
  tenantId: string | null;
  setTenantId: (id: string) => void;
  range: Range;
  setRange: (r: Range) => void;
}

const FiltersContext = createContext<Filters | null>(null);

export function presetRange(days: 7 | 30 | 90): Range {
  const end = new Date();
  const start = new Date(end.getTime() - (days - 1) * 86_400_000);
  return { start: isoDate(start), end: isoDate(end), preset: days };
}

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [tenantId, setTenantIdState] = useState<string | null>(() => {
    try {
      return window.localStorage.getItem("ma-admin-tenant");
    } catch {
      return null;
    }
  });
  const [range, setRange] = useState<Range>(() => presetRange(30));

  useEffect(() => {
    try {
      if (tenantId) window.localStorage.setItem("ma-admin-tenant", tenantId);
    } catch {
      // ignore
    }
  }, [tenantId]);

  const value = useMemo(() => ({ tenantId, setTenantId: setTenantIdState, range, setRange }), [tenantId, range]);
  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>;
}

export function useFilters(): Filters {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error("FiltersProvider missing");
  return ctx;
}
