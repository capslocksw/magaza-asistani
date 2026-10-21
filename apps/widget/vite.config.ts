import { defineConfig } from "vitest/config";

// Builds a single self-contained IIFE: dist/widget.js (CSS is inlined in the shadow root).
export default defineConfig({
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
