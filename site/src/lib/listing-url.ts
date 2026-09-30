const LINKEDIN_LISTING_HOST = "www.linkedin.com";

export function isCanonicalListingUrl(value: string, linkedinJobId: string): boolean {
  // These values are published verbatim. URL parsing would silently accept
  // whitespace, default ports, dot segments, and other noncanonical spellings.
  return (
    /^[0-9]{1,30}$/.test(linkedinJobId) &&
    value === `https://${LINKEDIN_LISTING_HOST}/jobs/view/${linkedinJobId}`
  );
}
