import {expect, test} from "bun:test";
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";

function assertNode(source: string, ...flags: string[]): void {
  // Exercise Node's loaders and bound vulnerable consumers without stalling Bun.
  const result = spawnSync("node", [...flags, "--eval", source], {
    cwd: fileURLToPath(new URL("../..", import.meta.url)),
    encoding: "utf8",
    timeout: 10_000,
  });
  expect(result.error).toBeUndefined();
  expect(result.status, result.stderr).toBe(0);
}

test("Lighthouse resolves compatible Puppeteer imports without extract-zip", () => {
  assertNode(
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
    "--input-type=module"
  );
}, 15_000);

test("ESLint and Lighthouse reject oversized Zod collections before validating elements", () => {
  assertNode(
    String.raw`
        const assert = require("node:assert/strict");
        const {createRequire} = require("node:module");
        const fromHooks = createRequire(require.resolve("eslint-plugin-react-hooks"));
        const fromLighthouse = createRequire(require.resolve("lighthouse"));
        const fromPuppeteer = createRequire(fromLighthouse.resolve("puppeteer-core"));
        const fromBidi = createRequire(fromPuppeteer.resolve("chromium-bidi"));
        for (const consumer of [fromHooks, fromBidi]) {
          const {z} = consumer("zod");
          let visited = 0;
          const schema = z.array(z.preprocess(value => {
            visited++;
            return value;
          }, z.string().min(4))).max(2);
          assert.deepEqual(schema.parse(["safe"]), ["safe"]);
          assert.equal(visited, 1);
          visited = 0;
          const result = schema.safeParse(Array(1_000_000).fill(""));
          assert.equal(result.success, false);
          assert.equal(result.error.issues.length, 1);
          assert.equal(result.error.issues[0].code, "too_big");
          assert.equal(visited, 0);
        }
      `,
    "--max-old-space-size=64",
    "--input-type=commonjs"
  );
}, 15_000);

test("Lighthouse's proxy dependency bounds malformed IPv6 parsing and preserves address bytes", () => {
  assertNode(
    String.raw`
        const assert = require("node:assert/strict");
        const {createRequire} = require("node:module");
        const fromSocks = createRequire(require.resolve("socks"));
        const {Address6} = fromSocks("ip-address");
        assert.equal(Address6.isValid("2001:db8::1"), true);
        assert.deepEqual(new Address6("2001:db8::1").toUnsignedByteArray(), [
          32, 1, 13, 184, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
        ]);
        assert.equal(Address6.isValid("%".repeat(1_000_000) + "\n"), false);
      `,
    "--max-old-space-size=64",
    "--input-type=commonjs"
  );
}, 15_000);

test("ESLint's scoped minimatch patch preserves legacy consumers and bounds pattern expansion", () => {
  assertNode(
    String.raw`
        const assert = require("node:assert/strict");
        const {createRequire} = require("node:module");
        const fromEstree = createRequire(require.resolve("@typescript-eslint/typescript-estree"));
        const {minimatch, Minimatch} = fromEstree("minimatch");
        assert.equal(minimatch("src/example.ts", "**/*.ts", {dot: true}), true);
        assert.equal(minimatch("src/example.js", "**/*.ts", {dot: true}), false);
        new Minimatch("**/../".repeat(20) + "example.ts", {optimizationLevel: 2});
        const fromEslint = createRequire(require.resolve("eslint"));
        const legacy = fromEslint("minimatch");
        assert.equal(typeof legacy, "function");
        assert.equal(legacy("src/example.js", "**/*.js"), true);
      `,
    "--max-old-space-size=64",
    "--input-type=commonjs"
  );
}, 15_000);

test("Ajv and Lighthouse preserve safe URI and query serialization with patched dependencies", () => {
  assertNode(
    String.raw`
        const assert = require("node:assert/strict");
        const {createRequire} = require("node:module");
        const fromAjv = createRequire(require.resolve("ajv"));
        const uri = fromAjv("fast-uri");
        assert.equal(uri.parse("https://example.invalid/roles").host, "example.invalid");
        assert.notEqual(uri.normalize("%6Aavascript:alert(1)"), "javascript:alert(1)");
        assert.equal(uri.equal("https://example.invalid/a", "https://example.invalid/a/"), false);
        const fromBodyParser = createRequire(require.resolve("body-parser"));
        const qs = fromBodyParser("qs");
        assert.equal(qs.stringify({roles: ["one", "two"]}, {arrayFormat: "comma"}), "roles=one%2Ctwo");
        const hostile = JSON.parse('{"roles":[{"toString":"x"}]}');
        for (const encodeValuesOnly of [false, true]) {
          assert.doesNotThrow(() => qs.stringify(hostile, {arrayFormat: "comma", encodeValuesOnly}));
        }
      `,
    "--max-old-space-size=64",
    "--input-type=commonjs"
  );
}, 15_000);

test("Lighthouse's FTP dependency keeps its CommonJS API and bounds malformed listing parsing", () => {
  // Only synthetic strings are parsed; no FTP connection is opened.
  assertNode(
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
          const mlsd = parseList("__proto__=x;type=file;size=10; example.txt\r\n");
          assert.deepEqual(mlsd.map(({name, size}) => ({name, size})), [
            {name: "example.txt", size: 10},
          ]);
        } finally {
          client.close();
        }
      `,
    "--input-type=commonjs"
  );
}, 15_000);
