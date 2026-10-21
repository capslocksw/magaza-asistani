// Entry point of widget.js. Embed with:
//   <script src="https://.../widget.js" data-tenant="pk_..." data-api="https://agent..." async></script>
import type { Order } from "@magaza/contracts";
import { AssistantWidget } from "./widget";

export const WIDGET_VERSION = "0.1.0";
const DEFAULT_API = import.meta.env.VITE_AGENT_URL || "http://localhost:8787";

interface PublicApi {
  version: string;
  open: (prompt?: string) => void;
  close: () => void;
  trackOrder: (order: Order) => void;
}

declare global {
  interface Window {
    MagazaAsistani?: PublicApi;
  }
}

class MagazaAsistaniElement extends HTMLElement {
  widget: AssistantWidget | null = null;

  connectedCallback(): void {
    if (this.widget) return;
    const publicKey = this.getAttribute("tenant");
    if (!publicKey) return;
    this.widget = new AssistantWidget(this, { publicKey, apiUrl: this.getAttribute("api") || DEFAULT_API });
    void this.widget.init().then(() => window.dispatchEvent(new CustomEvent("ma:ready")));
  }
}

function boot(): void {
  if (!customElements.get("magaza-asistani")) customElements.define("magaza-asistani", MagazaAsistaniElement);
  const script =
    (document.currentScript as HTMLScriptElement | null) ?? document.querySelector<HTMLScriptElement>("script[data-tenant]");
  const tenant = script?.dataset.tenant;
  if (!tenant || document.querySelector("magaza-asistani")) return;
  const host = document.createElement("magaza-asistani") as MagazaAsistaniElement;
  host.setAttribute("tenant", tenant);
  if (script?.dataset.api) host.setAttribute("api", script.dataset.api);
  const pendingOrders: Order[] = [];
  const trackedOrders = new Set<string>(); // a confirmation page may call trackOrder more than once
  window.MagazaAsistani = {
    version: WIDGET_VERSION,
    open: (prompt) => host.widget?.open(prompt),
    close: () => host.widget?.close(),
    trackOrder: (order) => {
      if (trackedOrders.has(order.order_id)) return;
      trackedOrders.add(order.order_id);
      if (host.widget?.config) host.widget.trackOrder(order);
      else pendingOrders.push(order);
    },
  };
  window.addEventListener("ma:ready", () => pendingOrders.splice(0).forEach((o) => host.widget?.trackOrder(o)), { once: true });
  document.body.appendChild(host);
}

if (typeof document !== "undefined" && typeof customElements !== "undefined") {
  if (document.body) boot();
  else document.addEventListener("DOMContentLoaded", boot, { once: true });
}
