import {expect, test} from "bun:test";
import {
  emptyLocalState,
  newOpportunityIds,
  parseLocalState,
  resumeLocalVisit,
  toggleLocalId,
} from "@/lib/local-opportunity-state";
import type {Opportunity} from "@/types/opportunity";

const now = "2026-09-28T12:00:00.000Z";
const ids = new Set(["123", "456"]);

test("first visit, corrupt, unknown version and future visit reset safely", () => {
  for (const raw of [
    null,
    "{",
    '{"version":2}',
    '{"version":1,"lastVisitAt":"2099-01-01","saved":[],"hidden":[],"applied":[]}',
  ]) {
    expect(parseLocalState(raw, ids, now)).toEqual(emptyLocalState(now));
  }
});

test("retains only current IDs and deduplicates all local lists", () => {
  const state = parseLocalState(
    JSON.stringify({
      version: 1,
      lastVisitAt: "2026-09-27T12:00:00Z",
      saved: ["123", "123", "gone"],
      hidden: ["456", "gone"],
      applied: ["123"],
    }),
    ids,
    now
  );
  expect(state.saved).toEqual(["123"]);
  expect(state.hidden).toEqual(["456"]);
  expect(state.applied).toEqual(["123"]);
  expect(toggleLocalId(state, "saved", "123").saved).toEqual([]);
  expect(toggleLocalId(state, "applied", "456").applied).toEqual(["123", "456"]);
});

test("counts only rows first seen strictly after the previous visit", () => {
  const rows = ["2026-09-27T12:00:00Z", "2026-09-28T11:00:00Z", "2026-09-26T12:00:00Z"].map(
    (firstSeenAt, index) => ({firstSeenAt, linkedinJobId: String(index)}) as Opportunity
  );
  expect(newOpportunityIds(rows, null).size).toBe(0);
  expect([...newOpportunityIds(rows, "2026-09-27T12:00:00Z")]).toEqual(["1"]);
});

test("SQLite timestamps are UTC and compare consistently with ISO offsets", () => {
  const rows = [
    "2026-09-28 12:00:00.000000",
    "2026-09-28 12:00:01.123456",
    "2026-09-28T14:00:01.123456+02:00",
  ].map((firstSeenAt, index) => ({firstSeenAt, linkedinJobId: String(index)}) as Opportunity);
  expect([...newOpportunityIds(rows, "2026-09-28T12:00:00Z")]).toEqual(["1", "2"]);
});
test("visit baseline survives reloads and advances after inactivity", () => {
  const old = {...emptyLocalState("2026-09-27T12:00:00Z"), saved: ["123"]};
  const first = resumeLocalVisit(old, now);
  const reload = resumeLocalVisit(first, "2026-09-28T12:05:00Z");
  expect(reload.previousVisitAt).toBe(old.lastVisitAt);
  expect(reload.saved).toEqual(["123"]);
  expect(resumeLocalVisit(reload, "2026-09-28T12:35:00Z").previousVisitAt).toBe(reload.lastVisitAt);
  const fresh = resumeLocalVisit(emptyLocalState(now), now);
  expect(resumeLocalVisit(fresh, "2026-09-28T12:05:00Z").previousVisitAt).toBeNull();
  expect(parseLocalState(JSON.stringify(reload), ids, "2026-09-28T12:06:00Z")).toEqual(reload);
});
