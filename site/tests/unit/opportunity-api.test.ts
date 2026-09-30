import {describe, expect, test} from "bun:test";
import fc from "fast-check";
import {apiEtag, apiPayload, matchesIfNoneMatch, parseApiQuery} from "@/lib/opportunity-api";
import type {Opportunity} from "@/types/opportunity";

const row = (id: string, fields: Partial<Opportunity> = {}): Opportunity => ({
  linkedinJobId: id,
  company: "Acme",
  title: "Intern 2027",
  location: "Berlin, Germany; Paris, France",
  link: `https://www.linkedin.com/jobs/view/${id}`,
  category: "software-engineering",
  industries: null,
  employmentType: "internship",
  startDate: null,
  firstSeenAt: "2026-07-17T12:00:00+00:00",
  ...fields,
});
const rows = [row("100"), row("101"), row("102", {company: "Other", employmentType: "new-grad"})];
const payload = (search = "", items = rows) =>
  apiPayload(items, "2026-07-17T12:00:00+00:00", parseApiQuery(search));

describe("public API contract", () => {
  test("filters combined search and exact country/company/category/type and snapshot recency", () => {
    const result = payload(
      "?q=intern&country=France&company=Acme&category=software-engineering&type=internship&first-seen=24-hours"
    );
    expect(result.pagination.total).toBe(2);
    expect(result.data.map((item) => item.linkedinJobId)).toEqual(["101", "100"]);
    expect(payload("?country=Spain").data).toEqual([]);
    expect(payload("?q=NEW-GRAD").pagination.total).toBe(1);
    expect(payload("?q=+NEW-GRAD+").data).toEqual(payload("?q=new-grad").data);
    expect(
      payload("?first-seen=24-hours", [row("1", {firstSeenAt: "2026-07-16T11:59:59Z"})]).pagination
        .total
    ).toBe(0);
  });

  test("equivalent parameter order and default pagination serialize identically with the same ETag", () => {
    const queries = [
      "",
      "?page=1&page-size=10&sort=first-seen-desc",
      "?sort=first-seen-desc&page-size=10&page=1",
    ];
    const representations = queries.map((query) => JSON.stringify(payload(query)));
    const etags = representations.map(apiEtag);

    expect(representations[1]).toBe(representations[0]);
    expect(representations[2]).toBe(representations[0]);
    expect(etags[1]).toBe(etags[0]);
    expect(etags[2]).toBe(etags[0]);

    const reorderedQueries = [
      "?q=intern&country=Germany&category=software-engineering&type=internship&sort=company-asc",
      "?sort=company-asc&type=internship&category=software-engineering&country=Germany&q=intern",
    ];
    const reorderedRepresentations = reorderedQueries.map((query) =>
      JSON.stringify(payload(query))
    );
    expect(reorderedRepresentations[1]).toBe(reorderedRepresentations[0]);
    expect(apiEtag(reorderedRepresentations[1])).toBe(apiEtag(reorderedRepresentations[0]));
  });

  test("stable sorting, numeric ID ties, bounded pagination and empty/out-of-range pages", () => {
    expect(payload("?sort=company-asc&page-size=1&page=2").data[0].linkedinJobId).toBe("100");
    expect(payload("?sort=first-seen-asc").data.map((item) => item.linkedinJobId)).toEqual([
      "102",
      "101",
      "100",
    ]);
    expect(payload("?page=99").pagination).toEqual({
      page: 99,
      pageSize: 10,
      total: 3,
      totalPages: 1,
    });
    expect(payload("?page=99").data).toEqual([]);
    expect(payload("", []).pagination).toEqual({page: 1, pageSize: 10, total: 0, totalPages: 0});
    expect(payload("", []).data).toEqual([]);
    expect(payload("?sort=role-desc").data.map((item) => item.linkedinJobId)).toEqual([
      "102",
      "101",
      "100",
    ]);
  });

  test("orders distinct microseconds chronologically before applying numeric ID ties", () => {
    const items = [
      row("9", {firstSeenAt: "2026-07-17T12:00:00.123456Z"}),
      row("10", {firstSeenAt: "2026-07-17 12:00:00.123456"}),
      row("11", {firstSeenAt: "2026-07-17T14:00:00.123457+02:00"}),
      row("12", {firstSeenAt: "2026-07-17T12:00:00.123455+00:00"}),
    ];
    expect(payload("", items).data.map((item) => item.linkedinJobId)).toEqual([
      "11",
      "10",
      "9",
      "12",
    ]);
    expect(payload("?sort=first-seen-asc", items).data.map((item) => item.linkedinJobId)).toEqual([
      "12",
      "10",
      "9",
      "11",
    ]);
    expect(items.map((item) => item.linkedinJobId)).toEqual(["9", "10", "11", "12"]);
  });

  test("publishes UTC RFC 3339 first-seen timestamps without losing microseconds", () => {
    const examples = [
      ["2026-07-17 12:00:00.123456", "2026-07-17T12:00:00.123456+00:00"],
      ["2026-07-17T12:00:00Z", "2026-07-17T12:00:00.000000+00:00"],
      ["2026-07-17T14:00:00.123456+02:00", "2026-07-17T12:00:00.123456+00:00"],
    ] as const;
    for (const [stored, published] of examples) {
      expect(payload("", [row("100", {firstSeenAt: stored})]).data[0].firstSeenAt).toBe(published);
    }
    expect(
      payload("", [row("100", {firstSeenAt: "2026-07-17T12:00:00.1Z"})]).data[0].firstSeenAt
    ).toBe("2026-07-17T12:00:00.100000+00:00");
    expect(() => payload("", [row("100", {firstSeenAt: "not a date"})])).toThrow();
  });

  test("rejects impossible first-seen calendar and time values", () => {
    const invalidTimestamps = [
      "2026-00-17T12:00:00Z",
      "2026-13-17T12:00:00Z",
      "2026-02-29T12:00:00Z",
      "2026-02-31T12:00:00Z",
      "2026-04-31T12:00:00Z",
      "2026-07-17T24:00:00Z",
      "2026-07-17T12:60:00Z",
      "2026-07-17T12:00:60Z",
    ];
    for (const firstSeenAt of invalidTimestamps) {
      expect(() => payload("", [row("100", {firstSeenAt})])).toThrow(
        "Invalid first-seen timestamp"
      );
    }
  });

  test("invalid snapshot timestamps cannot turn recency results into a successful empty list", () => {
    const query = "?sort=company-asc&first-seen=7-days";
    expect(() => payload(query, [row("1", {firstSeenAt: "2026-02-30 12:00:00"})])).toThrow(
      "Invalid first-seen timestamp"
    );
    expect(() => apiPayload(rows, "invalid", parseApiQuery(query))).toThrow(
      "Invalid collection timestamp"
    );
  });

  test("stable explicit public field allowlist", () => {
    expect(Object.keys(payload().data[0])).toEqual([
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
    expect(Object.keys(payload())).toEqual(["version", "pagination", "data"]);
    expect(payload().version).toBe("v1");
    expect(JSON.stringify(payload())).not.toMatch(/status|provenance|search_runs|diagnostics/);
    const extraFieldRow = {...row("103"), status: "open", internalPath: "private"};
    expect(Object.keys(payload("", [extraFieldRow]).data[0])).toEqual(
      Object.keys(payload().data[0])
    );
    expect(JSON.stringify(payload("", [extraFieldRow]))).not.toContain("internalPath");
  });

  test("bounded property fuzzing preserves encoded queries and rejects duplicate keys", () => {
    const queryText = fc
      .array(fc.constantFrom("a", "Z", "0", " ", "&", "=", "%", "+", "-", "_"), {
        maxLength: 200,
      })
      .map((characters) => characters.join(""));

    fc.assert(
      fc.property(
        queryText,
        fc.integer({min: 1, max: 10000}),
        fc.integer({min: 1, max: 100}),
        (q, page, pageSize) => {
          const params = new URLSearchParams({
            q,
            page: String(page),
            "page-size": String(pageSize),
          });
          const parsed = parseApiQuery(`?${params}`);
          expect(parsed.filters.q).toBe(q);
          expect(parsed.page).toBe(page);
          expect(parsed.pageSize).toBe(pageSize);

          const reversed = new URLSearchParams([...params].reverse());
          expect(JSON.stringify(payload(`?${params}`))).toBe(
            JSON.stringify(payload(`?${reversed}`))
          );
          expect(() => parseApiQuery(`?${params}&q=duplicate`)).toThrow();
        }
      ),
      {seed: 2027, numRuns: 150}
    );
  });

  test("rejects malformed, duplicate, unknown and excessive input", () => {
    for (const search of [
      "?company=",
      "?country=",
      "?category=",
      "?company=+Acme+",
      "?type=contract",
      "?type=",
      "?sort=",
      "?first-seen=",
      "?first-seen=all",
      "?sort=title-asc",
      "?page=0",
      "?page=-1",
      "?page=1.2",
      "?page=10001",
      "?page-size=101",
      "?page-size=1e2",
      "?page=1&page=2",
      "?unknown=1",
      "?q=%00",
      "?q=%ZZ",
      `?q=${"x".repeat(201)}`,
    ])
      expect(() => parseApiQuery(search)).toThrow();
    expect(parseApiQuery("?page=10000&page-size=100").pageSize).toBe(100);
  });

  test("body-derived ETags and weak/list conditional matching", () => {
    const tag = apiEtag(JSON.stringify(payload()));
    expect(tag).toBe(apiEtag(JSON.stringify(payload())));
    expect(tag).not.toBe(apiEtag(JSON.stringify(payload("?page=2"))));
    expect(matchesIfNoneMatch(`"other", W/${tag}`, tag)).toBe(true);
    expect(matchesIfNoneMatch("*", tag)).toBe(true);
    expect(matchesIfNoneMatch('"different"', tag)).toBe(false);
    expect(matchesIfNoneMatch(null, tag)).toBe(false);
  });
});
