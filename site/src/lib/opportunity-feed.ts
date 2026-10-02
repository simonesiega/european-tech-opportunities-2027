import {filterOpportunities} from "@/lib/opportunity-filter";
import {formatCategory, parseOpportunityTimestamp} from "@/lib/opportunity-presentation";
import {siteConfig} from "@/lib/site-config";
import type {Opportunity} from "@/types/opportunity";

export const FEED_ITEM_LIMIT = 50;
const FEED_PARAMETERS = ["type", "country", "category"];
const FEED_TEXT_LIMIT = 120;

export type FeedFormat = "rss" | "atom";
export type FeedFilters = {
  type: "" | Opportunity["employmentType"];
  country: string;
  category: string;
};

export class InvalidFeedQuery extends Error {
  constructor() {
    super("Invalid feed query");
  }
}

export function parseFeedQuery(rawSearch: string): FeedFilters {
  if (rawSearch.length > 1024 || /%(?![0-9a-fA-F]{2})/.test(rawSearch)) {
    throw new InvalidFeedQuery();
  }

  const params = new URLSearchParams(rawSearch);
  for (const [key, value] of params) {
    if (!FEED_PARAMETERS.includes(key)) {
      throw new InvalidFeedQuery();
    }
    if (
      params.getAll(key).length !== 1 ||
      !value ||
      value.length > FEED_TEXT_LIMIT ||
      value !== value.trim() ||
      /[\p{Cc}\uFFFD]/u.test(value)
    ) {
      throw new InvalidFeedQuery();
    }
  }

  const type = params.get("type") ?? "";
  if (type !== "" && type !== "internship" && type !== "new-grad") throw new InvalidFeedQuery();

  return {
    type,
    country: params.get("country") ?? "",
    category: params.get("category") ?? "",
  };
}

export function renderOpportunityFeed(
  format: FeedFormat,
  opportunities: Opportunity[],
  lastUpdatedAt: string | null,
  filters: FeedFilters,
  siteOrigin: URL
): string {
  // The shared database query supplies newest-first rows; filtering preserves that order.
  const matches = filterOpportunities(
    opportunities,
    {
      q: "",
      company: "",
      country: filters.country,
      category: filters.category,
      type: filters.type,
      firstSeen: "",
    },
    0
  ).slice(0, FEED_ITEM_LIMIT);
  const selfUrl = getFeedUrl(format, filters, siteOrigin);
  const homeUrl = new URL("/", siteOrigin).toString();
  const updatedAt = getUpdatedAt(opportunities, lastUpdatedAt);
  const title = getFeedTitle(filters);
  const description = getFeedDescription(filters);

  return format === "rss"
    ? renderRssFeed(matches, selfUrl, homeUrl, updatedAt, title, description)
    : renderAtomFeed(matches, selfUrl, homeUrl, updatedAt.toISOString(), title, description);
}

