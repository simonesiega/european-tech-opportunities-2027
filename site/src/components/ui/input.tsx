import type {ComponentPropsWithRef} from "react";
import {cn} from "@/lib/cn";

export function Input({className, ...props}: ComponentPropsWithRef<"input">) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-[13px] text-[var(--text)] shadow-[0_1px_2px_rgb(0_0_0/3%)] outline-none placeholder:text-[var(--text-faint)] focus:border-[var(--text-faint)] focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--text)_9%,transparent)]",
        className
      )}
      {...props}
    />
  );
}
