import AxeBuilder from "@axe-core/playwright";
import {expect, test} from "@playwright/test";
import {expectRoleCount, openDirectory} from "./helpers";

const key = "opportunities-directory-state";
const role = "Software Engineering Intern 2027";

test("first and returning visits, corrupt state and stale IDs", async ({page}) => {
  await openDirectory(page);
  await expect(page.getByRole("columnheader").allTextContents()).resolves.toEqual([
    "Listing",
    "Company",
    "New",
    "Role",
    "Category",
    "Industries",
    "Employment type",
    "Location",
    "Start date",
    "First seen",
    "Your list",
  ]);
  await expect(page.getByRole("cell", {name: /Not new since your last visit/})).toHaveCount(10);
  await expect(page.getByText(/new opportunities since your last visit/)).toHaveCount(0);
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
  await expectRoleCount(page, 2);
  await expect(page.getByRole("cell", {name: /New since your last visit/})).toHaveCount(2);
  const newest = page
    .getByRole("row")
    .filter({has: page.getByRole("cell", {name: /New since your last visit/})})
    .first();
  await newest.getByRole("button", {name: /More actions for/}).click();
  await page.getByRole("menuitem", {name: /Hide/}).click();
  await expectRoleCount(page, 1);
  await expect(
    page.getByText("We found 1 new opportunity since your last visit.", {exact: false})
  ).toBeVisible();
  expect(JSON.parse((await page.evaluate((key) => localStorage.getItem(key), key))!).saved).toEqual(
    []
  );
  await page.evaluate((key) => localStorage.setItem(key, "{bad"), key);
  await page.reload();
  await expectRoleCount(page, 12);
  await expect(page.getByText(/new opportunities since your last visit/)).toHaveCount(0);
});

test("download controls move below the directory text under 1090px", async ({page}) => {
  await page.setViewportSize({width: 1085, height: 800});
  await openDirectory(page);
  const summary = await page.getByText(/You have saved/).boundingBox();
  const download = await page.getByRole("link", {name: "Download CSV"}).boundingBox();
  expect(summary).not.toBeNull();
  expect(download).not.toBeNull();
  expect(download!.y).toBeGreaterThan(summary!.y + summary!.height);
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
  await expectRoleCount(page, 1);
  await page.reload();
  await page.getByRole("button", {name: "View 1 applied opportunities"}).click();
  await expect(page.getByRole("link", {name: role, exact: true})).toBeVisible();
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).click();
  await page.getByRole("menuitem", {name: `Hide ${role} at Acme Labs`}).click();
  await expectRoleCount(page, 0);
  await page.getByRole("button", {name: "View 1 hidden opportunities"}).click();
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).click();
  await expect(page.getByRole("menuitem", {name: `Restore ${role} at Acme Labs`})).toBeVisible();
  await page.reload();
  await page.getByRole("button", {name: "View 1 hidden opportunities"}).click();
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).click();
  await page.getByRole("menuitem", {name: `Restore ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: "View 1 saved opportunities"}).click();
  await expectRoleCount(page, 1);
  await expect(page).toHaveURL(/company=Acme\+Labs&sort=company-asc&page-size=20/);
  await page.getByRole("button", {name: `Unmark applied ${role} at Acme Labs`}).click();
  await page.getByRole("button", {name: "View 0 applied opportunities"}).click();
  await expectRoleCount(page, 0);
  await page.getByRole("button", {name: "View all opportunities"}).click();
  await expectRoleCount(page, 2);
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
  await expect(page).toHaveURL(/page=2/);
  await expect(page.getByText("Page 1 of 1")).toBeVisible();
  await page.getByRole("button", {name: "Company"}).click();
  await expect(page).toHaveURL(/sort=company-asc/);
  await expect(page.getByRole("link", {name: role, exact: true})).toBeVisible();
});

test("keyboard actions, menu dismissal and mobile row density", async ({page}) => {
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
  const column = page
    .getByRole("row")
    .filter({has: page.getByRole("link", {name: role, exact: true})})
    .locator("td")
    .last();
  const [columnBox, menuBox] = await Promise.all([column.boundingBox(), menu.boundingBox()]);
  expect(columnBox).not.toBeNull();
  expect(menuBox).not.toBeNull();
  expect(
    Math.abs(menuBox!.x + menuBox!.width / 2 - (columnBox!.x + columnBox!.width / 2))
  ).toBeLessThan(2);
  await expect(page.getByRole("menuitem", {name: `Hide ${role} at Acme Labs`})).toBeFocused();
  expect(
    (
      await new AxeBuilder({page})
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"])
        .analyze()
    ).violations
  ).toEqual([]);
  await page.waitForTimeout(200); // Allow the menu's opening scroll to settle.
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
  await page.getByRole("button", {name: `More actions for ${role} at Acme Labs`}).click();
  await page.getByRole("menuitem", {name: `Hide ${role} at Acme Labs`}).click();
  await expectRoleCount(page, 1);
  await page.getByRole("button", {name: "View 1 hidden opportunities"}).click();
  await expectRoleCount(page, 1);
  // The three controls remain in one horizontal line at mobile width.
  const buttons = page
    .getByRole("row")
    .filter({has: page.getByRole("link", {name: role, exact: true})})
    .getByRole("button");
  const bounds = await buttons.evaluateAll((elements) =>
    elements.map((element) => element.getBoundingClientRect().top)
  );
  expect(Math.max(...bounds) - Math.min(...bounds)).toBeLessThan(2);
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
