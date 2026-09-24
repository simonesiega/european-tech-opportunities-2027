import type {Metadata} from "next";
import {SiteFooter} from "@/components/layout/site-footer";
import {SiteHeader} from "@/components/layout/site-header";
import {OpportunityDirectory} from "@/components/opportunities/opportunity-directory";
import {getDirectoryData} from "@/lib/opportunities";
import {siteUrl} from "@/lib/site-url";
import {buildStructuredData, serializeStructuredData} from "@/lib/structured-data";
import {DEFAULT_DIRECTORY_PAGE_SIZE} from "@/types/directory";

export const dynamic = "force-dynamic";

type PageSearchParams = Record<string, string | string[] | undefined>;

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}): Promise<Metadata> {
  const parameters = await searchParams;
  const rawPage = parameters.page;
  const page = typeof rawPage === "string" ? Number(rawPage) : 1;
  const validPage =
    rawPage === undefined ||
    (typeof rawPage === "string" && /^[1-9]\d*$/.test(rawPage) && Number.isSafeInteger(page));
  const hasAlternateView = [
    "q",
    "company",
    "country",
    "category",
    "type",
    "first-seen",
    "sort",
    "page-size",
  ].some((parameter) => parameters[parameter] !== undefined);
  const defaultPageCount = Math.max(
    Math.ceil(getDirectoryData().opportunities.length / DEFAULT_DIRECTORY_PAGE_SIZE),
    1
  );
  const indexable = validPage && !hasAlternateView && page <= defaultPageCount;

  return {
    alternates: {canonical: indexable && page > 1 ? `/?page=${page}` : "/"},
    robots: {index: indexable, follow: true},
  };
}

export default function Home() {
  const {opportunities, lastUpdatedAt} = getDirectoryData();
  const referenceTime = new Date().toISOString();
  const structuredData = buildStructuredData(siteUrl, lastUpdatedAt);

  return (
    <div className="mx-auto flex min-h-svh w-[min(calc(100%_-_40px),1376px)] flex-col pt-18 max-[760px]:w-[min(calc(100%_-_28px),1376px)] max-[639px]:pt-22">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{__html: serializeStructuredData(structuredData)}}
      />
      <SiteHeader />
      <main className="flex-1">
        <OpportunityDirectory opportunities={opportunities} referenceTime={referenceTime} />
      </main>
      <SiteFooter lastUpdatedAt={lastUpdatedAt} />
    </div>
  );
}
