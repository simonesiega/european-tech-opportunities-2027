import {contentEtag, matchesIfNoneMatch, REVALIDATE_CACHE_CONTROL} from "@/lib/http-cache";
import {getDirectoryData} from "@/lib/opportunities";
import {InvalidApiQuery, apiPayload, parseApiQuery} from "@/lib/opportunity-api";
import {
  API_JSON_HEADERS,
  apiErrorResponse,
  apiMethodNotAllowed,
  apiOptionsResponse,
} from "@/lib/api-response";

export const dynamic = "force-dynamic";

export function GET(request: Request): Response {
  let query: ReturnType<typeof parseApiQuery>;
  try {
    query = parseApiQuery(new URL(request.url).search);
  } catch (error) {
    if (error instanceof InvalidApiQuery) {
      return apiErrorResponse(400, "invalid_query", error.message);
    }
    throw error;
  }

  try {
    const {opportunities, lastUpdatedAt} = getDirectoryData();
    const body = JSON.stringify(apiPayload(opportunities, lastUpdatedAt, query));
    const etag = contentEtag(body);
    const headers = {...API_JSON_HEADERS, "Cache-Control": REVALIDATE_CACHE_CONTROL, ETag: etag};
    if (matchesIfNoneMatch(request.headers.get("if-none-match"), etag)) {
      return new Response(null, {status: 304, headers});
    }
    return new Response(body, {status: 200, headers});
  } catch {
    return apiErrorResponse(503, "unavailable", "Directory unavailable");
  }
}

export function HEAD(request: Request): Response {
  const response = GET(request);
  return new Response(null, {status: response.status, headers: response.headers});
}

export function OPTIONS(request: Request): Response {
  return apiOptionsResponse(request);
}

// Explicit 405 handlers guarantee the documented Allow header; none mutates state.
export function POST(): Response {
  return apiMethodNotAllowed();
}

export function PUT(): Response {
  return apiMethodNotAllowed();
}

export function PATCH(): Response {
  return apiMethodNotAllowed();
}

export function DELETE(): Response {
  return apiMethodNotAllowed();
}
