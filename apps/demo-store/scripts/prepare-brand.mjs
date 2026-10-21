// Copies the generated demo data of one brand (data/demo/<brand>) into public/ and writes a compact
// search index. Run before `next build` / `next dev`; BRAND=yapi-market|ambalaj (default yapi-market).
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const appDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const brand = process.env.BRAND ?? "yapi-market";
const dataDir = resolve(appDir, "../../data/demo", brand);
const publicDir = join(appDir, "public");

if (!existsSync(join(dataDir, "catalog.json"))) {
  console.error(`Demo data for "${brand}" not found in ${dataDir}. Run \`make data\` first.`);
  process.exit(1);
}

for (const sub of ["images", "docs", "feed.xml", "logo.svg", "search-index.json"]) {
  rmSync(join(publicDir, sub), { recursive: true, force: true });
}
mkdirSync(publicDir, { recursive: true });
cpSync(join(dataDir, "images"), join(publicDir, "images"), { recursive: true });
mkdirSync(join(publicDir, "docs"), { recursive: true });
cpSync(join(dataDir, "docs"), join(publicDir, "docs"), {
  recursive: true,
  filter: (src) => !src.endsWith(".md"),
});
cpSync(join(dataDir, "feed.xml"), join(publicDir, "feed.xml"));
cpSync(join(dataDir, "logo.svg"), join(publicDir, "logo.svg"));

const catalog = JSON.parse(readFileSync(join(dataDir, "catalog.json"), "utf8"));
const index = catalog.map((p) => ({
  sku: p.sku,
  title: p.title,
  brand: p.brand,
  category: p.category,
  category_name: p.category_name,
  subcategory: p.subcategory,
  tags: p.tags,
  price: p.price,
  list_price: p.list_price,
  stock: p.stock,
  image_url: p.image_url,
  url: p.url,
  rating: p.rating,
  review_count: p.review_count,
  sales_rank: p.sales_rank,
  max_installments: p.max_installments,
  free_shipping: p.free_shipping,
}));
writeFileSync(join(publicDir, "search-index.json"), JSON.stringify(index));
console.log(`prepare-brand: ${brand} -> public/ (${catalog.length} products)`);
