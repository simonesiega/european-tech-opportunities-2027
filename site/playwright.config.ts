import path from "node:path";
import {defineConfig, devices} from "@playwright/test";

const testDatabasePath = path.resolve("tests/e2e/.tmp/opportunities.db");

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    colorScheme: "light",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: {...devices["Desktop Chrome"]},
    },
  ],
  webServer: {
    command: "bun run dev --hostname 127.0.0.1 --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      INTERNSHIPS_DATABASE_PATH: testDatabasePath,
      SITE_URL: "http://127.0.0.1:3100",
    },
  },
});
