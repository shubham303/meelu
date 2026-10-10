import test from "node:test";
import assert from "node:assert/strict";
import { availableUpdate, installerUrl, isNewer } from "../src/main/update-check.js";

const manifest = {
  version: "0.2.0",
  installers: {
    "darwin-arm64": "https://downloads.meelu.tech/Meelu-mac-arm64.dmg",
    "darwin-x64": "https://downloads.meelu.tech/Meelu-mac-x64.dmg",
    "win32-x64": "https://downloads.meelu.tech/Meelu-windows-x64.exe",
  },
};

test("versions compare by number, not by text", () => {
  assert.equal(isNewer("0.10.0", "0.9.0"), true);
  assert.equal(isNewer("0.9.0", "0.10.0"), false);
  assert.equal(isNewer("1.0.0", "1.0.0"), false);
  assert.equal(isNewer("v1.0.1", "1.0.0"), true);
});

test("a malformed version is never newer", () => {
  assert.equal(isNewer("latest", "0.1.0"), false);
  assert.equal(isNewer(undefined, "0.1.0"), false);
  assert.equal(isNewer("0.2.0", "dev"), false);
});

test("the installer matches the running platform and architecture", () => {
  assert.equal(installerUrl(manifest, "darwin", "x64"), manifest.installers["darwin-x64"]);
  assert.equal(installerUrl(manifest, "win32", "x64"), manifest.installers["win32-x64"]);
});

test("an unknown platform or a non-https link falls back to the download page", () => {
  assert.equal(installerUrl(manifest, "linux", "x64"), "https://meelu.tech/download");
  assert.equal(
    installerUrl({ installers: { "darwin-arm64": "http://evil.example/x.dmg" } }, "darwin", "arm64"),
    "https://meelu.tech/download",
  );
});

test("an update is offered only when the manifest is ahead", () => {
  const where = { platform: "darwin", arch: "arm64" };
  assert.deepEqual(availableUpdate(manifest, { currentVersion: "0.1.0", ...where }), {
    currentVersion: "0.1.0",
    version: "0.2.0",
    downloadUrl: manifest.installers["darwin-arm64"],
  });
  assert.equal(availableUpdate(manifest, { currentVersion: "0.2.0", ...where }), null);
});
