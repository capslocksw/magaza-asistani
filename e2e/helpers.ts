import { mkdirSync } from "node:fs";
import type { Page, TestInfo } from "@playwright/test";

export const STORES = [
  { id: "yapi-market", url: "http://localhost:3101", category: "yapistirici-silikon", search: "silikon" },
  { id: "ambalaj", url: "http://localhost:3102", category: "koli-cift-oluklu", search: "koli bandı" },
] as const;

/** Saves a screenshot under artifacts/screenshots/<group>/<name>-<project>.png for later design review. */
export async function shot(page: Page, testInfo: TestInfo, group: string, name: string, fullPage = true): Promise<void> {
  const dir = `artifacts/screenshots/${group}`;
  mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: `${dir}/${name}-${testInfo.project.name}.png`, fullPage });
}

export function isMobile(testInfo: TestInfo): boolean {
  return testInfo.project.name === "mobile";
}
