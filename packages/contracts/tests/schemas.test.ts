import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import { describe, expect, it } from "vitest";
import { buildBundle } from "../scripts/generate.mjs";
import {
  ADD_TO_CART_EVENT,
  ANALYTICS_EVENT_TYPES,
  SSE_EVENT_TYPES,
  SseParser,
  encodeSseEvent,
  formatTRY,
  type AddToCartDetail,
  type Order,
  type Product,
  type SseEvent,
} from "../src/index";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const readJson = (rel: string) => JSON.parse(readFileSync(join(root, rel), "utf8")) as Record<string, unknown[]>;

const bundle = buildBundle();
const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);
ajv.addSchema(bundle);
const validatorFor = (name: string) => ajv.getSchema(`magaza-contracts.bundle.json#/$defs/${name}`)!;

describe("JSON Schema bundle", () => {
  it("is in sync with the committed generated bundle", () => {
    expect(readJson("generated/bundle.schema.json")).toEqual(JSON.parse(JSON.stringify(bundle)));
  });

  it("contains every contract type", () => {
    for (const name of ["TenantConfig", "PersonaTemplate", "Product", "DocChunk", "ChatRequest", "SseEvent", "AnalyticsEvent"]) {
      expect(bundle.$defs).toHaveProperty(name);
    }
  });

  const valid = readJson("examples/valid.json");
  for (const [name, samples] of Object.entries(valid)) {
    it(`accepts valid ${name} examples`, () => {
      const validate = validatorFor(name);
      for (const sample of samples) {
        expect(validate(sample), JSON.stringify(validate.errors)).toBe(true);
      }
    });
  }

  const invalid = readJson("examples/invalid.json");
  for (const [name, samples] of Object.entries(invalid)) {
    it(`rejects invalid ${name} examples`, () => {
      const validate = validatorFor(name);
      for (const sample of samples) {
        expect(validate(sample)).toBe(false);
      }
    });
  }
});

describe("generated TypeScript types", () => {
  it("type-check representative values", () => {
    const product: Product = {
      sku: "KC-KOL-0034",
      title: "Çift Oluklu Koli 30x30x30",
      brand: "Kolipak",
      category: "koli",
      category_name: "Koliler",
      description: "BC dalga",
      price: 24.9,
      currency: "TRY",
      stock: 1200,
      unit: "adet",
      image_url: "/images/KC-KOL-0034.svg",
      url: "/urun/KC-KOL-0034/",
      specs: [{ key: "dalga", label: "Dalga tipi", value: "BC" }],
      tags: [],
      complement_skus: [],
    };
    const detail: AddToCartDetail = { source: "magaza-asistani", items: [{ sku: product.sku, title: product.title, price: 24.9, qty: 2 }] };
    const order: Order = { order_id: "ORD-1", items: [{ sku: product.sku, qty: 2, price: 24.9 }], total: 49.8, currency: "TRY" };
    expect(detail.items[0]?.qty).toBe(2);
    expect(order.total).toBeCloseTo(49.8);
    expect(ADD_TO_CART_EVENT).toBe("ma:add-to-cart");
    expect(SSE_EVENT_TYPES).toHaveLength(7);
    expect(ANALYTICS_EVENT_TYPES).toContain("quote_request");
  });
});

describe("formatTRY", () => {
  it.each([
    [1234.9, "₺1.234,90"],
    [0, "₺0,00"],
    [19.99, "₺19,99"],
    [1234567.891, "₺1.234.567,89"],
    [-5, "-₺5,00"],
  ])("formats %s as %s", (value, expected) => {
    expect(formatTRY(value)).toBe(expected);
  });
});

describe("SSE helpers", () => {
  it("round-trips events through chunked parsing", () => {
    const events: SseEvent[] = [
      { type: "token", text: "Merhaba " },
      { type: "token", text: "dünya" },
      { type: "done", session_id: "s_1", message_id: "m_1" },
    ];
    const wire = events.map(encodeSseEvent).join("");
    const parser = new SseParser();
    const parsed: SseEvent[] = [];
    for (let i = 0; i < wire.length; i += 7) parsed.push(...parser.push(wire.slice(i, i + 7)));
    expect(parsed).toEqual(events);
  });
});
