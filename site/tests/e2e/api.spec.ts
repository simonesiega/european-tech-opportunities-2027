import {readFileSync} from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import {expect, test} from "@playwright/test";

const endpoint = "/api/v1/opportunities";
const contract = JSON.parse(
  readFileSync(path.resolve("../schemas/opportunities-v1.schema.json"), "utf8")
);
const ajv = new Ajv2020();
const validateApi = ajv.compile({$ref: "#/$defs/apiResponse", $defs: contract.$defs});
const validateDownload = ajv.compile(contract);

test("serves the exact repository v1 schema at its canonical product URL", async ({request}) => {
  const response = await request.get("/schemas/opportunities-v1.schema.json");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toContain("application/schema+json");
  expect(await response.body()).toEqual(
    readFileSync(path.resolve("../schemas/opportunities-v1.schema.json"))
  );
  expect((await response.json()).$id).toBe(
    "https://techopportunities.eu/schemas/opportunities-v1.schema.json"
  );
});

test("v1 schema rejects private API fields and invalid envelopes", () => {
  expect(
    validateApi({version: "v1", error: {code: "unavailable", message: "Directory unavailable"}})
  ).toBe(true);
  expect(
    validateApi({
      version: "v1",
      error: {code: "invalid_query", message: "Invalid query", privatePath: "/tmp/db"},
    })
  ).toBe(false);
  expect(
    validateApi({
      version: "v1",
      pagination: {page: 0, pageSize: 10, total: 0, totalPages: 0},
      data: [],
    })
  ).toBe(false);
  expect(validateDownload([{company: "incomplete"}])).toBe(false);
});

test("read-only API serves canonical rows with stable schema, filtering and pagination", async ({
  request,
}) => {
  const response = await request.get(endpoint);
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toBe("application/json; charset=utf-8");
  expect(response.headers()["access-control-allow-origin"]).toBe("*");
  expect(response.headers()["access-control-expose-headers"]).toBe("ETag, Cache-Control");
  const body = await response.json();
  expect(validateApi(body), JSON.stringify(validateApi.errors)).toBe(true);
  expect(body.data[0].firstSeenAt).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$/);
  expect(
    validateApi({
      ...body,
      data: [{...body.data[0], firstSeenAt: "2026-07-17 12:00:00.000000"}],
    })
  ).toBe(false);
  for (const noncanonical of [
    "2026-07-17T12:00:00",
    "2026-07-17T12:00:00Z",
    "2026-07-17T12:00:00.123+00:00",
  ]) {
    expect(validateApi({...body, data: [{...body.data[0], firstSeenAt: noncanonical}]})).toBe(
      false
    );
  }
  expect(body.version).toBe("v1");
  expect(body.pagination).toEqual({page: 1, pageSize: 10, total: 12, totalPages: 2});
  expect(body.data).toHaveLength(10);
  expect(Object.keys(body.data[0])).toEqual([
    "linkedinJobId",
    "company",
    "title",
    "location",
    "link",
    "category",
    "industries",
    "employmentType",
    "startDate",
    "firstSeenAt",
  ]);
  expect(JSON.stringify(body)).not.toMatch(/status|search_runs|provenance|diagnostics|database/);

  const second = await request.get(`${endpoint}?page=2`);
  expect((await second.json()).data).toHaveLength(2);
  const filtered = await request.get(
    `${endpoint}?country=Ireland&company=Acme+Labs&category=cybersecurity&type=internship&q=cyber&first-seen=30-days&page-size=1`
  );
  const filteredBody = await filtered.json();
  expect(filteredBody.pagination).toEqual({page: 1, pageSize: 1, total: 1, totalPages: 1});
  expect(filteredBody.data[0].linkedinJobId).toBe("1000000002");
  expect((await (await request.get(`${endpoint}?country=Unknown`)).json()).data).toEqual([]);

  const allApiRows = (await (await request.get(`${endpoint}?page-size=100`)).json()).data;
  expect(
    allApiRows.find((row: {linkedinJobId: string}) => row.linkedinJobId === "1000000001")
      ?.firstSeenAt
  ).toMatch(/T.*\+00:00$/);
  const exportRows = await (await request.get("/open-opportunities.json")).json();
  expect(validateDownload(exportRows), JSON.stringify(validateDownload.errors)).toBe(true);
  const byId = (left: {linkedin_job_id: string}, right: {linkedin_job_id: string}) =>
    left.linkedin_job_id.localeCompare(right.linkedin_job_id, "en", {numeric: true});
  expect(
    allApiRows
      .map((row: (typeof allApiRows)[number]) => ({
        linkedin_job_id: row.linkedinJobId,
        company: row.company,
        title: row.title,
        location: row.location,
        link: row.link,
        category: row.category,
        industries: row.industries,
        employment_type: row.employmentType,
        start_date: row.startDate,
      }))
      .sort(byId)
  ).toEqual(exportRows.sort(byId));
});

