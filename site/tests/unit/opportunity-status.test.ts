import {describe, expect, test} from "bun:test";
import {readFileSync} from "node:fs";
import path from "node:path";
import Ajv2020 from "ajv/dist/2020.js";
import {statusPayload, statusResponse} from "@/lib/opportunity-status";

const metadata = {
  schema_version: "v1",
  generated_at: "2026-07-17T12:05:00+00:00",
  total: 2,
  internship_count: 1,
  new_grad_count: 1,
  json_sha256: "a".repeat(64),
  csv_sha256: "b".repeat(64),
};
const summary = {lastUpdatedAt: "2026-07-17 12:00:00.123456", opportunities: 2};
const payload = () => statusPayload(summary, metadata, metadata.json_sha256, "123-1");

describe("production status contract", () => {
  test("publishes only explicit public fields with UTC timestamps and no private metadata", () => {
    expect(
      statusPayload(
        summary,
        {...metadata, private_path: "/private/state"},
        metadata.json_sha256,
        "123-1"
      )
    ).toEqual({
      last_successful_collection: "2026-07-17T12:00:00.123456+00:00",
      dataset_generated_at: "2026-07-17T12:05:00.000000+00:00",
      opportunities: 2,
      dataset_sha256: metadata.json_sha256,
      release: "123-1",
    });
  });

  test("an empty, never-collected legacy dataset is valid but not invented on errors", () => {
    expect(
      statusPayload(
        {lastUpdatedAt: null, opportunities: 0},
        {...metadata, total: 0, internship_count: 0, new_grad_count: 0},
        metadata.json_sha256,
        null
      )
    ).toMatchObject({last_successful_collection: null, opportunities: 0, release: null});
    expect(() => statusPayload(summary, null, metadata.json_sha256, null)).toThrow();
  });

  test.each(["2026-07-17T12:05:00.654321Z", "2026-07-17T12:05:00.654321+00:00"])(
    "preserves generation microseconds from %s independently of collection time",
    (generatedAt) => {
      expect(
        statusPayload(summary, {...metadata, generated_at: generatedAt}, metadata.json_sha256, null)
      ).toMatchObject({
        last_successful_collection: "2026-07-17T12:00:00.123456+00:00",
        dataset_generated_at: "2026-07-17T12:05:00.654321+00:00",
      });
    }
  );

  test.each<[string, unknown]>([
    ["null", null],
    ["array", []],
    ["missing fields", {}],
    ["unsupported version", {...metadata, schema_version: "v2"}],
    ["total differs from SQLite", {...metadata, total: 3}],
    ["string total", {...metadata, total: "2"}],
    ["negative total", {...metadata, total: -1}],
    ["employment counts do not sum to total", {...metadata, internship_count: 0}],
    ["fractional employment count", {...metadata, internship_count: 1.5}],
    ["negative employment count", {...metadata, new_grad_count: -1}],
    ["missing generation time", {...metadata, generated_at: null}],
    ["generation time without a zone", {...metadata, generated_at: "2026-07-17T12:05:00"}],
    ["non-UTC generation time", {...metadata, generated_at: "2026-07-17T14:05:00+02:00"}],
    ["impossible generation date", {...metadata, generated_at: "2026-02-30T12:05:00Z"}],
    ["uppercase JSON hash", {...metadata, json_sha256: "A".repeat(64)}],
    ["malformed JSON hash", {...metadata, json_sha256: "invalid"}],
    ["missing CSV hash", {...metadata, csv_sha256: null}],
  ])("rejects metadata: %s", (_reason, value) => {
    expect(() => statusPayload(summary, value, metadata.json_sha256, "123-1")).toThrow();
  });

  test("rejects a different download hash, invalid database aggregates, and unsafe release IDs", () => {
    expect(() => statusPayload(summary, metadata, "c".repeat(64), "123-1")).toThrow();
    for (const opportunities of [-1, 2.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
      expect(() =>
        statusPayload({...summary, opportunities}, metadata, metadata.json_sha256, null)
      ).toThrow();
    }
    expect(() =>
      statusPayload({...summary, lastUpdatedAt: "invalid"}, metadata, metadata.json_sha256, null)
    ).toThrow();
    for (const release of [
      "",
      "../123-1",
      "/srv/releases/123-1",
      "private-name",
      "123-1\n",
      " 123-1",
      "123-1 ",
    ]) {
      expect(() => statusPayload(summary, metadata, metadata.json_sha256, release)).toThrow();
    }
  });

  test("the shared schema validates status and rejects extra fields or invalid values", () => {
    const contract = JSON.parse(
      readFileSync(path.resolve("../schemas/opportunities-v1.schema.json"), "utf8")
    );
    const validate = new Ajv2020().compile({$ref: "#/$defs/statusResponse", $defs: contract.$defs});
    expect(validate(payload()), JSON.stringify(validate.errors)).toBe(true);
    expect(validate({...payload(), last_successful_collection: null, release: null})).toBe(true);
    for (const value of [
      {...payload(), private_path: "/private/state"},
      {...payload(), release: "/srv/releases/123-1"},
      {...payload(), opportunities: -1},
      {...payload(), dataset_sha256: "invalid"},
      {...payload(), dataset_generated_at: null},
      {...payload(), last_successful_collection: "2026-07-17 12:00:00"},
    ])
      expect(validate(value)).toBe(false);
    for (const field of [
      "last_successful_collection",
      "dataset_generated_at",
      "dataset_sha256",
      "release",
    ] as const) {
      expect(validate({...payload(), [field]: `${payload()[field]}\n`})).toBe(false);
    }
  });
});

describe("status HTTP responses", () => {
  test("always rereads status without caching or conditional 304 responses", async () => {
    let reads = 0;
    const read = async () => ({...payload(), release: `${++reads}-1`});
    for (let count = 1; count <= 2; count++) {
      const response = await statusResponse(
        new Request("https://example.test/api/v1/status", {
          headers: {"If-None-Match": "*"},
        }),
        read
      );
      expect(response.status).toBe(200);
      expect(response.headers.get("cache-control")).toBe("no-store");
      expect(response.headers.get("etag")).toBeNull();
      expect(response.headers.get("access-control-allow-origin")).toBe("*");
      expect(await response.json()).toEqual({...payload(), release: `${count}-1`});
    }
  });

  test.each(["GET", "HEAD"])(
    "sanitizes %s errors and rejects queries before reading state",
    async (method) => {
      let reads = 0;
      const read = async () => {
        reads++;
        throw new Error("/private/database/path: secret configuration");
      };
      const invalid = await statusResponse(
        new Request("https://example.test/api/v1/status?debug=1", {method}),
        read
      );
      expect(invalid.status).toBe(400);
      expect(reads).toBe(0);
      const failure = await statusResponse(
        new Request("https://example.test/api/v1/status", {method}),
        read
      );
      expect(failure.status).toBe(503);
      expect(reads).toBe(1);
      expect(failure.headers.get("cache-control")).toBe("no-store");
      expect(failure.headers.get("access-control-allow-origin")).toBe("*");
      if (method === "HEAD") {
        expect(await invalid.text()).toBe("");
        expect(await failure.text()).toBe("");
      } else {
        expect(await invalid.json()).toEqual({
          version: "v1",
          error: {code: "invalid_query", message: "Status does not accept query parameters"},
        });
        expect(await failure.json()).toEqual({
          version: "v1",
          error: {code: "unavailable", message: "Status unavailable"},
        });
      }
    }
  );
});
