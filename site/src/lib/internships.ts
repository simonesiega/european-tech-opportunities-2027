import {DatabaseSync} from "node:sqlite";
import type {Opportunity} from "@/types/opportunity";

const LAST_UPDATED_QUERY = `
  SELECT MAX(finished_at) AS lastUpdatedAt
  FROM search_runs
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
  const databasePath = process.env.INTERNSHIPS_DATABASE_PATH ?? "../data/internships.db";
  const database = new DatabaseSync(databasePath, {readOnly: true});

  try {
    const {lastUpdatedAt} = database.prepare(LAST_UPDATED_QUERY).get() as {
      lastUpdatedAt: string | null;
    };
    const rows = database.prepare(OPEN_OPPORTUNITIES_QUERY).all() as Opportunity[];

    // node:sqlite rows have a null prototype and cannot cross the Server Component boundary.
    const opportunities = rows.map((row) => ({...row}));
    return {opportunities, lastUpdatedAt};
  } finally {
    database.close();
  }
}
