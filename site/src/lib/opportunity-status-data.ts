import "server-only";

import {createHash} from "node:crypto";
import {constants} from "node:fs";
import {open} from "node:fs/promises";
import path from "node:path";
import {DatabaseSync} from "node:sqlite";
import {readDirectorySummary} from "@/lib/opportunities";
import {limitStatusReads, statusPayload} from "@/lib/opportunity-status";
import {publicationPaths} from "@/lib/release-path";

async function* readStatusFile(
  directory: string,
  name: "dataset-metadata.json" | "open-opportunities.json",
  limit: number
): AsyncGenerator<Buffer> {
  const filename = path.join(/* turbopackIgnore: true */ directory, name);
  // Nonblocking opens let named pipes reach the regular-file check without waiting for a writer.
  const file = await open(
    /* turbopackIgnore: true */ filename,
    constants.O_RDONLY | (constants.O_NONBLOCK ?? 0)
  );
  try {
    const stat = await file.stat();
    if (!stat.isFile() || stat.size > limit) throw new Error("Dataset exceeds status limit");
    let bytes = 0;
    // Allow one extra byte to detect growth after the file-size check.
    for await (const chunk of file.createReadStream({
      autoClose: false,
      highWaterMark: Math.min(limit + 1, 64 * 1024),
      end: limit,
    })) {
      bytes += chunk.length;
      if (bytes > limit) throw new Error("Dataset exceeds status limit");
      yield chunk;
    }
  } finally {
    await file.close();
  }
}

export const getOpportunityStatus = limitStatusReads(async () => {
  // Pin current once so a publication switch cannot mix database and export releases.
  const {databasePath, exportDirectory, release} = publicationPaths();
  const database = new DatabaseSync(databasePath, {readOnly: true});
  let summary: ReturnType<typeof readDirectorySummary>;
  try {
    summary = readDirectorySummary(database);
  } finally {
    database.close();
  }
  const chunks: Buffer[] = [];
  for await (const chunk of readStatusFile(exportDirectory, "dataset-metadata.json", 4096)) {
    chunks.push(chunk);
  }
  const metadata = JSON.parse(
    new TextDecoder("utf-8", {fatal: true}).decode(Buffer.concat(chunks))
  );
  const hash = createHash("sha256");
  for await (const chunk of readStatusFile(
    exportDirectory,
    "open-opportunities.json",
    64 * 1024 * 1024
  )) {
    hash.update(chunk);
  }
  return statusPayload(summary, metadata, hash.digest("hex"), release);
});
