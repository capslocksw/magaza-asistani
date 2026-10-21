import {
  ADD_TO_CART_EVENT,
  formatTRY,
  type AddToCartDetail,
  type Bundle,
  type CartLine,
  type ClientEvent,
  type Order,
  type ProductCard,
  type SourceRef,
  type SseEvent,
  type WidgetPublicConfig,
} from "@magaza/contracts";
import { AgentClient } from "./api";
import { STYLES } from "./styles";
import { el, ensureContrast, randomId, renderRichText, storage } from "./util";

const ICON_CHAT =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/><path d="M8.5 11h.01M12 11h.01M15.5 11h.01"/></svg>';
const ICON_SEND =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>';

const ERROR_TEXT: Record<string, string> = {
  rate_limited: "Çok hızlı mesaj gönderiyorsunuz; lütfen birkaç saniye sonra tekrar deneyin.",
  quota_exceeded: "Asistan şu anda yoğun; lütfen daha sonra tekrar deneyin.",
  origin_not_allowed: "Bu sitede asistan etkin değil.",
  unknown_tenant: "Bu sitede asistan etkin değil.",
  invalid_request: "Mesajınız işlenemedi.",
  internal: "Bir sorun oluştu; lütfen tekrar deneyin.",
};

export interface WidgetOptions {
  publicKey: string;
  apiUrl: string;
}

interface Turn {
  bubble: HTMLDivElement;
  extras: HTMLDivElement;
  text: string;
}

/** The assistant UI. Lives inside the shadow root of <magaza-asistani> so storefront CSS cannot leak in. */
export class AssistantWidget {
  readonly client: AgentClient;
  config: WidgetPublicConfig | null = null;
  private readonly root: ShadowRoot;
  private readonly host: HTMLElement;
  private readonly local = storage("local");
  private readonly session = storage("session");
  private readonly visitorId: string;
  private sessionId: string | null;
  private launcher!: HTMLButtonElement;
  private panel!: HTMLDivElement;
  private messages!: HTMLDivElement;
  private input!: HTMLTextAreaElement;
  private busy = false;
  private openedOnce = false;
  private lastBundle: Bundle | null = null;
  private pendingPrompt: string | null = null;

  constructor(
    host: HTMLElement,
    private readonly options: WidgetOptions,
  ) {
    this.host = host;
    this.root = host.attachShadow({ mode: "open" });
    this.client = new AgentClient(options.apiUrl, options.publicKey);
    this.visitorId = this.local?.getItem("ma_vid") ?? randomId("v_");
    this.local?.setItem("ma_vid", this.visitorId);
    this.sessionId = this.session?.getItem(this.key("sid")) ?? null;
  }

  private key(name: string): string {
    return `ma_${name}:${this.options.publicKey}`;
  }

  get group(): "assistant" | "control" {
    return this.config?.group ?? "assistant";
  }

  async init(): Promise<void> {
    try {
      this.config = await this.client.getConfig(this.visitorId);
    } catch {
      return; // Agent unreachable: stay invisible; the storefront keeps working.
    }
    if (!this.session?.getItem(this.key("visit"))) {
      this.session?.setItem(this.key("visit"), "1");
      this.track({ event_type: "visit", payload: { group: this.group, page_url: location.href } });
    }
    if (this.group === "control") return; // Holdout visitors never see the assistant.
    this.render();
    if (this.pendingPrompt !== null) this.open(this.pendingPrompt);
  }

  private track(event: Omit<ClientEvent, "visitor_id">): void {
    this.client.sendEvent({ visitor_id: this.visitorId, session_id: this.sessionId, ...event });
  }

  private markAssisted(): void {
    this.session?.setItem(this.key("assisted"), "1");
  }

