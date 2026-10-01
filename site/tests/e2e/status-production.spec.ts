import {spawn, type ChildProcess} from "node:child_process";
import {once} from "node:events";
import {createHash} from "node:crypto";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  symlinkSync,
  truncateSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import {tmpdir} from "node:os";
import path from "node:path";
import {DatabaseSync} from "node:sqlite";
import {expect, test, type APIRequestContext} from "@playwright/test";

const endpoint = "/api/v1/status";
const versioned = process.platform !== "win32";
const sha256 = (bytes: Buffer) => createHash("sha256").update(bytes).digest("hex");
let root: string;
let databasePath: string;
let metadataPath: string;
let jsonPath: string;
let server: ChildProcess;
let client: APIRequestContext;

// Production avoids dev-server file watching while faults are injected into isolated state.
test.describe.configure({mode: "serial"});
test.beforeAll(async ({playwright}) => {
  if (!existsSync(path.resolve(".next/standalone/server.js"))) {
    throw new Error("Run bun run build before the production status tests");
  }
  root = mkdtempSync(path.join(tmpdir(), "opportunities-status-"));
  const directory = versioned ? path.join(root, "releases", "1-1") : root;
  const exports = path.join(directory, "exports");
  mkdirSync(exports, {recursive: true});
  databasePath = path.join(directory, "opportunities.db");
  metadataPath = path.join(exports, "dataset-metadata.json");
  jsonPath = path.join(exports, "open-opportunities.json");
  copyFileSync(path.resolve("tests/e2e/.tmp/opportunities.db"), databasePath);
  for (const filename of ["dataset-metadata.json", "open-opportunities.json"]) {
    copyFileSync(path.resolve("tests/e2e/.tmp", filename), path.join(exports, filename));
  }
  if (versioned) symlinkSync("releases/1-1", path.join(root, "current"), "dir");
  server = spawn("node", [path.resolve("scripts/start.mjs")], {
    env: {
      ...process.env,
      HOSTNAME: "127.0.0.1",
      PORT: "3101",
      NODE_ENV: "production",
      NEXT_DIST_DIR: ".next",
      SITE_URL: "https://techopportunities.eu",
      OPPORTUNITIES_RELEASE_ROOT: versioned ? root : "",
      OPPORTUNITIES_DATABASE_PATH: databasePath,
      OPPORTUNITIES_PUBLIC_EXPORT_DIR: exports,
      OPPORTUNITIES_SCHEMA_PATH: path.resolve("../schemas/opportunities-v1.schema.json"),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  // Do not join an existing service on this port: require this child's readiness signal.
  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error("Status fixture server did not start")),
      20_000
    );
    let output = "";
    server.on("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });
    server.on("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`Status fixture server exited before readiness (code ${code})`));
    });
    server.stderr?.resume();
    server.stdout?.on("data", (chunk: Buffer) => {
      output = (output + chunk.toString()).slice(-4096);
      if (output.includes("Ready in")) {
        clearTimeout(timeout);
        resolve();
      }
    });
  });
  client = await playwright.request.newContext({baseURL: "http://127.0.0.1:3101"});
});

test.afterAll(async () => {
  await client?.dispose();
  if (server && server.exitCode === null && server.signalCode === null) {
    const exited = once(server, "exit");
    server.kill();
    await exited;
  }
  if (root) rmSync(root, {recursive: true, force: true});
});

async function withRestoredFixture(action: () => Promise<void>) {
  const originals = [databasePath, metadataPath, jsonPath].map((filename) => ({
    filename,
    bytes: readFileSync(filename),
  }));
  try {
    await action();
  } finally {
    for (const {filename, bytes} of originals) writeFileSync(filename, bytes);
  }
}

test("production status reads the selected dataset without modifying SQLite", async () => {
  const before = readFileSync(databasePath);
  const response = await client.get(endpoint);
  expect(response.status()).toBe(200);
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  expect(await response.json()).toMatchObject({
    last_successful_collection: "2026-07-17T12:00:00.000000+00:00",
    opportunities: 12,
    dataset_sha256: sha256(readFileSync(jsonPath)),
    release: versioned ? "1-1" : null,
  });
  expect(readFileSync(databasePath)).toEqual(before);
});

