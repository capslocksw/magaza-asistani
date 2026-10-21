// Builds one static export per demo brand: dist/yapi-market and dist/ambalaj.
import { spawnSync } from "node:child_process";
import { cpSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const nextBin = createRequire(import.meta.url).resolve("next/dist/bin/next");
const brands = process.argv.slice(2).length ? process.argv.slice(2) : ["yapi-market", "ambalaj"];

function run(args, brand) {
  const result = spawnSync(process.execPath, args, { cwd: appDir, stdio: "inherit", env: { ...process.env, BRAND: brand } });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

for (const brand of brands) {
  console.log(`\n=== building demo store: ${brand} ===`);
  run([join(appDir, "scripts", "prepare-brand.mjs")], brand);
  run([nextBin, "build"], brand);
  const target = join(appDir, "dist", brand);
  rmSync(target, { recursive: true, force: true });
  cpSync(join(appDir, "out"), target, { recursive: true });
  console.log(`=> ${target}`);
}
