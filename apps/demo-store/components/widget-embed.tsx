"use client";

import { useEffect } from "react";
import { AGENT_URL, WIDGET_URL, brandConfig } from "@/lib/brand";

declare global {
  interface Window {
    MagazaAsistani?: {
      open: (prompt?: string) => void;
      close: () => void;
      trackOrder: (order: unknown) => void;
    };
  }
}

const OVERRIDE_KEY = "ma-demo-agent-url";

/**
 * Embeds the assistant exactly like a customer site would: one <script> tag with data-tenant.
 * `?ma_api=<url>` (remembered for the tab) points the widget at another agent, e.g. the real agent-api.
 */
export function WidgetEmbed() {
  useEffect(() => {
    if (document.getElementById("magaza-asistani-script")) return;
    let api = AGENT_URL;
    try {
      const fromQuery = new URLSearchParams(window.location.search).get("ma_api");
      if (fromQuery) window.sessionStorage.setItem(OVERRIDE_KEY, fromQuery);
      api = window.sessionStorage.getItem(OVERRIDE_KEY) ?? AGENT_URL;
    } catch {
      // sessionStorage unavailable; keep the default agent.
    }
    const script = document.createElement("script");
    script.id = "magaza-asistani-script";
    script.src = WIDGET_URL;
    script.async = true;
    script.dataset.tenant = brandConfig.publicKey;
    script.dataset.api = api;
    document.body.appendChild(script);
  }, []);
  return null;
}

export function openAssistant(prompt?: string): void {
  window.MagazaAsistani?.open(prompt);
}
