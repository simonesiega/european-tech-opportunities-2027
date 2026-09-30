import {
  feedMethodNotAllowed,
  getFeedHeadResponse,
  getFeedResponse,
} from "@/lib/opportunity-feed-response";

export const dynamic = "force-dynamic";

export function GET(request: Request): Response {
  return getFeedResponse(request, "atom");
}

export function HEAD(request: Request): Response {
  return getFeedHeadResponse(request, "atom");
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
