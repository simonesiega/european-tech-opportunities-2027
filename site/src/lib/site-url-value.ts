const DEFAULT_SITE_URL = "http://localhost:3000";
const INVALID_SITE_URL_MESSAGE =
  "SITE_URL must be an HTTP(S) origin without credentials, a path, query, or fragment; the legacy domain is forbidden and the production domain requires HTTPS without a custom port";

export function parseSiteUrl(value: string | undefined): URL {
  let url: URL;
  try {
    url = new URL(value ?? DEFAULT_SITE_URL);
  } catch {
    throw new Error(INVALID_SITE_URL_MESSAGE);
  }

  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash ||
    url.hostname === "opportunities2027.simonesiega.com" ||
    (url.hostname === "techopportunities.eu" && url.origin !== "https://techopportunities.eu")
  ) {
    throw new Error(INVALID_SITE_URL_MESSAGE);
  }

  return url;
}
