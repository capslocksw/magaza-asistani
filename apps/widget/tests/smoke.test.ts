import { describe, expect, it } from "vitest";
import { WIDGET_VERSION } from "../src/index";

describe("widget", () => {
  it("has a version", () => {
    expect(WIDGET_VERSION).toBe("0.1.0");
  });
});
