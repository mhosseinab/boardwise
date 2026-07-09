import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// BoardWise frontend (S14). Dev-server proxy forwards relative /api/* calls
// (decision §4.11) to the local FastAPI backend on port 8006 so the SPA can
// always call same-origin `/api/...` paths in both dev and the nginx-served
// production build.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8006",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    css: false,
  },
});
