const LINKEDIN_LISTING_HOST = "www.linkedin.com";

export function isCanonicalListingUrl(value: string, linkedinJobId: string): boolean {
  if (!/^[0-9]{1,30}$/.test(linkedinJobId)) {
    return false;
  }
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      url.hostname === LINKEDIN_LISTING_HOST &&
      url.port === "" &&
      url.username === "" &&
      url.password === "" &&
      url.pathname === `/jobs/view/${linkedinJobId}` &&
      url.search === "" &&
      url.hash === ""
    );
  } catch {
    return false;
  }
}
