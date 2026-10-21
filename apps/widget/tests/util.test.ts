import { describe, expect, it } from "vitest";
import { contrastRatio, ensureContrast, escapeHtml, renderRichText } from "../src/util";

describe("renderRichText", () => {
  it("escapes HTML before formatting", () => {
    expect(renderRichText("<img src=x onerror=alert(1)> **kalın**")).toBe(
      "<p>&lt;img src=x onerror=alert(1)&gt; <strong>kalın</strong></p>",
    );
  });

  it("renders bullets, numbered lists and SKU chips", () => {
    const html = renderRichText("Önerim:\n- Montaj (YM-YAP-0001)\n- Tabanca\n1. Temizle\n2. Uygula");
    expect(html).toContain('<ul><li>Montaj <span class="sku">YM-YAP-0001</span></li><li>Tabanca</li></ul>');
    expect(html).toContain("<ol><li>Temizle</li><li>Uygula</li></ol>");
  });

  it("escapes quotes", () => {
    expect(escapeHtml(`"a" & 'b'`)).toBe("&quot;a&quot; &amp; &#39;b&#39;");
  });
});

describe("ensureContrast", () => {
  it("darkens brand colours until white text reaches WCAG AA", () => {
    expect(contrastRatio("#E8590C", "#FFFFFF")).toBeLessThan(4.5);
    const fixed = ensureContrast("#E8590C", "#FFFFFF");
    expect(contrastRatio(fixed, "#FFFFFF")).toBeGreaterThanOrEqual(4.5);
    expect(ensureContrast("#0F766E", "#FFFFFF")).toBe("#0F766E");
  });
});