for (const failure of [
  "database missing",
  "database invalid",
  "database unmigrated",
  "metadata missing",
  "metadata invalid",
  "metadata invalid UTF-8",
  "metadata oversized",
  "metadata wrong count",
  "metadata wrong hash",
  "download missing",
  "download changed",
  "download oversized",
]) {
  test(`production status fails closed without leaking details: ${failure}`, async () => {
    await withRestoredFixture(async () => {
      if (failure === "database missing") unlinkSync(databasePath);
      if (failure === "database invalid") writeFileSync(databasePath, "not a SQLite database");
      if (failure === "database unmigrated") writeFileSync(databasePath, Buffer.alloc(0));
      const databaseBefore = existsSync(databasePath) ? readFileSync(databasePath) : null;
      if (failure === "metadata missing") unlinkSync(metadataPath);
      if (failure === "metadata invalid")
        writeFileSync(metadataPath, '{"private_path":"/private/fixture",');
      if (failure === "metadata invalid UTF-8") writeFileSync(metadataPath, Buffer.from([0xff]));
      if (failure === "metadata oversized") writeFileSync(metadataPath, " ".repeat(4097));
      if (failure === "metadata wrong count" || failure === "metadata wrong hash") {
        const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
        if (failure === "metadata wrong count") {
          metadata.total++;
          metadata.internship_count++;
        } else metadata.json_sha256 = "0".repeat(64);
        writeFileSync(metadataPath, JSON.stringify(metadata));
      }
      if (failure === "download missing") unlinkSync(jsonPath);
      if (failure === "download changed") writeFileSync(jsonPath, "[]\n");
      if (failure === "download oversized") truncateSync(jsonPath, 64 * 1024 * 1024 + 1);
      const response = await client.get(endpoint);
      expect(response.status()).toBe(503);
      expect(response.headers()["cache-control"]).toBe("no-store");
      expect(await response.json()).toEqual({
        version: "v1",
        error: {code: "unavailable", message: "Status unavailable"},
      });
      const head = await client.head(endpoint);
      expect(head.status()).toBe(503);
      expect(await head.text()).toBe("");
      if (databaseBefore === null) expect(existsSync(databasePath)).toBe(false);
      else expect(readFileSync(databasePath)).toEqual(databaseBefore);
    });
    expect((await client.get(endpoint)).status()).toBe(200);
  });
}

test("production status counts only open rows and represents a never-collected empty dataset", async () => {
  await withRestoredFixture(async () => {
    const database = new DatabaseSync(databasePath);
    try {
      database.exec("UPDATE jobs SET status = 'closed'; DELETE FROM search_runs");
    } finally {
      database.close();
    }
    writeFileSync(jsonPath, "[]\n");
    const metadata = JSON.parse(readFileSync(metadataPath, "utf8"));
    writeFileSync(
      metadataPath,
      JSON.stringify({
        ...metadata,
        total: 0,
        internship_count: 0,
        new_grad_count: 0,
        json_sha256: sha256(readFileSync(jsonPath)),
      })
    );
    const response = await client.get(endpoint);
    expect(response.status()).toBe(200);
    expect(await response.json()).toMatchObject({
      last_successful_collection: null,
      opportunities: 0,
    });
  });
});

test("production status follows release cutovers and rejects a missing pointer without legacy fallback", async () => {
  test.skip(!versioned, "POSIX publication pointers are not exercised on Windows");
  const next = path.join(root, "releases", "2-1");
  mkdirSync(path.join(next, "exports"), {recursive: true});
  copyFileSync(databasePath, path.join(next, "opportunities.db"));
  const database = new DatabaseSync(path.join(next, "opportunities.db"));
  try {
    database.exec(`
      UPDATE jobs SET status = 'closed';
      UPDATE search_runs SET finished_at = '2026-08-01 12:00:00.000000' WHERE status = 'success'
    `);
  } finally {
    database.close();
  }
  const json = Buffer.from("[]\n");
  writeFileSync(path.join(next, "exports", "open-opportunities.json"), json);
  const metadata = {
    ...JSON.parse(readFileSync(metadataPath, "utf8")),
    generated_at: "2026-08-01T12:00:00+00:00",
    total: 0,
    internship_count: 0,
    new_grad_count: 0,
    json_sha256: sha256(json),
  };
  writeFileSync(path.join(next, "exports", "dataset-metadata.json"), JSON.stringify(metadata));
  symlinkSync("releases/2-1", path.join(root, "next"), "dir");
  renameSync(path.join(root, "next"), path.join(root, "current"));
  const response = await client.get(endpoint);
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual({
    release: "2-1",
    opportunities: 0,
    last_successful_collection: "2026-08-01T12:00:00.000000+00:00",
    dataset_generated_at: "2026-08-01T12:00:00.000000+00:00",
    dataset_sha256: metadata.json_sha256,
  });
  unlinkSync(path.join(root, "current"));
  expect((await client.get(endpoint)).status()).toBe(503);
});
