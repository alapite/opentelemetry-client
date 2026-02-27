import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  base: "/ui/",
  plugins: [react()],
  build: {
    outDir: path.resolve(__dirname, "../src/primes/ui/dist"),
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./vitest.setup.ts",
  },
});
