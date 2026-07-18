import {expect, test, type Page} from "@playwright/test";

async function expectRoleCount(page: Page, count: number) {
  const label = count === 1 ? "role" : "roles";
  await expect(page.locator(".directory-count")).toHaveText(
    new RegExp(`${count}\\s*open ${label}`)
  );
}

test("filters opportunities and writes shareable URL parameters", async ({page}) => {
  await page.goto("/");

  await expectRoleCount(page, 12);
  await page.getByLabel("Company").selectOption("Acme Labs");

  await expect(page).toHaveURL(/company=Acme\+Labs/);
  await expectRoleCount(page, 2);
  await expect(page.getByRole("link", {name: "Graduate Data Analyst 2027"})).toHaveCount(0);

  await page.getByLabel("Category").selectOption("cybersecurity");
  await expect(page).toHaveURL(/category=cybersecurity/);
  await expectRoleCount(page, 1);
  await expect(page.getByRole("link", {name: "Cybersecurity Intern 2027"})).toBeVisible();
});

test("filters one employment type at a time", async ({page}) => {
  await page.goto("/");

  await page.getByLabel("Employment type").selectOption("new-grad");
  await expect(page).toHaveURL(/type=new-grad/);
  await expectRoleCount(page, 1);
  await expect(page.getByRole("link", {name: "Graduate Data Analyst 2027"})).toBeVisible();

  await page.getByLabel("Employment type").selectOption("internship");
  await expect(page).toHaveURL(/type=internship/);
  await expect(page).not.toHaveURL(/new-grad/);
  await expectRoleCount(page, 11);
});

test("restores filters from a shared URL and browser history", async ({page}) => {
  await page.goto("/?q=analyst&country=France&type=new-grad");

  await expect(page.getByLabel("Search")).toHaveValue("analyst");
  await expect(page.getByLabel("Location")).toHaveValue("France");
  await expect(page.getByLabel("Employment type")).toHaveValue("new-grad");
  await expectRoleCount(page, 1);
  await expect(page.getByRole("link", {name: "Graduate Data Analyst 2027"})).toBeVisible();

  await page.getByLabel("Location").selectOption("Germany");
  await expectRoleCount(page, 0);
  await page.goBack();
  await expect(page.getByLabel("Location")).toHaveValue("France");
  await expectRoleCount(page, 1);
});

test("search, reset, keyboard focus, and sorting remain interactive", async ({page}) => {
  await page.goto("/?source=e2e");

  await page.keyboard.press("Control+k");
  await expect(page.getByLabel("Search")).toBeFocused();
  await page.getByLabel("Search").fill("acme");
  await expect(page).toHaveURL(/q=acme/);
  await expectRoleCount(page, 2);

  await page.getByRole("button", {name: "Reset"}).click();
  await expect(page).toHaveURL("/?source=e2e");
  await expectRoleCount(page, 12);

  await page.getByRole("button", {name: "Company"}).click();
  await page.getByRole("button", {name: "Company"}).click();
  const firstCompanyCell = page.locator("tbody tr").first().locator("td").nth(1);
  await expect(firstCompanyCell).toHaveText("Northstar Data");
});

test("paginates results and persists the selected theme", async ({page}) => {
  await page.goto("/");

  await expect(page.getByText("Page 1 of 2")).toBeVisible();
  await expect(page.getByRole("link", {name: "Graduate Data Analyst 2027"})).toHaveCount(0);
  await page.getByRole("button", {name: "Next page"}).click();
  await expect(page.getByText("Page 2 of 2")).toBeVisible();
  await expect(page.getByRole("link", {name: "Graduate Data Analyst 2027"})).toBeVisible();

  await page.getByRole("button", {name: "Toggle color theme"}).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("internships-theme")))
    .toBe("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("publishes canonical SEO and crawler metadata", async ({page, request}) => {
  await page.goto("/?company=Acme+Labs");

  await expect(page).toHaveTitle("European Tech Internships 2027");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "http://127.0.0.1:3100"
  );
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute(
    "content",
    /opengraph-image/
  );
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute(
    "content",
    "summary_large_image"
  );
  await expect(page.locator('meta[name="author"]')).toHaveAttribute("content", "Simone Siega");

  const manifestResponse = await request.get("/manifest.webmanifest");
  expect(manifestResponse.ok()).toBeTruthy();
  expect(await manifestResponse.json()).toMatchObject({
    id: "/",
    scope: "/",
    start_url: "/",
    name: "European Tech Internships 2027",
    short_name: "Internships ’27",
    lang: "en-GB",
    dir: "ltr",
  });

  const robots = await request.get("/robots.txt");
  expect(robots.ok()).toBeTruthy();
  expect(await robots.text()).toContain("Sitemap: http://127.0.0.1:3100/sitemap.xml");

  const sitemap = await request.get("/sitemap.xml");
  expect(sitemap.ok()).toBeTruthy();
  expect(await sitemap.text()).toContain("<loc>http://127.0.0.1:3100/</loc>");
});
