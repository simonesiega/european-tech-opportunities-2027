import {useMemo} from "react";
import {usePathname, useSearchParams} from "next/navigation";
import {
  ALL_FILTER_VALUE,
  getCountries,
  parseOpportunityTimestamp,
} from "@/lib/opportunity-presentation";
import {
  DIRECTORY_PAGE_SIZES,
  DIRECTORY_SORTS,
  DEFAULT_DIRECTORY_PAGE_SIZE,
  FIRST_SEEN_OPTIONS,
  type DirectoryPageSize,
  type DirectorySort,
} from "@/types/directory";
import type {EmploymentType, Opportunity} from "@/types/opportunity";

const EMPLOYMENT_TYPE_OPTIONS: EmploymentType[] = ["internship", "new-grad"];
const DEFAULT_SORT: DirectorySort = "first-seen-desc";
const FIRST_SEEN_VALUES = FIRST_SEEN_OPTIONS.map((option) => option.value);

const FILTER_PARAMETERS = {
  query: "q",
  company: "company",
  location: "country",
  category: "category",
  employmentType: "type",
  firstSeen: "first-seen",
} as const;

const VIEW_PARAMETERS = {
  sort: "sort",
  page: "page",
  pageSize: "page-size",
} as const;

type FilterName = keyof typeof FILTER_PARAMETERS;
type DirectoryParameter =
  | (typeof FILTER_PARAMETERS)[keyof typeof FILTER_PARAMETERS]
  | (typeof VIEW_PARAMETERS)[keyof typeof VIEW_PARAMETERS];
type HistoryMode = "push" | "replace";

