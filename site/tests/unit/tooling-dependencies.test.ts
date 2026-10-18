import {expect, test} from "bun:test";
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";

test("Lighthouse resolves compatible Puppeteer imports without extract-zip", () => {
  // Exercise Node's loaders, not Bun's interop; Lighthouse runs under Node in CI.
  const result = spawnSync(
    "node",
    [
      "--input-type=module",
      "--eval",
      String.raw`
        import assert from "node:assert/strict";
        import {createRequire} from "node:module";
        import {pathToFileURL} from "node:url";
        const require = createRequire(import.meta.url);
        const fromLighthouse = createRequire(require.resolve("lighthouse"));
        const entry = fromLighthouse.resolve("puppeteer-core");
        const esm = await import(pathToFileURL(entry).href);
        const fromCli = createRequire(require.resolve("@lhci/cli/package.json"));
        const cjs = fromCli("puppeteer-core");
        for (const api of [esm.default, cjs]) {
          assert.equal(typeof api.connect, "function");
          assert.equal(typeof api.launch, "function");
        }
        assert.equal(fromCli.resolve("puppeteer-core"), entry);
        const fromPuppeteer = createRequire(entry);
        const fromBrowsers = createRequire(fromPuppeteer.resolve("@puppeteer/browsers"));
        assert.throws(() => fromBrowsers.resolve("extract-zip"), {code: "MODULE_NOT_FOUND"});
      `,
    ],
    {
      cwd: fileURLToPath(new URL("../..", import.meta.url)),
      encoding: "utf8",
      timeout: 10_000,
    }
  );
  expect(result.error).toBeUndefined();
  expect(result.status, result.stderr).toBe(0);
}, 15_000);

test("Lighthouse's FTP dependency keeps its CommonJS API and bounds malformed listing parsing", () => {
  // Isolate the parser so a vulnerable transitive version cannot hang the test runner.
  // Only synthetic strings are parsed; no FTP connection is opened.
  const result = spawnSync(
    "node",
    [
      "--input-type=commonjs",
      "--eval",
      String.raw`
        const assert = require("node:assert/strict");
        const {createRequire} = require("node:module");
        const fromConsumer = createRequire(require.resolve("get-uri"));
        const {Client, parseList} = fromConsumer("basic-ftp");
        const client = new Client();
        try {
          for (const method of ["access", "lastMod", "list", "downloadTo", "close"]) {
            assert.equal(typeof client[method], "function");
          }
          const malformed = "-rw-r--r-- 1 " + "a ".repeat(65536) + "!\r\n";
          const valid = "-rw-r--r-- 1 owner group 42 Jan 1 2020 example.txt\r\n";
          const entries = parseList(malformed + valid);
          assert.deepEqual(entries.map(({name, size}) => ({name, size})), [
            {name: "example.txt", size: 42},
          ]);
        } finally {
          client.close();
        }
      `,
    ],
    {
      cwd: fileURLToPath(new URL("../..", import.meta.url)),
      encoding: "utf8",
      timeout: 10_000,
    }
  );
  expect(result.error).toBeUndefined();
  expect(result.status, result.stderr).toBe(0);
}, 15_000);
