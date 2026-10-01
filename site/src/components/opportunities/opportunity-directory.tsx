"use client";

import {useEffect, useMemo, useRef, useState, useSyncExternalStore} from "react";
import {Download} from "lucide-react";
import {OpportunityFilters} from "@/components/opportunities/opportunity-filters";
import {OpportunityList} from "@/components/opportunities/opportunity-list";
import {useLocalOpportunities} from "@/components/opportunities/use-local-opportunities";
import {useOpportunityDirectory} from "@/components/opportunities/use-opportunity-directory";
import {Badge} from "@/components/ui/badge";
import {newOpportunityIds, type LocalOpportunityView} from "@/lib/local-opportunity-state";
import {siteConfig} from "@/lib/site-config";
import type {Opportunity} from "@/types/opportunity";

type OpportunityDirectoryProps = {
  opportunities: Opportunity[];
  referenceTime: string;
};

// Keep SSR and initial hydration identical before exposing browser-only interaction state.
const subscribeToHydration = () => () => undefined;
const getClientHydrationState = () => true;
const getServerHydrationState = () => false;

export function OpportunityDirectory({opportunities, referenceTime}: OpportunityDirectoryProps) {
  const searchInputRef = useRef<HTMLInputElement>(null);
  const hiddenViewRef = useRef<HTMLButtonElement>(null);
  const allViewRef = useRef<HTMLButtonElement>(null);
  const savedViewRef = useRef<HTMLButtonElement>(null);
  const appliedViewRef = useRef<HTMLButtonElement>(null);
  const [localView, setLocalView] = useState<LocalOpportunityView>("all");
  const {state, previousVisit, toggle} = useLocalOpportunities(opportunities);
  const newIds = useMemo(
    () => newOpportunityIds(opportunities, previousVisit),
    [opportunities, previousVisit]
  );
  const visibleOpportunities = useMemo(
    () =>
      opportunities.filter((item) => {
        if (!state) return true;
        const id = item.linkedinJobId;
        if (localView === "hidden") return state.hidden.includes(id);
        if (state.hidden.includes(id)) return false;
        if (localView === "new") return newIds.has(id);
        return localView === "all" || state[localView].includes(id);
      }),
    [opportunities, state, localView, newIds]
  );
  const newCount = [...newIds].filter((id) => !state?.hidden.includes(id)).length;
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
  } = useOpportunityDirectory(opportunities, referenceTime, visibleOpportunities);

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
      <div className="flex items-start justify-between gap-6 max-[1090px]:flex-col">
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
          {state ? (
            <p className="mt-[7px] text-sm text-[var(--text-soft)] max-[600px]:text-[13px] max-[600px]:leading-normal">
              You have saved{" "}
              <button
                ref={savedViewRef}
                type="button"
                aria-pressed={localView === "saved"}
                aria-label={`View ${state.saved.length} saved opportunities`}
                className="cursor-pointer rounded-sm text-[var(--text)] underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
                onClick={() => setLocalView("saved")}
              >
                {state.saved.length}
              </button>{" "}
              {state.saved.length === 1 ? "opportunity" : "opportunities"}, marked{" "}
              <button
                ref={appliedViewRef}
                type="button"
                aria-pressed={localView === "applied"}
                aria-label={`View ${state.applied.length} applied opportunities`}
                className="cursor-pointer rounded-sm text-[var(--text)] underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
                onClick={() => setLocalView("applied")}
              >
                {state.applied.length}
              </button>{" "}
              {state.applied.length === 1 ? "opportunity" : "opportunities"} as applied, and hidden{" "}
              <button
                ref={hiddenViewRef}
                type="button"
                aria-pressed={localView === "hidden"}
                aria-label={`View ${state.hidden.length} hidden opportunities`}
                className="cursor-pointer rounded-sm text-[var(--text)] underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
                onClick={() => setLocalView("hidden")}
              >
                {state.hidden.length}
              </button>
              .{" "}
              <button
                ref={allViewRef}
                type="button"
                aria-pressed={localView === "all"}
                className="cursor-pointer rounded-sm text-[var(--text)] underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
                onClick={() => setLocalView("all")}
              >
                View all opportunities
              </button>
              .
            </p>
          ) : null}
          {state && newCount > 0 ? (
            <p className="mt-[7px] text-sm text-[var(--text-soft)] max-[600px]:text-[13px] max-[600px]:leading-normal">
              We found <span className="text-[var(--text)]">{newCount}</span> new{" "}
              {newCount === 1 ? "opportunity" : "opportunities"} since your last visit.{" "}
              <button
                type="button"
                aria-pressed={localView === "new"}
                className="cursor-pointer rounded-sm text-[var(--text)] underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
                onClick={() => setLocalView("new")}
              >
                View new opportunities
              </button>
              .
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2 max-[1090px]:w-full max-[480px]:flex-wrap max-[400px]:flex-nowrap">
          {(["csv", "json"] as const).map((format) => (
            <a
              key={format}
              aria-label={`Download ${format.toUpperCase()}`}
              className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 text-[12px] font-medium whitespace-nowrap text-[var(--text)] shadow-[0_1px_2px_rgb(0_0_0/3%)] transition-colors duration-150 hover:bg-[var(--surface-hover)] [&_svg]:size-3.5"
              href={`/open-opportunities.${format}`}
              download
            >
              <Download aria-hidden="true" />
              <span className="max-[400px]:hidden">Download </span>
              {format.toUpperCase()}
            </a>
          ))}
          <Badge
            className="min-h-8 gap-1.5 rounded-md px-2.5 py-0 max-[1090px]:ml-auto"
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
        localState={state}
        onToggle={(field, id) => {
          // Move focus before a local action can remove its own row from the current list.
          if (field === "hidden") {
            (localView === "hidden" ? allViewRef : hiddenViewRef).current?.focus();
          }
          if (field === "saved" && localView === "saved") savedViewRef.current?.focus();
          if (field === "applied" && localView === "applied") appliedViewRef.current?.focus();
          toggle(field, id);
        }}
        localView={localView}
        newIds={newIds}
      />
    </section>
  );
}
