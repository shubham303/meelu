import { randomBytes } from "node:crypto";
import fs from "node:fs";
import { safeStorage } from "electron";
import { appFile } from "../paths.js";

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
    const body = safeStorage.isEncryptionAvailable()
      ? safeStorage.decryptString(raw)
      : raw.toString("utf8");
    return JSON.parse(body);
  } catch {
    return {};
  }
}

function writeTokens(tokens) {
  const body = JSON.stringify(tokens);
  fs.writeFileSync(
    tokenFile(),
    safeStorage.isEncryptionAvailable()
      ? safeStorage.encryptString(body)
      : Buffer.from(body, "utf8"),
  );
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
