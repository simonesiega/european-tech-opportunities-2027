import type {RefObject} from "react";
import {ChevronDown, Search, X} from "lucide-react";
import {Button} from "@/components/ui/button";
import {Input} from "@/components/ui/input";
import {cn} from "@/lib/cn";
import {ALL_FILTER_VALUE, formatCategory} from "@/lib/opportunity-presentation";

type OpportunityFiltersProps = {
  searchInputRef: RefObject<HTMLInputElement | null>;
  filters: {
    query: string;
    company: string;
    location: string;
    category: string;
    employmentType: string;
  };
  options: {
    companies: string[];
    locations: string[];
    categories: string[];
    employmentTypes: string[];
  };
  hasActiveFilters: boolean;
  onQueryChange: (value: string) => void;
  onCompanyChange: (value: string) => void;
  onLocationChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onEmploymentTypeChange: (value: string) => void;
  onClear: () => void;
};

type FilterSelectProps = {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
};

function FilterSelect({label, value, options, onChange}: FilterSelectProps) {
  return (
    <label className="flex min-w-0 flex-col gap-[7px]">
      <span className="text-[11px] font-[550] text-[var(--text-soft)]">{label}</span>
      <span className="relative">
        <select
          className="h-9 w-full cursor-pointer appearance-none rounded-md border border-[var(--border)] bg-[var(--surface)] py-0 pr-8 pl-2.5 text-[13px] text-[var(--text)] shadow-[0_1px_2px_rgb(0_0_0/3%)] outline-none focus:border-[var(--text-faint)] focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--text)_9%,transparent)]"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value={ALL_FILTER_VALUE}>All</option>
          {options.map((option) => (
            <option key={option} value={option}>
              {label === "Category" || label === "Employment type"
                ? formatCategory(option)
                : option}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute top-1/2 right-2.5 size-3.5 -translate-y-1/2 text-[var(--text-faint)]"
          aria-hidden="true"
        />
      </span>
    </label>
  );
}

export function OpportunityFilters({
  searchInputRef,
  filters,
  options,
  hasActiveFilters,
  onQueryChange,
  onCompanyChange,
  onLocationChange,
  onCategoryChange,
  onEmploymentTypeChange,
  onClear,
}: OpportunityFiltersProps) {
  return (
    <div
      className="mt-7 grid grid-cols-[minmax(260px,1.5fr)_repeat(4,minmax(130px,0.7fr))_auto] gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[0_1px_2px_rgb(0_0_0/3%)] max-[1040px]:grid-cols-3 max-[620px]:grid-cols-1 max-[620px]:p-3.5"
      aria-label="Opportunity filters"
    >
      <label
        className={cn(
          "flex min-w-0 flex-col gap-[7px]",
          "max-[1040px]:col-span-full max-[620px]:col-span-1"
        )}
      >
        <span className="text-[11px] font-[550] text-[var(--text-soft)]">Search</span>
        <div className="relative">
          <Search
            className="pointer-events-none absolute top-2.5 left-[11px] z-1 size-4 text-[var(--text-faint)]"
            aria-hidden="true"
          />
          <Input
            className="pl-[35px]"
            ref={searchInputRef}
            type="search"
            value={filters.query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search company, role, or location..."
          />
        </div>
      </label>

      <FilterSelect
        label="Company"
        value={filters.company}
        options={options.companies}
        onChange={onCompanyChange}
      />
      <FilterSelect
        label="Location"
        value={filters.location}
        options={options.locations}
        onChange={onLocationChange}
      />
      <FilterSelect
        label="Category"
        value={filters.category}
        options={options.categories}
        onChange={onCategoryChange}
      />
      <FilterSelect
        label="Employment type"
        value={filters.employmentType}
        options={options.employmentTypes}
        onChange={onEmploymentTypeChange}
      />

      {hasActiveFilters ? (
        <Button variant="outline" className="self-end max-[620px]:w-full" onClick={onClear}>
          <X aria-hidden="true" />
          Reset
        </Button>
      ) : (
        <span className="w-[88px] max-[620px]:hidden" aria-hidden="true" />
      )}
    </div>
  );
}
