import {createHash} from "node:crypto";
import {filterOpportunities} from "@/lib/opportunity-filter";
import {parseOpportunityTimestamp} from "@/lib/opportunity-presentation";
import {DIRECTORY_SORTS, FIRST_SEEN_OPTIONS} from "@/types/directory";
import type {Opportunity} from "@/types/opportunity";

export const API_VERSION = "v1";
export const API_CACHE_CONTROL = "public, max-age=0, must-revalidate";
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

export class InvalidApiQuery extends Error {
  constructor(message: string) {
    super(message);
  }
}

export function parseApiQuery(rawSearch: string) {
  if (rawSearch.length > 2048 || /%(?![0-9a-fA-F]{2})/.test(rawSearch)) {
    throw new InvalidApiQuery("Invalid query string");
  }
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
  const sort = params.has("sort") ? readText("sort") : "first-seen-desc";
  if (params.has("type") && type !== "internship" && type !== "new-grad")
    throw new InvalidApiQuery("Invalid type");
  if (
    params.has("first-seen") &&
    !FIRST_SEEN_OPTIONS.some((option) => option.value === firstSeen)
  ) {
    throw new InvalidApiQuery("Invalid first-seen");
  }
  if (!DIRECTORY_SORTS.some((option) => option === sort)) throw new InvalidApiQuery("Invalid sort");
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
  const referenceTimestamp = opportunities.reduce(
    (latest, row) => Math.max(latest, parseOpportunityTimestamp(row.firstSeenAt)),
    lastUpdatedAt ? parseOpportunityTimestamp(lastUpdatedAt) : 0
  );
  const filtered = filterOpportunities(opportunities, query.filters, referenceTimestamp);
  const descending = query.sort.endsWith("-desc");
  const field = query.sort.replace(/-(asc|desc)$/, "");
  const sorted = filtered.sort((a, b) => {
    const left =
      field === "role"
        ? a.title
        : field === "first-seen"
          ? a.firstSeenAt
          : field === "company"
            ? a.company
            : a.location;
    const right =
      field === "role"
        ? b.title
        : field === "first-seen"
          ? b.firstSeenAt
          : field === "company"
            ? b.company
            : b.location;
    const order =
      field === "first-seen"
        ? Math.sign(parseOpportunityTimestamp(left) - parseOpportunityTimestamp(right))
        : left.localeCompare(right, "en");
    return (
      (descending ? -order : order) ||
      b.linkedinJobId.localeCompare(a.linkedinJobId, "en", {numeric: true})
    );
  });
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
      firstSeenAt: apiFirstSeenAt(item.firstSeenAt),
    })),
  };
}

function apiFirstSeenAt(value: string): string {
  const match =
    /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|([+-])(\d{2}):(\d{2}))?$/.exec(
      value
    );
  if (!match) throw new Error("Invalid first-seen timestamp");

  const [
    ,
    yearText,
    monthText,
    dayText,
    hourText,
    minuteText,
    secondText,
    fractionText,
    ,
    sign,
    offsetHourText,
    offsetMinuteText,
  ] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  const offsetHour = Number(offsetHourText ?? 0);
  const offsetMinute = Number(offsetMinuteText ?? 0);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > daysInMonth[month - 1]! ||
    hour > 23 ||
    minute > 59 ||
    second > 59 ||
    offsetHour > 23 ||
    offsetMinute > 59
  ) {
    throw new Error("Invalid first-seen timestamp");
  }

  const timestamp = new Date(0);
  timestamp.setUTCFullYear(year, month - 1, day);
  timestamp.setUTCHours(hour, minute, second, 0);
  const offset = (offsetHour * 60 + offsetMinute) * (sign === "+" ? 1 : -1);
  timestamp.setTime(timestamp.getTime() - offset * 60_000);
  const normalized = timestamp.toISOString();
  if (!/^\d{4}-/.test(normalized)) throw new Error("Invalid first-seen timestamp");
  const fraction = (fractionText ?? "").padEnd(6, "0");
  return `${normalized.slice(0, 19)}.${fraction}+00:00`;
}

export function apiEtag(body: string): string {
  return `"${createHash("sha256").update(body).digest("hex")}"`;
}

export function matchesIfNoneMatch(header: string | null, etag: string): boolean {
  if (!header) return false;
  return header.split(",").some((value) => {
    const tag = value.trim();
    return tag === "*" || tag === etag || tag === `W/${etag}`;
  });
}
