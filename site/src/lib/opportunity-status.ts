import {API_JSON_HEADERS, apiErrorResponse} from "@/lib/api-response";
import {normalizeOpportunityTimestamp} from "@/lib/opportunity-presentation";

export type OpportunityStatus = {
  last_successful_collection: string | null;
  dataset_generated_at: string;
  opportunities: number;
  dataset_sha256: string;
  release: string | null;
};

export function statusPayload(
  summary: {lastUpdatedAt: string | null; opportunities: number},
  metadata: unknown,
  jsonSha256: string,
  release: string | null
): OpportunityStatus {
  if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
    throw new Error("Invalid dataset metadata");
  }
  const record = metadata as Record<string, unknown>;
  const count = (value: unknown): value is number =>
    typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
  const sha256 = (value: unknown): value is string =>
    typeof value === "string" && value.length === 64 && /^[0-9a-f]{64}$/.test(value);
  if (
    record.schema_version !== "v1" ||
    typeof record.generated_at !== "string" ||
    record.generated_at[10] !== "T" ||
    !/(?:Z|\+00:00)$/.test(record.generated_at) ||
    !count(record.total) ||
    !count(record.internship_count) ||
    !count(record.new_grad_count) ||
    record.internship_count + record.new_grad_count !== record.total ||
    !count(summary.opportunities) ||
    record.total !== summary.opportunities ||
    !sha256(record.json_sha256) ||
    !sha256(record.csv_sha256) ||
    record.json_sha256 !== jsonSha256 ||
    (release !== null && (release !== release.trim() || !/^[0-9]+-[0-9]+$/.test(release)))
  ) {
    throw new Error("Inconsistent dataset status");
  }
  // Keep an explicit allowlist: future metadata fields must not enter the status contract.
  return {
    last_successful_collection:
      summary.lastUpdatedAt === null ? null : normalizeOpportunityTimestamp(summary.lastUpdatedAt),
    dataset_generated_at: normalizeOpportunityTimestamp(record.generated_at),
    opportunities: summary.opportunities,
    dataset_sha256: record.json_sha256,
    release,
  };
}

export async function statusResponse(
  request: Request,
  readStatus: () => Promise<OpportunityStatus>
): Promise<Response> {
  let response: Response;
  if (new URL(request.url).search) {
    response = apiErrorResponse(400, "invalid_query", "Status does not accept query parameters");
  } else {
    try {
      response = Response.json(await readStatus(), {
        headers: {...API_JSON_HEADERS, "Cache-Control": "no-store"},
      });
    } catch {
      response = apiErrorResponse(503, "unavailable", "Status unavailable");
    }
  }
  return request.method === "HEAD"
    ? new Response(null, {status: response.status, headers: response.headers})
    : response;
}
