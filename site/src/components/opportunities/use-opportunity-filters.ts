import {useMemo} from "react";
import {usePathname, useSearchParams} from "next/navigation";
import {ALL_FILTER_VALUE, getCountry} from "@/lib/opportunity-presentation";
import type {EmploymentType, Opportunity} from "@/types/opportunity";

const EMPLOYMENT_TYPE_OPTIONS: EmploymentType[] = ["internship", "new-grad"];

const FILTER_PARAMETERS = {
  query: "q",
  company: "company",
  location: "country",
  category: "category",
  employmentType: "type",
} as const;

type FilterName = keyof typeof FILTER_PARAMETERS;
type HistoryMode = "push" | "replace";

export function useOpportunityFilters(opportunities: Opportunity[]) {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const options = useMemo(
    () => ({
      companies: [...new Set(opportunities.map((item) => item.company))].sort(),
      locations: [...new Set(opportunities.map((item) => getCountry(item.location)))].sort(),
      categories: [...new Set(opportunities.map((item) => item.category))].sort(),
      employmentTypes: EMPLOYMENT_TYPE_OPTIONS,
    }),
    [opportunities]
  );

  const query = searchParams.get(FILTER_PARAMETERS.query) ?? "";
  const requestedCompany = searchParams.get(FILTER_PARAMETERS.company);
  const requestedLocation = searchParams.get(FILTER_PARAMETERS.location);
  const requestedCategory = searchParams.get(FILTER_PARAMETERS.category);
  const requestedEmploymentType = searchParams.get(FILTER_PARAMETERS.employmentType);
  const company = validOption(requestedCompany, options.companies);
  const location = validOption(requestedLocation, options.locations);
  const category = validOption(requestedCategory, options.categories);
  const employmentType = validOption(requestedEmploymentType, options.employmentTypes);

  const filteredOpportunities = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return opportunities.filter((opportunity) => {
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
        (location === ALL_FILTER_VALUE || getCountry(opportunity.location) === location) &&
        (category === ALL_FILTER_VALUE || opportunity.category === category) &&
        (employmentType === ALL_FILTER_VALUE || opportunity.employmentType === employmentType)
      );
    });
  }, [category, company, employmentType, location, opportunities, query]);

  function setFilter(name: FilterName, value: string, historyMode: HistoryMode) {
    const parameters = new URLSearchParams(searchParams.toString());
    const parameter = FILTER_PARAMETERS[name];

    if (!value || value === ALL_FILTER_VALUE) {
      parameters.delete(parameter);
    } else {
      parameters.set(parameter, value);
    }

    const queryString = parameters.toString();
    const url = queryString ? `${pathname}?${queryString}` : pathname;
    window.history[`${historyMode}State`]({}, "", url);
  }

  function clearFilters() {
    const parameters = new URLSearchParams(searchParams.toString());
    Object.values(FILTER_PARAMETERS).forEach((parameter) => parameters.delete(parameter));
    const queryString = parameters.toString();
    window.history.pushState({}, "", queryString ? `${pathname}?${queryString}` : pathname);
  }

  return {
    filters: {query, company, location, category, employmentType},
    setters: {
      setQuery: (value: string) => setFilter("query", value, "replace"),
      setCompany: (value: string) => setFilter("company", value, "push"),
      setLocation: (value: string) => setFilter("location", value, "push"),
      setCategory: (value: string) => setFilter("category", value, "push"),
      setEmploymentType: (value: string) => setFilter("employmentType", value, "push"),
    },
    options,
    filteredOpportunities,
    hasActiveFilters:
      query !== "" ||
      company !== ALL_FILTER_VALUE ||
      location !== ALL_FILTER_VALUE ||
      category !== ALL_FILTER_VALUE ||
      employmentType !== ALL_FILTER_VALUE,
    clearFilters,
  };
}

function validOption(requested: string | null, options: string[]): string {
  return requested && options.includes(requested) ? requested : ALL_FILTER_VALUE;
}
