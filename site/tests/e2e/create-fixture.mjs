import {mkdirSync, rmSync} from "node:fs";
import path from "node:path";
import {Database} from "bun:sqlite";

const fixtureDirectory = path.resolve("tests/e2e/.tmp");
const databasePath = path.join(fixtureDirectory, "internships.db");

mkdirSync(fixtureDirectory, {recursive: true});
rmSync(databasePath, {force: true});

const database = new Database(databasePath, {create: true, strict: true});

database.run(`
  CREATE TABLE search_runs (
    id INTEGER PRIMARY KEY,
    finished_at TEXT
  )
`);
database.run(`
  CREATE TABLE jobs (
    linkedin_job_id TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    link TEXT NOT NULL,
    category TEXT NOT NULL,
    industries TEXT,
    employment_type TEXT,
    start_date TEXT,
    first_seen_at TEXT NOT NULL,
    status TEXT NOT NULL
  )
`);

database.run("INSERT INTO search_runs (id, finished_at) VALUES (1, ?)", [
  "2026-07-17T12:00:00+00:00",
]);

const insertJob = database.prepare(`
  INSERT INTO jobs (
    linkedin_job_id, company, title, location, link, category, industries,
    employment_type, start_date, first_seen_at, status
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
`);

const jobs = [
  [
    "1000000001",
    "Acme Labs",
    "Software Engineering Intern 2027",
    "Berlin, Germany",
    "https://www.linkedin.com/jobs/view/1000000001",
    "software-engineering",
    "Software Development",
    "internship",
    "June 2027",
    "2026-07-10T09:00:00+00:00",
  ],
  [
    "1000000002",
    "Acme Labs",
    "Cybersecurity Intern 2027",
    "Dublin, Ireland",
    "https://www.linkedin.com/jobs/view/1000000002",
    "cybersecurity",
    "Computer and Network Security",
    "internship",
    null,
    "2026-07-11T09:00:00+00:00",
  ],
  [
    "1000000003",
    "Northstar Data",
    "Graduate Data Analyst 2027",
    "Paris, France",
    "https://www.linkedin.com/jobs/view/1000000003",
    "data-science",
    "Information Technology",
    "new-grad",
    "Summer 2027",
    "2026-07-12T09:00:00+00:00",
  ],
];

for (let index = 1; index <= 9; index += 1) {
  jobs.push([
    String(1000000003 + index),
    `Example ${String(index).padStart(2, "0")}`,
    `Platform Engineering Intern ${index}`,
    "Madrid, Spain",
    `https://www.linkedin.com/jobs/view/${1000000003 + index}`,
    "software-engineering",
    "Software Development",
    "internship",
    null,
    `2026-07-${String(12 + index).padStart(2, "0")}T09:00:00+00:00`,
  ]);
}

const transaction = database.transaction((rows) => {
  for (const job of rows) insertJob.run(...job);
});
transaction(jobs);
database.close();
