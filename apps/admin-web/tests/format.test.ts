import { describe, expect, it } from "vitest";
import { qs } from "../src/lib/api";
import { delta, formatTRY, int, pct, shortDate, usd } from "../src/lib/format";

describe("admin formatters", () => {
  it("formats numbers the Turkish way", () => {
    expect(formatTRY(358109.5)).toBe("₺358.109,50");
    expect(pct(0.0849)).toBe("%8,5");
    expect(pct(null)).toBe("—");
    expect(delta(79.5)).toBe("+%79,5");
    expect(delta(-3)).toBe("−%3,0");
    expect(int(18609)).toBe("18.609");
    expect(usd(14.8879)).toBe("$14.89");
    expect(shortDate("2026-10-19")).toBe("19.10");
  });

  it("builds query strings without empty values", () => {
    expect(qs({ start: "2026-10-01", q: "", limit: 5 })).toBe("?start=2026-10-01&limit=5");
    expect(qs({})).toBe("");
  });
});
