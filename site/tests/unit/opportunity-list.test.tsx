import {expect, test} from "bun:test";
import {renderToStaticMarkup} from "react-dom/server";
import {OpportunityList} from "@/components/opportunities/opportunity-list";

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
