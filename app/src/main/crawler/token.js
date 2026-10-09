import { randomBytes } from "node:crypto";
import fs from "node:fs";
import { safeStorage } from "electron";
import { appFile, writeSecretFile } from "../paths.js";

function tokenFile() {
  return appFile("crawl-tokens.enc");
}

function readTokens() {
  let raw;
  try {
    raw = fs.readFileSync(tokenFile());
  } catch {
    return {};
  }
  try {
    return JSON.parse(safeStorage.decryptString(raw));
  } catch {
    return {};
  }
}

function writeTokens(tokens) {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error("Secure storage is unavailable on this machine, so the crawl token was not saved.");
  }
  writeSecretFile(tokenFile(), safeStorage.encryptString(JSON.stringify(tokens)));
}

export function crawlToken(domain) {
  const key = String(domain ?? "").trim().toLowerCase();
  if (!key) return null;
  const tokens = readTokens();
  if (!tokens[key]) {
    tokens[key] = `mlc_${randomBytes(24).toString("base64url")}`;
    writeTokens(tokens);
  }
  return tokens[key];
}