export function useOpportunityDirectory(opportunities: Opportunity[], referenceTime: string) {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const options = useMemo(
    () => ({
      companies: [...new Set(opportunities.map((item) => item.company))].sort(),
      locations: [...new Set(opportunities.flatMap((item) => getCountries(item.location)))].sort(),
      categories: [...new Set(opportunities.map((item) => item.category))].sort(),
      employmentTypes: EMPLOYMENT_TYPE_OPTIONS,
      firstSeenPeriods: FIRST_SEEN_VALUES,
    }),
    [opportunities]
  );

  const query = searchParams.get(FILTER_PARAMETERS.query) ?? "";
  const company = validOption(searchParams.get(FILTER_PARAMETERS.company), options.companies);
  const location = validOption(searchParams.get(FILTER_PARAMETERS.location), options.locations);
  const category = validOption(searchParams.get(FILTER_PARAMETERS.category), options.categories);
  const employmentType = validOption(
    searchParams.get(FILTER_PARAMETERS.employmentType),
    options.employmentTypes
  );
  const firstSeen = validOption(
    searchParams.get(FILTER_PARAMETERS.firstSeen),
    options.firstSeenPeriods
  );
  const firstSeenOption = FIRST_SEEN_OPTIONS.find((option) => option.value === firstSeen);
  const referenceTimestamp = parseOpportunityTimestamp(referenceTime);
  const firstSeenCutoff = firstSeenOption ? referenceTimestamp - firstSeenOption.durationMs : null;

  const filteredOpportunities = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return opportunities.filter((opportunity) => {
      const firstSeenTimestamp = parseOpportunityTimestamp(opportunity.firstSeenAt);
      const searchableText = [
        opportunity.company,
        opportunity.title,
        opportunity.category,
        opportunity.industries,
        opportunity.employmentType,
        opportunity.location,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return (
        (!normalizedQuery || searchableText.includes(normalizedQuery)) &&
        (company === ALL_FILTER_VALUE || opportunity.company === company) &&
        (location === ALL_FILTER_VALUE || getCountries(opportunity.location).includes(location)) &&
        (category === ALL_FILTER_VALUE || opportunity.category === category) &&
        (employmentType === ALL_FILTER_VALUE || opportunity.employmentType === employmentType) &&
        (firstSeenCutoff === null ||
          (firstSeenTimestamp >= firstSeenCutoff && firstSeenTimestamp <= referenceTimestamp))
      );
    });
  }, [
    category,
    company,
    employmentType,
    firstSeenCutoff,
    location,
    opportunities,
    query,
    referenceTimestamp,
  ]);

  const sort = validSort(searchParams.get(VIEW_PARAMETERS.sort));
  const pageSize = validPageSize(searchParams.get(VIEW_PARAMETERS.pageSize));
  const requestedPage = validPage(searchParams.get(VIEW_PARAMETERS.page));
  const pageCount = Math.max(Math.ceil(filteredOpportunities.length / pageSize), 1);
  const page = Math.min(requestedPage, pageCount);

  function directoryUrl(updates: Partial<Record<DirectoryParameter, string | null>>) {
    const parameters = new URLSearchParams(searchParams.toString());

    for (const [parameter, value] of Object.entries(updates)) {
      if (value) {
        parameters.set(parameter, value);
      } else {
        parameters.delete(parameter);
      }
    }

    const queryString = parameters.toString();
    return queryString ? `${pathname}?${queryString}` : pathname;
  }

  function updateUrl(
    updates: Partial<Record<DirectoryParameter, string | null>>,
    historyMode: HistoryMode
  ) {
    const url = directoryUrl(updates);
    if (historyMode === "push") {
      window.history.pushState({}, "", url);
    } else {
      window.history.replaceState({}, "", url);
    }
  }

  function setFilter(name: FilterName, value: string, historyMode: HistoryMode) {
    updateUrl(
      {
        [FILTER_PARAMETERS[name]]: value && value !== ALL_FILTER_VALUE ? value : null,
        [VIEW_PARAMETERS.page]: null,
      },
      historyMode
    );
  }

  function clearFilters() {
    const updates: Partial<Record<DirectoryParameter, null>> = {
      [VIEW_PARAMETERS.page]: null,
    };
    Object.values(FILTER_PARAMETERS).forEach((parameter) => {
      updates[parameter] = null;
    });
    updateUrl(updates, "push");
  }

  return {
    filters: {query, company, location, category, employmentType, firstSeen},
    filterSetters: {
      setQuery: (value: string) => setFilter("query", value, "replace"),
      setCompany: (value: string) => setFilter("company", value, "push"),
      setLocation: (value: string) => setFilter("location", value, "push"),
      setCategory: (value: string) => setFilter("category", value, "push"),
      setEmploymentType: (value: string) => setFilter("employmentType", value, "push"),
      setFirstSeen: (value: string) => setFilter("firstSeen", value, "push"),
    },
    view: {sort, page, pageSize},
    pageHref: (value: number) =>
      directoryUrl({[VIEW_PARAMETERS.page]: value > 1 ? String(value) : null}),
    viewSetters: {
      setSort: (value: DirectorySort) =>
        updateUrl(
          {
            [VIEW_PARAMETERS.sort]: value === DEFAULT_SORT ? null : value,
            [VIEW_PARAMETERS.page]: null,
          },
          "push"
        ),
      setPage: (value: number) =>
        updateUrl({[VIEW_PARAMETERS.page]: value > 1 ? String(value) : null}, "push"),
      setPageSize: (value: DirectoryPageSize) =>
        updateUrl(
          {
            [VIEW_PARAMETERS.pageSize]:
              value === DEFAULT_DIRECTORY_PAGE_SIZE ? null : String(value),
            [VIEW_PARAMETERS.page]: null,
          },
          "push"
        ),
    },
    options,
    filteredOpportunities,
    hasActiveFilters:
      query !== "" ||
      company !== ALL_FILTER_VALUE ||
      location !== ALL_FILTER_VALUE ||
      category !== ALL_FILTER_VALUE ||
      employmentType !== ALL_FILTER_VALUE ||
      firstSeen !== ALL_FILTER_VALUE,
    clearFilters,
  };
}

function validOption(requested: string | null, options: readonly string[]): string {
  return requested && options.includes(requested) ? requested : ALL_FILTER_VALUE;
}

function validSort(requested: string | null): DirectorySort {
  return isDirectorySort(requested) ? requested : DEFAULT_SORT;
}

function isDirectorySort(value: string | null): value is DirectorySort {
  return value !== null && DIRECTORY_SORTS.some((sort) => sort === value);
}

function validPageSize(requested: string | null): DirectoryPageSize {
  const parsed = Number(requested);
  return (
    DIRECTORY_PAGE_SIZES.find((pageSize) => pageSize === parsed) ?? DEFAULT_DIRECTORY_PAGE_SIZE
  );
}

function validPage(requested: string | null): number {
  const parsed = Number(requested);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 1;
}
