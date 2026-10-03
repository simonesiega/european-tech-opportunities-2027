import {describe, expect, test} from "bun:test";
import {
  formatOpportunityDate,
  getCountries,
  normalizeOpportunityTimestamp,
  parseOpportunityTimestamp,
} from "@/lib/opportunity-presentation";

describe("opportunity presentation", () => {
  test("extracts every unique country from a multi-location value", () => {
    expect(getCountries("Madrid, Spain; Lisbon, Portugal; Porto, Portugal")).toEqual([
      "Spain",
      "Portugal",
    ]);
  });

  test.each([
    "2026-02-29 12:00:00",
    "2026-02-30T12:00:00Z",
    "2026-04-31T12:00:00Z",
    "2026-07-17T24:00:00Z",
    "0000-01-01T00:00:00Z",
    "0001-01-01T00:00:00+01:00",
    "9999-12-31T23:59:59-01:00",
    "not a date",
  ])("rejects invalid calendar or out-of-range UTC evidence: %s", (value) => {
    expect(() => normalizeOpportunityTimestamp(value)).toThrow("Invalid opportunity timestamp");
    expect(parseOpportunityTimestamp(value)).toBeNaN();
  });

  test("normalizes valid leap days, UTC offsets and fractional seconds", () => {
    expect(normalizeOpportunityTimestamp("2028-02-29 23:59:59.123456")).toBe(
      "2028-02-29T23:59:59.123456+00:00"
    );
    expect(normalizeOpportunityTimestamp("2026-07-17T00:30:00.1+01:00")).toBe(
      "2026-07-16T23:30:00.100000+00:00"
    );
    expect(parseOpportunityTimestamp("2026-07-17 12:00:00.123456")).toBe(
      Date.parse("2026-07-17T12:00:00.123Z")
    );
  });

  test("formats offset and SQLite timestamps consistently in UTC", () => {
    expect(formatOpportunityDate("2026-07-17T23:30:00-02:00")).toBe("18 Jul 2026");
    expect(formatOpportunityDate("2026-07-17 23:30:00")).toBe("17 Jul 2026");
  });
});
