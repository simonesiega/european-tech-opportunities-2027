import "server-only";

import {DatabaseSync} from "node:sqlite";
import {cache} from "react";
import {isCanonicalListingUrl} from "@/lib/listing-url";
import {publicationPaths} from "@/lib/release-path";
import type {Opportunity} from "@/types/opportunity";

export function readDirectorySummary(database: DatabaseSync): {
  lastUpdatedAt: string | null;
  opportunities: number;
} {
  // One statement gives both aggregates the same SQLite read snapshot.
  return database
    .prepare(
      `
    SELECT
      (SELECT MAX(finished_at) FROM search_runs WHERE status = 'success') AS lastUpdatedAt,
      (SELECT COUNT(*) FROM jobs WHERE status = 'open') AS opportunities
  `
    )
    .get() as {lastUpdatedAt: string | null; opportunities: number};
}

const OPEN_OPPORTUNITIES_QUERY = `
  SELECT
    linkedin_job_id AS linkedinJobId,
    company,
    title,
    location,
    link,
    category,
    industries,
    employment_type AS employmentType,
    start_date AS startDate,
    first_seen_at AS firstSeenAt
  FROM jobs
  WHERE status = 'open'
  ORDER BY first_seen_at DESC, linkedin_job_id DESC
`;

type DirectoryData = {
  opportunities: Opportunity[];
  lastUpdatedAt: string | null;
};

// Metadata and the page share one read of the selected release per request.
export const getDirectoryData = cache(function getDirectoryData(): DirectoryData {
  const {databasePath} = publicationPaths();
  const database = new DatabaseSync(databasePath, {readOnly: true});

  try {
    // Fixed-path deployments can have an active writer. Pin both reads to one
    // SQLite snapshot so the collection timestamp cannot describe different rows.
    database.exec("BEGIN");
    const {lastUpdatedAt} = readDirectorySummary(database);
    const rows = database.prepare(OPEN_OPPORTUNITIES_QUERY).all() as Opportunity[];
    database.exec("COMMIT");

    // node:sqlite rows have a null prototype and cannot cross the Server Component boundary.
    const opportunities = rows.map((row) => {
      const opportunity = {...row};
      if (!isCanonicalListingUrl(opportunity.link, opportunity.linkedinJobId)) {
        throw new Error("Opportunity database contains an invalid listing URL");
      }
      return opportunity;
    });
    return {opportunities, lastUpdatedAt};
  } finally {
    database.close();
  }
});
