import {realpathSync, readlinkSync} from "node:fs";
import path from "node:path";

// A release is pinned once per server operation. Never reopen `current` after
// selecting it: it may change between the database query and the next file read.
export function currentReleaseDirectory(root: string): string {
  const target = readlinkSync(path.join(root, "current"));
  if (!/^releases\/[0-9]+-[0-9]+$/.test(target)) {
    throw new Error("Invalid publication pointer");
  }
  // Resolve the leaf as well as the pointer: a release-directory symlink must
  // not escape the configured releases root, even with a valid pointer name.
  const releases = realpathSync(path.join(root, "releases"));
  const release = realpathSync(path.join(root, target));
  if (path.dirname(release) !== releases) {
    throw new Error("Publication pointer escapes release directory");
  }
  return release;
}
