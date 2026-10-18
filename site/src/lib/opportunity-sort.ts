import {normalizeOpportunityTimestamp} from "@/lib/opportunity-presentation";
import type {DirectorySort} from "@/types/directory";
import type {Opportunity} from "@/types/opportunity";

const TEXT_ORDER = new Intl.Collator("en");
const NUMERIC_ID_ORDER = new Intl.Collator("en", {numeric: true});

// Use the same ordering in the directory and API, without mutating their input rows.
export function sortOpportunities(
  opportunities: Opportunity[],
  sort: DirectorySort
): Opportunity[] {
  const descending = sort.endsWith("-desc");
  const field = sort.replace(/-(asc|desc)$/, "");
  return opportunities
    .map((opportunity) => ({
      opportunity,
      value:
        field === "role"
          ? opportunity.title
          : field === "first-seen"
            ? normalizeOpportunityTimestamp(opportunity.firstSeenAt)
            : field === "company"
              ? opportunity.company
              : opportunity.location,
    }))
    .sort((left, right) => {
      // Fixed-width UTC timestamps retain all six fractional digits. Date.parse
      // would discard microseconds and incorrectly turn distinct times into ties.
      const order =
        field === "first-seen"
          ? left.value < right.value
            ? -1
            : left.value > right.value
              ? 1
              : 0
          : TEXT_ORDER.compare(left.value, right.value);
      return (
        (descending ? -order : order) ||
        NUMERIC_ID_ORDER.compare(right.opportunity.linkedinJobId, left.opportunity.linkedinJobId) ||
        TEXT_ORDER.compare(right.opportunity.linkedinJobId, left.opportunity.linkedinJobId)
      );
    })
    .map(({opportunity}) => opportunity);
}
