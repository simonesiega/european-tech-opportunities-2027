import {describe, expect, test} from "bun:test";
import {filterOpportunities, type OpportunityFilters} from "@/lib/opportunity-filter";
import type {Opportunity} from "@/types/opportunity";

const opportunity: Opportunity = {
  linkedinJobId: "100",
  company: "Acme",
  title: "Software Intern 2027",
  location: "Berlin, Germany; Paris, France",
  link: "https://www.linkedin.com/jobs/view/100",
  category: "software-engineering",
  industries: null,
  employmentType: "internship",
  startDate: null,
  firstSeenAt: "2026-07-17T12:00:00Z",
};
const filters: OpportunityFilters = {
  q: "",
  company: "",
  country: "",
  category: "",
  type: "",
  firstSeen: "",
};
const referenceTimestamp = Date.parse(opportunity.firstSeenAt);

describe("shared opportunity filtering", () => {
  test("empty filters preserve every row and its order without mutating the input", () => {
    const rows = [opportunity, {...opportunity, linkedinJobId: "101"}];
    const original = structuredClone(rows);
    const result = filterOpportunities(rows, filters, referenceTimestamp);
    expect(result).toEqual(rows);
    expect(rows).toEqual(original);
  });

  test("search spans nonempty fields with normalized case and surrounding whitespace", () => {
    expect(
      filterOpportunities(
        [opportunity],
        {...filters, q: "  SOFTWARE-ENGINEERING INTERNSHIP  "},
        referenceTimestamp
      )
    ).toEqual([opportunity]);
    expect(
      filterOpportunities(
        [{...opportunity, industries: "Robotics"}],
        {...filters, q: "robotics"},
        referenceTimestamp
      )
    ).toHaveLength(1);
    expect(
      filterOpportunities([opportunity], {...filters, q: "robotics"}, referenceTimestamp)
    ).toEqual([]);
  });

  test("recency includes both boundaries and excludes old, future, and invalid timestamps", () => {
    const rows = [
      {...opportunity, firstSeenAt: "2026-07-16T12:00:00Z"},
      opportunity,
      {...opportunity, firstSeenAt: "2026-07-16T11:59:59Z"},
      {...opportunity, firstSeenAt: "2026-07-17T12:00:01Z"},
      {...opportunity, firstSeenAt: "invalid"},
    ];
    expect(
      filterOpportunities(rows, {...filters, firstSeen: "24-hours"}, referenceTimestamp)
    ).toEqual(rows.slice(0, 2));
    expect(filterOpportunities(rows, filters, referenceTimestamp)).toEqual(rows);
  });
});
