import fs from "node:fs";
import { safeStorage } from "electron";
import { appFile } from "../paths.js";

function cacheFile() {
  return appFile("workspace-keys.json");
}

function read() {
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(cacheFile(), "utf8"));
  } catch {
    return {};
  }
  if (!raw?.keysEnc) return {};
  try {
    return JSON.parse(safeStorage.decryptString(Buffer.from(raw.keysEnc, "base64")));
  } catch {
    return {};
  }
}

function write(map) {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error(
      "Secure storage is unavailable on this machine, so the workspace API key cannot " +
        "be saved. Set MEELU_API_KEY (Dashboard → Settings → API keys) instead.",
    );
  }
  fs.writeFileSync(
    cacheFile(),
    JSON.stringify(
      { updatedAt: new Date().toISOString(), keysEnc: safeStorage.encryptString(JSON.stringify(map)).toString("base64") },
      null,
      2,
    ),
  );
}

export function cachedWorkspaceKey(liveIds) {
  const map = read();
  const live = new Set(liveIds);
  const hit = Object.keys(map).find((id) => live.has(id));
  return hit ? map[hit] : null;
}

export function rememberWorkspaceKey(id, key, liveIds = []) {
  const live = new Set([...liveIds, id]);
  const map = Object.fromEntries(Object.entries(read()).filter(([k]) => live.has(k)));
  map[id] = key;
  write(map);
}
