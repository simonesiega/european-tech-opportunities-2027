import {ThemeToggle} from "@/components/theme/theme-toggle";
import {cn} from "@/lib/cn";

export function SiteHeader() {
  return (
    <div className="fixed inset-x-0 top-0 z-50 bg-[var(--header-overlay)] backdrop-blur-[28px] backdrop-saturate-[1.2] transition-colors duration-300 after:pointer-events-none after:absolute after:inset-x-0 after:-bottom-4 after:h-4 after:bg-linear-to-b after:from-[var(--header-overlay)] after:to-transparent after:[mask-image:linear-gradient(to_bottom,black,transparent)] after:backdrop-blur-xl after:content-['']">
      <header className="min-h-18 w-full border-b border-[var(--border)] max-[639px]:min-h-22">
        <div className="mx-auto flex min-h-18 w-[min(calc(100%_-_40px),1376px)] items-center justify-between max-[760px]:w-[min(calc(100%_-_28px),1376px)] max-[639px]:min-h-22">
          <p className="text-xl leading-none font-[550] tracking-[-0.025em] max-[639px]:text-lg max-[520px]:max-w-[130px] max-[520px]:overflow-hidden max-[520px]:text-[15px] max-[520px]:leading-[1.2] max-[520px]:text-ellipsis max-[520px]:whitespace-nowrap">
            Opportunities ’27
          </p>
          <div className="flex items-center gap-8 max-[520px]:gap-2.5">
            <a
              className="flex items-center text-base leading-none font-medium text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)] max-[520px]:text-[13px]"
              href="https://github.com/simonesiega/european-tech-opportunities-27/issues/new?template=add-position.yml"
              target="_blank"
              rel="noreferrer"
            >
              <span className="max-[520px]:hidden">Add a position</span>
              <span className="hidden max-[520px]:inline">Add</span>
            </a>
            <a
              className={cn(
                "flex items-center text-base leading-none font-medium text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)] max-[520px]:text-[13px]",
                "gap-1"
              )}
              href="https://github.com/simonesiega/european-tech-opportunities-27"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
              <svg
                className="w-3.5 fill-none stroke-current [stroke-width:1.4] [stroke-linecap:round] [stroke-linejoin:round]"
                aria-hidden="true"
                viewBox="0 0 16 16"
              >
                <path d="M5 11 11 5M6 5h5v5" />
              </svg>
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>
    </div>
  );
}
