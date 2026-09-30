"use client";

import {useEffect, useRef, useState} from "react";
import {createPortal} from "react-dom";
import {Bookmark, Check, Ellipsis, Eye, EyeOff} from "lucide-react";
import {Button} from "@/components/ui/button";
import type {Opportunity} from "@/types/opportunity";

type ActionProps = {
  opportunity: Opportunity;
  saved: boolean;
  applied: boolean;
  hidden: boolean;
  disabled: boolean;
  onToggle: (field: "saved" | "applied" | "hidden", id: string) => void;
};

export function OpportunityActions({
  opportunity,
  saved,
  applied,
  hidden,
  disabled,
  onToggle,
}: ActionProps) {
  const [position, setPosition] = useState<{left: number; top?: number; bottom?: number} | null>(
    null
  );
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const name = `${opportunity.title} at ${opportunity.company}`;

  function toggleAndKeepFocus(field: "saved" | "applied") {
    onToggle(field, opportunity.linkedinJobId);
    // Table cells can be remounted when local state changes. Restore keyboard
    // focus to the same action if the row remains in the current view.
    requestAnimationFrame(() => {
      document
        .querySelector<HTMLButtonElement>(
          `[data-local-id="${opportunity.linkedinJobId}"][data-local-action="${field}"]`
        )
        ?.focus();
    });
  }

  useEffect(() => {
    if (!position) return;
    menuRef.current?.querySelector("button")?.focus({preventScroll: true});
    function dismiss(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !triggerRef.current?.contains(event.target) &&
        !menuRef.current?.contains(event.target)
      )
        setPosition(null);
    }
    function dismissOnFocus(event: FocusEvent) {
      if (
        event.target instanceof Node &&
        !triggerRef.current?.contains(event.target) &&
        !menuRef.current?.contains(event.target)
      )
        setPosition(null);
    }
    function restoreFocusAndDismiss() {
      if (menuRef.current?.contains(document.activeElement)) {
        triggerRef.current?.focus({preventScroll: true});
      }
      setPosition(null);
    }
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setPosition(null);
        triggerRef.current?.focus({preventScroll: true});
      } else if (event.key === "Tab") {
        // The portal is at the end of the document. Resume normal tab order
        // from its trigger rather than jumping to the browser toolbar.
        restoreFocusAndDismiss();
      }
    }
    const dismissOnScroll = restoreFocusAndDismiss;
    // Opening the menu may finish scrolling the trigger into view. Ignore that
    // initial browser scroll; subsequent page/table scrolling dismisses it.
    const scrollTimer = window.setTimeout(() => {
      window.addEventListener("scroll", dismissOnScroll, true);
    }, 150);
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("focusin", dismissOnFocus);
    window.addEventListener("resize", restoreFocusAndDismiss);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      window.clearTimeout(scrollTimer);
      window.removeEventListener("scroll", dismissOnScroll, true);
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("focusin", dismissOnFocus);
      window.removeEventListener("resize", restoreFocusAndDismiss);
    };
  }, [position]);

  return (
    <div className="flex items-center gap-0.5 whitespace-nowrap">
      <Button
        variant="ghost"
        size="icon"
        className="size-8 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
        disabled={disabled}
        aria-label={`${saved ? "Unsave" : "Save"} ${name}`}
        title={saved ? "Saved — remove" : "Save"}
        aria-pressed={saved}
        data-local-id={opportunity.linkedinJobId}
        data-local-action="saved"
        onClick={() => toggleAndKeepFocus("saved")}
      >
        <Bookmark aria-hidden="true" fill={saved ? "currentColor" : "none"} />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="size-8 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
        disabled={disabled}
        aria-label={`${applied ? "Unmark applied" : "Mark applied"} ${name}`}
        title={applied ? "Applied — unmark" : "Mark applied"}
        aria-pressed={applied}
        data-local-id={opportunity.linkedinJobId}
        data-local-action="applied"
        onClick={() => toggleAndKeepFocus("applied")}
      >
        <Check
          aria-hidden="true"
          className={applied ? "text-[var(--text)]" : "opacity-50"}
          strokeWidth={applied ? 3 : 2}
        />
      </Button>
      <Button
        ref={triggerRef}
        variant="ghost"
        size="icon"
        className="size-8 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
        disabled={disabled}
        aria-label={`More actions for ${name}`}
        title="More actions"
        aria-expanded={Boolean(position)}
        aria-haspopup="menu"
        onClick={() => {
          if (position) {
            setPosition(null);
            return;
          }
          const bounds = triggerRef.current?.getBoundingClientRect();
          const cellBounds = triggerRef.current?.closest("td")?.getBoundingClientRect();
          if (bounds && cellBounds)
            setPosition({
              // Anchor to the column, not the rightmost icon (which can shift on mobile).
              left: Math.min(
                window.innerWidth - 60,
                Math.max(60, (cellBounds.left + cellBounds.right) / 2)
              ),
              // Near the fixed header, keep the menu below the trigger so it
              // remains reachable without scrolling under the header.
              ...(bounds.top < 130
                ? {top: bounds.bottom}
                : {bottom: window.innerHeight - bounds.top}),
            });
        }}
      >
        <Ellipsis aria-hidden="true" />
      </Button>
      {position &&
        createPortal(
          <div
            ref={menuRef}
            role="menu"
            aria-label={`More actions for ${name}`}
            style={{
              left: position.left,
              top: position.top,
              bottom: position.bottom,
              transform: "translateX(-50%)",
            }}
            className="fixed z-40 rounded-md border border-[var(--border)] bg-[var(--surface)] p-1 shadow-md"
          >
            <button
              type="button"
              role="menuitem"
              className="flex h-8 cursor-pointer items-center gap-2 rounded-md px-2 text-[13px] text-[var(--text)] hover:bg-[var(--surface-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--text)]"
              aria-label={`${hidden ? "Restore" : "Hide"} ${name}`}
              onClick={() => {
                setPosition(null);
                onToggle("hidden", opportunity.linkedinJobId);
              }}
            >
              {hidden ? (
                <Eye aria-hidden="true" className="size-4" />
              ) : (
                <EyeOff aria-hidden="true" className="size-4" />
              )}
              {hidden ? "Restore" : "Hide"}
            </button>
          </div>,
          document.body
        )}
    </div>
  );
}