  // ------------------------------------------------------------------ rendering
  private render(): void {
    const config = this.config!;
    const onPrimary = config.theme.text_on_primary;
    const primary = ensureContrast(config.theme.primary_color, onPrimary);
    this.host.style.setProperty("--ma-primary", primary);
    this.host.style.setProperty("--ma-on-primary", onPrimary);
    this.host.style.setProperty("--ma-accent", ensureContrast(config.theme.accent_color, "#ffffff"));
    this.host.dataset.position = config.theme.position ?? "right";

    const style = el("style");
    style.textContent = STYLES;

    this.launcher = el("button", { class: "launcher", type: "button", "aria-label": `${config.theme.launcher_label} — ${config.assistant_name}`, "data-testid": "ma-launcher" });
    this.launcher.innerHTML = `${ICON_CHAT}<span>${config.theme.launcher_label}</span>`;
    this.launcher.addEventListener("click", () => this.open());

    const close = el("button", { class: "icon", type: "button", "aria-label": "Asistanı kapat", "data-testid": "ma-close" }, "✕");
    close.addEventListener("click", () => this.close());
    const quoteButton = config.actions.quote_request
      ? el("button", { type: "button", "data-testid": "ma-quote-open" }, "Teklif iste")
      : null;
    quoteButton?.addEventListener("click", () => this.showQuoteForm());
    const logo = config.theme.logo_url ? el("img", { src: config.theme.logo_url, alt: "" }) : null;
    const header = el(
      "header",
      {},
      logo,
      el("div", { class: "titles" }, el("div", { class: "name" }, config.assistant_name), el("div", { class: "sub" }, `${config.display_name} asistanı`)),
      quoteButton,
      close,
    );

    this.messages = el("div", { class: "messages", role: "log", "aria-live": "polite", "aria-label": "Sohbet", "data-testid": "ma-messages" });
    this.input = el("textarea", { rows: "1", placeholder: "Sorununuzu yazın…", "aria-label": "Mesajınız", "data-testid": "ma-input" });
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
      }
    });
    const send = el("button", { type: "submit", "aria-label": "Gönder", "data-testid": "ma-send" });
    send.innerHTML = ICON_SEND;
    const form = el("form", { class: "composer" }, el("label", { class: "sr" }, "Mesajınız"), this.input, send);
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      void this.send(this.input.value);
    });

    this.panel = el(
      "div",
      { class: "panel", role: "dialog", "aria-label": `${config.assistant_name} sohbet penceresi`, "data-testid": "ma-panel" },
      header,
      this.messages,
      form,
      el("p", { class: "disclaimer" }, "Yapay zeka asistanıdır; ürün bilgilerini sipariş öncesi kontrol edin."),
    );
    this.panel.hidden = true;
    this.root.append(style, this.launcher, this.panel);
    this.renderWelcome();
  }

  private renderWelcome(): void {
    const config = this.config!;
    const bubble = el("div", { class: "msg bot" });
    bubble.innerHTML = renderRichText(config.greeting);
    const chips = el("div", { class: "chips", "data-testid": "ma-suggestions" });
    for (const q of config.suggested_questions) {
      const chip = el("button", { class: "chip", type: "button" }, q);
      chip.addEventListener("click", () => void this.send(q));
      chips.append(chip);
    }
    this.messages.append(bubble, chips);
  }

  open(prompt?: string): void {
    if (!this.panel) {
      this.pendingPrompt = prompt ?? "";
      return;
    }
    this.panel.hidden = false;
    this.launcher.hidden = true;
    if (!this.openedOnce) {
      this.openedOnce = true;
      this.track({ event_type: "widget_open", payload: { page_url: location.href } });
    }
    window.dispatchEvent(new CustomEvent("ma:open"));
    if (prompt) void this.send(prompt);
    else this.input.focus();
  }

  close(): void {
    if (!this.panel) return;
    this.panel.hidden = true;
    this.launcher.hidden = false;
    window.dispatchEvent(new CustomEvent("ma:close"));
    this.launcher.focus();
  }

  private scroll(): void {
    this.messages.scrollTop = this.messages.scrollHeight;
  }

  // ------------------------------------------------------------------ chat
  async send(raw: string): Promise<void> {
    const text = raw.trim();
    if (!text || this.busy) return;
    this.busy = true;
    this.input.value = "";
    this.markAssisted();
    this.messages.querySelector('[data-testid="ma-suggestions"]')?.remove();
    this.messages.append(el("div", { class: "msg user", "data-testid": "ma-user-msg" }, text));
    const bubble = el("div", { class: "msg bot", "data-testid": "ma-bot-msg" });
    bubble.innerHTML = '<span class="typing" aria-label="Yazıyor"><i></i><i></i><i></i></span>';
    const extras = el("div", { class: "extras" });
    extras.style.cssText = "display:flex;flex-direction:column;gap:10px";
    this.messages.append(bubble, extras);
    this.scroll();
    const turn: Turn = { bubble, extras, text: "" };
    try {
      await this.client.chat(
        { message: text, session_id: this.sessionId, visitor_id: this.visitorId, page_url: location.href, cart_skus: [] },
        (event) => this.onEvent(turn, event),
      );
    } catch {
      this.onEvent(turn, { type: "error", code: "internal", message: "network" });
    } finally {
      if (!turn.text && !turn.bubble.classList.contains("error")) turn.bubble.remove();
      this.busy = false;
      this.scroll();
    }
  }

  private onEvent(turn: Turn, event: SseEvent): void {
    switch (event.type) {
      case "token":
        turn.text += event.text;
        turn.bubble.innerHTML = renderRichText(turn.text);
        break;
      case "products":
        if (event.products.length) turn.extras.append(this.productCards(event.products));
        break;
      case "bundle":
        this.lastBundle = event.bundle;
        turn.extras.append(this.bundleCard(event.bundle));
        break;
      case "source":
        if (event.sources.length) turn.extras.prepend(this.sourceChips(event.sources));
        break;
      case "action":
        if (event.action === "suggest_quote" && this.config?.actions.quote_request) {
          const button = el("button", { class: "btn secondary", type: "button", "data-testid": "ma-quote-suggest" }, event.label ?? "Teklif talebi oluştur");
          button.addEventListener("click", () => this.showQuoteForm());
          turn.extras.append(button);
        } else if (event.action === "quote_created") {
          const payload = (event.payload ?? {}) as Record<string, unknown>;
          const id = typeof payload.quote_id === "string" ? payload.quote_id : "";
          turn.extras.append(el("div", { class: "msg system" }, `Teklif talebiniz alındı${id ? ` (no: ${id})` : ""}.`));
        }
        break;
      case "done":
        this.sessionId = event.session_id;
        this.session?.setItem(this.key("sid"), event.session_id);
        turn.extras.append(this.feedback(event.message_id));
        break;
      case "error":
        turn.bubble.className = "msg error";
        if (event.code === "quota_exceeded") {
          // The session hit its message limit: forget it so the next message starts a new conversation.
          this.sessionId = null;
          this.session?.removeItem(this.key("sid"));
        }
        turn.bubble.textContent =
          event.code === "quota_exceeded" && event.message ? event.message : (ERROR_TEXT[event.code] ?? ERROR_TEXT.internal!);
        break;
    }
    this.scroll();
  }

  // ------------------------------------------------------------------ cart
  private addToCart(items: CartLine[], button: HTMLButtonElement, bundleId: string | null): void {
    if (!items.length) return;
    const detail: AddToCartDetail = { source: "magaza-asistani", session_id: this.sessionId, bundle_id: bundleId, items: items as AddToCartDetail["items"] };
    window.dispatchEvent(new CustomEvent<AddToCartDetail>(ADD_TO_CART_EVENT, { detail }));
    this.markAssisted();
    this.track({
      event_type: "add_to_cart",
      payload: {
        bundle_id: bundleId,
        skus: items.map((i) => i.sku),
        items: items.map((i) => ({ sku: i.sku, qty: i.qty, price: i.price })),
        value: Math.round(items.reduce((s, i) => s + i.price * i.qty, 0) * 100) / 100,
      },
    });
    button.classList.add("done");
    button.textContent = "Sepete eklendi ✓";
  }

  private productCards(products: ProductCard[]): HTMLElement {
    const wrap = el("div", { class: "cards", "data-testid": "ma-products" });
    for (const p of products) {
      const price = el("div", { class: "price" });
      price.innerHTML = `${p.list_price && p.list_price > p.price ? `<span class="old">${formatTRY(p.list_price)}</span>` : ""}${formatTRY(p.price)}`;
      const canAdd = this.config?.actions.add_to_cart !== false;
      const button = canAdd
        ? el("button", { class: "btn", type: "button", "data-testid": "ma-add-product", "aria-label": `${p.title} sepete ekle` }, p.in_stock ? "Sepete ekle" : "Stokta yok")
        : null;
      if (button) {
        button.disabled = !p.in_stock;
        button.addEventListener("click", () =>
          this.addToCart([{ sku: p.sku, title: p.title, price: p.price, qty: 1, image_url: p.image_url, url: p.url }], button, null),
        );
      }
      wrap.append(
        el(
          "div",
          { class: "card", "data-sku": p.sku },
          el("img", { src: p.image_url, alt: "", loading: "lazy" }),
          el(
            "div",
            { class: "body" },
            el("a", { class: "t", href: p.url, target: "_top" }, p.title),
            p.reason ? el("div", { class: "reason" }, p.reason) : null,
            price,
            button,
          ),
        ),
      );
    }
    return wrap;
  }

  private bundleCard(bundle: Bundle): HTMLElement {
    const list = el("ul");
    for (const item of bundle.items) {
      list.append(
        el(
          "li",
          {},
          el("img", { src: item.image_url, alt: "" }),
          el("span", { class: "n" }, el("span", { class: "role" }, item.role === "main" ? "Ana ürün" : "Tamamlayıcı"), el("br"), `${item.qty} × ${item.title}`),
          el("strong", {}, formatTRY(item.price * item.qty)),
        ),
      );
    }
    const canAdd = this.config?.actions.add_to_cart !== false;
    const button = canAdd ? el("button", { class: "btn", type: "button", "data-testid": "ma-add-bundle" }, "Paketi sepete ekle") : null;
    button?.addEventListener("click", () =>
      this.addToCart(
        bundle.items.map((i) => ({ sku: i.sku, title: i.title, price: i.price, qty: i.qty, image_url: i.image_url, url: i.url })),
        button!,
        bundle.bundle_id,
      ),
    );
    return el(
      "div",
      { class: "bundle", "data-testid": "ma-bundle" },
      el("h4", {}, bundle.title),
      el("p", { class: "why" }, bundle.rationale),
      list,
      el("div", { class: "total" }, el("span", {}, "Paket toplamı ", el("strong", {}, formatTRY(bundle.total))), button),
    );
  }

  private sourceChips(sources: SourceRef[]): HTMLElement {
    const wrap = el("div", { class: "sources", "data-testid": "ma-sources" });
    for (const s of sources) {
      wrap.append(el("a", { class: "source", href: s.url, target: "_blank", rel: "noopener", title: s.title }, `📄 föye göre: ${s.title.replace(/ — Teknik Föy$/, "")}`));
    }
    return wrap;
  }

  private feedback(messageId: string): HTMLElement {
    const wrap = el("div", { class: "feedback", role: "group", "aria-label": "Yanıtı değerlendir" });
    for (const [rating, label, icon] of [
      ["up", "Yararlı", "👍"],
      ["down", "Yararlı değil", "👎"],
    ] as const) {
      const b = el("button", { type: "button", "aria-label": label, "aria-pressed": "false", "data-testid": `ma-feedback-${rating}` }, icon);
      b.addEventListener("click", () => {
        wrap.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", "false"));
        b.setAttribute("aria-pressed", "true");
        this.track({ event_type: "feedback", payload: { message_id: messageId, rating } });
      });
      wrap.append(b);
    }
    return wrap;
  }

  // ------------------------------------------------------------------ quote (only when the tenant enables it)
  private showQuoteForm(): void {
    if (!this.config?.actions.quote_request) return;
    this.messages.querySelector(".quote")?.remove();
    const bundle = this.lastBundle;
    const field = (label: string, name: string, type = "text", required = true) =>
      el("label", {}, label, el("input", { name, type, required: required ? "" : undefined, autocomplete: "on" }));
    const form = el("form", { class: "quote", "data-testid": "ma-quote-form" }, el("h4", {}, "Teklif talebi"));
    if (bundle) {
      const items = el("ul", { class: "items" });
      for (const i of bundle.items) items.append(el("li", {}, `${i.qty} × ${i.title}`));
      form.append(items);
    } else {
      form.append(el("p", { class: "why" }, "Teklif için önce asistandan bir ürün paketi isteyin."));
    }
    form.append(
      field("Firma adı", "company_name"),
      el("div", { class: "row" }, field("Ad soyad", "contact_name"), field("Telefon", "phone", "tel", false)),
      field("E-posta", "email", "email"),
      el("label", {}, "Adet / not", el("textarea", { name: "note", rows: "2" })),
    );
    const submit = el("button", { class: "btn", type: "submit", "data-testid": "ma-quote-submit" }, "Teklif iste");
    submit.disabled = !bundle;
    const cancel = el("button", { class: "btn secondary", type: "button" }, "Vazgeç");
    cancel.addEventListener("click", () => form.remove());
    form.append(el("div", { class: "actions" }, cancel, submit));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!bundle) return;
      const data = new FormData(form);
      submit.disabled = true;
      try {
        const res = await this.client.createQuote({
          visitor_id: this.visitorId,
          session_id: this.sessionId,
          company_name: String(data.get("company_name") ?? ""),
          contact_name: String(data.get("contact_name") ?? ""),
          email: String(data.get("email") ?? ""),
          phone: String(data.get("phone") ?? "") || null,
          note: String(data.get("note") ?? "") || null,
          items: bundle.items.map((i) => ({ sku: i.sku, qty: i.qty })) as [{ sku: string; qty: number }],
        });
        form.replaceWith(el("div", { class: "msg system", "data-testid": "ma-quote-done" }, `Teklif talebiniz alındı (no: ${res.quote_id}). Satış ekibimiz e-postayla dönüş yapacak.`));
      } catch {
        submit.disabled = false;
        form.append(el("div", { class: "msg error" }, "Teklif gönderilemedi; lütfen tekrar deneyin."));
      }
      this.scroll();
    });
    this.messages.append(form);
    this.scroll();
    form.querySelector("input")?.focus();
  }

  // ------------------------------------------------------------------ conversion tracking
  trackOrder(order: Order): void {
    this.track({
      event_type: "order",
      payload: {
        order_id: order.order_id,
        total: order.total,
        currency: order.currency,
        items: order.items.map((i) => ({ sku: i.sku, qty: i.qty, price: i.price })),
        assisted: this.session?.getItem(this.key("assisted")) === "1",
        group: this.group,
      },
    });
  }
}
