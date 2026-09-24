import {expect, test} from "bun:test";
import {serializeStructuredData} from "@/lib/structured-data";

test("escapes markup that could terminate the JSON-LD script", () => {
  const serialized = serializeStructuredData({value: "</script><script>alert(1)</script>"});

  expect(serialized).not.toContain("<");
  expect(JSON.parse(serialized)).toEqual({value: "</script><script>alert(1)</script>"});
});
