import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadTenants, type MockTenant } from "../mock-agent/scenarios.mjs";

export const DATA_DIR = join(dirname(fileURLToPath(import.meta.url)), "../../../data/demo");
export const HAS_DATA = existsSync(join(DATA_DIR, "yapi-market", "catalog.json"));
export const tenants: Map<string, MockTenant> = HAS_DATA ? loadTenants(DATA_DIR) : new Map();
