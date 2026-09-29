"use client";

import {useEffect, useRef, useState} from "react";
import {
  LOCAL_STATE_KEY,
  parseLocalState,
  toggleLocalId,
  type LocalOpportunityState,
} from "@/lib/local-opportunity-state";
import type {Opportunity} from "@/types/opportunity";

export function useLocalOpportunities(opportunities: Opportunity[]) {
  const initialized = useRef(false);
  const currentState = useRef<LocalOpportunityState | null>(null);
  const [state, setState] = useState<LocalOpportunityState | null>(null);
  const [previousVisit, setPreviousVisit] = useState<string | null>(null);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    const now = new Date().toISOString();
    const ids = new Set(opportunities.map((item) => item.linkedinJobId));
    let raw: string | null = null;
    try {
      raw = window.localStorage.getItem(LOCAL_STATE_KEY);
    } catch {
      // Storage may be blocked; the directory still works in memory for this tab.
    }
    const stored = parseLocalState(raw, ids, now);
    // Capture the previous visit before recording this one, so actions and reloads
    // during this visit do not change the displayed new-opportunity count.
    setPreviousVisit(raw && stored.lastVisitAt !== now ? stored.lastVisitAt : null);
    const current = {...stored, lastVisitAt: now};
    currentState.current = current;
    setState(current);
    try {
      window.localStorage.setItem(LOCAL_STATE_KEY, JSON.stringify(current));
    } catch {
      // Private browsing or quota errors must not break the page.
    }
  }, [opportunities]);

  function toggle(field: "saved" | "hidden" | "applied", id: string) {
    if (!opportunities.some((item) => item.linkedinJobId === id)) return;
    if (!currentState.current) return;
    const next = toggleLocalId(currentState.current, field, id);
    currentState.current = next;
    setState(next);
    try {
      window.localStorage.setItem(LOCAL_STATE_KEY, JSON.stringify(next));
    } catch {
      // Keep the action usable in memory even without persistent storage.
    }
  }

  return {state, previousVisit, toggle};
}
