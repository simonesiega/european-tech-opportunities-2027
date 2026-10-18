import "server-only";

import {constants} from "node:fs";
import {open} from "node:fs/promises";
import path from "node:path";
import {Readable} from "node:stream";
import {publicationPaths} from "@/lib/release-path";

type PublicExportFormat = "csv" | "json" | "metadata";

const exportMetadata: Record<PublicExportFormat, {filename: string; contentType: string}> = {
  csv: {
    filename: "open-opportunities.csv",
    contentType: "text/csv; charset=utf-8",
  },
  json: {
    filename: "open-opportunities.json",
    contentType: "application/json; charset=utf-8",
  },
  metadata: {
    filename: "dataset-metadata.json",
    contentType: "application/json; charset=utf-8",
  },
};

export async function getPublicExport(format: PublicExportFormat, head = false): Promise<Response> {
  const {filename, contentType} = exportMetadata[format];
  try {
    const {exportDirectory} = publicationPaths();
    // Deployment supplies these files at runtime; do not trace them into the build output.
    const exportPath = path.join(/* turbopackIgnore: true */ exportDirectory, filename);
    // Open before sending headers so missing files return 503. Nonblocking mode
    // lets named pipes reach the regular-file check without waiting for a writer.
    const file = await open(
      /* turbopackIgnore: true */ exportPath,
      constants.O_RDONLY | (constants.O_NONBLOCK ?? 0)
    );
    try {
      if (!(await file.stat()).isFile()) throw new Error("Public export is not a regular file");
      // The open descriptor survives atomic replacement; the stream closes it on cancellation.
      // Node and DOM types describe the same native Web Stream.
      const body = head
        ? null
        : (Readable.toWeb(file.createReadStream(), {
            strategy: {highWaterMark: 1},
          }) as unknown as ReadableStream<Uint8Array>);
      if (head) await file.close();
      return new Response(body, {
        headers: {
          "Cache-Control": "no-store",
          "Content-Disposition": `attachment; filename="${filename}"`,
          "Content-Type": contentType,
        },
      });
    } catch (error) {
      await file.close();
      throw error;
    }
  } catch {
    return new Response(head ? null : "Public export is currently unavailable.\n", {
      status: 503,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": "text/plain; charset=utf-8",
      },
    });
  }
}
