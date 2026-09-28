import {readFile} from "node:fs/promises";
import path from "node:path";

export const dynamic = "force-dynamic";

// The repository schema is copied verbatim into the site image. Local development
// reads that same source file; no second checked-in copy can drift from the pipeline.
const schemaPath =
  process.env.OPPORTUNITIES_SCHEMA_PATH ??
  path.resolve(process.cwd(), "../schemas/opportunities-v1.schema.json");

export async function GET() {
  try {
    const content = await readFile(/* turbopackIgnore: true */ schemaPath);
    return new Response(content, {
      headers: {
        "Cache-Control": "public, max-age=3600",
        "Content-Type": "application/schema+json; charset=utf-8",
      },
    });
  } catch {
    return new Response("Public schema is currently unavailable.\n", {
      status: 503,
      headers: {"Cache-Control": "no-store", "Content-Type": "text/plain; charset=utf-8"},
    });
  }
}
