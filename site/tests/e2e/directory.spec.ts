import {expect, test} from "@playwright/test";
import {siteConfig} from "@/lib/site-config";
import {expectRoleCount, openDirectory} from "./helpers";

test("downloads sanitized public CSV and JSON exports", async ({page, request}) => {
  await openDirectory(page);

  const csvLink = page.getByRole("link", {name: "Download CSV"});
  const jsonLink = page.getByRole("link", {name: "Download JSON"});
  await expect(csvLink).toHaveAttribute("href", "/open-opportunities.csv");
  await expect(jsonLink).toHaveAttribute("href", "/open-opportunities.json");

  const csvResponse = await request.get("/open-opportunities.csv");
  expect(csvResponse.ok()).toBeTruthy();
  expect(csvResponse.headers()["content-type"]).toContain("text/csv");
  expect(csvResponse.headers()["content-disposition"]).toContain("open-opportunities.csv");
  expect(await csvResponse.text()).toContain(
    "linkedin_job_id,company,title,location,link,category,industries,employment_type,start_date"
  );

  const jsonResponse = await request.get("/open-opportunities.json");
  expect(jsonResponse.ok()).toBeTruthy();
  expect(jsonResponse.headers()["content-type"]).toContain("application/json");
  expect(jsonResponse.headers()["content-disposition"]).toContain("open-opportunities.json");
  const rows = (await jsonResponse.json()) as Record<string, unknown>[];
  expect(rows).toHaveLength(12);
  expect(Object.keys(rows[0])).toEqual([
    "linkedin_job_id",
    "company",
    "title",
    "location",
    "link",
    "category",
    "industries",
    "employment_type",
    "start_date",
  ]);
  expect(rows[0]).not.toHaveProperty("status");
  expect(rows[0]).not.toHaveProperty("first_seen_at");
});

test("filters opportunities and writes shareable URL parameters", async ({page}) => {
  await openDirectory(page);

  await expectRoleCount(page, 12);
  await page.getByLabel("Company").selectOption("Acme Labs");

  await expect(page).toHaveURL(/company=Acme\+Labs/);
  await expectRoleCount(page, 2);
  await expect(
    page.getByRole("link", {name: "Graduate Data Analyst 2027", exact: true})
  ).toHaveCount(0);

  await page.getByLabel("Category").selectOption("cybersecurity");
  await expect(page).toHaveURL(/category=cybersecurity/);
  await expectRoleCount(page, 1);
  await expect(
    page.getByRole("link", {name: "Cybersecurity Intern 2027", exact: true})
  ).toBeVisible();
});

test("filters one employment type at a time", async ({page}) => {
  await openDirectory(page);

  await page.getByLabel("Employment type").selectOption("new-grad");
  await expect(page).toHaveURL(/type=new-grad/);
  await expectRoleCount(page, 1);
  await expect(
    page.getByRole("link", {name: "Graduate Data Analyst 2027", exact: true})
  ).toBeVisible();

  await page.getByLabel("Employment type").selectOption("internship");
  await expect(page).toHaveURL(/type=internship/);
  await expect(page).not.toHaveURL(/new-grad/);
  await expectRoleCount(page, 11);
});

test("filters opportunities by when they were first seen", async ({page}) => {
  await openDirectory(page);

  const firstSeen = page.getByLabel("First seen");
  await firstSeen.selectOption("24-hours");
  await expect(page).toHaveURL(/first-seen=24-hours/);
  await expectRoleCount(page, 2);

  await firstSeen.selectOption("7-days");
  await expect(page).toHaveURL(/first-seen=7-days/);
  await expectRoleCount(page, 7);

  await firstSeen.selectOption("30-days");
  await expect(page).toHaveURL(/first-seen=30-days/);
  await expectRoleCount(page, 11);

  await page.getByRole("button", {name: "Reset"}).click();
  await expect(firstSeen).toHaveValue("all");
  await expect(page).not.toHaveURL(/first-seen=/);
  await expectRoleCount(page, 12);
});

test("restores filters from a shared URL and browser history", async ({page}) => {
  await openDirectory(page, "/?q=analyst&country=France&type=new-grad&first-seen=30-days");

  await expect(page.getByLabel("Search")).toHaveValue("analyst");
  await expect(page.getByLabel("Location")).toHaveValue("France");
  await expect(page.getByLabel("Employment type")).toHaveValue("new-grad");
  await expect(page.getByLabel("First seen")).toHaveValue("30-days");
  await expectRoleCount(page, 1);
  await expect(
    page.getByRole("link", {name: "Graduate Data Analyst 2027", exact: true})
  ).toBeVisible();

  await page.getByLabel("Location").selectOption("Germany");
  await expectRoleCount(page, 0);
  await page.goBack();
  await expect(page.getByLabel("Location")).toHaveValue("France");
  await expectRoleCount(page, 1);
});

