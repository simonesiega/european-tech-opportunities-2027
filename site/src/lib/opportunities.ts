import {DatabaseSync} from "node:sqlite";
import {isCanonicalListingUrl} from "@/lib/listing-url";
import type {Opportunity} from "@/types/opportunity";

const LAST_UPDATED_QUERY = `
  SELECT MAX(finished_at) AS lastUpdatedAt
  FROM search_runs
  WHERE status = 'success'
`;

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
  ORDER BY lower(company), lower(title), location
`;

type DirectoryData = {
  opportunities: Opportunity[];
  lastUpdatedAt: string | null;
};

export function getDirectoryData(): DirectoryData {
  const databasePath = process.env.OPPORTUNITIES_DATABASE_PATH ?? "../data/opportunities.db";
  const database = new DatabaseSync(databasePath, {readOnly: true});

  try {
    const {lastUpdatedAt} = database.prepare(LAST_UPDATED_QUERY).get() as {
      lastUpdatedAt: string | null;
    };
    const rows = database.prepare(OPEN_OPPORTUNITIES_QUERY).all() as Opportunity[];

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
}
