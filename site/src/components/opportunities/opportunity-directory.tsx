"use client";

import {useEffect, useRef, useSyncExternalStore} from "react";
import {Download} from "lucide-react";
import {OpportunityFilters} from "@/components/opportunities/opportunity-filters";
import {OpportunityList} from "@/components/opportunities/opportunity-list";
import {useOpportunityDirectory} from "@/components/opportunities/use-opportunity-directory";
import {Badge} from "@/components/ui/badge";
import {siteConfig} from "@/lib/site-config";
import type {Opportunity} from "@/types/opportunity";

type OpportunityDirectoryProps = {
  opportunities: Opportunity[];
  referenceTime: string;
};

const subscribeToHydration = () => () => undefined;
const getClientHydrationState = () => true;
const getServerHydrationState = () => false;

export function OpportunityDirectory({opportunities, referenceTime}: OpportunityDirectoryProps) {
  const searchInputRef = useRef<HTMLInputElement>(null);
  const isInteractive = useSyncExternalStore(
    subscribeToHydration,
    getClientHydrationState,
    getServerHydrationState
  );
  const {
    filters,
    filterSetters,
    view,
    viewSetters,
    pageHref,
    options,
    filteredOpportunities,
    hasActiveFilters,
    clearFilters,
  } = useOpportunityDirectory(opportunities, referenceTime);

  useEffect(() => {
    function focusSearch(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    }

    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  return (
    <section
      className="py-6 pt-11 max-[600px]:pt-8"
      aria-busy={!isInteractive}
      aria-labelledby="opportunities-title"
    >
      <div className="flex items-start justify-between gap-6 max-[760px]:flex-col">
        <div>
          <h1
            id="opportunities-title"
            className="text-[26px] leading-[1.2] font-[650] tracking-[-0.035em] max-[600px]:text-[23px]"
          >
            Opportunity directory
          </h1>
          <p className="mt-[7px] text-sm text-[var(--text-soft)] max-[600px]:max-w-[300px] max-[600px]:text-[13px] max-[600px]:leading-normal">
            {siteConfig.description}
          </p>
        </div>
        <div className="flex items-center gap-2 max-[760px]:w-full max-[480px]:flex-wrap">
          {(["csv", "json"] as const).map((format) => (
            <a
              key={format}
              className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 text-[12px] font-medium whitespace-nowrap text-[var(--text)] shadow-[0_1px_2px_rgb(0_0_0/3%)] transition-colors duration-150 hover:bg-[var(--surface-hover)] [&_svg]:size-3.5"
              href={`/open-opportunities.${format}`}
              download
            >
              <Download aria-hidden="true" />
              Download {format.toUpperCase()}
            </a>
          ))}
          <Badge
            className="min-h-8 gap-1.5 rounded-md px-2.5 py-0 max-[760px]:ml-auto"
            variant="outline"
            role="status"
            aria-atomic="true"
          >
            <strong className="text-base font-bold tracking-[-0.03em] text-[var(--text)]">
              {filteredOpportunities.length}
            </strong>
            <span className="text-[11px] text-[var(--text-soft)]">
              open {filteredOpportunities.length === 1 ? "role" : "roles"}
            </span>
          </Badge>
        </div>
      </div>

      <OpportunityFilters
        searchInputRef={searchInputRef}
        filters={filters}
        options={options}
        hasActiveFilters={hasActiveFilters}
        onQueryChange={filterSetters.setQuery}
        onCompanyChange={filterSetters.setCompany}
        onLocationChange={filterSetters.setLocation}
        onCategoryChange={filterSetters.setCategory}
        onEmploymentTypeChange={filterSetters.setEmploymentType}
        onFirstSeenChange={filterSetters.setFirstSeen}
        onClear={clearFilters}
      />
      <OpportunityList
        opportunities={filteredOpportunities}
        view={view}
        pageHref={pageHref}
        hasActiveFilters={hasActiveFilters}
        onSortChange={viewSetters.setSort}
        onPageChange={viewSetters.setPage}
        onPageSizeChange={viewSetters.setPageSize}
        onReset={clearFilters}
      />
    </section>
  );
}
