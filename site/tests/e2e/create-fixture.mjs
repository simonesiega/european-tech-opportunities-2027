import {spawnSync} from "node:child_process";
import path from "node:path";
import {fileURLToPath} from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
// Exercise the real migrated schema and Python serialization, not a parallel test-only contract.
const result = spawnSync(
  "uv",
  ["run", "--frozen", "python", "scripts/testing/create_site_fixture.py"],
  {
    cwd: root,
    stdio: "inherit",
    shell: false,
  }
);
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
