import {formatOpportunityDate} from "@/lib/opportunity-presentation";
import {addPositionUrl, newIssueUrl, repositoryUrl} from "@/lib/project-links";
import {siteConfig} from "@/lib/site-config";

type SiteFooterProps = {
  lastUpdatedAt: string | null;
};

export function SiteFooter({lastUpdatedAt}: SiteFooterProps) {
  return (
    <footer className="flex min-h-16 items-center justify-between gap-8 border-t border-[var(--border)] py-3 text-[13px] leading-[1.45] text-[var(--text-faint)] max-[680px]:flex-col max-[680px]:items-start max-[680px]:gap-3 max-[680px]:py-[18px]">
      <div className="flex flex-col gap-0.5">
        <strong className="font-semibold text-[var(--text)]">{siteConfig.shortName}</strong>
        <span>{siteConfig.description}</span>
      </div>

      <div className="flex flex-col items-end gap-0.5 text-right max-[680px]:items-start max-[680px]:text-left">
        <nav className="flex items-center gap-1.5 max-[680px]:flex-wrap" aria-label="Project links">
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href={addPositionUrl}
            target="_blank"
            rel="noreferrer"
          >
            Contribute
          </a>
          <span aria-hidden="true">·</span>
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href="/api/v1/opportunities"
          >
            Public API
          </a>
          <span aria-hidden="true">·</span>
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href="/feed.xml"
          >
            RSS feed
          </a>
          <span aria-hidden="true">·</span>
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href="/atom.xml"
          >
            Atom feed
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
            href="https://docs.techopportunities.eu/docs/users/index.html"
          >
            Help
          </a>
          <span aria-hidden="true">·</span>
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href="https://docs.techopportunities.eu/PRIVACY.html"
          >
            Privacy
          </a>
          <span aria-hidden="true">·</span>
          <a
            className="text-[var(--text-soft)] transition-colors duration-180 hover:text-[var(--text)]"
            href={newIssueUrl}
            target="_blank"
            rel="noreferrer"
          >
            Report an issue
          </a>
        </nav>
        <span>
          Last successful collection:{" "}
          {lastUpdatedAt ? formatOpportunityDate(lastUpdatedAt) : "Not available"}
        </span>
      </div>
    </footer>
  );
}
