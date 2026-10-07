import AxeBuilder from "@axe-core/playwright";
import {expect, test} from "@playwright/test";
import {expectResultCount, openDirectory} from "./helpers";

const key = "opportunities-directory-state";
const role = "Software Engineering Intern 2027";

test("crawler HTML contains no fabricated local-state summaries", async ({request, page}) => {
  const response = await request.get("/");
  expect(response.ok()).toBe(true);
  const html = await response.text();
  expect(html).not.toContain("You have saved");
  expect(html).not.toContain("new opportunities since your last visit");

  await openDirectory(page);
  await expect(page.getByText("You have saved", {exact: false})).toHaveCount(1);
  await expect(page.getByRole("button", {name: "View 0 saved opportunities"})).toBeVisible();
  await expect(page.getByRole("button", {name: "View 0 applied opportunities"})).toBeVisible();
  await expect(page.getByRole("button", {name: "View 0 hidden opportunities"})).toBeVisible();
});

test("first and returning visits, corrupt state and stale IDs", async ({page}) => {
  await openDirectory(page);
  await expect(page.getByRole("cell", {name: /Not new since your last visit/})).toHaveCount(10);
  await expect(page.getByText(/new opportunities since your last visit/)).toBeHidden();
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), key)).not.toBeNull();
  await page.evaluate(
    (key) =>
      localStorage.setItem(
        key,
        JSON.stringify({
          version: 1,
          lastVisitAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          saved: ["gone"],
          hidden: [],
          applied: [],
        })
      ),
    key
  );
  await page.reload();
  await expect(
    page.getByText("We found 2 new opportunities since your last visit.", {exact: false})
  ).toBeVisible();
  await page.getByRole("button", {name: "View new opportunities"}).click();
  await expectResultCount(page, 2);
  await expect(page.getByRole("cell", {name: /New since your last visit/})).toHaveCount(2);
  const markedBeforeReload = await page
    .getByRole("row")
    .filter({has: page.getByRole("cell", {name: /New since your last visit/})})
    .allTextContents();
  await page.reload();
  await expect(
    page.getByText("We found 2 new opportunities since your last visit.", {exact: false})
  ).toBeVisible();
  await page.getByRole("button", {name: "View new opportunities"}).click();
  await expectResultCount(page, 2);
  expect(
    await page
      .getByRole("row")
      .filter({has: page.getByRole("cell", {name: /New since your last visit/})})
      .allTextContents()
  ).toEqual(markedBeforeReload);
  const newest = page
    .getByRole("row")
    .filter({has: page.getByRole("cell", {name: /New since your last visit/})})
    .first();
  await newest.getByRole("button", {name: /More actions for/}).click();
  await page.getByRole("menuitem", {name: /Hide/}).click();
  await expectResultCount(page, 1);
  await expect(
    page.getByText("We found 1 new opportunity since your last visit.", {exact: false})
  ).toBeVisible();
  expect(JSON.parse((await page.evaluate((key) => localStorage.getItem(key), key))!).saved).toEqual(
    []
  );
  await page.evaluate((key) => localStorage.setItem(key, "{bad"), key);
  await page.reload();
  await expectResultCount(page, 12);
  await expect(page.getByText(/new opportunities since your last visit/)).toBeHidden();
});

test("empty local lists explain the selected view without claiming the directory is empty", async ({
  page,
}) => {
  await openDirectory(page);
  await page.getByRole("button", {name: "View 0 saved opportunities"}).click();
  await expectResultCount(page, 0);
  await expect(page.getByText("No saved opportunities to show", {exact: true})).toBeVisible();
  await page.getByRole("button", {name: "View 0 applied opportunities"}).click();
  await expect(page.getByText("No applied opportunities to show", {exact: true})).toBeVisible();
  await expect(page.getByText("The directory currently has no open roles.")).toHaveCount(0);
  await page.getByRole("button", {name: "View all opportunities"}).click();
  await expectResultCount(page, 12);
  await expect(page).toHaveURL("/");
});

test("mobile empty messages and reset controls need no horizontal scrolling", async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await openDirectory(page);
  await page.getByRole("button", {name: "View 0 saved opportunities"}).click();
  await expectResultCount(page, 0);
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await expect(page.getByText("No saved opportunities to show", {exact: true})).toBeInViewport({
    ratio: 1,
  });

  await openDirectory(page, "/?q=does-not-match-any-opportunity");
  await expectResultCount(page, 0);
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await expect(page.getByRole("button", {name: "Reset filters"})).toBeInViewport({ratio: 1});
  await page.getByRole("button", {name: "Reset filters"}).click();
  await expectResultCount(page, 12);
});

