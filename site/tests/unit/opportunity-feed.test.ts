import {describe, expect, test} from "bun:test";
import {
  FEED_ITEM_LIMIT,
  InvalidFeedQuery,
  parseFeedQuery,
  renderOpportunityFeed,
  xmlEscape,
} from "@/lib/opportunity-feed";
import type {Opportunity} from "@/types/opportunity";

const row = (id: string, fields: Partial<Opportunity> = {}): Opportunity => ({
  linkedinJobId: id,
  company: "Example Labs",
  title: "Software Engineering Intern 2027",
  location: "Dublin, Ireland",
  link: `https://www.linkedin.com/jobs/view/${id}`,
  category: "software-engineering",
  industries: "Software Development",
  employmentType: "internship",
  startDate: "June 2027",
  firstSeenAt: "2026-07-17T12:00:00+00:00",
  ...fields,
});

const origin = new URL("https://techopportunities.eu");
const defaultFilters = {type: "" as const, country: "", category: ""};

describe("public opportunity feeds", () => {
  test("parses only bounded, single type, country, and category filters", () => {
    expect(parseFeedQuery("")).toEqual({type: "", country: "", category: ""});
    expect(
      parseFeedQuery("?type=internship&country=Ireland&category=software-engineering")
    ).toEqual({
      type: "internship",
      country: "Ireland",
      category: "software-engineering",
    });
    expect(parseFeedQuery("?category=software-engineering&country=Ireland&type=new-grad")).toEqual({
      type: "new-grad",
      country: "Ireland",
      category: "software-engineering",
    });

    for (const query of [
      "?type=contract",
      "?type=",
      "?type=internship&type=new-grad",
      "?country=Ireland&country=France",
      "?category=software-engineering&debug=1",
      "?country=+Ireland",
      "?country=%00",
      "?country=%ZZ",
      `?category=${"x".repeat(121)}`,
      `?country=${"x".repeat(1010)}`,
    ]) {
      expect(() => parseFeedQuery(query)).toThrow(InvalidFeedQuery);
    }
  });

  test("filters exact employment type, country, and category with combined AND semantics", () => {
    const rows = [
      row("1"),
      row("2", {category: "cybersecurity", title: "Security Intern 2027"}),
      row("3", {employmentType: "new-grad", title: "Software Engineer New Grad 2027"}),
      row("4", {location: "Berlin, Germany"}),
    ];
    const xml = renderOpportunityFeed(
      "rss",
      rows,
      null,
      {type: "internship", country: "Ireland", category: "software-engineering"},
      origin
    );

    expect(xml.match(/<item>/g)).toHaveLength(1);
    expect(xml).toContain("Software Engineering Intern 2027 — Example Labs");
    expect(xml).not.toContain("Security Intern 2027");
    expect(xml).not.toContain("Software Engineer New Grad 2027");
    expect(xml).not.toContain("Berlin, Germany");
    expect(xml).toContain(
      'href="https://techopportunities.eu/feed.xml?country=Ireland&amp;category=software-engineering&amp;type=internship"'
    );
  });

  test("renders escaped RSS and Atom with listing dates and canonical links", () => {
    const unsafeRow = row("100", {
      company: 'A&B "Labs" <Group>',
      title: "<Engineer & Intern> 2027",
      industries: "Research & Development <R&D>",
    });
    const rss = renderOpportunityFeed("rss", [unsafeRow], null, defaultFilters, origin);
    const atom = renderOpportunityFeed("atom", [unsafeRow], null, defaultFilters, origin);

    expect(rss).toContain('<rss version="2.0"');
    expect(rss).toContain("<pubDate>Fri, 17 Jul 2026 12:00:00 GMT</pubDate>");
    expect(rss).toContain(
      "&lt;Engineer &amp; Intern&gt; 2027 — A&amp;B &quot;Labs&quot; &lt;Group&gt;"
    );
    expect(rss).toContain("Research &amp; Development &lt;R&amp;D&gt;");
    expect(rss).not.toContain("<Engineer");
    expect(atom).toContain('<feed xmlns="http://www.w3.org/2005/Atom">');
    expect(atom).toContain("<id>urn:linkedin:job:100</id>");
    expect(atom).toContain("<published>2026-07-17T12:00:00.000Z</published>");
    expect(atom).toContain("<updated>2026-07-17T12:00:00.000Z</updated>");
    expect(atom).toContain("&lt;Engineer &amp; Intern&gt; 2027");
  });

  test("removes XML-invalid code points and caps results at the newest 50", () => {
    expect(xmlEscape("a\u0000b\ud800c & d")).toBe("abc &amp; d");
    const rows = Array.from({length: FEED_ITEM_LIMIT + 1}, (_, index) =>
      row(String(index + 1), {
        firstSeenAt: new Date(Date.UTC(2026, 6, 31 - index, 12)).toISOString(),
      })
    );
    const xml = renderOpportunityFeed("rss", rows, null, defaultFilters, origin);

    expect(xml.match(/<item>/g)).toHaveLength(FEED_ITEM_LIMIT);
    expect(xml).toContain('<guid isPermaLink="true">https://www.linkedin.com/jobs/view/1</guid>');
    expect(xml).not.toContain("https://www.linkedin.com/jobs/view/51</guid>");
  });

  test("canonicalizes filter order and returns a valid empty feed", () => {
    const filters = parseFeedQuery("?type=new-grad&category=software-engineering&country=Ireland");
    const reorderedFilters = parseFeedQuery(
      "?country=Ireland&category=software-engineering&type=new-grad"
    );
    const xml = renderOpportunityFeed("atom", [], null, filters, origin);
    const reordered = renderOpportunityFeed("atom", [], null, reorderedFilters, origin);

    expect(xml).toBe(reordered);
    expect(xml).toContain("<updated>1970-01-01T00:00:00.000Z</updated>");
    expect(xml).toContain(
      "https://techopportunities.eu/atom.xml?country=Ireland&amp;category=software-engineering&amp;type=new-grad"
    );
    expect(xml).not.toContain("<entry>");
  });

  test("uses the latest successful collection timestamp for empty Atom feeds", () => {
    const xml = renderOpportunityFeed(
      "atom",
      [],
      "2026-07-18T09:30:00+00:00",
      {type: "new-grad", country: "Ireland", category: ""},
      origin
    );

    expect(xml).toContain("<updated>2026-07-18T09:30:00.000Z</updated>");
    expect(xml).toContain("New Grad — Ireland");
  });
});
