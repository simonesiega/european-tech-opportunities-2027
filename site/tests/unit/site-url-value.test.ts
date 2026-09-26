import {describe, expect, test} from "bun:test";
import {parseSiteUrl} from "@/lib/site-url-value";

describe("site URL validation", () => {
  test("accepts canonical HTTP and HTTPS origins", () => {
    expect(parseSiteUrl(undefined).toString()).toBe("http://localhost:3000/");
    expect(parseSiteUrl("https://techopportunities.eu").toString()).toBe(
      "https://techopportunities.eu/"
    );
  });

  test("rejects values that are unsafe or are not origins", () => {
    const invalidValues = [
      "not-a-url",
      "ftp://example.com",
      "https://user@example.com",
      "https://example.com/directory",
      "https://example.com/?source=test",
      "https://example.com/#directory",
      "https://opportunities2027.simonesiega.com",
      "http://techopportunities.eu",
      "https://techopportunities.eu:8443",
    ];

    for (const value of invalidValues) {
      expect(() => parseSiteUrl(value)).toThrow("SITE_URL must be an HTTP(S) origin");
    }
  });
});
