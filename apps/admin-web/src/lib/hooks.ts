import { useQuery } from "@tanstack/react-query";
import { apiGet, qs } from "./api";
import { useFilters } from "./state";
import type { TenantConfig } from "./types";

export function useTenants() {
  return useQuery({ queryKey: ["tenants"], queryFn: () => apiGet<TenantConfig[]>("/api/tenants") });
}

export function useDashboard<T>(name: string) {
  const { tenantId, range } = useFilters();
  return useQuery({
    queryKey: ["dashboard", name, tenantId, range.start, range.end],
    queryFn: () => apiGet<T>(`/api/tenants/${tenantId}/dashboards/${name}${qs({ start: range.start, end: range.end })}`),
    enabled: Boolean(tenantId),
  });
}
