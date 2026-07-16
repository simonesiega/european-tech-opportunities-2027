import {DatabaseSync} from "node:sqlite";

export type Internship = {
  linkedinJobId: string;
  company: string;
  title: string;
  location: string;
  link: string;
};

const OPEN_INTERNSHIPS_QUERY = `
  SELECT
    linkedin_job_id AS linkedinJobId,
    company,
    title,
    location,
    link
  FROM jobs
  WHERE status = 'open'
  ORDER BY lower(company), lower(title), location
`;

export function getOpenInternships(): Internship[] {
  const databasePath = process.env.INTERNSHIPS_DATABASE_PATH ?? "../data/internships.db";
  const database = new DatabaseSync(databasePath, {readOnly: true});

  try {
    // Open a short-lived read-only connection so each request observes the latest
    // committed collection without sharing mutable SQLite state between requests.
    return database.prepare(OPEN_INTERNSHIPS_QUERY).all() as Internship[];
  } finally {
    database.close();
  }
}
