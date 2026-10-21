import {
  SseParser,
  type ChatRequest,
  type ClientEvent,
  type QuoteRequest,
  type QuoteResponse,
  type SseEvent,
  type WidgetPublicConfig,
} from "@magaza/contracts";

/** Thin client for the agent API (`/v1/t/{publicKey}/...`). The tenant is identified only by its public key. */
export class AgentClient {
  private readonly base: string;

  constructor(apiUrl: string, publicKey: string) {
    this.base = `${apiUrl.replace(/\/$/, "")}/v1/t/${encodeURIComponent(publicKey)}`;
  }

  async getConfig(visitorId: string): Promise<WidgetPublicConfig> {
    const res = await fetch(`${this.base}/config?visitor_id=${encodeURIComponent(visitorId)}`);
    if (!res.ok) throw new Error(`config ${res.status}`);
    return (await res.json()) as WidgetPublicConfig;
  }

  async chat(request: ChatRequest, onEvent: (event: SseEvent) => void, signal?: AbortSignal): Promise<void> {
    const res = await fetch(`${this.base}/chat`, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "text/event-stream" },
      body: JSON.stringify(request),
      signal,
    });
    if (!res.ok || !res.body) {
      onEvent({ type: "error", code: res.status === 429 ? "rate_limited" : "internal", message: `HTTP ${res.status}` });
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    const parser = new SseParser();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const event of parser.push(decoder.decode(value, { stream: true }))) onEvent(event);
    }
  }

  sendEvent(event: ClientEvent): void {
    const body = JSON.stringify(event);
    // keepalive lets order/add-to-cart events survive an immediate page navigation.
    void fetch(`${this.base}/events`, { method: "POST", headers: { "content-type": "application/json" }, body, keepalive: true }).catch(
      () => undefined,
    );
  }

  async createQuote(request: QuoteRequest): Promise<QuoteResponse> {
    const res = await fetch(`${this.base}/quotes`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) throw new Error(`quote ${res.status}`);
    return (await res.json()) as QuoteResponse;
  }
}
