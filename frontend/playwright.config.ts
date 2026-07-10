import { defineConfig, devices } from "@playwright/test";

// S18 offline Playwright smoke test. Chromium only, fixed port, zero retries
// (deterministic per project rule "offline determinism"). The webServer runs
// the plain Vite dev server on a fixed, non-default port so the test never
// collides with a developer's own `npm run dev`; every network call the app
// makes during the test is intercepted in `e2e/smoke.spec.ts` via
// `page.route`, so no real backend on :8006 is required or contacted.
const PORT = 4319;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    port: PORT,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
