import { expect, test } from "@playwright/test";
import { STORES, shot } from "./helpers";

for (const store of STORES) {
  test.describe(`demo store ${store.id}`, () => {
    test("browse → add to cart → checkout → order confirmation", async ({ page }, testInfo) => {
      await page.goto(`${store.url}/`);
      await expect(page.locator("html")).toHaveAttribute("data-brand", store.id);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByTestId("product-card").first()).toBeVisible();
      await shot(page, testInfo, "m3", `${store.id}-01-home`);

      await page.goto(`${store.url}/kategori/${store.category}/`);
      await expect(page.getByTestId("product-card").first()).toBeVisible();
      const total = Number(await page.getByTestId("result-count").innerText());
      expect(total).toBeGreaterThan(5);
      await page.getByLabel("Sırala").selectOption("price-asc");
      await shot(page, testInfo, "m3", `${store.id}-02-category`);

      await page.goto(`${store.url}/ara/?q=${encodeURIComponent(store.search)}`);
      await expect(page.getByTestId("product-card").first()).toBeVisible();
      await shot(page, testInfo, "m3", `${store.id}-03-search`);

      const card = page.getByTestId("product-card").filter({ has: page.getByTestId("add-to-cart") }).first();
      const sku = await card.getAttribute("data-sku");
      await card.locator("h3 a").click();
      await expect(page).toHaveURL(new RegExp(`/urun/${sku}/$`));
      await expect(page.getByTestId("product-title")).toBeVisible();
      await expect(page.getByRole("heading", { name: "Teknik özellikler" })).toBeVisible();
      await shot(page, testInfo, "m3", `${store.id}-04-product`);

      await page.getByTestId("add-to-cart-main").click();
      await expect(page.getByTestId("cart-item")).toHaveCount(1);
      await expect(page.getByTestId("cart-count")).toHaveText("1");
      await shot(page, testInfo, "m3", `${store.id}-05-cart`, false);

      await page.getByTestId("checkout-link").click();
      await expect(page).toHaveURL(/\/odeme\/$/);
      await page.getByLabel("Ad soyad").fill("Deniz Test");
      await page.getByLabel("Telefon").fill("05550000000");
      await page.getByLabel("E-posta").fill("deniz@example.com");
      await page.getByLabel("Adres").fill("Demo Mah. Test Sok. No:1 Kadıköy");
      await shot(page, testInfo, "m3", `${store.id}-06-checkout`);
      await page.getByTestId("place-order").click();

      await expect(page.getByTestId("order-confirmation")).toBeVisible();
      await expect(page.getByTestId("order-id")).toHaveText(/^ORD-[0-9A-Z]+$/);
      await expect(page.getByTestId("cart-count")).toHaveText("0");
      await shot(page, testInfo, "m3", `${store.id}-07-confirmation`);
    });

    test("product page links its data sheet PDF and the merchant feed is served", async ({ page, request }) => {
      const feed = await request.get(`${store.url}/feed.xml`);
      expect(feed.ok()).toBeTruthy();
      const xml = await feed.text();
      expect(xml).toContain('xmlns:g="http://base.google.com/ns/1.0"');
      const sku = /<g:id>([^<]+)<\/g:id>/.exec(xml)?.[1];
      expect(sku).toBeTruthy();

      const withDoc = /<g:id>([^<]+)<\/g:id>(?:(?!<\/item>)[\s\S])*<ma:doc_url>([^<]+)<\/ma:doc_url>/.exec(xml);
      expect(withDoc).toBeTruthy();
      await page.goto(`${store.url}/urun/${withDoc![1]}/`);
      const link = page.getByTestId("datasheet-link");
      await expect(link).toHaveAttribute("href", withDoc![2]!);
      const pdf = await request.get(`${store.url}${withDoc![2]}`);
      expect(pdf.headers()["content-type"]).toBe("application/pdf");
    });
  });
}
