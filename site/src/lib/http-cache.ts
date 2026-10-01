import {createHash} from "node:crypto";

export const REVALIDATE_CACHE_CONTROL = "public, max-age=0, must-revalidate";

export function contentEtag(body: string): string {
  return `"${createHash("sha256").update(body).digest("hex")}"`;
}

export function matchesIfNoneMatch(header: string | null, etag: string): boolean {
  if (!header) return false;
  return header.split(",").some((value) => {
    const tag = value.trim();
    return tag === "*" || tag === etag || tag === `W/${etag}`;
  });
}
