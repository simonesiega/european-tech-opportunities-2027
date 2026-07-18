import {formatPublishedDate} from "@/lib/opportunity-presentation";

const repositoryUrl = "https://github.com/simonesiega/european-tech-opportunities-27";

type SiteFooterProps = {
  lastUpdatedAt: string | null;
};

export function SiteFooter({lastUpdatedAt}: SiteFooterProps) {
  return (
    <footer className="flex min-h-16 items-center justify-between gap-8 border-t border-[var(--border)] py-3 text-[13px] leading-[1.45] text-[var(--text-faint)] max-[680px]:flex-col max-[680px]:items-start max-[680px]:gap-3 max-[680px]:py-[18px]">
      <div className="flex flex-col gap-0.5">
        <strong className="font-semibold text-[var(--text)]">Opportunities ’27</strong>
        <span>Discover open 2027 tech internships and New Grad roles across Europe.</span>
      </div>

      <div className="flex flex-col items-end gap-0.5 text-right max-[680px]:items-start max-[680px]:text-left">
        <nav className="flex items-center gap-1.5 max-[680px]:flex-wrap" aria-label="Project links">
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href={`${repositoryUrl}/issues/new?template=add-position.yml`}
            target="_blank"
            rel="noreferrer"
          >
            Contribute
          </a>
          <span aria-hidden="true">·</span>
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href={repositoryUrl}
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <span aria-hidden="true">·</span>
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href={`${repositoryUrl}/issues/new`}
            target="_blank"
            rel="noreferrer"
          >
            Report an issue
          </a>
        </nav>
        <span>
          Last updated: {lastUpdatedAt ? formatPublishedDate(lastUpdatedAt) : "Not available"}
        </span>
      </div>
    </footer>
  );
}
