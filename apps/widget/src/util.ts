/** Small, dependency-free helpers (the bundle must stay well under 60 KB gzip). */

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string | undefined> = {},
  ...children: (Node | string | null | undefined)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined) continue;
    if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) {
    if (child === null || child === undefined) continue;
    node.append(child);
  }
  return node;
}

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]!);
}

/**
 * Renders the assistant's reply: escapes HTML first, then supports **bold**, "- " bullets, numbered lists
 * and line breaks; SKU codes in parentheses become small chips.
 */
export function renderRichText(text: string): string {
  const lines = escapeHtml(text).split("\n");
  const out: string[] = [];
  let list: "ul" | "ol" | null = null;
  const inline = (s: string) =>
    s
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\(([A-Z]{2,4}-[A-Z0-9]{2,5}-\d{3,6})\)/g, '<span class="sku">$1</span>');
  for (const raw of lines) {
    const line = raw.trimEnd();
    const bullet = /^\s*[-•*]\s+(.*)$/.exec(line);
    const numbered = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    const kind = bullet ? "ul" : numbered ? "ol" : null;
    if (kind !== list) {
      if (list) out.push(`</${list}>`);
      if (kind) out.push(`<${kind}>`);
      list = kind;
    }
    if (bullet || numbered) out.push(`<li>${inline((bullet ?? numbered)![1]!)}</li>`);
    else if (line.trim()) out.push(`<p>${inline(line)}</p>`);
  }
  if (list) out.push(`</${list}>`);
  return out.join("");
}

function luminance(hex: string): number {
  const rgb = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = rgb.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

/** Darkens `bg` until text in `fg` reaches WCAG AA (4.5:1). Tenants pick brand colours; the widget keeps them legible. */
export function ensureContrast(bg: string, fg: string, target = 4.5): string {
  let color = bg;
  for (let i = 0; i < 20 && contrastRatio(color, fg) < target; i++) {
    color = `#${[1, 3, 5]
      .map((j) => Math.max(0, Math.round(parseInt(color.slice(j, j + 2), 16) * 0.92)).toString(16).padStart(2, "0"))
      .join("")}`;
  }
  return color;
}

export function randomId(prefix: string): string {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return prefix + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function storage(kind: "local" | "session"): Storage | null {
  try {
    const s = kind === "local" ? window.localStorage : window.sessionStorage;
    s.setItem("__ma", "1");
    s.removeItem("__ma");
    return s;
  } catch {
    return null;
  }
}
