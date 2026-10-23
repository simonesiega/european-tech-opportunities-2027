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

test("new rows preserve microsecond boundaries across UTC, SQLite and offset timestamps", () => {
  const rows = [
    "2026-09-28T12:00:00.122999Z",
    "2026-09-28 12:00:00.123000",
    "2026-09-28T14:00:00.123000+02:00",
    "2026-09-28 12:00:00.123001",
    "2026-09-28T14:00:00.123999+02:00",
    "2026-09-28T12:00:00.124000Z",
    "not a date",
    "2026-02-30T12:00:00Z",
  ].map((firstSeenAt, index) => ({firstSeenAt, linkedinJobId: String(index)}) as Opportunity);
  const original = structuredClone(rows);
  for (const cutoff of ["2026-09-28T12:00:00.123Z", "2026-09-28T14:00:00.123000+02:00"]) {
    expect([...newOpportunityIds(rows, cutoff)]).toEqual(["3", "4", "5"]);
  }
  expect([...newOpportunityIds(rows, "2026-09-28T12:00:00.123500Z")]).toEqual(["4", "5"]);
  expect(rows).toEqual(original);
});

test("invalid previous-visit evidence never invents new rows", () => {
  const rows = [{firstSeenAt: "2026-03-03T12:00:00Z", linkedinJobId: "123"} as Opportunity];
  for (const cutoff of [null, "", "not a date", "2026-02-30T12:00:00Z"]) {
    expect([...newOpportunityIds(rows, cutoff)]).toEqual([]);
  }
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
