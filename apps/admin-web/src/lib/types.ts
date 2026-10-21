import type { TenantConfig } from "@magaza/contracts";

export type { TenantConfig };

export interface ExecutiveData {
  kpis: {
    assisted_revenue: number;
    revenue: number;
    assisted_revenue_share: number | null;
    conversion_assisted: number | null;
    conversion_unassisted: number | null;
    aov_assisted: number | null;
    aov_unassisted: number | null;
    aov_diff_pct: number | null;
    cross_sell_acceptance: number | null;
    conversations: number;
    orders: number;
    holdout_conversion_assistant_group: number | null;
    holdout_conversion_control_group: number | null;
    holdout_uplift_pct: number | null;
  };
  weekly: { week: string; assisted_revenue: number; revenue: number; conversations: number }[];
}

export interface FunnelData {
  stages: { stage: string; label: string; count: number; step_rate: number | null; overall_rate: number | null }[];
}

export interface DemandData {
  topics: { topic: string; label: string; count: number; share: number; previous: number; growth_pct: number | null }[];
  rising: DemandData["topics"];
  samples: { session_id: string; ts: string; text: string; topic: string | null; topic_label: string }[];
}

export interface UnmetData {
  kpis: { unmet_answers: number; unmet_rate: number | null; zero_result_searches: number; out_of_stock_requests: number };
  not_in_catalog: { query: string; count: number }[];
  out_of_stock: { sku: string; title: string; count: number }[];
  zero_result: { query: string; count: number }[];
}

export interface ProductsData {
  top: { sku: string; title: string; shown: number; added: number; ordered: number; shown_to_cart: number | null; cart_to_order: number | null }[];
  pairs: { sku_a: string; sku_b: string; title_a: string; title_b: string; count: number }[];
}

export interface QualityData {
  kpis: {
    like_rate: number | null;
    feedback_count: number;
    dont_know_rate: number | null;
    abandonment_rate: number | null;
    guardrail_triggers: number;
    latency_avg_ms: number | null;
    latency_p95_ms: number | null;
  };
  guardrails: { guardrail: string; label: string; count: number }[];
  weekly: { week: string; like_rate: number | null; dont_know_rate: number | null }[];
}

export interface UsageRow {
  tenant_id: string;
  month: string;
  conversations: number;
  messages: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
}

export interface UsageData {
  rows: UsageRow[];
  totals: { conversations: number; messages: number; tokens_in: number; tokens_out: number; cost_usd: number };
}

export interface ConversationItem {
  session_id: string;
  started: string;
  turns: number;
  adds: number;
  likes: number;
  dislikes: number;
  guardrails: number;
  first_message: string;
  topic: string | null;
  topic_label: string;
}

export interface ConversationEvent {
  event_type: string;
  ts: string;
  model: string | null;
  latency_ms: number | null;
  payload: Record<string, unknown>;
}

export interface PersonaTemplate {
  template_id: string;
  name: string;
  description: string;
  instruction: string;
  version: number;
}