test("restores sorting, page, and page size from a shared URL", async ({page}) => {
  await openDirectory(page, "/?q=intern&sort=company-asc&page=2&page-size=10");

  await expect(page.getByLabel("Search")).toHaveValue("intern");
  await expectRoleCount(page, 11);
  await expect(page.getByRole("columnheader", {name: "Company"})).toHaveAttribute(
    "aria-sort",
    "ascending"
  );
  await expect(page.getByLabel("Rows per page")).toHaveValue("10");
  await expect(page.getByText("Page 2 of 2")).toBeVisible();
  await expect(page.locator("tbody tr").first().locator("td").nth(1)).toHaveText("Example 09");

  await page.getByRole("link", {name: "Previous page"}).click();
  await expect(page).not.toHaveURL(/(?:\?|&)page=2(?:&|$)/);
  await page.goBack();
  await expect(page.getByText("Page 2 of 2")).toBeVisible();

  await page.getByRole("columnheader", {name: "Location"}).getByRole("button").click();
  await expect(page).toHaveURL(/sort=location-asc/);
  await expect(page).not.toHaveURL(/(?:\?|&)page=2(?:&|$)/);
  await expect(page.getByText("Page 1 of 2")).toBeVisible();
});

test("falls back safely for unsupported directory view parameters", async ({page}) => {
  await openDirectory(page, "/?first-seen=tomorrow&sort=unsupported&page=-2&page-size=11");

  await expect(page.getByLabel("First seen")).toHaveValue("all");
  await expect(page.getByRole("columnheader", {name: "First seen"})).toHaveAttribute(
    "aria-sort",
    "descending"
  );
  await expect(page.getByLabel("Rows per page")).toHaveValue("10");
  await expect(page.getByText("Page 1 of 2")).toBeVisible();
});

test("search, reset, keyboard focus, and sorting remain interactive", async ({page}) => {
  await openDirectory(page, "/?source=e2e&sort=company-desc&page-size=20");

  await page.keyboard.press("Control+k");
  await expect(page.getByLabel("Search")).toBeFocused();
  await page.getByLabel("Search").fill("acme");
  await expect(page).toHaveURL(/q=acme/);
  await expectRoleCount(page, 2);

  await page.getByRole("button", {name: "Reset"}).click();
  await expect(page).toHaveURL("/?source=e2e&sort=company-desc&page-size=20");
  await expectRoleCount(page, 12);

  const companyHeader = page.getByRole("columnheader", {name: "Company"});
  await companyHeader.getByRole("button").click();
  await expect(companyHeader).toHaveAttribute("aria-sort", "ascending");
  await expect(page).toHaveURL(/sort=company-asc/);
  await companyHeader.getByRole("button").click();
  await expect(companyHeader).toHaveAttribute("aria-sort", "descending");
  await expect(page).toHaveURL(/sort=company-desc/);
  const firstCompanyCell = page.locator("tbody tr").first().locator("td").nth(1);
  await expect(firstCompanyCell).toHaveText("Northstar Data");
});

test("defaults to latest first seen and paginates results", async ({page}) => {
  await openDirectory(page);

  const firstSeenHeader = page.getByRole("columnheader", {name: "First seen"});
  await expect(firstSeenHeader).toHaveAttribute("aria-sort", "descending");
  await expect(
    page
      .locator("tbody tr")
      .first()
      .getByRole("link", {name: "Platform Engineering Intern 9", exact: true})
  ).toBeVisible();

  await expect(page.getByText("Page 1 of 2")).toBeVisible();
  await expect(
    page.getByRole("link", {name: "Software Engineering Intern 2027", exact: true})
  ).toHaveCount(0);
  await page.getByRole("link", {name: "Next page"}).click();
  await expect(page).toHaveURL(/page=2/);
  await expect(page.getByText("Page 2 of 2")).toBeVisible();
  await expect(
    page.getByRole("link", {name: "Software Engineering Intern 2027", exact: true})
  ).toBeVisible();

  await page.getByLabel("Rows per page").selectOption("20");
  await expect(page).toHaveURL(/page-size=20/);
  await expect(page).not.toHaveURL(/(?:\?|&)page=2(?:&|$)/);
  await expect(page.getByText("Page 1 of 1")).toBeVisible();

  await page.getByRole("button", {name: "Toggle color theme"}).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("opportunities-theme")))
    .toBe("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("keeps directory controls usable at a mobile viewport", async ({page}) => {
  await page.setViewportSize({width: 390, height: 844});
  await openDirectory(page);

  await expect(page.getByRole("heading", {name: "Opportunity directory"})).toBeVisible();
  await expect(page.getByRole("search", {name: "Opportunity filters"})).toBeVisible();
  const csvLink = page.getByRole("link", {name: "Download CSV"});
  const jsonLink = page.getByRole("link", {name: "Download JSON"});
  await expect(csvLink).toBeVisible();
  await expect(jsonLink).toBeVisible();
  expect(
    await csvLink.evaluate((element) =>
      element instanceof HTMLElement ? element.innerText.trim() : ""
    )
  ).toBe("CSV");
  expect(
    await jsonLink.evaluate((element) =>
      element instanceof HTMLElement ? element.innerText.trim() : ""
    )
  ).toBe("JSON");
  const exportAndCountRow = csvLink.locator("..");
  expect(
    await exportAndCountRow.evaluate((element) => {
      const tops = Array.from(element.children, (child) => child.getBoundingClientRect().top);
      return Math.max(...tops) - Math.min(...tops);
    })
  ).toBeLessThan(1);
  await expect(page.getByRole("button", {name: "Toggle color theme"})).toBeVisible();

  const table = page.getByRole("table", {name: "Open opportunities"});
  await expect(table).toBeVisible();
  expect(
    await table.locator("..").evaluate((element) => element.scrollWidth > element.clientWidth)
  ).toBe(true);

  await page.getByLabel("Search").fill("analyst");
  await expectRoleCount(page, 1);
});

