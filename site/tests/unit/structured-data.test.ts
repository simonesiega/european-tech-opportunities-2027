import {expect, test} from "bun:test";
import {buildStructuredData, serializeStructuredData} from "@/lib/structured-data";

test("does not mark a Dataset as part of its containing WebSite", () => {
  const data = buildStructuredData(new URL("https://techopportunities.eu"), null);
  const website = data["@graph"].find((item) => item["@type"] === "WebSite");
  const dataset = data["@graph"].find((item) => item["@type"] === "Dataset");

  expect(website).toHaveProperty("mainEntity", {"@id": "https://techopportunities.eu/#dataset"});
  expect(dataset).not.toHaveProperty("isPartOf");
});

test.each([
  ["2026-07-17 12:00:00.000000", "2026-07-17T12:00:00.000Z"],
  ["2026-07-17T14:00:00+02:00", "2026-07-17T12:00:00.000Z"],
  [null, undefined],
  ["invalid", undefined],
  ["2026-02-30 12:00:00", undefined],
  ["2026-07-17T24:00:00Z", undefined],
])("publishes a timezone-explicit date or omits invalid evidence: %s", (source, expected) => {
  const data = buildStructuredData(new URL("https://techopportunities.eu"), source);
  const dataset = data["@graph"].find((item) => item["@type"] === "Dataset");
  if (expected) expect(dataset).toHaveProperty("dateModified", expected);
  else expect(dataset).not.toHaveProperty("dateModified");
});

test("escapes markup that could terminate the JSON-LD script", () => {
  const serialized = serializeStructuredData({value: "</script><script>alert(1)</script>"});

  expect(serialized).not.toContain("<");
  expect(JSON.parse(serialized)).toEqual({value: "</script><script>alert(1)</script>"});
});
