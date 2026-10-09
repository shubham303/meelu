import fs from "node:fs";
import { safeStorage } from "electron";
import { appFile, writeSecretFile } from "./paths.js";

const CONNECTOR_FIELDS = {
  gsc: { refreshToken: "secret" },
  ga4: { refreshToken: "secret" },
  analytics: { projectDir: "plain", dataDir: "plain" },
};

const MANUAL_CONNECTORS = new Set(["analytics"]);

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
  writeSecretFile(storeFile(), JSON.stringify(store, null, 2));
}

function mask(value) {
  return value.length > 8 ? `••••${value.slice(-4)}` : "••••••";
}

function encodeRecord(fields, values = {}) {
  const clean = {};
  for (const [k, v] of Object.entries(values ?? {})) {
    if (Object.hasOwn(fields, k) && typeof v === "string" && v.trim() !== "") clean[k] = v.trim();
  }
  const record = { updatedAt: new Date().toISOString(), preview: {} };
  for (const [k, v] of Object.entries(clean)) {
    record.preview[k] = fields[k] === "secret" ? mask(v) : v;
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

function knownProvider(provider) {
  if (typeof provider !== "string" || !Object.hasOwn(CONNECTOR_FIELDS, provider)) {
    throw new Error("Unknown connector.");
  }
  return provider;
}

export function saveConnector(provider, values = {}) {
  const store = readStore();
  store[knownProvider(provider)] = encodeRecord(CONNECTOR_FIELDS[provider], values);
  writeStore(store);
}

export function saveManualConnector(provider, values = {}) {
  if (!MANUAL_CONNECTORS.has(provider)) throw new Error("This connector cannot be set by hand.");
  saveConnector(provider, values);
}

export function removeConnector(provider) {
  knownProvider(provider);
  const store = readStore();
  delete store[provider];
  writeStore(store);
}
