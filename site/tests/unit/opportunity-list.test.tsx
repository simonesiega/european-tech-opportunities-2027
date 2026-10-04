import {expect, test} from "bun:test";
import {renderToStaticMarkup} from "react-dom/server";
import {OpportunityList} from "@/components/opportunities/opportunity-list";
import type {Opportunity} from "@/types/opportunity";

const noOp = () => undefined;
const view = {sort: "first-seen-desc", page: 1, pageSize: 10} as const;
const commonProps = {
  opportunities: [],
  view,
  pageHref: (page: number) => `/?page=${page}`,
  onSortChange: noOp,
  onPageChange: noOp,
  onPageSizeChange: noOp,
  onReset: noOp,
  localState: null,
  onToggle: noOp,
  localView: "all" as const,
  newIds: new Set<string>(),
};

// IDs 9/10 share an instant; 11/12 differ only at microsecond precision.
const opportunities: Opportunity[] = [
  ["9", "2026-07-17T12:00:00.123456Z"],
  ["10", "2026-07-17 12:00:00.123456"],
  ["11", "2026-07-17T14:00:00.123457+02:00"],
  ["12", "2026-07-17T12:00:00.123455+00:00"],
].map(([linkedinJobId, firstSeenAt]) => ({
  linkedinJobId,
  firstSeenAt,
  company: "Example",
  title: "Intern 2027",
  location: "Berlin, Germany",
  link: `https://www.linkedin.com/jobs/view/${linkedinJobId}`,
  category: "software-engineering",
  industries: null,
  employmentType: "internship",
  startDate: null,
}));

// Keep expectations literal so a shared API/UI sorting bug cannot become the test oracle.
test.each([
  ["first-seen-desc", ["11", "10", "9", "12"]],
  ["first-seen-asc", ["12", "10", "9", "11"]],
] as const)("rendered %s rows preserve microseconds and numeric ID ties", (sort, expected) => {
  const html = renderToStaticMarkup(
    <OpportunityList
      {...commonProps}
      view={{...view, sort}}
      opportunities={opportunities}
      hasActiveFilters={false}
    />
  );
  // Each row links through both its arrow and title; count each identity once, in order.
  const renderedIds = [
    ...new Set(
      [...html.matchAll(/href="https:\/\/www.linkedin.com\/jobs\/view\/(\d+)"/g)].map(
        (match) => match[1]
      )
    ),
  ];
  expect(renderedIds).toEqual([...expected]);
  expect(html).toContain('dateTime="2026-07-17T12:00:00.123456+00:00"');
});
