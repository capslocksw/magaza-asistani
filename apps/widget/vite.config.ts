import { defineConfig } from "vitest/config";

// Builds a single self-contained IIFE: dist/widget.js (CSS is inlined in the shadow root).
// AGENT_URL (see .env.example) becomes the default agent of the built widget; empty -> mock-agent.
const agentUrl = process.env.VITE_AGENT_URL ?? process.env.AGENT_URL ?? "";

export default defineConfig({
  define: { "import.meta.env.VITE_AGENT_URL": JSON.stringify(agentUrl) },
  build: {
    lib: { entry: "src/main.ts", name: "MagazaAsistaniWidget", formats: ["iife"], fileName: () => "widget.js" },
    outDir: "dist",
    emptyOutDir: true,
    target: "es2020",
    minify: "esbuild",
    sourcemap: false,
  },
  server: { port: 5174, strictPort: true },
  test: { environment: "happy-dom" },
});
