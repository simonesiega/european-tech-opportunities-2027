import {getDirectoryData} from "@/lib/opportunities";
import {
  API_CACHE_CONTROL,
  API_VERSION,
  InvalidApiQuery,
  apiEtag,
  apiPayload,
  matchesIfNoneMatch,
  parseApiQuery,
} from "@/lib/opportunity-api";

export const dynamic = "force-dynamic";

const jsonHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Expose-Headers": "ETag, Cache-Control",
  "Content-Type": "application/json; charset=utf-8",
};
const allowHeader = {Allow: "GET, HEAD, OPTIONS"};

export function GET(request: Request): Response {
  let query: ReturnType<typeof parseApiQuery>;
  try {
    query = parseApiQuery(new URL(request.url).search);
  } catch (error) {
    if (error instanceof InvalidApiQuery) {
      return Response.json(
        {version: API_VERSION, error: {code: "invalid_query", message: error.message}},
        {
          status: 400,
          headers: {...jsonHeaders, "Cache-Control": "no-store"},
        }
      );
    }
    throw error;
  }

  try {
    const {opportunities, lastUpdatedAt} = getDirectoryData();
    const body = JSON.stringify(apiPayload(opportunities, lastUpdatedAt, query));
    const etag = apiEtag(body);
    const headers = {...jsonHeaders, "Cache-Control": API_CACHE_CONTROL, ETag: etag};
    if (matchesIfNoneMatch(request.headers.get("if-none-match"), etag)) {
      return new Response(null, {status: 304, headers});
    }
    return new Response(body, {status: 200, headers});
  } catch {
    return Response.json(
      {version: API_VERSION, error: {code: "unavailable", message: "Directory unavailable"}},
      {
        status: 503,
        headers: {...jsonHeaders, "Cache-Control": "no-store"},
      }
    );
  }
}

export function HEAD(request: Request): Response {
  const response = GET(request);
  return new Response(null, {status: response.status, headers: response.headers});
}

export function OPTIONS(request: Request): Response {
  const requestedMethod = request.headers.get("access-control-request-method");
  const requestedHeaders = (request.headers.get("access-control-request-headers") ?? "")
    .split(",")
    .map((header) => header.trim().toLowerCase())
    .filter(Boolean);
  if (
    (requestedMethod && requestedMethod !== "GET" && requestedMethod !== "HEAD") ||
    requestedHeaders.some((header) => header !== "if-none-match")
  ) {
    return new Response(null, {status: 403, headers: {"Cache-Control": "no-store"}});
  }
  return new Response(null, {
    status: 204,
    headers: {
      ...allowHeader,
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD",
      "Access-Control-Allow-Headers": "If-None-Match",
      "Access-Control-Max-Age": "86400",
      "Cache-Control": "no-store",
      Vary: "Access-Control-Request-Method, Access-Control-Request-Headers",
    },
  });
}

function methodNotAllowed(): Response {
  return new Response(null, {
    status: 405,
    headers: {
      ...allowHeader,
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    },
  });
}

// Explicit 405 handlers guarantee the documented Allow header; none mutates state.
export function POST(): Response {
  return methodNotAllowed();
}

export function PUT(): Response {
  return methodNotAllowed();
}

export function PATCH(): Response {
  return methodNotAllowed();
}

export function DELETE(): Response {
  return methodNotAllowed();
}
