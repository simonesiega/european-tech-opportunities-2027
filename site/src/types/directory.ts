const DAY_IN_MILLISECONDS = 24 * 60 * 60 * 1000;

export const DEFAULT_DIRECTORY_PAGE_SIZE = 10;
export const DIRECTORY_PAGE_SIZES = [DEFAULT_DIRECTORY_PAGE_SIZE, 20, 30, 50, 100] as const;
export const FIRST_SEEN_OPTIONS = [
  {value: "24-hours", label: "Last 24 hours", durationMs: DAY_IN_MILLISECONDS},
  {value: "7-days", label: "Last 7 days", durationMs: 7 * DAY_IN_MILLISECONDS},
  {value: "30-days", label: "Last 30 days", durationMs: 30 * DAY_IN_MILLISECONDS},
] as const;
export const DIRECTORY_SORTS = [
  "company-asc",
  "company-desc",
  "role-asc",
  "role-desc",
  "location-asc",
  "location-desc",
  "first-seen-asc",
  "first-seen-desc",
] as const;

export type DirectoryPageSize = (typeof DIRECTORY_PAGE_SIZES)[number];
export type DirectorySort = (typeof DIRECTORY_SORTS)[number];

export type DirectoryView = {
  sort: DirectorySort;
  page: number;
  pageSize: DirectoryPageSize;
};
