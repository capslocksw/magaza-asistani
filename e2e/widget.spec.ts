import { expect, test, type Page } from "@playwright/test";
import { STORES, isMobile, shot } from "./helpers";

// Visitor ids whose deterministic holdout bucket is known (see assign_group / assignGroup).
const ASSISTANT_VISITOR = "v_e2e_assistant_0001";
const CONTROL_VISITOR = "v_e2e_control_0014"; // control group for yapi-market at 10% holdout
const MOCK_AGENT = "http://localhost:8787";

const PROMPTS: Record<(typeof STORES)[number]["id"], string> = {
  "yapi-market": "Kornişim koptu, matkabım yok",
  ambalaj: "2 kg seramik kupa göndereceğim, hangi koli?",
};

async function asVisitor(page: Page, visitorId: string) {
  await page.addInitScript((id) => {
    window.localStorage.setItem("ma_vid", id);
    window.sessionStorage.removeItem("ma-demo-agent-url");
  }, visitorId);
}

async function mockEvents(page: Page): Promise<{ event_type: string; tenant_id: string; visitor_id: string; payload: Record<string, unknown> }[]> {
  const res = await page.request.get(`${MOCK_AGENT}/__events`);
  return res.json();
}

for (const store of STORES) {
  test.describe(`widget on ${store.id} (mock-agent)`, () => {
    test("open → ask → product cards → add bundle → storefront cart grows → order tracked", async ({ page }, testInfo) => {
      await asVisitor(page, `${ASSISTANT_VISITOR}`);
      await page.goto(`${store.url}/`);
      const launcher = page.getByTestId("ma-launcher");
      await expect(launcher).toBeVisible();
      await expect(page.getByTestId("cart-count")).toHaveText("0");
      await shot(page, testInfo, "m4", `${store.id}-01-launcher`, false);

      await launcher.click();
      const panel = page.getByTestId("ma-panel");
      await expect(panel).toBeVisible();
      await expect(page.getByTestId("ma-suggestions")).toBeVisible();
      await shot(page, testInfo, "m4", `${store.id}-02-open`, false);

      await page.getByTestId("ma-input").fill(PROMPTS[store.id]);
      await page.getByTestId("ma-send").click();
      await expect(page.getByTestId("ma-user-msg")).toHaveText(PROMPTS[store.id]);
      await expect(page.getByTestId("ma-bundle")).toBeVisible();
      const cards = page.getByTestId("ma-products").locator(".card");
      expect(await cards.count()).toBeGreaterThanOrEqual(2);
      await expect(page.getByTestId("ma-sources")).toContainText("föye göre");
      await expect(page.getByTestId("ma-bot-msg").last()).toContainText("Önerim");
      await shot(page, testInfo, "m4", `${store.id}-03-answer`, false);

      const bundleItems = await page.getByTestId("ma-bundle").locator("li").count();
      await page.getByTestId("ma-add-bundle").click();
      await expect(page.getByTestId("ma-add-bundle")).toHaveText(/Sepete eklendi/);
      await expect(page.getByTestId("cart-count")).toHaveText(String(bundleItems));
      await shot(page, testInfo, "m4", `${store.id}-04-added`, false);

      await expect
        .poll(async () => (await mockEvents(page)).some((e) => e.event_type === "add_to_cart" && e.tenant_id === store.id))
        .toBe(true);

      if (isMobile(testInfo)) await page.getByTestId("ma-close").click();
      await page.goto(`${store.url}/odeme/`);
      await page.getByLabel("Ad soyad").fill("Deniz Test");
      await page.getByLabel("Telefon").fill("05550000000");
      await page.getByLabel("E-posta").fill("deniz@example.com");
      await page.getByLabel("Adres").fill("Demo Mah. Test Sok. No:1");
      await page.getByTestId("place-order").click();
      await expect(page.getByTestId("order-confirmation")).toHaveAttribute("data-tracked", "true");
      const orderId = await page.getByTestId("order-id").innerText();
      await expect
        .poll(async () => (await mockEvents(page)).find((e) => e.event_type === "order" && e.payload.order_id === orderId)?.payload.assisted)
        .toBe(true);
    });
  });
}

test("ambalaj: B2B quote request form (only on the tenant that enables it)", async ({ page }, testInfo) => {
  await asVisitor(page, ASSISTANT_VISITOR);
  await page.goto("http://localhost:3102/");
  await page.getByTestId("ma-launcher").click();
  await page.getByTestId("ma-input").fill("Ayda 1000 koli gönderiyorum, teklif alabilir miyim?");
  await page.getByTestId("ma-send").click();
  await page.getByTestId("ma-quote-suggest").click();
  const form = page.getByTestId("ma-quote-form");
  await form.getByLabel("Firma adı").fill("Kupa Atölyesi Ltd.");
  await form.getByLabel("Ad soyad").fill("Deniz Kaya");
  await form.getByLabel("E-posta").fill("deniz@example.com");
  await shot(page, testInfo, "m4", "ambalaj-05-quote-form", false);
  await page.getByTestId("ma-quote-submit").click();
  await expect(page.getByTestId("ma-quote-done")).toContainText("Teklif talebiniz alındı");

  await page.goto("http://localhost:3101/");
  await page.getByTestId("ma-launcher").click();
  await expect(page.getByTestId("ma-quote-open")).toHaveCount(0);
});

test("holdout visitors do not see the widget but their visit is counted", async ({ page }) => {
  await asVisitor(page, CONTROL_VISITOR);
  await page.goto("http://localhost:3101/");
  await expect
    .poll(async () => (await mockEvents(page)).some((e) => e.event_type === "visit" && e.visitor_id === CONTROL_VISITOR && e.payload.group === "control"))
    .toBe(true);
  await expect(page.getByTestId("ma-launcher")).toHaveCount(0);
});