test("publishes canonical SEO and crawler metadata", async ({page, request}) => {
  await openDirectory(page, "/?company=Acme+Labs");

  await expect(page).toHaveTitle(siteConfig.name);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute(
    "content",
    siteConfig.description
  );
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "http://127.0.0.1:3100"
  );
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex, follow/);
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute(
    "content",
    /opengraph-image/
  );
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute(
    "content",
    "summary_large_image"
  );
  await expect(page.locator('meta[name="author"]')).toHaveAttribute(
    "content",
    siteConfig.maintainer.name
  );
  await expect(page.locator('script[src="https://cloud.umami.is/script.js"]')).toHaveCount(0);
  await expect(page.getByText("Last successful collection: 17 Jul 2026")).toBeVisible();

  const jsonLd = await page.locator('script[type="application/ld+json"]').textContent();
  expect(jsonLd).not.toBeNull();
  expect(jsonLd).not.toContain("JobPosting");
  const structuredData = JSON.parse(jsonLd!) as {
    "@graph": Array<Record<string, unknown>>;
  };
  const dataset = structuredData["@graph"].find((item) => item["@type"] === "Dataset");
  expect(dataset).toMatchObject({
    "@id": "http://127.0.0.1:3100/#dataset",
    dateModified: "2026-07-17T12:00:00+00:00",
    distribution: [
      {contentUrl: "http://127.0.0.1:3100/open-opportunities.csv"},
      {contentUrl: "http://127.0.0.1:3100/open-opportunities.json"},
    ],
  });

  const openGraphImage = await request.get("/opengraph-image");
  expect(openGraphImage.ok()).toBeTruthy();
  expect(openGraphImage.headers()["content-type"]).toContain("image/png");

  const manifestResponse = await request.get("/manifest.webmanifest");
  expect(manifestResponse.ok()).toBeTruthy();
  expect(await manifestResponse.json()).toMatchObject({
    id: "/",
    scope: "/",
    start_url: "/",
    name: siteConfig.name,
    short_name: siteConfig.shortName,
    description: siteConfig.description,
    lang: siteConfig.language,
    dir: "ltr",
  });

  const robots = await request.get("/robots.txt");
  expect(robots.ok()).toBeTruthy();
  expect(await robots.text()).toContain("Sitemap: http://127.0.0.1:3100/sitemap.xml");

  const sitemap = await request.get("/sitemap.xml");
  expect(sitemap.ok()).toBeTruthy();
  expect(await sitemap.text()).toContain("<loc>http://127.0.0.1:3100/</loc>");
});

test("crawler can follow unfiltered pages without JavaScript", async ({browser}) => {
  const context = await browser.newContext({javaScriptEnabled: false});
  try {
    const page = await context.newPage();
    await page.goto("/");

    const nextPage = page.getByRole("link", {name: "Next page"});
    await expect(nextPage).toHaveAttribute("href", "/?page=2");
    await nextPage.click();

    await expect(page).toHaveURL("/?page=2");
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
      "href",
      "http://127.0.0.1:3100/?page=2"
    );
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "index, follow");
    await expect(
      page.getByRole("link", {name: "Software Engineering Intern 2027", exact: true})
    ).toBeVisible();
    await expect(page.getByRole("link", {name: "Previous page"})).toHaveAttribute("href", "/");
  } finally {
    await context.close();
  }
});

test("does not index out-of-range or alternate directory pages", async ({page}) => {
  await openDirectory(page, "/?page=999");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "http://127.0.0.1:3100"
  );
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex, follow/);

  await openDirectory(page, "/?page=2&sort=company-asc");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "http://127.0.0.1:3100"
  );
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex, follow/);

  await openDirectory(page, "/?source=e2e&page=2");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "http://127.0.0.1:3100/?page=2"
  );
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "index, follow");
});
