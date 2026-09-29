import {expect, test} from "bun:test";
import {renderToStaticMarkup} from "react-dom/server";
import {OpportunityActions} from "@/components/opportunities/opportunity-actions";
import type {Opportunity} from "@/types/opportunity";

const opportunity = {linkedinJobId: "123", title: "Intern", company: "Example"} as Opportunity;

test("compact row actions expose stateful labels and pressed semantics", () => {
  const markup = renderToStaticMarkup(
    <OpportunityActions
      opportunity={opportunity}
      saved
      applied
      hidden={false}
      disabled={false}
      onToggle={() => undefined}
    />
  );
  expect(markup).toContain('aria-label="Unsave Intern at Example"');
  expect(markup).toContain('aria-label="Unmark applied Intern at Example"');
  expect(markup).toContain('aria-pressed="true"');
  expect(markup).toContain('aria-label="More actions for Intern at Example"');
  expect(markup).not.toContain('aria-label="Hide Intern at Example"');
});
