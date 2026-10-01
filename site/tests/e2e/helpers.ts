import {expect, type Page} from "@playwright/test";

export async function openDirectory(page: Page, url = "/") {
  await page.goto(url);
  // Server HTML appears before hydration; wait for the directory's interactive state.
  await expect(page.getByRole("region", {name: "Opportunity directory"})).toHaveAttribute(
    "aria-busy",
    "false"
  );
}

export async function expectRoleCount(page: Page, count: number) {
  const label = count === 1 ? "role" : "roles";
  await expect(page.getByRole("status")).toHaveText(new RegExp(`${count}\\s*open ${label}`));
}
