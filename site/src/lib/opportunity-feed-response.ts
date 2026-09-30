import "server-only";

import {createHash} from "node:crypto";
import {getDirectoryData} from "@/lib/opportunities";
import {
  InvalidFeedQuery,
  parseFeedQuery,
  renderOpportunityFeed,
  type FeedFormat,
} from "@/lib/opportunity-feed";
import {siteUrl} from "@/lib/site-url";

const FEED_CONTENT_TYPES: Record<FeedFormat, string> = {
  rss: "application/rss+xml; charset=utf-8",
  atom: "application/atom+xml; charset=utf-8",
};
const CACHE_CONTROL = "public, max-age=0, must-revalidate";

export function getFeedResponse(request: Request, format: FeedFormat): Response {
  let filters: ReturnType<typeof parseFeedQuery>;
  try {
    filters = parseFeedQuery(new URL(request.url).search);
  } catch (error) {
    if (error instanceof InvalidFeedQuery) {
      return new Response("Invalid feed query.\n", {
        status: 400,
        headers: {"Cache-Control": "no-store", "Content-Type": "text/plain; charset=utf-8"},
      });
    }
    throw error;
  }

  try {
    const {opportunities, lastUpdatedAt} = getDirectoryData();
    const body = renderOpportunityFeed(format, opportunities, lastUpdatedAt, filters, siteUrl);
    const etag = `"${createHash("sha256").update(body).digest("hex")}"`;
    const headers = {
      "Cache-Control": CACHE_CONTROL,
      "Content-Type": FEED_CONTENT_TYPES[format],
      ETag: etag,
    };
    if (matchesIfNoneMatch(request.headers.get("if-none-match"), etag)) {
      return new Response(null, {status: 304, headers});
    }
    return new Response(body, {status: 200, headers});
  } catch {
    return new Response("Feed is currently unavailable.\n", {
      status: 503,
      headers: {"Cache-Control": "no-store", "Content-Type": "text/plain; charset=utf-8"},
    });
  }
}

export function getFeedHeadResponse(request: Request, format: FeedFormat): Response {
  const response = getFeedResponse(request, format);
  return new Response(null, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
  });
}

export function feedMethodNotAllowed(): Response {
  return new Response(null, {
    status: 405,
    headers: {Allow: "GET, HEAD", "Cache-Control": "no-store"},
  });
}

function matchesIfNoneMatch(header: string | null, etag: string): boolean {
  if (!header) return false;
  return header.split(",").some((value) => {
    const tag = value.trim();
    return tag === "*" || tag === etag || tag === `W/${etag}`;
  });
}
