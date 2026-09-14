import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

const SERVERS = [
  { dir: "email-mcp", missing: "the mailbox connector cannot send or read" },
];

const run = (command, args, cwd) =>
  spawnSync(command, args, { cwd, stdio: "inherit", shell: process.platform === "win32" });

let failed = 0;

for (const { dir, missing } of SERVERS) {
  const cwd = path.join(REPO_ROOT, dir);
  if (!fs.existsSync(path.join(cwd, "package.json"))) {
    console.warn(`! ${dir} is not in this checkout — skipping (${missing}).`);
    continue;
  }
  console.log(`— building ${dir} …`);
  const result = run("npm", ["install", "--no-audit", "--no-fund"], cwd);
  if (result.status !== 0) {
    failed += 1;
    console.warn(
      `! ${dir} did not build, so ${missing}.\n` +
        `  Fix it with:  npm install --prefix ${dir}   (from the repo root)`,
    );
  }
}


if (failed > 0) {
  console.warn(`\n${failed} server(s) did not build. The app will still start.`);
}
