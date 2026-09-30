import AxeBuilder from "@axe-core/playwright";
import {expect, test, type Page} from "@playwright/test";
import {expectRoleCount, openDirectory} from "./helpers";

const wcagTags = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"];

async function expectNoAccessibilityViolations(page: Page) {
  const results = await new AxeBuilder({page}).withTags(wcagTags).analyze();
  expect(results.violations).toEqual([]);
}

test.describe("automated accessibility", () => {
  test("normal directory", async ({page}) => {
    await openDirectory(page);
    await expectNoAccessibilityViolations(page);
  });

  test("filtered directory", async ({page}) => {
    await openDirectory(page, "/?company=Acme+Labs&category=cybersecurity");
    await expectRoleCount(page, 1);
    await expectNoAccessibilityViolations(page);
  });

  test("empty results", async ({page}) => {
    await openDirectory(page, "/?q=does-not-match-any-opportunity");
    await expectRoleCount(page, 0);
    await expectNoAccessibilityViolations(page);
    await page.getByRole("button", {name: "Reset filters"}).click();
    await expectRoleCount(page, 12);
    await expect(page.getByLabel("Search")).toHaveValue("");
    await expect(page).not.toHaveURL(/q=/);
  });

  test("dark mode", async ({page}) => {
    await openDirectory(page);
    await page.getByRole("button", {name: "Toggle color theme"}).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expectNoAccessibilityViolations(page);
  });
});