test("hiding every role leaves a clear route to restoring the directory", async ({page}) => {
  await openDirectory(page);
  await expect(page.getByRole("button", {name: "View 0 hidden opportunities"})).toBeVisible();
  await page.evaluate((key) => {
    const state = JSON.parse(localStorage.getItem(key)!);
    state.hidden = Array.from({length: 12}, (_, index) => String(1000000001 + index));
    localStorage.setItem(key, JSON.stringify(state));
  }, key);
  await page.reload();
  await expectResultCount(page, 0);
  await expect(page.getByText("No visible opportunities", {exact: true})).toBeVisible();
  await page.getByRole("button", {name: "View 12 hidden opportunities"}).click();
  await expectResultCount(page, 12);
  await page
    .getByRole("button", {name: /More actions for/})
    .first()
    .click();
  await page.getByRole("menuitem", {name: /Restore/}).click();
  await page.getByRole("button", {name: "View all opportunities"}).click();
  await expectResultCount(page, 1);
});

test("menu dismissal preserves tab order and focus after a viewport change", async ({page}) => {
  await openDirectory(page, "/?company=Acme+Labs");
  const name = "Cybersecurity Intern 2027 at Acme Labs";
  const trigger = page.getByRole("button", {name: `More actions for ${name}`});
  const menu = page.getByRole("menu", {name: `More actions for ${name}`});
  await trigger.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("menuitem", {name: `Hide ${name}`})).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(menu).toHaveCount(0);
  await expect(page.getByRole("link", {name: `Open ${role} at Acme Labs`})).toBeFocused();

  await trigger.focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Shift+Tab");
  await expect(menu).toHaveCount(0);
  await expect(page.getByRole("button", {name: `Mark applied ${name}`})).toBeFocused();

  await trigger.focus();
  await page.keyboard.press("Enter");
  await expect(menu).toBeVisible();
  await page.setViewportSize({width: 1100, height: 800});
  await expect(menu).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test("saved, applied, hidden and restored work across filters, pages and reloads", async ({
  page,
}) => {
  await openDirectory(page, "/?company=Acme+Labs&sort=company-asc&page-size=20");
  await page.getByRole("button", {name: `Save ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: `Mark applied ${role} at Acme Labs`}).click();
  await expect(page.getByRole("button", {name: "View 1 saved opportunities"})).toHaveAttribute(
    "aria-pressed",
    "false"
  );
  await page.getByRole("button", {name: "View 1 saved opportunities"}).click();
  await expectResultCount(page, 1);
  await page.reload();
  await page.getByRole("button", {name: "View 1 applied opportunities"}).click();
  await expect(page.getByRole("link", {name: role, exact: true})).toBeVisible();
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).click();
  await page.getByRole("menuitem", {name: `Hide ${role} at Acme Labs`}).click();
  await expectResultCount(page, 0);
  await page.getByRole("button", {name: "View 1 hidden opportunities"}).click();
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).click();
  await expect(page.getByRole("menuitem", {name: `Restore ${role} at Acme Labs`})).toBeVisible();
  await page.reload();
  await page.getByRole("button", {name: "View 1 hidden opportunities"}).click();
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).click();
  await page.getByRole("menuitem", {name: `Restore ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: "View 1 saved opportunities"}).click();
  await expectResultCount(page, 1);
  await expect(page).toHaveURL(/company=Acme\+Labs&sort=company-asc&page-size=20/);
  await page.getByRole("button", {name: `Unmark applied ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: "View 0 applied opportunities"}).click();
  await expectResultCount(page, 0);
  await page.getByRole("button", {name: "View all opportunities"}).click();
  await expectResultCount(page, 2);
  await expect(
    new AxeBuilder({page})
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"])
      .analyze()
      .then((result) => result.violations)
  ).resolves.toEqual([]);
});

test("saved rows respect pagination and sorting without changing URL semantics", async ({page}) => {
  await openDirectory(page);
  await page.getByRole("link", {name: "Next page"}).click();
  await page.getByRole("button", {name: `Save ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: "View 1 saved opportunities"}).click();
  await expect(page.getByRole("link", {name: role, exact: true})).toBeVisible();
  // Clamp the private list's page without rewriting the public pagination parameter.
  await expect(page).toHaveURL(/page=2/);
  await expect(page.getByText("Page 1 of 1")).toBeVisible();
  await page.getByRole("button", {name: "Company"}).click();
  await expect(page).toHaveURL(/sort=company-asc/);
  await expect(page.getByRole("link", {name: role, exact: true})).toBeVisible();
});

test("keyboard actions, menu dismissal, focus and mobile reachability", async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await openDirectory(page, "/?company=Acme+Labs");
  const save = page.getByRole("button", {name: `Save ${role} at Acme Labs`});
  await save.focus();
  await page.keyboard.press("Space");
  await expect(page.getByRole("button", {name: `Unsave ${role} at Acme Labs`})).toHaveAttribute(
    "aria-pressed",
    "true"
  );
  await expect(page.getByRole("button", {name: `Unsave ${role} at Acme Labs`})).toBeFocused();
  await page.getByRole("button", {name: `Mark applied ${role} at Acme Labs`}).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", {name: `Unmark applied ${role} at Acme Labs`})
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).focus();
  await page.keyboard.press("Enter");
  const menu = page.getByRole("menu", {name: `More actions for ${role} at Acme Labs`});
  await expect(menu).toBeVisible();
  const menuBox = await menu.boundingBox();
  expect(menuBox).not.toBeNull();
  // The menu must be reachable, not centered to a particular CSS implementation.
  expect(menuBox!.x).toBeGreaterThanOrEqual(0);
  expect(menuBox!.x + menuBox!.width).toBeLessThanOrEqual(390);
  expect(menuBox!.y + menuBox!.height).toBeLessThanOrEqual(844);
  await expect(page.getByRole("menuitem", {name: `Hide ${role} at Acme Labs`})).toBeFocused();
  expect(
    (
      await new AxeBuilder({page})
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"])
        .analyze()
    ).violations
  ).toEqual([]);
  // Wait past OpportunityActions' 150 ms opening-scroll grace period before testing dismissal.
  await page.waitForTimeout(200);
  await page
    .locator("table")
    .locator("..")
    .evaluate((container) => {
      container.scrollLeft = Math.max(0, container.scrollLeft - 60);
    });
  await expect(menu).toHaveCount(0);
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).focus();
  await page.keyboard.press("Enter");
  await expect(menu).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toHaveCount(0);
  await expect(
    page.getByRole("button", {name: `More actions for ${role} at Acme Labs`})
  ).toBeFocused();
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).click();
  await page.getByRole("menuitem", {name: `Hide ${role} at Acme Labs`}).click();
  await expectResultCount(page, 1);
  await page.getByRole("button", {name: "View 1 hidden opportunities"}).click();
  await expectResultCount(page, 1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test("local actions still work when storage access is disabled", async ({page}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get: () => {
        throw new Error("blocked");
      },
    });
  });
  await openDirectory(page, "/?company=Acme+Labs");
  await page.getByRole("button", {name: `Save ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: "View 1 saved opportunities"}).click();
  await expect(page.getByRole("link", {name: role, exact: true})).toBeVisible();
});

test("tabs merge sequential local actions and synchronize clearing without requests", async ({
  page,
  context,
}) => {
  const other = await context.newPage();
  await openDirectory(page, "/?company=Acme+Labs");
  await openDirectory(other, "/?company=Acme+Labs");
  // Observe only local actions, not the requests needed to load the two pages.
  const requests: string[] = [];
  context.on("request", (request) =>
    requests.push(`${request.method()} ${request.url()} ${request.postData() ?? ""}`)
  );
  await page.getByRole("button", {name: `Save ${role} at Acme Labs`}).click();
  await expect(other.getByRole("button", {name: `Unsave ${role} at Acme Labs`})).toHaveAttribute(
    "aria-pressed",
    "true"
  );
  await other
    .getByRole("button", {name: "Mark applied Cybersecurity Intern 2027 at Acme Labs"})
    .click();
  await expect(
    page.getByRole("button", {name: "Unmark applied Cybersecurity Intern 2027 at Acme Labs"})
  ).toHaveAttribute("aria-pressed", "true");
  const stored = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!), key);
  expect(stored.saved).toEqual(["1000000001"]);
  expect(stored.applied).toEqual(["1000000002"]);
  expect(Object.keys(stored).sort()).toEqual([
    "applied",
    "hidden",
    "lastVisitAt",
    "previousVisitAt",
    "saved",
    "version",
  ]);
  // Simulate a stale clear notification without clearing the newer value in storage.
  await page.evaluate((key) => {
    window.dispatchEvent(
      new StorageEvent("storage", {
        key,
        newValue: null,
        storageArea: window.localStorage,
      })
    );
  }, key);
  await expect(page.getByRole("button", {name: `Unsave ${role} at Acme Labs`})).toHaveAttribute(
    "aria-pressed",
    "true"
  );
  await expect(page.getByRole("button", {name: "View 1 applied opportunities"})).toBeVisible();
  await expect(page).toHaveURL("/?company=Acme+Labs");
  await expect(other).toHaveURL("/?company=Acme+Labs");
  await other.evaluate(() => localStorage.clear());
  await expect(page.getByRole("button", {name: `Save ${role} at Acme Labs`})).toHaveAttribute(
    "aria-pressed",
    "false"
  );
  await expect(page.getByRole("button", {name: "View 0 applied opportunities"})).toBeVisible();
  // Clearing preferences is private too; include it in the network and URL checks.
  expect(requests).toEqual([]);
  await expect(page).toHaveURL("/?company=Acme+Labs");
  await expect(other).toHaveURL("/?company=Acme+Labs");
  await other.close();
});

test("quota failures retain consecutive in-memory actions instead of stale stored state", async ({
  page,
}) => {
  await openDirectory(page, "/?company=Acme+Labs");
  // Keep reads working with the old stored state; only subsequent writes fail.
  await page.evaluate(() => {
    Storage.prototype.setItem = () => {
      throw new DOMException("full", "QuotaExceededError");
    };
  });
  await page.getByRole("button", {name: `Save ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: `Mark applied ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: "View 1 saved opportunities"}).click();
  await expectResultCount(page, 1);
  await expect(
    page.getByRole("button", {name: `Unmark applied ${role} at Acme Labs`})
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", {name: `Unsave ${role} at Acme Labs`}).click();
  await expectResultCount(page, 0);
  await expect(page.getByRole("button", {name: "View 0 saved opportunities"})).toBeFocused();
});
