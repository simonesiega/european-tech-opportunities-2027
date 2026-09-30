import {parseOpportunityTimestamp} from "@/lib/opportunity-presentation";
import {repositoryUrl} from "@/lib/project-links";
import {siteConfig} from "@/lib/site-config";

const licenseUrl = "https://spdx.org/licenses/MIT.html";

export function buildStructuredData(siteUrl: URL, lastUpdatedAt: string | null) {
  const directoryUrl = siteUrl.toString();
  const websiteId = `${directoryUrl}#website`;
  const datasetId = `${directoryUrl}#dataset`;
  const updated = lastUpdatedAt ? parseOpportunityTimestamp(lastUpdatedAt) : NaN;

  return {
    "@context": {
      "@vocab": "https://schema.org/",
      dcterms: "http://purl.org/dc/terms/",
    },
    "@graph": [
      {
        "@type": "WebSite",
        "@id": websiteId,
        url: directoryUrl,
        name: siteConfig.name,
        description: siteConfig.description,
        inLanguage: siteConfig.language,
        publisher: {"@id": siteConfig.maintainer.id},
        mainEntity: {"@id": datasetId},
      },
      {
        "@type": "Dataset",
        "@id": datasetId,
        name: `${siteConfig.name} open opportunities dataset`,
        description: siteConfig.description,
        url: directoryUrl,
        sameAs: repositoryUrl,
        inLanguage: siteConfig.language,
        temporalCoverage: siteConfig.cycle,
        spatialCoverage: {"@type": "Place", name: siteConfig.coverage},
        license: licenseUrl,
        isAccessibleForFree: true,
        creator: {"@id": siteConfig.maintainer.id},
        publisher: {"@id": siteConfig.maintainer.id},
        maintainer: {"@id": siteConfig.maintainer.id},
        "dcterms:accrualPeriodicity": {
          "@id": "http://purl.org/cld/freq/daily",
          name: "Daily",
        },
        ...(Number.isFinite(updated) ? {dateModified: new Date(updated).toISOString()} : {}),
        distribution: [
          {
            "@type": "DataDownload",
            encodingFormat: "text/csv",
            contentUrl: new URL("/open-opportunities.csv", directoryUrl).toString(),
          },
          {
            "@type": "DataDownload",
            encodingFormat: "application/json",
            contentUrl: new URL("/open-opportunities.json", directoryUrl).toString(),
          },
        ],
      },
      {
        "@type": "Person",
        "@id": siteConfig.maintainer.id,
        name: siteConfig.maintainer.name,
        url: siteConfig.maintainer.url,
      },
    ],
  };
}

export function serializeStructuredData(value: unknown): string {
  return JSON.stringify(value).replaceAll("<", "\\u003c");
}
