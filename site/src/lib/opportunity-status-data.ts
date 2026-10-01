import "server-only";

import {createHash} from "node:crypto";
import {createReadStream} from "node:fs";
import {open} from "node:fs/promises";
import path from "node:path";
import {DatabaseSync} from "node:sqlite";
import {readDirectorySummary} from "@/lib/opportunities";
import {statusPayload, type OpportunityStatus} from "@/lib/opportunity-status";
import {publicationPaths} from "@/lib/release-path";

const MAX_METADATA_BYTES = 4096;
const MAX_DATASET_BYTES = 64 * 1024 * 1024;

async function readMetadata(directory: string): Promise<unknown> {
  const filename = path.join(/* turbopackIgnore: true */ directory, "dataset-metadata.json");
  const file = await open(/* turbopackIgnore: true */ filename, "r");
  try {
    const buffer = Buffer.alloc(MAX_METADATA_BYTES + 1);
    let length = 0;
    while (length < buffer.length) {
      const {bytesRead} = await file.read(buffer, length, buffer.length - length, null);
      if (bytesRead === 0) break;
      length += bytesRead;
    }
    if (length > MAX_METADATA_BYTES) throw new Error("Dataset metadata exceeds status limit");
    return JSON.parse(new TextDecoder("utf-8", {fatal: true}).decode(buffer.subarray(0, length)));
  } finally {
    await file.close();
  }
}

async function datasetHash(directory: string): Promise<string> {
  const filename = path.join(/* turbopackIgnore: true */ directory, "open-opportunities.json");
  const hash = createHash("sha256");
  let bytes = 0;
  // Hash the download itself: metadata alone cannot prove that its bytes match.
  for await (const chunk of createReadStream(/* turbopackIgnore: true */ filename)) {
    bytes += chunk.length;
    if (bytes > MAX_DATASET_BYTES) throw new Error("Dataset exceeds status limit");
    hash.update(chunk);
  }
  return hash.digest("hex");
}

export async function getOpportunityStatus(): Promise<OpportunityStatus> {
  // Pin current once so a publication switch cannot mix database and export releases.
  const {databasePath, exportDirectory, release} = publicationPaths();
  const database = new DatabaseSync(databasePath, {readOnly: true});
  let summary: ReturnType<typeof readDirectorySummary>;
  try {
    summary = readDirectorySummary(database);
  } finally {
    database.close();
  }
  const metadata = await readMetadata(exportDirectory);
  const jsonSha256 = await datasetHash(exportDirectory);
  return statusPayload(summary, metadata, jsonSha256, release);
}
