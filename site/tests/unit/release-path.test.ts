import {afterEach, expect, test} from "bun:test";
import {mkdtempSync, mkdirSync, renameSync, rmSync, symlinkSync} from "node:fs";
import {tmpdir} from "node:os";
import path from "node:path";
import {currentReleaseDirectory, publicationPaths} from "@/lib/release-path";

const roots: string[] = [];
function root() {
  const directory = mkdtempSync(path.join(tmpdir(), "opportunities-release-"));
  roots.push(directory);
  mkdirSync(path.join(directory, "releases", "1-1"), {recursive: true});
  mkdirSync(path.join(directory, "releases", "2-1"));
  symlinkSync("releases/1-1", path.join(directory, "current"), "dir");
  return directory;
}

afterEach(() => {
  for (const directory of roots.splice(0)) rmSync(directory, {recursive: true, force: true});
});

test("legacy publication paths preserve defaults and explicit overrides without inventing a release", () => {
  expect(publicationPaths({})).toEqual({
    databasePath: "../data/opportunities.db",
    exportDirectory: "../data/exports",
    release: null,
  });
  expect(
    publicationPaths({
      OPPORTUNITIES_RELEASE_ROOT: "",
      OPPORTUNITIES_DATABASE_PATH: "synthetic.db",
      OPPORTUNITIES_PUBLIC_EXPORT_DIR: "synthetic-exports",
    })
  ).toEqual({databasePath: "synthetic.db", exportDirectory: "synthetic-exports", release: null});
});

test("an invalid release root never falls back to legacy database or export paths", () => {
  const directory = mkdtempSync(path.join(tmpdir(), "opportunities-missing-release-"));
  roots.push(directory);
  expect(() =>
    publicationPaths({
      OPPORTUNITIES_RELEASE_ROOT: directory,
      OPPORTUNITIES_DATABASE_PATH: "synthetic.db",
      OPPORTUNITIES_PUBLIC_EXPORT_DIR: "synthetic-exports",
    })
  ).toThrow();
});

// Host symlink replacement and POSIX traversal are production Linux contracts.
const linuxTest = process.platform === "win32" ? test.skip : test;

linuxTest("pins a real release directory even when the pointer changes", () => {
  const directory = root();
  const first = currentReleaseDirectory(directory);
  const selection = publicationPaths({OPPORTUNITIES_RELEASE_ROOT: directory});
  symlinkSync("releases/2-1", path.join(directory, ".next"), "dir");
  renameSync(path.join(directory, ".next"), path.join(directory, "current"));
  expect(first).toEndWith(path.join("releases", "1-1"));
  expect(currentReleaseDirectory(directory)).toEndWith(path.join("releases", "2-1"));
  // A pinned status read must not mix the old database with the next release's metadata.
  expect(selection).toEqual({
    databasePath: path.join(first, "opportunities.db"),
    exportDirectory: path.join(first, "exports"),
    release: "1-1",
  });
  expect(publicationPaths({OPPORTUNITIES_RELEASE_ROOT: directory}).release).toBe("2-1");
});

linuxTest("fails closed for missing, invalid, and escaping pointers", () => {
  const directory = root();
  rmSync(path.join(directory, "current"));
  expect(() => currentReleaseDirectory(directory)).toThrow();
  symlinkSync("../legacy", path.join(directory, "current"), "dir");
  expect(() => currentReleaseDirectory(directory)).toThrow("Invalid publication pointer");
  rmSync(path.join(directory, "current"));
  rmSync(path.join(directory, "releases", "2-1"), {recursive: true});
  symlinkSync(tmpdir(), path.join(directory, "releases", "2-1"), "dir");
  symlinkSync("releases/2-1", path.join(directory, "current"), "dir");
  expect(() => currentReleaseDirectory(directory)).toThrow("escapes release directory");
});

linuxTest("does not expose a non-public directory name through a release alias", () => {
  const directory = root();
  const internal = path.join(directory, "releases", "private-name");
  mkdirSync(internal);
  rmSync(path.join(directory, "releases", "1-1"), {recursive: true});
  symlinkSync(internal, path.join(directory, "releases", "1-1"), "dir");
  expect(() => publicationPaths({OPPORTUNITIES_RELEASE_ROOT: directory})).toThrow(
    "Invalid publication identifier"
  );
});
