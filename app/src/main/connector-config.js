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

const RESERVED = new Set(["mailboxAccounts", "providerDefaults"]);

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
    if (RESERVED.has(provider)) continue;
    out[provider] = { fields: rec.preview ?? {}, updatedAt: rec.updatedAt ?? null };
  }
  return out;
}

export function connectorValues(provider) {
  return decodeRecord(readStore()[provider]);
}

export function saveConnector(provider, values = {}, secretKeys = []) {
  if (typeof provider !== "string" || !/^[\w-]+$/.test(provider) || RESERVED.has(provider)) {
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

function accountId(address) {
  const id = String(address ?? "").trim().toLowerCase();
  if (!id.includes("@")) throw new Error("A mailbox needs an email address.");
  return id;
}

function mailboxBook(store) {
  return store.mailboxAccounts ?? {};
}

export function listMailboxAccounts() {
  const store = readStore();
  return Object.entries(mailboxBook(store)).map(([id, rec]) => ({
    id,
    address: rec.preview?.address ?? id,
    fields: rec.preview ?? {},
    updatedAt: rec.updatedAt ?? null,
  }));
}

export function saveMailboxAccount(values = {}, secretKeys = []) {
  const id = accountId(values?.address);
  const store = readStore();
  const book = { ...mailboxBook(store) };
  book[id] = encodeRecord(values, secretKeys);
  store.mailboxAccounts = book;
  writeStore(store);
  return id;
}

export function removeMailboxAccount(id) {
  const store = readStore();
  const book = { ...mailboxBook(store) };
  delete book[id];
  store.mailboxAccounts = book;
  writeStore(store);
}

function mailboxAccountFor(address) {
  const book = mailboxBook(readStore());
  if (address) return book[address] ? address : null;
  const ids = Object.keys(book);
  return ids.length === 1 ? ids[0] : null;
}

export function mailboxValuesFor(address) {
  const id = mailboxAccountFor(address);
  return id == null ? null : decodeRecord(mailboxBook(readStore())[id]);
}

export function providerDefault(domain) {
  const defaults = readStore().providerDefaults ?? {};
  return defaults[domain] ?? null;
}

export function setProviderDefault(domain, providerId) {
  const store = readStore();
  const defaults = { ...(store.providerDefaults ?? {}) };
  if (providerId) defaults[domain] = providerId;
  else delete defaults[domain];
  store.providerDefaults = defaults;
  writeStore(store);
}

export function migrateLegacyMailbox() {
  const store = readStore();
  const legacy = store.mailbox;
  if (!legacy || store.mailboxAccounts) return;
  const address = legacy.preview?.address;
  if (!address) return;
  store.mailboxAccounts = { [accountId(address)]: legacy };
  delete store.mailbox;
  writeStore(store);
}
