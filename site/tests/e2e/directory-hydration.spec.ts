import {expect, test} from "@playwright/test";
import {LOCAL_STATE_KEY} from "@/lib/local-opportunity-state";
import {expectResultCount} from "./helpers";

for (const width of [320, 390, 1085, 1280]) {
  for (const visit of ["first", "returning", "all-hidden", "corrupt", "blocked"] as const) {
    test(`${visit} visit keeps the header and directory in place during hydration at ${width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({width, height: 900});
      await page.addInitScript(
        ({key, visit}) => {
          if (visit === "blocked") {
            Object.defineProperty(window, "localStorage", {
              get: () => {
                throw new Error("Storage is unavailable");
              },
            });
          } else if (visit === "corrupt") {
            localStorage.setItem(key, "{bad");
          } else if (visit !== "first") {
            const ids = Array.from({length: 12}, (_, index) => String(1000000001 + index));
            localStorage.setItem(
              key,
              JSON.stringify({
                version: 1,
                lastVisitAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
                saved: visit === "all-hidden" ? ids : ids.slice(0, 4),
                applied: visit === "all-hidden" ? ids : ids.slice(0, 4),
                hidden: visit === "all-hidden" ? ids : [ids[11]],
              })
            );
          }
        },
        {key: LOCAL_STATE_KEY, visit}
      );

      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });

      // Hold JavaScript, not HTML/CSS, so the server-rendered layout is measured separately.
      let releaseScripts!: () => void;
      const scriptsReady = new Promise<void>((resolve) => {
        releaseScripts = resolve;
      });
      await page.route(/\/_next\/static\/.*\.js(?:\?.*)?$/, async (route) => {
        await scriptsReady;
        await route.continue();
      });

      try {
        await page.goto("/", {waitUntil: "commit"});
        const directory = page.getByRole("region", {name: "Opportunity directory"});
        const total = page.getByRole("status", {name: "Open roles", exact: true});
        await expect(directory).toHaveAttribute("aria-busy", "true");
        await expect(total).toHaveText("12 open roles");
        await expect(page.getByRole("button", {name: /View \d+ saved opportunities/})).toHaveCount(
          0
        );
        await page.waitForFunction(() =>
          Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')).every(
            (link) => link.sheet !== null
          )
        );
        await page.evaluate(() => document.fonts.ready.then(() => undefined));

        const anchors = [
          page.getByRole("heading", {name: "Opportunity directory"}),
          page.getByRole("link", {name: "Download CSV"}),
          total,
          page.getByRole("search", {name: "Opportunity filters"}),
          page.getByRole("table", {name: "Open opportunities"}),
        ];
        const initialTops = await Promise.all(
          anchors.map((anchor) => anchor.evaluate((element) => element.getBoundingClientRect().top))
        );

        releaseScripts();
        await expect(directory).toHaveAttribute("aria-busy", "false");
        const count = visit === "all-hidden" ? 12 : visit === "returning" ? 4 : 0;
        const hiddenCount = visit === "all-hidden" ? 12 : visit === "returning" ? 1 : 0;
        await expect(
          page.getByRole("button", {name: `View ${count} saved opportunities`})
        ).toBeVisible();
        await expect(
          page.getByRole("button", {name: `View ${count} applied opportunities`})
        ).toBeVisible();
        await expect(
          page.getByRole("button", {name: `View ${hiddenCount} hidden opportunities`})
        ).toBeVisible();
        if (visit === "returning") {
          await expect(page.getByRole("button", {name: "View new opportunities"})).toBeVisible();
        } else {
          await expect(page.getByRole("button", {name: "View new opportunities"})).toHaveCount(0);
        }
        await expectResultCount(page, 12 - hiddenCount);
        for (const [index, anchor] of anchors.entries()) {
          const top = await anchor.evaluate((element) => element.getBoundingClientRect().top);
          expect(Math.abs(top - initialTops[index])).toBeLessThan(1);
        }
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
          width
        );
        expect(errors).toEqual([]);
      } finally {
        releaseScripts();
      }
    });
  }
}
