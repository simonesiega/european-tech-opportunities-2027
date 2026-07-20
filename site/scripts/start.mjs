import {cpSync, existsSync, mkdirSync} from "node:fs";
import path from "node:path";
import {fileURLToPath, pathToFileURL} from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const standalone = path.join(root, ".next", "standalone");
const server = path.join(standalone, "server.js");

if (!existsSync(server)) {
  throw new Error("Standalone build not found. Run `bun run build` before `bun run start`.");
}

mkdirSync(path.join(standalone, ".next"), {recursive: true});
cpSync(path.join(root, ".next", "static"), path.join(standalone, ".next", "static"), {
  recursive: true,
});

const publicDirectory = path.join(root, "public");
if (existsSync(publicDirectory)) {
  cpSync(publicDirectory, path.join(standalone, "public"), {recursive: true});
}

await import(pathToFileURL(server).href);
