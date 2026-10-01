import {getCountries, parseOpportunityTimestamp} from "@/lib/opportunity-presentation";
import {FIRST_SEEN_OPTIONS} from "@/types/directory";
import type {Opportunity} from "@/types/opportunity";

export type OpportunityFilters = {
  q: string;
  company: string;
  country: string;
  category: string;
  type: string;
  firstSeen: string;
};

// Shared by the interactive directory and the public API; no lifecycle decisions here.
export function filterOpportunities(
  opportunities: Opportunity[],
  filters: OpportunityFilters,
  referenceTimestamp: number
): Opportunity[] {
  const query = filters.q.trim().toLowerCase();
  const period = FIRST_SEEN_OPTIONS.find((option) => option.value === filters.firstSeen);
  const cutoff = period ? referenceTimestamp - period.durationMs : null;

  return opportunities.filter((opportunity) => {
    if (
      (filters.company && opportunity.company !== filters.company) ||
      (filters.category && opportunity.category !== filters.category) ||
      (filters.type && opportunity.employmentType !== filters.type) ||
      (filters.country && !getCountries(opportunity.location).includes(filters.country))
    ) {
      return false;
    }

    if (query) {
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
      if (!searchableText.includes(query)) return false;
    }

    if (cutoff === null) return true;
    const firstSeen = parseOpportunityTimestamp(opportunity.firstSeenAt);
    return firstSeen >= cutoff && firstSeen <= referenceTimestamp;
  });
}
