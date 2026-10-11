import {expect, test} from "@playwright/test";
import {LOCAL_STATE_KEY} from "@/lib/local-opportunity-state";
import {expectResultCount} from "./helpers";

test("hydration restores private lists without guessing their counts in server HTML", async ({
  page,
}) => {
  await page.addInitScript((key) => {
    localStorage.setItem(
      key,
      JSON.stringify({
        version: 1,
        lastVisitAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        saved: ["1000000001", "1000000012"],
        applied: ["1000000001"],
        hidden: ["1000000012"],
      })
    );
  }, LOCAL_STATE_KEY);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });

  // Hold application JavaScript so server HTML is observable before React reads private state.
  let releaseScripts!: () => void;
  const scriptsReady = new Promise<void>((resolve) => {
    releaseScripts = resolve;
  });
  await page.route(/\/_next\/static\/.*\.js(?:\?.*)?$/, async (route) => {
    await scriptsReady;
    await route.continue();
  });
  try {
    // DOMContentLoaded would wait for the withheld scripts; commit exposes the server HTML.
    const response = await page.goto("/", {waitUntil: "commit"});
    expect(response?.ok()).toBe(true);
    const html = await response!.text();
    expect(html).not.toContain("You have saved");
    expect(html).not.toContain("new opportunities since your last visit");
    const directory = page.getByRole("region", {name: "Opportunity directory"});
    await expect(directory).toHaveAttribute("aria-busy", "true");
    await expectResultCount(page, 12);
    await expect(page.getByText("You have saved", {exact: false})).toHaveCount(0);
    await expect(page.getByText(/new opportunities since your last visit/)).toHaveCount(0);
    for (const list of ["saved", "applied", "hidden"]) {
      await expect(
        page.getByRole("button", {name: new RegExp(`View \\d+ ${list} opportunities`)})
      ).toHaveCount(0);
    }
    releaseScripts();
    await expect(directory).toHaveAttribute("aria-busy", "false");
    await expectResultCount(page, 11);
    // Hidden rows keep their saved marks but do not appear in the saved view.
    await page.getByRole("button", {name: "View 2 saved opportunities"}).click();
    await expectResultCount(page, 1);
    await expect(
      page.getByRole("link", {name: "Software Engineering Intern 2027", exact: true})
    ).toBeVisible();
    await expect(page).toHaveURL("/");
    expect(errors).toEqual([]);
  } finally {
    releaseScripts();
  }
});
