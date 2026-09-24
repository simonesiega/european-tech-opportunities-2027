import "server-only";

import {readFile} from "node:fs/promises";
import path from "node:path";
import {currentReleaseDirectory} from "@/lib/release-path";

type PublicExportFormat = "csv" | "json";

const exportMetadata: Record<PublicExportFormat, {filename: string; contentType: string}> = {
  csv: {
    filename: "open-opportunities.csv",
    contentType: "text/csv; charset=utf-8",
  },
  json: {
    filename: "open-opportunities.json",
    contentType: "application/json; charset=utf-8",
  },
};

export async function getPublicExport(format: PublicExportFormat): Promise<Response> {
  const {filename, contentType} = exportMetadata[format];
  try {
    const exportDirectory = process.env.OPPORTUNITIES_RELEASE_ROOT
      ? path.join(currentReleaseDirectory(process.env.OPPORTUNITIES_RELEASE_ROOT), "exports")
      : (process.env.OPPORTUNITIES_PUBLIC_EXPORT_DIR ?? "../data/exports");
    const exportPath = path.join(/* turbopackIgnore: true */ exportDirectory, filename);
    const content = await readFile(/* turbopackIgnore: true */ exportPath);
    return new Response(content, {
      headers: {
        "Cache-Control": "no-store",
        "Content-Disposition": `attachment; filename="${filename}"`,
        "Content-Type": contentType,
      },
    });
  } catch {
    return new Response("Public export is currently unavailable.\n", {
      status: 503,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": "text/plain; charset=utf-8",
      },
    });
  }
}
