import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import { describe, expect, it } from "vitest";
import { assignGroup, buildScenario, widgetConfig } from "../mock-agent/scenarios.mjs";
import { HAS_DATA, tenants } from "./scenario-fixtures";

const bundle = JSON.parse(
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), "../../../packages/contracts/generated/bundle.schema.json"), "utf8"),
);
const ajv = new Ajv2020({ strict: false, allErrors: true });
addFormats(ajv);
ajv.addSchema(bundle);
const validateEvent = ajv.getSchema("magaza-contracts.bundle.json#/$defs/SseEvent")!;
const validateConfig = ajv.getSchema("magaza-contracts.bundle.json#/$defs/WidgetPublicConfig")!;

describe.skipIf(!HAS_DATA)("mock-agent scenarios", () => {
  const cases: [string, string, boolean][] = [
    ["pk_test_yapimarket", "Kornişim koptu, matkabım yok", true],
    ["pk_test_yapimarket", "Salonu boyayacağım", true],
    ["pk_test_yapimarket", "merhaba", false],
    ["pk_test_ambalaj", "2 kg seramik kupa göndereceğim, hangi koli?", true],
    ["pk_test_ambalaj", "Ayda 1000 koli gönderiyorum, teklif alabilir miyim?", true],
  ];
  for (const [key, message, expectsBundle] of cases) {
    it(`emits contract-valid events for "${message}"`, () => {
      const events = buildScenario(tenants.get(key)!, message);
      for (const event of events) expect(validateEvent(event), JSON.stringify(validateEvent.errors)).toBe(true);
      expect(events.at(-1)!.type).toBe("done");
      expect(events.some((e) => e.type === "bundle")).toBe(expectsBundle);
    });
  }

  it("follows the kickoff examples", () => {
    const titles = (key: string, message: string) => {
      const event = buildScenario(tenants.get(key)!, message).find((e) => e.type === "bundle");
      return event?.type === "bundle" ? event.bundle.items.map((i) => i.title).join(" | ") : "";
    };
    expect(titles("pk_test_yapimarket", "Kornişim koptu, matkabım yok")).toMatch(/Montaj Yapıştırıcısı.*Silikon Tabancası.*Yüzey Temizleyici/);
    expect(titles("pk_test_ambalaj", "2 kg seramik kupa göndereceğim, hangi koli?")).toMatch(/Çift Oluklu Koli.*Balonlu Naylon.*Koli Bandı/);
  });

  it("serves a contract-valid widget config with deterministic holdout", () => {
    const tenant = tenants.get("pk_test_ambalaj")!;
    expect(validateConfig(widgetConfig(tenant, "v_e2e_visitor_0001"))).toBe(true);
    expect(assignGroup("ambalaj", "v_x", 0)).toBe("assistant");
    expect(assignGroup("ambalaj", "v_x", 100)).toBe("control");
    expect(assignGroup("ambalaj", "v_x", 50)).toBe(assignGroup("ambalaj", "v_x", 50));
  });
});
