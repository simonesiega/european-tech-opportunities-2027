import {createHash} from "node:crypto";
import {mkdirSync, rmSync, writeFileSync} from "node:fs";
import path from "node:path";
import {Database} from "bun:sqlite";

const fixtureDirectory = path.resolve("tests/e2e/.tmp");
const databasePath = path.join(fixtureDirectory, "opportunities.db");

mkdirSync(fixtureDirectory, {recursive: true});
rmSync(databasePath, {force: true});

const database = new Database(databasePath, {create: true, strict: true});

database.run(`
  CREATE TABLE search_runs (
    id INTEGER PRIMARY KEY,
    status TEXT NOT NULL,
    finished_at TEXT NOT NULL
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

database.run("INSERT INTO search_runs (id, status, finished_at) VALUES (1, 'success', ?)", [
  "2026-07-17T12:00:00+00:00",
]);
database.run("INSERT INTO search_runs (id, status, finished_at) VALUES (2, 'failed', ?)", [
  "2026-07-19T12:00:00+00:00",
]);

const insertJob = database.prepare(`
  INSERT INTO jobs (
    linkedin_job_id, company, title, location, link, category, industries,
    employment_type, start_date, first_seen_at, status
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
`);

const now = Date.now();
const hoursAgo = (hours) => new Date(now - hours * 60 * 60 * 1000).toISOString();

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
    hoursAgo(40 * 24),
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
    hoursAgo(20 * 24),
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
    hoursAgo(8 * 24),
  ],
];

const exampleAgeHours = [28 * 24, 14 * 24, 6 * 24, 5 * 24, 4 * 24, 3 * 24, 2 * 24, 12, 2];

for (let index = 1; index <= 9; index += 1) {
  jobs.push([
    String(1000000003 + index),
    `Example ${String(index).padStart(2, "0")}`,
    `Platform Engineering Intern ${index}`,
    index === 1 ? "Madrid, Spain; Lisbon, Portugal" : "Madrid, Spain",
    `https://www.linkedin.com/jobs/view/${1000000003 + index}`,
    "software-engineering",
    "Software Development",
    "internship",
    null,
    hoursAgo(exampleAgeHours[index - 1]),
  ]);
}

// Exercise the real SQLite timestamp representation at the API boundary.
jobs[0][9] = jobs[0][9].replace("T", " ").replace("Z", "");

const transaction = database.transaction((rows) => {
  for (const job of rows) insertJob.run(...job);
});
transaction(jobs);
database.close();

const publicFields = [
  "linkedin_job_id",
  "company",
  "title",
  "location",
  "link",
  "category",
  "industries",
  "employment_type",
  "start_date",
];
const publicRows = jobs
  .toReversed()
  .map((job) => Object.fromEntries(publicFields.map((field, index) => [field, job[index]])));
const csvCell = (value) => {
  if (value === null) return "";
  const text = String(value);
  const safe = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text;
  return /[",\n\r]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
};
const csv = [
  publicFields.join(","),
  ...publicRows.map((row) => publicFields.map((field) => csvCell(row[field])).join(",")),
].join("\n");

const csvContent = `${csv}\n`;
const jsonContent = `${JSON.stringify(publicRows, null, 2)}\n`;
writeFileSync(path.join(fixtureDirectory, "open-opportunities.csv"), csvContent, "utf8");
writeFileSync(path.join(fixtureDirectory, "open-opportunities.json"), jsonContent, "utf8");
const sha256 = (content) => createHash("sha256").update(content).digest("hex");
writeFileSync(
  path.join(fixtureDirectory, "dataset-metadata.json"),
  `${JSON.stringify({
    schema_version: "v1",
    generated_at: "2026-07-17T12:00:00+00:00",
    total: publicRows.length,
    internship_count: publicRows.filter((row) => row.employment_type === "internship").length,
    new_grad_count: publicRows.filter((row) => row.employment_type === "new-grad").length,
    json_sha256: sha256(jsonContent),
    csv_sha256: sha256(csvContent),
  })}\n`,
  "utf8"
);
