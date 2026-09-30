import {expect, test} from "@playwright/test";

const countMatches = (content: string, expression: RegExp) =>
  content.match(expression)?.length ?? 0;

test("RSS publishes recent open opportunities as a bounded, cacheable read-only feed", async ({
  request,
}) => {
  const response = await request.get("/feed.xml");
  const xml = await response.text();

  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toBe("application/rss+xml; charset=utf-8");
  expect(response.headers()["cache-control"]).toBe("public, max-age=0, must-revalidate");
  expect(response.headers().etag).toMatch(/^"[0-9a-f]{64}"$/);
  expect(xml).toContain('<rss version="2.0"');
  expect(xml).toContain(`href="${new URL(response.url()).origin}/feed.xml"`);
  expect(xml).toContain("https://www.linkedin.com/jobs/view/1000000001");
  expect(countMatches(xml, /<item>/g)).toBe(12);
  expect(xml).not.toMatch(/search_runs|provenance|diagnostics|database/i);

  const homepage = await request.get("/");
  const html = await homepage.text();
  expect(html).toMatch(
    /rel="alternate"[^>]+type="application\/rss\+xml"[^>]+href="[^"]*feed\.xml"/
  );
  expect(html).toMatch(
    /rel="alternate"[^>]+type="application\/atom\+xml"[^>]+href="[^"]*atom\.xml"/
  );
  expect(html).toContain("RSS feed");
  expect(html).toContain("Atom feed");
});

test("RSS and Atom accept only safe exact filters and return an empty feed for unmatched values", async ({
  request,
}) => {
  const irelandInternships = await request.get(
    "/feed.xml?country=Ireland&category=cybersecurity&type=internship"
  );
  const irelandXml = await irelandInternships.text();
  expect(irelandInternships.status()).toBe(200);
  expect(countMatches(irelandXml, /<item>/g)).toBe(1);
  expect(irelandXml).toContain("1000000002");
  expect(irelandXml).not.toContain("1000000001");
  expect(irelandXml).toContain(
    "feed.xml?country=Ireland&amp;category=cybersecurity&amp;type=internship"
  );

  const newGradFeed = await request.get("/atom.xml?type=new-grad");
  const atomXml = await newGradFeed.text();
  expect(newGradFeed.headers()["content-type"]).toBe("application/atom+xml; charset=utf-8");
  expect(countMatches(atomXml, /<entry>/g)).toBe(1);
  expect(atomXml).toContain("Graduate Data Analyst 2027");
  expect(atomXml).toContain("urn:linkedin:job:1000000003");

  const empty = await request.get("/feed.xml?country=Unknown");
  const emptyXml = await empty.text();
  expect(empty.status()).toBe(200);
  expect(emptyXml).toContain("<channel>");
  expect(emptyXml).not.toContain("<item>");

  for (const query of [
    "?type=contract",
    "?type=internship&type=new-grad",
    "?category=software-engineering&unknown=x",
    "?country=%00",
  ]) {
    const invalid = await request.get(`/feed.xml${query}`);
    expect(invalid.status()).toBe(400);
    expect(invalid.headers()["cache-control"]).toBe("no-store");
    expect(await invalid.text()).toBe("Invalid feed query.\n");
  }
});

test("feed validators support HEAD and conditional GET without mutation methods", async ({
  request,
}) => {
  const response = await request.get("/feed.xml?type=internship");
  const etag = response.headers().etag;
  expect(etag).toMatch(/^"[0-9a-f]{64}"$/);

  const unchanged = await request.get("/feed.xml?type=internship", {
    headers: {"If-None-Match": `W/${etag}`},
  });
  expect(unchanged.status()).toBe(304);
  expect(await unchanged.text()).toBe("");
  expect(unchanged.headers().etag).toBe(etag);

  const head = await request.fetch("/atom.xml", {method: "HEAD"});
  const get = await request.get("/atom.xml");
  expect(head.status()).toBe(200);
  expect(await head.text()).toBe("");
  expect(head.headers()["content-type"]).toBe(get.headers()["content-type"]);
  expect(head.headers().etag).toBe(get.headers().etag);

  for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
    const rejected = await request.fetch("/feed.xml", {method, data: "ignored"});
    expect(rejected.status()).toBe(405);
    expect(rejected.headers().allow).toBe("GET, HEAD");
  }
});