export function xmlEscape(value: string): string {
  // Escaping markup cannot make forbidden XML 1.0 code points valid; remove them first.
  const xmlSafe = Array.from(value)
    .filter((character) => {
      const codePoint = character.codePointAt(0)!;
      return (
        codePoint === 0x9 ||
        codePoint === 0xa ||
        codePoint === 0xd ||
        (codePoint >= 0x20 && codePoint <= 0xd7ff) ||
        (codePoint >= 0xe000 && codePoint <= 0xfffd) ||
        (codePoint >= 0x10000 && codePoint <= 0x10ffff)
      );
    })
    .join("");
  return xmlSafe
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function getFeedUrl(format: FeedFormat, filters: FeedFilters, siteOrigin: URL): string {
  const url = new URL(format === "rss" ? "/feed.xml" : "/atom.xml", siteOrigin);
  const params = new URLSearchParams();
  if (filters.country) params.set("country", filters.country);
  if (filters.category) params.set("category", filters.category);
  if (filters.type) params.set("type", filters.type);
  url.search = params.toString();
  return url.toString();
}

function getFeedTitle(filters: FeedFilters): string {
  const labels = [
    filters.type ? (filters.type === "internship" ? "Internship" : "New Grad") : "",
    filters.country,
    filters.category ? formatCategory(filters.category) : "",
  ].filter(Boolean);
  return [siteConfig.name, ...labels].join(" — ");
}

function getFeedDescription(filters: FeedFilters): string {
  const labels = [
    filters.type ? (filters.type === "internship" ? "internship" : "New Grad") : "",
    filters.country,
    filters.category ? formatCategory(filters.category) : "",
  ].filter(Boolean);
  const scope = labels.length ? ` matching ${labels.join(", ")}` : "";
  return `The ${FEED_ITEM_LIMIT} most recently discovered currently open 2027 technology opportunities${scope} across Europe.`;
}

function getUpdatedAt(opportunities: Opportunity[], lastUpdatedAt: string | null): Date {
  let latestTimestamp = 0;
  if (lastUpdatedAt) latestTimestamp = parseTimestamp(lastUpdatedAt);
  for (const opportunity of opportunities) {
    latestTimestamp = Math.max(latestTimestamp, parseTimestamp(opportunity.firstSeenAt));
  }
  return new Date(latestTimestamp);
}

function parseTimestamp(value: string): number {
  const timestamp = parseOpportunityTimestamp(value);
  if (!Number.isFinite(timestamp)) throw new Error("Invalid opportunity timestamp");
  return timestamp;
}

function formatEntry(opportunity: Opportunity) {
  const publishedAt = new Date(parseTimestamp(opportunity.firstSeenAt));
  const type = opportunity.employmentType === "internship" ? "Internship" : "New Grad";
  const description = [
    opportunity.company,
    opportunity.location,
    `Category: ${formatCategory(opportunity.category)}`,
    `Type: ${type}`,
    opportunity.startDate ? `Start: ${opportunity.startDate}` : "",
    opportunity.industries ? `Industry: ${opportunity.industries}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return {publishedAt, description};
}

function renderRssFeed(
  opportunities: Opportunity[],
  selfUrl: string,
  homeUrl: string,
  updatedAt: Date,
  title: string,
  description: string
): string {
  const items = opportunities
    .map((opportunity) => {
      const {publishedAt, description: summary} = formatEntry(opportunity);
      const link = xmlEscape(opportunity.link);
      return [
        "    <item>",
        `      <title>${xmlEscape(`${opportunity.title} — ${opportunity.company}`)}</title>`,
        `      <link>${link}</link>`,
        `      <guid isPermaLink="true">${link}</guid>`,
        `      <pubDate>${publishedAt.toUTCString()}</pubDate>`,
        `      <category>${xmlEscape(opportunity.category)}</category>`,
        `      <description>${xmlEscape(summary)}</description>`,
        "    </item>",
      ].join("\n");
    })
    .join("\n");
  const entries = items ? `\n${items}\n` : "\n";

  return [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
    "  <channel>",
    `    <title>${xmlEscape(title)}</title>`,
    `    <link>${xmlEscape(homeUrl)}</link>`,
    `    <description>${xmlEscape(description)}</description>`,
    `    <language>${siteConfig.language}</language>`,
    `    <lastBuildDate>${updatedAt.toUTCString()}</lastBuildDate>`,
    `    <atom:link rel="self" type="application/rss+xml" href="${xmlEscape(selfUrl)}" />`,
    "    <ttl>60</ttl>",
    entries.trimEnd(),
    "  </channel>",
    "</rss>",
    "",
  ].join("\n");
}

function renderAtomFeed(
  opportunities: Opportunity[],
  selfUrl: string,
  homeUrl: string,
  updatedAt: string,
  title: string,
  description: string
): string {
  const entries = opportunities
    .map((opportunity) => {
      const {publishedAt, description: summary} = formatEntry(opportunity);
      return [
        "  <entry>",
        `    <title>${xmlEscape(`${opportunity.title} — ${opportunity.company}`)}</title>`,
        `    <id>urn:linkedin:job:${xmlEscape(opportunity.linkedinJobId)}</id>`,
        `    <link rel="alternate" href="${xmlEscape(opportunity.link)}" />`,
        `    <published>${publishedAt.toISOString()}</published>`,
        `    <updated>${publishedAt.toISOString()}</updated>`,
        `    <summary>${xmlEscape(summary)}</summary>`,
        `    <category term="${xmlEscape(opportunity.category)}" label="${xmlEscape(formatCategory(opportunity.category))}" />`,
        "  </entry>",
      ].join("\n");
    })
    .join("\n");

  return [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom">',
    `  <title>${xmlEscape(title)}</title>`,
    `  <id>${xmlEscape(selfUrl)}</id>`,
    `  <updated>${updatedAt}</updated>`,
    `  <link rel="alternate" type="text/html" href="${xmlEscape(homeUrl)}" />`,
    `  <link rel="self" type="application/atom+xml" href="${xmlEscape(selfUrl)}" />`,
    `  <subtitle>${xmlEscape(description)}</subtitle>`,
    "  <author>",
    `    <name>${xmlEscape(siteConfig.maintainer.name)}</name>`,
    `    <uri>${xmlEscape(siteConfig.maintainer.url)}</uri>`,
    "  </author>",
    entries,
    "</feed>",
    "",
  ].join("\n");
}
