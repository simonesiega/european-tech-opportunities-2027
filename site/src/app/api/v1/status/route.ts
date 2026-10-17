import {statusResponse} from "@/lib/opportunity-status";
import {getOpportunityStatus} from "@/lib/opportunity-status-data";

export {
  apiOptionsResponse as OPTIONS,
  apiMethodNotAllowed as POST,
  apiMethodNotAllowed as PUT,
  apiMethodNotAllowed as PATCH,
  apiMethodNotAllowed as DELETE,
} from "@/lib/api-response";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET(request: Request): Promise<Response> {
  return statusResponse(request, getOpportunityStatus);
}

export const HEAD = GET;
