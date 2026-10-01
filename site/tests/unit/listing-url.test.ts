import {expect, test} from "bun:test";
import {isCanonicalListingUrl} from "@/lib/listing-url";

const jobId = "1000000001";

test("accepts only the canonical HTTPS LinkedIn listing matching the job ID", () => {
  expect(isCanonicalListingUrl(`https://www.linkedin.com/jobs/view/${jobId}`, jobId)).toBe(true);

  // Reject safe but noncanonical spellings too: consumers do not repair stored URLs.
  const rejectedUrls = [
    "https://www.linkedin.com/jobs/view/1000000002",
    `http://www.linkedin.com/jobs/view/${jobId}`,
    `https://linkedin.com/jobs/view/${jobId}`,
    `https://user@www.linkedin.com/jobs/view/${jobId}`,
    `https://www.linkedin.com/jobs/view/${jobId}?tracking=1`,
    `https://www.linkedin.com/jobs/view/${jobId}#details`,
    `https://www.linkedin.com/jobs/view/${jobId}?`,
    `https://www.linkedin.com/jobs/view/${jobId}#`,
    `https://www.linkedin.com:443/jobs/view/${jobId}`,
    `HTTPS://WWW.LINKEDIN.COM/jobs/view/${jobId}`,
    ` https://www.linkedin.com/jobs/view/${jobId}`,
    `https://www.linkedin.com/jobs/view/${jobId}\n`,
    `https://www.linke\tdin.com/jobs/view/${jobId}`,
    `https://www.linkedin.com/jobs/extra/../view/${jobId}`,
    `https://www.linkedin.com\\jobs\\view\\${jobId}`,
    "javascript:alert(1)",
    "not-a-url",
  ];

  for (const url of rejectedUrls) {
    expect(isCanonicalListingUrl(url, jobId)).toBe(false);
  }

  for (const invalidId of ["", "not-numeric", "1".repeat(31), `${jobId}\n`, "١٢٣"]) {
    expect(
      isCanonicalListingUrl(`https://www.linkedin.com/jobs/view/${invalidId}`, invalidId)
    ).toBe(false);
  }
});
