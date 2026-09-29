import type {Opportunity} from "@/types/opportunity";

export const LOCAL_STATE_KEY = "opportunities-directory-state";

export type LocalOpportunityState = {
  version: 1;
  lastVisitAt: string;
  saved: string[];
  hidden: string[];
  applied: string[];
};

export function emptyLocalState(now: string): LocalOpportunityState {
  return {version: 1, lastVisitAt: now, saved: [], hidden: [], applied: []};
}

export function parseLocalState(
  raw: string | null,
  ids: Set<string>,
  now: string
): LocalOpportunityState {
  if (!raw) return emptyLocalState(now);
  try {
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object" || !("version" in value) || value.version !== 1)
      return emptyLocalState(now);
    const record = value as Record<string, unknown>;
    if (
      typeof record.lastVisitAt !== "string" ||
      !Number.isFinite(Date.parse(record.lastVisitAt)) ||
      Date.parse(record.lastVisitAt) > Date.parse(now) ||
      ![record.saved, record.hidden, record.applied].every(
        (entries) => Array.isArray(entries) && entries.every((id) => typeof id === "string")
      )
    )
      return emptyLocalState(now);
    const keep = (entries: unknown) => [
      ...new Set((entries as string[]).filter((id) => ids.has(id))),
    ];
    return {
      version: 1,
      lastVisitAt: record.lastVisitAt,
      saved: keep(record.saved),
      hidden: keep(record.hidden),
      applied: keep(record.applied),
    };
  } catch {
    return emptyLocalState(now);
  }
}

export function newOpportunityIds(
  opportunities: Opportunity[],
  previousVisit: string | null
): Set<string> {
  if (!previousVisit) return new Set();
  const cutoff = Date.parse(previousVisit);
  return new Set(
    opportunities
      .filter((item) => {
        const seen = Date.parse(item.firstSeenAt);
        return Number.isFinite(seen) && seen > cutoff;
      })
      .map((item) => item.linkedinJobId)
  );
}

export function toggleLocalId(
  state: LocalOpportunityState,
  field: "saved" | "hidden" | "applied",
  id: string
): LocalOpportunityState {
  const entries = state[field];
  return {
    ...state,
    [field]: entries.includes(id) ? entries.filter((entry) => entry !== id) : [...entries, id],
  };
}
