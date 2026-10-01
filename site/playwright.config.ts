import path from "node:path";
import {defineConfig, devices} from "@playwright/test";

const testFixtureDirectory = path.resolve("tests/e2e/.tmp");
const testDatabasePath = path.join(testFixtureDirectory, "opportunities.db");

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: 1,
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
    command: "bun run dev --webpack --hostname 127.0.0.1 --port 3100",
    url: "http://127.0.0.1:3100",
    // A reused dev server may read non-fixture state; always start the isolated test server.
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      NEXT_DIST_DIR: ".next-e2e",
      OPPORTUNITIES_DATABASE_PATH: testDatabasePath,
      OPPORTUNITIES_PUBLIC_EXPORT_DIR: testFixtureDirectory,
      // Never inherit an operator's production release or schema override.
      OPPORTUNITIES_RELEASE_ROOT: "",
      OPPORTUNITIES_SCHEMA_PATH: path.resolve("../schemas/opportunities-v1.schema.json"),
      SITE_URL: "http://127.0.0.1:3100",
    },
  },
});
