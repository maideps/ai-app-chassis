/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // 5173 falls in a Windows excluded port range on some machines; PORT overrides.
    port: Number(process.env.PORT ?? 4173),
    // The UI calls /api/*; the FastAPI backend serves the same routes at its root. In
    // production a reverse proxy does this rewrite, so the backend needs no CORS setup.
    proxy: {
      "/api": {
        target: process.env.API_URL ?? "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
