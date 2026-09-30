import {
  feedMethodNotAllowed,
  getFeedHeadResponse,
  getFeedResponse,
} from "@/lib/opportunity-feed-response";

export const dynamic = "force-dynamic";

export function GET(request: Request): Response {
  return getFeedResponse(request, "rss");
}

export function HEAD(request: Request): Response {
  return getFeedHeadResponse(request, "rss");
}

export function POST(): Response {
  return feedMethodNotAllowed();
}

export function PUT(): Response {
  return feedMethodNotAllowed();
}

export function PATCH(): Response {
  return feedMethodNotAllowed();
}

export function DELETE(): Response {
  return feedMethodNotAllowed();
}
