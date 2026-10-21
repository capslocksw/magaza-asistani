import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { shot } from "./helpers";

const ADMIN = "http://localhost:5175";
const PAGES = [
  { path: "/", heading: "Yönetici özeti", name: "01-yonetici-ozeti" },
  { path: "/huni", heading: "Dönüşüm hunisi", name: "02-huni" },
  { path: "/talepler", heading: "Müşteri talepleri", name: "03-talepler" },
  { path: "/karsilanmayan", heading: "Karşılanmayan talep", name: "04-karsilanmayan" },
  { path: "/urunler", heading: "Ürün ve paket performansı", name: "05-urunler" },
  { path: "/kalite", heading: "Konuşma kalitesi", name: "06-kalite" },
  { path: "/kullanim", heading: "Kullanım ve maliyet", name: "07-kullanim" },
  { path: "/konusmalar", heading: "Konuşmalar", name: "08-konusmalar" },
  { path: "/ayarlar", heading: "Tenant ayarları", name: "09-ayarlar" },
];

test.describe("admin panel", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${ADMIN}/giris`);
    await page.getByTestId("dev-login").click();
    await expect(page.getByRole("heading", { name: "Yönetici özeti" })).toBeVisible();
  });

  test("every dashboard renders with data", async ({ page }, testInfo) => {
    for (const p of PAGES) {
      await page.goto(`${ADMIN}${p.path}`);
      await expect(page.getByRole("heading", { level: 1, name: p.heading })).toBeVisible();
      if (p.path !== "/ayarlar") {
        await expect(page.getByTestId("data-table").or(page.getByTestId("chart")).first()).toBeVisible();
        await expect(page.getByText("Veri alınamadı")).toHaveCount(0);
      }
      await page.waitForTimeout(400); // let ECharts finish its entry animation before the screenshot
      await shot(page, testInfo, "m6", p.name);
    }
    await page.getByTestId("tenant-select").selectOption("ambalaj");
    await page.goto(`${ADMIN}/`);
    await expect(page.getByTestId("kpi").first()).toContainText("₺");
    await shot(page, testInfo, "m6", "10-ambalaj-yonetici-ozeti");
  });

  test("downloads a CSV and the monthly PDF report", async ({ page }) => {
    const [csv] = await Promise.all([page.waitForEvent("download"), page.getByTestId("csv-yonetici-ozeti").click()]);
    expect(csv.suggestedFilename()).toMatch(/yonetici-ozeti.*\.csv$/);
    const csvBytes = readFileSync((await csv.path())!);
    expect(csvBytes.subarray(0, 3)).toEqual(Buffer.from([0xef, 0xbb, 0xbf]));
    expect(csvBytes.toString("utf8")).toContain("Asistan destekli ciro (TL)");

    const [pdf] = await Promise.all([page.waitForEvent("download", { timeout: 60_000 }), page.getByTestId("pdf-report").click()]);
    expect(pdf.suggestedFilename()).toMatch(/rapor-\d{4}-\d{2}\.pdf$/);
    expect(readFileSync((await pdf.path())!).subarray(0, 5).toString()).toBe("%PDF-");
  });

  test("conversation explorer opens a conversation", async ({ page }, testInfo) => {
    await page.goto(`${ADMIN}/konusmalar`);
    await page.getByTestId("data-table").locator("tbody tr").first().click();
    const detail = page.getByTestId("conversation-detail");
    await expect(detail).toBeVisible();
    await expect(detail.locator("p").first()).not.toBeEmpty();
    await shot(page, testInfo, "m6", "11-konusma-detayi", false);
  });
});
