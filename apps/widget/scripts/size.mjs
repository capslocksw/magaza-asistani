// Fails if the gzip size of dist/widget.js reaches the 60 KB budget.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const LIMIT = 60 * 1024;
const file = join(dirname(fileURLToPath(import.meta.url)), "..", "dist", "widget.js");
const raw = readFileSync(file);
const gz = gzipSync(raw, { level: 9 }).length;
console.log(`widget.js: ${(raw.length / 1024).toFixed(1)} KB raw, ${(gz / 1024).toFixed(1)} KB gzip (limit ${LIMIT / 1024} KB)`);
if (gz >= LIMIT) process.exit(1);
