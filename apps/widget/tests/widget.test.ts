import { encodeSseEvent, type AddToCartDetail, type SseEvent, type WidgetPublicConfig } from "@magaza/contracts";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buildScenario } from "../mock-agent/scenarios.mjs";
import { AssistantWidget } from "../src/widget";
import { HAS_DATA, tenants } from "./scenario-fixtures";

const CONFIG: WidgetPublicConfig = {
  display_name: "Yapıcı Market",
  assistant_name: "Usta",
  greeting: "Merhaba!",
  suggested_questions: ["Kornişim koptu, matkabım yok"],
  theme: { primary_color: "#E8590C", accent_color: "#1F2937", text_on_primary: "#FFFFFF", launcher_label: "Ustaya sor" },
  actions: { add_to_cart: true, quote_request: true },
  group: "assistant",
};

type Call = { url: string; body: { event_type?: string; payload?: Record<string, unknown> } | null };

function sseResponse(events: SseEvent[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const e of events) controller.enqueue(encoder.encode(encodeSseEvent(e)));
      controller.close();
    },
  });
  return new Response(body, { headers: { "content-type": "text/event-stream" } });
}

function mount(config: WidgetPublicConfig, chatEvents: SseEvent[]) {
  const calls: Call[] = [];
  vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
    calls.push({ url, body: init?.body ? JSON.parse(String(init.body)) : null });
    if (url.includes("/config")) return new Response(JSON.stringify(config));
    if (url.includes("/chat")) return sseResponse(chatEvents);
    if (url.includes("/quotes")) return new Response(JSON.stringify({ quote_id: "Q-1", status: "received" }));
    return new Response("{}", { status: 202 });
  });
  const host = document.createElement("div");
  document.body.append(host);
  const widget = new AssistantWidget(host, { publicKey: "pk_test_yapimarket", apiUrl: "http://agent.test" });
  return { widget, host, calls };
}

const eventsOf = (calls: Call[], type: string) => calls.filter((c) => c.body?.event_type === type);

describe.skipIf(!HAS_DATA)("AssistantWidget", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  it("streams an answer, renders cards and adds the bundle to the cart", async () => {
    const events = buildScenario(tenants.get("pk_test_yapimarket")!, "Kornişim koptu, matkabım yok");
    const { widget, host, calls } = mount(CONFIG, events);
    await widget.init();
    const root = host.shadowRoot!;
    expect(root.querySelector('[data-testid="ma-launcher"]')).not.toBeNull();
    expect(eventsOf(calls, "visit")).toHaveLength(1);

    widget.open();
    expect(eventsOf(calls, "widget_open")).toHaveLength(1);
    await widget.send("Kornişim koptu, matkabım yok");
    expect(root.querySelector('[data-testid="ma-bot-msg"]')!.textContent).toContain("Önerim");
    expect(root.querySelectorAll('[data-testid="ma-products"] .card').length).toBeGreaterThanOrEqual(3);
    expect(root.querySelector('[data-testid="ma-sources"]')!.textContent).toContain("föye göre");
    expect(root.querySelector(".msg.bot .sku")!.textContent).toMatch(/^YM-/);

    const received: AddToCartDetail[] = [];
    window.addEventListener("ma:add-to-cart", (e) => received.push((e as CustomEvent<AddToCartDetail>).detail));
    (root.querySelector('[data-testid="ma-add-bundle"]') as HTMLButtonElement).click();
    const bundleEvent = events.find((e) => e.type === "bundle");
    expect(received).toHaveLength(1);
    expect(received[0]!.items.length).toBe(bundleEvent?.type === "bundle" ? bundleEvent.bundle.items.length : -1);
    expect(received[0]!.source).toBe("magaza-asistani");
    expect(eventsOf(calls, "add_to_cart")).toHaveLength(1);

    (root.querySelector('[data-testid="ma-feedback-up"]') as HTMLButtonElement).click();
    expect(eventsOf(calls, "feedback")[0]!.body!.payload!.rating).toBe("up");

    widget.trackOrder({ order_id: "ORD-1", items: [{ sku: "YM-YAP-0001", qty: 1, price: 199.9 }], total: 199.9, currency: "TRY" });
    expect(eventsOf(calls, "order")[0]!.body!.payload!.assisted).toBe(true);
  });

  it("stays hidden for holdout (control) visitors but still tracks the visit", async () => {
    const { widget, host, calls } = mount({ ...CONFIG, group: "control" }, []);
    await widget.init();
    expect(host.shadowRoot!.querySelector('[data-testid="ma-launcher"]')).toBeNull();
    expect(eventsOf(calls, "visit")).toHaveLength(1);
    widget.trackOrder({ order_id: "ORD-2", items: [{ sku: "YM-YAP-0001", qty: 1, price: 199.9 }], total: 199.9, currency: "TRY" });
    expect(eventsOf(calls, "order")[0]!.body!.payload!.group).toBe("control");
  });

  it("shows a friendly message on errors", async () => {
    const { widget, host } = mount(CONFIG, [{ type: "error", code: "rate_limited", message: "x" }]);
    await widget.init();
    widget.open();
    await widget.send("merhaba");
    expect(host.shadowRoot!.querySelector(".msg.error")!.textContent).toContain("Çok hızlı");
  });
});
