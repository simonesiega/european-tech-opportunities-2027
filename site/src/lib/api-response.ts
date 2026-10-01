import {API_VERSION} from "@/lib/opportunity-api";

export const API_JSON_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Expose-Headers": "ETag, Cache-Control",
  "Content-Type": "application/json; charset=utf-8",
};
const allowHeader = {Allow: "GET, HEAD, OPTIONS"};

export function apiErrorResponse(
  status: 400 | 503,
  code: "invalid_query" | "unavailable",
  message: string
): Response {
  return Response.json(
    {version: API_VERSION, error: {code, message}},
    {status, headers: {...API_JSON_HEADERS, "Cache-Control": "no-store"}}
  );
}

export function apiOptionsResponse(request: Request): Response {
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

export function apiMethodNotAllowed(): Response {
  return new Response(null, {
    status: 405,
    headers: {
      ...allowHeader,
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    },
  });
}
