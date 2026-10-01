import {describe, expect, test} from "bun:test";
import {contentEtag, matchesIfNoneMatch} from "@/lib/http-cache";

describe("conditional HTTP caching", () => {
  test("strong ETags depend only on response content", () => {
    const tag = contentEtag("response");
    expect(tag).toMatch(/^"[0-9a-f]{64}"$/);
    expect(tag).toBe(contentEtag("response"));
    expect(tag).not.toBe(contentEtag("different response"));
  });

  test.each([
    [null, false],
    ["", false],
    ['"different"', false],
    ['W/"different"', false],
    ["*", true],
    ['"tag"', true],
    ['W/"tag"', true],
    [' "other", W/"tag" ', true],
  ])("matches If-None-Match %j: %j", (header, matches) => {
    expect(matchesIfNoneMatch(header, '"tag"')).toBe(matches);
  });
});
