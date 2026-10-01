import {createHash} from "node:crypto";
import {readFileSync} from "node:fs";
import path from "node:path";
import {expect, test} from "@playwright/test";
import Ajv2020 from "ajv/dist/2020.js";

const endpoint = "/api/v1/status";
const fixture = path.resolve("tests/e2e/.tmp");
const databasePath = path.join(fixture, "opportunities.db");
const sha256 = (bytes: Buffer) => createHash("sha256").update(bytes).digest("hex");
const contract = JSON.parse(
  readFileSync(path.resolve("../schemas/opportunities-v1.schema.json"), "utf8")
);
const validate = new Ajv2020().compile({$ref: "#/$defs/statusResponse", $defs: contract.$defs});

test("status reports the served dataset, not a newer failed collection or a runtime path", async ({
  request,
}) => {
  const databaseBefore = readFileSync(databasePath);
  const response = await request.get(endpoint);
  const metadata = await (await request.get("/dataset-metadata.json")).json();
  const download = await (await request.get("/open-opportunities.json")).body();
  const directory = await (await request.get("/api/v1/opportunities")).json();
  const body = await response.json();
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toBe("application/json; charset=utf-8");
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect(response.headers()["access-control-allow-origin"]).toBe("*");
  expect(response.headers().etag).toBeUndefined();
  expect(validate(body), JSON.stringify(validate.errors)).toBe(true);
  expect(body).toEqual({
    last_successful_collection: "2026-07-17T12:00:00.000000+00:00",
    dataset_generated_at: expect.any(String),
    opportunities: 12,
    dataset_sha256: sha256(download),
    release: null,
  });
  // Compare the export clock, not collection time; the production test covers microseconds.
  expect(Date.parse(body.dataset_generated_at)).toBe(Date.parse(metadata.generated_at));
  expect(body.opportunities).toBe(directory.pagination.total);
  expect(body.opportunities).toBe(metadata.total);
  expect(body.dataset_sha256).toBe(metadata.json_sha256);
  expect(readFileSync(databasePath)).toEqual(databaseBefore);
  const conditional = await request.get(endpoint, {headers: {"If-None-Match": "*"}});
  expect(conditional.status()).toBe(200);
  expect(await conditional.json()).toEqual(body);
});

test("status supports HEAD and CORS but rejects queries and mutation methods", async ({
  request,
}) => {
  const get = await request.get(endpoint);
  const head = await request.head(endpoint);
  expect(head.status()).toBe(200);
  expect(await head.text()).toBe("");
  for (const header of ["content-type", "cache-control", "access-control-allow-origin"]) {
    expect(head.headers()[header]).toBe(get.headers()[header]);
  }
  for (const query of ["?page=1", "?debug=true", "?release=1-1", "?path=..%2Fprivate"]) {
    const response = await request.get(`${endpoint}${query}`);
    expect(response.status()).toBe(400);
    expect(response.headers()["cache-control"]).toBe("no-store");
    expect(validate(await response.json())).toBe(true);
  }
  expect((await request.head(`${endpoint}?debug=1`)).status()).toBe(400);
  for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
    const response = await request.fetch(endpoint, {method, data: "{}"});
    expect(response.status()).toBe(405);
    expect(response.headers().allow).toBe("GET, HEAD, OPTIONS");
    expect(response.headers()["cache-control"]).toBe("no-store");
    expect(await response.text()).toBe("");
  }
  const options = await request.fetch(endpoint, {
    method: "OPTIONS",
    headers: {
      Origin: "https://consumer.example",
      "Access-Control-Request-Method": "GET",
      "Access-Control-Request-Headers": "If-None-Match",
    },
  });
  expect(options.status()).toBe(204);
  expect(options.headers().allow).toBe("GET, HEAD, OPTIONS");
  expect(options.headers()["access-control-allow-origin"]).toBe("*");
  const deniedHeaders: Record<string, string>[] = [
    {"Access-Control-Request-Method": "POST"},
    {"Access-Control-Request-Headers": "Authorization"},
  ];
  for (const headers of deniedHeaders) {
    expect((await request.fetch(endpoint, {method: "OPTIONS", headers})).status()).toBe(403);
  }
});
