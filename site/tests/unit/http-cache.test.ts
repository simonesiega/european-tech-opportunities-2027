import {describe, expect, test} from "bun:test";
import {matchesIfNoneMatch} from "@/lib/http-cache";

describe("conditional HTTP caching", () => {
  // GET revalidation uses weak comparison, so W/ and strong tags can match the same content.
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
