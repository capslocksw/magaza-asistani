export * from "./generated/contracts";
export * from "./format";
export * from "./sse";

import type { AnalyticsEvent, BrowserEventName, SseEvent } from "./generated/contracts";

export const CONTRACTS_VERSION = "0.1.0";

/** CustomEvent name the widget dispatches on `window` when the user adds items to the cart. */
export const ADD_TO_CART_EVENT = "ma:add-to-cart" satisfies BrowserEventName;

export const SSE_EVENT_TYPES = [
  "token",
  "products",
  "bundle",
  "action",
  "source",
  "done",
  "error",
] as const satisfies readonly SseEvent["type"][];

export const ANALYTICS_EVENT_TYPES = [
  "visit",
  "widget_open",
  "user_message",
  "agent_message",
  "tool_call",
  "product_shown",
  "add_to_cart",
  "quote_request",
  "order",
  "feedback",
] as const satisfies readonly AnalyticsEvent["event_type"][];
