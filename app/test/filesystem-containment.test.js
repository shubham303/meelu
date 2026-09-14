import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const MAIN = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/main");
const PATHS_MODULE = path.join(MAIN, "paths.js");

const DECLARED_EXCEPTIONS = {
  desktop: "screenshotDir — Cmd+Shift+S saves where the user expects a screenshot",
  downloads: "saveDialogDir — only the default offered in a native Save As dialog",
};

function sources(dir = MAIN) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) return sources(full);
    return e.isFile() && e.name.endsWith(".js") ? [full] : [];
  });
}

const files = sources().map((file) => ({
  file,
  rel: path.relative(MAIN, file),
  text: fs.readFileSync(file, "utf8"),
}));

test("every filesystem root enters through paths.js", () => {
  const strays = files
    .filter((f) => f.file !== PATHS_MODULE && /\bapp\.getPath\(/.test(f.text))
    .map((f) => f.rel);
  assert.deepEqual(
    strays,
    [],
    `these ask the OS for a root directly instead of importing from paths.js: ${strays.join(", ")}`,
  );
});

test("paths.js reaches outside the app root only where declared", () => {
  const text = fs.readFileSync(PATHS_MODULE, "utf8");
  const asked = [...text.matchAll(/app\.getPath\("([^"]+)"\)/g)].map((m) => m[1]);
  assert.ok(asked.includes("userData"), "paths.js must define the app root");
  const outside = asked.filter((name) => name !== "userData");
  const undeclared = outside.filter((name) => !(name in DECLARED_EXCEPTIONS));
  assert.deepEqual(
    undeclared,
    [],
    `paths.js reaches ${undeclared.join(", ")} with no entry in DECLARED_EXCEPTIONS — ` +
      "add one saying why the app writes there, or keep the write inside the app root",
  );
});

test("no write targets a hardcoded absolute path", () => {
  const write = /\b(?:writeFileSync|appendFileSync|copyFileSync|mkdirSync|createWriteStream|unlinkSync|rmSync)\s*\(\s*(["'`])([^"'`]*)\1/g;
  const offenders = [];
  for (const { rel, text } of files) {
    for (const [, , literal] of text.matchAll(write)) {
      if (literal.startsWith("/") || literal.startsWith("~")) offenders.push(`${rel}: ${literal}`);
    }
  }
  assert.deepEqual(offenders, [], `absolute write targets: ${offenders.join(", ")}`);
});

test("no module uses app or path without importing it", () => {
  const broken = [];
  for (const { rel, text } of files) {
    const body = text.replace(/^import[\s\S]*?from\s+["'][^"']+["'];?$/gm, "");
    if (/\bapp\.\w/.test(body) && !/^import\s*\{[^}]*\bapp\b[^}]*\}\s*from\s*"electron"/m.test(text)) {
      broken.push(`${rel} uses app.* without importing it from electron`);
    }
    if (/\bpath\.\w/.test(body) && !/^import\s+path\s+from\s+"node:path"/m.test(text)) {
      broken.push(`${rel} uses path.* without importing node:path`);
    }
  }
  assert.deepEqual(broken, [], broken.join("; "));
});
