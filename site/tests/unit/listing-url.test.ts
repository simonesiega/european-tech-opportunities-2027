import {expect, test} from "bun:test";
import {isCanonicalListingUrl} from "@/lib/listing-url";

test("accepts only the HTTPS LinkedIn listing that matches the canonical job ID", () => {
  expect(isCanonicalListingUrl("https://www.linkedin.com/jobs/view/1000000001", "1000000001")).toBe(
    true
  );
  expect(isCanonicalListingUrl("https://www.linkedin.com/jobs/view/1000000002", "1000000001")).toBe(
    false
  );
  expect(isCanonicalListingUrl("http://www.linkedin.com/jobs/view/1000000001", "1000000001")).toBe(
    false
  );
  expect(isCanonicalListingUrl("javascript:alert(1)", "1000000001")).toBe(false);
});
