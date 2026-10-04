import {createHash} from "node:crypto";
import {expect, test} from "@playwright/test";
import {openDirectory} from "./helpers";

test("downloads sanitized exports whose counts and hashes match their metadata", async ({
  request,
}) => {
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
  const publicFields = [
    "linkedin_job_id",
    "company",
    "title",
    "location",
    "link",
    "category",
    "industries",
    "employment_type",
    "start_date",
  ];
  for (const row of rows) expect(Object.keys(row)).toEqual(publicFields);

  const metadataResponse = await request.get("/dataset-metadata.json");
  expect(metadataResponse.ok()).toBeTruthy();
  const metadata = await metadataResponse.json();
  expect(metadata.schema_version).toBe("v1");
  expect(metadata.total).toBe(rows.length);
  expect(metadata.internship_count + metadata.new_grad_count).toBe(rows.length);
  // Hash the served bytes, not reserialized data; formatting is part of artifact integrity.
  expect(metadata.csv_sha256).toBe(
    createHash("sha256")
      .update(await csvResponse.body())
      .digest("hex")
  );
  expect(metadata.json_sha256).toBe(
    createHash("sha256")
      .update(await jsonResponse.body())
      .digest("hex")
  );
});

for (const width of [390, 1085]) {
  test(`CSV and JSON downloads work at ${width}px without horizontal scrolling`, async ({page}) => {
    await page.setViewportSize({width, height: 844});
    await openDirectory(page);
    for (const format of ["CSV", "JSON"]) {
      const link = page.getByRole("link", {name: `Download ${format}`});
      // Check before clicking: Playwright's automatic scrolling could hide clipped controls.
      await expect(link).toBeInViewport({ratio: 1});
      const downloaded = page.waitForEvent("download");
      await link.click();
      const file = await downloaded;
      expect(file.suggestedFilename()).toBe(`open-opportunities.${format.toLowerCase()}`);
      expect(await file.failure()).toBeNull();
    }
  });
}
