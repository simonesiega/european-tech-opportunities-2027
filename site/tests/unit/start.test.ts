import {afterEach, expect, test} from "bun:test";
import {copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import path from "node:path";
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";

const roots: string[] = [];
const variables = [
  "OPPORTUNITIES_DATABASE_PATH",
  "OPPORTUNITIES_PUBLIC_EXPORT_DIR",
  "OPPORTUNITIES_SCHEMA_PATH",
  "OPPORTUNITIES_RELEASE_ROOT",
];

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, {recursive: true, force: true});
});

test.each(["defaults", "relative", "absolute"] as const)(
  "standalone startup preserves %s data paths after Next changes directory",
  (mode) => {
    const root = mkdtempSync(path.join(tmpdir(), "opportunities-start-"));
    roots.push(root);
    const site = path.join(root, "site");
    const standalone = path.join(site, ".next", "standalone");
    mkdirSync(standalone, {recursive: true});
    mkdirSync(path.join(site, ".next", "static"));
    mkdirSync(path.join(site, "scripts"));
    writeFileSync(path.join(site, ".next", "static", "marker.js"), "synthetic static asset");
    copyFileSync(
      fileURLToPath(new URL("../../scripts/start.mjs", import.meta.url)),
      path.join(site, "scripts", "start.mjs")
    );
    // Model the standalone server's cwd change without starting a service or
    // reading a real database, environment file, or deployment configuration.
    writeFileSync(
      path.join(standalone, "server.js"),
      `process.chdir(__dirname);
       console.log(JSON.stringify(Object.fromEntries(${JSON.stringify(variables)}.map(
         name => [name, process.env[name] ?? null]
       ))));`
    );
    const env: NodeJS.ProcessEnv = {...process.env, NODE_ENV: "production"};
    for (const name of variables) delete env[name];
    const expected: Record<string, string | null> = {
      OPPORTUNITIES_DATABASE_PATH: path.join(root, "data", "opportunities.db"),
      OPPORTUNITIES_PUBLIC_EXPORT_DIR: path.join(root, "data", "exports"),
      OPPORTUNITIES_SCHEMA_PATH: path.join(root, "schemas", "opportunities-v1.schema.json"),
      OPPORTUNITIES_RELEASE_ROOT: null,
    };
    if (mode !== "defaults") {
      for (const [index, name] of variables.entries()) {
        env[name] = mode === "absolute" ? path.join(root, `fixture-${index}`) : `fixture-${index}`;
        expected[name] = path.resolve(site, env[name]!);
      }
    }
    const result = spawnSync("node", [path.join(site, "scripts", "start.mjs")], {
      cwd: root,
      env,
      encoding: "utf8",
      timeout: 15_000,
    });
    expect(result.error).toBeUndefined();
    expect(result.status, result.stderr).toBe(0);
    expect(JSON.parse(result.stdout)).toEqual(expected);
    expect(readFileSync(path.join(standalone, ".next", "static", "marker.js"), "utf8")).toBe(
      "synthetic static asset"
    );
  }
);
