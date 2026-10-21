import type { Product, SseEvent, TenantConfig, WidgetPublicConfig } from "@magaza/contracts";

export interface MockTenant {
  config: TenantConfig;
  catalog: Product[];
  bySku: Map<string, Product>;
}

export declare function fold(text: string): string;
export declare function loadTenants(dataDir: string): Map<string, MockTenant>;
export declare function assignGroup(tenantId: string, visitorId: string, holdoutPct: number): "assistant" | "control";
export declare function widgetConfig(tenant: MockTenant, visitorId: string): WidgetPublicConfig;
export declare function buildScenario(tenant: MockTenant, message: string, sessionId?: string | null): SseEvent[];
