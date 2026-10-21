import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 5175, strictPort: true },
  preview: { port: 5175, strictPort: true },
  build: { chunkSizeWarningLimit: 1500 },
  test: { environment: "happy-dom" },
});
