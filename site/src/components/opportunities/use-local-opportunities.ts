"use client";

import {useLayoutEffect, useMemo, useRef, useState} from "react";
import {
  LOCAL_STATE_KEY,
  parseLocalState,
  resumeLocalVisit,
  toggleLocalId,
  type LocalOpportunityState,
} from "@/lib/local-opportunity-state";
import type {Opportunity} from "@/types/opportunity";

export function useLocalOpportunities(opportunities: Opportunity[]) {
  const ids = useMemo(
    () => new Set(opportunities.map((item) => item.linkedinJobId)),
    [opportunities]
  );
  const currentState = useRef<LocalOpportunityState | null>(null);
  const storageAvailable = useRef(true);
  const [state, setState] = useState<LocalOpportunityState | null>(null);

  function publish(next: LocalOpportunityState) {
    currentState.current = next;
    setState(next);
    try {
      window.localStorage.setItem(LOCAL_STATE_KEY, JSON.stringify(next));
    } catch {
      // Preserve subsequent in-memory actions instead of rereading an older stored value.
      storageAvailable.current = false;
    }
  }

  // Keep SSR deterministic, then restore private lists before hydration's next paint.
  useLayoutEffect(() => {
    const now = new Date().toISOString();
    let raw = currentState.current ? JSON.stringify(currentState.current) : null;
    if (storageAvailable.current) {
      try {
        raw = window.localStorage.getItem(LOCAL_STATE_KEY);
      } catch {
        storageAvailable.current = false;
      }
    }
    const stored = parseLocalState(raw, ids, now);
    publish(currentState.current ? stored : resumeLocalVisit(stored, now));

    function synchronize(event: StorageEvent) {
      if (!storageAvailable.current || (event.key !== LOCAL_STATE_KEY && event.key !== null))
        return;
      try {
        if (event.storageArea !== window.localStorage) return;
        // Read current storage: an older queued event must not undo a newer local action.
        const next = parseLocalState(
          window.localStorage.getItem(LOCAL_STATE_KEY),
          ids,
          new Date().toISOString()
        );
        // No write on receipt: synchronization is not visitor activity or a feedback loop.
        currentState.current = next;
        setState(next);
      } catch {
        storageAvailable.current = false;
      }
    }
    window.addEventListener("storage", synchronize);
    return () => window.removeEventListener("storage", synchronize);
  }, [ids]);

  function toggle(field: "saved" | "hidden" | "applied", id: string) {
    if (!ids.has(id) || !currentState.current) return;
    const now = new Date().toISOString();
    let latest = currentState.current;
    if (storageAvailable.current) {
      try {
        // Another tab may have written before its storage event reached this tab.
        latest = parseLocalState(window.localStorage.getItem(LOCAL_STATE_KEY), ids, now);
      } catch {
        storageAvailable.current = false;
      }
    }
    publish({...toggleLocalId(latest, field, id), lastVisitAt: now});
  }

  return {state, previousVisit: state?.previousVisitAt ?? null, toggle};
}
