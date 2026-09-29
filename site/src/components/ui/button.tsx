import type {ComponentPropsWithRef} from "react";
import {cn} from "@/lib/cn";

type ButtonProps = ComponentPropsWithRef<"button"> & {
  variant: "outline" | "ghost";
  size?: "default" | "sm" | "icon";
};

export function Button({className, variant, size = "default", ...props}: ButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-2 rounded-md border border-transparent text-[13px] font-medium whitespace-nowrap transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-45 [&_svg]:size-[15px]",
        variant === "outline" &&
          "border-[var(--border)] bg-[var(--surface)] text-[var(--text)] shadow-[0_1px_2px_rgb(0_0_0/3%)] hover:not-disabled:bg-[var(--surface-hover)]",
        variant === "ghost" &&
          "bg-transparent text-[var(--text-soft)] hover:not-disabled:bg-[var(--surface-hover)]",
        size === "default" && "h-9 px-3.5",
        size === "sm" && "h-8 px-2.5",
        size === "icon" && "size-[34px] p-0",
        className
      )}
      {...props}
    />
  );
}
