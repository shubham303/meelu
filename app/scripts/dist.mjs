import { spawnSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const APP_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const FLAVOURS = {
  prod: { productName: "Meelu", appId: "tech.meelu.app", artifactPrefix: "Meelu" },
  test: { productName: "Meelu Test", appId: "tech.meelu.app.test", artifactPrefix: "Meelu-Test" },
};

const PLATFORMS = {
  mac: { os: "darwin", flag: "--mac", label: "mac", archs: ["arm64", "x64"] },
  win: { os: "win32", flag: "--win", label: "windows", archs: ["x64"] },
  store: { os: "win32", flag: "--win", target: "appx", label: "windows", archs: ["x64"], prodOnly: true },
};

function fail(message) {
  console.error(`[dist] ${message}`);
  process.exit(1);
}

function nativePackages(os, arch) {
  return [`@anthropic-ai/claude-agent-sdk-${os}-${arch}`, `@img/sharp-${os}-${arch}`];
}

function installed(name) {
  return fs.existsSync(path.join(APP_ROOT, "node_modules", name, "package.json"));
}

const [flavourName, platformName, ...rest] = process.argv.slice(2);
const flavour = FLAVOURS[flavourName];
const platform = PLATFORMS[platformName];
if (!flavour || !platform) fail("usage: node scripts/dist.mjs <prod|test> <mac|win|store> [--arm64] [--x64]");
if (platform.prodOnly && flavourName !== "prod") fail(`${platformName} builds use the Store identity and exist only for prod`);

const requested = platform.archs.filter((arch) => rest.includes(`--${arch}`));
const archs = requested.length
  ? requested
  : platform.archs.filter((arch) => nativePackages(platform.os, arch).every(installed));
if (archs.length === 0) {
  fail(`no ${platform.label} architecture has its native packages installed; run npm ci --os=${platform.os} --cpu=<arch>`);
}
for (const arch of archs) {
  const missing = nativePackages(platform.os, arch).filter((name) => !installed(name));
  if (missing.length > 0) {
    fail(`${platform.label} ${arch} needs ${missing.join(", ")}; run npm ci --os=${platform.os} --cpu=${arch} first`);
  }
}

const passthrough = rest.filter((arg) => !platform.archs.some((arch) => arg === `--${arch}`));

const args = [
  platform.flag,
  ...(platform.target ? [platform.target] : []),
  ...archs.map((arch) => `--${arch}`),
  "--publish",
  "never",
  `-c.extraMetadata.meeluFlavour=${flavourName}`,
  `-c.productName=${flavour.productName}`,
  `-c.appId=${flavour.appId}`,
  `-c.${platform.target ?? platformName}.artifactName=${flavour.artifactPrefix}-${platform.label}-\${arch}.\${ext}`,
  ...(platformName === "mac"
    ? [
        "-c.electronFuses.enableEmbeddedAsarIntegrityValidation=true",
        "-c.electronFuses.resetAdHocDarwinSignature=true",
      ]
    : []),
  ...passthrough,
];

const cli = createRequire(import.meta.url).resolve("electron-builder/cli.js");
const result = spawnSync(process.execPath, [cli, ...args], { cwd: APP_ROOT, stdio: "inherit" });
process.exit(result.status ?? 1);
