import {SiteFooter} from "@/components/layout/site-footer";
import {SiteHeader} from "@/components/layout/site-header";
import {OpportunityDirectory} from "@/components/opportunities/opportunity-directory";
import {getDirectoryData} from "@/lib/internships";

export const dynamic = "force-dynamic";

export default function Home() {
  const {opportunities, lastUpdatedAt} = getDirectoryData();

  return (
    <div className="mx-auto flex min-h-svh w-[min(calc(100%_-_40px),1376px)] flex-col pt-18 max-[760px]:w-[min(calc(100%_-_28px),1376px)] max-[639px]:pt-22">
      <SiteHeader />
      <main className="flex-1">
        <OpportunityDirectory opportunities={opportunities} />
      </main>
      <SiteFooter lastUpdatedAt={lastUpdatedAt} />
    </div>
  );
}
