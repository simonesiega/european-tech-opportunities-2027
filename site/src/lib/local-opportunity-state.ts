import {normalizeOpportunityTimestamp} from "@/lib/opportunity-presentation";
import type {Opportunity} from "@/types/opportunity";

export const LOCAL_STATE_KEY = "opportunities-directory-state";
export type LocalOpportunityView = "all" | "saved" | "applied" | "hidden" | "new";

export type LocalOpportunityState = {
  version: 1;
  lastVisitAt: string;
  previousVisitAt?: string | null;
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
      // Preserve null (no earlier visit) separately from a missing legacy baseline.
      ...(record.previousVisitAt === null ||
      (typeof record.previousVisitAt === "string" &&
        Number.isFinite(Date.parse(record.previousVisitAt)) &&
        Date.parse(record.previousVisitAt) <= Date.parse(record.lastVisitAt))
        ? {previousVisitAt: record.previousVisitAt}
        : {}),
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
  let cutoff: string;
  try {
    cutoff = normalizeOpportunityTimestamp(previousVisit);
  } catch {
    return new Set();
  }
  const ids = new Set<string>();
  for (const item of opportunities) {
    try {
      // Fixed-width UTC strings preserve microseconds at the visit boundary.
      if (normalizeOpportunityTimestamp(item.firstSeenAt) > cutoff) ids.add(item.linkedinJobId);
    } catch {
      // Invalid timestamps are not evidence of a new opportunity.
    }
  }
  return ids;
}

export function selectLocalOpportunities(
  opportunities: Opportunity[],
  state: LocalOpportunityState | null,
  view: LocalOpportunityView,
  newIds: Set<string>
): {visibleOpportunities: Opportunity[]; newCount: number} {
  // Index lists once, rather than scanning stored ID arrays for every directory row.
  const hidden = new Set(state?.hidden);
  let newCount = 0;
  for (const id of newIds) {
    if (!hidden.has(id)) newCount++;
  }
  if (!state || (view === "all" && hidden.size === 0))
    return {visibleOpportunities: opportunities, newCount};

  const selected = view === "saved" || view === "applied" ? new Set(state[view]) : null;
  const visibleOpportunities = opportunities.filter(({linkedinJobId: id}) => {
    if (view === "hidden") return hidden.has(id);
    if (hidden.has(id)) return false;
    if (view === "new") return newIds.has(id);
    return selected === null || selected.has(id);
  });
  return {visibleOpportunities, newCount};
}

// A visit continues across reloads and tabs until 30 minutes of inactivity.
export function resumeLocalVisit(state: LocalOpportunityState, now: string): LocalOpportunityState {
  const continuing =
    state.previousVisitAt !== undefined &&
    Date.parse(now) - Date.parse(state.lastVisitAt) < 30 * 60 * 1000;
  return {
    ...state,
    previousVisitAt: continuing
      ? state.previousVisitAt
      : state.lastVisitAt === now
        ? null
        : state.lastVisitAt,
    lastVisitAt: now,
  };
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
