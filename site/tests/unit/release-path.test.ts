import {afterEach, expect, test} from "bun:test";
import {mkdtempSync, mkdirSync, renameSync, rmSync, symlinkSync} from "node:fs";
import {tmpdir} from "node:os";
import path from "node:path";
import {currentReleaseDirectory} from "@/lib/release-path";

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

// Host symlink replacement and POSIX traversal are production Linux contracts.
const linuxTest = process.platform === "win32" ? test.skip : test;

linuxTest("pins a real release directory even when the pointer changes", () => {
  const directory = root();
  const first = currentReleaseDirectory(directory);
  symlinkSync("releases/2-1", path.join(directory, ".next"), "dir");
  renameSync(path.join(directory, ".next"), path.join(directory, "current"));
  expect(first).toEndWith(path.join("releases", "1-1"));
  expect(currentReleaseDirectory(directory)).toEndWith(path.join("releases", "2-1"));
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
