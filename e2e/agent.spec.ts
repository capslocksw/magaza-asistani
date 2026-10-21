import { expect, test } from "@playwright/test";
import { STORES, shot } from "./helpers";

// Widget wired to the real services/agent-api (ADK agent, Firestore emulator, FakeLlm unless LLM_MODE=vertex).
const AGENT_API = "http://localhost:8080";
const PROMPTS = {
  "yapi-market": { text: "Kornişim koptu, matkabım yok", expect: /Montaj Yapıştırıcısı/ },
  ambalaj: { text: "2 kg seramik kupa göndereceğim, hangi koli?", expect: /Çift Oluklu Koli/ },
} as const;

for (const store of STORES) {
  test(`${store.id}: widget → real agent-api → grounded bundle → storefront cart`, async ({ page }, testInfo) => {
    await page.addInitScript(() => window.localStorage.setItem("ma_vid", "v_e2e_assistant_0001"));
    await page.goto(`${store.url}/?ma_api=${encodeURIComponent(AGENT_API)}`);
    await page.getByTestId("ma-launcher").click();
    await page.getByTestId("ma-input").fill(PROMPTS[store.id].text);
    await page.getByTestId("ma-send").click();

    const bundle = page.getByTestId("ma-bundle");
    await expect(bundle).toBeVisible({ timeout: 30_000 });
    await expect(bundle).toContainText(PROMPTS[store.id].expect);
    await expect(page.getByTestId("ma-sources")).toContainText("föye göre");
    const answer = await page.getByTestId("ma-bot-msg").last().innerText();
    const skus = answer.match(/[A-Z]{2}-[A-Z]{3}-\d{4}/g) ?? [];
    expect(skus.length).toBeGreaterThan(0);
    expect(skus.every((s) => s.startsWith(store.id === "ambalaj" ? "KC-" : "YM-"))).toBe(true);
    await shot(page, testInfo, "m5", `${store.id}-real-agent`, false);

    const items = await bundle.locator("li").count();
    await page.getByTestId("ma-add-bundle").click();
    await expect(page.getByTestId("cart-count")).toHaveText(String(items));
  });
}