test("semantically equivalent query strings return identical representations and ETags", async ({
  request,
}) => {
  const equivalentRequests = [
    endpoint,
    `${endpoint}?sort=first-seen-desc&page=1&page-size=10`,
    `${endpoint}?page-size=10&sort=first-seen-desc&page=1`,
  ];
  const responses = await Promise.all(equivalentRequests.map((url) => request.get(url)));
  const bodies = await Promise.all(responses.map((response) => response.body()));
  const etags = responses.map((response) => response.headers().etag);

  expect(bodies[1]).toEqual(bodies[0]);
  expect(bodies[2]).toEqual(bodies[0]);
  expect(etags[1]).toBe(etags[0]);
  expect(etags[2]).toBe(etags[0]);

  const reorderedFilters = await request.get(
    `${endpoint}?q=intern&country=Germany&category=software-engineering&type=internship&sort=company-asc`
  );
  const reorderedEquivalent = await request.get(
    `${endpoint}?sort=company-asc&type=internship&category=software-engineering&country=Germany&q=intern`
  );
  expect(await reorderedEquivalent.body()).toEqual(await reorderedFilters.body());
  expect(reorderedEquivalent.headers().etag).toBe(reorderedFilters.headers().etag);
});

test("ETag revalidation, validation errors, and no mutation endpoints", async ({request}) => {
  const response = await request.get(endpoint);
  const etag = response.headers().etag;
  expect(etag).toMatch(/^"[0-9a-f]{64}"$/);
  expect(response.headers()["cache-control"]).toBe("public, max-age=0, must-revalidate");
  const repeat = await request.get(endpoint, {headers: {"If-None-Match": `W/${etag}`}});
  expect(repeat.status()).toBe(304);
  expect(await repeat.text()).toBe("");
  expect(repeat.headers().etag).toBe(etag);
  expect(repeat.headers()["cache-control"]).toBe("public, max-age=0, must-revalidate");
  expect(repeat.headers()["access-control-allow-origin"]).toBe("*");
  expect((await request.get(`${endpoint}?page=2`)).headers().etag).not.toBe(etag);
  expect((await request.get(`${endpoint}?q=+INTERN+`)).headers().etag).toBe(
    (await request.get(`${endpoint}?q=intern`)).headers().etag
  );
  for (const query of [
    "?page=0",
    "?page-size=101",
    "?sort=oops",
    "?page=1&page=2",
    "?debug=true",
  ]) {
    const invalid = await request.get(`${endpoint}${query}`);
    expect(invalid.status()).toBe(400);
    const errorBody = await invalid.json();
    expect(validateApi(errorBody), JSON.stringify(validateApi.errors)).toBe(true);
    expect(errorBody).toMatchObject({version: "v1", error: {code: "invalid_query"}});
    expect(invalid.headers()["cache-control"]).toBe("no-store");
    expect(invalid.headers()["access-control-allow-origin"]).toBe("*");
  }
  for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
    const rejected = await request.fetch(endpoint, {method, data: "{}"});
    expect(rejected.status()).toBe(405);
    expect(rejected.headers().allow).toBe("GET, HEAD, OPTIONS");
  }
  const head = await request.fetch(endpoint, {method: "HEAD"});
  expect(head.status()).toBe(response.status());
  for (const header of [
    "etag",
    "cache-control",
    "access-control-allow-origin",
    "access-control-expose-headers",
    "content-type",
  ]) {
    expect(head.headers()[header]).toBe(response.headers()[header]);
  }
  expect(await head.text()).toBe("");

  const preflight = await request.fetch(endpoint, {
    method: "OPTIONS",
    headers: {
      Origin: "https://consumer.example",
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": "If-None-Match",
    },
  });
  expect(preflight.status()).toBe(204);
  expect(preflight.headers()["access-control-allow-origin"]).toBe("*");
  expect(preflight.headers()["access-control-allow-methods"]).toBe("GET, HEAD");
  expect(preflight.headers()["access-control-allow-headers"]).toBe("If-None-Match");
  expect(preflight.headers().allow).toBe("GET, HEAD, OPTIONS");
  const deniedPreflight = await request.fetch(endpoint, {
    method: "OPTIONS",
    headers: {"Access-Control-Request-Method": "POST"},
  });
  expect(deniedPreflight.status()).toBe(403);
  expect((await (await request.get(endpoint)).json()).pagination.total).toBe(12);
});
