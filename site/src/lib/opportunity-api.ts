import {filterOpportunities} from "@/lib/opportunity-filter";
import {
  normalizeOpportunityTimestamp,
  parseOpportunityTimestamp,
} from "@/lib/opportunity-presentation";
import {sortOpportunities} from "@/lib/opportunity-sort";
import {DIRECTORY_SORTS, FIRST_SEEN_OPTIONS} from "@/types/directory";
import type {Opportunity} from "@/types/opportunity";

export const API_VERSION = "v1";
const PARAMETERS = [
  "country",
  "company",
  "category",
  "type",
  "q",
  "first-seen",
  "sort",
  "page",
  "page-size",
];
const MAX_PAGE_SIZE = 100;
const MAX_PAGE = 10000;

export class InvalidApiQuery extends Error {}

export function parseApiQuery(rawSearch: string) {
  if (rawSearch.length > 2048 || /%(?![0-9a-fA-F]{2})/.test(rawSearch)) {
    throw new InvalidApiQuery("Invalid query string");
  }
  // URLSearchParams repairs malformed input; reject replacement characters below
  // instead of silently accepting a different query from the one the caller sent.
  const params = new URLSearchParams(rawSearch);
  for (const [key, value] of params) {
    if (!PARAMETERS.includes(key) || params.getAll(key).length !== 1) {
      throw new InvalidApiQuery("Unknown or repeated parameter");
    }
    if (value.length > 200 || /[\u0000-\u001f\u007f\ufffd]/u.test(value)) {
      throw new InvalidApiQuery(`Invalid value for ${key}`);
    }
  }
  const readText = (key: string) => {
    const value = params.get(key) ?? "";
    if (key !== "q" && value && value !== value.trim()) {
      throw new InvalidApiQuery(`Invalid value for ${key}`);
    }
    return value;
  };
  for (const key of ["country", "company", "category"]) {
    if (params.has(key) && !readText(key)) {
      throw new InvalidApiQuery(`Invalid value for ${key}`);
    }
  }
  const type = readText("type");
  const firstSeen = readText("first-seen");
  const requestedSort = params.has("sort") ? readText("sort") : "first-seen-desc";
  const sort = DIRECTORY_SORTS.find((option) => option === requestedSort);
  if (params.has("type") && type !== "internship" && type !== "new-grad")
    throw new InvalidApiQuery("Invalid type");
  if (
    params.has("first-seen") &&
    !FIRST_SEEN_OPTIONS.some((option) => option.value === firstSeen)
  ) {
    throw new InvalidApiQuery("Invalid first-seen");
  }
  if (!sort) throw new InvalidApiQuery("Invalid sort");
  const integer = (key: string, fallback: number, maximum: number) => {
    const value = params.get(key);
    if (value === null) return fallback;
    if (!/^[1-9][0-9]*$/.test(value) || Number(value) > maximum) {
      throw new InvalidApiQuery(`Invalid ${key}: expected an integer from 1 to ${maximum}`);
    }
    return Number(value);
  };
  return {
    filters: {
      q: readText("q"),
      country: readText("country"),
      company: readText("company"),
      category: readText("category"),
      type,
      firstSeen,
    },
    sort,
    page: integer("page", 1, MAX_PAGE),
    pageSize: integer("page-size", 10, MAX_PAGE_SIZE),
  };
}

export function apiPayload(
  opportunities: Opportunity[],
  lastUpdatedAt: string | null,
  query: ReturnType<typeof parseApiQuery>
) {
  // A release-relative clock makes recency queries reproducible for the same
  // canonical snapshot. Manual-only databases have no successful search run.
  const lastUpdatedTimestamp = lastUpdatedAt ? parseOpportunityTimestamp(lastUpdatedAt) : 0;
  if (!Number.isFinite(lastUpdatedTimestamp)) throw new Error("Invalid collection timestamp");
  const referenceTimestamp = opportunities.reduce((latest, row) => {
    const timestamp = parseOpportunityTimestamp(row.firstSeenAt);
    if (!Number.isFinite(timestamp)) throw new Error("Invalid first-seen timestamp");
    return Math.max(latest, timestamp);
  }, lastUpdatedTimestamp);
  const filtered = filterOpportunities(opportunities, query.filters, referenceTimestamp);
  const sorted = sortOpportunities(filtered, query.sort);
  const total = sorted.length;
  const totalPages = Math.ceil(total / query.pageSize);
  const offset = (query.page - 1) * query.pageSize;
  return {
    version: API_VERSION,
    pagination: {
      page: query.page,
      pageSize: query.pageSize,
      total,
      totalPages,
    },
    // Keep an explicit allowlist: future internal fields must not enter the v1 contract.
    data: sorted.slice(offset, offset + query.pageSize).map((item) => ({
      linkedinJobId: item.linkedinJobId,
      company: item.company,
      title: item.title,
      location: item.location,
      link: item.link,
      category: item.category,
      industries: item.industries,
      employmentType: item.employmentType,
      startDate: item.startDate,
      firstSeenAt: normalizeOpportunityTimestamp(item.firstSeenAt),
    })),
  };
}
