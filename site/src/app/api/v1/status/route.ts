import {apiMethodNotAllowed, apiOptionsResponse} from "@/lib/api-response";
import {statusResponse} from "@/lib/opportunity-status";
import {getOpportunityStatus} from "@/lib/opportunity-status-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET(request: Request): Promise<Response> {
  return statusResponse(request, getOpportunityStatus);
}

export function HEAD(request: Request): Promise<Response> {
  return statusResponse(request, getOpportunityStatus);
}

export function OPTIONS(request: Request): Response {
  return apiOptionsResponse(request);
}

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
