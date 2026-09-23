import fs from "node:fs";
import { safeStorage } from "electron";
import { appFile } from "./paths.js";

function storeFile() {
  return appFile("connectors.json");
}

function readStore() {
  try {
    return JSON.parse(fs.readFileSync(storeFile(), "utf8"));
  } catch {
    return {};
  }
}

function writeStore(store) {
  fs.writeFileSync(storeFile(), JSON.stringify(store, null, 2));
}

function mask(value) {
  return value.length > 8 ? `••••${value.slice(-4)}` : "••••••";
}

function encodeRecord(values = {}, secretKeys = []) {
  const clean = {};
  for (const [k, v] of Object.entries(values ?? {})) {
    if (typeof v === "string" && v.trim() !== "") clean[k] = v.trim();
  }
  const secret = new Set(Array.isArray(secretKeys) ? secretKeys : []);
  const record = { updatedAt: new Date().toISOString(), preview: {} };
  for (const [k, v] of Object.entries(clean)) {
    record.preview[k] = secret.has(k) ? mask(v) : v;
  }
  if (Object.keys(clean).length > 0) {
    if (!safeStorage.isEncryptionAvailable()) {
      throw new Error("Secure storage is unavailable on this machine, so the key was not saved.");
    }
    record.valuesEnc = safeStorage.encryptString(JSON.stringify(clean)).toString("base64");
  }
  return record;
}

function decodeRecord(rec) {
  if (!rec) return null;
  if (!rec.valuesEnc) return {};
  try {
    return JSON.parse(safeStorage.decryptString(Buffer.from(rec.valuesEnc, "base64")));
  } catch {
    return {};
  }
}

export function listConnectors() {
  const out = {};
  for (const [provider, rec] of Object.entries(readStore())) {
    out[provider] = { fields: rec.preview ?? {}, updatedAt: rec.updatedAt ?? null };
  }
  return out;
}

export function connectorValues(provider) {
  return decodeRecord(readStore()[provider]);
}

export function saveConnector(provider, values = {}, secretKeys = []) {
  if (typeof provider !== "string" || !/^[\w-]+$/.test(provider)) {
    throw new Error("Invalid provider.");
  }
  const store = readStore();
  store[provider] = encodeRecord(values, secretKeys);
  writeStore(store);
}

export function removeConnector(provider) {
  const store = readStore();
  delete store[provider];
  writeStore(store);
}
