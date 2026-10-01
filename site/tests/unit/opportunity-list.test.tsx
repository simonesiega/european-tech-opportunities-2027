import {expect, test} from "bun:test";
import {renderToStaticMarkup} from "react-dom/server";
import {OpportunityList} from "@/components/opportunities/opportunity-list";
import {emptyLocalState} from "@/lib/local-opportunity-state";
import {apiPayload, parseApiQuery} from "@/lib/opportunity-api";
import {DIRECTORY_SORTS} from "@/types/directory";
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

test("renders an actionable message only when filters hide every opportunity", () => {
  const emptyDirectory = renderToStaticMarkup(
    <OpportunityList {...commonProps} hasActiveFilters={false} />
  );
  expect(emptyDirectory).toContain("No open opportunities");
  expect(emptyDirectory).toContain("The directory currently has no open roles.");
  expect(emptyDirectory).not.toContain("Reset filters");

  const emptyFilterResult = renderToStaticMarkup(
    <OpportunityList {...commonProps} hasActiveFilters />
  );
  expect(emptyFilterResult).toContain("No opportunities found");
  expect(emptyFilterResult).toContain("Try changing or clearing your filters.");
  expect(emptyFilterResult).toContain("Reset filters");
});

test.each(["saved", "applied", "new", "hidden"] as const)(
  "empty %s lists do not claim the directory has no open roles",
  (localView) => {
    const html = renderToStaticMarkup(
      <OpportunityList {...commonProps} localView={localView} hasActiveFilters={false} />
    );
    expect(html).toContain(`No ${localView} opportunities`);
    expect(html).not.toContain("The directory currently has no open roles.");
    expect(html).not.toContain("Reset filters");
  }
);

test("an all-hidden directory explains where to restore the roles", () => {
  const html = renderToStaticMarkup(
    <OpportunityList
      {...commonProps}
      hasActiveFilters={false}
      localState={{...emptyLocalState("2026-09-28T12:00:00Z"), hidden: ["1"]}}
    />
  );
  expect(html).toContain("No visible opportunities");
  expect(html).toContain("View your hidden opportunities to restore them.");
});

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

test.each([...DIRECTORY_SORTS])("rendered rows follow the API's %s ordering", (sort) => {
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
  expect(renderedIds).toEqual(
    apiPayload(opportunities, null, parseApiQuery(`?sort=${sort}`)).data.map(
      (opportunity) => opportunity.linkedinJobId
    )
  );
  expect(html).toContain('dateTime="2026-07-17T12:00:00.123456+00:00"');
  if (sort === "first-seen-desc") expect(renderedIds).toEqual(["11", "10", "9", "12"]);
  if (sort === "first-seen-asc") expect(renderedIds).toEqual(["12", "10", "9", "11"]);
});
