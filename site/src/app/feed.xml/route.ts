import {getFeedHeadResponse, getFeedResponse} from "@/lib/opportunity-feed-response";

export {
  feedMethodNotAllowed as POST,
  feedMethodNotAllowed as PUT,
  feedMethodNotAllowed as PATCH,
  feedMethodNotAllowed as DELETE,
} from "@/lib/opportunity-feed-response";

export const dynamic = "force-dynamic";

export function GET(request: Request): Response {
  return getFeedResponse(request, "rss");
}

export function HEAD(request: Request): Response {
  return getFeedHeadResponse(request, "rss");
}
