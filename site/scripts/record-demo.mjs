// Record the real production-built directory using only fixed-clock synthetic state.
// Raw video and screenshots stay ignored. See docs/assets/README.md for encoding.
import {spawn, spawnSync} from "node:child_process";
import {mkdirSync, writeFileSync} from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {chromium, expect} from "@playwright/test";

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const root = path.dirname(site);
const output = path.join(root, "quality-reports", "demo");
mkdirSync(output, {recursive: true});
const fixture = spawnSync(
  "uv",
  ["run", "--frozen", "python", "scripts/testing/create_site_fixture.py", "--demo"],
  {
    cwd: root,
    stdio: "inherit",
    shell: false,
  }
);
if (fixture.error) throw fixture.error;
if (fixture.status !== 0) throw new Error("Synthetic fixture creation failed");

const origin = "http://127.0.0.1:3200";
const env = {
  ...process.env,
  HOSTNAME: "127.0.0.1",
  PORT: "3200",
  SITE_URL: origin,
  OPPORTUNITIES_DATABASE_PATH: path.join(site, "tests/e2e/.tmp/demo/opportunities.db"),
  OPPORTUNITIES_PUBLIC_EXPORT_DIR: path.join(site, "tests/e2e/.tmp/demo"),
  OPPORTUNITIES_SCHEMA_PATH: path.join(root, "schemas/opportunities-v1.schema.json"),
};
delete env.OPPORTUNITIES_RELEASE_ROOT;
const server = spawn(process.execPath, ["scripts/start.mjs"], {cwd: site, env, stdio: "pipe"});
let serverLog = "";
server.stdout.on("data", (data) => {
  serverLog += data;
});
server.stderr.on("data", (data) => {
  serverLog += data;
});
let browser;
try {
  // Do not probe a different service if this port was already occupied.
  await expect
    .poll(() => server.exitCode === null && serverLog.includes("Ready in"), {
      timeout: 30_000,
    })
    .toBe(true);
  expect((await fetch(origin)).status).toBe(200);
  browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: {width: 1600, height: 900},
    deviceScaleFactor: 1,
    colorScheme: "light",
    reducedMotion: "reduce",
    locale: "en-GB",
    timezoneId: "UTC",
    recordVideo: {dir: output, size: {width: 1600, height: 900}},
  });
  await context.route("**/*", (route) =>
    new URL(route.request().url()).origin === origin ? route.continue() : route.abort()
  );
  await context.addInitScript(() => {
    localStorage.setItem("opportunities-theme", "light");
    localStorage.setItem(
      "opportunities-directory-state",
      JSON.stringify({
        version: 1,
        lastVisitAt: "2026-09-27T12:00:00.000Z",
        saved: [],
        hidden: [],
        applied: [],
      })
    );
  });
  const page = await context.newPage();
  await page.clock.setFixedTime(new Date("2026-09-28T12:00:00.000Z"));
  await page.goto(origin, {waitUntil: "networkidle"});
  await expect(page.getByRole("button", {name: "View new opportunities"})).toBeVisible();
  await page.addStyleTag({
    content: `
    #demo-caption {position:fixed; bottom:18px; left:50%; transform:translateX(-50%); z-index:100;
      background:#102439; color:#fff; padding:14px 28px; border:1px solid #506c8a; border-radius:12px;
      box-shadow:0 10px 40px #0003; font:500 22px Arial,sans-serif; text-align:center; white-space:nowrap}
    #demo-label {position:fixed; top:17px; left:50%; transform:translateX(-50%); z-index:100;
      color:#677583; font:700 11px Arial,sans-serif; letter-spacing:1.6px; pointer-events:none}
  `,
  });
  await page.evaluate(() => {
    const caption = document.createElement("div");
    caption.id = "demo-caption";
    document.body.append(caption);
    const label = document.createElement("div");
    label.id = "demo-label";
    label.textContent = "PRODUCT TOUR · SYNTHETIC DATA · NO LIVE COLLECTION";
    document.body.append(label);
  });
  const began = Date.now();
  const marks = [];
  async function caption(text) {
    await page.locator("#demo-caption").evaluate((element, value) => {
      element.textContent = value;
    }, text);
    marks.push({seconds: (Date.now() - began) / 1000, text});
  }
  async function at(seconds) {
    await page.waitForTimeout(Math.max(0, began + seconds * 1000 - Date.now()));
  }
  async function click(locator) {
    const box = await locator.boundingBox();
    if (box) await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, {steps: 12});
    await locator.click();
  }
  await caption("Find your next tech role in Europe.");
  await page.screenshot({path: path.join(output, "poster.png")});
  await at(3);
  await caption("Search roles. Cut through the noise.");
  await click(page.getByLabel("Search"));
  await page.getByLabel("Search").pressSequentially("intern", {delay: 130});
  await at(6);
  await caption("Narrow it down by company, location or category.");
  await page.getByLabel("Company").selectOption("Acme Labs");
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await at(9);
  await caption("Save a shortlist — privately, in your browser.");
  await click(page.getByRole("button", {name: "Save Cybersecurity Intern 2027 at Acme Labs"}));
  await at(12);
  await click(page.getByRole("button", {name: "View 1 saved opportunities"}));
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await at(14);
  await caption("Keep track of applications. No account needed.");
  await click(
    page.getByRole("button", {name: "Mark applied Cybersecurity Intern 2027 at Acme Labs"})
  );
  await at(17);
  await click(page.getByRole("button", {name: "View all opportunities"}));
  await click(page.getByRole("button", {name: "Reset", exact: true}));
  await caption("Come back to see what’s new since your last visit.");
  await click(page.getByRole("button", {name: "View new opportunities"}));
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await at(21);
  await click(page.getByRole("button", {name: "Toggle color theme"}));
  await caption("Your next opportunity starts at techopportunities.eu");
  await at(26);
  await page.screenshot({path: path.join(output, "end.png")});
  const video = page.video();
  await context.close();
  await video.saveAs(path.join(output, "directory-tour-raw.webm"));
  writeFileSync(path.join(output, "timeline.json"), JSON.stringify(marks, null, 2));
} finally {
  await browser?.close();
  server.kill();
  writeFileSync(path.join(output, "server.log"), serverLog);
}
