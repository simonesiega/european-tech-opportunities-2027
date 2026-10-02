import {expect, type Page} from "@playwright/test";

export async function openDirectory(page: Page, url = "/") {
  await page.goto(url);
  // Server HTML appears before hydration; wait for the directory's interactive state.
  await expect(page.getByRole("region", {name: "Opportunity directory"})).toHaveAttribute(
    "aria-busy",
    "false"
  );
}

export async function expectResultCount(page: Page, count: number) {
  // Public and private filters change results, never the fixture's full open-role total.
  await expect(page.getByRole("status", {name: "Open roles", exact: true})).toHaveText(
    "12 open roles"
  );
  const label = count === 1 ? "result" : "results";
  await expect(page.getByRole("status", {name: "Matching opportunities"})).toHaveText(
    `${count} ${label}`
  );
}
