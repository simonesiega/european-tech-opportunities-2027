"use client";

import {useEffect, useRef} from "react";
import {OpportunityFilters} from "@/components/opportunities/opportunity-filters";
import {OpportunityList} from "@/components/opportunities/opportunity-list";
import {useOpportunityFilters} from "@/components/opportunities/use-opportunity-filters";
import {Badge} from "@/components/ui/badge";
import type {Opportunity} from "@/types/opportunity";

type OpportunityDirectoryProps = {
  opportunities: Opportunity[];
};

export function OpportunityDirectory({opportunities}: OpportunityDirectoryProps) {
  const searchInputRef = useRef<HTMLInputElement>(null);
  const {filters, setters, options, filteredOpportunities, hasActiveFilters, clearFilters} =
    useOpportunityFilters(opportunities);

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
    <section className="py-6 pt-11 max-[600px]:pt-8" aria-labelledby="opportunities-title">
      <div className="flex items-start justify-between gap-6">
        <div>
          <h1
            id="opportunities-title"
            className="text-[26px] leading-[1.2] font-[650] tracking-[-0.035em] max-[600px]:text-[23px]"
          >
            Internship directory
          </h1>
          <p className="mt-[7px] text-sm text-[var(--text-soft)] max-[600px]:max-w-[300px] max-[600px]:text-[13px] max-[600px]:leading-normal">
            Discover open 2027 technology internships and New Grad roles across Europe.
          </p>
        </div>
        <Badge
          className="directory-count min-h-8 gap-1.5 rounded-md px-2.5 py-0"
          variant="outline"
          aria-live="polite"
        >
          <strong className="text-base font-bold tracking-[-0.03em] text-[var(--text)]">
            {filteredOpportunities.length}
          </strong>
          <span className="text-[11px] text-[var(--text-soft)]">
            open {filteredOpportunities.length === 1 ? "role" : "roles"}
          </span>
        </Badge>
      </div>

      <OpportunityFilters
        searchInputRef={searchInputRef}
        filters={filters}
        options={options}
        hasActiveFilters={hasActiveFilters}
        onQueryChange={setters.setQuery}
        onCompanyChange={setters.setCompany}
        onLocationChange={setters.setLocation}
        onCategoryChange={setters.setCategory}
        onEmploymentTypeChange={setters.setEmploymentType}
        onClear={clearFilters}
      />
      <OpportunityList opportunities={filteredOpportunities} onReset={clearFilters} />
    </section>
  );
}
